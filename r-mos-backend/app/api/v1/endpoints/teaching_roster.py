"""
Teaching roster sub-router: classes / courses / enrollments / assignments / attempts.
Bare APIRouter (no prefix) — paths written in full.
"""
import logging
from datetime import datetime, timezone
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BusinessRuleViolation, ResourceNotFoundError
from app.models.evidence import EvidenceBundle
from app.models.timeline import AlignmentMap, EvidenceCard, MultimodalTimeline, TimelineSegment
from app.models.teaching import Assignment, Enrollment, EvidenceLink, TeachingClass
from app.schemas.teaching import (
    ClassCreate,
    ClassResponse,
    ClassUpdateRequest,
    CourseCreate,
    CourseResponse,
    EnrollmentCreate,
    EnrollmentResponse,
    AssignmentCreate,
    AssignmentResponse,
    AssignmentAttemptResponse,
    AttemptCreateRequest,
    AttemptStatusUpdateRequest,
    AttemptGradeRequest,
    AttemptEvidenceResponse,
    AttemptReplayResponse,
    EvidenceCardCreate,
    EvidenceCardReference,
    EvidenceCardResponse,
    DiagnosisReport,
    ReplayEvidenceRef,
    ReplayFailurePoint,
    ReplaySupplementItem,
)
from app.services.diagnosis_service import DiagnosisService, EvidenceFallbackError
from app.services.access_control import (
    log_allow_event,
    raise_read_access_denied,
    raise_write_access_denied,
)
from app.services.teaching_service import TeachingService
from app.services.evidence_engine import EvidenceEngine
from app.api.v1.endpoints.teaching_common import (
    _raise_business_error,
    _raise_not_found,
    _parse_user_id,
    _to_int_or_none,
)

router = APIRouter()
logger = logging.getLogger(__name__)


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
async def get_class(
    class_id: int,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    x_rmos_role: Optional[str] = Header(default=None, alias="X-RMOS-Role"),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-ID"),
):
    service = TeachingService(db)
    try:
        teaching_class = await service.get_class(class_id)
    except ResourceNotFoundError as exc:
        _raise_not_found(exc)

    role = (x_rmos_role or "").strip().lower()
    if role == "student":
        actor_student_id = _parse_user_id(x_user_id)
        if actor_student_id is None:
            await raise_read_access_denied(
                db,
                http_request,
                action="read_access_denied",
                resource_type="TeachingClass",
                resource_id=teaching_class.id,
                reason="invalid_actor_student_id",
                message="资源不存在",
            )

        enrollment_result = await db.execute(
            select(Enrollment.id).where(
                Enrollment.class_id == teaching_class.id,
                Enrollment.student_id == actor_student_id,
            )
        )
        if enrollment_result.scalar_one_or_none() is None:
            await raise_read_access_denied(
                db,
                http_request,
                action="read_access_denied",
                resource_type="TeachingClass",
                resource_id=teaching_class.id,
                reason="student_class_scope_mismatch",
                message="资源不存在",
            )

    return teaching_class


@router.patch(
    "/classes/{class_id}",
    response_model=ClassResponse,
    response_model_by_alias=True,
)
async def update_class(
    class_id: int,
    request: ClassUpdateRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    x_rmos_role: Optional[str] = Header(default=None, alias="X-RMOS-Role"),
):
    service = TeachingService(db)
    try:
        teaching_class = await service.get_class(class_id)
    except ResourceNotFoundError as exc:
        _raise_not_found(exc)

    if x_rmos_role and x_rmos_role.strip().lower() not in {"teacher", "admin"}:
        await raise_write_access_denied(
            db,
            http_request,
            action="permission_denied",
            resource_type="TeachingClass",
            resource_id=teaching_class.id,
            reason="missing_role:teacher_or_admin",
            message="权限不足：仅teacher/admin可修改class",
        )

    payload = request.model_dump(exclude_unset=True)
    metadata = payload.pop("metadata_json", None)
    if metadata is not None:
        payload["metadata"] = metadata
    try:
        return await service.update_class(class_id, **payload)
    except BusinessRuleViolation as exc:
        _raise_business_error(exc)
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
    x_rmos_role: Optional[str] = Header(default=None, alias="X-RMOS-Role"),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-ID"),
):
    service = TeachingService(db)
    attempt = await service.get_attempt(attempt_id)

    role = (x_rmos_role or "").strip().lower()
    if role == "student":
        actor_student_id = _parse_user_id(x_user_id)
        if actor_student_id is None or actor_student_id != attempt.student_id:
            await raise_read_access_denied(
                db,
                http_request,
                action="read_access_denied",
                resource_type="AssignmentAttempt",
                resource_id=attempt.id,
                reason="student_attempt_scope_mismatch",
                message="资源不存在",
            )

    return attempt


@router.get(
    "/teaching/attempts/{attempt_id}/replay",
    response_model=AttemptReplayResponse,
    response_model_by_alias=True,
)
async def get_attempt_replay(
    attempt_id: int,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    x_rmos_role: Optional[str] = Header(default=None, alias="X-RMOS-Role"),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-ID"),
):
    service = TeachingService(db)
    attempt = await service.get_attempt(attempt_id)

    role = (x_rmos_role or "").strip().lower()
    actor_user_id = _parse_user_id(x_user_id)
    if role == "student":
        if actor_user_id is None or actor_user_id != attempt.student_id:
            await raise_read_access_denied(
                db,
                http_request,
                action="access_denied",
                resource_type="AssignmentAttempt",
                resource_id=attempt.id,
                reason="student_attempt_scope_mismatch",
                message="资源不存在",
            )
    elif role == "teacher":
        if actor_user_id is None:
            await raise_read_access_denied(
                db,
                http_request,
                action="access_denied",
                resource_type="AssignmentAttempt",
                resource_id=attempt.id,
                reason="invalid_actor_teacher_id",
                message="资源不存在",
            )
        teacher_result = await db.execute(
            select(TeachingClass.teacher_id)
            .join(Assignment, Assignment.class_id == TeachingClass.id)
            .where(Assignment.id == attempt.assignment_id)
        )
        class_teacher_id = teacher_result.scalar_one_or_none()
        if class_teacher_id is None or class_teacher_id != actor_user_id:
            await raise_read_access_denied(
                db,
                http_request,
                action="access_denied",
                resource_type="AssignmentAttempt",
                resource_id=attempt.id,
                reason="teacher_course_scope_mismatch",
                message="资源不存在",
            )

    timeline_result = await db.execute(
        select(MultimodalTimeline)
        .where(
            MultimodalTimeline.scope_type == "attempt",
            MultimodalTimeline.scope_id == str(attempt.id),
        )
        .order_by(MultimodalTimeline.id.desc())
    )
    timeline = timeline_result.scalars().first()

    if timeline is None:
        await log_allow_event(
            db,
            http_request,
            action="replay_requested",
            actor_user_id=str(actor_user_id) if actor_user_id is not None else None,
            resource_type="AssignmentAttempt",
            resource_id=attempt.id,
            reason="replay_insufficient_data",
        )
        return AttemptReplayResponse(
            attempt_id=attempt.id,
            status="insufficient_data",
            failure_point=ReplayFailurePoint(failure_type="insufficient_data"),
            supplement_plan=[
                ReplaySupplementItem(
                    data_type="timeline",
                    reason="missing_timeline_segments",
                )
            ],
            evidence_refs=[],
        )

    segment_result = await db.execute(
        select(TimelineSegment)
        .where(TimelineSegment.timeline_id == timeline.id)
        .order_by(TimelineSegment.start_ts_ms.asc(), TimelineSegment.id.asc())
    )
    segments = segment_result.scalars().all()
    if not segments:
        await log_allow_event(
            db,
            http_request,
            action="replay_requested",
            actor_user_id=str(actor_user_id) if actor_user_id is not None else None,
            resource_type="AssignmentAttempt",
            resource_id=attempt.id,
            reason="replay_insufficient_data",
        )
        return AttemptReplayResponse(
            attempt_id=attempt.id,
            status="insufficient_data",
            failure_point=ReplayFailurePoint(failure_type="insufficient_data"),
            supplement_plan=[
                ReplaySupplementItem(
                    data_type="timeline_segment",
                    reason="missing_timeline_segments",
                )
            ],
            evidence_refs=[],
        )

    alignment_result = await db.execute(
        select(AlignmentMap).where(AlignmentMap.timeline_id == timeline.id)
    )
    alignments = alignment_result.scalars().all()
    aligned_segment_ids = {row.segment_id for row in alignments}

    evidence_refs: list[ReplayEvidenceRef] = []
    for segment in segments:
        if segment.id not in aligned_segment_ids:
            continue
        if not segment.ref_id:
            continue
        evidence_refs.append(
            ReplayEvidenceRef(
                ref_id=segment.ref_id,
                timeline_id=timeline.id,
                segment_id=segment.id,
                start_ts_ms=segment.start_ts_ms,
                end_ts_ms=segment.end_ts_ms,
            )
        )

    first_payload = segments[0].payload if isinstance(segments[0].payload, dict) else {}
    failure_point = ReplayFailurePoint(
        step_id=_to_int_or_none(first_payload.get("step_id")),
        event_id=_to_int_or_none(first_payload.get("event_id")),
        failure_type=str(first_payload.get("failure_type") or "unknown"),
        rule_hit=str(first_payload.get("rule_hit")) if first_payload.get("rule_hit") is not None else None,
    )

    status = "ok" if evidence_refs else "insufficient_data"
    supplement_plan = (
        []
        if evidence_refs
        else [
            ReplaySupplementItem(
                data_type="evidence_ref",
                reason="missing_replayable_refs",
            )
        ]
    )

    await log_allow_event(
        db,
        http_request,
        action="replay_requested",
        actor_user_id=str(actor_user_id) if actor_user_id is not None else None,
        resource_type="AssignmentAttempt",
        resource_id=attempt.id,
        reason="replay_success" if status == "ok" else "replay_insufficient_data",
    )

    return AttemptReplayResponse(
        attempt_id=attempt.id,
        status=status,
        failure_point=failure_point,
        supplement_plan=supplement_plan,
        evidence_refs=evidence_refs,
    )


@router.post(
    "/evidence_cards",
    response_model=EvidenceCardResponse,
    status_code=201,
    response_model_by_alias=True,
)
async def create_evidence_card(
    request: EvidenceCardCreate,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    x_rmos_role: Optional[str] = Header(default=None, alias="X-RMOS-Role"),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-ID"),
):
    service = TeachingService(db)
    try:
        attempt = await service.get_attempt(request.attempt_id)
    except ResourceNotFoundError as exc:
        _raise_not_found(exc)

    role = (x_rmos_role or "").strip().lower()
    actor_user_id = _parse_user_id(x_user_id)
    if role == "teacher":
        if actor_user_id is None:
            await raise_write_access_denied(
                db,
                http_request,
                action="write_access_denied",
                resource_type="AssignmentAttempt",
                resource_id=attempt.id,
                reason="invalid_actor_teacher_id",
                message="权限不足",
            )
        teacher_result = await db.execute(
            select(TeachingClass.teacher_id)
            .join(Assignment, Assignment.class_id == TeachingClass.id)
            .where(Assignment.id == attempt.assignment_id)
        )
        class_teacher_id = teacher_result.scalar_one_or_none()
        if class_teacher_id is None or class_teacher_id != actor_user_id:
            await raise_write_access_denied(
                db,
                http_request,
                action="write_access_denied",
                resource_type="AssignmentAttempt",
                resource_id=attempt.id,
                reason="teacher_attempt_scope_mismatch",
                message="权限不足",
            )
    elif role != "admin":
        await raise_write_access_denied(
            db,
            http_request,
            action="write_access_denied",
            resource_type="AssignmentAttempt",
            resource_id=attempt.id,
            reason="missing_role:teacher_or_admin",
            message="权限不足",
        )

    timeline_result = await db.execute(
        select(MultimodalTimeline)
        .where(
            MultimodalTimeline.scope_type == "attempt",
            MultimodalTimeline.scope_id == str(attempt.id),
        )
        .order_by(MultimodalTimeline.id.desc())
    )
    timeline = timeline_result.scalars().first()
    if timeline is None:
        raise BusinessRuleViolation(
            message="缺乏可回放时间轴，无法生成证据卡片",
            code="TIMELINE_007_MISSING_TIMELINE",
        )

    segment_result = await db.execute(
        select(TimelineSegment)
        .where(
            TimelineSegment.timeline_id == timeline.id,
            TimelineSegment.segment_type.in_(["event", "log", "snapshot"]),
            TimelineSegment.ref_id.isnot(None),
        )
        .order_by(TimelineSegment.start_ts_ms.asc(), TimelineSegment.id.asc())
    )
    segments = segment_result.scalars().all()
    if not segments:
        raise BusinessRuleViolation(
            message="缺乏可回放引用，无法生成证据卡片",
            code="TIMELINE_007_MISSING_REFERENCES",
        )

    references_json: list[dict[str, Any]] = []
    for segment in segments:
        payload = segment.payload if isinstance(segment.payload, dict) else {}
        snippet_value = payload.get("snippet") or payload.get("summary") or payload.get("message")
        references_json.append(
            {
                "type": segment.segment_type,
                "ref_id": segment.ref_id,
                "snippet": str(snippet_value) if snippet_value is not None else None,
                "timestamp_ms": segment.start_ts_ms,
                "timeline_id": timeline.id,
                "segment_id": segment.id,
            }
        )

    evidence_card = EvidenceCard(
        attempt_id=attempt.id,
        card_type=request.card_type,
        title=f"{request.card_type} 证据卡片",
        summary="基于时间轴日志/事件/快照聚合生成",
        timestamp=datetime.now(timezone.utc),
        references=references_json,
        media_preview={},
    )
    db.add(evidence_card)
    await db.commit()
    await db.refresh(evidence_card)

    await log_allow_event(
        db,
        http_request,
        action="evidence_card_created",
        actor_user_id=str(actor_user_id) if actor_user_id is not None else None,
        resource_type="EvidenceCard",
        resource_id=evidence_card.id,
        reason="timeline_refs_aggregated",
    )

    return EvidenceCardResponse(
        evidence_card_id=evidence_card.id,
        attempt_id=evidence_card.attempt_id,
        card_type=evidence_card.card_type,
        title=evidence_card.title,
        summary=evidence_card.summary,
        timestamp=evidence_card.timestamp,
        references=[EvidenceCardReference(**item) for item in references_json],
        media_preview=evidence_card.media_preview or {},
        created_at=evidence_card.created_at,
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
        # attempt 未关联 task（task_id 为空）不是服务器故障，而是"无诊断可用"的数据状态 → 404；
        # 仅当有 task 却仍无法生成证据时才是真正的 500。
        if exc.task_id is None:
            raise HTTPException(status_code=404, detail="该测评暂无可用诊断（未关联任务）")
        logger.error(
            "Diagnosis evidence fallback failed: attempt_id=%s task_id=%s",
            exc.attempt_id,
            exc.task_id,
        )
        raise HTTPException(status_code=500, detail="EVIDENCE_FALLBACK_FAILED")
    except ResourceNotFoundError as exc:
        _raise_not_found(exc)
