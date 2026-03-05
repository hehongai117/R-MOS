"""
Knowledge Services Package - P1-7
"""
try:
    from .embedding import EmbeddingService, embedding_service
except Exception:  # pragma: no cover - optional in partial environments
    EmbeddingService = None
    embedding_service = None

from .hub import KnowledgeHub, knowledge_hub, RetrievalResult
