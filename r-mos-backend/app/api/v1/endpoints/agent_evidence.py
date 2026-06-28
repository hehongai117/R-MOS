"""
Agent Evidence Sub-Router
/evidence/... routes extracted from agent.py (Phase 3 refactor).
Aggregated by agent.py via router.include_router(agent_evidence.router).
"""

from fastapi import APIRouter, Depends

from app.services.authz_guard import require_permission
from app.services.evidence_enforcement import evidence_enforcer, ACTION_EVIDENCE_REQUIREMENTS
from app.schemas.agent import EvidenceCollectRequest

router = APIRouter()


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
