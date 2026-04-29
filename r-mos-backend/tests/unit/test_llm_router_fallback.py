"""LLM Router fallback chain tests."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.llm.router import LLMRouter, LLMProvider, LLMResponse


@pytest.mark.asyncio
async def test_router_falls_back_to_secondary_on_timeout():
    """Router tries secondary provider when primary times out."""
    router = LLMRouter()

    # Primary (deepseek) raises timeout
    primary_client = AsyncMock()
    primary_client.chat = AsyncMock(side_effect=TimeoutError("DeepSeek timeout"))

    # Secondary (minimax) succeeds
    secondary_client = AsyncMock()
    secondary_client.chat = AsyncMock(return_value=("fallback content", 10, 5, {}))

    with patch.object(router, "_get_client") as mock_get:
        def side_effect(provider, **kwargs):
            if provider == LLMProvider.DEEPSEEK:
                return primary_client
            return secondary_client

        mock_get.side_effect = side_effect

        response = await router.chat_with_fallback(
            messages=[{"role": "user", "content": "test"}],
            model="deepseek-chat",
        )

        assert response.content == "fallback content"
        assert response.is_fallback is True


@pytest.mark.asyncio
async def test_router_falls_back_to_mock_when_all_fail():
    """Router uses mock when both providers fail."""
    router = LLMRouter()

    failing_client = AsyncMock()
    failing_client.chat = AsyncMock(side_effect=Exception("API Error"))

    with patch.object(router, "_get_client", return_value=failing_client):
        response = await router.chat_with_fallback(
            messages=[{"role": "user", "content": "诊断故障"}],
            model="deepseek-chat",
        )

        assert response.content != ""  # Mock returns something
        assert response.is_fallback is True
        assert response.provider_used == "mock"


@pytest.mark.asyncio
async def test_router_primary_success_no_fallback():
    """Router returns primary result without fallback."""
    router = LLMRouter()

    primary_client = AsyncMock()
    primary_client.chat = AsyncMock(return_value=("primary content", 100, 50, {}))

    with patch.object(router, "_get_client", return_value=primary_client):
        response = await router.chat_with_fallback(
            messages=[{"role": "user", "content": "test"}],
            model="deepseek-chat",
        )

        assert response.content == "primary content"
        assert response.is_fallback is False
