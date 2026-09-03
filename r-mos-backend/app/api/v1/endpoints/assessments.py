"""
Assessment provider and external assessment API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.ownership import ensure_role_for_write
from app.services.authz_guard import ActorContext, get_current_actor
from app.schemas.assessment import (
    AssessmentProviderCreate,
    AssessmentProviderUpdate,
    AssessmentProviderResponse,
    AssessmentProviderListResponse,
    ExternalAssessmentCreate,
    ExternalAssessmentResponse,
    ExternalAssessmentListResponse,
    AssessmentAuditTrail,
    AssessmentStatusChangeRequest,
    AssessmentStatus,
    AuditAction,
)
from app.services.assessment_service import AssessmentService

router = APIRouter()


@router.get("/assessment-providers", response_model=AssessmentProviderListResponse)
async def list_assessment_providers(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List assessment providers."""
    service = AssessmentService(db)
    return await service.list_providers(page=page, size=size)


@router.post("/assessment-providers", response_model=AssessmentProviderResponse, status_code=201)
async def create_assessment_provider(
    request: AssessmentProviderCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register an assessment provider."""
    service = AssessmentService(db)
    return await service.create_provider(request)


@router.get("/assessment-providers/{provider_id}", response_model=AssessmentProviderResponse)
async def get_assessment_provider(
    provider_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get provider details."""
    service = AssessmentService(db)
    provider = await service.get_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Assessment provider not found")
    return provider


@router.patch("/assessment-providers/{provider_id}", response_model=AssessmentProviderResponse)
async def update_assessment_provider(
    provider_id: str,
    request: AssessmentProviderUpdate,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """Update provider metadata."""
    # 董事会 2026-09-03 裁定：仅管理员。
    # 该对象无归属字段，无法做对象级校验；角色制为过渡方案（审计 M-01）。
    await ensure_role_for_write(
        db, http_request, actor, "admin",
        action="update_assessment_provider", resource_type="AssessmentProvider", resource_id=provider_id,
    )
    service = AssessmentService(db)
    provider = await service.update_provider(provider_id, request)
    if not provider:
        raise HTTPException(status_code=404, detail="Assessment provider not found")
    return provider


@router.get("/assessments", response_model=ExternalAssessmentListResponse)
async def list_assessments(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List external assessment references."""
    service = AssessmentService(db)
    return await service.list_assessments(page=page, size=size)


@router.post("/assessments", response_model=ExternalAssessmentResponse, status_code=201)
async def create_assessment(
    request: ExternalAssessmentCreate,
    db: AsyncSession = Depends(get_db),
):
    """Submit an assessment reference."""
    service = AssessmentService(db)
    assessment = await service.create_assessment(request)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment provider not found")
    return assessment


@router.get("/assessments/{assessment_id}", response_model=ExternalAssessmentResponse)
async def get_assessment(
    assessment_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get assessment reference details."""
    service = AssessmentService(db)
    assessment = await service.get_assessment(assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment


@router.get("/assessments/{assessment_id}/audit", response_model=AssessmentAuditTrail)
async def get_assessment_audit(
    assessment_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get assessment audit trail."""
    service = AssessmentService(db)
    audit = await service.get_audit_trail(assessment_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return audit


@router.post("/assessments/{assessment_id}/revoke", response_model=ExternalAssessmentResponse)
async def revoke_assessment(
    assessment_id: str,
    request: AssessmentStatusChangeRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """Revoke an assessment reference."""
    # 董事会 2026-09-03 裁定：仅管理员。
    # 该对象无归属字段，无法做对象级校验；角色制为过渡方案（审计 M-01）。
    await ensure_role_for_write(
        db, http_request, actor, "admin",
        action="revoke_assessment", resource_type="ExternalAssessment", resource_id=assessment_id,
    )
    service = AssessmentService(db)
    assessment = await service.change_assessment_status(
        assessment_id=assessment_id,
        new_status=AssessmentStatus.REVOKED,
        action=AuditAction.REVOKED,
        request=request,
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment


@router.post("/assessments/{assessment_id}/dispute", response_model=ExternalAssessmentResponse)
async def dispute_assessment(
    assessment_id: str,
    request: AssessmentStatusChangeRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """Dispute an assessment reference."""
    # 董事会 2026-09-03 裁定：教学内容 → 教师与管理员。
    # 该对象无归属字段，无法做对象级校验；角色制为过渡方案（审计 M-01）。
    await ensure_role_for_write(
        db, http_request, actor, "teacher", "admin",
        action="dispute_assessment", resource_type="ExternalAssessment", resource_id=assessment_id,
    )
    service = AssessmentService(db)
    assessment = await service.change_assessment_status(
        assessment_id=assessment_id,
        new_status=AssessmentStatus.DISPUTED,
        action=AuditAction.DISPUTED,
        request=request,
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment


@router.post("/assessments/{assessment_id}/reinstate", response_model=ExternalAssessmentResponse)
async def reinstate_assessment(
    assessment_id: str,
    request: AssessmentStatusChangeRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """Reinstate an assessment reference."""
    # 董事会 2026-09-03 裁定：仅管理员。
    # 该对象无归属字段，无法做对象级校验；角色制为过渡方案（审计 M-01）。
    await ensure_role_for_write(
        db, http_request, actor, "admin",
        action="reinstate_assessment", resource_type="ExternalAssessment", resource_id=assessment_id,
    )
    service = AssessmentService(db)
    assessment = await service.change_assessment_status(
        assessment_id=assessment_id,
        new_status=AssessmentStatus.ACTIVE,
        action=AuditAction.REINSTATED,
        request=request,
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment
