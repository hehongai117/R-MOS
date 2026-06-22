"""
LongTermMemory - P1-6-3
PostgreSQL-based persistent memory
"""
import logging
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_runtime import BeliefStateRecord

logger = logging.getLogger(__name__)


class LongTermMemory:
    """
    长期记忆层 (PostgreSQL)

    用于存储持久化的信念状态和决策记录
    """

    def __init__(self):
        pass

    async def read(
        self,
        db: AsyncSession,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> list[BeliefStateRecord]:
        """
        读取长期记忆

        Args:
            db: 数据库会话
            user_id: 用户 ID
            session_id: 会话 ID (可选)

        Returns:
            记忆记录列表
        """
        try:
            query = select(BeliefStateRecord).where(
                BeliefStateRecord.user_id == user_id
            )

            if session_id:
                query = query.where(
                    BeliefStateRecord.session_id == session_id
                )

            result = await db.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.warning(f"Failed to read long-term memory: {e}")
            return []

    async def write(
        self,
        db: AsyncSession,
        user_id: str,
        session_id: str,
        trace_id: str,
        belief_state: dict,
        decision: Optional[str] = None,
    ) -> BeliefStateRecord:
        """
        写入长期记忆

        Args:
            db: 数据库会话
            user_id: 用户 ID
            session_id: 会话 ID
            trace_id: Trace ID
            belief_state: 信念状态
            decision: 决策 (可选)

        Returns:
            创建的记录
        """
        try:
            record = BeliefStateRecord(
                user_id=user_id,
                session_id=session_id,
                trace_id=trace_id,
                belief_state=belief_state,
                decision=decision,
                created_at=datetime.now(timezone.utc),
            )

            db.add(record)
            await db.commit()
            await db.refresh(record)

            return record
        except Exception as e:
            logger.warning(f"Failed to write long-term memory: {e}")
            await db.rollback()
            raise

    async def update(
        self,
        db: AsyncSession,
        record_id: int,
        updates: dict,
    ) -> Optional[BeliefStateRecord]:
        """
        更新长期记忆

        Args:
            db: 数据库会话
            record_id: 记录 ID
            updates: 更新内容

        Returns:
            更新后的记录
        """
        try:
            result = await db.execute(
                select(BeliefStateRecord).where(
                    BeliefStateRecord.id == record_id
                )
            )
            record = result.scalar_one_or_none()

            if record:
                for key, value in updates.items():
                    if hasattr(record, key):
                        setattr(record, key, value)

                await db.commit()
                await db.refresh(record)

            return record
        except Exception as e:
            logger.warning(f"Failed to update long-term memory: {e}")
            await db.rollback()
            return None

    async def delete(
        self,
        db: AsyncSession,
        record_id: int,
    ) -> bool:
        """
        删除长期记忆

        Args:
            db: 数据库会话
            record_id: 记录 ID

        Returns:
            是否成功
        """
        try:
            result = await db.execute(
                select(BeliefStateRecord).where(
                    BeliefStateRecord.id == record_id
                )
            )
            record = result.scalar_one_or_none()

            if record:
                await db.delete(record)
                await db.commit()
                return True

            return False
        except Exception as e:
            logger.warning(f"Failed to delete long-term memory: {e}")
            await db.rollback()
            return False


# 全局实例
long_term_memory = LongTermMemory()
