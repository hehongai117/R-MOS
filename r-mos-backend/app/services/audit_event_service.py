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
        _deny_entrypoint: str | None = None,
    ) -> AuditEvent | None:
        """写入审计事件。

        失败时不抛出异常，避免覆盖原始业务错误。
        """
        # Gate-1 B-002 约束：deny 审计必须经由 access_control.log_deny_event 统一进入。
        if decision == "deny" and _deny_entrypoint != "access_control.log_deny_event":
            logger.error(
                "拒绝写入散落入口: action=%s resource=%s:%s",
                action,
                resource_type,
                resource_id,
            )
            raise ValueError("deny 审计必须通过 access_control.log_deny_event")

        event = AuditEvent(
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            decision=decision,
            reason=reason,
            request_meta=request_meta or {},
            trace_id=trace_id,
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
