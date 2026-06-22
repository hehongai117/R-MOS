"""
KnowledgeHub - P1-7-4
混合检索 API: 关键词召回 + 向量语义召回 + 简单重排序
"""
import logging
import math
from typing import Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_chunk import AIKnowledgeChunk as KnowledgeChunk

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """检索结果"""
    chunk_id: str
    title: str
    content: str
    source: str           # "keyword" | "semantic" | "hybrid"
    score: float
    metadata: Optional[dict] = None


class KnowledgeHub:
    """
    知识中枢

    支持混合检索：
    1. 关键词召回 (BM25 风格)
    2. 向量语义召回 (需要 embedding)
    3. 重排序 (简单分数融合)
    """

    def __init__(self):
        self._top_k = 5

    async def search(
        self,
        db: AsyncSession,
        query: str,
        embedding: Optional[list[float]] = None,
        top_k: int = 5,
        use_hybrid: bool = True,
        filters: Optional[dict[str, Any]] = None,
        allow_degraded: bool = False,
        allow_expired: bool = False,
    ) -> list[RetrievalResult]:
        """
        搜索知识

        Args:
            db: 数据库会话
            query: 查询文本
            embedding: query 的 embedding (可选，用于语义召回)
            top_k: 返回数量
            use_hybrid: 是否使用混合检索

        Returns:
            检索结果列表
        """
        results = []

        # 1. 关键词召回
        keyword_results = await self._keyword_search(db, query, top_k * 2)
        results.extend(keyword_results)

        # 2. 向量语义召回 (如果提供了 embedding)
        if embedding:
            semantic_results = await self._semantic_search(
                db, embedding, top_k * 2
            )
            results.extend(semantic_results)

        # 3. 重排序
        if use_hybrid and len(results) > 1:
            results = self._rerank(results)

        # 4. 过滤（品牌/型号 + 过期）
        filtered = self._apply_filters(
            results=results,
            filters=filters,
            allow_expired=allow_expired,
        )

        # 5. 降级策略：若过滤后为空，可放宽过期过滤
        if allow_degraded and not filtered:
            filtered = self._apply_filters(
                results=results,
                filters=filters,
                allow_expired=True,
            )

        # 6. 取 top_k
        return filtered[:top_k]

    async def _keyword_search(
        self,
        db: AsyncSession,
        query: str,
        limit: int,
    ) -> list[RetrievalResult]:
        """关键词搜索"""
        try:
            # 简单的 LIKE 匹配
            query_lower = query.lower()
            keywords = query_lower.split()

            conditions = []
            for kw in keywords:
                conditions.append(
                    or_(
                        KnowledgeChunk.content.ilike(f"%{kw}%"),
                        KnowledgeChunk.source_id.ilike(f"%{kw}%"),
                    )
                )

            result = await db.execute(
                select(KnowledgeChunk).where(
                    and_(*conditions)
                ).limit(limit)
            )

            chunks = result.scalars().all()
            return [
                RetrievalResult(
                    chunk_id=c.id,
                    title=c.source_id or "chunk",
                    content=c.content[:200],
                    source="keyword",
                    score=0.5,  # 简单分数
                    metadata=c.metadata_json if isinstance(c.metadata_json, dict) else None,
                )
                for c in chunks
            ]
        except Exception as e:
            logger.warning(f"Keyword search failed: {e}")
            return []

    async def _semantic_search(
        self,
        db: AsyncSession,
        embedding: list[float],
        limit: int,
    ) -> list[RetrievalResult]:
        """语义向量搜索。

        PostgreSQL 环境优先走 pgvector 余弦相似度；
        其余测试/降级环境回退到 Python 余弦计算，避免重新退化为随机结果。
        """
        try:
            bind = db.get_bind()
            if bind is not None and bind.dialect.name == "postgresql":
                try:
                    return await self._semantic_search_pgvector(db, embedding, limit)
                except Exception as exc:
                    logger.warning(f"pgvector semantic search failed, falling back to Python cosine search: {exc}")

            return await self._semantic_search_python(db, embedding, limit)
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            return []

    async def _semantic_search_pgvector(
        self,
        db: AsyncSession,
        embedding: list[float],
        limit: int,
    ) -> list[RetrievalResult]:
        query_vector = "[" + ",".join(f"{value:.12g}" for value in embedding) + "]"
        result = await db.execute(
            text(
                """
                SELECT
                    id,
                    source_id,
                    content,
                    metadata,
                    1 - (embedding_vec <=> CAST(:query_vector AS vector)) AS similarity
                FROM ai_knowledge_chunks
                WHERE embedding_vec IS NOT NULL
                ORDER BY embedding_vec <=> CAST(:query_vector AS vector)
                LIMIT :limit
                """
            ),
            {"query_vector": query_vector, "limit": limit},
        )

        rows = result.mappings().all()
        return [
            RetrievalResult(
                chunk_id=str(row["id"]),
                title=row.get("source_id") or "chunk",
                content=str(row["content"])[:200],
                source="semantic",
                score=float(row["similarity"]),
                metadata=row.get("metadata") if isinstance(row.get("metadata"), dict) else None,
            )
            for row in rows
        ]

    async def _semantic_search_python(
        self,
        db: AsyncSession,
        embedding: list[float],
        limit: int,
    ) -> list[RetrievalResult]:
        result = await db.execute(
            select(KnowledgeChunk).where(
                KnowledgeChunk.embedding.isnot(None)
            )
        )
        chunks = result.scalars().all()

        scored_results: list[RetrievalResult] = []
        for chunk in chunks:
            similarity = self._cosine_similarity(embedding, chunk.embedding)
            if similarity is None:
                continue
            scored_results.append(
                RetrievalResult(
                    chunk_id=chunk.id,
                    title=chunk.source_id or "chunk",
                    content=chunk.content[:200],
                    source="semantic",
                    score=similarity,
                    metadata=chunk.metadata_json if isinstance(chunk.metadata_json, dict) else None,
                )
            )

        scored_results.sort(key=lambda item: item.score, reverse=True)
        return scored_results[:limit]

    def _cosine_similarity(
        self,
        query_embedding: list[float],
        chunk_embedding: Any,
    ) -> Optional[float]:
        if not isinstance(chunk_embedding, list) or len(query_embedding) != len(chunk_embedding):
            return None
        if not query_embedding or not chunk_embedding:
            return None

        dot_product = sum(q * c for q, c in zip(query_embedding, chunk_embedding))
        query_norm = math.sqrt(sum(q * q for q in query_embedding))
        chunk_norm = math.sqrt(sum(c * c for c in chunk_embedding))
        if query_norm == 0 or chunk_norm == 0:
            return None

        return dot_product / (query_norm * chunk_norm)

    def _rerank(
        self,
        results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        """重排序 (简单分数融合)"""
        # 按分数排序
        # 如果有多个来源相同 chunk_id，合并分数
        seen = {}
        for r in results:
            if r.chunk_id in seen:
                seen[r.chunk_id].score += r.score
                if seen[r.chunk_id].source != r.source:
                    seen[r.chunk_id].source = "hybrid"
            else:
                seen[r.chunk_id] = r

        # 重新排序
        return sorted(seen.values(), key=lambda x: x.score, reverse=True)

    def _apply_filters(
        self,
        results: list[RetrievalResult],
        filters: Optional[dict[str, Any]],
        allow_expired: bool,
    ) -> list[RetrievalResult]:
        filtered: list[RetrievalResult] = []
        for item in results:
            if not self._matches_filters(item, filters):
                continue
            if not allow_expired and self._is_expired(item):
                continue
            filtered.append(item)
        return filtered

    def _matches_filters(self, result: RetrievalResult, filters: Optional[dict[str, Any]]) -> bool:
        if not filters:
            return True
        metadata = result.metadata or {}
        for key, expected in filters.items():
            if expected in (None, ""):
                continue
            actual = metadata.get(key)
            if str(actual).lower() != str(expected).lower():
                return False
        return True

    def _is_expired(self, result: RetrievalResult) -> bool:
        metadata = result.metadata or {}
        expires_at_raw = metadata.get("expires_at")
        if not expires_at_raw:
            return False
        try:
            expires_at = self._parse_datetime(str(expires_at_raw))
            return expires_at <= datetime.now(timezone.utc)
        except Exception:
            return False

    def _parse_datetime(self, raw: str) -> datetime:
        normalized = raw.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed


# 全局实例
knowledge_hub = KnowledgeHub()
