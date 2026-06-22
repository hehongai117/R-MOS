"""Gate-2 E-001：Command/ToolCall 运行时模型。"""
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint

from .base import TZDateTime, Base, utcnow


class Command(Base):
    """AI 命令入口记录。Extended with 10 evidence fields (Phase 0 Week 2)"""

    __tablename__ = "commands"
    __table_args__ = (
        UniqueConstraint("trace_id", name="ux_commands_trace_id"),
        Index("ix_commands_risk_status", "risk_level", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    trace_id = Column(String(64), nullable=False, index=True)
    actor_user_id = Column(String(64), nullable=True, index=True)
    intent = Column(String(128), nullable=False, index=True)
    skill_id = Column(String(128), nullable=True, index=True)
    status = Column(String(32), nullable=False, default="created", index=True)
    approval_id = Column(Integer, ForeignKey("approvals.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(TZDateTime, nullable=False, default=utcnow, index=True)
    updated_at = Column(TZDateTime, nullable=False, default=utcnow, onupdate=utcnow)

    # Phase 0: Extended fields (10 new evidence fields)
    # 1. Resource binding
    resource_ref = Column(JSON, nullable=True)
    # 2. Policy context
    policy_context = Column(JSON, nullable=True)
    # 3. Intent classification
    intent_classification = Column(String(64), nullable=True, index=True)
    # 4. Idempotency key
    idempotency_key = Column(String(128), nullable=True, unique=True, index=True)
    # 5. Policy decision result
    policy_decision = Column(JSON, nullable=True)
    # 6. Risk level
    risk_level = Column(String(8), nullable=True, index=True)
    # 7. Evidence references
    evidence_refs = Column(JSON, nullable=False, default=list)
    # 8. Approved by
    approved_by = Column(String(64), nullable=True)
    # 9. Approved at
    approved_at = Column(TZDateTime, nullable=True)
    # 10. Execution budget
    execution_budget_ms = Column(Integer, nullable=True)


class AIToolCall(Base):
    """命令内的工具调用记录。Extended with 8 evidence fields (Phase 0 Week 2)"""

    __tablename__ = "ai_tool_calls"
    __table_args__ = (
        Index("ix_tool_calls_trace_skill", "trace_id", "skill_id"),
        Index("ix_tool_calls_status_time", "status", "created_at"),
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
    created_at = Column(TZDateTime, nullable=False, default=utcnow, index=True)

    # Phase 0: Extended fields (8 new evidence fields)
    # 1. Input parameters
    input_params = Column(JSON, nullable=True)
    # 2. Execution time
    execution_time_ms = Column(Integer, nullable=True)
    # 3. Retry count
    retry_count = Column(Integer, nullable=False, default=0)
    # 4. Parent tool call ID (for nested calls)
    parent_tool_call_id = Column(Integer, ForeignKey("ai_tool_calls.id", ondelete="SET NULL"), nullable=True)
    # 5. Call depth
    call_depth = Column(Integer, nullable=False, default=0)
    # 6. Evidence collected
    evidence_collected = Column(JSON, nullable=False, default=list)
    # 7. Safety check passed
    safety_check_passed = Column(String(8), nullable=True)
    # 8. Model version
    model_version = Column(String(32), nullable=True)
