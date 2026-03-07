"""
LLM Audit Middleware - P1-1-3
自动将 LLM 调用写入 audit_events 表
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_event import AuditEvent

logger = logging.getLogger(__name__)


class LLMAuditMiddleware:
    """LLM 调用审计中间件"""

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db

    async def write_audit(
        self,
        prompt_hash: str,
        response_hash: str,
        provider: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
        action: str = "llm_call",
        actor_user_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        **kwargs,
    ) -> AuditEvent:
        """
        写入审计记录

        Args:
            prompt_hash: Prompt 内容哈希
            response_hash: Response 内容哈希
            provider: LLM Provider
            model: 模型名称
            tokens_in: 输入 token 数
            tokens_out: 输出 token 数
            action: 操作类型
            actor_user_id: 用户 ID
            trace_id: Trace ID

        Returns:
            AuditEvent: 审计记录
        """
        if not self.db:
            logger.warning("No database session, skipping audit")
            return None

        audit_event = AuditEvent(
            actor_user_id=actor_user_id,
            action=action,
            resource_type="llm",
            resource_id=f"{provider}:{model}",
            decision="success" if tokens_out > 0 else "fallback",
            reason=f"tokens_in={tokens_in}, tokens_out={tokens_out}",
            trace_id=trace_id,
            # LLM 审计字段
            prompt_hash=prompt_hash,
            response_hash=response_hash,
            provider=provider,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            request_meta=kwargs.get("request_meta"),
        )

        self.db.add(audit_event)
        await self.db.commit()
        await self.db.refresh(audit_event)

        logger.info(
            f"LLM audit written: provider={provider}, model={model}, "
            f"tokens_in={tokens_in}, tokens_out={tokens_out}"
        )

        return audit_event


# 全局实例
llm_audit = LLMAuditMiddleware()
