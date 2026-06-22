"""
UF-06: Training Session Models
训练会话状态机模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.base import TZDateTime, Base, TimestampMixin, utcnow


class TrainingSession(Base, TimestampMixin):
    """训练会话表 - UF-06-a-1"""
    __tablename__ = "training_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), unique=True, nullable=False, index=True)
    project_id = Column(String(36), nullable=False, index=True)

    # 关联用户
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user = relationship("User", backref="training_sessions")

    # 会话状态
    status = Column(String(20), nullable=False, default="active", index=True)  # active/paused/submitted/abandoned/expired

    # 当前进度
    current_step = Column(Integer, nullable=False, default=0)

    # 项目快照
    project_snapshot = Column(JSON, nullable=True)

    # 时间记录
    started_at = Column(TZDateTime, nullable=False, default=utcnow)
    paused_at = Column(TZDateTime, nullable=True)
    submitted_at = Column(TZDateTime, nullable=True)

    # 统计
    total_duration = Column(Integer, nullable=False, default=0)  # 秒
    score = Column(Numeric(5, 2), nullable=True)
    submit_type = Column(String(20), nullable=True)  # manual/timeout/teacher/abandoned

    # A/B测试分组
    ab_group = Column(String(10), nullable=True)

    # 步骤记录
    step_records = relationship("SessionStepRecord", back_populates="session", cascade="all, delete-orphan")


class SessionStepRecord(Base, TimestampMixin):
    """会话步骤记录表 - UF-06-a-2"""
    __tablename__ = "session_step_records"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(String(36), unique=True, nullable=False, index=True)

    # 关联会话
    session_id = Column(String(36), ForeignKey("training_sessions.session_id"), nullable=False, index=True)
    session = relationship("TrainingSession", back_populates="step_records")

    # 步骤信息
    step_id = Column(String(50), nullable=False)
    step_index = Column(Integer, nullable=False)

    # 状态
    status = Column(String(20), nullable=False, default="pending", index=True)  # pending/in_progress/pass/fail/skip

    # 操作记录
    attempt_count = Column(Integer, nullable=False, default=0)
    tools_confirmed = Column(JSON, nullable=True)  # [{ tool_id, status, confirmed_at }]
    evidence = Column(JSON, nullable=True)  # { input_value, photo_url, notes }
    verdict_result = Column(JSON, nullable=True)  # { rule_result, llm_explanation, ref_ids }

    # 时间
    duration_sec = Column(Integer, nullable=True)
    started_at = Column(TZDateTime, nullable=True)
    completed_at = Column(TZDateTime, nullable=True)
