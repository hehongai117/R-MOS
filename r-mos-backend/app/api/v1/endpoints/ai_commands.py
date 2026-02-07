"""Gate-2 E-001：AI Command 最小读链路入口。"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.approval import Approval
from app.models.command_runtime import AIToolCall, Command
from app.services.access_control import log_allow_event, log_deny_event
from app.services.authz_guard import ActorContext, get_current_actor
from app.services.tool_executor import execute_read_tool


router = APIRouter()


class CommandCreateRequest(BaseModel):
    intent: str = Field(min_length=1, max_length=128)
    skill_id: str | None = Field(default=None, max_length=128)
    tool_name: str = Field(min_length=1, max_length=128)
    tool_args: dict[str, Any] = Field(default_factory=dict)
    side_effects: list[str] = Field(default_factory=list)
    approval_id: int | None = None


@router.post("/ai/commands", status_code=201)
async def create_ai_command(
    payload: CommandCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    trace_id = getattr(request.state, "trace_id", None) or str(uuid.uuid4())[:8]
    request.state.trace_id = trace_id

    command = Command(
        trace_id=trace_id,
        actor_user_id=str(actor.user_id),
        intent=payload.intent,
        skill_id=payload.skill_id,
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

    tool_call = AIToolCall(
        command_id=command.id,
        trace_id=trace_id,
        actor_user_id=str(actor.user_id),
        skill_id=payload.skill_id,
        tool_name=payload.tool_name,
        side_effects=list(payload.side_effects),
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
    )

    if payload.side_effects:
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
        command.status = "pending_approval"
        await db.commit()

        await log_allow_event(
            db,
            request,
            action="approval_created",
            actor_user_id=str(actor.user_id),
            resource_type="Approval",
            resource_id=approval.id,
            reason="approval_pending_created",
        )

        return {
            "command_id": command.id,
            "tool_call_id": tool_call.id,
            "trace_id": trace_id,
            "status": command.status,
            "approval_id": approval.id,
            "result": None,
        }

    try:
        result_payload = execute_read_tool(
            intent=payload.intent,
            tool_name=payload.tool_name,
            skill_id=payload.skill_id,
            tool_args=payload.tool_args,
        )
        tool_call.status = "success"
        tool_call.result_payload = result_payload
        command.status = "succeeded"
        await db.commit()

        await log_allow_event(
            db,
            request,
            action="tool_call_success",
            actor_user_id=str(actor.user_id),
            resource_type="AIToolCall",
            resource_id=tool_call.id,
            reason="read_tool_success",
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
        )
        raise HTTPException(status_code=500, detail="读工具执行失败")
