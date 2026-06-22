"""Task execution persistence models."""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import TZDateTime, Base, TimestampMixin, utcnow


class TaskExecution(Base, TimestampMixin):
    """Persists a student's SOP execution session."""
    __tablename__ = "task_executions"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, nullable=False, index=True, comment="学生 user ID")
    sop_id = Column(Integer, ForeignKey("sops.id", ondelete="SET NULL"), nullable=True)
    diagnosis_trace_id = Column(String(100), nullable=True, comment="诊断追踪 ID")
    fault_type = Column(String(50), nullable=True, index=True, comment="故障类型")
    status = Column(String(20), default="in_progress", nullable=False, comment="in_progress/completed/abandoned")
    started_at = Column(TZDateTime, default=utcnow, nullable=False)
    completed_at = Column(TZDateTime, nullable=True)

    step_results = relationship("TaskStepResult", back_populates="execution", cascade="all, delete-orphan", lazy="selectin")


class TaskStepResult(Base, TimestampMixin):
    """Result of a single SOP step execution."""
    __tablename__ = "task_step_results"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("task_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    step_index = Column(Integer, nullable=False, comment="步骤序号")
    status = Column(String(20), default="completed", comment="completed/skipped/failed")
    duration_seconds = Column(Integer, nullable=True, comment="耗时秒数")
    evidence_type = Column(String(30), nullable=True, comment="photo/numeric/checkbox")
    evidence_value = Column(JSON, nullable=True, comment="证据内容")
    is_compliant = Column(Boolean, default=True, comment="是否合规")
    feedback = Column(String(500), nullable=True, comment="即时反馈")

    execution = relationship("TaskExecution", back_populates="step_results")
