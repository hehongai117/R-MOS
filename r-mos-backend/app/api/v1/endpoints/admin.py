"""
Admin 端最小 RBAC 路由（Gate-1 / B-001）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.services.authz_guard import ActorContext, require_permission


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
            }
            for user in users
        ],
        "total": len(users),
    }
