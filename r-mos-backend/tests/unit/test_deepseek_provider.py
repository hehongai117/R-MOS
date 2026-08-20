"""DeepSeek Provider unit tests."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.llm.deepseek_provider import DeepSeekClient


@pytest.mark.asyncio
async def test_deepseek_chat_returns_content():
    """DeepSeek client returns content from OpenAI-compatible API."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "诊断结果：关节过热"
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50

    with patch("app.services.llm.deepseek_provider.AsyncOpenAI") as MockClient:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        MockClient.return_value = mock_client

        client = DeepSeekClient(api_key="test-key")
        content, tokens_in, tokens_out, raw = await client.chat(
            messages=[{"role": "user", "content": "诊断故障"}],
            model="deepseek-chat",
        )

        assert content == "诊断结果：关节过热"
        assert tokens_in == 100
        assert tokens_out == 50


@pytest.mark.asyncio
async def test_deepseek_chat_with_timeout():
    """DeepSeek client respects timeout parameter."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "ok"
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5

    with patch("app.services.llm.deepseek_provider.AsyncOpenAI") as MockClient:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        MockClient.return_value = mock_client

        client = DeepSeekClient(api_key="test-key", timeout=5.0)
        content, _, _, _ = await client.chat(
            messages=[{"role": "user", "content": "test"}],
            model="deepseek-chat",
        )
        assert content == "ok"
        MockClient.assert_called_once_with(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            timeout=5.0,
        )


@pytest.mark.asyncio
async def test_deepseek_chat_disables_thinking_mode():
    """V4 系列思考模式默认开启，必须显式关闭——失效会静默产生推理成本与时延。"""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "ok"
    mock_response.usage.prompt_tokens = 1
    mock_response.usage.completion_tokens = 1

    with patch("app.services.llm.deepseek_provider.AsyncOpenAI") as MockClient:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        MockClient.return_value = mock_client

        client = DeepSeekClient(api_key="test-key")
        await client.chat(messages=[{"role": "user", "content": "test"}])

        kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert kwargs["extra_body"] == {"thinking": {"type": "disabled"}}
        assert kwargs["model"] == "deepseek-v4-flash"
