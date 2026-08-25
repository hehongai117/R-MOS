"""
统一访问拒绝语义与审计收敛。

约束：
- READ 越权：抛出 ReadAccessDeniedError（404）
- WRITE 越权：抛出 WriteAccessDeniedError（403）
- 抛错前统一写入 audit_events，确保记录真实 resource_id
"""
from __future__ import annotations

from typing import Any, NoReturn, Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ReadAccessDeniedError, WriteAccessDeniedError
from app.services.audit_event_service import AuditEventService


def _extract_actor_user_id(request: Request) -> Optional[str]:
    """审计操作者只取服务端已验证的令牌主体（AUTH-104）。

    改造前这里从客户端 `X-User-ID` 头兜底，任何调用者都能污染审计中的操作者身份。
    现在只读 `request.state.actor`——它由 `get_current_actor` 在认证成功后写入。
    取不到就返回 None（表示当时没有已认证主体），**不得**回落到客户端头。
    """
    actor = getattr(request.state, "actor", None)
    if actor is None:
        return None
    return str(actor.user_id)


def _build_request_meta(request: Request) -> dict[str, Any]:
    trace_id = getattr(request.state, "trace_id", None)
    return {
        "method": request.method,
        "path": request.url.path,
        "query": request.url.query,
        "trace_id": trace_id,
    }


async def log_deny_event(
    db: AsyncSession,
    request: Request,
    *,
    action: str,
    resource_type: str,
    resource_id: Any,
    reason: str,
    actor_user_id: Optional[str] = None,
    skill_id: Optional[str] = None,
    skill_version: Optional[str] = None,
    tool_call_args: Optional[dict[str, Any]] = None,
    side_effects_applied: Optional[list[str]] = None,
    approval_id: Optional[int] = None,
) -> None:
    service = AuditEventService(db)
    await service.log_event(
        action=action,
        decision="deny",
        actor_user_id=actor_user_id if actor_user_id is not None else _extract_actor_user_id(request),
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        reason=reason,
        request_meta=_build_request_meta(request),
        trace_id=getattr(request.state, "trace_id", None),
        skill_id=skill_id,
        skill_version=skill_version,
        tool_call_args=tool_call_args,
        side_effects_applied=side_effects_applied,
        approval_id=approval_id,
    )


async def log_allow_event(
    db: AsyncSession,
    request: Request,
    *,
    action: str,
    resource_type: str,
    resource_id: Any,
    reason: str,
    actor_user_id: Optional[str] = None,
    request_meta: Optional[dict[str, Any]] = None,
    skill_id: Optional[str] = None,
    skill_version: Optional[str] = None,
    tool_call_args: Optional[dict[str, Any]] = None,
    side_effects_applied: Optional[list[str]] = None,
    approval_id: Optional[int] = None,
) -> None:
    service = AuditEventService(db)
    await service.log_event(
        action=action,
        decision="allow",
        actor_user_id=actor_user_id if actor_user_id is not None else _extract_actor_user_id(request),
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        reason=reason,
        request_meta=request_meta if request_meta is not None else _build_request_meta(request),
        trace_id=getattr(request.state, "trace_id", None),
        skill_id=skill_id,
        skill_version=skill_version,
        tool_call_args=tool_call_args,
        side_effects_applied=side_effects_applied,
        approval_id=approval_id,
    )


async def raise_read_access_denied(
    db: AsyncSession,
    request: Request,
    *,
    action: str,
    resource_type: str,
    resource_id: Any,
    reason: str,
    message: str = "资源不存在",
) -> NoReturn:
    await log_deny_event(
        db,
        request,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        reason=reason,
    )
    raise ReadAccessDeniedError(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        reason=reason,
        message=message,
    )


async def raise_write_access_denied(
    db: AsyncSession,
    request: Request,
    *,
    action: str,
    resource_type: str,
    resource_id: Any,
    reason: str,
    message: str = "权限不足",
) -> NoReturn:
    await log_deny_event(
        db,
        request,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        reason=reason,
    )
    raise WriteAccessDeniedError(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        reason=reason,
        message=message,
    )
