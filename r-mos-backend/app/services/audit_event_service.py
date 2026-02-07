"""
通用审计事件服务（Gate-1 / C-001）。
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_event import AuditEvent

logger = logging.getLogger(__name__)


class AuditEventService:
    """统一审计写入服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_event(
        self,
        *,
        action: str,
        decision: str,
        actor_user_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        reason: str | None = None,
        request_meta: dict[str, Any] | None = None,
        trace_id: str | None = None,
        skill_id: str | None = None,
        skill_version: str | None = None,
        tool_call_args: dict[str, Any] | None = None,
        side_effects_applied: list[str] | None = None,
        approval_id: int | None = None,
    ) -> AuditEvent | None:
        """写入审计事件。

        失败时不抛出异常，避免覆盖原始业务错误。
        """
        event = AuditEvent(
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            decision=decision,
            reason=reason,
            request_meta=request_meta or {},
            trace_id=trace_id,
            skill_id=skill_id,
            skill_version=skill_version,
            tool_call_args=tool_call_args,
            side_effects_applied=side_effects_applied,
            approval_id=approval_id,
        )
        try:
            self.db.add(event)
            await self.db.commit()
            await self.db.refresh(event)
            return event
        except Exception:
            logger.exception("审计写入失败: action=%s resource=%s:%s", action, resource_type, resource_id)
            await self.db.rollback()
            return None
