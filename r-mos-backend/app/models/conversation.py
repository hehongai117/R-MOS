"""
ConversationTurn Model - P1-8-1
对话记录表
"""
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text, Index

from app.models.base import Base


class ConversationTurn(Base):
    """对话记录表"""

    __tablename__ = "conversation_turns"

    __table_args__ = (
        Index("ix_conv_session_created", "session_id", "created_at"),
        Index("ix_conv_task_created", "task_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), nullable=False, index=True, comment="会话ID")
    task_id = Column(String(64), nullable=True, index=True, comment="任务ID")
    step_index = Column(Integer, nullable=True, comment="步骤索引")
    role = Column(String(16), nullable=False, comment="角色: user/assistant/system")
    content = Column(Text, nullable=False, comment="对话内容")
    metadata = Column(String(512), nullable=True, comment="元数据 JSON")
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )
