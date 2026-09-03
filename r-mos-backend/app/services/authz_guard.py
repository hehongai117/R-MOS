"""
RBAC 路由守卫（Gate-1 / B-001）。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import (
    AccessDeniedError,
    AuthenticationRequiredError,
    PermissionDeniedError,
    RoleRequiredError,
)
from app.core.public_routes import PUBLIC_ROUTES
from app.core.security import hash_token
from app.models.access_token import AccessToken
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User
from app.services.access_control import log_deny_event


@dataclass
class ActorContext:
    """守卫解析后的最小用户上下文。

    ⚠️ 系统里存在**两套角色**，本类分别承载，不要混用：

    - `roles` / `permissions`：RBAC 表（`roles` / `user_roles` / `permissions`）里的
      细粒度授权。注意注册流程**不写** `user_roles`，只有 seed 脚本会写，
      因此正常注册的用户这两个集合为空。
    - `account_role`：`users.role` 列上的粗粒度账号角色（`student` / `teacher` /
      `admin`），注册时写入。教学域的角色分支用它——它正是改造前
      `X-RMOS-Role` 头所携带的那个值，只是现在来自服务端令牌而非客户端。

    `school_name` 用于跨校归属校验（决策 K）。当前全仓只有 `users` 表带学校维度，
    因此跨校比较通过"操作者 user → school_name"进行，不做数据分库。
    """

    user_id: int
    email: str
    roles: set[str]
    permissions: set[str]
    account_role: str = ""
    school_name: str | None = None


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
    request: Request,
    db: AsyncSession = Depends(get_db),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> ActorContext:
    """从 Access Token 持久化表解析当前用户与权限上下文。

    结果缓存在 `request.state.actor`：默认拒绝网关（`enforce_authenticated`）
    与端点自身的 `Depends(get_current_actor)` 会在同一个请求里各要一次上下文，
    缓存后整个请求只查一次库。
    """
    cached = getattr(request.state, "actor", None)
    if cached is not None:
        return cached

    token = _parse_bearer_token(authorization)
    if token is None:
        raise AuthenticationRequiredError("未登录，请先登录后重试")

    now = datetime.now(timezone.utc)
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

    actor = ActorContext(
        user_id=user.id,
        email=user.email,
        roles=roles,
        permissions=permissions,
        # 两者都来自上面已经查过的 User 行，不产生额外查询
        account_role=(user.role or "").strip().lower(),
        school_name=user.school_name,
    )
    request.state.actor = actor
    return actor


def resolve_actor_identity(
    actor: ActorContext,
    claimed: Any = None,
    *,
    action: str,
    resource_type: str,
    resource_id: Any = None,
) -> int:
    """返回**认证上下文**中的用户编号，作为写入业务记录的唯一操作人身份。

    审计 M-02：系统曾在多处把请求体自带的 `user_id` / `teacher_id` 当作操作人写库，
    甚至用它做管辖权判定。任何「是否存在身份检查」的静态扫描对这类写法都会打勾，
    因此必须把「业务身份取自何处」这条规则收口到一个地方。

    Args:
        actor: 认证守卫解析出的调用者上下文。
        claimed: 请求体声明的身份（若接口为兼容保留该字段）。
            **不为 None 且与认证身份不一致时视为冒用，直接拒绝**，
            而不是静默改用认证身份——静默改用会让冒用尝试不可见。

    Returns:
        `actor.user_id`，始终是认证身份。
    """
    if claimed is not None and str(claimed) != str(actor.user_id):
        raise AccessDeniedError(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            reason="identity_mismatch_between_token_and_body",
            message="请求体声明的身份与认证身份不一致",
        )
    return actor.user_id


async def enforce_authenticated(
    request: Request,
    db: AsyncSession = Depends(get_db),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    """默认拒绝网关（AUTH-101 / AUTH-102）。

    挂在 `main.py` 的 `include_router(api_router, prefix="/api/v1", ...)` 上，
    对 `/api/v1` 下**每一条**路由生效。因此某个端点函数是否声明
    `Depends(get_current_actor)` 不再决定它是否受保护——漏加认证也拦得住。

    只有登记在 `app.core.public_routes.PUBLIC_ROUTES` 的
    (方法, 路由模板) 组合可以匿名通过。

    按**路由模板**匹配而不是具体请求路径，这样 `/schools/{school_name}/teachers`
    这类带参数的公开路由才能正确豁免。
    """
    route = request.scope.get("route")
    route_path = getattr(route, "path", None) or request.url.path
    if (request.method.upper(), route_path) in PUBLIC_ROUTES:
        return

    # 复用同一份解析逻辑；结果写入 request.state.actor，端点侧不会重复查库。
    await get_current_actor(request=request, db=db, authorization=authorization)


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
