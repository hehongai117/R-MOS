"""教师 Onboarding 端点。"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.robot_model import RobotModel, RobotStatus, TeacherRobotBinding
from app.models.user import User
from app.services.authz_guard import ActorContext, get_current_actor

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


class RobotSelectionRequest(BaseModel):
    robot_ids: list[int] = Field(..., min_length=1, max_length=5, description="机器人ID列表，1~5个")


@router.get("/robots")
async def list_available_robots(
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """获取可选机器人列表（教师 onboarding 用）。"""
    if "teacher" not in actor.roles:
        raise HTTPException(status_code=403, detail="仅教师可访问")

    stmt = select(RobotModel).where(RobotModel.status == RobotStatus.READY)
    result = await db.execute(stmt)
    robots = result.scalars().all()

    return {
        "items": [
            {
                "id": r.id,
                "brand": r.brand,
                "model_name": r.model_name,
                "description": r.description,
                "thumbnail_path": r.thumbnail_path,
            }
            for r in robots
        ]
    }


@router.post("/robots")
async def select_robots(
    payload: RobotSelectionRequest,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """教师完成机器人选择（onboarding 最后一步）。"""
    if "teacher" not in actor.roles:
        raise HTTPException(status_code=403, detail="仅教师可访问")

    # 检查是否已完成 onboarding
    user_result = await db.execute(select(User).where(User.id == actor.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.onboarding_completed:
        raise HTTPException(status_code=400, detail="已完成机器人选择，无需重复操作")

    # 校验所有 robot_id 存在且状态为 ready
    for rid in payload.robot_ids:
        robot = (
            await db.execute(
                select(RobotModel).where(RobotModel.id == rid, RobotModel.status == RobotStatus.READY)
            )
        ).scalar_one_or_none()
        if not robot:
            raise HTTPException(status_code=400, detail=f"机器人 ID={rid} 不存在或不可用")

    # 批量创建绑定
    for rid in payload.robot_ids:
        existing = (
            await db.execute(
                select(TeacherRobotBinding).where(
                    TeacherRobotBinding.teacher_id == actor.user_id,
                    TeacherRobotBinding.robot_model_id == rid,
                )
            )
        ).scalar_one_or_none()
        if not existing:
            db.add(TeacherRobotBinding(teacher_id=actor.user_id, robot_model_id=rid))

    # 更新 onboarding 状态
    user.onboarding_completed = True
    await db.commit()

    return {"message": "机器人选择完成", "bound_count": len(payload.robot_ids)}
