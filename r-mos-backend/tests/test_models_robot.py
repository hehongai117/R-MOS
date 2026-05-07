"""Tests for RobotModel and TeacherRobotBinding ORM models."""
import pytest
from sqlalchemy import select
from app.models.robot_model import RobotModel, TeacherRobotBinding, RobotVisibility, RobotStatus


@pytest.mark.asyncio
async def test_create_robot_model(db_session):
    robot = RobotModel(
        brand="R-MOS", model_name="ATOM-01", version="1.0",
        visibility=RobotVisibility.PRIVATE, status=RobotStatus.DRAFT,
    )
    db_session.add(robot)
    await db_session.commit()
    await db_session.refresh(robot)
    assert robot.id is not None
    assert robot.brand == "R-MOS"
    assert robot.visibility == RobotVisibility.PRIVATE
    assert robot.created_at is not None


@pytest.mark.asyncio
async def test_create_teacher_binding(db_session):
    robot = RobotModel(brand="宇树", model_name="H1", version="2.0")
    db_session.add(robot)
    await db_session.commit()
    await db_session.refresh(robot)
    binding = TeacherRobotBinding(teacher_id=1, robot_model_id=robot.id, binding_type="owner")
    db_session.add(binding)
    await db_session.commit()
    await db_session.refresh(binding)
    assert binding.id is not None
    assert binding.binding_type == "owner"


@pytest.mark.asyncio
async def test_robot_model_shared_visibility(db_session):
    robot = RobotModel(
        brand="优必选", model_name="Walker X", version="1.0",
        visibility=RobotVisibility.SHARED, status=RobotStatus.READY,
        description="通用人形机器人",
    )
    db_session.add(robot)
    await db_session.commit()
    result = await db_session.execute(
        select(RobotModel).where(RobotModel.visibility == RobotVisibility.SHARED)
    )
    found = result.scalar_one()
    assert found.brand == "优必选"
    assert found.status == RobotStatus.READY
