# r-mos-backend/tests/test_api_robots.py
"""Integration tests for robot API endpoints."""
import pytest
import pytest_asyncio
from uuid import uuid4

from app.models.robot_model import RobotModel, RobotVisibility, RobotStatus, TeacherRobotBinding
from app.models.robot_asset import RobotAsset, AssetType
from app.models.analysis_task import AnalysisTask, AnalysisTaskStatus, AnalysisTaskType
from app.models.user import User


def test_robots_module_imports():
    """Verify the robots endpoint module can be imported."""
    from app.api.v1.endpoints import robots
    assert hasattr(robots, "router")
    assert hasattr(robots, "create_robot")
    assert hasattr(robots, "list_robots")
    assert hasattr(robots, "get_robot")
    assert hasattr(robots, "update_robot")
    assert hasattr(robots, "delete_robot")
    assert hasattr(robots, "upload_robot_files")
    assert hasattr(robots, "trigger_analysis")
    assert hasattr(robots, "publish_robot")
    assert hasattr(robots, "set_visibility")


# --- DB-level tests (no HTTP, using fixtures from conftest) ---

@pytest.mark.asyncio
async def test_create_robot_model_db(test_db):
    """Test creating a RobotModel directly in DB."""
    robot = RobotModel(
        brand="TestBrand",
        model_name="TestBot-X1",
        version="1.0",
        visibility=RobotVisibility.PRIVATE,
        status=RobotStatus.DRAFT,
    )
    test_db.add(robot)
    await test_db.commit()
    await test_db.refresh(robot)
    assert robot.id is not None
    assert robot.brand == "TestBrand"
    assert robot.status == RobotStatus.DRAFT


@pytest.mark.asyncio
async def test_robot_publish_state_machine(test_db):
    """Test publish state transitions."""
    robot = RobotModel(
        brand="TestBrand",
        model_name="TestBot-X2",
        visibility=RobotVisibility.PRIVATE,
        status=RobotStatus.DRAFT,
    )
    test_db.add(robot)
    await test_db.commit()

    # draft → ready
    robot.status = RobotStatus.READY
    await test_db.commit()
    await test_db.refresh(robot)
    assert robot.status == RobotStatus.READY

    # ready → draft (unpublish)
    robot.status = RobotStatus.DRAFT
    await test_db.commit()
    await test_db.refresh(robot)
    assert robot.status == RobotStatus.DRAFT


@pytest.mark.asyncio
async def test_robot_visibility_toggle(test_db):
    """Test visibility toggle."""
    robot = RobotModel(
        brand="TestBrand",
        model_name="TestBot-X3",
        visibility=RobotVisibility.PRIVATE,
        status=RobotStatus.DRAFT,
    )
    test_db.add(robot)
    await test_db.commit()

    robot.visibility = RobotVisibility.SHARED
    await test_db.commit()
    await test_db.refresh(robot)
    assert robot.visibility == RobotVisibility.SHARED


@pytest.mark.asyncio
async def test_robot_asset_creation(test_db):
    """Test creating an asset record."""
    robot = RobotModel(
        brand="TestBrand",
        model_name="TestBot-X4",
        visibility=RobotVisibility.PRIVATE,
        status=RobotStatus.DRAFT,
    )
    test_db.add(robot)
    await test_db.flush()

    asset = RobotAsset(
        robot_model_id=robot.id,
        asset_type=AssetType.UPLOAD_ORIGINAL,
        file_path="1/uploads/manual.pdf",
        file_size=1024,
    )
    test_db.add(asset)
    await test_db.commit()
    await test_db.refresh(asset)
    assert asset.id is not None
    assert asset.asset_type == AssetType.UPLOAD_ORIGINAL


@pytest.mark.asyncio
async def test_analysis_task_creation(test_db):
    """Test creating an analysis task."""
    robot = RobotModel(
        brand="TestBrand",
        model_name="TestBot-X5",
        visibility=RobotVisibility.PRIVATE,
        status=RobotStatus.DRAFT,
    )
    test_db.add(robot)
    await test_db.flush()

    task = AnalysisTask(
        robot_model_id=robot.id,
        task_type=AnalysisTaskType.FULL,
        status=AnalysisTaskStatus.PENDING,
        input_document_ids=[1, 2, 3],
    )
    test_db.add(task)
    await test_db.commit()
    await test_db.refresh(task)
    assert task.id is not None
    assert task.status == AnalysisTaskStatus.PENDING


@pytest.mark.asyncio
async def test_teacher_robot_binding(test_db, test_user):
    """Test creating teacher-robot binding."""
    robot = RobotModel(
        brand="TestBrand",
        model_name="TestBot-X6",
        owner_teacher_id=test_user.id,
        visibility=RobotVisibility.PRIVATE,
        status=RobotStatus.DRAFT,
    )
    test_db.add(robot)
    await test_db.flush()

    binding = TeacherRobotBinding(
        teacher_id=test_user.id,
        robot_model_id=robot.id,
        binding_type="owner",
    )
    test_db.add(binding)
    await test_db.commit()
    await test_db.refresh(binding)
    assert binding.binding_type == "owner"
