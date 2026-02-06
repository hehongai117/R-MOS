"""
Teaching domain API endpoints.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BusinessRuleViolation, ResourceNotFoundError
from app.models.evidence import EvidenceBundle
from app.models.teaching import EvidenceLink
from app.schemas.teaching import (
    GuidancePolicyCreate,
    GuidancePolicyResponse,
    ClassCreate,
    ClassResponse,
    CourseCreate,
    CourseResponse,
    EnrollmentCreate,
    EnrollmentResponse,
    AssignmentCreate,
    AssignmentResponse,
    AssignmentAttemptResponse,
    AttemptEvidenceResponse,
    DiagnosisReport,
)
from app.services.diagnosis_service import DiagnosisService, EvidenceFallbackError
from app.services.access_control import raise_read_access_denied, raise_write_access_denied
from app.services.teaching_service import TeachingService
from app.services.evidence_engine import EvidenceEngine


router = APIRouter()
logger = logging.getLogger(__name__)


class AttemptCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
    student_id: int
    task_id: Optional[int] = None


class AttemptStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
    status: str


class AttemptGradeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
    score: float


def _raise_business_error(exc: BusinessRuleViolation) -> None:
    raise exc


def _raise_not_found(exc: ResourceNotFoundError) -> None:
    raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/guidance-policies",
    response_model=List[GuidancePolicyResponse],
    response_model_by_alias=True,
)
async def list_guidance_policies(db: AsyncSession = Depends(get_db)):
    service = TeachingService(db)
    return await service.list_guidance_policies()


@router.post(
    "/guidance-policies",
    response_model=GuidancePolicyResponse,
    status_code=201,
    response_model_by_alias=True,
)
async def create_guidance_policy(
    request: GuidancePolicyCreate,
    db: AsyncSession = Depends(get_db),
):
    service = TeachingService(db)
    try:
        return await service.create_guidance_policy(**request.model_dump())
    except BusinessRuleViolation as exc:
        _raise_business_error(exc)


@router.get(
    "/guidance-policies/{policy_id}",
    response_model=GuidancePolicyResponse,
    response_model_by_alias=True,
)
async def get_guidance_policy(policy_id: int, db: AsyncSession = Depends(get_db)):
    service = TeachingService(db)
    try:
        return await service.get_guidance_policy(policy_id)
    except ResourceNotFoundError as exc:
        _raise_not_found(exc)


@router.get(
    "/classes",
    response_model=List[ClassResponse],
    response_model_by_alias=True,
)
async def list_classes(db: AsyncSession = Depends(get_db)):
    service = TeachingService(db)
    return await service.list_classes()


@router.post(
    "/classes",
    response_model=ClassResponse,
    status_code=201,
    response_model_by_alias=True,
)
async def create_class(request: ClassCreate, db: AsyncSession = Depends(get_db)):
    service = TeachingService(db)
    try:
        payload = request.model_dump()
        metadata = payload.pop("metadata_json", None)
        if metadata is not None:
            payload["metadata"] = metadata
        return await service.create_class(**payload)
    except BusinessRuleViolation as exc:
        _raise_business_error(exc)


@router.get(
    "/classes/{class_id}",
    response_model=ClassResponse,
    response_model_by_alias=True,
)
async def get_class(class_id: int, db: AsyncSession = Depends(get_db)):
    service = TeachingService(db)
    try:
        return await service.get_class(class_id)
    except ResourceNotFoundError as exc:
        _raise_not_found(exc)


@router.get(
    "/courses",
    response_model=List[CourseResponse],
    response_model_by_alias=True,
)
async def list_courses(
    class_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = TeachingService(db)
    return await service.list_courses(class_id=class_id)


@router.post(
    "/courses",
    response_model=CourseResponse,
    status_code=201,
    response_model_by_alias=True,
)
async def create_course(request: CourseCreate, db: AsyncSession = Depends(get_db)):
    service = TeachingService(db)
    try:
        payload = request.model_dump()
        metadata = payload.pop("metadata_json", None)
        if metadata is not None:
            payload["metadata"] = metadata
        return await service.create_course(**payload)
    except BusinessRuleViolation as exc:
        _raise_business_error(exc)
    except ResourceNotFoundError as exc:
        _raise_not_found(exc)


@router.get(
    "/courses/{course_id}",
    response_model=CourseResponse,
    response_model_by_alias=True,
)
async def get_course(course_id: int, db: AsyncSession = Depends(get_db)):
    service = TeachingService(db)
    try:
        return await service.get_course(course_id)
    except ResourceNotFoundError as exc:
        _raise_not_found(exc)


@router.get(
    "/enrollments",
    response_model=List[EnrollmentResponse],
    response_model_by_alias=True,
)
async def list_enrollments(
    class_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = TeachingService(db)
    return await service.list_enrollments(class_id=class_id)


@router.post(
    "/enrollments",
    response_model=EnrollmentResponse,
    status_code=201,
    response_model_by_alias=True,
)
async def enroll_student(request: EnrollmentCreate, db: AsyncSession = Depends(get_db)):
    service = TeachingService(db)
    try:
        return await service.enroll_student(**request.model_dump())
    except BusinessRuleViolation as exc:
        _raise_business_error(exc)
    except ResourceNotFoundError as exc:
        _raise_not_found(exc)


@router.get(
    "/assignments",
    response_model=List[AssignmentResponse],
    response_model_by_alias=True,
)
async def list_assignments(
    class_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = TeachingService(db)
    return await service.list_assignments(class_id=class_id)


@router.post(
    "/assignments",
    response_model=AssignmentResponse,
    status_code=201,
    response_model_by_alias=True,
)
async def create_assignment(
    payload: AssignmentCreate,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    x_rmos_role: Optional[str] = Header(default=None, alias="X-RMOS-Role"),
):
    if x_rmos_role and x_rmos_role.strip().lower() not in {"teacher", "admin"}:
        await raise_write_access_denied(
            db,
            http_request,
            action="permission_denied",
            resource_type="TeachingClass",
            resource_id=payload.class_id,
            reason="missing_role:teacher_or_admin",
            message="权限不足：仅teacher/admin可创建assignment",
        )

    service = TeachingService(db)
    try:
        return await service.create_assignment(**payload.model_dump())
    except BusinessRuleViolation as exc:
        _raise_business_error(exc)
    except ResourceNotFoundError as exc:
        _raise_not_found(exc)


@router.get(
    "/assignments/{assignment_id}",
    response_model=AssignmentResponse,
    response_model_by_alias=True,
)
async def get_assignment(assignment_id: int, db: AsyncSession = Depends(get_db)):
    service = TeachingService(db)
    try:
        return await service.get_assignment(assignment_id)
    except ResourceNotFoundError as exc:
        _raise_not_found(exc)


@router.get(
    "/assignments/{assignment_id}/attempts",
    response_model=List[AssignmentAttemptResponse],
    response_model_by_alias=True,
)
async def list_attempts(assignment_id: int, db: AsyncSession = Depends(get_db)):
    service = TeachingService(db)
    try:
        return await service.list_attempts(assignment_id=assignment_id)
    except ResourceNotFoundError as exc:
        _raise_not_found(exc)


@router.post(
    "/assignments/{assignment_id}/attempts",
    response_model=AssignmentAttemptResponse,
    status_code=201,
    response_model_by_alias=True,
)
async def create_attempt(
    assignment_id: int,
    request: AttemptCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    service = TeachingService(db)
    try:
        return await service.create_attempt(
            assignment_id=assignment_id,
            student_id=request.student_id,
            task_id=request.task_id,
        )
    except BusinessRuleViolation as exc:
        _raise_business_error(exc)
    except ResourceNotFoundError as exc:
        _raise_not_found(exc)


@router.get(
    "/attempts/{attempt_id}",
    response_model=AssignmentAttemptResponse,
    response_model_by_alias=True,
)
async def get_attempt(
    attempt_id: int,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    service = TeachingService(db)
    try:
        return await service.get_attempt(attempt_id)
    except ResourceNotFoundError as exc:
        await raise_read_access_denied(
            db,
            http_request,
            action="access_denied",
            resource_type=exc.resource_type,
            resource_id=exc.resource_id,
            reason="resource_not_found_or_access_denied",
            message="资源不存在",
        )


@router.patch(
    "/attempts/{attempt_id}",
    response_model=AssignmentAttemptResponse,
    response_model_by_alias=True,
)
async def update_attempt_status(
    attempt_id: int,
    request: AttemptStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    service = TeachingService(db)
    try:
        return await service.update_attempt_status(attempt_id, request.status)
    except BusinessRuleViolation as exc:
        _raise_business_error(exc)
    except ResourceNotFoundError as exc:
        _raise_not_found(exc)


@router.post(
    "/attempts/{attempt_id}/grade",
    response_model=AssignmentAttemptResponse,
    response_model_by_alias=True,
)
async def grade_attempt(
    attempt_id: int,
    request: AttemptGradeRequest,
    db: AsyncSession = Depends(get_db),
):
    service = TeachingService(db)
    try:
        return await service.grade_attempt(attempt_id, score=request.score)
    except BusinessRuleViolation as exc:
        _raise_business_error(exc)
    except ResourceNotFoundError as exc:
        _raise_not_found(exc)


@router.get(
    "/attempts/{attempt_id}/evidence",
    response_model=AttemptEvidenceResponse,
    response_model_by_alias=True,
)
async def get_attempt_evidence(
    attempt_id: int,
    db: AsyncSession = Depends(get_db),
):
    service = TeachingService(db)
    try:
        attempt = await service.get_attempt(attempt_id)
    except ResourceNotFoundError as exc:
        _raise_not_found(exc)

    async def load_latest_link() -> EvidenceLink | None:
        result = await db.execute(
            select(EvidenceLink)
            .where(EvidenceLink.attempt_id == attempt_id)
            .order_by(EvidenceLink.created_at.desc())
        )
        return result.scalars().first()

    link = await load_latest_link()
    if not link and attempt.task_id:
        try:
            engine = EvidenceEngine(db)
            await engine.generate_bundle_for_task(
                attempt.task_id,
                preferred_attempt_id=attempt_id,
            )
        except BusinessRuleViolation as exc:
            _raise_business_error(exc)
        link = await load_latest_link()

    if not link:
        if attempt.task_id is None:
            raise HTTPException(status_code=404, detail="attempt未关联task，无法生成证据")
        raise HTTPException(status_code=404, detail="证据关联不存在")

    bundle = await db.get(EvidenceBundle, link.bundle_id)
    if not bundle:
        raise HTTPException(status_code=500, detail="证据包不存在")

    return AttemptEvidenceResponse(
        bundle_id=bundle.id,
        task_id=link.task_id,
        attempt_id=attempt_id,
        summary=bundle.machine_tags,
    )


@router.get(
    "/attempts/{attempt_id}/diagnosis",
    response_model=DiagnosisReport,
    response_model_by_alias=True,
)
async def get_attempt_diagnosis(
    attempt_id: int,
    db: AsyncSession = Depends(get_db),
):
    service = DiagnosisService(db)
    try:
        return await service.get_diagnosis_report(attempt_id)
    except EvidenceFallbackError as exc:
        logger.error(
            "Diagnosis evidence fallback failed: attempt_id=%s task_id=%s",
            exc.attempt_id,
            exc.task_id,
        )
        raise HTTPException(status_code=500, detail="EVIDENCE_FALLBACK_FAILED")
    except ResourceNotFoundError as exc:
        _raise_not_found(exc)
