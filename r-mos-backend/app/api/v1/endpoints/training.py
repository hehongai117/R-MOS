"""
UF-04, UF-06: Training API Endpoints
训练项目与会话管理接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import logging

from app.core.database import get_db
from app.models.audit_event import AuditEvent
from app.services.training.session_service import SessionService
from app.services.training.submission_service import SubmissionService
from app.services.training.feedback_generator import FeedbackGenerator, FeedbackRole
from app.services.identity.class_membership import ClassMembershipService
from app.services.memory.skill_profile_service import SkillProfileService
from app.models.training_submission import TrainingSubmission
from app.schemas.training_workbench import (
    SessionCreateRequest, SessionResponse, StepRecordResponse,
    StepUpdateRequest, SessionDetailResponse, SubmitSessionRequest,
    ForceSubmitSessionRequest, SubmitSessionResponse,
    SkillProfileResponse, WeakStepResponse, FeedbackResponse,
)
from app.api.v1.endpoints import training_workbench

logger = logging.getLogger(__name__)

router = APIRouter()

router.include_router(training_workbench.router)


# ============ UF-06: Session Routes ============

@router.post(
    "/training/sessions",
    response_model=SessionResponse,
    tags=["Training"]
)
async def create_session(
    request: SessionCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """UF-06-b-1: 创建训练会话"""
    service = SessionService(db)
    session_id = await service.create_session(
        user_id=request.user_id,
        project_id=request.project_id,
        project_snapshot=request.project_snapshot,
        ab_group=request.ab_group,
    )

    # 获取创建后的会话
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=500, detail="Failed to create session")

    return SessionResponse(
        session_id=session.session_id,
        project_id=session.project_id,
        user_id=session.user_id,
        status=session.status,
        current_step=session.current_step,
        score=session.score,
        total_duration=session.total_duration,
        submit_type=session.submit_type,
        started_at=session.started_at,
        paused_at=session.paused_at,
        submitted_at=session.submitted_at,
        project_snapshot=session.project_snapshot,
    )


@router.get(
    "/training/sessions/{session_id}",
    response_model=SessionResponse,
    tags=["Training"]
)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """UF-06-b-3: 获取会话状态"""
    service = SessionService(db)
    session = await service.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse(
        session_id=session.session_id,
        project_id=session.project_id,
        user_id=session.user_id,
        status=session.status,
        current_step=session.current_step,
        score=session.score,
        total_duration=session.total_duration,
        submit_type=session.submit_type,
        started_at=session.started_at,
        paused_at=session.paused_at,
        submitted_at=session.submitted_at,
        project_snapshot=session.project_snapshot,
    )


@router.get(
    "/training/sessions/{session_id}/detail",
    response_model=SessionDetailResponse,
    tags=["Training"]
)
async def get_session_detail(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """UF-06-b-3: 获取会话详情（含步骤记录）"""
    service = SessionService(db)
    result = await service.get_session_with_steps(session_id)

    if not result:
        raise HTTPException(status_code=404, detail="Session not found")

    session = result["session"]
    steps = result["steps"]

    return SessionDetailResponse(
        session=SessionResponse(
            session_id=session.session_id,
            project_id=session.project_id,
            user_id=session.user_id,
            status=session.status,
            current_step=session.current_step,
            score=session.score,
            total_duration=session.total_duration,
            submit_type=session.submit_type,
            started_at=session.started_at,
            paused_at=session.paused_at,
            submitted_at=session.submitted_at,
            project_snapshot=session.project_snapshot,
        ),
        steps=[
            StepRecordResponse(
                record_id=s.record_id,
                session_id=s.session_id,
                step_id=s.step_id,
                step_index=s.step_index,
                status=s.status,
                attempt_count=s.attempt_count,
                duration_sec=s.duration_sec,
                tools_confirmed=s.tools_confirmed,
                evidence=s.evidence,
                verdict_result=s.verdict_result,
                started_at=s.started_at,
                completed_at=s.completed_at,
            )
            for s in steps
        ],
    )


@router.patch(
    "/training/sessions/{session_id}/pause",
    response_model=SessionResponse,
    tags=["Training"]
)
async def pause_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """UF-06-b-1: 暂停会话"""
    service = SessionService(db)
    session = await service.pause(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse(
        session_id=session.session_id,
        project_id=session.project_id,
        user_id=session.user_id,
        status=session.status,
        current_step=session.current_step,
        score=session.score,
        total_duration=session.total_duration,
        submit_type=session.submit_type,
        started_at=session.started_at,
        paused_at=session.paused_at,
        submitted_at=session.submitted_at,
        project_snapshot=session.project_snapshot,
    )


@router.patch(
    "/training/sessions/{session_id}/resume",
    response_model=SessionResponse,
    tags=["Training"]
)
async def resume_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """UF-06-b-1: 恢复会话"""
    service = SessionService(db)
    session = await service.resume(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse(
        session_id=session.session_id,
        project_id=session.project_id,
        user_id=session.user_id,
        status=session.status,
        current_step=session.current_step,
        score=session.score,
        total_duration=session.total_duration,
        submit_type=session.submit_type,
        started_at=session.started_at,
        paused_at=session.paused_at,
        submitted_at=session.submitted_at,
        project_snapshot=session.project_snapshot,
    )


@router.patch(
    "/training/sessions/{session_id}/abandon",
    tags=["Training"]
)
async def abandon_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """UF-06-c-4: 放弃会话"""
    service = SessionService(db)
    success = await service.abandon(session_id)

    if not success:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"message": "Session abandoned", "session_id": session_id}


@router.post(
    "/training/sessions/{session_id}/submit",
    response_model=SubmitSessionResponse,
    tags=["Training"]
)
async def submit_session(
    session_id: str,
    request: SubmitSessionRequest,
    db: AsyncSession = Depends(get_db)
):
    """UF-08: 手动提交训练（走 SubmissionService）"""
    service = SubmissionService(db)

    check_result = await service.check_submit_ready(session_id)
    if not check_result.can_submit:
        if check_result.message == "会话不存在":
            raise HTTPException(status_code=404, detail="Session not found")
        raise HTTPException(status_code=400, detail=check_result.message)

    if check_result.incomplete_steps and not request.confirm_incomplete:
        raise HTTPException(
            status_code=409,
            detail={
                "message": check_result.message,
                "incomplete_steps": check_result.incomplete_steps,
                "requires_confirmation": True,
            },
        )

    submission = await service.submit_manual(
        session_id=session_id,
        user_id=request.user_id,
        confirm_incomplete=request.confirm_incomplete,
    )

    if not submission:
        raise HTTPException(status_code=400, detail="Submit failed")

    return SubmitSessionResponse(
        submission_id=submission.submission_id,
        session_id=submission.session_id,
        user_id=submission.user_id,
        submit_type=submission.submit_type,
        score=submission.payload.get("score"),
    )


@router.post(
    "/training/sessions/{session_id}/force-submit",
    response_model=SubmitSessionResponse,
    tags=["Training"],
)
async def force_submit_session(
    session_id: str,
    request: ForceSubmitSessionRequest,
    db: AsyncSession = Depends(get_db),
):
    """教师强制提交训练（需 teacher 对 student 有班级管辖权）。"""
    session_service = SessionService(db)
    training_session = await session_service.get_session(session_id)
    if not training_session:
        raise HTTPException(status_code=404, detail="Session not found")

    membership_service = ClassMembershipService(db)
    has_scope = await membership_service.teacher_has_student_scope(
        teacher_id=request.teacher_id,
        student_id=training_session.user_id,
    )
    if not has_scope:
        raise HTTPException(status_code=403, detail="Teacher has no scope for this student")

    submission_service = SubmissionService(db)
    submission = await submission_service.submit_by_teacher(
        session_id=session_id,
        teacher_id=request.teacher_id,
    )
    if not submission:
        raise HTTPException(status_code=400, detail="Force submit failed")

    db.add(
        AuditEvent(
            actor_user_id=str(request.teacher_id),
            action="student_notified",
            resource_type="TrainingSession",
            resource_id=session_id,
            decision="allow",
            reason="teacher_force_submit",
            request_meta={"student_user_id": training_session.user_id},
        )
    )
    await db.commit()

    return SubmitSessionResponse(
        submission_id=submission.submission_id,
        session_id=submission.session_id,
        user_id=submission.user_id,
        submit_type=submission.submit_type,
        score=submission.payload.get("score"),
    )


@router.post(
    "/training/sessions/{session_id}/steps",
    tags=["Training"]
)
async def update_step(
    session_id: str,
    request: StepUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """UF-06-b-2: 更新步骤记录"""
    service = SessionService(db)

    record_id = await service.update_step(
        session_id=session_id,
        step_id=request.step_id,
        step_index=request.step_index,
        status=request.status,
        attempt_count=request.attempt_count,
        tools_confirmed=request.tools_confirmed,
        evidence=request.evidence,
        verdict_result=request.verdict_result,
        duration_sec=request.duration_sec,
    )

    return {"record_id": record_id, "session_id": session_id}


@router.get(
    "/training/sessions/{session_id}/steps",
    response_model=List[StepRecordResponse],
    tags=["Training"]
)
async def get_step_records(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """UF-06-b-3: 获取步骤记录列表"""
    service = SessionService(db)
    result = await service.get_session_with_steps(session_id)

    if not result:
        raise HTTPException(status_code=404, detail="Session not found")

    steps = result["steps"]
    return [
        StepRecordResponse(
            record_id=s.record_id,
            session_id=s.session_id,
            step_id=s.step_id,
            step_index=s.step_index,
            status=s.status,
            attempt_count=s.attempt_count,
            duration_sec=s.duration_sec,
            tools_confirmed=s.tools_confirmed,
            evidence=s.evidence,
            verdict_result=s.verdict_result,
            started_at=s.started_at,
            completed_at=s.completed_at,
        )
        for s in steps
    ]


@router.get(
    "/training/users/{user_id}/sessions",
    response_model=List[SessionResponse],
    tags=["Training"]
)
async def get_user_sessions(
    user_id: int,
    status: Optional[str] = None,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """获取用户会话列表"""
    service = SessionService(db)
    sessions = await service.get_user_sessions(user_id, status, limit)

    return [
        SessionResponse(
            session_id=s.session_id,
            project_id=s.project_id,
            user_id=s.user_id,
            status=s.status,
            current_step=s.current_step,
            score=s.score,
            total_duration=s.total_duration,
            submit_type=s.submit_type,
            started_at=s.started_at,
            paused_at=s.paused_at,
            submitted_at=s.submitted_at,
            project_snapshot=s.project_snapshot,
        )
        for s in sessions
    ]


@router.get(
    "/training/users/{user_id}/active-session",
    response_model=SessionResponse,
    tags=["Training"]
)
async def get_active_session(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取用户当前活跃会话（用于断点续训）"""
    service = SessionService(db)
    session = await service.get_user_active_session(user_id)

    if not session:
        raise HTTPException(status_code=404, detail="No active session found")

    return SessionResponse(
        session_id=session.session_id,
        project_id=session.project_id,
        user_id=session.user_id,
        status=session.status,
        current_step=session.current_step,
        score=session.score,
        total_duration=session.total_duration,
        submit_type=session.submit_type,
        started_at=session.started_at,
        paused_at=session.paused_at,
        submitted_at=session.submitted_at,
        project_snapshot=session.project_snapshot,
    )


@router.get(
    "/training/feedback/{session_id}",
    response_model=FeedbackResponse,
    tags=["Training"]
)
async def get_training_feedback(
    session_id: str,
    role: str = Query(default="student", pattern="^(student|teacher)$"),
    db: AsyncSession = Depends(get_db)
):
    """UF-09: 获取训练反馈报告"""
    result = await db.execute(
        select(TrainingSubmission)
        .where(TrainingSubmission.session_id == session_id)
        .order_by(TrainingSubmission.submitted_at.desc())
    )
    submission = result.scalars().first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    if not submission.feedback:
        feedback_generator = FeedbackGenerator(db)
        feedback = await feedback_generator.generate(
            submission_id=submission.submission_id,
            role=FeedbackRole.TEACHER if role == "teacher" else FeedbackRole.STUDENT,
        )
        payload = {
            "overall_score": feedback.overall_score,
            "score_breakdown": feedback.score_breakdown,
            "step_analyses": [
                {
                    "step_id": s.step_id,
                    "step_index": s.step_index,
                    "status": s.status,
                    "attempt_count": s.attempt_count,
                    "analysis": s.analysis,
                    "suggestions": s.suggestions,
                    "ref_ids": s.ref_ids,
                }
                for s in feedback.step_analyses
            ],
            "suggestions": feedback.suggestions,
            "next_learning_plan": feedback.next_learning_plan,
            "teaching_diagnosis": feedback.teaching_diagnosis,
            "ranking_percentile": feedback.ranking_percentile,
            "hint_level_suggestion": feedback.hint_level_suggestion,
        }
    else:
        payload = dict(submission.feedback)

    return FeedbackResponse(
        session_id=session_id,
        submission_id=submission.submission_id,
        overall_score=float(payload.get("overall_score", 0)),
        score_breakdown=payload.get("score_breakdown", {}),
        step_analyses=payload.get("step_analyses", []),
        suggestions=payload.get("suggestions", []),
        next_learning_plan=payload.get("next_learning_plan", ""),
        teaching_diagnosis=payload.get("teaching_diagnosis"),
        ranking_percentile=payload.get("ranking_percentile"),
        hint_level_suggestion=payload.get("hint_level_suggestion"),
    )


@router.get(
    "/students/{user_id}/profile",
    response_model=SkillProfileResponse,
    tags=["Training"]
)
async def get_student_skill_profile(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """UF-10: 获取学员技能画像"""
    service = SkillProfileService(db)
    profile = await service.get_or_create_profile(user_id)

    return SkillProfileResponse(
        user_id=profile.user_id,
        overall_level=profile.overall_level,
        total_sessions=profile.total_sessions,
        total_duration=profile.total_duration,
        last_trained_at=profile.last_trained_at,
        score_safety=float(profile.score_safety) if profile.score_safety is not None else None,
        score_procedure=float(profile.score_procedure) if profile.score_procedure is not None else None,
        score_precision=float(profile.score_precision) if profile.score_precision is not None else None,
        score_efficiency=float(profile.score_efficiency) if profile.score_efficiency is not None else None,
        score_tools=float(profile.score_tools) if profile.score_tools is not None else None,
        cert_l1_passed=profile.cert_l1_passed,
        cert_l2_passed=profile.cert_l2_passed,
        cert_l3_eligible=profile.cert_l3_eligible,
    )


@router.get(
    "/students/{user_id}/weak-steps",
    response_model=List[WeakStepResponse],
    tags=["Training"]
)
async def get_student_weak_steps(
    user_id: int,
    unresolved_only: bool = False,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """UF-10: 获取学员薄弱步骤列表"""
    service = SkillProfileService(db)
    weak_steps = await service.get_weak_steps(
        user_id=user_id,
        unresolved_only=unresolved_only,
        limit=limit,
    )

    return [
        WeakStepResponse(
            step_id=step.step_id,
            sop_id=step.sop_id,
            fail_count=step.fail_count,
            last_failed_at=step.last_failed_at,
            fail_tags=step.fail_tags,
            is_resolved=step.is_resolved,
        )
        for step in weak_steps
    ]
