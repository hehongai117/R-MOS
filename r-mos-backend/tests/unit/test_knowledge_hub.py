"""
P1-7-4: KnowledgeHub hybrid retrieval tests.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.models.knowledge_chunk import AIKnowledgeChunk
from app.services.knowledge.hub import KnowledgeHub


def _chunk(
    *,
    source_id: str,
    content: str,
    embedding: list[float] | None,
    metadata_json: dict | None = None,
) -> AIKnowledgeChunk:
    return AIKnowledgeChunk(
        source_type="manual",
        source_id=source_id,
        content=content,
        embedding=embedding,
        metadata_json=metadata_json,
        created_at=datetime.utcnow(),
    )


@pytest.mark.asyncio
async def test_knowledge_hub_hybrid_fusion(test_db):
    test_db.add_all(
        [
            _chunk(
                source_id="chunk-1",
                content="ABB IRB1200 motor maintenance guide",
                embedding=[0.1, 0.2, 0.3],
                metadata_json={"brand": "ABB", "model": "IRB1200"},
            ),
            _chunk(
                source_id="chunk-2",
                content="ABB IRB1200 emergency stop checklist",
                embedding=None,
                metadata_json={"brand": "ABB", "model": "IRB1200"},
            ),
        ]
    )
    await test_db.commit()

    hub = KnowledgeHub()
    results = await hub.search(
        db=test_db,
        query="ABB IRB1200",
        embedding=[0.1, 0.2, 0.3],
        top_k=5,
        use_hybrid=True,
        filters={"brand": "ABB", "model": "IRB1200"},
    )

    assert len(results) >= 2
    assert results[0].score >= results[1].score


@pytest.mark.asyncio
async def test_knowledge_hub_filters_out_expired_chunks(test_db):
    test_db.add_all(
        [
            _chunk(
                source_id="chunk-expired",
                content="ABB old SOP",
                embedding=[0.1],
                metadata_json={
                    "brand": "ABB",
                    "model": "IRB1200",
                    "expires_at": "2000-01-01T00:00:00",
                },
            ),
            _chunk(
                source_id="chunk-fresh",
                content="ABB fresh SOP",
                embedding=[0.2],
                metadata_json={
                    "brand": "ABB",
                    "model": "IRB1200",
                    "expires_at": "2099-01-01T00:00:00",
                },
            ),
        ]
    )
    await test_db.commit()

    hub = KnowledgeHub()
    results = await hub.search(
        db=test_db,
        query="ABB SOP",
        embedding=[0.2],
        top_k=5,
        filters={"brand": "ABB", "model": "IRB1200"},
    )

    source_ids = [item.title for item in results]
    assert "chunk-fresh" in source_ids
    assert "chunk-expired" not in source_ids


@pytest.mark.asyncio
async def test_knowledge_hub_degraded_mode_relaxes_expired_filter(test_db):
    test_db.add(
        _chunk(
            source_id="only-expired",
            content="KUKA old SOP",
            embedding=[0.3],
            metadata_json={
                "brand": "KUKA",
                "model": "KR6",
                "expires_at": "2000-01-01T00:00:00",
            },
        )
    )
    await test_db.commit()

    hub = KnowledgeHub()
    results = await hub.search(
        db=test_db,
        query="KUKA KR6",
        embedding=[0.3],
        top_k=5,
        filters={"brand": "KUKA", "model": "KR6"},
        allow_degraded=True,
    )

    assert results
    assert results[0].title == "only-expired"


@pytest.mark.asyncio
async def test_knowledge_hub_semantic_search_ranks_by_similarity(test_db):
    test_db.add_all(
        [
            _chunk(
                source_id="chunk-far",
                content="General maintenance appendix",
                embedding=[0.0, 1.0, 0.0],
            ),
            _chunk(
                source_id="chunk-mid",
                content="Motor inspection checklist",
                embedding=[0.7, 0.3, 0.0],
            ),
            _chunk(
                source_id="chunk-near",
                content="Motor stall recovery procedure",
                embedding=[1.0, 0.0, 0.0],
            ),
        ]
    )
    await test_db.commit()

    hub = KnowledgeHub()
    results = await hub._semantic_search(
        db=test_db,
        embedding=[1.0, 0.0, 0.0],
        limit=3,
    )

    assert [item.title for item in results] == ["chunk-near", "chunk-mid", "chunk-far"]
    assert results[0].score > results[1].score > results[2].score
