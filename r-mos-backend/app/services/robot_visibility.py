"""机器人读取可见性的共享判定。"""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.robot_model import RobotModel, RobotVisibility, TeacherRobotBinding
from app.services.authz_guard import ActorContext, actor_has_role


async def get_visible_robot_or_404(
    db: AsyncSession, robot_id: int, actor: ActorContext
) -> RobotModel:
    """按可见性/绑定规则取机器人；不存在或无权一律 404（AUTH-103）。

    越权读对外返回 404 而不是 403：403 会泄漏“这台机器人存在”。
    见验收章程 G1 与单校五机验收矩阵对 AUTH-103 的复验口径。

    可见性只有 PRIVATE / SHARED 两档（app/models/robot_model.py:8-11），
    没有面向匿名的公开档——SHARED 表示对已认证用户可见，
    因此资产不存在合法的匿名读取场景。
    """
    result = await db.execute(select(RobotModel).where(RobotModel.id == robot_id))
    robot = result.scalar_one_or_none()
    if robot is None:
        raise HTTPException(status_code=404, detail="机器人不存在")

    if actor_has_role(actor, "admin") or actor.account_role == "admin":
        return robot
    if robot.visibility == RobotVisibility.SHARED:
        return robot
    if robot.owner_teacher_id == actor.user_id:
        return robot

    binding_result = await db.execute(
        select(TeacherRobotBinding).where(
            TeacherRobotBinding.teacher_id == actor.user_id,
            TeacherRobotBinding.robot_model_id == robot_id,
        )
    )
    if binding_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="机器人不存在")
    return robot
