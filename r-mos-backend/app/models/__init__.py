"""
R-MOS 数据模型导出

所有 ORM 模型统一从此模块导出，供 Alembic 迁移和业务层使用。
"""
from app.models.base import Base, TimestampMixin
from app.models.sop import SOP, SOPStep
from app.models.task import Task, TaskStatus
from app.models.event import Event, EventType
from app.models.snapshot import Snapshot
from app.models.fault import FaultCase
from app.models.incident import Incident
from app.models.observation import Observation
from app.models.evidence import EvidenceBundle, EvidenceItem
from app.models.assessment import AssessmentProvider, ExternalAssessment, AssessmentAuditEvent
from app.models.audit_log import SOPAuditLog, AuditAction, ActorType  # V2.3 新增
from app.models.audit_event import AuditEvent
from app.models.skill_registry import Skill, SkillReview, SkillRelease
from app.models.command_runtime import Command, AIToolCall
from app.models.approval import Approval
from app.models.knowledge_chunk import AIKnowledgeChunk
from app.models.robot_project import RobotProject, RobotProjectStatus
from app.models.robot_project_file import RobotProjectFile
from app.models.robot_part_manifest import RobotPartManifest
from app.models.robot_sop_draft import RobotSOPDraft, RobotSOPDraftReviewStatus
from app.models.timeline import MultimodalTimeline, TimelineSegment, AlignmentMap, EvidenceCard
from app.models.rbac import Role, Permission, UserRole, RolePermission
from app.models.refresh_token import RefreshToken
from app.models.access_token import AccessToken
from app.models.user import User
from app.models.user_preference import UserPreference
from app.models.fault_sop_mapping import FaultSOPMapping
from app.models.task_execution import TaskExecution, TaskStepResult
from app.models.knowledge_document import KnowledgeDocument
from app.models.teaching import (
    GuidancePolicy,
    TeachingClass,
    Course,
    Enrollment,
    Assignment,
    AssignmentAttempt,
    EvidenceLink,
)
from app.models.robot_model import RobotModel, RobotVisibility, RobotStatus, TeacherRobotBinding
from app.models.robot_asset import RobotAsset, AssetType
from app.models.analysis_task import AnalysisTask, AnalysisTaskType, AnalysisTaskStatus
from app.models.school import School  # noqa: F401
from app.models.training import TrainingSession, SessionStepRecord
from app.models.training_submission import TrainingSubmission
from app.models.skill_profile import StudentSkillProfile, StudentWeakStep
from app.models.conversation import ConversationTurn
from app.models.agent_runtime import (
    AgentRuntimeSnapshot,
    BeliefStateRecord,
    DecisionRecordDB,
    ApprovalRecordDB,
    ReplayCheckpoint,
)

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    # SOP
    "SOP",
    "SOPStep",
    # Task
    "Task",
    "TaskStatus",
    # Event
    "Event",
    "EventType",
    # Snapshot
    "Snapshot",
    # Fault
    "FaultCase",
    # Incident
    "Incident",
    # Observation
    "Observation",
    # Evidence
    "EvidenceBundle",
    "EvidenceItem",
    # Assessment
    "AssessmentProvider",
    "ExternalAssessment",
    "AssessmentAuditEvent",
    # Audit (V2.3 新增)
    "SOPAuditLog",
    "AuditAction",
    "ActorType",
    "AuditEvent",
    # Skill registry
    "Skill",
    "SkillReview",
    "SkillRelease",
    "Command",
    "AIToolCall",
    "Approval",
    "AIKnowledgeChunk",
    "RobotProject",
    "RobotProjectStatus",
    "RobotProjectFile",
    "RobotPartManifest",
    "RobotSOPDraft",
    "RobotSOPDraftReviewStatus",
    "MultimodalTimeline",
    "TimelineSegment",
    "AlignmentMap",
    "EvidenceCard",
    # RBAC
    "Role",
    "Permission",
    "UserRole",
    "RolePermission",
    # Auth tokens
    "AccessToken",
    "RefreshToken",
    # Auth
    "User",
    "UserPreference",
    # Teaching domain
    "GuidancePolicy",
    "TeachingClass",
    "Course",
    "Enrollment",
    "Assignment",
    "AssignmentAttempt",
    "EvidenceLink",
    # Pipeline
    "FaultSOPMapping",
    "TaskExecution",
    "TaskStepResult",
    "KnowledgeDocument",
    # Robot platform
    "RobotModel",
    "RobotVisibility",
    "RobotStatus",
    "TeacherRobotBinding",
    "RobotAsset",
    "AssetType",
    "AnalysisTask",
    "AnalysisTaskType",
    "AnalysisTaskStatus",
    # School whitelist
    "School",
    # Training system
    "TrainingSession",
    "SessionStepRecord",
    "TrainingSubmission",
    # Skill profile
    "StudentSkillProfile",
    "StudentWeakStep",
    # Conversation
    "ConversationTurn",
    # Agent runtime
    "AgentRuntimeSnapshot",
    "BeliefStateRecord",
    "DecisionRecordDB",
    "ApprovalRecordDB",
    "ReplayCheckpoint",
]
