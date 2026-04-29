"""MiniMax Provider unit tests."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.llm.minimax_provider import MiniMaxClient


@pytest.mark.asyncio
async def test_minimax_chat_returns_content():
    """MiniMax client returns content from HTTP API."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "维保建议：检查散热风扇"}}],
        "usage": {"prompt_tokens": 80, "completion_tokens": 30},
    }
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.llm.minimax_provider.httpx.AsyncClient") as MockHttpx:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        MockHttpx.return_value = mock_client

        client = MiniMaxClient(api_key="test-key", group_id="test-group")
        content, tokens_in, tokens_out, raw = await client.chat(
            messages=[{"role": "user", "content": "如何处理过热"}],
            model="abab6.5-chat",
        )

        assert content == "维保建议：检查散热风扇"
        assert tokens_in == 80
        assert tokens_out == 30


@pytest.mark.asyncio
async def test_minimax_chat_raises_on_http_error():
    """MiniMax client raises on HTTP error."""
    import httpx

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server Error", request=MagicMock(), response=mock_response
    )

    with patch("app.services.llm.minimax_provider.httpx.AsyncClient") as MockHttpx:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        MockHttpx.return_value = mock_client

        client = MiniMaxClient(api_key="test-key", group_id="test-group")
        with pytest.raises(httpx.HTTPStatusError):
            await client.chat(
                messages=[{"role": "user", "content": "test"}],
                model="abab6.5-chat",
            )
