"""
QueryEmbeddingService
面向检索查询的 embedding 包装层。
"""
from __future__ import annotations

from app.services.knowledge import embedding_service
from app.services.knowledge.fallback_embedding import fallback_embedding_service


class QueryEmbeddingService:
    """为知识检索生成 query embedding。"""

    async def embed_query(self, text: str) -> list[float]:
        if embedding_service is None:
            return fallback_embedding_service.embed(text)
        try:
            return await embedding_service.embed(text)
        except Exception:
            return fallback_embedding_service.embed(text)


query_embedding_service = QueryEmbeddingService()
