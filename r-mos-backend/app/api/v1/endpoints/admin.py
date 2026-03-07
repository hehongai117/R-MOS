"""
Admin 端最小 RBAC 路由（Gate-1 / B-001）。
V0.2 UF-01-b: 新增角色管理接口
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.services.authz_guard import ActorContext, require_permission
from app.models.audit_event import AuditEvent
from app.models.event import EventType


router = APIRouter()


@router.get("/admin/users")
async def list_users(
    limit: int = Query(default=100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _actor: ActorContext = Depends(
        require_permission("users:read", required_role="admin")
    ),
):
    result = await db.execute(
        select(User).order_by(User.id.asc()).limit(limit)
    )
    users = result.scalars().all()
    return {
        "items": [
            {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "role": getattr(user, 'role', 'student'),
            }
            for user in users
        ],
        "total": len(users),
    }


# ============ UF-01-b: Role Management ============

class UpdateRoleRequest(BaseModel):
    """更新用户角色请求"""
    role: str = Field(..., description="角色: student | teacher | admin")


@router.post("/admin/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    request: UpdateRoleRequest,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(require_permission("users:write", required_role="admin")),
):
    """UF-01-b-1: 更新用户角色，仅 admin 可调用"""
    # Validate role
    valid_roles = ["student", "teacher", "admin"]
    if request.role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {valid_roles}"
        )

    # Get user
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    old_role = getattr(user, 'role', 'student')
    user.role = request.role

    # Write audit event
    audit = AuditEvent(
        event_type=EventType.ROLE_CHANGE,
        user_id=actor.user.id,
        details={
            "target_user_id": user_id,
            "old_role": old_role,
            "new_role": request.role,
        },
    )
    db.add(audit)

    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "message": f"Role updated from '{old_role}' to '{request.role}'"
    }


# ============ UF-01-b: Class Management ============

class CreateClassRequest(BaseModel):
    """创建班级请求"""
    name: str = Field(..., min_length=1, max_length=100)
    term: Optional[str] = None


class AddMembersRequest(BaseModel):
    """添加班级成员请求"""
    student_ids: list[int] = Field(..., description="学生ID列表")
