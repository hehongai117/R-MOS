"""
访问令牌持久化模型（Gate-1 / B-001）。
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String

from .base import Base, TimestampMixin


class AccessToken(Base, TimestampMixin):
    """访问令牌持久化表。"""

    __tablename__ = "access_tokens"
    __table_args__ = (
        Index("ix_access_tokens_user_id", "user_id"),
        Index("ix_access_tokens_access_token_hash", "access_token_hash"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    access_token_hash = Column(String(64), nullable=False, unique=True)
    issued_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, nullable=False, default=False)
    revoked_at = Column(DateTime, nullable=True)
