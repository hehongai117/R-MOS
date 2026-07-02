"""
Agent API Endpoints
P0: Frontend integration for Agent services
"""

from fastapi import APIRouter, Depends, Request
from typing import Dict, Any
import uuid
import logging

from app.core.database import get_db
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
from app.services.orchestrator_v2 import orchestrator_v2
from app.services.authz_guard import require_permission
from app.schemas.agent import (
    CoachRecommendRequest,
    DiagnoseRequest,
    CoordinateRequest,
    AgentExecuteMode,
    AgentExecuteRequest,
    AgentExecuteResponse,
)
from app.api.v1.endpoints import agent_knowledge, agent_evidence, agent_v2, agent_governance
from app.api.v1.endpoints.agent_v2 import _require_agent_permission

# Re-export symbols that tests access via `agent_endpoints.<name>`
from app.services.knowledge_governance import knowledge_governance  # noqa: F401
from app.api.v1.endpoints.agent_knowledge import knowledge_upload_jobs  # noqa: F401

router = APIRouter(prefix="/agent", tags=["agent"])

router.include_router(agent_knowledge.router)
router.include_router(agent_evidence.router)
router.include_router(agent_v2.router)
router.include_router(agent_governance.router)


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
            # 注意：Command 模型的用户字段是 actor_user_id（非 user_id），且 trace_id 必填、
            # 无 input_text 列。此前误用 user_id/input_text 会在构造时抛 TypeError 被吞成 error。
            command = Command(
                trace_id=trace_id,
                actor_user_id=request.user_id,
                intent=command_payload["intent"],
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
