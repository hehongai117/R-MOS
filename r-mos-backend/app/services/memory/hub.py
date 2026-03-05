"""
MemoryHub - P1-6-4
统一记忆接口，同时读写短期和长期记忆
"""
import logging
from typing import Any, Optional
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

try:
    from .short_term import ShortTermMemory
except Exception:  # pragma: no cover - optional dependency fallback
    class ShortTermMemory:  # type: ignore[no-redef]
        def __init__(self):
            self._store: dict[str, dict] = {}

        def read(self, session_id: str):
            return self._store.get(session_id)

        def write(self, session_id: str, data: dict) -> bool:
            self._store[session_id] = data
            return True

        def append(self, session_id: str, entry: dict) -> bool:
            current = self._store.get(session_id) or {"entries": []}
            current.setdefault("entries", []).append(entry)
            self._store[session_id] = current
            return True

        def delete(self, session_id: str) -> bool:
            self._store.pop(session_id, None)
            return True

try:
    from .long_term import LongTermMemory
except Exception:  # pragma: no cover - optional dependency fallback
    class LongTermMemory:  # type: ignore[no-redef]
        async def read(self, db: AsyncSession, user_id: str, session_id: Optional[str] = None):
            return []

        async def write(
            self,
            db: AsyncSession,
            user_id: str,
            session_id: str,
            trace_id: str,
            belief_state: dict,
            decision: Optional[str] = None,
        ):
            return None

        async def delete(self, db: AsyncSession, record_id: int) -> bool:
            return True

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """记忆条目"""
    source: str           # "short_term" | "long_term"
    session_id: str
    data: dict
    created_at: Optional[str] = None


class MemoryHub:
    """
    记忆中枢

    统一接口：
    - read(): 先查 Redis，再查 PostgreSQL
    - write(): 同时写两层
    """

    def __init__(self):
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()

    async def read(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> list[MemoryEntry]:
        """
        读取记忆

        先从 Redis 读取，再从 PostgreSQL 读取

        Args:
            session_id: 会话 ID
            user_id: 用户 ID (用于长期记忆)
            db: 数据库会话

        Returns:
            记忆条目列表
        """
        entries = []

        # 1. 从 Redis 读取短期记忆
        short_data = self.short_term.read(session_id)
        if short_data:
            entries.append(MemoryEntry(
                source="short_term",
                session_id=session_id,
                data=short_data,
            ))

        # 2. 从 PostgreSQL 读取长期记忆
        if db and user_id:
            long_records = await self.long_term.read(
                db=db,
                user_id=user_id,
                session_id=session_id
            )

            for record in long_records:
                entries.append(MemoryEntry(
                    source="long_term",
                    session_id=session_id,
                    data={
                        "belief_state": record.belief_state,
                        "decision": record.decision,
                        "trace_id": record.trace_id,
                    },
                    created_at=record.created_at.isoformat() if record.created_at else None
                ))

        return entries

    async def write(
        self,
        session_id: str,
        data: dict,
        user_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        is_long_term: bool = False,
    ) -> bool:
        """
        写入记忆

        Args:
            session_id: 会话 ID
            data: 记忆内容
            user_id: 用户 ID (用于长期记忆)
            trace_id: Trace ID (用于长期记忆)
            db: 数据库会话
            is_long_term: 是否写入长期记忆

        Returns:
            是否成功
        """
        success = True

        # 1. 写入 Redis (短期记忆)
        if not self.short_term.write(session_id, data):
            success = False
            logger.warning("Failed to write short-term memory")

        # 2. 写入 PostgreSQL (长期记忆)
        if is_long_term and db and user_id and trace_id:
            try:
                await self.long_term.write(
                    db=db,
                    user_id=user_id,
                    session_id=session_id,
                    trace_id=trace_id,
                    belief_state=data,
                )
            except Exception as e:
                success = False
                logger.warning(f"Failed to write long-term memory: {e}")

        return success

    async def append(
        self,
        session_id: str,
        entry: dict,
    ) -> bool:
        """
        追加记忆条目 (短期)

        Args:
            session_id: 会话 ID
            entry: 记忆条目

        Returns:
            是否成功
        """
        return self.short_term.append(session_id, entry)

    async def clear(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> bool:
        """
        清除记忆

        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            db: 数据库会话

        Returns:
            是否成功
        """
        success = True

        # 清除短期记忆
        if not self.short_term.delete(session_id):
            success = False

        # 清除长期记忆 (可选)
        if db and user_id:
            records = await self.long_term.read(db, user_id, session_id)
            for record in records:
                await self.long_term.delete(db, record.id)

        return success


# 全局实例
memory_hub = MemoryHub()
