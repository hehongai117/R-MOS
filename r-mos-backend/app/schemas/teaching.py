"""
Teaching domain schemas (Pydantic v2, camelCase outputs).
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, AliasChoices
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
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        validation_alias=AliasChoices("metadata", "metadata_json"),
    )


class ClassResponse(ClassCreate):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CourseCreate(TeachingBaseModel):
    class_id: int
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    schedule: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        validation_alias=AliasChoices("metadata", "metadata_json"),
    )


class CourseResponse(CourseCreate):
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
