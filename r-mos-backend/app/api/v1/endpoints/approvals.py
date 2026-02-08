"""Gate-2 F-001：Approval Service 最小审批接口。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ReadAccessDeniedError, ResourceNotFoundError, RoleRequiredError
from app.models.approval import Approval
from app.services.access_control import log_allow_event, log_deny_event
from app.services.approval_service import ApprovalService
from app.services.authz_guard import ActorContext, require_permission


router = APIRouter()


class ApprovalDecisionRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=256)


def _ensure_admin_or_auditor(actor: ActorContext) -> bool:
    return bool({"admin", "auditor"}.intersection(actor.roles))


def _serialize_approval(approval: Approval) -> dict[str, Any]:
    return {
        "id": approval.id,
        "trace_id": approval.trace_id,
        "command_id": approval.command_id,
        "tool_call_id": approval.tool_call_id,
        "status": approval.status,
        "reason": approval.reason,
        "created_by_user_id": approval.created_by_user_id,
        "decided_by_user_id": approval.decided_by_user_id,
        "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
        "created_at": approval.created_at.isoformat() if approval.created_at else None,
        "updated_at": approval.updated_at.isoformat() if approval.updated_at else None,
    }


@router.get("/ai/approvals")
async def list_approvals(
    request: Request,
    trace_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    actor_user_id: str | None = Query(default=None),
    command_id: int | None = Query(default=None, ge=1),
    tool_call_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(require_permission("approvals:read")),
):
    if not _ensure_admin_or_auditor(actor):
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
            message="仅管理员或审计员可查询审批记录",
        )

    conditions = []
    if trace_id:
        conditions.append(Approval.trace_id == trace_id)
    if status:
        conditions.append(Approval.status == status)
    if actor_user_id:
        conditions.append(Approval.created_by_user_id == actor_user_id)
    if command_id is not None:
        conditions.append(Approval.command_id == command_id)
    if tool_call_id is not None:
        conditions.append(Approval.tool_call_id == tool_call_id)

    items_stmt = select(Approval)
    count_stmt = select(func.count()).select_from(Approval)
    if conditions:
        items_stmt = items_stmt.where(*conditions)
        count_stmt = count_stmt.where(*conditions)

    items_stmt = items_stmt.order_by(Approval.id.desc()).offset(offset).limit(limit)
    result = await db.execute(items_stmt)
    items = result.scalars().all()

    count_result = await db.execute(count_stmt)
    total_count = int(count_result.scalar_one() or 0)

    await log_allow_event(
        db,
        request,
        action="approval_query",
        actor_user_id=str(actor.user_id),
        resource_type="Approval",
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
        "items": [_serialize_approval(item) for item in items],
        "limit": limit,
        "offset": offset,
        "count": total_count,
    }


@router.get("/ai/approvals/{id}")
async def get_approval_detail(
    id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(require_permission("approvals:read")),
):
    service = ApprovalService(db)
    approval = await service.get_by_id(id)
    if approval is None:
        raise ResourceNotFoundError("Approval", id)

    request.state.trace_id = approval.trace_id or getattr(request.state, "trace_id", None)
    if not _ensure_admin_or_auditor(actor):
        reason = "missing_role:admin_or_auditor"
        await log_deny_event(
            db,
            request,
            action="permission_denied",
            resource_type="Approval",
            resource_id=id,
            reason=reason,
            actor_user_id=str(actor.user_id),
            approval_id=approval.id,
        )
        raise ReadAccessDeniedError(
            action="permission_denied",
            resource_type="Approval",
            resource_id=id,
            reason=reason,
            message="资源不存在",
        )

    await log_allow_event(
        db,
        request,
        action="approval_read",
        actor_user_id=str(actor.user_id),
        resource_type="Approval",
        resource_id=id,
        reason="read_success",
        approval_id=approval.id,
    )
    return _serialize_approval(approval)


@router.post("/ai/approvals/{id}/grant")
async def grant_approval(
    id: int,
    payload: ApprovalDecisionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(require_permission("approvals:grant")),
):
    if not _ensure_admin_or_auditor(actor):
        reason = "missing_role:admin_or_auditor"
        await log_deny_event(
            db,
            request,
            action="permission_denied",
            resource_type="Approval",
            resource_id=id,
            reason=reason,
            actor_user_id=str(actor.user_id),
        )
        raise RoleRequiredError(
            action="permission_denied",
            resource_type="Approval",
            resource_id=id,
            reason=reason,
            message="仅管理员或审计员可执行审批通过",
        )

    service = ApprovalService(db)
    approval = await service.get_by_id(id)
    if approval is None:
        raise ResourceNotFoundError("Approval", id)
    _, runtime_tool_call = await service.get_runtime_bundle(approval)

    request.state.trace_id = approval.trace_id or getattr(request.state, "trace_id", None)
    result = await service.grant(
        approval,
        decided_by_user_id=actor.user_id,
        reason=payload.reason,
    )
    await log_allow_event(
        db,
        request,
        action="approval_granted",
        actor_user_id=str(actor.user_id),
        resource_type="Approval",
        resource_id=id,
        reason=result.reason,
        skill_id=runtime_tool_call.skill_id,
        side_effects_applied=runtime_tool_call.side_effects or [],
        approval_id=approval.id,
    )

    tool_call_event_written = False
    command, tool_call, runtime_changed = await service.execute_after_grant(approval)
    if runtime_changed:
        tool_call_event_written = True
        if tool_call.status == "success":
            await log_allow_event(
                db,
                request,
                action="tool_call_success",
                actor_user_id=str(actor.user_id),
                resource_type="AIToolCall",
                resource_id=tool_call.id,
                reason="approval_granted_execute_write_stub",
                skill_id=tool_call.skill_id,
                side_effects_applied=tool_call.side_effects or [],
                approval_id=approval.id,
            )
        elif tool_call.status == "failed":
            await log_deny_event(
                db,
                request,
                action="tool_call_failed",
                resource_type="AIToolCall",
                resource_id=tool_call.id,
                reason=tool_call.error_message or "write_tool_execution_failed",
                actor_user_id=str(actor.user_id),
                skill_id=tool_call.skill_id,
                side_effects_applied=tool_call.side_effects or [],
                approval_id=approval.id,
            )
        else:
            await log_deny_event(
                db,
                request,
                action="tool_call_failed",
                resource_type="AIToolCall",
                resource_id=tool_call.id,
                reason=f"unexpected_tool_call_status:{tool_call.status}",
                actor_user_id=str(actor.user_id),
                skill_id=tool_call.skill_id,
                side_effects_applied=tool_call.side_effects or [],
                approval_id=approval.id,
            )

    return {
        "approval_id": approval.id,
        "trace_id": approval.trace_id,
        "status": approval.status,
        "changed": result.changed,
        "command_status": command.status,
        "tool_call_status": tool_call.status,
        "tool_call_event_written": tool_call_event_written,
    }


@router.post("/ai/approvals/{id}/reject")
async def reject_approval(
    id: int,
    payload: ApprovalDecisionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(require_permission("approvals:reject")),
):
    if not _ensure_admin_or_auditor(actor):
        reason = "missing_role:admin_or_auditor"
        await log_deny_event(
            db,
            request,
            action="permission_denied",
            resource_type="Approval",
            resource_id=id,
            reason=reason,
            actor_user_id=str(actor.user_id),
        )
        raise RoleRequiredError(
            action="permission_denied",
            resource_type="Approval",
            resource_id=id,
            reason=reason,
            message="仅管理员或审计员可执行审批拒绝",
        )

    service = ApprovalService(db)
    approval = await service.get_by_id(id)
    if approval is None:
        raise ResourceNotFoundError("Approval", id)
    _, runtime_tool_call = await service.get_runtime_bundle(approval)

    request.state.trace_id = approval.trace_id or getattr(request.state, "trace_id", None)
    result = await service.reject(
        approval,
        decided_by_user_id=actor.user_id,
        reason=payload.reason,
    )
    await log_allow_event(
        db,
        request,
        action="approval_rejected",
        actor_user_id=str(actor.user_id),
        resource_type="Approval",
        resource_id=id,
        reason=result.reason,
        skill_id=runtime_tool_call.skill_id,
        side_effects_applied=runtime_tool_call.side_effects or [],
        approval_id=approval.id,
    )

    tool_call_event_written = False
    command, tool_call, runtime_changed = await service.fail_after_reject(approval)
    if runtime_changed:
        tool_call_event_written = True
        await log_deny_event(
            db,
            request,
            action="tool_call_failed",
            resource_type="AIToolCall",
            resource_id=tool_call.id,
            reason="approval_rejected",
            actor_user_id=str(actor.user_id),
            skill_id=tool_call.skill_id,
            side_effects_applied=tool_call.side_effects or [],
            approval_id=approval.id,
        )

    return {
        "approval_id": approval.id,
        "trace_id": approval.trace_id,
        "status": approval.status,
        "changed": result.changed,
        "command_status": command.status,
        "tool_call_status": tool_call.status,
        "tool_call_event_written": tool_call_event_written,
    }
