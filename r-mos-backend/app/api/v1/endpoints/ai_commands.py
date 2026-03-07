"""Gate-2 E-001：AI Command 最小读链路入口。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ReadAccessDeniedError,
    ResourceNotFoundError,
)
from app.core.database import get_db
from app.models.audit_event import AuditEvent
from app.models.command_runtime import AIToolCall
from app.models.knowledge_chunk import AIKnowledgeChunk
from app.services.access_control import log_allow_event, log_deny_event
from app.services.authz_guard import ActorContext, get_current_actor, require_permission


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


def _is_trace_replay_reader(actor: ActorContext) -> bool:
    return bool({"admin", "auditor"} & actor.roles)


READ_TOOL_SUCCESS_RATE_METRIC_ID = "read_tool_success_rate"
READ_TOOL_SUCCESS_RATE_TARGET = 99.0
REDTEAM_BATCH_METRIC_ID = "sec_t001_t007_batch"

_REDTEAM_SECURITY_CASES = {
    "SEC-T001": "SECURITY_BLACKLIST_KEYWORD",
    "SEC-T002": "SECURITY_INJECTION_PATTERN",
    "SEC-T003": "SECURITY_INVALID_REFERENCE",
    "SEC-T004": "SECURITY_PARAM_OUT_OF_RANGE",
}
_REDTEAM_SCOPE_CASES = {
    "SEC-T005": "student_attempt_scope_mismatch",
    "SEC-T006": "teacher_course_scope_mismatch",
}
_REDTEAM_RISK_BLOCK_REASONS = {"feature_flag_disabled", "permission_denied"}


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


@router.get("/ai/replay/{trace_id}")
async def get_trace_replay(
    trace_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(require_permission("audit_events:read")),
):
    """J-001：按 trace_id 回放关键审计序列（最小闭环）。"""
    request.state.trace_id = trace_id

    if not _is_trace_replay_reader(actor):
        reason = "trace_scope_denied:admin_or_auditor"
        await log_deny_event(
            db,
            request,
            action="access_denied",
            resource_type="TraceReplay",
            resource_id=trace_id,
            reason=reason,
            actor_user_id=str(actor.user_id),
        )
        raise ReadAccessDeniedError(
            action="access_denied",
            resource_type="TraceReplay",
            resource_id=trace_id,
            reason=reason,
            message="资源不存在",
        )

    result = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.trace_id == trace_id)
        .order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
    )
    events = list(result.scalars().all())
    if not events:
        raise ResourceNotFoundError("TraceReplay", trace_id)

    await log_allow_event(
        db,
        request,
        action="trace_replay_read",
        actor_user_id=str(actor.user_id),
        resource_type="TraceReplay",
        resource_id=trace_id,
        reason="trace_replay_success",
    )

    items = [
        {
            "id": event.id,
            "trace_id": event.trace_id,
            "action": event.action,
            "decision": event.decision,
            "actor_user_id": event.actor_user_id,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "reason": event.reason,
            "approval_id": event.approval_id,
            "created_at": event.created_at.isoformat() if event.created_at else None,
        }
        for event in events
    ]
    return {
        "trace_id": trace_id,
        "count": len(items),
        "items": items,
    }


@router.get("/ai/replay/metrics/read-tool-success-rate")
async def get_read_tool_success_rate(
    request: Request,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(require_permission("audit_events:read")),
):
    """J-002：Read Tool 成功率统计最小闭环。"""
    metric_id = READ_TOOL_SUCCESS_RATE_METRIC_ID
    if not _is_trace_replay_reader(actor):
        reason = "trace_scope_denied:admin_or_auditor"
        await log_deny_event(
            db,
            request,
            action="access_denied",
            resource_type="ReadToolMetric",
            resource_id=metric_id,
            reason=reason,
            actor_user_id=str(actor.user_id),
        )
        raise ReadAccessDeniedError(
            action="access_denied",
            resource_type="ReadToolMetric",
            resource_id=metric_id,
            reason=reason,
            message="资源不存在",
        )

    bounded_limit = max(1, min(limit, 1000))
    result = await db.execute(
        select(AIToolCall).order_by(AIToolCall.id.desc()).limit(bounded_limit)
    )
    tool_calls = list(result.scalars().all())
    read_tool_calls = [call for call in tool_calls if not (call.side_effects or [])]
    total = len(read_tool_calls)
    success = sum(1 for call in read_tool_calls if call.status == "success")
    failed = sum(1 for call in read_tool_calls if call.status in {"failed", "rejected"})
    non_terminal = max(total - success - failed, 0)
    success_rate = round((success / total) * 100, 2) if total else 0.0
    meets_target = total > 0 and success_rate >= READ_TOOL_SUCCESS_RATE_TARGET

    await log_allow_event(
        db,
        request,
        action="read_tool_success_rate_read",
        actor_user_id=str(actor.user_id),
        resource_type="ReadToolMetric",
        resource_id=metric_id,
        reason="read_tool_success_rate_computed",
    )

    return {
        "metric_id": metric_id,
        "trace_id": getattr(request.state, "trace_id", None),
        "total": total,
        "success": success,
        "failed": failed,
        "non_terminal": non_terminal,
        "success_rate": success_rate,
        "target_rate": READ_TOOL_SUCCESS_RATE_TARGET,
        "meets_target": meets_target,
    }


@router.get("/ai/replay/metrics/red-team-pass-rate")
async def get_redteam_pass_rate(
    request: Request,
    limit: int = 2000,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(require_permission("audit_events:read")),
):
    """J-003：红队 P0 用例跑批最小闭环（SEC-T001~SEC-T007）。"""
    metric_id = REDTEAM_BATCH_METRIC_ID
    if not _is_trace_replay_reader(actor):
        reason = "trace_scope_denied:admin_or_auditor"
        await log_deny_event(
            db,
            request,
            action="access_denied",
            resource_type="RedTeamBatch",
            resource_id=metric_id,
            reason=reason,
            actor_user_id=str(actor.user_id),
        )
        raise ReadAccessDeniedError(
            action="access_denied",
            resource_type="RedTeamBatch",
            resource_id=metric_id,
            reason=reason,
            message="资源不存在",
        )

    bounded_limit = max(1, min(limit, 5000))
    result = await db.execute(
        select(AuditEvent).order_by(AuditEvent.id.desc()).limit(bounded_limit)
    )
    events = list(result.scalars().all())

    denied_security_codes = {
        event.reason
        for event in events
        if event.action == "tool_call_failed" and event.decision == "deny" and event.reason
    }
    denied_scope_reasons = {
        event.reason
        for event in events
        if event.decision == "deny"
        and event.action in {"access_denied", "read_access_denied"}
        and event.resource_type in {"AssignmentAttempt", "attempt"}
        and event.reason
    }
    sec_t007_hit = any(
        event.decision == "deny"
        and event.action in {"tool_call_failed", "write_access_denied"}
        and (event.reason or "") in _REDTEAM_RISK_BLOCK_REASONS
        for event in events
    )

    cases = {
        case_id: (reason in denied_security_codes)
        for case_id, reason in _REDTEAM_SECURITY_CASES.items()
    }
    cases.update(
        {
            case_id: (reason in denied_scope_reasons)
            for case_id, reason in _REDTEAM_SCOPE_CASES.items()
        }
    )
    cases["SEC-T007"] = sec_t007_hit

    total = len(cases)
    pass_count = sum(1 for passed in cases.values() if passed)
    pass_rate = round((pass_count / total) * 100, 2) if total else 0.0
    meets_target = pass_count == total

    await log_allow_event(
        db,
        request,
        action="redteam_batch_read",
        actor_user_id=str(actor.user_id),
        resource_type="RedTeamBatch",
        resource_id=metric_id,
        reason="redteam_batch_summary",
    )

    return {
        "metric_id": metric_id,
        "trace_id": getattr(request.state, "trace_id", None),
        "total": total,
        "pass_count": pass_count,
        "pass_rate": pass_rate,
        "meets_target": meets_target,
        "cases": cases,
    }
