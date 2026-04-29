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
    DEEPSEEK = "deepseek"
    MINIMAX = "minimax"


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
    is_fallback: bool = False
    provider_used: str = ""


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

    def _build_client(
        self,
        provider: LLMProvider,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> BaseLLMClient:
        """根据 provider 与可选覆盖配置创建 client。"""
        if provider == LLMProvider.OPENAI:
            return OpenAIClient(api_key=api_key, base_url=base_url)
        if provider == LLMProvider.ANTHROPIC:
            return AnthropicClient(api_key=api_key)
        if provider == LLMProvider.DEEPSEEK:
            from .deepseek_provider import DeepSeekClient
            from app.core.config import settings
            return DeepSeekClient(
                api_key=api_key or settings.DEEPSEEK_API_KEY,
                base_url=base_url or settings.DEEPSEEK_BASE_URL,
                timeout=settings.LLM_TIMEOUT_SECONDS,
            )
        if provider == LLMProvider.MINIMAX:
            from .minimax_provider import MiniMaxClient
            from app.core.config import settings
            return MiniMaxClient(
                api_key=api_key or settings.MINIMAX_API_KEY,
                group_id=settings.MINIMAX_GROUP_ID,
                timeout=settings.LLM_TIMEOUT_SECONDS,
            )
        return OllamaClient(base_url=base_url)

    def _get_client(
        self,
        provider: LLMProvider,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> BaseLLMClient:
        """获取或创建指定 Provider 的 Client"""
        if api_key is not None or base_url is not None:
            return self._build_client(provider, api_key=api_key, base_url=base_url)

        if provider not in self._clients:
            self._clients[provider] = self._build_client(provider)
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
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
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
            client = self._get_client(provider, api_key=api_key, base_url=base_url)
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

    async def chat_with_fallback(
        self,
        messages: list[dict],
        model: str = "deepseek-chat",
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Chat with automatic fallback chain:
        primary → fallback → mock
        """
        from .mock_provider import match_intent

        providers_to_try = [
            (LLMProvider.DEEPSEEK, model),
            (LLMProvider.MINIMAX, "abab6.5-chat"),
        ]

        prompt_hash = self._compute_hash(str(messages))
        last_error: Optional[Exception] = None

        for provider, provider_model in providers_to_try:
            try:
                client = self._get_client(provider)
                content, tokens_in, tokens_out, raw = await client.chat(
                    messages=messages,
                    model=provider_model,
                    tools=tools,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return LLMResponse(
                    content=content,
                    provider=provider,
                    model=provider_model,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    raw_response=raw,
                    prompt_hash=prompt_hash,
                    response_hash=self._compute_hash(content),
                    is_fallback=(provider != LLMProvider.DEEPSEEK),
                    provider_used=provider.value,
                )
            except Exception as e:
                logger.warning(f"LLM call failed ({provider.value}/{provider_model}): {e}")
                last_error = e
                continue

        # All providers failed — use mock
        last_msg = messages[-1].get("content", "") if messages else ""
        mock_result = match_intent(last_msg)
        content = mock_result.text

        return LLMResponse(
            content=content,
            provider=LLMProvider.OPENAI,  # placeholder
            model="mock",
            tokens_in=0,
            tokens_out=0,
            raw_response={"error": str(last_error), "fallback": "mock"},
            prompt_hash=prompt_hash,
            response_hash=self._compute_hash(content),
            is_fallback=True,
            provider_used="mock",
        )

    def set_fallback(self, enabled: bool):
        """设置是否启用 fallback"""
        self._fallback_enabled = enabled


# 全局实例
llm_router = LLMRouter()
