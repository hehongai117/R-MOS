"""
UF-08: Training Submission Model
训练提交记录模型
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Numeric
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.base import TZDateTime, Base, TimestampMixin, utcnow


class TrainingSubmission(Base, TimestampMixin):
    """训练提交记录表 - UF-08-b"""
    __tablename__ = "training_submissions"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(String(36), unique=True, nullable=False, index=True)

    # 关联会话
    session_id = Column(String(36), ForeignKey("training_sessions.session_id"), nullable=False, index=True)
    session = relationship("TrainingSession", backref="submissions")

    # 用户信息
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user = relationship("User", foreign_keys=[user_id], backref="training_submissions")

    # 提交信息
    submit_type = Column(String(20), nullable=False)  # manual/timeout/teacher/abandoned
    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # 教师强制提交时
    submitted_by_user = relationship("User", foreign_keys=[submitted_by], backref="forced_training_submissions")
    submitted_at = Column(TZDateTime, nullable=False, default=utcnow)

    # 提交包内容
    payload = Column(JSON, nullable=False)  # 完整的提交包 JSON

    # 评分
    score = Column(Numeric(5, 2), nullable=True)

    # 统计
    total_steps = Column(Integer, nullable=False, default=0)
    completed_steps = Column(Integer, nullable=False, default=0)
    failed_steps = Column(Integer, nullable=False, default=0)
    total_duration = Column(Integer, nullable=False, default=0)

    # AI 反馈
    feedback = Column(JSON, nullable=True)  # UF-09 生成的反馈报告
    feedback_generated_at = Column(TZDateTime, nullable=True)
