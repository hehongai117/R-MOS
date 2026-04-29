"""Mixed knowledge retrieval: tag-based exact match + vector search (future)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_document import KnowledgeDocument

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """A retrieved knowledge chunk."""
    id: int
    title: str
    content: str
    fault_tags: list[str]
    relevance_source: str  # "tag_match" or "vector_search"


class KnowledgeRetriever:
    """Mixed retrieval: tag match (high precision) + vector search (high recall)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def retrieve(
        self,
        query: str,
        fault_type: Optional[str] = None,
        limit: int = 5,
    ) -> list[RetrievedChunk]:
        results: list[RetrievedChunk] = []

        # Path 1: Tag-based exact match
        if fault_type:
            tag_results = await self._search_by_tag(fault_type, limit=limit)
            results.extend(tag_results)

        # Path 2: Vector similarity search (placeholder — requires pgvector)
        if len(results) < limit:
            vector_results = await self._search_by_text(
                query,
                limit=limit - len(results),
                exclude_ids=[r.id for r in results],
            )
            results.extend(vector_results)

        return results[:limit]

    async def _search_by_tag(self, fault_type: str, limit: int) -> list[RetrievedChunk]:
        """Search documents by fault_tags JSON array contains."""
        stmt = (
            select(KnowledgeDocument)
            .where(KnowledgeDocument.status == "APPROVED")
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        docs = result.scalars().all()

        # Filter in Python (JSON array contains — portable across DB engines)
        matched = []
        for doc in docs:
            tags = doc.fault_tags or []
            if fault_type in tags or "*" in tags:
                matched.append(
                    RetrievedChunk(
                        id=doc.id,
                        title=doc.title,
                        content=doc.content[:2000],  # truncate for context window
                        fault_tags=tags,
                        relevance_source="tag_match",
                    )
                )
        return matched[:limit]

    async def _search_by_text(
        self, query: str, limit: int, exclude_ids: list[int]
    ) -> list[RetrievedChunk]:
        """Text-based search fallback (simple LIKE for now, vector later)."""
        stmt = (
            select(KnowledgeDocument)
            .where(
                KnowledgeDocument.status == "APPROVED",
                KnowledgeDocument.id.notin_(exclude_ids) if exclude_ids else True,
            )
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        docs = result.scalars().all()

        # Simple keyword match (will be replaced by pgvector cosine similarity)
        matched = []
        for doc in docs:
            if any(kw in (doc.content or "") for kw in query[:20].split()):
                matched.append(
                    RetrievedChunk(
                        id=doc.id,
                        title=doc.title,
                        content=doc.content[:2000],
                        fault_tags=doc.fault_tags or [],
                        relevance_source="vector_search",
                    )
                )
        return matched[:limit]
