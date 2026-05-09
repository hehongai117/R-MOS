"""Unit tests for CAD → GLB converter."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.analysis_task import AnalysisTask, AnalysisTaskType
from app.models.robot_asset import RobotAsset, AssetType
from app.services.analysis.cad_converter import CadConverter


@pytest.fixture
def converter():
    return CadConverter()


@pytest.fixture
def mock_task():
    task = MagicMock(spec=AnalysisTask)
    task.id = 1
    task.robot_model_id = 10
    task.task_type = AnalysisTaskType.CAD_PARSE
    return task


@pytest.mark.asyncio
async def test_process_no_cad_files(converter, mock_task):
    """没有 CAD/GLB 资产时应返回 skipped。"""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await converter.process(mock_task, mock_db)
    assert result.get("skipped") is True


@pytest.mark.asyncio
async def test_process_glb_file_direct_copy(converter, mock_task):
    """GLB 文件应直接复制，不转换。"""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()

    mock_asset = MagicMock(spec=RobotAsset)
    mock_asset.id = 100
    mock_asset.robot_model_id = 10
    mock_asset.asset_type = AssetType.UPLOAD_ORIGINAL
    mock_asset.file_path = "10/uploads/robot.glb"
    mock_asset.file_size = 5000

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_asset]
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch.object(converter, "_copy_glb_asset") as mock_copy:
        mock_copy.return_value = {"file_path": "10/models/robot.glb", "file_size": 5000}
        result = await converter.process(mock_task, mock_db)

    assert result["glb_copied"] == 1
    mock_copy.assert_called_once_with(mock_asset)
    assert mock_db.add.call_count == 1
    created = mock_db.add.call_args_list[0][0][0]
    assert isinstance(created, RobotAsset)
    assert created.asset_type == AssetType.MODEL_GLB


@pytest.mark.asyncio
async def test_process_cad_file_converted(converter, mock_task):
    """STEP 文件应触发 CAD 转换。"""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()

    mock_asset = MagicMock(spec=RobotAsset)
    mock_asset.id = 200
    mock_asset.robot_model_id = 10
    mock_asset.asset_type = AssetType.UPLOAD_ORIGINAL
    mock_asset.file_path = "10/uploads/part.step"
    mock_asset.file_size = 10000

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_asset]
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch.object(converter, "_convert_cad_to_glb") as mock_convert:
        mock_convert.return_value = {
            "file_path": "10/models/part.glb",
            "file_size": 8000,
            "quality": {"passed": True, "issues": None},
        }
        result = await converter.process(mock_task, mock_db)

    assert result["models_converted"] == 1
    assert result.get("glb_copied", 0) == 0
    mock_convert.assert_called_once_with(mock_asset)
    assert mock_db.add.call_count == 1
    created = mock_db.add.call_args_list[0][0][0]
    assert isinstance(created, RobotAsset)
    assert created.asset_type == AssetType.MODEL_GLB


@pytest.mark.asyncio
async def test_process_cad_conversion_failure(converter, mock_task):
    """CAD 转换失败时应记录错误，不抛出异常。"""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()

    mock_asset = MagicMock(spec=RobotAsset)
    mock_asset.id = 300
    mock_asset.robot_model_id = 10
    mock_asset.asset_type = AssetType.UPLOAD_ORIGINAL
    mock_asset.file_path = "10/uploads/bad.stp"
    mock_asset.file_size = 5000

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_asset]
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch.object(converter, "_convert_cad_to_glb") as mock_convert:
        mock_convert.return_value = None  # 转换失败返回 None
        result = await converter.process(mock_task, mock_db)

    assert result["models_converted"] == 0
    assert result["errors"] is not None
    assert len(result["errors"]) >= 1


def test_quality_check_valid(converter):
    """质量检查应通过正常参数。"""
    result = converter._quality_check(vertices=1000, faces=500, file_size=1024 * 100)
    assert result["passed"] is True
    assert result["issues"] is None


def test_quality_check_too_few_vertices(converter):
    """顶点数太少应不通过。"""
    result = converter._quality_check(vertices=2, faces=1, file_size=100)
    assert result["passed"] is False
    assert result["issues"] is not None


def test_quality_check_file_too_large(converter):
    """文件超过 200MB 应不通过。"""
    result = converter._quality_check(vertices=1000, faces=500, file_size=201 * 1024 * 1024)
    assert result["passed"] is False
    assert result["issues"] is not None


def test_quality_check_both_issues(converter):
    """顶点数太少且文件过大时，issues 列表应包含两个问题。"""
    result = converter._quality_check(vertices=1, faces=0, file_size=300 * 1024 * 1024)
    assert result["passed"] is False
    assert len(result["issues"]) >= 2
