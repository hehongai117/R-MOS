"""Gate-2 F-001：Approval Service 最小审批接口。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ResourceNotFoundError, RoleRequiredError
from app.services.access_control import log_allow_event, log_deny_event
from app.services.approval_service import ApprovalService
from app.services.authz_guard import ActorContext, require_permission


router = APIRouter()


class ApprovalDecisionRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=256)


def _ensure_admin_or_auditor(actor: ActorContext) -> bool:
    return bool({"admin", "auditor"}.intersection(actor.roles))


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
    )

    return {
        "approval_id": approval.id,
        "trace_id": approval.trace_id,
        "status": approval.status,
        "changed": result.changed,
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
    )

    return {
        "approval_id": approval.id,
        "trace_id": approval.trace_id,
        "status": approval.status,
        "changed": result.changed,
    }
