"""DeepSeek LLM Provider — OpenAI-compatible API."""
from typing import Any, Optional

from openai import AsyncOpenAI

from .router import BaseLLMClient


class DeepSeekClient(BaseLLMClient):
    """DeepSeek Chat API client using OpenAI SDK with custom base_url."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com",
        timeout: float = 10.0,
    ):
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )

    async def chat(
        self,
        messages: list[dict],
        model: str = "deepseek-chat",
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> tuple[str, int, int, Any]:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
        if max_tokens:
            kwargs["max_tokens"] = max_tokens

        response = await self.client.chat.completions.create(**kwargs)

        content = response.choices[0].message.content or ""
        tokens_in = response.usage.prompt_tokens
        tokens_out = response.usage.completion_tokens

        return content, tokens_in, tokens_out, response
