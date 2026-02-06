"""
通用审计事件模型（Gate-1 / C-001）。

用于统一记录：
- 访问拒绝（access_denied）
- 权限拒绝（permission_denied）
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, JSON, String, func

from .base import Base


class AuditEvent(Base):
    """统一审计事件表。"""

    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    actor_user_id = Column(String(64), nullable=True, index=True)
    action = Column(String(64), nullable=False, index=True)
    resource_type = Column(String(64), nullable=True, index=True)
    resource_id = Column(String(128), nullable=True, index=True)
    decision = Column(String(16), nullable=False, index=True)
    reason = Column(String(256), nullable=True)
    request_meta = Column(JSON, nullable=True)
    trace_id = Column(String(64), nullable=True, index=True)
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        index=True,
    )
