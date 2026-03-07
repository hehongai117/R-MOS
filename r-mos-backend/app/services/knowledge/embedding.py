"""
EmbeddingService - P1-7-2
生成文本 embedding 向量
"""
import logging
from typing import Optional

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Embedding 生成服务

    使用 OpenAI text-embedding-3-small 模型
    """

    def __init__(self, model: str = "text-embedding-3-small"):
        self._client = AsyncOpenAI()
        self._model = model

    async def embed(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> list[float]:
        """
        生成 embedding 向量

        Args:
            text: 输入文本
            model: 模型名称 (可选)

        Returns:
            embedding 向量 (1536 维)
        """
        try:
            response = await self._client.embeddings.create(
                input=text,
                model=model or self._model,
            )

            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}")
            raise

    async def embed_batch(
        self,
        texts: list[str],
        model: Optional[str] = None,
    ) -> list[list[float]]:
        """
        批量生成 embedding

        Args:
            texts: 输入文本列表
            model: 模型名称 (可选)

        Returns:
            embedding 向量列表
        """
        try:
            response = await self._client.embeddings.create(
                input=texts,
                model=model or self._model,
            )

            # 按顺序返回
            embeddings = [item.embedding for item in response.data]
            return sorted(embeddings, key=lambda x: response.data[embeddings.index(x)].index)
        except Exception as e:
            logger.warning(f"Batch embedding generation failed: {e}")
            raise


# 全局实例
embedding_service = EmbeddingService()
