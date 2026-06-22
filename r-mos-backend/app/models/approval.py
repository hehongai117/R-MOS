"""Gate-2 F-001：审批记录模型。"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, String

from .base import Base, utcnow


class Approval(Base):
    """最小审批流记录。"""

    __tablename__ = "approvals"
    __table_args__ = (
        Index("ix_approvals_trace_status", "trace_id", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    trace_id = Column(String(64), nullable=False, index=True)
    command_id = Column(Integer, nullable=False, index=True)
    tool_call_id = Column(Integer, nullable=False, index=True)
    status = Column(String(32), nullable=False, default="pending", index=True)
    reason = Column(String(256), nullable=True)
    created_by_user_id = Column(String(64), nullable=True, index=True)
    decided_by_user_id = Column(String(64), nullable=True, index=True)
    decided_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
