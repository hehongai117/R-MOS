"""
SQLAlchemy Base类定义（V2.0+兼容版）
"""
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, DateTime
from datetime import datetime


class Base(DeclarativeBase):
    """SQLAlchemy 2.0+ 声明式基类"""
    pass


class TimestampMixin:
    """时间戳Mixin

    所有模型自动添加创建时间和更新时间
    """
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
