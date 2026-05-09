"""Unit tests for assembly manifest generator."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.analysis_task import AnalysisTask, AnalysisTaskType
from app.models.robot_asset import RobotAsset, AssetType
from app.services.analysis.manifest_generator import ManifestGenerator


@pytest.fixture
def generator():
    return ManifestGenerator()


@pytest.fixture
def mock_task():
    task = MagicMock(spec=AnalysisTask)
    task.id = 1
    task.robot_model_id = 10
    task.task_type = AnalysisTaskType.CAD_PARSE
    return task


@pytest.mark.asyncio
async def test_process_no_glb_assets(generator, mock_task):
    """没有 GLB 资产时应返回 manifests_created=0。"""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await generator.process(mock_task, mock_db)
    assert result["manifests_created"] == 0


@pytest.mark.asyncio
async def test_process_creates_manifest_asset(generator, mock_task):
    """应为 GLB 资产生成装配清单并存储。"""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()

    mock_glb = MagicMock(spec=RobotAsset)
    mock_glb.id = 200
    mock_glb.robot_model_id = 10
    mock_glb.asset_type = AssetType.MODEL_GLB
    mock_glb.file_path = "10/models/robot.glb"

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_glb]
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch.object(generator, "_parse_glb_nodes") as mock_parse, \
         patch.object(generator, "_store_manifest") as mock_store:
        mock_parse.return_value = {
            "name": "root",
            "children": [
                {"name": "base_link", "type": "mesh", "vertices": 500, "faces": 200},
                {"name": "arm_link", "type": "mesh", "vertices": 300, "faces": 100},
            ]
        }
        mock_store.return_value = "10/manifests/robot_manifest.json"

        result = await generator.process(mock_task, mock_db)

    assert result["manifests_created"] == 1
    assert mock_db.add.call_count == 1
    created = mock_db.add.call_args_list[0][0][0]
    assert isinstance(created, RobotAsset)
    assert created.asset_type == AssetType.MANIFEST
    assert created.robot_model_id == 10


@pytest.mark.asyncio
async def test_process_continues_on_parse_error(generator, mock_task):
    """单个 GLB 解析失败时应继续处理其他资产，不抛出异常。"""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()

    mock_glb1 = MagicMock(spec=RobotAsset)
    mock_glb1.id = 200
    mock_glb1.robot_model_id = 10
    mock_glb1.asset_type = AssetType.MODEL_GLB
    mock_glb1.file_path = "10/models/robot1.glb"

    mock_glb2 = MagicMock(spec=RobotAsset)
    mock_glb2.id = 201
    mock_glb2.robot_model_id = 10
    mock_glb2.asset_type = AssetType.MODEL_GLB
    mock_glb2.file_path = "10/models/robot2.glb"

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_glb1, mock_glb2]
    mock_db.execute = AsyncMock(return_value=mock_result)

    def parse_side_effect(asset):
        if asset.id == 200:
            raise RuntimeError("trimesh load failed")
        return {"name": "root", "children": []}

    with patch.object(generator, "_parse_glb_nodes", side_effect=parse_side_effect), \
         patch.object(generator, "_store_manifest", return_value="10/manifests/robot2_manifest.json"):
        result = await generator.process(mock_task, mock_db)

    assert result["manifests_created"] == 1


def test_count_nodes(generator):
    """节点计数应递归统计所有节点。"""
    tree = {
        "name": "root",
        "children": [
            {"name": "base_link", "children": []},
            {"name": "arm_link", "children": [
                {"name": "gripper", "children": []}
            ]},
        ]
    }
    assert generator._count_nodes(tree) == 4  # root + 2 children + 1 grandchild


def test_count_nodes_single(generator):
    """单节点（无 children 字段）应返回 1。"""
    tree = {"name": "root"}
    assert generator._count_nodes(tree) == 1


def test_build_node_tree_from_scene(generator):
    """_build_node_tree 应从 trimesh scene 构建正确的树结构。"""
    mock_scene = MagicMock()
    mock_geom1 = MagicMock()
    mock_geom1.vertices = MagicMock()
    mock_geom1.vertices.shape = (500, 3)
    mock_geom1.faces = MagicMock()
    mock_geom1.faces.shape = (200, 3)
    mock_scene.geometry = {"base_link": mock_geom1}

    tree = generator._build_node_tree(mock_scene)
    assert tree["name"] == "root"
    assert len(tree["children"]) == 1
    assert tree["children"][0]["name"] == "base_link"
    assert tree["children"][0]["vertices"] == 500
    assert tree["children"][0]["faces"] == 200
    assert tree["children"][0]["type"] == "mesh"


def test_build_node_tree_single_mesh(generator):
    """单个 Mesh（非 Scene）应直接包装为根节点。"""
    import trimesh
    mock_mesh = MagicMock(spec=trimesh.Trimesh)
    mock_mesh.vertices = MagicMock()
    mock_mesh.vertices.shape = (100, 3)
    mock_mesh.faces = MagicMock()
    mock_mesh.faces.shape = (50, 3)

    tree = generator._build_node_tree(mock_mesh)
    assert tree["name"] == "root"
    assert tree["type"] == "mesh"
    assert tree["vertices"] == 100
    assert tree["faces"] == 50
    assert tree.get("children", []) == []
