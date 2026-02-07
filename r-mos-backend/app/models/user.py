"""
用户模型（Gate-1 / A-001）。
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String

from .base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """认证用户表。"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(512), nullable=False)
    full_name = Column(String(200), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    last_login_at = Column(DateTime, nullable=True)
