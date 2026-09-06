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
        viewer_user_id: Optional[int] = None,
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

        # 审计 C-AUTH-01／C-AUTH-05：检索此前不按条目归属过滤，
        # 任何调用者都能召回他人（含他校）的私有知识块。
        # 口径与模块 F 一致（见 `ownership.py` 的 `ensure_user_scope` 文档）：
        # **同校可读是既定设计，跨校不是**——学校是租户边界。
        # `viewer_user_id` 缺省表示无调用者身份（后台任务等），此时只放行公共条目。
        visible_owner_ids = await self._resolve_visible_owner_ids(db, viewer_user_id)

        # 1. 关键词召回
        keyword_results = await self._keyword_search(
            db, query, top_k * 2, visible_owner_ids=visible_owner_ids
        )
        results.extend(keyword_results)

        # 2. 向量语义召回 (如果提供了 embedding)
        if embedding:
            semantic_results = await self._semantic_search(
                db, embedding, top_k * 2, visible_owner_ids=visible_owner_ids
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


    async def _resolve_visible_owner_ids(
        self,
        db: AsyncSession,
        viewer_user_id: Optional[int],
    ) -> Optional[set[str]]:
        """返回该调用者可见的私有条目 owner 集合；`None` 表示不限制（管理员）。

        公共条目（`owner_user_id IS NULL`）对所有人可见，不在本集合内单独表达。
        无 `viewer_user_id`（后台任务等）返回空集——只剩公共条目可见。
        """
        if viewer_user_id is None:
            return set()

        from app.models.user import User

        viewer = (
            await db.execute(select(User).where(User.id == viewer_user_id))
        ).scalar_one_or_none()
        if viewer is None:
            return set()
        if (viewer.role or "").strip().lower() == "admin":
            return None

        if not viewer.school_name:
            return {str(viewer.id)}

        same_school = await db.execute(
            select(User.id).where(User.school_name == viewer.school_name)
        )
        return {str(uid) for uid in same_school.scalars()}

    @staticmethod
    def _owner_visibility_clause(visible_owner_ids: Optional[set[str]]):
        """构造归属可见性条件；`None` 表示不加限制。"""
        if visible_owner_ids is None:
            return None
        public_only = KnowledgeChunk.owner_user_id.is_(None)
        if not visible_owner_ids:
            return public_only
        return or_(public_only, KnowledgeChunk.owner_user_id.in_(visible_owner_ids))

    async def _keyword_search(
        self,
        db: AsyncSession,
        query: str,
        limit: int,
        visible_owner_ids: Optional[set[str]] = None,
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

            visibility = self._owner_visibility_clause(visible_owner_ids)
            where_clause = and_(*conditions) if visibility is None else and_(*conditions, visibility)
            result = await db.execute(
                select(KnowledgeChunk).where(where_clause).limit(limit)
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
        visible_owner_ids: Optional[set[str]] = None,
    ) -> list[RetrievalResult]:
        """语义向量搜索。

        PostgreSQL 环境优先走 pgvector 余弦相似度；
        其余测试/降级环境回退到 Python 余弦计算，避免重新退化为随机结果。
        """
        try:
            bind = db.get_bind()
            if bind is not None and bind.dialect.name == "postgresql":
                try:
                    # SAVEPOINT 隔离 pgvector 查询：失败时只回滚到 savepoint，
                    # 外部事务及已加载的 ORM 对象均不受影响（不 expire）。
                    async with db.begin_nested():
                        return await self._semantic_search_pgvector(db, embedding, limit, visible_owner_ids)
                except Exception as exc:
                    logger.warning(f"pgvector semantic search failed, falling back to Python cosine search: {exc}")

            return await self._semantic_search_python(db, embedding, limit, visible_owner_ids)
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            return []

    async def _semantic_search_pgvector(
        self,
        db: AsyncSession,
        embedding: list[float],
        limit: int,
        visible_owner_ids: Optional[set[str]] = None,
    ) -> list[RetrievalResult]:
        query_vector = "[" + ",".join(f"{value:.12g}" for value in embedding) + "]"
        params: dict[str, Any] = {"query_vector": query_vector, "limit": limit}
        # 归属可见性必须**在 SQL 里**过滤：若先取回再筛，pgvector 的 LIMIT
        # 会先被他人条目占满，同校条目反而被挤掉。
        if visible_owner_ids is None:
            visibility_sql = ""
        elif visible_owner_ids:
            visibility_sql = " AND (owner_user_id IS NULL OR owner_user_id = ANY(:owner_ids))"
            params["owner_ids"] = list(visible_owner_ids)
        else:
            visibility_sql = " AND owner_user_id IS NULL"
        result = await db.execute(
            text(
                f"""
                SELECT
                    id,
                    source_id,
                    content,
                    metadata,
                    1 - (embedding_vec <=> CAST(:query_vector AS vector)) AS similarity
                FROM ai_knowledge_chunks
                WHERE embedding_vec IS NOT NULL{visibility_sql}
                ORDER BY embedding_vec <=> CAST(:query_vector AS vector)
                LIMIT :limit
                """
            ),
            params,
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
        visible_owner_ids: Optional[set[str]] = None,
    ) -> list[RetrievalResult]:
        visibility = self._owner_visibility_clause(visible_owner_ids)
        base = KnowledgeChunk.embedding.isnot(None)
        result = await db.execute(
            select(KnowledgeChunk).where(
                base if visibility is None else and_(base, visibility)
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
