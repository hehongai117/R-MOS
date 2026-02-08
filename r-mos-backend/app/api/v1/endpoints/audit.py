"""
审计查询 API（Gate-1 / C-002、C-003）。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import RoleRequiredError
from app.models.audit_event import AuditEvent
from app.services.access_control import log_allow_event, log_deny_event
from app.services.authz_guard import ActorContext, require_permission


router = APIRouter()


def _serialize_event(event: AuditEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "action": event.action,
        "decision": event.decision,
        "actor_user_id": event.actor_user_id,
        "resource_type": event.resource_type,
        "resource_id": event.resource_id,
        "reason": event.reason,
        "trace_id": event.trace_id,
        "skill_id": event.skill_id,
        "skill_version": event.skill_version,
        "tool_call_args": event.tool_call_args,
        "side_effects_applied": event.side_effects_applied,
        "approval_id": event.approval_id,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


@router.get("/audit/events")
async def list_audit_events(
    request: Request,
    trace_id: str | None = Query(default=None),
    actor_user_id: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    decision: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    resource_id: str | None = Query(default=None),
    approval_id: int | None = Query(default=None, ge=1),
    skill_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(require_permission("audit_events:read")),
):
    allowed_roles = {"admin", "auditor"}
    if not (actor.roles & allowed_roles):
        reason = "missing_role:admin_or_auditor"
        await log_deny_event(
            db,
            request,
            action="permission_denied",
            resource_type="Route",
            resource_id=request.url.path,
            reason=reason,
            actor_user_id=str(actor.user_id),
        )
        raise RoleRequiredError(
            action="permission_denied",
            resource_type="Route",
            resource_id=request.url.path,
            reason=reason,
            message="仅管理员或审计员可查询审计事件",
        )

    conditions = []
    if trace_id:
        conditions.append(AuditEvent.trace_id == trace_id)
    actor_filter_user_id = actor_user_id or user_id
    if actor_filter_user_id:
        conditions.append(AuditEvent.actor_user_id == actor_filter_user_id)
    if action:
        conditions.append(AuditEvent.action == action)
    if decision:
        conditions.append(AuditEvent.decision == decision)
    if resource_type:
        conditions.append(AuditEvent.resource_type == resource_type)
    if resource_id:
        conditions.append(AuditEvent.resource_id == resource_id)
    if approval_id is not None:
        conditions.append(AuditEvent.approval_id == approval_id)
    if skill_id:
        conditions.append(AuditEvent.skill_id == skill_id)

    items_stmt = select(AuditEvent)
    count_stmt = select(func.count()).select_from(AuditEvent)
    if conditions:
        items_stmt = items_stmt.where(*conditions)
        count_stmt = count_stmt.where(*conditions)

    items_stmt = (
        items_stmt.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(items_stmt)
    events = result.scalars().all()

    count_result = await db.execute(count_stmt)
    total_count = int(count_result.scalar_one() or 0)

    await log_allow_event(
        db,
        request,
        action="audit_query",
        actor_user_id=str(actor.user_id),
        resource_type="AuditEvent",
        resource_id="*",
        reason="query_success",
        request_meta={
            "method": request.method,
            "path": request.url.path,
            "query": request.url.query,
            "trace_id": getattr(request.state, "trace_id", None),
        },
    )

    return {
        "items": [_serialize_event(event) for event in events],
        "limit": limit,
        "offset": offset,
        "count": total_count,
    }
