"""
Agent Governance API Endpoints
Approval queue, user preferences, evaluation reports, SOP quality checks.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.authz_guard import ActorContext, get_current_actor, require_permission
from app.services.approval_queue import approval_queue, ApprovalPriority
from app.services.teaching.report_generator import ReportGenerator
from app.services.sop.quality_monitor import SOPQualityMonitor
from app.schemas.agent import (
    CreateApprovalRequest,
    GenerateReportRequest,
    GenerateReportResponse,
    SOPQualityCheckRequest,
    SOPQualityCheckResponse,
    GuidanceModeRequest,
    LLMPreferenceRequest,
    UserPreferenceResponse,
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


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
