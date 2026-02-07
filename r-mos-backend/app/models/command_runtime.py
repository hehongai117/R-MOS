"""Gate-2 E-001：Command/ToolCall 运行时模型。"""
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint

from .base import Base


class Command(Base):
    """AI 命令入口记录。"""

    __tablename__ = "commands"
    __table_args__ = (
        UniqueConstraint("trace_id", name="ux_commands_trace_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    trace_id = Column(String(64), nullable=False, index=True)
    actor_user_id = Column(String(64), nullable=True, index=True)
    intent = Column(String(128), nullable=False, index=True)
    skill_id = Column(String(128), nullable=True, index=True)
    status = Column(String(32), nullable=False, default="created", index=True)
    approval_id = Column(Integer, ForeignKey("approvals.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class AIToolCall(Base):
    """命令内的工具调用记录。"""

    __tablename__ = "ai_tool_calls"
    __table_args__ = (
        Index("ix_tool_calls_trace_skill", "trace_id", "skill_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    command_id = Column(Integer, ForeignKey("commands.id", ondelete="CASCADE"), nullable=False, index=True)
    trace_id = Column(String(64), nullable=False, index=True)
    actor_user_id = Column(String(64), nullable=True, index=True)
    skill_id = Column(String(128), nullable=True, index=True)
    tool_name = Column(String(128), nullable=False)
    side_effects = Column(JSON, nullable=False, default=list)
    status = Column(String(32), nullable=False, default="pending", index=True)
    approval_id = Column(Integer, ForeignKey("approvals.id", ondelete="SET NULL"), nullable=True, index=True)
    result_payload = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
