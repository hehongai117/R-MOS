"""
Agent API Endpoints
P0: Frontend integration for Agent services
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.services.agent_service import orchestrator, AgentRequest, AgentResponse
from app.services.coach_agent import coach_agent, CoachOutput
from app.services.diagnoser_agent import diagnoser_agent, DiagnoserOutput
from app.services.knowledge_governance import knowledge_governance
from app.services.multi_agent_coordinator import multi_agent_coordinator
from app.services.evidence_enforcement import evidence_enforcer, ACTION_EVIDENCE_REQUIREMENTS

router = APIRouter(prefix="/agent", tags=["agent"])


# ============ Request/Response Models ============

class AgentRequestModel(BaseModel):
    user_id: str
    message: str
    context: Dict[str, Any] = Field(default_factory=dict)


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


# ============ Agent Orchestrator Endpoints ============

@router.post("/request", response_model=Dict[str, Any])
async def send_agent_request(request: AgentRequestModel):
    """Process user request through agent pipeline"""
    agent_req = AgentRequest(
        user_id=request.user_id,
        message=request.message,
        context=request.context
    )

    response = orchestrator.process_request(agent_req)
    return {
        "response_id": response.response_id,
        "request_id": response.request_id,
        "message": response.message,
        "action_suggested": response.action_suggested,
        "confidence": response.confidence,
        "evidence_refs": response.evidence_refs,
    }


@router.get("/task-status/{user_id}")
async def get_task_status(user_id: str):
    """Get current task status for user"""
    status = orchestrator.get_task_status(user_id)
    return status


# ============ Coach Agent Endpoints ============

@router.post("/coach/recommend", response_model=Dict[str, Any])
async def get_coach_recommendation(request: CoachRecommendRequest):
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
async def diagnose_error(request: DiagnoseRequest):
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
async def search_knowledge(request: KnowledgeSearchRequest):
    """Search knowledge entries"""
    from app.services.knowledge_governance import KnowledgeStatus

    status = KnowledgeStatus.APPROVED if request.status == "APPROVED" else KnowledgeStatus.PENDING

    results = knowledge_governance.search_knowledge({
        "query": request.query,
        "device_model": request.device_model,
        "part_type": request.part_type,
        "status": status,
    })

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
async def create_knowledge(request: KnowledgeCreateRequest):
    """Create new knowledge entry"""
    from app.services.knowledge_governance import KnowledgeType, RiskLevel, Scope

    entry = knowledge_governance.create_knowledge(
        title=request.title,
        content=request.content,
        entry_type=KnowledgeType(request.type),
        creator_id="current_user",  # TODO: get from auth
        scope=Scope(**request.scope) if request.scope else None,
        risk_level=RiskLevel(request.risk_level),
    )

    return {
        "id": entry.id,
        "status": entry.status.value,
        "title": entry.title,
    }


@router.post("/knowledge/{entry_id}/submit")
async def submit_knowledge(entry_id: str):
    """Submit knowledge for review"""
    success, message = knowledge_governance.submit_for_review(entry_id)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"status": "submitted"}


@router.post("/knowledge/{entry_id}/approve")
async def approve_knowledge(entry_id: str, request: KnowledgeApproveRequest):
    """Approve or reject knowledge"""
    from app.services.knowledge_governance import ApprovalRequest

    success, message = knowledge_governance.approve_knowledge(
        ApprovalRequest(
            entry_id=entry_id,
            reviewer_id="current_user",  # TODO: get from auth
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
async def coordinate_agents(request: CoordinateRequest):
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
async def get_evidence_status(step_id: str):
    """Get evidence collection status for a step"""
    status = evidence_enforcer.get_evidence_status(step_id)
    return status


@router.post("/evidence/collect")
async def collect_evidence(request: EvidenceCollectRequest):
    """Record evidence collection"""
    evidence_enforcer.collect_evidence(
        step_id=request.step_id,
        evidence_id=request.evidence_id,
        evidence_type=request.evidence_type
    )
    return {"status": "collected"}


@router.get("/evidence/can-proceed/{step_id}")
async def can_proceed(step_id: str):
    """Check if can proceed to next step"""
    allowed, reason = evidence_enforcer.can_proceed(step_id)
    return {"allowed": allowed, "reason": reason}


# ============ Action Evidence Requirements ============

@router.get("/evidence/requirements/{action_type}")
async def get_evidence_requirements(action_type: str):
    """Get required evidence for an action type"""
    requirements = ACTION_EVIDENCE_REQUIREMENTS.get(action_type, [])
    return {"action_type": action_type, "requirements": [r.model_dump() for r in requirements]}
