"""Gate-2 E-001：AI Command 最小读链路入口。"""
from __future__ import annotations

from dataclasses import dataclass
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ReadAccessDeniedError,
    ResourceNotFoundError,
    SecurityViolationError,
)
from app.core.database import get_db
from app.models.approval import Approval
from app.models.command_runtime import AIToolCall, Command
from app.models.knowledge_chunk import AIKnowledgeChunk
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


class RagQueryRequest(BaseModel):
    input_text: str | None = Field(default=None, max_length=2048)
    skill_id: str | None = Field(default="rag.read.query", max_length=128)
    tool_args: dict[str, Any] = Field(default_factory=dict)


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


def _is_rag_query(tool_name: str) -> bool:
    return tool_name.strip().lower() in {"rag.query", "ai.rag.query"}


async def _filter_rag_citations_by_existing_ref(
    *,
    db: AsyncSession,
    request: Request,
    actor: ActorContext,
    tool_name: str,
    result_payload: dict[str, Any],
) -> dict[str, Any]:
    """H-003 最小闭环：仅返回可见且可验证引用，并记录 deny_count 审计。"""
    if not _is_rag_query(tool_name):
        return result_payload

    normalized_payload = dict(result_payload)
    citations_raw = normalized_payload.get("citations")
    if not isinstance(citations_raw, list):
        citations_raw = []

    if not citations_raw:
        hits = normalized_payload.get("hits")
        if isinstance(hits, list):
            for hit in hits:
                if isinstance(hit, dict) and isinstance(hit.get("ref_id"), str):
                    citations_raw.append(
                        {
                            "ref_id": hit["ref_id"],
                            "title": hit.get("title") or "RAG 命中引用",
                        }
                    )

    ref_ids = []
    for item in citations_raw:
        if isinstance(item, dict) and isinstance(item.get("ref_id"), str):
            ref_ids.append(item["ref_id"])
    if not ref_ids:
        return normalized_payload

    existing_result = await db.execute(
        select(AIKnowledgeChunk).where(AIKnowledgeChunk.id.in_(ref_ids))
    )
    chunks = list(existing_result.scalars().all())
    existing_ref_ids = {chunk.id for chunk in chunks}

    privileged = bool({"admin", "auditor"}.intersection(actor.roles))
    visible_ref_ids: set[str] = set()
    if privileged:
        visible_ref_ids = set(existing_ref_ids)
    else:
        actor_user_id = str(actor.user_id)
        for chunk in chunks:
            owner_user_id = (chunk.owner_user_id or "").strip()
            if not owner_user_id or owner_user_id == actor_user_id:
                visible_ref_ids.add(chunk.id)

    filtered_citations = [
        item
        for item in citations_raw
        if isinstance(item, dict) and item.get("ref_id") in visible_ref_ids
    ]
    filtered_out_count = len(citations_raw) - len(filtered_citations)
    if filtered_out_count > 0:
        await log_deny_event(
            db,
            request,
            action="rag_filter_applied",
            resource_type="AIKnowledgeChunk",
            resource_id="*",
            reason="rag_visibility_filtered",
            actor_user_id=str(actor.user_id),
            request_meta={"deny_count": filtered_out_count},
        )

    normalized_payload["citations"] = filtered_citations

    hits = normalized_payload.get("hits")
    if isinstance(hits, list):
        normalized_payload["hits"] = [
            hit
            for hit in hits
            if not isinstance(hit, dict) or hit.get("ref_id") in visible_ref_ids
        ]

    items = normalized_payload.get("items")
    if isinstance(items, list):
        normalized_payload["items"] = [
            item
            for item in items
            if not isinstance(item, dict) or item.get("ref_id") in visible_ref_ids
        ]

    return normalized_payload


@router.get("/ai/citations/{ref_id}")
async def get_ai_citation(
    ref_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    result = await db.execute(
        select(AIKnowledgeChunk).where(AIKnowledgeChunk.id == ref_id)
    )
    chunk = result.scalar_one_or_none()
    if chunk is None:
        raise ResourceNotFoundError("Citation", ref_id)

    owner_user_id = (chunk.owner_user_id or "").strip()
    privileged = bool({"admin", "auditor"}.intersection(actor.roles))
    if owner_user_id and owner_user_id != str(actor.user_id) and not privileged:
        await log_deny_event(
            db,
            request,
            action="access_denied",
            resource_type="AIKnowledgeChunk",
            resource_id=ref_id,
            reason="citation_scope_mismatch",
            actor_user_id=str(actor.user_id),
        )
        raise ReadAccessDeniedError(
            action="access_denied",
            resource_type="AIKnowledgeChunk",
            resource_id=ref_id,
            reason="citation_scope_mismatch",
            message="资源不存在",
        )

    await log_allow_event(
        db,
        request,
        action="citation_read",
        actor_user_id=str(actor.user_id),
        resource_type="AIKnowledgeChunk",
        resource_id=ref_id,
        reason="read_success",
    )
    return {
        "ref_id": chunk.id,
        "source_type": chunk.source_type,
        "source_id": chunk.source_id,
        "content": chunk.content,
        "owner_user_id": chunk.owner_user_id,
        "course_id": chunk.course_id,
        "attempt_id": chunk.attempt_id,
        "metadata": chunk.metadata_json,
        "created_at": chunk.created_at.isoformat() if chunk.created_at else None,
    }


@router.post("/ai/rag/query")
async def query_ai_rag(
    payload: RagQueryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """H-002 最小闭环：RAG 查询接口（经独立端点）。"""
    trace_id = getattr(request.state, "trace_id", None) or str(uuid.uuid4())[:8]
    request.state.trace_id = trace_id

    tool_args = dict(payload.tool_args)
    if payload.input_text and "input_text" not in tool_args:
        tool_args["input_text"] = payload.input_text

    try:
        validate_tool_request_security(
            tool_name="rag.query",
            tool_args=tool_args,
        )
    except SecurityViolationError as exc:
        await log_deny_event(
            db,
            request,
            action="tool_call_failed",
            resource_type="Skill",
            resource_id=payload.skill_id or "rag.query",
            reason=exc.code,
            actor_user_id=str(actor.user_id),
            skill_id=payload.skill_id,
            tool_call_args=tool_args,
            side_effects_applied=[],
        )
        raise

    try:
        result_payload = execute_read_tool(
            intent="explain",
            tool_name="rag.query",
            skill_id=payload.skill_id,
            tool_args=tool_args,
        )
        result_payload = await _filter_rag_citations_by_existing_ref(
            db=db,
            request=request,
            actor=actor,
            tool_name="rag.query",
            result_payload=result_payload,
        )

        insufficient_template = build_insufficient_data_template(
            intent="explain",
            tool_name="rag.query",
            tool_args=tool_args,
            execution_result=result_payload,
        )
        if insufficient_template is not None:
            result_payload = insufficient_template

        await log_allow_event(
            db,
            request,
            action="rag_query",
            actor_user_id=str(actor.user_id),
            resource_type="RAGQuery",
            resource_id="*",
            reason="insufficient_data" if result_payload.get("status") == "insufficient_data" else "query_success",
            skill_id=payload.skill_id,
            tool_call_args=tool_args,
            side_effects_applied=[],
        )
        return {
            "trace_id": trace_id,
            "status": result_payload.get("status", "ok"),
            "result": result_payload,
        }
    except SecurityViolationError:
        raise
    except Exception as exc:  # pragma: no cover - 保护性分支
        await log_deny_event(
            db,
            request,
            action="tool_call_failed",
            resource_type="RAGQuery",
            resource_id="*",
            reason=f"rag_query_error:{type(exc).__name__}",
            actor_user_id=str(actor.user_id),
            skill_id=payload.skill_id,
            tool_call_args=tool_args,
            side_effects_applied=[],
        )
        raise HTTPException(status_code=500, detail="RAG 查询失败")


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
        result_payload = await _filter_rag_citations_by_existing_ref(
            db=db,
            request=request,
            actor=actor,
            tool_name=planned_tool.tool_name,
            result_payload=result_payload,
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
