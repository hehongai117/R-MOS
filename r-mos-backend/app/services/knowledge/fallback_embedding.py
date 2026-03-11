from __future__ import annotations

import hashlib
import math
import re


_TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fff]|[A-Za-z0-9_]+", re.UNICODE)


class FallbackEmbeddingService:
    def __init__(self, dimension: int = 1536) -> None:
        self.dimension = dimension

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = self._tokenize(text)
        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            primary = int.from_bytes(digest[:4], "big") % self.dimension
            secondary = int.from_bytes(digest[4:8], "big") % self.dimension
            tertiary = int.from_bytes(digest[8:12], "big") % self.dimension
            sign = 1.0 if digest[12] % 2 == 0 else -1.0
            vector[primary] += sign * 1.0
            vector[secondary] += sign * 0.5
            vector[tertiary] += sign * 0.25

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]

    def _tokenize(self, text: str) -> list[str]:
        return [token.lower() for token in _TOKEN_PATTERN.findall(text or "")]


fallback_embedding_service = FallbackEmbeddingService()
