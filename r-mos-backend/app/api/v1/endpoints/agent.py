"""
Agent API Endpoints
P0: Frontend integration for Agent services
"""

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import time
import uuid
import logging
import enum

from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.command_runtime import Command, AIToolCall
from app.models.approval import Approval
from app.services.tool_executor import validate_tool_request_security
from app.services.access_control import log_allow_event, log_deny_event
from app.services.authz_guard import ActorContext, get_current_actor
from app.api.v1.endpoints.ai_commands import _plan_tool_call, PlannedToolCall

logger = logging.getLogger(__name__)

from app.services.agent_service import orchestrator
from app.services.coach_agent import coach_agent, CoachOutput
from app.services.diagnoser_agent import diagnoser_agent, DiagnoserOutput
from app.services.knowledge_governance import knowledge_governance
from app.services.multi_agent_coordinator import multi_agent_coordinator
from app.services.evidence_enforcement import evidence_enforcer, ACTION_EVIDENCE_REQUIREMENTS
from app.services.orchestrator_v2 import orchestrator_v2, TaskFSMState, TaskEventType
from app.services.feature_flag import feature_flags
from app.services.belief_state import get_or_create_belief_state, get_belief_state, BeliefConfidence, BeliefSource
from app.services.evidence_collector import evidence_collector, EvidenceType, EvidenceStatus
from app.services.compensation_planner import compensation_planner, CompensationStrategy
from app.services.approval_queue import approval_queue, ApprovalPriority
from app.services.policy_matrix import policy_matrix, PolicyDecision
from app.services.authz_guard import require_permission
from app.services.teaching.report_generator import ReportGenerator
from app.schemas.report import LLMEvaluationReport

router = APIRouter(prefix="/agent", tags=["agent"])
knowledge_upload_jobs: dict[str, dict[str, Any]] = {}


class CoachRecommendRequest(BaseModel):
    task_id: str
    current_step: int
    step_history: List[Dict[str, Any]] = Field(default_factory=list)
    trainee_action: Optional[Dict[str, Any]] = None


class DiagnoseRequest(BaseModel):
    task_id: str
    error_history: List[Dict[str, Any]] = Field(default_factory=list)
    action_history: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)


class KnowledgeSearchRequest(BaseModel):
    query: str = ""
    device_model: Optional[str] = None
    part_type: Optional[str] = None
    status: Optional[str] = "APPROVED"


class KnowledgeCreateRequest(BaseModel):
    title: str
    content: str
    type: str = "solution"
    scope: Optional[Dict[str, Any]] = None
    risk_level: str = "R1"


class KnowledgeApproveRequest(BaseModel):
    decision: str  # approve, reject
    feedback: str = ""
    rating: Optional[float] = None


class CoordinateRequest(BaseModel):
    task_id: str
    user_id: str
    action: str
    context: Dict[str, Any] = Field(default_factory=dict)


class EvidenceCollectRequest(BaseModel):
    step_id: str
    evidence_id: str
    evidence_type: str


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


# ============ Knowledge Governance Endpoints ============

@router.post("/knowledge/search")
async def search_knowledge(request: KnowledgeSearchRequest, _: None = Depends(require_permission("agent:read"))):
    """Search knowledge entries"""
    from app.services.knowledge_governance import KnowledgeSearchQuery, KnowledgeStatus

    status = KnowledgeStatus.APPROVED if request.status == "APPROVED" else KnowledgeStatus.PENDING

    results = knowledge_governance.search_knowledge(
        KnowledgeSearchQuery(
            query=request.query,
            device_model=request.device_model,
            part_type=request.part_type,
            status=status,
        )
    )

    return {
        "results": [
            {
                "id": m.entry.id,
                "type": m.entry.type.value,
                "status": m.entry.status.value,
                "title": m.entry.title,
                "content": m.entry.content,
                "scope": m.entry.scope.model_dump(),
                "contraindications": m.entry.contraindications.model_dump(),
                "risk_level": m.entry.risk_level.value,
                "confidence": m.entry.confidence.model_dump(),
                "relevance_score": m.relevance_score,
                "match_reasons": m.match_reasons,
            }
            for m in results
        ]
    }


@router.post("/knowledge")
async def create_knowledge(
    request: KnowledgeCreateRequest,
    actor: ActorContext = Depends(require_permission("agent:execute")),
):
    """Create new knowledge entry"""
    from app.services.knowledge_governance import KnowledgeType, RiskLevel, Scope

    entry = knowledge_governance.create_knowledge(
        title=request.title,
        content=request.content,
        entry_type=KnowledgeType(request.type),
        creator_id=str(actor.user_id),
        scope=Scope(**request.scope) if request.scope else None,
        risk_level=RiskLevel(request.risk_level),
    )

    return {
        "id": entry.id,
        "status": entry.status.value,
        "title": entry.title,
    }


@router.post("/knowledge/upload")
async def upload_knowledge_file(
    file: UploadFile = File(...),
    brand: Optional[str] = None,
    _: None = Depends(require_permission("agent:execute")),
):
    """Upload a knowledge file and create an ingest job record."""
    content = await file.read()
    job_id = f"kb-job-{uuid.uuid4().hex[:12]}"
    knowledge_upload_jobs[job_id] = {
        "job_id": job_id,
        "status": "completed" if content else "failed",
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": len(content),
        "brand": brand,
    }
    return knowledge_upload_jobs[job_id]


@router.get("/knowledge/upload/{job_id}")
async def get_knowledge_upload_job(
    job_id: str,
    _: None = Depends(require_permission("agent:read")),
):
    """Query upload ingest job status."""
    job = knowledge_upload_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Knowledge upload job not found")
    return job


@router.post("/knowledge/{entry_id}/submit")
async def submit_knowledge(entry_id: str, _: None = Depends(require_permission("agent:execute"))):
    """Submit knowledge for review"""
    success, message = knowledge_governance.submit_for_review(entry_id)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"status": "submitted"}


@router.post("/knowledge/{entry_id}/approve")
async def approve_knowledge(
    entry_id: str,
    request: KnowledgeApproveRequest,
    actor: ActorContext = Depends(require_permission("agent:execute")),
):
    """Approve or reject knowledge"""
    from app.services.knowledge_governance import ApprovalRequest

    success, message = knowledge_governance.approve_knowledge(
        ApprovalRequest(
            entry_id=entry_id,
            reviewer_id=str(actor.user_id),
            decision=request.decision,
            feedback=request.feedback,
            rating=request.rating,
        )
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"status": request.decision}


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


# ============ Evidence Enforcement Endpoints ============

@router.get("/evidence/status/{step_id}")
async def get_evidence_status(step_id: str, _: None = Depends(require_permission("agent:read"))):
    """Get evidence collection status for a step"""
    status = evidence_enforcer.get_evidence_status(step_id)
    return status


@router.post("/evidence/collect")
async def collect_evidence(request: EvidenceCollectRequest, _: None = Depends(require_permission("agent:execute"))):
    """Record evidence collection"""
    evidence_enforcer.collect_evidence(
        step_id=request.step_id,
        evidence_id=request.evidence_id,
        evidence_type=request.evidence_type
    )
    return {"status": "collected"}


@router.get("/evidence/can-proceed/{step_id}")
async def can_proceed(step_id: str, _: None = Depends(require_permission("agent:read"))):
    """Check if can proceed to next step"""
    allowed, reason = evidence_enforcer.can_proceed(step_id)
    return {"allowed": allowed, "reason": reason}


# ============ Action Evidence Requirements ============

@router.get("/evidence/requirements/{action_type}")
async def get_evidence_requirements(action_type: str, _: None = Depends(require_permission("agent:read"))):
    """Get required evidence for an action type"""
    requirements = ACTION_EVIDENCE_REQUIREMENTS.get(action_type, [])
    return {"action_type": action_type, "requirements": [r.model_dump() for r in requirements]}


# ============ P2-1: Unified Agent Execute Schema ============

class AgentExecuteMode(str, enum.Enum):
    """Execution mode for unified agent endpoint"""
    COMMAND = "command"
    MESSAGE = "message"
    AUTO = "auto"         # Auto-detect based on input


class AgentExecuteRequest(BaseModel):
    """Unified Agent Execute Request - P2-1 Convergence

    Supports both command-style and message-style invocation.
    """
    # Common fields
    user_id: str
    mode: AgentExecuteMode = Field(default=AgentExecuteMode.AUTO, description="Execution mode: command|message|auto")

    # Command mode fields
    intent: Optional[str] = Field(default=None, description="Command intent")
    tool_name: Optional[str] = Field(default=None, description="Tool to execute")
    tool_args: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    skill_id: Optional[str] = Field(default=None, description="Skill ID")
    side_effects: List[str] = Field(default_factory=list, description="Side effects")
    input_text: Optional[str] = Field(default=None, description="Input text for command")

    # Message mode fields
    message: Optional[str] = Field(default=None, description="Natural language message")

    # Shared fields
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    resource_ref: Optional[Dict[str, Any]] = Field(default=None, description="Resource reference")
    policy_context: Optional[Dict[str, Any]] = Field(default=None, description="Policy context")
    intent_classification: Optional[str] = Field(default=None, description="Pre-classified intent")
    trace_id: Optional[str] = Field(default=None, description="Trace ID for replay")
    idempotency_key: Optional[str] = Field(default=None, description="Idempotency key")

    class Config:
        json_schema_extra = {
            "examples": [
                # Command mode example
                {
                    "mode": "command",
                    "user_id": "user-123",
                    "intent": "dispatch",
                    "tool_name": "assignments.create_draft",
                    "skill_id": "teaching.dispatch.draft",
                    "tool_args": {"input_text": "Create a task for robot arm maintenance"},
                    "side_effects": ["assignments.write"],
                },
                # Message mode example
                {
                    "mode": "message",
                    "user_id": "user-123",
                    "message": "Help me with the current maintenance task",
                    "context": {"task_id": "task-456"},
                },
            ]
        }


class AgentExecuteResponse(BaseModel):
    """Unified Agent Execute Response"""
    status: str = Field(description="Execution status: success|pending_approval|error")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Execution result")
    trace_id: str = Field(description="Trace ID for this execution")
    from_cache: bool = Field(default=False, description="Whether result was from cache")
    approval_id: Optional[int] = Field(default=None, description="Approval ID if pending")
    mode_used: str = Field(description="Actual mode used: command|message")

# ============ P2-1: Unified Agent Execute Endpoint ============

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
    _: None = Depends(require_permission("agent:execute")),
):
    """Unified Agent Execute Endpoint - P2-1 Convergence

    This endpoint handles both command execution and message processing.
    """
    # Generate trace_id if not provided
    trace_id = request.trace_id or str(uuid.uuid4())[:8]
    http_request.state.trace_id = trace_id

    # Detect execution mode
    mode = _detect_mode(request)
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
            response = orchestrator_v2.process_request(
                user_id=request.user_id,
                message=request.message or "",
                resource_ref=request.resource_ref,
                policy_context=request.policy_context,
                intent_classification=request.intent_classification,
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


# ============ Feature Flag Endpoints ============

@router.get("/features")
async def list_feature_flags(_: None = Depends(require_permission("agent:read"))):
    """List all feature flags"""
    flags = feature_flags.list_flags()
    return {
        "flags": [
            {
                "name": name,
                "enabled": flag.enabled,
                "rollout_percentage": flag.rollout_percentage,
                "description": flag.description,
            }
            for name, flag in flags.items()
        ]
    }


@router.get("/features/{flag_name}/status")
async def get_feature_flag_status(flag_name: str, user_id: Optional[str] = None, _: None = Depends(require_permission("agent:read"))):
    """Check if a feature flag is enabled"""
    enabled = feature_flags.is_enabled(flag_name, user_id)
    flag = feature_flags.get_flag(flag_name)
    return {
        "flag_name": flag_name,
        "enabled": enabled,
        "rollout_percentage": flag.rollout_percentage if flag else 0,
        "description": flag.description if flag else "",
    }


@router.post("/features/{flag_name}/enable")
async def enable_feature_flag(flag_name: str, _: None = Depends(require_permission("agent:execute"))):
    """Enable a feature flag"""
    feature_flags.enable_flag(flag_name)
    return {"flag_name": flag_name, "enabled": True}


@router.post("/features/{flag_name}/disable")
async def disable_feature_flag(flag_name: str, _: None = Depends(require_permission("agent:execute"))):
    """Disable a feature flag"""
    feature_flags.disable_flag(flag_name)
    return {"flag_name": flag_name, "enabled": False}


@router.post("/features/{flag_name}/rollout")
async def set_rollout_percentage(flag_name: str, percentage: int, _: None = Depends(require_permission("agent:execute"))):
    """Set rollout percentage for a feature flag"""
    feature_flags.set_rollout_percentage(flag_name, percentage)
    flag = feature_flags.get_flag(flag_name)
    return {"flag_name": flag_name, "rollout_percentage": flag.rollout_percentage if flag else 0}


# ============ Belief State Endpoints (Phase 2) ============

class AddBeliefRequest(BaseModel):
    """Request to add a belief"""
    trace_id: str
    category: str
    proposition: str
    confidence: str
    confidence_value: float
    source: str
    evidence_refs: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class UpdateBeliefRequest(BaseModel):
    """Request to update a belief"""
    proposition: Optional[str] = None
    confidence: Optional[str] = None
    confidence_value: Optional[float] = None
    evidence_refs: Optional[List[str]] = None


@router.post("/belief")
async def add_belief(request: AddBeliefRequest, _: None = Depends(require_permission("agent:execute"))):
    """Add a new belief to the belief state"""
    belief_state = get_or_create_belief_state(request.trace_id)

    belief_id = belief_state.add_belief(
        category=request.category,
        proposition=request.proposition,
        confidence=BeliefConfidence(request.confidence),
        confidence_value=request.confidence_value,
        source=BeliefSource(request.source),
        evidence_refs=request.evidence_refs,
        metadata=request.metadata,
    )

    return {"belief_id": belief_id, "trace_id": request.trace_id}


@router.get("/belief/{trace_id}")
async def get_belief_state_info(trace_id: str, _: None = Depends(require_permission("agent:read"))):
    """Get belief state for a trace"""
    belief_state = get_belief_state(trace_id)

    if not belief_state:
        return {"trace_id": trace_id, "exists": False}

    return belief_state.get_belief_summary()


@router.get("/belief/{trace_id}/beliefs")
async def get_beliefs(trace_id: str, category: Optional[str] = None, _: None = Depends(require_permission("agent:read"))):
    """Get beliefs for a trace"""
    belief_state = get_belief_state(trace_id)

    if not belief_state:
        return {"beliefs": []}

    if category:
        beliefs = belief_state.get_beliefs_by_category(category)
    else:
        beliefs = belief_state.get_all_beliefs()

    return {
        "beliefs": [
            {
                "id": b.id,
                "category": b.category,
                "proposition": b.proposition,
                "confidence": b.confidence.value,
                "confidence_value": b.confidence_value,
                "source": b.source.value,
                "evidence_refs": b.evidence_refs,
                "created_at": b.created_at,
                "updated_at": b.updated_at,
            }
            for b in beliefs
        ]
    }


@router.get("/belief/{trace_id}/conflicts")
async def resolve_belief_conflicts(trace_id: str, _: None = Depends(require_permission("agent:read"))):
    """Resolve conflicts in belief state"""
    belief_state = get_belief_state(trace_id)

    if not belief_state:
        return {"conflicts": []}

    conflicts = belief_state.resolve_conflicts()
    return {"conflicts": conflicts}


@router.get("/belief/{trace_id}/world-model")
async def get_world_model(trace_id: str, _: None = Depends(require_permission("agent:read"))):
    """Get world model for a trace"""
    belief_state = get_belief_state(trace_id)

    if not belief_state:
        return {"world_model": None}

    wm = belief_state.get_world_model()
    return {
        "world_model": {
            "robot_state": wm.robot_state,
            "environment_state": wm.environment_state,
            "task_progress": wm.task_progress,
            "last_update": wm.last_update,
        }
    }


@router.post("/belief/{trace_id}/world-model")
async def update_world_model(
    trace_id: str,
    robot_state: Optional[Dict[str, Any]] = None,
    environment_state: Optional[Dict[str, Any]] = None,
    task_progress: Optional[Dict[str, Any]] = None,
    _: None = Depends(require_permission("agent:execute")),
):
    """Update world model"""
    belief_state = get_or_create_belief_state(trace_id)

    belief_state.update_world_model(
        robot_state=robot_state,
        environment_state=environment_state,
        task_progress=task_progress,
    )

    return {"status": "updated", "trace_id": trace_id}


# ============ Evidence Collector Endpoints (Phase 2) ============

class CollectEvidenceRequest(BaseModel):
    """Request to collect evidence"""
    evidence_type: str
    trace_id: str
    step_id: Optional[str] = None
    content: Any
    collected_by: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@router.post("/evidence/v2/collect")
async def collect_evidence_v2(request: CollectEvidenceRequest, _: None = Depends(require_permission("agent:execute"))):
    """Collect evidence for an action"""
    evidence_id = evidence_collector.collect_evidence(
        evidence_type=EvidenceType(request.evidence_type),
        trace_id=request.trace_id,
        step_id=request.step_id,
        content=request.content,
        collected_by=request.collected_by,
        metadata=request.metadata,
    )

    return {"evidence_id": evidence_id, "status": "collected"}


@router.get("/evidence/v2/{trace_id}/summary")
async def get_evidence_summary(trace_id: str, _: None = Depends(require_permission("agent:read"))):
    """Get evidence summary for a trace"""
    return evidence_collector.get_evidence_summary(trace_id)


@router.get("/evidence/v2/{trace_id}/chain")
async def get_evidence_chain(trace_id: str, _: None = Depends(require_permission("agent:read"))):
    """Get evidence chain for a trace"""
    chain = evidence_collector.get_evidence_chain(trace_id)
    return {"trace_id": trace_id, "chain": chain}


@router.get("/evidence/v2/can-proceed/{action_type}")
async def can_proceed_with_evidence(action_type: str, trace_id: str, _: None = Depends(require_permission("agent:read"))):
    """Check if can proceed based on evidence collection"""
    allowed, reason = evidence_collector.can_proceed(action_type, trace_id)
    return {"allowed": allowed, "reason": reason}


@router.get("/evidence/v2/requirements/{action_type}")
async def get_evidence_requirements_v2(action_type: str, _: None = Depends(require_permission("agent:read"))):
    """Get evidence requirements for an action type"""
    requirements = evidence_collector.get_requirements(action_type)
    return {
        "action_type": action_type,
        "requirements": [
            {
                "type": r.type.value,
                "description": r.description,
                "required": r.required,
            }
            for r in requirements
        ]
    }


@router.post("/evidence/v2/{evidence_id}/validate")
async def validate_evidence(
    evidence_id: str,
    valid: bool,
    message: Optional[str] = None,
    _: None = Depends(require_permission("agent:execute")),
):
    """Validate evidence"""
    result = evidence_collector.validate_evidence(evidence_id, valid, message)
    return {"evidence_id": evidence_id, "validated": result}


# ============ Compensation Planner Endpoints (Phase 2) ============

class AnalyzeFailureRequest(BaseModel):
    """Request to analyze failure"""
    failure_type: str
    failure_message: str
    context: Dict[str, Any] = Field(default_factory=dict)


class GeneratePlanRequest(BaseModel):
    """Request to generate compensation plan"""
    failure_id: str
    preferred_strategy: Optional[str] = None


@router.post("/compensation/analyze")
async def analyze_failure(request: AnalyzeFailureRequest, _: None = Depends(require_permission("agent:execute"))):
    """Analyze a failure and determine root cause"""
    analysis = compensation_planner.analyze_failure(
        failure_type=request.failure_type,
        failure_message=request.failure_message,
        context=request.context,
    )

    return {
        "failure_id": analysis.failure_id,
        "failure_type": analysis.failure_type.value,
        "failure_message": analysis.failure_message,
        "root_cause": analysis.root_cause,
        "affected_steps": analysis.affected_steps,
        "severity": analysis.severity,
    }


@router.post("/compensation/plan")
async def generate_compensation_plan(request: GeneratePlanRequest, _: None = Depends(require_permission("agent:execute"))):
    """Generate compensation plan for a failure"""
    # Get failure from history
    failures = compensation_planner.get_failure_history()
    failure = next((f for f in failures if f.failure_id == request.failure_id), None)

    if not failure:
        raise HTTPException(status_code=404, detail="Failure not found")

    # Generate plan
    strategy = CompensationStrategy(request.preferred_strategy) if request.preferred_strategy else None
    plan = compensation_planner.generate_compensation_plan(failure, strategy)

    return {
        "plan_id": plan.plan_id,
        "failure_id": plan.failure_id,
        "status": plan.status,
        "strategy": plan.strategy.value,
        "actions": [
            {
                "action_id": a.action_id,
                "action_type": a.action_type.value,
                "description": a.description,
                "target_step_id": a.target_step_id,
                "estimated_duration_ms": a.estimated_duration_ms,
                "risk_level": a.risk_level,
            }
            for a in plan.actions
        ],
        "estimated_duration_ms": plan.estimated_duration_ms,
    }


@router.get("/compensation/plan/{plan_id}")
async def get_compensation_plan(plan_id: str, _: None = Depends(require_permission("agent:read"))):
    """Get compensation plan by ID"""
    plan = compensation_planner.get_plan(plan_id)

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    return {
        "plan_id": plan.plan_id,
        "failure_id": plan.failure_id,
        "status": plan.status,
        "strategy": plan.strategy.value,
        "actions": [
            {
                "action_id": a.action_id,
                "action_type": a.action_type.value,
                "description": a.description,
                "target_step_id": a.target_step_id,
                "estimated_duration_ms": a.estimated_duration_ms,
                "risk_level": a.risk_level,
            }
            for a in plan.actions
        ],
        "estimated_duration_ms": plan.estimated_duration_ms,
        "approved_by": plan.approved_by,
        "created_at": plan.created_at,
    }


@router.post("/compensation/plan/{plan_id}/approve")
async def approve_compensation_plan(
    plan_id: str,
    approved_by: str,
    _: None = Depends(require_permission("agent:execute")),
):
    """Approve a compensation plan"""
    success = compensation_planner.update_plan_status(plan_id, "approved", approved_by)

    if not success:
        raise HTTPException(status_code=404, detail="Plan not found")

    return {"plan_id": plan_id, "status": "approved", "approved_by": approved_by}


@router.post("/compensation/plan/{plan_id}/execute")
async def execute_compensation_plan(plan_id: str, _: None = Depends(require_permission("agent:execute"))):
    """Execute a compensation plan"""
    success = compensation_planner.update_plan_status(plan_id, "executing")

    if not success:
        raise HTTPException(status_code=404, detail="Plan not found")

    return {"plan_id": plan_id, "status": "executing"}


@router.post("/compensation/plan/{plan_id}/complete")
async def complete_compensation_plan(plan_id: str, _: None = Depends(require_permission("agent:execute"))):
    """Mark compensation plan as completed"""
    success = compensation_planner.update_plan_status(plan_id, "completed")

    if not success:
        raise HTTPException(status_code=404, detail="Plan not found")

    return {"plan_id": plan_id, "status": "completed"}


@router.get("/compensation/plans")
async def list_compensation_plans(status: Optional[str] = None, _: None = Depends(require_permission("agent:read"))):
    """List compensation plans"""
    if status:
        plans = compensation_planner.get_plans_by_status(status)
    else:
        # Return all plans
        plans = list(compensation_planner._plans.values())

    return {
        "plans": [
            {
                "plan_id": p.plan_id,
                "failure_id": p.failure_id,
                "status": p.status,
                "strategy": p.strategy.value,
                "estimated_duration_ms": p.estimated_duration_ms,
                "created_at": p.created_at,
            }
            for p in plans
        ]
    }


# ============ Approval Queue Endpoints (Phase 2) ============

class CreateApprovalRequest(BaseModel):
    """Request to create approval"""
    requester_id: str
    resource_type: str
    resource_id: str
    action: str
    reason: str
    priority: str = "normal"
    evidence_refs: Optional[List[str]] = None
    ttl_seconds: Optional[int] = None


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

# ============ Decision Replay and Recalculation Endpoints ============

from app.services.decision_recalculator import (
    DecisionRecalculator,
    DecisionType,
    RecalculationRequest,
)
from app.services.acceptance_metrics import (
    acceptance_metrics,
    MetricCategory,
    MetricStatus,
)
from app.services.system_monitor import (
    system_monitor,
    HealthStatus,
    AlertLevel,
)

# Import singleton
decision_recalculator = DecisionRecalculator()


class RecordDecisionRequest(BaseModel):
    """Request to record a decision"""
    decision_type: str
    trace_id: str
    input_context: Dict[str, Any]
    decision_result: Dict[str, Any]
    risk_level: str
    policy_rules_matched: List[str] = []
    approved_by: Optional[str] = None


class RecalculateDecisionRequest(BaseModel):
    """Request to recalculate a decision"""
    original_decision_id: str
    modified_params: Dict[str, Any] = {}
    include_diff: bool = True


@router.post("/replay/decision/record")
async def record_decision(request: RecordDecisionRequest, _: None = Depends(require_permission("agent:execute"))):
    """Record a decision for future replay"""
    try:
        decision_type = DecisionType(request.decision_type)
    except ValueError:
        decision_type = DecisionType.POLICY_EVALUATION

    decision_id = decision_recalculator.record_decision(
        decision_type=decision_type,
        trace_id=request.trace_id,
        input_context=request.input_context,
        decision_result=request.decision_result,
        risk_level=request.risk_level,
        policy_rules_matched=request.policy_rules_matched,
        approved_by=request.approved_by,
    )

    return {
        "decision_id": decision_id,
        "status": "recorded",
    }


@router.get("/replay/decision/{decision_id}")
async def get_decision(decision_id: str, _: None = Depends(require_permission("agent:read"))):
    """Get a recorded decision"""
    decision = decision_recalculator.get_decision(decision_id)

    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    return {
        "decision_id": decision.decision_id,
        "decision_type": decision.decision_type.value,
        "trace_id": decision.trace_id,
        "timestamp": decision.timestamp,
        "input_context": decision.input_context,
        "decision_result": decision.decision_result,
        "risk_level": decision.risk_level,
        "policy_rules_matched": decision.policy_rules_matched,
        "approved_by": decision.approved_by,
    }


@router.get("/replay/trace/{trace_id}/decisions")
async def get_trace_decisions(trace_id: str, _: None = Depends(require_permission("agent:read"))):
    """Get all decisions for a trace"""
    decisions = decision_recalculator.get_decisions_by_trace(trace_id)

    return {
        "trace_id": trace_id,
        "decisions": [
            {
                "decision_id": d.decision_id,
                "decision_type": d.decision_type.value,
                "timestamp": d.timestamp,
                "risk_level": d.risk_level,
            }
            for d in decisions
        ]
    }


@router.post("/replay/recalculate")
async def recalculate_decision(request: RecalculateDecisionRequest, _: None = Depends(require_permission("agent:execute"))):
    """Recalculate a decision with modified parameters"""
    recalc_request = RecalculationRequest(
        original_decision_id=request.original_decision_id,
        recalculation_type="whatif",
        modified_params=request.modified_params,
        include_diff=request.include_diff,
    )

    result = await decision_recalculator.recalculate(recalc_request)

    if result.status.value == "failed":
        raise HTTPException(status_code=400, detail=result.error)

    return {
        "request_id": result.request_id,
        "original_decision_id": result.original_decision.decision_id if result.original_decision else None,
        "status": result.status.value,
        "recalculated_result": result.recalculated_result,
        "diff": result.diff,
        "recalculated_at": result.recalculated_at,
    }


@router.get("/replay/recalculations")
async def get_recalculation_history(
    decision_id: Optional[str] = None,
    limit: int = 100,
    _: None = Depends(require_permission("agent:read")),
):
    """Get recalculation history"""
    results = decision_recalculator.get_recalculation_history(decision_id, limit)

    return {
        "recalculations": [
            {
                "request_id": r.request_id,
                "original_decision_id": r.original_decision.decision_id if r.original_decision else None,
                "status": r.status.value,
                "recalculated_at": r.recalculated_at,
                "error": r.error,
            }
            for r in results
        ]
    }


# V2: Enhanced Replay Endpoint with full trace
class ReplayTraceRequest(BaseModel):
    """Request to replay a full trace"""
    trace_id: str
    include_events: bool = True
    include_decisions: bool = True
    include_evidence: bool = True
    start_ts_ms: Optional[int] = None
    end_ts_ms: Optional[int] = None


@router.post("/replay/trace")
async def replay_trace(request: ReplayTraceRequest, _: None = Depends(require_permission("agent:execute"))):
    """Replay a full trace with all events, decisions, and evidence"""
    from app.services.orchestrator_v2 import orchestrator_v2

    # Get events from orchestrator
    events = []
    if request.include_events:
        events = orchestrator_v2.get_trace_events(request.trace_id)

    # Filter by time range if specified
    if request.start_ts_ms or request.end_ts_ms:
        events = [
            e for e in events
            if (not request.start_ts_ms or e.get("timestamp", 0) >= request.start_ts_ms)
            and (not request.end_ts_ms or e.get("timestamp", 0) <= request.end_ts_ms)
        ]

    # Get decisions
    decisions = []
    if request.include_decisions:
        decisions = decision_recalculator.get_decisions_by_trace(request.trace_id)

    # Get evidence chain
    from app.services.evidence_collector import evidence_collector
    evidence = {}
    if request.include_evidence:
        evidence = evidence_collector.get_evidence_summary(request.trace_id)

    return {
        "trace_id": request.trace_id,
        "events": events,
        "decisions": [
            {
                "decision_id": d.decision_id,
                "decision_type": d.decision_type.value,
                "timestamp": d.timestamp,
                "risk_level": d.risk_level,
                "decision_result": d.decision_result,
            }
            for d in decisions
        ],
        "evidence": evidence,
        "event_count": len(events),
        "decision_count": len(decisions),
    }


# ============ Acceptance Metrics Endpoints ============

class RecordMetricRequest(BaseModel):
    """Request to record a metric event"""
    metric_type: str
    entry_id: Optional[str] = None
    has_object_binding: bool = False
    is_replayable: bool = False
    is_unauthorized: bool = False


@router.post("/metrics/record")
async def record_metric_event(request: RecordMetricRequest, _: None = Depends(require_permission("agent:execute"))):
    """Record a metric event for acceptance tracking"""
    if request.metric_type == "write_request":
        acceptance_metrics.record_write_request(
            entry_id=request.entry_id or f"entry-{int(time.time() * 1000)}",
            has_object_binding=request.has_object_binding,
        )
    elif request.metric_type == "trace":
        acceptance_metrics.record_trace(
            trace_id=request.entry_id or f"trace-{int(time.time() * 1000)}",
            is_replayable=request.is_replayable,
        )
    elif request.metric_type == "unauthorized":
        acceptance_metrics.record_unauthorized_attempt(request.entry_id or "unknown")

    return {"status": "recorded"}


@router.get("/metrics")
async def get_current_metrics(_: None = Depends(require_permission("agent:read"))):
    """Get current metric values"""
    return {
        "metrics": [
            {
                "metric_id": m.metric_id,
                "name": m.name,
                "category": m.category.value,
                "target_value": m.target_value,
                "actual_value": m.actual_value,
                "status": m.status.value,
                "details": m.details,
            }
            for m in acceptance_metrics.get_metrics()
        ]
    }


@router.get("/metrics/{metric_id}")
async def get_specific_metric(metric_id: str, _: None = Depends(require_permission("agent:read"))):
    """Get specific metric"""
    metric = acceptance_metrics.get_metric(metric_id)

    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")

    return {
        "metric_id": metric.metric_id,
        "name": metric.name,
        "description": metric.description,
        "target_value": metric.target_value,
        "actual_value": metric.actual_value,
        "status": metric.status.value,
        "timestamp": metric.timestamp,
        "details": metric.details,
    }


@router.post("/metrics/report")
async def generate_acceptance_report(_: None = Depends(require_permission("agent:execute"))):
    """Generate acceptance report"""
    report = acceptance_metrics.generate_report()

    return {
        "report_id": report.report_id,
        "timestamp": report.timestamp,
        "total_metrics": report.total_metrics,
        "passed": report.passed,
        "failed": report.failed,
        "warnings": report.warnings,
        "recommendation": report.recommendation,
        "metrics": [
            {
                "metric_id": m.metric_id,
                "name": m.name,
                "target_value": m.target_value,
                "actual_value": m.actual_value,
                "status": m.status.value,
            }
            for m in report.metrics
        ],
    }


@router.get("/metrics/reports")
async def get_acceptance_reports(limit: int = 10, _: None = Depends(require_permission("agent:read"))):
    """Get acceptance report history"""
    reports = acceptance_metrics.get_reports(limit)

    return {
        "reports": [
            {
                "report_id": r.report_id,
                "timestamp": r.timestamp,
                "total_metrics": r.total_metrics,
                "passed": r.passed,
                "failed": r.failed,
                "warnings": r.warnings,
                "recommendation": r.recommendation,
            }
            for r in reports
        ]
    }


@router.post("/metrics/reset")
async def reset_metrics(_: None = Depends(require_permission("agent:execute"))):
    """Reset metric counters"""
    acceptance_metrics.reset_counters()
    return {"status": "counters_reset"}


# ============ System Monitoring Endpoints ============

@router.get("/monitor/health")
async def get_health_status(_: None = Depends(require_permission("agent:read"))):
    """Get system health status"""
    health = system_monitor.get_health_summary()
    return health


@router.get("/monitor/metrics")
async def get_system_metrics(_: None = Depends(require_permission("agent:read"))):
    """Get current system metrics"""
    metrics = system_monitor.get_system_metrics()
    return {
        "cpu_percent": metrics.cpu_percent,
        "memory_percent": metrics.memory_percent,
        "disk_percent": metrics.disk_percent,
        "network_sent": metrics.network_sent,
        "network_recv": metrics.network_recv,
        "timestamp": metrics.timestamp,
    }


@router.get("/monitor/metrics/history")
async def get_metrics_history(limit: int = 100, _: None = Depends(require_permission("agent:read"))):
    """Get metrics history"""
    history = system_monitor.get_metrics_history(limit)
    return {
        "metrics": [
            {
                "cpu_percent": m.cpu_percent,
                "memory_percent": m.memory_percent,
                "disk_percent": m.disk_percent,
                "timestamp": m.timestamp,
            }
            for m in history
        ]
    }


@router.get("/monitor/alerts")
async def get_alerts(level: Optional[str] = None, limit: int = 100, _: None = Depends(require_permission("agent:read"))):
    """Get system alerts"""
    alert_level = AlertLevel(level) if level else None
    alerts = system_monitor.get_alerts(alert_level, limit)

    return {
        "alerts": [
            {
                "alert_id": a.alert_id,
                "level": a.level.value,
                "component": a.component,
                "message": a.message,
                "created_at": a.created_at,
                "acknowledged": a.acknowledged,
            }
            for a in alerts
        ]
    }


@router.post("/monitor/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, _: None = Depends(require_permission("agent:execute"))):
    """Acknowledge an alert"""
    success = system_monitor.acknowledge_alert(alert_id)

    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {"alert_id": alert_id, "acknowledged": True}


@router.post("/monitor/alerts/clear")
async def clear_alerts(_: None = Depends(require_permission("agent:execute"))):
    """Clear acknowledged alerts"""
    system_monitor.clear_alerts()
    return {"status": "alerts_cleared"}


@router.get("/monitor/checks")
async def get_health_checks(_: None = Depends(require_permission("agent:read"))):
    """Get all health checks"""
    checks = system_monitor.run_all_health_checks()
    return {
        "checks": [
            {
                "component": c.component,
                "status": c.status.value,
                "message": c.message,
                "details": c.details,
                "timestamp": c.timestamp,
            }
            for c in checks
        ]
    }


# ============ P2-2: Evaluation Report Endpoints ============

class GenerateReportRequest(BaseModel):
    """Request to generate evaluation report"""
    task_id: int
    use_llm: bool = Field(default=True, description="Whether to use LLM for narrative")


class GenerateReportResponse(BaseModel):
    """Response for evaluation report generation"""
    report: LLMEvaluationReport
    bundle_id: Optional[str] = Field(default=None, description="Evidence bundle ID if saved")


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

from app.services.sop.quality_monitor import SOPQualityMonitor


class SOPQualityCheckRequest(BaseModel):
    """Request to check SOP quality"""
    sop_id: Optional[int] = Field(default=None, description="Specific SOP ID to check")
    time_range_days: int = Field(default=30, description="Time range in days")


class SOPQualityCheckResponse(BaseModel):
    """Response for SOP quality check"""
    alerts: List[Dict[str, Any]]
    tickets_created: List[Dict[str, Any]]


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

class GuidanceModeRequest(BaseModel):
    """Request to update guidance mode"""
    mode: str = Field(..., description="Guidance mode: full_time | on_demand | silent")


class UserPreferenceResponse(BaseModel):
    """User preference response"""
    user_id: int
    guidance_mode: str
    guidance_mode_display: str
    preferences: Dict[str, Any]


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
    pref = await service.get_or_create_preference(actor.user.id)

    return UserPreferenceResponse(
        user_id=pref.user_id,
        guidance_mode=pref.guidance_mode,
        guidance_mode_display=GuidanceMode.get_display_name(pref.guidance_mode),
        preferences=pref.preferences or {},
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
    pref = await service.update_guidance_mode(actor.user.id, request.mode)

    return UserPreferenceResponse(
        user_id=pref.user_id,
        guidance_mode=pref.guidance_mode,
        guidance_mode_display=GuidanceMode.get_display_name(pref.guidance_mode),
        preferences=pref.preferences or {},
    )
