"""
ShortTermMemory - P1-6-2
Redis-based session-level memory with TTL
"""
import json
import logging
from typing import Any, Optional

try:
    import redis
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    redis = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """
    短期记忆层 (Redis)

    用于存储会话级信息，TTL 默认 30 分钟
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        ttl_seconds: int = 1800,  # 30 分钟
    ):
        self._client = None
        self._fallback_store: dict[str, str] = {}
        if redis is not None:
            self._client = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=True
            )
        self._ttl = ttl_seconds

    def _make_key(self, session_id: str) -> str:
        """生成 Redis key"""
        return f"memory:session:{session_id}"

    def read(self, session_id: str) -> Optional[dict]:
        """
        读取会话记忆

        Args:
            session_id: 会话 ID

        Returns:
            记忆内容，不存在则返回 None
        """
        try:
            key = self._make_key(session_id)
            if self._client is None:
                data = self._fallback_store.get(key)
            else:
                data = self._client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning(f"Failed to read short-term memory: {e}")
            return None

    def write(self, session_id: str, data: dict) -> bool:
        """
        写入会话记忆

        Args:
            session_id: 会话 ID
            data: 记忆内容

        Returns:
            是否成功
        """
        try:
            key = self._make_key(session_id)
            dumped = json.dumps(data, ensure_ascii=False)
            if self._client is None:
                self._fallback_store[key] = dumped
            else:
                self._client.setex(
                    key,
                    self._ttl,
                    dumped
                )
            return True
        except Exception as e:
            logger.warning(f"Failed to write short-term memory: {e}")
            return False

    def append(self, session_id: str, entry: dict) -> bool:
        """
        追加记忆条目

        Args:
            session_id: 会话 ID
            entry: 记忆条目

        Returns:
            是否成功
        """
        current = self.read(session_id) or {"entries": []}
        current["entries"].append(entry)
        return self.write(session_id, current)

    def delete(self, session_id: str) -> bool:
        """
        删除会话记忆

        Args:
            session_id: 会话 ID

        Returns:
            是否成功
        """
        try:
            key = self._make_key(session_id)
            if self._client is None:
                self._fallback_store.pop(key, None)
            else:
                self._client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Failed to delete short-term memory: {e}")
            return False

    def exists(self, session_id: str) -> bool:
        """检查会话记忆是否存在"""
        try:
            key = self._make_key(session_id)
            if self._client is None:
                return key in self._fallback_store
            return bool(self._client.exists(key))
        except Exception:
            return False

    def refresh(self, session_id: str) -> bool:
        """刷新 TTL"""
        try:
            key = self._make_key(session_id)
            if self._client is None:
                return key in self._fallback_store
            return self._client.expire(key, self._ttl)
        except Exception:
            return False


# 全局实例
short_term_memory = ShortTermMemory()
