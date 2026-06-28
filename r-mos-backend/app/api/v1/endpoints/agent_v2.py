"""
Agent V2 API Endpoints
Task FSM, policy evaluation, idempotency, trace events, module registry.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.exceptions import PermissionDeniedError
from app.services.access_control import log_deny_event
from app.services.authz_guard import ActorContext, get_current_actor, require_permission
from app.services.orchestrator_v2 import orchestrator_v2, TaskEventType
from app.services.policy_matrix import policy_matrix
from app.schemas.agent import (
    DiagnosisTraceActionRequest,
    DiagnosisTraceActionResponse,
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


async def _require_agent_permission(
    http_request: Request,
    db: AsyncSession,
    actor: ActorContext,
    *,
    permission_key: str,
) -> None:
    if permission_key in actor.permissions:
        return

    reason = f"missing_permission:{permission_key}"
    await log_deny_event(
        db,
        http_request,
        action="permission_denied",
        resource_type="Route",
        resource_id=http_request.url.path,
        reason=reason,
        actor_user_id=str(actor.user_id),
    )
    raise PermissionDeniedError(
        action="permission_denied",
        resource_type="Route",
        resource_id=http_request.url.path,
        reason=reason,
        message="权限不足",
    )


# V2: Task FSM Endpoints
@router.post("/v2/trace/{trace_id}/diagnosis-action", response_model=DiagnosisTraceActionResponse)
async def record_diagnosis_trace_action(
    trace_id: str,
    request: DiagnosisTraceActionRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    await _require_agent_permission(
        http_request,
        db,
        actor,
        permission_key="agent:read",
    )

    action_messages = {
        "confirm_execution": "已确认执行方案，请转入 SOP 工作台执行。",
        "escalate_to_teacher": "已上报教师审核，请等待处理。",
    }
    message = action_messages.get(request.action)
    if message is None:
        raise HTTPException(status_code=400, detail=f"Unsupported diagnosis action: {request.action}")

    orchestrator_v2.record_trace_event(
        trace_id,
        "diagnosis_action",
        {
            "action": request.action,
            "actor_user_id": str(actor.user_id),
            "message": message,
        },
    )
    return DiagnosisTraceActionResponse(
        trace_id=trace_id,
        action=request.action,
        message=message,
        recorded=True,
    )


@router.post("/v2/task/create")
async def create_task_v2(
    user_id: str,
    skill_id: Optional[str] = None,
    budget_limit_ms: int = 300000,
    _: None = Depends(require_permission("agent:execute")),
):
    """Create a new task with FSM"""
    context = orchestrator_v2.create_task(
        user_id=user_id,
        skill_id=skill_id,
        budget_limit_ms=budget_limit_ms,
    )
    return {
        "task_id": context.task_id,
        "trace_id": context.trace_id,
        "state": context.state.value,
        "budget_limit_ms": context.budget_limit_ms,
    }


@router.post("/v2/task/{task_id}/transition")
async def transition_task_state(
    task_id: str,
    event: str,
    _: None = Depends(require_permission("agent:execute")),
):
    """Transition task state"""
    try:
        event_type = TaskEventType(event)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid event: {event}")

    success, message, state = orchestrator_v2.transition_state(task_id, event_type)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "task_id": task_id,
        "state": state.value,
        "message": message,
    }


@router.get("/v2/task/{task_id}")
async def get_task_status_v2(task_id: str, _: None = Depends(require_permission("agent:read"))):
    """Get task status"""
    context = orchestrator_v2.get_task_context(task_id)

    if not context:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": context.task_id,
        "trace_id": context.trace_id,
        "state": context.state.value,
        "user_id": context.user_id,
        "skill_id": context.skill_id,
        "current_step": context.current_step,
        "total_steps": context.total_steps,
        "budget_used_ms": context.budget_used_ms,
        "budget_limit_ms": context.budget_limit_ms,
        "created_at": context.created_at,
        "started_at": context.started_at,
        "completed_at": context.completed_at,
    }


# V2: Policy Evaluation Endpoint
@router.post("/v2/policy/evaluate")
async def evaluate_policy_v2(
    action: str,
    context: Dict[str, Any],
    _: None = Depends(require_permission("agent:execute")),
):
    """Evaluate policy for an action"""
    decision = policy_matrix.evaluate(action, context)
    return decision.model_dump()


# V2: Idempotency Check Endpoint
@router.get("/v2/idempotency/{idempotency_key}")
async def check_idempotency(idempotency_key: str, _: None = Depends(require_permission("agent:read"))):
    """Check if request has been processed"""
    # This is a simplified version - in production, this would check the database
    return {
        "exists": False,
        "message": "Use /v2/request with idempotency_key to check"
    }


# V2: Trace Events Endpoint
@router.get("/v2/trace/{trace_id}/events")
async def get_trace_events(trace_id: str, _: None = Depends(require_permission("agent:read"))):
    """Get events for a trace"""
    events = orchestrator_v2.get_trace_events(trace_id)
    return {
        "trace_id": trace_id,
        "events": events,
    }


# V2: Module Registry Endpoints
@router.get("/v2/modules")
async def list_modules(_: None = Depends(require_permission("agent:read"))):
    """List available modules"""
    modules = orchestrator_v2._module_registry.list_modules()
    return {
        "modules": [
            {
                "id": m,
                "metadata": orchestrator_v2._module_registry.get_metadata(m)
            }
            for m in modules
        ]
    }
