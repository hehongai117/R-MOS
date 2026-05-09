"""学生相关 API 端点。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.robot_model import RobotModel, RobotStatus, TeacherRobotBinding
from app.models.user import User
from app.schemas.robot_model import RobotModelListResponse
from app.services.authz_guard import ActorContext, get_current_actor

router = APIRouter(prefix="/students", tags=["students"])


@router.get("/{student_id}/robots", response_model=RobotModelListResponse)
async def list_student_robots(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """学生查看绑定教师名下已发布(READY)的机器人列表。"""
    # 权限检查：只能查自己的，教师/管理员可查任意学生
    if "admin" not in actor.roles and "teacher" not in actor.roles:
        if actor.user_id != student_id:
            raise HTTPException(status_code=403, detail="只能查看自己的机器人列表")

    student_result = await db.execute(select(User).where(User.id == student_id))
    student = student_result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    if not student.teacher_id:
        return RobotModelListResponse(items=[], total=0)

    stmt = (
        select(RobotModel)
        .join(TeacherRobotBinding, TeacherRobotBinding.robot_model_id == RobotModel.id)
        .where(
            TeacherRobotBinding.teacher_id == student.teacher_id,
            RobotModel.status == RobotStatus.READY,
        )
    )
    result = await db.execute(stmt)
    items = list(result.scalars().all())
    return RobotModelListResponse(items=items, total=len(items))
