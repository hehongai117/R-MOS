from __future__ import annotations

from pathlib import Path

from app.models.robot_project import RobotProject, RobotProjectStatus
from app.models.robot_project_file import RobotProjectFile
from app.services.knowledge.robot_manifest_builder import RobotManifestBuilder


def test_robot_manifest_builder_preserves_paths_and_marks_review_nodes() -> None:
    project = RobotProject(
        id="proj-1",
        robot_key="fourier-n1-v1",
        brand="Fourier",
        model="N1",
        version="v1",
        status=RobotProjectStatus.UPLOADED,
        source_package_path="storage/proj-1/FourierN1.zip",
    )
    files = [
        RobotProjectFile(
            project_id=project.id,
            filename="总装.SLDASM",
            relative_path="cad/总装.SLDASM",
            file_kind="assembly",
            storage_path="storage/proj-1/cad/总装.SLDASM",
        ),
        RobotProjectFile(
            project_id=project.id,
            filename="手臂.SLDPRT",
            relative_path="cad/手臂.SLDPRT",
            file_kind="part_model",
            storage_path="storage/proj-1/cad/手臂.SLDPRT",
        ),
        RobotProjectFile(
            project_id=project.id,
            filename="手臂.glb",
            relative_path="viewer/手臂.glb",
            file_kind="viewer_asset",
            storage_path="storage/proj-1/viewer/手臂.glb",
        ),
    ]

    manifest = RobotManifestBuilder().build(project, files)

    assert manifest["viewer_manifest"]["robotId"] == "fourier-n1-v1"
    assert "viewer/手臂.glb" in manifest["viewer_manifest"]["parts"]
    assert manifest["mapping"]["手臂"]["source_paths"] == ["cad/手臂.SLDPRT", "viewer/手臂.glb"]
    assert manifest["needs_review_nodes"]


def test_robot_manifest_builder_promotes_urdf_and_stl_into_runtime_assets(tmp_path: Path) -> None:
    project = RobotProject(
        id="proj-urdf",
        robot_key="fourier-n1-urdf",
        brand="Fourier",
        model="N1",
        version="urdf",
        status=RobotProjectStatus.UPLOADED,
        source_package_path=str(tmp_path / "FourierN1.zip"),
    )
    urdf_path = tmp_path / "urdf" / "N1.urdf"
    urdf_path.parent.mkdir(parents=True, exist_ok=True)
    urdf_path.write_text(
        """
        <robot name="N1">
          <link name="base_link">
            <visual>
              <geometry>
                <mesh filename="../meshes/base_link.STL" />
              </geometry>
            </visual>
          </link>
          <link name="elbow_link">
            <visual>
              <geometry>
                <mesh filename="../meshes/elbow_link.STL" />
              </geometry>
            </visual>
          </link>
          <joint name="base_to_elbow" type="fixed">
            <parent link="base_link" />
            <child link="elbow_link" />
          </joint>
        </robot>
        """,
        encoding="utf-8",
    )
    mesh_dir = tmp_path / "meshes"
    mesh_dir.mkdir(parents=True, exist_ok=True)
    (mesh_dir / "base_link.STL").write_text("solid base\nendsolid base\n", encoding="utf-8")
    (mesh_dir / "elbow_link.STL").write_text("solid elbow\nendsolid elbow\n", encoding="utf-8")
    step_path = tmp_path / "cad" / "base_link.STEP"
    step_path.parent.mkdir(parents=True, exist_ok=True)
    step_path.write_text("ISO-10303-21;", encoding="utf-8")

    files = [
        RobotProjectFile(
            project_id=project.id,
            filename="N1.urdf",
            relative_path="urdf/N1.urdf",
            file_kind="structure",
            storage_path=str(urdf_path),
        ),
        RobotProjectFile(
            project_id=project.id,
            filename="base_link.STL",
            relative_path="meshes/base_link.STL",
            file_kind="part_model",
            storage_path=str(mesh_dir / "base_link.STL"),
        ),
        RobotProjectFile(
            project_id=project.id,
            filename="elbow_link.STL",
            relative_path="meshes/elbow_link.STL",
            file_kind="part_model",
            storage_path=str(mesh_dir / "elbow_link.STL"),
        ),
        RobotProjectFile(
            project_id=project.id,
            filename="base_link.STEP",
            relative_path="cad/base_link.STEP",
            file_kind="part_model",
            storage_path=str(step_path),
        ),
    ]

    manifest = RobotManifestBuilder().build(project, files)

    assert manifest["viewer_manifest"]["parts"] == ["meshes/base_link.STL", "meshes/elbow_link.STL"]
    assert manifest["viewer_manifest"]["structures"] == [
        {
            "path": "urdf/N1.urdf",
            "root_nodes": ["base_link"],
            "structure_type": "urdf",
        }
    ]
    assert manifest["viewer_manifest"]["assets"] == [
        {
            "asset_id": "base_link::meshes/base_link.STL",
            "asset_type": "stl",
            "display_name": "base_link",
            "node_id": "base_link",
            "path": "meshes/base_link.STL",
            "source_paths": ["meshes/base_link.STL", "cad/base_link.STEP", "urdf/N1.urdf"],
        },
        {
            "asset_id": "elbow_link::meshes/elbow_link.STL",
            "asset_type": "stl",
            "display_name": "elbow_link",
            "node_id": "elbow_link",
            "path": "meshes/elbow_link.STL",
            "source_paths": ["meshes/elbow_link.STL", "urdf/N1.urdf"],
        },
    ]
    assert manifest["mapping"]["base_link"]["runtime_asset_paths"] == ["meshes/base_link.STL"]
    assert manifest["mapping"]["base_link"]["source_paths"] == [
        "meshes/base_link.STL",
        "cad/base_link.STEP",
        "urdf/N1.urdf",
    ]
    assert manifest["mapping"]["elbow_link"]["runtime_asset_paths"] == ["meshes/elbow_link.STL"]
    assert manifest["tree"]["root_nodes"] == ["base_link"]
    assert manifest["tree"]["nodes"] == [
        {
            "children": ["elbow_link"],
            "display_name": "base_link",
            "file_kinds": ["part_model", "structure"],
            "id": "base_link",
            "parent_id": None,
            "runtime_asset_paths": ["meshes/base_link.STL"],
            "source_paths": ["meshes/base_link.STL", "cad/base_link.STEP", "urdf/N1.urdf"],
        },
        {
            "children": [],
            "display_name": "elbow_link",
            "file_kinds": ["part_model", "structure"],
            "id": "elbow_link",
            "parent_id": "base_link",
            "runtime_asset_paths": ["meshes/elbow_link.STL"],
            "source_paths": ["meshes/elbow_link.STL", "urdf/N1.urdf"],
        },
    ]
