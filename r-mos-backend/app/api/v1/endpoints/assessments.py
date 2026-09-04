"""
Assessment provider and external assessment API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.ownership import ensure_role_for_write, ensure_write_owner
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
from app.models.assessment import ExternalAssessment
from app.services.assessment_service import AssessmentService

router = APIRouter()


async def _load_assessment_or_404(db: AsyncSession, assessment_id: str) -> ExternalAssessment:
    """取外部评估记录供归属校验；不存在则 404（与守卫的 403 区分开）。"""
    assessment = await db.get(ExternalAssessment, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return assessment



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
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """Register an assessment provider."""
    # 审计 M-01 / 裁定 §9-2：此前无身份注入；建者即所有者。
    # 机构登记属治理动作，维持 admin-only（与 update_assessment_provider 一致）。
    await ensure_role_for_write(
        db, http_request, actor, "admin",
        action="create_assessment_provider", resource_type="AssessmentProvider",
    )
    service = AssessmentService(db)
    return await service.create_provider(
        request,
        created_by_user_id=actor.user_id,
        school_name=actor.school_name,
    )


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
    # 裁定 §9-2 补齐归属字段后**此处维持 admin-only**：撤销/恢复评估记录与
    # 变更机构元数据是治理动作，其授权依据是职权而非「谁建的」，
    # 归属字段的存在不改变结论。此项因此**不是**待放宽的过渡状态。
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
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """Submit an assessment reference."""
    # 审计 M-01 / 裁定 §9-2：此前无身份注入；录入者即所有者，
    # 后续 dispute 由 `ensure_write_owner` 按此归属判定。
    await ensure_role_for_write(
        db, http_request, actor, "teacher", "admin",
        action="create_assessment", resource_type="ExternalAssessment",
    )
    service = AssessmentService(db)
    assessment = await service.create_assessment(
        request,
        created_by_user_id=actor.user_id,
        school_name=actor.school_name,
    )
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
    # 裁定 §9-2 补齐归属字段后**此处维持 admin-only**：撤销/恢复评估记录与
    # 变更机构元数据是治理动作，其授权依据是职权而非「谁建的」，
    # 归属字段的存在不改变结论。此项因此**不是**待放宽的过渡状态。
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
    # 审计 M-01 / 裁定 §9-2：归属字段已补齐，由角色制过渡改为对象级校验。
    # 此处 `created_by_user_id` 语义为「谁录入了这份外部评估」；
    # 历史行为 NULL＝系统内置内容，仅管理员可改。
    assessment_obj = await _load_assessment_or_404(db, assessment_id)
    await ensure_write_owner(
        db, http_request, actor, assessment_obj.created_by_user_id,
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
    # 裁定 §9-2 补齐归属字段后**此处维持 admin-only**：撤销/恢复评估记录与
    # 变更机构元数据是治理动作，其授权依据是职权而非「谁建的」，
    # 归属字段的存在不改变结论。此项因此**不是**待放宽的过渡状态。
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
