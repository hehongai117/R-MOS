"""MiniMax LLM Provider — HTTP direct call."""
from typing import Any, Optional

import httpx

from .router import BaseLLMClient


class MiniMaxClient(BaseLLMClient):
    """MiniMax ChatCompletion Pro client via HTTP API."""

    BASE_URL = "https://api.minimax.chat/v1/text/chatcompletion_v2"

    def __init__(
        self,
        api_key: Optional[str] = None,
        group_id: Optional[str] = None,
        timeout: float = 10.0,
    ):
        self.api_key = api_key
        self.group_id = group_id
        self.timeout = timeout

    async def chat(
        self,
        messages: list[dict],
        model: str = "abab6.5-chat",
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> tuple[str, int, int, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = tools

        url = f"{self.BASE_URL}?GroupId={self.group_id}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)

        return content, tokens_in, tokens_out, data
