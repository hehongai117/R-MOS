"""Gate-2 E-001：AI Command 最小读链路入口。"""
from __future__ import annotations

from dataclasses import dataclass
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import SecurityViolationError
from app.core.database import get_db
from app.models.approval import Approval
from app.models.command_runtime import AIToolCall, Command
from app.services.access_control import log_allow_event, log_deny_event
from app.services.authz_guard import ActorContext, get_current_actor
from app.services.tool_executor import (
    build_insufficient_data_template,
    execute_read_tool,
    validate_tool_request_security,
)


router = APIRouter()


class CommandCreateRequest(BaseModel):
    intent: str = Field(min_length=1, max_length=128)
    input_text: str | None = Field(default=None, max_length=2048)
    skill_id: str | None = Field(default=None, max_length=128)
    tool_name: str | None = Field(default=None, min_length=1, max_length=128)
    tool_args: dict[str, Any] = Field(default_factory=dict)
    side_effects: list[str] = Field(default_factory=list)
    approval_id: int | None = None


@dataclass
class PlannedToolCall:
    tool_name: str
    skill_id: str | None
    tool_args: dict[str, Any]
    side_effects: list[str]
    via_planner: bool


def _plan_tool_call(payload: CommandCreateRequest) -> PlannedToolCall:
    """G-003 最小规划器：在 dispatch 场景补齐 Tool Plan。"""
    if payload.tool_name:
        return PlannedToolCall(
            tool_name=payload.tool_name,
            skill_id=payload.skill_id,
            tool_args=dict(payload.tool_args),
            side_effects=list(payload.side_effects),
            via_planner=False,
        )

    normalized_intent = payload.intent.strip().lower()
    if normalized_intent != "dispatch":
        raise HTTPException(status_code=422, detail="缺少 tool_name，且当前意图未命中最小规划器")

    input_text = str(payload.input_text or "").strip()
    if not input_text:
        raise HTTPException(status_code=422, detail="dispatch 意图缺少 input_text")

    planned_args = dict(payload.tool_args)
    planned_args.setdefault("input_text", input_text)
    planned_args.setdefault("dispatch_mode", "draft_only")

    return PlannedToolCall(
        tool_name="assignments.create_draft",
        skill_id=payload.skill_id or "teaching.dispatch.draft",
        tool_args=planned_args,
        side_effects=list(payload.side_effects or ["assignments.write"]),
        via_planner=True,
    )


@router.post("/ai/commands", status_code=201)
async def create_ai_command(
    payload: CommandCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    trace_id = getattr(request.state, "trace_id", None) or str(uuid.uuid4())[:8]
    request.state.trace_id = trace_id
    planned_tool = _plan_tool_call(payload)

    try:
        validate_tool_request_security(
            tool_name=planned_tool.tool_name,
            tool_args=planned_tool.tool_args,
        )
    except SecurityViolationError as exc:
        await log_deny_event(
            db,
            request,
            action="tool_call_failed",
            resource_type="Skill",
            resource_id=planned_tool.skill_id or planned_tool.tool_name,
            reason=exc.code,
            actor_user_id=str(actor.user_id),
            skill_id=planned_tool.skill_id,
            tool_call_args=planned_tool.tool_args,
            side_effects_applied=list(planned_tool.side_effects),
        )
        raise

    command = Command(
        trace_id=trace_id,
        actor_user_id=str(actor.user_id),
        intent=payload.intent,
        skill_id=planned_tool.skill_id,
        status="created",
        approval_id=None,
    )
    db.add(command)
    await db.commit()
    await db.refresh(command)

    await log_allow_event(
        db,
        request,
        action="command_created",
        actor_user_id=str(actor.user_id),
        resource_type="Command",
        resource_id=command.id,
        reason="command_received",
    )

    if planned_tool.via_planner:
        await log_allow_event(
            db,
            request,
            action="tool_plan_generated",
            actor_user_id=str(actor.user_id),
            resource_type="Command",
            resource_id=command.id,
            reason="dispatch_minimal_planner",
            skill_id=planned_tool.skill_id,
            tool_call_args=planned_tool.tool_args,
            side_effects_applied=list(planned_tool.side_effects),
        )

    tool_call = AIToolCall(
        command_id=command.id,
        trace_id=trace_id,
        actor_user_id=str(actor.user_id),
        skill_id=planned_tool.skill_id,
        tool_name=planned_tool.tool_name,
        side_effects=list(planned_tool.side_effects),
        status="pending",
        approval_id=None,
    )
    db.add(tool_call)
    await db.commit()
    await db.refresh(tool_call)

    await log_allow_event(
        db,
        request,
        action="tool_call_pending",
        actor_user_id=str(actor.user_id),
        resource_type="AIToolCall",
        resource_id=tool_call.id,
        reason="tool_call_created",
        skill_id=planned_tool.skill_id,
        tool_call_args=planned_tool.tool_args,
        side_effects_applied=list(planned_tool.side_effects),
    )

    if planned_tool.side_effects:
        approval = Approval(
            trace_id=trace_id,
            command_id=command.id,
            tool_call_id=tool_call.id,
            status="pending",
            reason="awaiting_approval",
            created_by_user_id=str(actor.user_id),
        )
        db.add(approval)
        await db.commit()
        await db.refresh(approval)

        command.approval_id = approval.id
        tool_call.approval_id = approval.id
        command.status = "waiting_approval" if planned_tool.via_planner else "pending_approval"
        await db.commit()

        await log_allow_event(
            db,
            request,
            action="approval_created",
            actor_user_id=str(actor.user_id),
            resource_type="Approval",
            resource_id=approval.id,
            reason="approval_pending_created",
            skill_id=planned_tool.skill_id,
            tool_call_args=planned_tool.tool_args,
            side_effects_applied=list(planned_tool.side_effects),
            approval_id=approval.id,
        )

        result_payload: dict[str, Any] | None = None
        if planned_tool.via_planner:
            result_payload = {
                "status": "waiting_approval",
                "sop_draft_id": f"sop-draft-{command.id}",
                "task_chain_draft_id": f"task-chain-{command.id}",
                "rubric_draft_id": f"rubric-{command.id}",
                "citations": [
                    {
                        "ref_id": "dispatch-plan-stub",
                        "title": "口述派单最小规划草案",
                    }
                ],
                "tool_plan": {
                    "tool_name": planned_tool.tool_name,
                    "skill_id": planned_tool.skill_id,
                    "side_effects": list(planned_tool.side_effects),
                },
            }

        return {
            "command_id": command.id,
            "tool_call_id": tool_call.id,
            "trace_id": trace_id,
            "status": command.status,
            "approval_id": approval.id,
            "result": result_payload,
        }

    try:
        result_payload = execute_read_tool(
            intent=payload.intent,
            tool_name=planned_tool.tool_name,
            skill_id=planned_tool.skill_id,
            tool_args=planned_tool.tool_args,
        )
        insufficient_template = build_insufficient_data_template(
            intent=payload.intent,
            tool_name=planned_tool.tool_name,
            tool_args=planned_tool.tool_args,
            execution_result=result_payload,
        )
        if insufficient_template is not None:
            result_payload = insufficient_template

        tool_call.status = "success"
        tool_call.result_payload = result_payload
        command.status = "succeeded"
        await db.commit()

        success_reason = (
            "insufficient_data"
            if result_payload.get("status") == "insufficient_data"
            else "read_tool_success"
        )

        await log_allow_event(
            db,
            request,
            action="tool_call_success",
            actor_user_id=str(actor.user_id),
            resource_type="AIToolCall",
            resource_id=tool_call.id,
            reason=success_reason,
            skill_id=planned_tool.skill_id,
            tool_call_args=planned_tool.tool_args,
            side_effects_applied=list(planned_tool.side_effects),
            approval_id=command.approval_id,
        )
        return {
            "command_id": command.id,
            "tool_call_id": tool_call.id,
            "trace_id": trace_id,
            "status": command.status,
            "approval_id": command.approval_id,
            "result": result_payload,
        }
    except Exception as exc:  # pragma: no cover - 保护性分支
        tool_call.status = "failed"
        tool_call.error_message = str(exc)
        command.status = "failed"
        await db.commit()

        await log_deny_event(
            db,
            request,
            action="tool_call_failed",
            resource_type="AIToolCall",
            resource_id=tool_call.id,
            reason=f"read_tool_error:{type(exc).__name__}",
            actor_user_id=str(actor.user_id),
            skill_id=planned_tool.skill_id,
            tool_call_args=planned_tool.tool_args,
            side_effects_applied=list(planned_tool.side_effects),
            approval_id=command.approval_id,
        )
        raise HTTPException(status_code=500, detail="读工具执行失败")
