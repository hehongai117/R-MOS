"""
Training workbench Pydantic schemas.
Extracted verbatim from app/api/v1/endpoints/training.py (Phase 3 refactor).
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


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
    project_snapshot: Optional[dict] = None

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
    tools_confirmed: Optional[list[dict]] = None
    evidence: Optional[dict] = None
    verdict_result: Optional[dict] = None
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


class WorkbenchDraftRequest(BaseModel):
    """训练工作台空态草案生成请求。"""

    robot_model: str = Field(min_length=1)
    robot_id: int | None = None
    task_summary: str = Field(default="关节电机盖拆装", min_length=1)
    focus_prompt: str = Field(default="强调工具确认、证据留存与 AI 提示", min_length=1)


class WorkbenchDraftToolResponse(BaseModel):
    id: str
    name: str
    spec: str
    is_critical: bool = False
    recommendation: Optional[str] = None


class WorkbenchDraftStepResponse(BaseModel):
    id: str
    step_index: int
    title: str
    status: str
    instruction: str
    evidence_hint: str
    model_targets: list[str] = Field(default_factory=list)
    tools: list[WorkbenchDraftToolResponse] = Field(default_factory=list)


class WorkbenchDraftMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime


class WorkbenchDraftProjectResponse(BaseModel):
    session_id: str
    project_id: str
    title: str
    summary: str
    progress_percent: int


class WorkbenchDraftResponse(BaseModel):
    project: WorkbenchDraftProjectResponse
    steps: list[WorkbenchDraftStepResponse] = Field(default_factory=list)
    messages: list[WorkbenchDraftMessageResponse] = Field(default_factory=list)


class WorkbenchToolConfirmRequest(BaseModel):
    tool_id: str
    status: str


class WorkbenchEvidenceUploadResponse(BaseModel):
    evidence_bundle_id: str
    filename: str
    content_uri: str
    human_summary: Optional[str] = None


class WorkbenchStepSubmitRequest(BaseModel):
    step_index: int
    note: str = ""
    evidence_bundle_id: Optional[str] = None
    tools_confirmed: list[WorkbenchToolConfirmRequest] = Field(default_factory=list)


class WorkbenchStepVerdictResponse(BaseModel):
    result: str
    summary: str
    details: str
    missing_critical_tools: list[str] = Field(default_factory=list)
    anomaly_tools: list[str] = Field(default_factory=list)
    evidence_bundle_id: Optional[str] = None


class WorkbenchStepSubmitResponse(BaseModel):
    record_id: str
    status: str
    verdict: WorkbenchStepVerdictResponse
    next_step_id: Optional[str] = None
    session_submitted: bool = False
    feedback: Optional[dict] = None
    evidence_bundle_id: Optional[str] = None


class WorkbenchAskRequest(BaseModel):
    session_id: str
    step_id: str
    question: str = Field(min_length=1)
    messages: list[dict] = Field(default_factory=list)


class WorkbenchAssistantMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: str


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
