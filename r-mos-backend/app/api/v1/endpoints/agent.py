"""
Agent API Endpoints
P0: Frontend integration for Agent services
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional, List, Dict, Any
import uuid
import logging

from app.core.database import get_db
from app.core.exceptions import PermissionDeniedError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.command_runtime import Command, AIToolCall
from app.models.approval import Approval
from app.services.tool_executor import validate_tool_request_security
from app.services.access_control import log_allow_event, log_deny_event
from app.services.authz_guard import ActorContext, get_current_actor
from app.api.v1.endpoints.ai_commands import _plan_tool_call

logger = logging.getLogger(__name__)

from app.services.agent_service import orchestrator
from app.services.coach_agent import coach_agent
from app.services.diagnoser_agent import diagnoser_agent
from app.services.multi_agent_coordinator import multi_agent_coordinator
from app.services.orchestrator_v2 import orchestrator_v2, TaskEventType
from app.services.approval_queue import approval_queue, ApprovalPriority
from app.services.policy_matrix import policy_matrix
from app.services.authz_guard import require_permission
from app.services.teaching.report_generator import ReportGenerator
from app.services.sop.quality_monitor import SOPQualityMonitor
from app.schemas.agent import (
    CoachRecommendRequest,
    DiagnoseRequest,
    CoordinateRequest,
    AgentExecuteMode,
    AgentExecuteRequest,
    AgentExecuteResponse,
    DiagnosisTraceActionRequest,
    DiagnosisTraceActionResponse,
    CreateApprovalRequest,
    GenerateReportRequest,
    GenerateReportResponse,
    SOPQualityCheckRequest,
    SOPQualityCheckResponse,
    GuidanceModeRequest,
    LLMPreferenceRequest,
    UserPreferenceResponse,
)
from app.api.v1.endpoints import agent_knowledge, agent_evidence

# Re-export symbols that tests access via `agent_endpoints.<name>`
from app.services.knowledge_governance import knowledge_governance  # noqa: F401
from app.api.v1.endpoints.agent_knowledge import knowledge_upload_jobs  # noqa: F401

router = APIRouter(prefix="/agent", tags=["agent"])

router.include_router(agent_knowledge.router)
router.include_router(agent_evidence.router)


@router.get("/task-status/{user_id}")
async def get_task_status(
    user_id: str,
    _: None = Depends(require_permission("agent:read", required_role="agent_user")),
):
    """Get current task status for user"""
    status = orchestrator.get_task_status(user_id)
    return status


# ============ Coach Agent Endpoints ============

@router.post("/coach/recommend", response_model=Dict[str, Any])
async def get_coach_recommendation(request: CoachRecommendRequest, _: None = Depends(require_permission("agent:execute"))):
    """Get coach agent recommendation for next action"""
    output = coach_agent.analyze_and_recommend(
        task_id=request.task_id,
        current_step=request.current_step,
        step_history=request.step_history,
        trainee_action=request.trainee_action
    )

    return {
        "next_action": output.next_action.model_dump() if output.next_action else None,
        "explanation": output.explanation,
        "risk_events": output.risk_events,
        "confidence": output.confidence,
        "reasoning": output.reasoning,
    }


# ============ Diagnoser Agent Endpoints ============

@router.post("/diagnoser/diagnose", response_model=Dict[str, Any])
async def diagnose_error(request: DiagnoseRequest, _: None = Depends(require_permission("agent:execute"))):
    """Diagnose root cause of errors"""
    output = diagnoser_agent.diagnose(
        task_id=request.task_id,
        error_history=request.error_history,
        action_history=request.action_history,
        available_evidence=request.evidence_refs
    )

    return {
        "root_cause": output.root_cause.cause_type.value if output.root_cause else None,
        "root_cause_confidence": output.root_cause.confidence if output.root_cause else 0,
        "evidence_refs": output.evidence_refs,
        "intervention": output.intervention,
        "baseline_comparison": output.baseline_comparison,
        "confidence": output.confidence,
        "reasoning": output.reasoning,
    }


# ============ Multi-Agent Coordination Endpoints ============

@router.post("/coordinate")
async def coordinate_agents(request: CoordinateRequest, _: None = Depends(require_permission("agent:execute"))):
    """Coordinate multiple agents"""
    result = await multi_agent_coordinator.coordinate(
        task_id=request.task_id,
        user_id=request.user_id,
        action=request.action,
        context=request.context
    )

    return {
        "task_id": result.task_id,
        "user_id": result.user_id,
        "final_action": result.final_action,
        "consensus": result.consensus,
        "conflicts": result.conflicts,
        "execution_time_ms": result.execution_time_ms,
    }


# ============ P2-1: Unified Agent Execute Schema ============

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

def _detect_mode(request: AgentExecuteRequest) -> str:
    """Auto-detect execution mode based on request fields"""
    if request.mode != AgentExecuteMode.AUTO:
        return request.mode

    # Auto-detect: command mode takes priority if command fields are provided
    if request.tool_name or request.intent:
        return AgentExecuteMode.COMMAND
    if request.message:
        return AgentExecuteMode.MESSAGE

    # Default to message mode
    return AgentExecuteMode.MESSAGE


@router.post("/execute", response_model=AgentExecuteResponse, deprecated=False)
async def execute_agent(
    request: AgentExecuteRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """Unified Agent Execute Endpoint - P2-1 Convergence

    This endpoint handles both command execution and message processing.
    """
    # Generate trace_id if not provided
    trace_id = request.trace_id or str(uuid.uuid4())[:8]
    http_request.state.trace_id = trace_id

    # Detect execution mode
    mode = _detect_mode(request)
    required_permission = "agent:execute" if mode == AgentExecuteMode.COMMAND else "agent:read"
    await _require_agent_permission(
        http_request,
        db,
        actor,
        permission_key=required_permission,
    )
    logger.info(f"[P2-1] Agent execute: mode={mode}, user_id={request.user_id}, trace_id={trace_id}")

    if mode == AgentExecuteMode.COMMAND:
        # A-mode: Handle as command execution
        try:
            # Build CommandCreateRequest-like payload
            command_payload = {
                "intent": request.intent or "dispatch",
                "input_text": request.input_text,
                "skill_id": request.skill_id,
                "tool_name": request.tool_name,
                "tool_args": request.tool_args,
                "side_effects": request.side_effects,
            }

            # Create Command record
            command = Command(
                user_id=request.user_id,
                intent=command_payload["intent"],
                input_text=command_payload.get("input_text"),
                skill_id=command_payload.get("skill_id"),
                status="pending",
            )
            db.add(command)
            await db.commit()
            await db.refresh(command)

            # Plan tool call
            from app.api.v1.endpoints.ai_commands import CommandCreateRequest

            cmd_req = CommandCreateRequest(**command_payload)
            planned_tool = _plan_tool_call(cmd_req)

            # Validate security
            try:
                validate_tool_request_security(
                    tool_name=planned_tool.tool_name,
                    tool_args=planned_tool.tool_args,
                )
            except Exception as sec_error:
                await log_deny_event(
                    db,
                    http_request,
                    action="tool_call_failed",
                    resource_type="Skill",
                    resource_id=planned_tool.skill_id or planned_tool.tool_name,
                    reason=str(sec_error),
                    actor_user_id=str(actor.user_id),
                    skill_id=planned_tool.skill_id,
                    tool_call_args=planned_tool.tool_args,
                    side_effects_applied=list(planned_tool.side_effects),
                )
                raise

            # Log allow event
            await log_allow_event(
                db,
                http_request,
                action="command_created",
                actor_user_id=str(actor.user_id),
                resource_type="Command",
                resource_id=command.id,
                reason="unified_agent_execute",
            )

            # Create tool call
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

            # Handle side effects - require approval
            approval_id = None
            result_status = "success"
            result_data = {
                "command_id": command.id,
                "tool_call_id": tool_call.id,
                "tool_name": planned_tool.tool_name,
                "skill_id": planned_tool.skill_id,
                "status": "pending",
            }

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

                approval_id = approval.id
                result_status = "pending_approval"
                result_data["status"] = "waiting_approval"
                result_data["approval_id"] = approval.id

            return AgentExecuteResponse(
                status=result_status,
                result=result_data,
                trace_id=trace_id,
                from_cache=False,
                approval_id=approval_id,
                mode_used=AgentExecuteMode.COMMAND,
            )

        except Exception as e:
            logger.error(f"[P2-1] Command mode error: {e}")
            return AgentExecuteResponse(
                status="error",
                result={"error": str(e)},
                trace_id=trace_id,
                from_cache=False,
                approval_id=None,
                mode_used=AgentExecuteMode.COMMAND,
            )

    else:
        # B-mode: Handle as message (via OrchestratorV2)
        try:
            response = await orchestrator_v2.process_request(
                user_id=request.user_id,
                message=request.message or "",
                resource_ref=request.resource_ref,
                policy_context=request.policy_context,
                intent_classification=request.intent_classification,
                telemetry_payload=request.telemetry_payload,
                trace_id=trace_id,
                idempotency_key=request.idempotency_key,
            )

            return AgentExecuteResponse(
                status="success",
                result=response,
                trace_id=trace_id,
                from_cache=response.get("from_cache", False),
                approval_id=response.get("approval_id"),
                mode_used=AgentExecuteMode.MESSAGE,
            )

        except Exception as e:
            logger.error(f"[P2-1] Message mode error: {e}")
            return AgentExecuteResponse(
                status="error",
                result={"error": str(e)},
                trace_id=trace_id,
                from_cache=False,
                approval_id=None,
                mode_used=AgentExecuteMode.MESSAGE,
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


# ============ Approval Queue Endpoints (Phase 2) ============

@router.post("/approval/request")
async def create_approval_request(request: CreateApprovalRequest, _: None = Depends(require_permission("agent:execute"))):
    """Create a new approval request"""
    request_id = approval_queue.create_request(
        requester_id=request.requester_id,
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        action=request.action,
        reason=request.reason,
        priority=ApprovalPriority(request.priority),
        evidence_refs=request.evidence_refs,
        ttl_seconds=request.ttl_seconds,
    )

    return {
        "request_id": request_id,
        "status": "pending",
    }


@router.get("/approval/pending")
async def get_pending_approvals(
    priority: Optional[str] = None,
    limit: int = 100,
    _: None = Depends(require_permission("agent:read")),
):
    """Get pending approval requests"""
    prio = ApprovalPriority(priority) if priority else None
    requests = approval_queue.get_pending_requests(prio, limit)

    return {
        "requests": [
            {
                "id": r.id,
                "requester_id": r.requester_id,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "action": r.action,
                "priority": r.priority.value,
                "reason": r.reason,
                "evidence_refs": r.evidence_refs,
                "created_at": r.created_at,
                "expires_at": r.expires_at,
            }
            for r in requests
        ]
    }


@router.get("/approval/history")
async def get_approval_history(
    limit: int = 100,
    offset: int = 0,
    _: None = Depends(require_permission("agent:read")),
):
    """Get approval request history (approved/rejected)"""
    history = approval_queue.get_request_history(limit, offset)

    return {
        "requests": [
            {
                "id": r.id,
                "requester_id": r.requester_id,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "action": r.action,
                "priority": r.priority.value if r.priority else None,
                "status": r.status.value if r.status else None,
                "reason": r.reason,
                "evidence_refs": r.evidence_refs,
                "created_at": r.created_at,
                "approved_by": getattr(r, 'approved_by', None),
                "approved_at": getattr(r, 'approved_at', None),
                "rejection_reason": getattr(r, 'rejection_reason', None),
            }
            for r in history
        ]
    }


@router.post("/approval/{request_id}/approve")
async def approve_request(
    request_id: str,
    approved_by: str,
    _: None = Depends(require_permission("agent:execute")),
):
    """Approve an approval request"""
    success = approval_queue.approve(request_id, approved_by)

    if not success:
        raise HTTPException(status_code=404, detail="Approval request not found")

    return {
        "request_id": request_id,
        "status": "approved",
        "approved_by": approved_by,
    }


@router.post("/approval/{request_id}/reject")
async def reject_request(
    request_id: str,
    rejection_reason: str,
    _: None = Depends(require_permission("agent:execute")),
):
    """Reject an approval request"""
    success = approval_queue.reject(request_id, rejection_reason)

    if not success:
        raise HTTPException(status_code=404, detail="Approval request not found")

# ============ P2-2: Evaluation Report Endpoints ============

@router.post("/evaluation/report", response_model=GenerateReportResponse)
async def generate_evaluation_report(
    request: GenerateReportRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("agent:read")),
):
    """Generate LLM-enhanced evaluation report for a task - P2-2

    This endpoint generates a comprehensive evaluation report that includes:
    - Basic scoring (4 dimensions)
    - Step-by-step analysis
    - LLM-generated narrative evaluation (if use_llm=True)
    """
    generator = ReportGenerator(db)

    # Generate report
    report = await generator.generate_report(
        task_id=request.task_id,
        use_llm=request.use_llm,
    )

    # Save to evidence bundle
    try:
        bundle = await generator.save_to_evidence_bundle(report, request.task_id)
        bundle_id = bundle.id
    except Exception as e:
        logger.warning(f"[P2-2] Failed to save report to evidence bundle: {e}")
        bundle_id = None

    return GenerateReportResponse(
        report=report,
        bundle_id=bundle_id,
    )


# ============ P2-3: SOP Quality Monitor Endpoints ============

@router.post("/sop/quality/check", response_model=SOPQualityCheckResponse)
async def check_sop_quality(
    request: SOPQualityCheckRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("agent:execute")),
):
    """Check SOP quality and create review tickets - P2-3-4

    Monitors step failure rates and automatically creates review tickets
    when failure rate exceeds 40%.
    """
    monitor = SOPQualityMonitor(db)

    if request.sop_id:
        # Check specific SOP
        alerts = await monitor.check_sop_quality(
            sop_id=request.sop_id,
            time_range_days=request.time_range_days,
        )
        tickets = []
        for alert in alerts:
            ticket = await monitor.create_quality_ticket(alert)
            tickets.append(ticket)

        return SOPQualityCheckResponse(
            alerts=[a.__dict__ for a in alerts],
            tickets_created=tickets,
        )
    else:
        # Run full quality check
        tickets = await monitor.run_quality_check(
            time_range_days=request.time_range_days,
        )

        return SOPQualityCheckResponse(
            alerts=[],
            tickets_created=tickets,
        )


# ============ P2-4: User Preference Endpoints ============

@router.get("/preference", response_model=UserPreferenceResponse)
async def get_user_preference(
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """Get current user's preference - P2-4-1

    Returns the user's guidance mode preference.
    """
    from app.services.user_preference_service import UserPreferenceService, GuidanceMode

    service = UserPreferenceService(db)
    pref = await service.get_or_create_preference(actor.user_id)

    return UserPreferenceResponse(
        user_id=pref.user_id,
        guidance_mode=pref.guidance_mode,
        guidance_mode_display=GuidanceMode.get_display_name(pref.guidance_mode),
        preferences=service.build_public_preferences(pref.preferences),
    )


@router.put("/preference/guidance-mode", response_model=UserPreferenceResponse)
async def update_guidance_mode(
    request: GuidanceModeRequest,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """Update user's guidance mode - P2-4-1

    Sets the user's preferred AI guidance mode:
    - full_time: Agent provides guidance throughout the task
    - on_demand: Agent provides guidance when user requests
    - silent: Agent does not provide guidance
    """
    from app.services.user_preference_service import UserPreferenceService, GuidanceMode

    service = UserPreferenceService(db)
    pref = await service.update_guidance_mode(actor.user_id, request.mode)

    return UserPreferenceResponse(
        user_id=pref.user_id,
        guidance_mode=pref.guidance_mode,
        guidance_mode_display=GuidanceMode.get_display_name(pref.guidance_mode),
        preferences=service.build_public_preferences(pref.preferences),
    )


@router.put("/preference/llm", response_model=UserPreferenceResponse)
async def update_llm_preference(
    request: LLMPreferenceRequest,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """Update current user's LLM provider/model/base_url/api_key settings."""
    from app.services.user_preference_service import UserPreferenceService, GuidanceMode

    service = UserPreferenceService(db)
    pref = await service.update_llm_preferences(
        actor.user_id,
        provider=request.provider,
        model=request.model,
        base_url=request.base_url,
        api_key=request.api_key,
    )

    return UserPreferenceResponse(
        user_id=pref.user_id,
        guidance_mode=pref.guidance_mode,
        guidance_mode_display=GuidanceMode.get_display_name(pref.guidance_mode),
        preferences=service.build_public_preferences(pref.preferences),
    )
