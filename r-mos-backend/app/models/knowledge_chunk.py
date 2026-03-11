"""Gate-3 H-001：RAG 知识分片最小模型。"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, JSON, String, Text

from .base import Base


class AIKnowledgeChunk(Base):
    """可被 citations 引用与校验的知识分片。"""

    __tablename__ = "ai_knowledge_chunks"
    __table_args__ = (
        Index("ix_chunks_owner_course", "owner_user_id", "course_id"),
        Index("ix_chunks_source", "source_type", "source_id"),
    )

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_type = Column(String(64), nullable=False, index=True)
    source_id = Column(String(128), nullable=True, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(JSON(none_as_null=True), nullable=True)
    owner_user_id = Column(String(64), nullable=True, index=True)
    course_id = Column(String(64), nullable=True, index=True)
    attempt_id = Column(String(64), nullable=True, index=True)
    metadata_json = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
