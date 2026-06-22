"""Gate-2 F-001：审批状态迁移服务。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolation
from app.models.approval import Approval
from app.models.command_runtime import AIToolCall, Command
from app.services.tool_executor import execute_write_tool_stub


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

    async def get_runtime_bundle(self, approval: Approval) -> tuple[Command, AIToolCall]:
        command_result = await self.db.execute(
            select(Command).where(Command.id == approval.command_id)
        )
        command = command_result.scalar_one_or_none()

        tool_call_result = await self.db.execute(
            select(AIToolCall).where(AIToolCall.id == approval.tool_call_id)
        )
        tool_call = tool_call_result.scalar_one_or_none()

        if command is None or tool_call is None:
            raise BusinessRuleViolation(
                message="审批关联的命令或工具调用不存在",
                code="APPROVAL_RUNTIME_MISSING",
                details={
                    "approval_id": approval.id,
                    "command_id": approval.command_id,
                    "tool_call_id": approval.tool_call_id,
                },
            )
        return command, tool_call

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
        approval.decided_at = datetime.now(timezone.utc)
        approval.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(approval)
        return ApprovalTransitionResult(approval=approval, changed=True, reason=reason)

    async def execute_after_grant(self, approval: Approval) -> tuple[Command, AIToolCall, bool]:
        command, tool_call = await self.get_runtime_bundle(approval)

        if tool_call.status == "success" and command.status == "succeeded":
            return command, tool_call, False
        if tool_call.status == "failed" and command.status == "failed":
            return command, tool_call, False

        try:
            result_payload = execute_write_tool_stub(
                intent=command.intent,
                tool_name=tool_call.tool_name,
                skill_id=tool_call.skill_id,
                side_effects=tool_call.side_effects or [],
            )
            tool_call.status = "success"
            tool_call.result_payload = result_payload
            tool_call.error_message = None
            command.status = "succeeded"
        except Exception as exc:
            error_code = getattr(exc, "code", None) or "write_tool_execution_failed"
            error_message = str(exc) or "write_tool_execution_failed"
            tool_call.status = "failed"
            tool_call.error_message = error_code
            tool_call.result_payload = {
                "mode": "write_stub_failed",
                "error_code": error_code,
                "error_message": error_message,
                "rollback_instructions": [
                    {
                        "type": "manual_review",
                        "reason": error_code,
                    }
                ],
            }
            command.status = "failed"

        command.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(command)
        await self.db.refresh(tool_call)
        return command, tool_call, True

    async def fail_after_reject(self, approval: Approval) -> tuple[Command, AIToolCall, bool]:
        command, tool_call = await self.get_runtime_bundle(approval)

        if tool_call.status in {"failed", "rejected"} and command.status == "failed":
            return command, tool_call, False

        tool_call.status = "failed"
        tool_call.error_message = "approval_rejected"
        command.status = "failed"
        command.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(command)
        await self.db.refresh(tool_call)
        return command, tool_call, True
