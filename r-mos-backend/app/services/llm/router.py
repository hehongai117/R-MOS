"""
LLMRouter Service - P1-1
统一 LLM 调用入口，支持 OpenAI/Anthropic/Ollama 三种 Provider

Usage:
    router = LLMRouter()
    response = await router.chat(
        messages=[{"role": "user", "content": "Hello"}],
        provider="openai",
        model="gpt-4"
    )
"""
import os
import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from openai import AsyncOpenAI
try:
    from anthropic import AsyncAnthropic  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    AsyncAnthropic = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """支持的 LLM Provider"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


@dataclass
class LLMResponse:
    """LLM 调用响应"""
    content: str
    provider: LLMProvider
    model: str
    tokens_in: int
    tokens_out: int
    raw_response: Any
    prompt_hash: str
    response_hash: str


class BaseLLMClient(ABC):
    """LLM Client 抽象基类"""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        model: str,
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> tuple[str, int, int, Any]:
        """返回: (content, tokens_in, tokens_out, raw_response)"""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI Client"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.client = AsyncOpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            base_url=base_url or os.getenv("OPENAI_BASE_URL"),
        )

    async def chat(
        self,
        messages: list[dict],
        model: str,
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> tuple[str, int, int, Any]:
        kwargs = {
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


class AnthropicClient(BaseLLMClient):
    """Anthropic Client"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client: Any | None = None

    def _get_client(self) -> Any:
        if self.client is not None:
            return self.client
        if AsyncAnthropic is None:
            raise RuntimeError("anthropic package is not installed")
        self.client = AsyncAnthropic(api_key=self.api_key)
        return self.client

    async def chat(
        self,
        messages: list[dict],
        model: str,
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> tuple[str, int, int, Any]:
        # Convert messages to Anthropic format
        system = None
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                anthropic_messages.append(msg)

        kwargs = {
            "model": model,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
        }
        if system:
            kwargs["system"] = system
        if tools:
            # Anthropic uses tools differently
            kwargs["tools"] = tools

        client = self._get_client()
        response = await client.messages.create(**kwargs)

        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text

        tokens_in = response.usage.input_tokens
        tokens_out = response.usage.output_tokens

        return content, tokens_in, tokens_out, response


class OllamaClient(BaseLLMClient):
    """Ollama Client (local models)"""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    async def chat(
        self,
        messages: list[dict],
        model: str,
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> tuple[str, int, int, Any]:
        import httpx

        async with httpx.AsyncClient() as client:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }
            if max_tokens:
                payload["options"] = {"num_predict": max_tokens}
            if tools:
                payload["tools"] = tools

            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

            content = data.get("message", {}).get("content", "")
            tokens_in = data.get("prompt_eval_count", 0)
            tokens_out = data.get("eval_count", 0)

            return content, tokens_in, tokens_out, data


class LLMRouter:
    """
    统一 LLM 路由服务

    支持:
    - OpenAI (gpt-4, gpt-3.5-turbo, etc.)
    - Anthropic (claude-3-opus, claude-3-sonnet, etc.)
    - Ollama (local models: llama2, mistral, etc.)
    """

    def __init__(self):
        self._clients: dict[LLMProvider, BaseLLMClient] = {}
        self._fallback_enabled = True

    def _get_client(self, provider: LLMProvider) -> BaseLLMClient:
        """获取或创建指定 Provider 的 Client"""
        if provider not in self._clients:
            if provider == LLMProvider.OPENAI:
                self._clients[provider] = OpenAIClient()
            elif provider == LLMProvider.ANTHROPIC:
                self._clients[provider] = AnthropicClient()
            elif provider == LLMProvider.OLLAMA:
                self._clients[provider] = OllamaClient()
        return self._clients[provider]

    @staticmethod
    def _compute_hash(text: str) -> str:
        """计算文本的 SHA256 哈希"""
        return hashlib.sha256(text.encode()).hexdigest()[:64]

    async def chat(
        self,
        messages: list[dict],
        provider: LLMProvider = LLMProvider.OPENAI,
        model: str = "gpt-4",
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        统一 LLM 调用接口

        Args:
            messages: 消息列表
            provider: LLM Provider
            model: 模型名称
            tools: 工具定义列表
            temperature: 温度参数
            max_tokens: 最大输出 tokens

        Returns:
            LLMResponse: 包含内容和审计信息
        """
        # 计算 prompt hash
        prompt_text = str(messages)
        prompt_hash = self._compute_hash(prompt_text)

        # 尝试调用 LLM
        try:
            client = self._get_client(provider)
            content, tokens_in, tokens_out, raw = await client.chat(
                messages=messages,
                model=model,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            logger.warning(f"LLM 调用失败 ({provider.value}/{model}): {e}")
            if not self._fallback_enabled:
                raise
            # Fallback 到规则模式
            content = self._fallback_response(messages)
            tokens_in = 0
            tokens_out = 0
            raw = {"error": str(e), "fallback": True}
            provider = LLMProvider.OPENAI  # 标记为 fallback

        # 计算 response hash
        response_hash = self._compute_hash(content)

        return LLMResponse(
            content=content,
            provider=provider,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            raw_response=raw,
            prompt_hash=prompt_hash,
            response_hash=response_hash,
        )

    def _fallback_response(self, messages: list[dict]) -> str:
        """Fallback 到规则模式的响应"""
        # 简单的规则匹配作为兜底
        last_message = messages[-1].get("content", "").lower() if messages else ""

        if "诊断" in last_message or "问题" in last_message:
            return "我需要更多上下文来进行诊断。请提供具体的错误信息或设备状态。"
        elif "教学" in last_message or "指导" in last_message:
            return "让我为您分析当前步骤的操作要点。请按照 SOP 顺序执行。"
        elif "知识" in last_message or "查询" in last_message:
            return "我正在检索相关知识库内容，请稍候。"
        else:
            return "我理解您的需求。让我为您处理这个请求。"

    def set_fallback(self, enabled: bool):
        """设置是否启用 fallback"""
        self._fallback_enabled = enabled


# 全局实例
llm_router = LLMRouter()
