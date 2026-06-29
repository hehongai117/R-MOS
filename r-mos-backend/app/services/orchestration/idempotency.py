"""
IdempotencyCache — in-memory idempotency cache.

Verbatim move from orchestrator_v2.py (Phase 3 refactor).
"""

import time
from typing import Dict, Any, Optional


class IdempotencyCache:
    """In-memory idempotency cache"""

    def __init__(self, ttl_seconds: int = 3600):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._timestamps: Dict[str, int] = {}
        self._ttl_seconds = ttl_seconds

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached response"""
        # Check expiry
        if key in self._timestamps:
            if time.time() - self._timestamps[key] > self._ttl_seconds:
                del self._cache[key]
                del self._timestamps[key]
                return None
        return self._cache.get(key)

    def set(self, key: str, value: Dict[str, Any]):
        """Cache response"""
        self._cache[key] = value
        self._timestamps[key] = int(time.time())

    def has(self, key: str) -> bool:
        """Check if key exists and is valid"""
        if key not in self._cache:
            return False
        # Check expiry
        if time.time() - self._timestamps[key] > self._ttl_seconds:
            del self._cache[key]
            del self._timestamps[key]
            return False
        return True

    def clear(self):
        """Clear all cache"""
        self._cache.clear()
        self._timestamps.clear()
