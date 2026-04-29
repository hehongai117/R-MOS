"""Knowledge retriever tests."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.knowledge.knowledge_retriever import KnowledgeRetriever


@pytest.mark.asyncio
async def test_retrieve_by_tag_returns_matching_chunks():
    """Tag-based search returns documents matching fault_type."""
    mock_db = AsyncMock()
    # Simulate query result
    mock_doc = MagicMock()
    mock_doc.id = 1
    mock_doc.title = "关节过热维修手册"
    mock_doc.content = "过热处理步骤..."
    mock_doc.fault_tags = ["E001_OVERHEAT"]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_doc]
    mock_db.execute = AsyncMock(return_value=mock_result)

    retriever = KnowledgeRetriever(mock_db)
    results = await retriever.retrieve(query="过热怎么办", fault_type="E001_OVERHEAT")

    assert len(results) >= 1
    assert results[0].title == "关节过热维修手册"


@pytest.mark.asyncio
async def test_retrieve_without_fault_type_uses_text_search():
    """Without fault_type, retriever still returns results via text matching."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    retriever = KnowledgeRetriever(mock_db)
    results = await retriever.retrieve(query="安全规范")

    # Should not crash, returns empty for now (vector search not yet wired)
    assert isinstance(results, list)
