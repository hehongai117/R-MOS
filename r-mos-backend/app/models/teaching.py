"""
Teaching domain models (classes, assignments, guidance policies, attempts).
"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Text,
    Float,
)
from sqlalchemy.orm import relationship

from .base import TZDateTime, Base, TimestampMixin


class GuidancePolicy(Base, TimestampMixin):
    __tablename__ = "guidance_policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    base_mode = Column(String(20), nullable=False, default="teaching")
    allow_ghost_hand = Column(Boolean, nullable=False, default=True)
    allow_hint_button = Column(Boolean, nullable=False, default=True)
    show_error_details = Column(Boolean, nullable=False, default=True)
    max_retry_count = Column(Integer, nullable=False, default=-1)
    description = Column(Text, nullable=True)

    assignments = relationship("Assignment", back_populates="guidance_policy")
    tasks = relationship("Task", back_populates="guidance_policy")


class TeachingClass(Base, TimestampMixin):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    term = Column(String(50), nullable=True)
    teacher_id = Column(Integer, nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True)

    courses = relationship("Course", back_populates="teaching_class", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="teaching_class", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="teaching_class", cascade="all, delete-orphan")
    evidence_links = relationship("EvidenceLink", back_populates="teaching_class")


class Course(Base, TimestampMixin):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    schedule = Column(JSON, nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True)

    teaching_class = relationship("TeachingClass", back_populates="courses")
    assignments = relationship("Assignment", back_populates="course")


class Enrollment(Base, TimestampMixin):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, nullable=False, index=True)
    role = Column(String(20), nullable=False, default="student")

    teaching_class = relationship("TeachingClass", back_populates="enrollments")


class Assignment(Base, TimestampMixin):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    sop_id = Column(Integer, ForeignKey("sops.id", ondelete="SET NULL"), nullable=True, index=True)
    guidance_policy_id = Column(Integer, ForeignKey("guidance_policies.id", ondelete="SET NULL"), nullable=True, index=True)
    start_at = Column(TZDateTime, nullable=True)
    due_at = Column(TZDateTime, nullable=True)
    max_attempts = Column(Integer, nullable=True, default=1)
    scoring_policy = Column(JSON, nullable=True)
    competition_mode = Column(Boolean, nullable=False, default=False)
    hidden_sop = Column(Boolean, nullable=False, default=False)
    blind_step_mask = Column(JSON, nullable=True)

    teaching_class = relationship("TeachingClass", back_populates="assignments")
    course = relationship("Course", back_populates="assignments")
    guidance_policy = relationship("GuidancePolicy", back_populates="assignments")
    attempts = relationship("AssignmentAttempt", back_populates="assignment", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="assignment")


class AssignmentAttempt(Base, TimestampMixin):
    __tablename__ = "assignment_attempts"

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    evidence_bundle_id = Column(String(64), ForeignKey("evidence_bundles.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="in_progress")
    score = Column(Float, nullable=True)
    graded_at = Column(TZDateTime, nullable=True)
    abandoned_at = Column(TZDateTime, nullable=True)
    attempt_index = Column(Integer, nullable=False, default=1)
    diagnosis_code = Column(String(100), nullable=True)
    path_score = Column(Float, nullable=True)
    evidence_quality_score = Column(Float, nullable=True)

    assignment = relationship("Assignment", back_populates="attempts")
    task = relationship("Task", back_populates="attempts")
    evidence_links = relationship("EvidenceLink", back_populates="attempt")


class EvidenceLink(Base, TimestampMixin):
    __tablename__ = "evidence_links"

    id = Column(Integer, primary_key=True, index=True)
    bundle_id = Column(String(64), ForeignKey("evidence_bundles.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True)
    attempt_id = Column(Integer, ForeignKey("assignment_attempts.id", ondelete="CASCADE"), nullable=True, index=True)
    student_id = Column(Integer, nullable=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="SET NULL"), nullable=True, index=True)

    attempt = relationship("AssignmentAttempt", back_populates="evidence_links")
    teaching_class = relationship("TeachingClass", back_populates="evidence_links")
