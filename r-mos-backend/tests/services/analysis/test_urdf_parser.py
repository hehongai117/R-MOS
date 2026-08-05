# tests/services/analysis/test_urdf_parser.py
import pytest
from app.services.analysis.urdf_parser import URDFParser, URDFParseResult

MINIMAL_URDF = """<?xml version="1.0"?>
<robot name="test_bot">
  <link name="base_link">
    <visual>
      <geometry><mesh filename="../meshes/base_link.STL"/></geometry>
      <origin xyz="0 0 0" rpy="0 0 0"/>
    </visual>
  </link>
  <link name="arm_link">
    <visual>
      <geometry><mesh filename="../meshes/arm_link.STL"/></geometry>
      <origin xyz="0 0 0" rpy="0 0 0"/>
    </visual>
  </link>
  <joint name="arm_joint" type="revolute">
    <parent link="base_link"/>
    <child link="arm_link"/>
    <origin xyz="0 0 0.5" rpy="0 0 0"/>
    <axis xyz="0 0 1"/>
    <limit lower="-1.57" upper="1.57" effort="100" velocity="1"/>
  </joint>
</robot>
"""


def test_parse_links():
    parser = URDFParser()
    result = parser.parse(MINIMAL_URDF)
    assert result.robot_name == "test_bot"
    assert len(result.links) == 2
    assert result.links[0].name == "base_link"
    assert result.links[0].mesh_filename == "../meshes/base_link.STL"
    assert result.links[1].name == "arm_link"


def test_parse_joints():
    parser = URDFParser()
    result = parser.parse(MINIMAL_URDF)
    assert len(result.joints) == 1
    j = result.joints[0]
    assert j.name == "arm_joint"
    assert j.joint_type == "revolute"
    assert j.parent_link == "base_link"
    assert j.child_link == "arm_link"
    assert j.origin_xyz == [0.0, 0.0, 0.5]
    assert j.origin_rpy == [0.0, 0.0, 0.0]
    assert j.axis == [0.0, 0.0, 1.0]
    assert j.limit_lower == pytest.approx(-1.57)
    assert j.limit_upper == pytest.approx(1.57)


def test_root_link_detection():
    parser = URDFParser()
    result = parser.parse(MINIMAL_URDF)
    assert result.root_link == "base_link"


def test_to_assembly_manifest():
    parser = URDFParser()
    result = parser.parse(MINIMAL_URDF)
    manifest = result.to_assembly_manifest(robot_model_id=99)
    assert manifest["version"] == "2026-05-16"
    assert manifest["robotId"] == "99"
    assert manifest["rootNodeId"] == "base_link"
    assert len(manifest["nodes"]) == 2
    assert len(manifest["joints"]) == 1
    # Check transform on child link (arm_link should have joint origin as translation)
    arm_node = next(n for n in manifest["nodes"] if n["id"] == "arm_link")
    assert arm_node["transform"]["translation"] == [0.0, 0.0, 0.5]
    assert arm_node["parent_id"] == "base_link"
    # mesh_catalog should map link_name_mesh → expected GLB path
    assert "base_link_mesh" in manifest["mesh_catalog"]
    assert "arm_link_mesh" in manifest["mesh_catalog"]


MIXED_CASE_URDF = """<?xml version="1.0"?>
<robot name="mixed_case_bot">
  <link name="base_link">
    <visual>
      <geometry><mesh filename="package://d/meshes/base_link.STL"/></geometry>
    </visual>
  </link>
  <link name="left_Link1">
    <visual>
      <geometry><mesh filename="package://d/meshes/left_Link1.STL"/></geometry>
    </visual>
  </link>
  <joint name="j1" type="revolute">
    <parent link="base_link"/>
    <child link="left_Link1"/>
    <origin xyz="0 0 0" rpy="0 0 0"/>
    <axis xyz="0 0 1"/>
    <limit lower="-1" upper="1" effort="1" velocity="1"/>
  </joint>
</robot>
"""


def test_mesh_catalog_paths_are_lowercase_for_mixed_case_links():
    """上传落盘会强制小写文件名，manifest 引用的 GLB 路径必须与之一致。

    回归用例：URDF link 名带大写（如 SolidWorks 导出的 left_Link1）时，
    manifest 若保留原大小写，会与实际落盘的 left_link1.glb 不匹配 —
    在大小写敏感的文件系统（Linux）上 3D 资产 404，
    且发布闸门精确比对时会误判"资产缺失"。
    """
    parser = URDFParser()
    result = parser.parse(MIXED_CASE_URDF)
    manifest = result.to_assembly_manifest(robot_model_id=1)

    # key 保留原始 link 名（nodes 通过它引用 catalog，不涉及文件系统）
    assert "left_Link1_mesh" in manifest["mesh_catalog"]
    # 值是文件路径，必须小写以匹配落盘
    assert manifest["mesh_catalog"]["left_Link1_mesh"] == "left_link1.glb"
    assert manifest["mesh_catalog"]["base_link_mesh"] == "base_link.glb"
