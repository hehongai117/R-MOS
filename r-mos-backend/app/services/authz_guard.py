"""
RBAC 路由守卫（Gate-1 / B-001）。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import (
    AuthenticationRequiredError,
    PermissionDeniedError,
    RoleRequiredError,
)
from app.core.security import hash_token
from app.models.access_token import AccessToken
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User
from app.services.access_control import log_deny_event


@dataclass
class ActorContext:
    """守卫解析后的最小用户上下文。"""

    user_id: int
    email: str
    roles: set[str]
    permissions: set[str]


def _parse_bearer_token(authorization: str | None) -> str | None:
    if authorization is None:
        return None
    value = authorization.strip()
    if not value:
        return None
    parts = value.split(" ", 1)
    if len(parts) != 2:
        return None
    if parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


async def get_current_actor(
    db: AsyncSession = Depends(get_db),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> ActorContext:
    """从 Access Token 持久化表解析当前用户与权限上下文。"""
    token = _parse_bearer_token(authorization)
    if token is None:
        raise AuthenticationRequiredError("未登录，请先登录后重试")

    now = datetime.utcnow()
    token_hash = hash_token(token)
    access_token_result = await db.execute(
        select(AccessToken).where(AccessToken.access_token_hash == token_hash)
    )
    access_token = access_token_result.scalar_one_or_none()
    if (
        access_token is None
        or access_token.is_revoked
        or access_token.revoked_at is not None
        or access_token.expires_at <= now
    ):
        raise AuthenticationRequiredError("登录态已失效，请重新登录")

    user_result = await db.execute(
        select(User).where(User.id == access_token.user_id)
    )
    user = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise AuthenticationRequiredError("用户不可用，请联系管理员")

    role_rows = await db.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
    )
    roles = {row[0] for row in role_rows.all()}

    permission_rows = await db.execute(
        select(Permission.key)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user.id)
    )
    permissions = {row[0] for row in permission_rows.all()}

    return ActorContext(
        user_id=user.id,
        email=user.email,
        roles=roles,
        permissions=permissions,
    )


def require_permission(permission_key: str, *, required_role: str | None = None) -> Callable:
    """
    路由级权限守卫。

    - 优先校验角色（AUTHZ_002）
    - 再校验权限键（AUTHZ_001）
    """

    async def _dependency(
        request: Request,
        db: AsyncSession = Depends(get_db),
        actor: ActorContext = Depends(get_current_actor),
    ) -> ActorContext:
        route_path = request.url.path
        if required_role and required_role not in actor.roles:
            reason = f"missing_role:{required_role}"
            await log_deny_event(
                db,
                request,
                action="permission_denied",
                resource_type="Route",
                resource_id=route_path,
                reason=reason,
                actor_user_id=str(actor.user_id),
            )
            raise RoleRequiredError(
                action="permission_denied",
                resource_type="Route",
                resource_id=route_path,
                reason=reason,
                message="缺少必需角色",
            )

        if permission_key not in actor.permissions:
            reason = f"missing_permission:{permission_key}"
            await log_deny_event(
                db,
                request,
                action="permission_denied",
                resource_type="Route",
                resource_id=route_path,
                reason=reason,
                actor_user_id=str(actor.user_id),
            )
            raise PermissionDeniedError(
                action="permission_denied",
                resource_type="Route",
                resource_id=route_path,
                reason=reason,
                message="权限不足",
            )

        return actor

    return _dependency
