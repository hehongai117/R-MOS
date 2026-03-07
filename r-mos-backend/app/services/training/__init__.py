"""
UF-04, UF-06, UF-08, UF-09: Training Services
训练服务模块
"""
from app.services.training.session_service import (
    SessionService,
)
from app.services.training.submission_service import (
    SubmissionService,
    TrainingSubmission,
    SubmissionCheckResult,
)
from app.services.training.feedback_generator import (
    FeedbackGenerator,
    TrainingFeedback,
    FeedbackRole,
)

# project_generator 依赖知识/LLM 子系统，启动时可能因环境缺失而不可用。
# 这里做惰性容错导入，避免影响与其无关的训练会话/提交/反馈接口。
try:
    from app.services.training.project_generator import (
        ProjectGenerator,
        TrainingProject,
        ProjectStatus,
        StepConfig,
        ToolConfig,
        VerdictConfig,
        RobotConfig,
    )
except Exception:  # pragma: no cover - graceful fallback for partial environments
    ProjectGenerator = None
    TrainingProject = None
    ProjectStatus = None
    StepConfig = None
    ToolConfig = None
    VerdictConfig = None
    RobotConfig = None

__all__ = [
    "ProjectGenerator",
    "TrainingProject",
    "ProjectStatus",
    "StepConfig",
    "ToolConfig",
    "VerdictConfig",
    "RobotConfig",
    "SessionService",
    "SubmissionService",
    "TrainingSubmission",
    "SubmissionCheckResult",
    "FeedbackGenerator",
    "TrainingFeedback",
    "FeedbackRole",
]
