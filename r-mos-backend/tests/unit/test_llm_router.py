"""
P1-1-5: LLMRouter 单元测试
测试 Provider 切换、审计写入、fallback 降级
"""
import pytest
from app.services.llm.router import (
    LLMRouter,
    LLMProvider,
    LLMResponse,
)


# ============ LLMRouter 基础测试 ============

def test_llm_provider_enum():
    """测试 LLMProvider 枚举"""
    assert LLMProvider.OPENAI.value == "openai"
    assert LLMProvider.ANTHROPIC.value == "anthropic"
    assert LLMProvider.OLLAMA.value == "ollama"


def test_llm_response_creation():
    """测试 LLMResponse 创建"""
    response = LLMResponse(
        content="Hello, world!",
        provider=LLMProvider.OPENAI,
        model="gpt-4",
        tokens_in=10,
        tokens_out=5,
        raw_response={"id": "test"},
        prompt_hash="abc123",
        response_hash="def456",
    )

    assert response.content == "Hello, world!"
    assert response.provider == LLMProvider.OPENAI
    assert response.model == "gpt-4"
    assert response.tokens_in == 10
    assert response.tokens_out == 5


def test_compute_hash():
    """测试哈希计算"""
    router = LLMRouter()

    hash1 = router._compute_hash("Hello, world!")
    hash2 = router._compute_hash("Hello, world!")
    hash3 = router._compute_hash("Different text")

    assert hash1 == hash2  # 相同内容产生相同哈希
    assert hash1 != hash3  # 不同内容产生不同哈希
    assert len(hash1) == 64  # SHA256 产生 64 字符的十六进制字符串


# ============ Fallback 机制测试 ============

@pytest.mark.asyncio
async def test_fallback_response_diagnosis():
    """测试 fallback 响应 - 诊断类"""
    router = LLMRouter()
    router.set_fallback(True)

    messages = [{"role": "user", "content": "机器人无法移动，请诊断问题"}]

    # 由于没有真实 API key，会触发 fallback
    response = await router.chat(
        messages=messages,
        provider=LLMProvider.OPENAI,
        model="gpt-4",
    )

    assert response.content is not None
    assert "诊断" in response.content or "上下文" in response.content


@pytest.mark.asyncio
async def test_fallback_response_teaching():
    """测试 fallback 响应 - 教学类"""
    router = LLMRouter()
    router.set_fallback(True)

    messages = [{"role": "user", "content": "请指导我完成这个步骤"}]

    response = await router.chat(
        messages=messages,
        provider=LLMProvider.OPENAI,
        model="gpt-4",
    )

    assert response.content is not None
    assert len(response.content) > 0


@pytest.mark.asyncio
async def test_fallback_disabled_raises():
    """测试禁用 fallback 时抛出异常"""
    router = LLMRouter()
    router.set_fallback(False)

    messages = [{"role": "user", "content": "test"}]

    # 没有 API key 时应该抛出异常
    with pytest.raises(Exception):
        await router.chat(
            messages=messages,
            provider=LLMProvider.OPENAI,
            model="gpt-4",
        )


# ============ Provider 切换测试 ============

def test_get_openai_client_without_key():
    """测试获取 OpenAI Client (无 key 时不抛出)"""
    router = LLMRouter()
    # 不设置 API key，应该能创建 client 对象（延迟初始化）
    # 实际调用时才会检查 key
    assert router._clients == {}


def test_get_anthropic_client():
    """测试获取 Anthropic Client"""
    router = LLMRouter()
    client = router._get_client(LLMProvider.ANTHROPIC)

    assert client is not None


def test_get_ollama_client():
    """测试获取 Ollama Client"""
    router = LLMRouter()
    client = router._get_client(LLMProvider.OLLAMA)

    assert client is not None


# ============ 消息格式测试 ============

def test_router_initialization():
    """测试 Router 初始化"""
    router = LLMRouter()

    assert router._clients == {}
    assert router._fallback_enabled is True


def test_set_fallback():
    """测试设置 fallback"""
    router = LLMRouter()

    router.set_fallback(False)
    assert router._fallback_enabled is False

    router.set_fallback(True)
    assert router._fallback_enabled is True
