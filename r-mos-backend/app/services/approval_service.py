"""Gate-2 F-001：审批状态迁移服务。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolation
from app.models.approval import Approval


@dataclass
class ApprovalTransitionResult:
    approval: Approval
    changed: bool
    reason: str


class ApprovalService:
    """封装审批 grant/reject 的最小幂等逻辑。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, approval_id: int) -> Approval | None:
        result = await self.db.execute(select(Approval).where(Approval.id == approval_id))
        return result.scalar_one_or_none()

    async def grant(
        self,
        approval: Approval,
        *,
        decided_by_user_id: int,
        reason: str | None,
    ) -> ApprovalTransitionResult:
        return await self._transition(
            approval,
            target_status="granted",
            decided_by_user_id=decided_by_user_id,
            reason=reason or "approval_granted",
        )

    async def reject(
        self,
        approval: Approval,
        *,
        decided_by_user_id: int,
        reason: str | None,
    ) -> ApprovalTransitionResult:
        return await self._transition(
            approval,
            target_status="rejected",
            decided_by_user_id=decided_by_user_id,
            reason=reason or "approval_rejected",
        )

    async def _transition(
        self,
        approval: Approval,
        *,
        target_status: str,
        decided_by_user_id: int,
        reason: str,
    ) -> ApprovalTransitionResult:
        current_status = approval.status
        if current_status == target_status:
            return ApprovalTransitionResult(
                approval=approval,
                changed=False,
                reason=f"idempotent_already_{target_status}",
            )

        if current_status != "pending":
            raise BusinessRuleViolation(
                message="审批状态不允许变更",
                code="APPROVAL_STATE_INVALID",
                details={
                    "approval_id": approval.id,
                    "current_status": current_status,
                    "target_status": target_status,
                },
            )

        approval.status = target_status
        approval.reason = reason
        approval.decided_by_user_id = str(decided_by_user_id)
        approval.decided_at = datetime.utcnow()
        approval.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(approval)
        return ApprovalTransitionResult(approval=approval, changed=True, reason=reason)
