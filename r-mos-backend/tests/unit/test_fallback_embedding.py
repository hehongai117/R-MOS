from __future__ import annotations

import math

from app.services.knowledge.fallback_embedding import FallbackEmbeddingService


def test_fallback_embedding_is_deterministic_and_1536_dimensional() -> None:
    service = FallbackEmbeddingService()

    first = service.embed("执行器弯曲维护 肘关节")
    second = service.embed("执行器弯曲维护 肘关节")

    assert len(first) == 1536
    assert first == second
    assert any(value != 0 for value in first)


def test_fallback_embedding_batch_aligns_with_single_embed() -> None:
    service = FallbackEmbeddingService()

    texts = ["执行器弯曲维护", "腕关节复核"]
    batch = service.embed_batch(texts)

    assert batch[0] == service.embed(texts[0])
    assert batch[1] == service.embed(texts[1])
    assert math.isclose(sum(value * value for value in batch[0]), 1.0, rel_tol=1e-6, abs_tol=1e-6)
