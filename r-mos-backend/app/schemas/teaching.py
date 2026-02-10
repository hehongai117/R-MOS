"""
Teaching domain schemas (Pydantic v2, camelCase outputs).
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, AliasChoices, RootModel
from pydantic.alias_generators import to_camel


class TeachingBaseModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )


class GuidancePolicyCreate(TeachingBaseModel):
    name: str = Field(..., max_length=100)
    base_mode: str = Field("teaching", description="teaching | exam")
    allow_ghost_hand: bool = True
    allow_hint_button: bool = True
    show_error_details: bool = True
    max_retry_count: int = Field(-1, ge=-1)
    description: Optional[str] = None


class GuidancePolicyResponse(GuidancePolicyCreate):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ClassCreate(TeachingBaseModel):
    name: str = Field(..., max_length=200)
    term: Optional[str] = None
    teacher_id: Optional[int] = None
    metadata_json: Optional[Dict[str, Any]] = Field(
        None,
        alias="metadata",
        validation_alias=AliasChoices("metadata", "metadata_json"),
    )


class ClassResponse(ClassCreate):
    metadata_json: Optional[Dict[str, Any]] = Field(
        None,
        alias="metadata",
        validation_alias="metadata_json",
    )
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CourseCreate(TeachingBaseModel):
    class_id: int
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    schedule: Optional[Dict[str, Any]] = None
    metadata_json: Optional[Dict[str, Any]] = Field(
        None,
        alias="metadata",
        validation_alias=AliasChoices("metadata", "metadata_json"),
    )


class CourseResponse(CourseCreate):
    metadata_json: Optional[Dict[str, Any]] = Field(
        None,
        alias="metadata",
        validation_alias="metadata_json",
    )
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EnrollmentCreate(TeachingBaseModel):
    class_id: int
    student_id: int
    role: str = Field("student", max_length=20)


class EnrollmentResponse(EnrollmentCreate):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AssignmentCreate(TeachingBaseModel):
    class_id: int
    course_id: Optional[int] = None
    title: str = Field(..., max_length=200)
    sop_id: Optional[int] = None
    guidance_policy_id: Optional[int] = None
    start_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    max_attempts: Optional[int] = Field(1, ge=1)
    scoring_policy: Optional[Dict[str, Any]] = None
    competition_mode: bool = False
    hidden_sop: bool = False
    blind_step_mask: Optional[Dict[str, Any]] = None


class AssignmentResponse(AssignmentCreate):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AttemptStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    GRADED = "graded"
    ABANDONED = "abandoned"


class DiagnosisSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AssignmentAttemptCreate(TeachingBaseModel):
    assignment_id: int
    student_id: int
    task_id: Optional[int] = None
    attempt_index: int = Field(1, ge=1)
    status: AttemptStatus = AttemptStatus.IN_PROGRESS


class AssignmentAttemptResponse(TeachingBaseModel):
    id: int
    assignment_id: int
    student_id: int
    task_id: Optional[int] = None
    evidence_bundle_id: Optional[str] = None
    status: AttemptStatus
    score: Optional[float] = None
    attempt_index: int
    diagnosis_code: Optional[str] = None
    path_score: Optional[float] = None
    evidence_quality_score: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EvidenceLinkResponse(TeachingBaseModel):
    id: int
    bundle_id: str
    task_id: Optional[int] = None
    attempt_id: Optional[int] = None
    student_id: Optional[int] = None
    class_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AttemptEvidenceResponse(TeachingBaseModel):
    bundle_id: str
    task_id: Optional[int] = None
    attempt_id: int
    summary: Optional[Dict[str, Any]] = None


class ReplayFailurePoint(TeachingBaseModel):
    step_id: Optional[int] = None
    event_id: Optional[int] = None
    failure_type: str = "unknown"
    rule_hit: Optional[str] = None


class ReplayEvidenceRef(TeachingBaseModel):
    ref_id: str
    timeline_id: int
    segment_id: int
    start_ts_ms: int
    end_ts_ms: int


class ReplaySupplementItem(TeachingBaseModel):
    data_type: str
    time_range: Optional[str] = None
    reason: str


class AttemptReplayResponse(TeachingBaseModel):
    attempt_id: int
    status: str
    failure_point: ReplayFailurePoint
    supplement_plan: list[ReplaySupplementItem] = Field(default_factory=list)
    evidence_refs: list[ReplayEvidenceRef] = Field(default_factory=list)


class DiagnosisFinding(RootModel[str]):
    """诊断发现项（保持输出为 string）。"""


class DiagnosisSourceRefs(TeachingBaseModel):
    attempt_evidence_id: int


class StepDiagnosisSourceRefs(TeachingBaseModel):
    step_id: Optional[int] = None
    snapshot_id: Optional[int] = None


class StepDiagnosis(TeachingBaseModel):
    step_index: int = Field(..., ge=1)
    step_diagnosis_code: str
    severity: DiagnosisSeverity
    findings: list[DiagnosisFinding] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    rule_id: str
    source_refs: StepDiagnosisSourceRefs = Field(default_factory=StepDiagnosisSourceRefs)


class DiagnosisReport(TeachingBaseModel):
    report_version: str = Field("v1")
    attempt_id: int
    diagnosis_code: str
    rule_id: str
    severity: DiagnosisSeverity
    findings: list[DiagnosisFinding] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    step_diagnoses: list[StepDiagnosis] = Field(default_factory=list)
    factors: list[dict[str, Any]] = Field(default_factory=list)
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    generated_at: datetime
    source_refs: DiagnosisSourceRefs
