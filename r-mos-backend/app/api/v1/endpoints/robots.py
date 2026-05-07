"""Robot model CRUD API endpoints."""
import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.authz_guard import ActorContext, get_current_actor
from app.models.robot_model import RobotModel, RobotVisibility, RobotStatus, TeacherRobotBinding
from app.schemas.robot_model import (
    RobotModelCreate,
    RobotModelUpdate,
    RobotModelResponse,
    RobotModelListResponse,
)

router = APIRouter(prefix="/robots", tags=["robots"])


def _require_teacher_or_admin(actor: ActorContext):
    if "teacher" not in actor.roles and "admin" not in actor.roles:
        raise HTTPException(status_code=403, detail="教师或管理员权限才能操作机器人")


@router.post("", response_model=RobotModelResponse, status_code=status.HTTP_201_CREATED)
async def create_robot(
    body: RobotModelCreate,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """创建新机器人型号。"""
    _require_teacher_or_admin(actor)
    robot = RobotModel(
        brand=body.brand,
        model_name=body.model_name,
        version=body.version,
        description=body.description,
        owner_teacher_id=actor.user_id,
        visibility=RobotVisibility.PRIVATE,
        status=RobotStatus.DRAFT,
    )
    db.add(robot)
    await db.flush()

    binding = TeacherRobotBinding(
        teacher_id=actor.user_id,
        robot_model_id=robot.id,
        binding_type="owner",
    )
    db.add(binding)
    await db.commit()
    await db.refresh(robot)
    return robot


@router.get("", response_model=RobotModelListResponse)
async def list_robots(
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """列出当前教师名下的机器人（自有 + 引用）。"""
    _require_teacher_or_admin(actor)
    stmt = (
        select(RobotModel)
        .join(TeacherRobotBinding, TeacherRobotBinding.robot_model_id == RobotModel.id)
        .where(TeacherRobotBinding.teacher_id == actor.user_id)
    )
    result = await db.execute(stmt)
    items = list(result.scalars().all())
    return RobotModelListResponse(items=items, total=len(items))


@router.get("/{robot_id}", response_model=RobotModelResponse)
async def get_robot(
    robot_id: int,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """获取机器人详情。"""
    result = await db.execute(select(RobotModel).where(RobotModel.id == robot_id))
    robot = result.scalar_one_or_none()
    if not robot:
        raise HTTPException(status_code=404, detail="机器人不存在")
    return robot


@router.put("/{robot_id}", response_model=RobotModelResponse)
async def update_robot(
    robot_id: int,
    body: RobotModelUpdate,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """更新机器人信息（仅 owner）。"""
    _require_teacher_or_admin(actor)
    result = await db.execute(select(RobotModel).where(RobotModel.id == robot_id))
    robot = result.scalar_one_or_none()
    if not robot:
        raise HTTPException(status_code=404, detail="机器人不存在")
    if robot.owner_teacher_id != actor.user_id and "admin" not in actor.roles:
        raise HTTPException(status_code=403, detail="只有创建者或管理员可以编辑")
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(robot, key, value)
    await db.commit()
    await db.refresh(robot)
    return robot


@router.delete("/{robot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_robot(
    robot_id: int,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """删除机器人（仅 owner）。"""
    _require_teacher_or_admin(actor)
    result = await db.execute(select(RobotModel).where(RobotModel.id == robot_id))
    robot = result.scalar_one_or_none()
    if not robot:
        raise HTTPException(status_code=404, detail="机器人不存在")
    if robot.owner_teacher_id != actor.user_id and "admin" not in actor.roles:
        raise HTTPException(status_code=403, detail="只有创建者或管理员可以删除")
    await db.delete(robot)
    await db.commit()
