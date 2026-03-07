"""
UF-04, UF-06: Training API Endpoints
训练项目与会话管理接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from datetime import datetime
import json
import logging

from app.core.database import get_db
from app.models.audit_event import AuditEvent
from app.services.training.session_service import SessionService
from app.services.training.submission_service import SubmissionService
from app.services.training.feedback_generator import FeedbackGenerator, FeedbackRole
from app.services.identity.class_membership import ClassMembershipService
from app.services.memory.skill_profile_service import SkillProfileService
from app.models.training_submission import TrainingSubmission

logger = logging.getLogger(__name__)

router = APIRouter()


# ============ Schemas ============

class SessionCreateRequest(BaseModel):
    """创建会话请求"""
    user_id: int
    project_id: str
    project_snapshot: dict
    ab_group: Optional[str] = None


class SessionResponse(BaseModel):
    """会话响应"""
    session_id: str
    project_id: str
    user_id: int
    status: str
    current_step: int
    score: Optional[float] = None
    total_duration: int
    submit_type: Optional[str] = None
    started_at: datetime
    paused_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StepRecordResponse(BaseModel):
    """步骤记录响应"""
    record_id: str
    session_id: str
    step_id: str
    step_index: int
    status: str
    attempt_count: int
    duration_sec: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StepUpdateRequest(BaseModel):
    """更新步骤请求"""
    step_id: str
    step_index: int
    status: str
    attempt_count: int = 0
    tools_confirmed: Optional[List[dict]] = None
    evidence: Optional[dict] = None
    verdict_result: Optional[dict] = None
    duration_sec: Optional[int] = None


class SessionDetailResponse(BaseModel):
    """会话详情响应（含步骤记录）"""
    session: SessionResponse
    steps: List[StepRecordResponse]


class ProjectGenerateRequest(BaseModel):
    """生成训练项目请求"""
    user_id: int
    robot_id: Optional[str] = None
    difficulty: str = "medium"  # easy/medium/hard
    focus_areas: Optional[List[str]] = None


class ProjectGenerateResponse(BaseModel):
    """生成训练项目响应"""
    project_id: str
    project: dict
    estimated_duration_minutes: int


class SubmitSessionRequest(BaseModel):
    """提交训练请求"""
    user_id: int
    confirm_incomplete: bool = False


class ForceSubmitSessionRequest(BaseModel):
    """教师强制提交请求"""
    teacher_id: int


class SubmitSessionResponse(BaseModel):
    """提交训练响应"""
    submission_id: str
    session_id: str
    user_id: int
    submit_type: str
    score: Optional[float] = None


class SkillProfileResponse(BaseModel):
    """技能画像响应"""
    user_id: int
    overall_level: int
    total_sessions: int
    total_duration: int
    last_trained_at: Optional[datetime] = None
    score_safety: Optional[float] = None
    score_procedure: Optional[float] = None
    score_precision: Optional[float] = None
    score_efficiency: Optional[float] = None
    score_tools: Optional[float] = None
    cert_l1_passed: bool
    cert_l2_passed: bool
    cert_l3_eligible: bool


class WeakStepResponse(BaseModel):
    """薄弱步骤响应"""
    step_id: str
    sop_id: Optional[str] = None
    fail_count: int
    last_failed_at: Optional[datetime] = None
    fail_tags: Optional[list[str]] = None
    is_resolved: bool


class FeedbackResponse(BaseModel):
    """训练反馈响应"""
    session_id: str
    submission_id: str
    overall_score: float
    score_breakdown: dict
    step_analyses: list[dict] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    next_learning_plan: str = ""
    teaching_diagnosis: Optional[str] = None
    ranking_percentile: Optional[float] = None
    hint_level_suggestion: Optional[int] = None


# ============ UF-04: Training Project Routes ============

@router.post(
    "/training/projects/generate",
    response_model=ProjectGenerateResponse,
    tags=["Training"]
)
async def generate_training_project(
    request: ProjectGenerateRequest,
    db: AsyncSession = Depends(get_db)
):
    """UF-04-b-2: 生成训练项目

    使用 SSE 流式返回项目配置
    """
    async def sse_stream():
        try:
            from app.services.training.project_generator import ProjectGenerator

            generator = ProjectGenerator(db)

            # 构建 intent 对象
            class IntentPlaceholder:
                category = None
                brand = request.robot_id
                model = None
                difficulty = request.difficulty
                focus_areas = request.focus_areas

            intent = IntentPlaceholder()

            # 流式生成项目
            async for chunk in generator.generate(intent, request.user_id):
                if "error" in chunk:
                    yield f"data: {json.dumps(chunk)}\n\n"
                    break

                if chunk.get("status") == "completed":
                    project = chunk.get("project")
                    if project:
                        yield f"data: {json.dumps({
                            "status": "completed",
                            "project_id": project.project_id,
                            "project": {
                                "project_id": project.project_id,
                                "title": project.title,
                                "description": project.description,
                                "estimated_time": project.estimated_time,
                                "difficulty_cap": project.difficulty_cap,
                            }
                        })}\n\n"
                    break

                yield f"data: {json.dumps(chunk)}\n\n"

        except Exception as e:
            logger.error(f"[UF-04] Project generation error: {e}")
            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(sse_stream(), media_type="text/event-stream")


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
    try:
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
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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

    try:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
