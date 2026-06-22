"""
SQLAlchemy Base类定义（V2.0+兼容版）
"""
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, DateTime
from sqlalchemy.types import TypeDecorator
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


class TZDateTime(TypeDecorator):
    """UTC-aware DateTime that round-trips consistently across backends.

    Columns store timezone-aware UTC datetimes. On backends without native
    timezone support (e.g. SQLite used in tests), values read back are
    naive; this decorator coerces them to UTC-aware so application code
    never mixes naive and aware datetimes when comparing. PostgreSQL
    already round-trips aware values, so this is a no-op there.

    Emits the same DDL as ``DateTime(timezone=True)``, so existing Alembic
    migrations remain valid.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value


class Base(DeclarativeBase):
    """SQLAlchemy 2.0+ 声明式基类"""
    pass


class TimestampMixin:
    """时间戳Mixin

    所有模型自动添加创建时间和更新时间
    """
    created_at = Column(TZDateTime, default=utcnow, nullable=False)
    updated_at = Column(TZDateTime, default=utcnow, onupdate=utcnow, nullable=False)
