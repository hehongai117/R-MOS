"""
通用审计事件模型（Gate-1 / C-001）。

用于统一记录：
- 访问拒绝（access_denied）
- 权限拒绝（permission_denied）
"""
from datetime import datetime

from sqlalchemy import Column, ForeignKey, Index, Integer, JSON, String, func

from .base import Base, TZDateTime, utcnow


class AuditEvent(Base):
    """统一审计事件表。"""

    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_trace_created", "trace_id", "created_at"),
        Index("ix_audit_action_created", "action", "created_at"),
        Index("ix_audit_actor_created", "actor_user_id", "created_at"),
        Index("ix_audit_resource_created", "resource_type", "resource_id", "created_at"),
        Index("ix_audit_approval_created", "approval_id", "created_at"),
        Index("ix_audit_skill_created", "skill_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    actor_user_id = Column(String(64), nullable=True, index=True)
    action = Column(String(64), nullable=False, index=True)
    resource_type = Column(String(64), nullable=True, index=True)
    resource_id = Column(String(128), nullable=True, index=True)
    decision = Column(String(16), nullable=False, index=True)
    reason = Column(String(256), nullable=True)
    request_meta = Column(JSON, nullable=True)
    trace_id = Column(String(64), nullable=True, index=True)
    skill_id = Column(String(128), nullable=True)
    skill_version = Column(String(32), nullable=True)
    tool_call_args = Column(JSON, nullable=True)
    side_effects_applied = Column(JSON, nullable=True)
    approval_id = Column(Integer, ForeignKey("approvals.id", ondelete="SET NULL"), nullable=True)

    # LLM 审计字段 (P1-0)
    prompt_hash = Column(String(64), nullable=True, index=True, comment="Prompt 内容哈希")
    response_hash = Column(String(64), nullable=True, index=True, comment="Response 内容哈希")
    provider = Column(String(32), nullable=True, comment="LLM Provider: openai/anthropic/ollama")
    model = Column(String(64), nullable=True, comment="模型名称: gpt-4/claude-3/llama2")
    tokens_in = Column(Integer, nullable=True, comment="输入 token 数量")
    tokens_out = Column(Integer, nullable=True, comment="输出 token 数量")

    created_at = Column(
        TZDateTime,
        nullable=False,
        default=utcnow,
        server_default=func.now(),
        index=True,
    )
