"""机器人读取可见性的共享判定。"""
from fastapi import HTTPException
from sqlalchemy import and_, exists, false, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.robot_model import RobotModel, RobotVisibility, TeacherRobotBinding
from app.models.user import User
from app.services.authz_guard import ActorContext, actor_has_role


def visible_robot_filter(actor: ActorContext):
    """返回与单对象读取完全一致的机器人可见性过滤条件。"""
    if actor_has_role(actor, "admin"):
        return true()

    same_school_owner = false()
    if actor.school_name is not None:
        same_school_owner = RobotModel.owner_teacher_id.in_(
            select(User.id).where(User.school_name == actor.school_name)
        )

    binding = aliased(TeacherRobotBinding)
    has_binding = exists(
        select(binding.id).where(
            binding.teacher_id == actor.user_id,
            binding.robot_model_id == RobotModel.id,
        )
    ).correlate(RobotModel)
    return or_(
        RobotModel.owner_teacher_id == actor.user_id,
        and_(
            RobotModel.owner_teacher_id.is_(None),
            RobotModel.visibility == RobotVisibility.SHARED,
        ),
        and_(
            same_school_owner,
            or_(RobotModel.visibility == RobotVisibility.SHARED, has_binding),
        ),
    )


async def get_visible_robot_or_404(
    db: AsyncSession,
    robot_id: int,
    actor: ActorContext,
) -> RobotModel:
    """按可见性/绑定规则取机器人；不存在或无权一律 404（AUTH-103）。

    越权读对外返回 404 而不是 403：403 会泄漏“这台机器人存在”。
    见验收章程 G1 与单校五机验收矩阵对 AUTH-103 的复验口径。

    SHARED 对同校已认证用户可见；owner 为空的系统内置 SHARED 机器人仍面向
    全平台已认证用户。学校是租户边界，绑定关系不能穿透该边界。
    """
    result = await db.execute(
        select(RobotModel).where(
            RobotModel.id == robot_id,
            visible_robot_filter(actor),
        )
    )
    robot = result.scalar_one_or_none()
    if robot is not None:
        return robot

    exists_result = await db.execute(
        select(RobotModel.id).where(RobotModel.id == robot_id)
    )
    if exists_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="机器人不存在")

    raise HTTPException(status_code=404, detail="机器人不存在")
