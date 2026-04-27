# Pipeline + LLM + Knowledge Base Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 3 end-to-end fault case pipelines (monitor→diagnosis→SOP→report) with DeepSeek/MiniMax LLM integration and mixed RAG knowledge base.

**Architecture:** Pipeline-First approach — wire the full flow using existing rule engines first, then layer LLM enhancement on top. Three-layer fallback (primary LLM → backup LLM → mock/rules) ensures demo stability in any network condition.

**Tech Stack:** FastAPI, SQLAlchemy 2.0+ (async), PostgreSQL + pgvector, openai SDK (for DeepSeek), httpx (for MiniMax), React + TypeScript, Zustand

---

## File Structure

### Backend — New Files
| File | Responsibility |
|------|---------------|
| `app/services/llm/deepseek_provider.py` | DeepSeek Chat API client (OpenAI-compatible) |
| `app/services/llm/minimax_provider.py` | MiniMax ChatCompletion Pro client |
| `app/services/llm/embedding_service.py` | Embedding generation (DeepSeek API + local fallback) |
| `app/services/knowledge/knowledge_retriever.py` | Mixed retrieval: tag match + vector search |
| `app/services/knowledge/knowledge_document.py` | Document model + CRUD |
| `app/services/pipeline/fault_diagnosis_service.py` | Fault telemetry → diagnosis orchestration |
| `app/services/pipeline/task_pipeline_service.py` | Diagnosis → task creation → SOP mapping |
| `app/models/fault_sop_mapping.py` | fault_type → sop_id mapping model |
| `app/models/task_execution.py` | Task execution + step results persistence |
| `app/models/knowledge_document.py` | Knowledge document with tags + status |
| `app/api/v1/endpoints/pipeline.py` | Pipeline API endpoints (from-diagnosis, complete) |
| `app/api/v1/endpoints/knowledge_upload.py` | Teacher document upload endpoint |
| `scripts/seed_knowledge.py` | Seed 5 knowledge documents for 3 fault cases |
| `scripts/seed_fault_sops.py` | Seed 3 SOPs + fault_sop_mapping |

### Backend — Modified Files
| File | Changes |
|------|---------|
| `app/services/llm/router.py` | Add DEEPSEEK/MINIMAX providers, fallback chain, timeout |
| `app/services/simulation/fault_scenarios.py` | Add E001/E005/E003 scenarios with proper telemetry effects |
| `app/services/diagnoser_agent.py` | Add `diagnose_fault()` method with LLM enhancement |
| `app/services/coach_agent.py` | Add `get_hint()` with LLM + template fallback |
| `app/models/knowledge_chunk.py` | Add `tags` and vector `embedding` column |
| `app/core/config.py` | Add LLM config (API keys, timeouts, provider selection) |
| `app/api/v1/__init__.py` | Register new routers |

### Frontend — Modified Files
| File | Changes |
|------|---------|
| `src/pages/MonitorPage.tsx` | Add FaultAlertCard with "一键诊断" button |
| `src/pages/agent/AgentWorkbenchPage.tsx` | Add "创建维保任务" action after diagnosis |
| `src/components/Maintenance/SOPPlayerAdjudicated.tsx` | Step completion → backend POST |
| `src/pages/ReportPage.tsx` | Enhanced report with radar chart + AI commentary |
| `src/api/pipeline.ts` | New API client for pipeline endpoints |

### Frontend — New Files
| File | Responsibility |
|------|---------------|
| `src/api/pipeline.ts` | Pipeline API client (from-diagnosis, step-complete, task-complete) |
| `src/components/Monitor/FaultAlertCard.tsx` | Fault alert card with one-click diagnosis |
| `src/components/Report/RadarChart.tsx` | Five-dimension radar chart component |

### Tests
| File | Tests |
|------|-------|
| `tests/unit/test_deepseek_provider.py` | DeepSeek provider unit tests |
| `tests/unit/test_minimax_provider.py` | MiniMax provider unit tests |
| `tests/unit/test_llm_router_fallback.py` | Router fallback chain tests |
| `tests/unit/test_fault_diagnosis_service.py` | Fault diagnosis pipeline tests |
| `tests/unit/test_knowledge_retriever.py` | Mixed retrieval tests |
| `tests/unit/test_task_pipeline_service.py` | Task creation + completion tests |
| `r-mos-frontend/src/pages/__tests__/MonitorPage.fault-alert.test.tsx` | Fault alert card tests |

---

## Task 1: LLM Router — Add DeepSeek Provider

**Files:**
- Create: `r-mos-backend/app/services/llm/deepseek_provider.py`
- Modify: `r-mos-backend/app/services/llm/router.py`
- Modify: `r-mos-backend/app/core/config.py`
- Test: `r-mos-backend/tests/unit/test_deepseek_provider.py`

- [ ] **Step 1: Write failing test for DeepSeek provider**

```python
# tests/unit/test_deepseek_provider.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd r-mos-backend && python -m pytest tests/unit/test_deepseek_provider.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.llm.deepseek_provider'"

- [ ] **Step 3: Implement DeepSeek provider**

```python
# app/services/llm/deepseek_provider.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd r-mos-backend && python -m pytest tests/unit/test_deepseek_provider.py -v`
Expected: 2 passed

- [ ] **Step 5: Add config settings for LLM providers**

Add to `app/core/config.py` inside the `Settings` class:

```python
    # LLM Provider Config
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    MINIMAX_API_KEY: str = ""
    MINIMAX_GROUP_ID: str = ""
    LLM_PRIMARY_PROVIDER: str = "deepseek"
    LLM_FALLBACK_PROVIDER: str = "minimax"
    LLM_TIMEOUT_SECONDS: float = 10.0
    LLM_ENABLE_MOCK_FALLBACK: bool = True
```

- [ ] **Step 6: Register DeepSeek in LLM Router**

Add to `app/services/llm/router.py`:

1. Add `DEEPSEEK = "deepseek"` to the `LLMProvider` enum.
2. In `_build_client()`, add:
```python
        if provider == LLMProvider.DEEPSEEK:
            from .deepseek_provider import DeepSeekClient
            from app.core.config import settings
            return DeepSeekClient(
                api_key=api_key or settings.DEEPSEEK_API_KEY,
                base_url=base_url or settings.DEEPSEEK_BASE_URL,
                timeout=settings.LLM_TIMEOUT_SECONDS,
            )
```

- [ ] **Step 7: Commit**

```bash
git add app/services/llm/deepseek_provider.py app/services/llm/router.py app/core/config.py tests/unit/test_deepseek_provider.py
git commit -m "feat: add DeepSeek LLM provider with OpenAI-compatible API"
```

---

## Task 2: LLM Router — Add MiniMax Provider

**Files:**
- Create: `r-mos-backend/app/services/llm/minimax_provider.py`
- Modify: `r-mos-backend/app/services/llm/router.py`
- Test: `r-mos-backend/tests/unit/test_minimax_provider.py`

- [ ] **Step 1: Write failing test for MiniMax provider**

```python
# tests/unit/test_minimax_provider.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd r-mos-backend && python -m pytest tests/unit/test_minimax_provider.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement MiniMax provider**

```python
# app/services/llm/minimax_provider.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd r-mos-backend && python -m pytest tests/unit/test_minimax_provider.py -v`
Expected: 2 passed

- [ ] **Step 5: Register MiniMax in LLM Router**

Add `MINIMAX = "minimax"` to the `LLMProvider` enum in `router.py`.

Add to `_build_client()`:
```python
        if provider == LLMProvider.MINIMAX:
            from .minimax_provider import MiniMaxClient
            from app.core.config import settings
            return MiniMaxClient(
                api_key=api_key or settings.MINIMAX_API_KEY,
                group_id=settings.MINIMAX_GROUP_ID,
                timeout=settings.LLM_TIMEOUT_SECONDS,
            )
```

- [ ] **Step 6: Commit**

```bash
git add app/services/llm/minimax_provider.py app/services/llm/router.py tests/unit/test_minimax_provider.py
git commit -m "feat: add MiniMax LLM provider with HTTP API"
```

---

## Task 3: LLM Router — Fallback Chain

**Files:**
- Modify: `r-mos-backend/app/services/llm/router.py`
- Test: `r-mos-backend/tests/unit/test_llm_router_fallback.py`

- [ ] **Step 1: Write failing test for fallback chain**

```python
# tests/unit/test_llm_router_fallback.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd r-mos-backend && python -m pytest tests/unit/test_llm_router_fallback.py -v`
Expected: FAIL with "AttributeError: 'LLMRouter' object has no attribute 'chat_with_fallback'"

- [ ] **Step 3: Implement `chat_with_fallback` method in LLMRouter**

Add to `LLMResponse` dataclass:
```python
    is_fallback: bool = False
    provider_used: str = ""
```

Add method to `LLMRouter` class:
```python
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
        from app.core.config import settings
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd r-mos-backend && python -m pytest tests/unit/test_llm_router_fallback.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add app/services/llm/router.py tests/unit/test_llm_router_fallback.py
git commit -m "feat: add LLM router fallback chain (primary→secondary→mock)"
```

---

## Task 4: Fault Scenarios — 3 Case Definitions

**Files:**
- Modify: `r-mos-backend/app/services/simulation/fault_scenarios.py`
- Test: `r-mos-backend/tests/unit/test_fault_scenarios.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_fault_scenarios.py
"""Fault scenario definitions tests."""
from app.services.simulation.fault_scenarios import (
    FAULT_SCENARIOS,
    FaultScenario,
    inject_fault,
    get_scenario,
)


def test_three_scenarios_defined():
    """3 fault scenarios exist."""
    assert "E001_OVERHEAT" in FAULT_SCENARIOS
    assert "E005_LOOSE" in FAULT_SCENARIOS
    assert "E003_VOLTAGE_DROP" in FAULT_SCENARIOS


def test_e001_scenario_structure():
    """E001 scenario has correct structure."""
    scenario = get_scenario("E001_OVERHEAT")
    assert scenario is not None
    assert scenario.fault_type == "E001_OVERHEAT"
    assert scenario.affected_joints == ["waist"]
    assert scenario.difficulty == "beginner"
    assert scenario.telemetry_effects["temperature_increase"] == 35.0


def test_e003_compound_scenario():
    """E003 compound scenario triggers E001 as secondary."""
    scenario = get_scenario("E003_VOLTAGE_DROP")
    assert scenario.difficulty == "advanced"
    assert scenario.compound_triggers == ["E001_OVERHEAT"]
    assert "shoulder" in scenario.affected_joints or "elbow" in scenario.affected_joints


def test_inject_fault_creates_active_fault():
    """inject_fault returns active fault with progress tracking."""
    fault = inject_fault("E001_OVERHEAT")
    assert fault.fault_type == "E001_OVERHEAT"
    assert fault.progress() >= 0.0
    assert not fault.is_complete
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd r-mos-backend && python -m pytest tests/unit/test_fault_scenarios.py -v`
Expected: FAIL with import errors

- [ ] **Step 3: Rewrite fault_scenarios.py with 3 scenarios**

```python
# app/services/simulation/fault_scenarios.py
"""Fault scenario definitions for 3 polished cases."""
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FaultScenario:
    """Static scenario definition."""
    fault_type: str
    name: str
    difficulty: str  # beginner / intermediate / advanced
    affected_joints: list[str]
    telemetry_effects: dict
    alert_threshold: dict
    compound_triggers: list[str] = field(default_factory=list)
    ramp_duration: float = 30.0


@dataclass
class ActiveFault:
    """A running fault instance with time-based progression."""
    fault_type: str
    scenario: FaultScenario
    start_time: float = field(default_factory=time.time)

    def progress(self) -> float:
        elapsed = time.time() - self.start_time
        return min(elapsed / self.scenario.ramp_duration, 1.0)

    @property
    def is_complete(self) -> bool:
        return self.progress() >= 1.0

    def current_effects(self) -> dict:
        p = self.progress()
        effects = {}
        for key, target_value in self.scenario.telemetry_effects.items():
            effects[key] = target_value * p
        return effects


FAULT_SCENARIOS: dict[str, FaultScenario] = {
    "E001_OVERHEAT": FaultScenario(
        fault_type="E001_OVERHEAT",
        name="关节过热",
        difficulty="beginner",
        affected_joints=["waist"],
        telemetry_effects={
            "temperature_increase": 35.0,  # 40°C base + 35 = 75°C threshold
            "torque_noise": 0.5,
        },
        alert_threshold={"temperature": 75.0},
        ramp_duration=30.0,
    ),
    "E005_LOOSE": FaultScenario(
        fault_type="E005_LOOSE",
        name="关节松动",
        difficulty="intermediate",
        affected_joints=["elbow"],
        telemetry_effects={
            "position_error_increase": 0.14,  # 0.01 base + 0.14 = 0.15 rad
            "vibration_increase": 2.0,
        },
        alert_threshold={"position_error": 0.10},
        ramp_duration=20.0,
    ),
    "E003_VOLTAGE_DROP": FaultScenario(
        fault_type="E003_VOLTAGE_DROP",
        name="电压跌落+过热联动",
        difficulty="advanced",
        affected_joints=["shoulder", "elbow"],
        telemetry_effects={
            "voltage_drop": 5.0,  # 24V - 5 = 19V
            "temperature_increase": 25.0,  # secondary effect on affected joints
        },
        alert_threshold={"voltage": 20.0, "temperature": 70.0},
        compound_triggers=["E001_OVERHEAT"],
        ramp_duration=25.0,
    ),
}


def get_scenario(fault_type: str) -> Optional[FaultScenario]:
    """Get scenario definition by fault type."""
    return FAULT_SCENARIOS.get(fault_type)


def inject_fault(fault_type: str) -> ActiveFault:
    """Create an active fault instance."""
    scenario = FAULT_SCENARIOS[fault_type]
    return ActiveFault(fault_type=fault_type, scenario=scenario)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd r-mos-backend && python -m pytest tests/unit/test_fault_scenarios.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add app/services/simulation/fault_scenarios.py tests/unit/test_fault_scenarios.py
git commit -m "feat: define 3 fault scenarios (E001 overheat, E005 loose, E003 compound)"
```

---

## Task 5: Data Models — fault_sop_mapping + task_execution

**Files:**
- Create: `r-mos-backend/app/models/fault_sop_mapping.py`
- Create: `r-mos-backend/app/models/task_execution.py`
- Modify: `r-mos-backend/app/models/__init__.py`

- [ ] **Step 1: Create fault_sop_mapping model**

```python
# app/models/fault_sop_mapping.py
"""Fault type → SOP mapping model."""
from sqlalchemy import Column, Integer, String, ForeignKey
from .base import Base, TimestampMixin


class FaultSOPMapping(Base, TimestampMixin):
    """Maps fault types to their corresponding SOPs."""
    __tablename__ = "fault_sop_mappings"

    id = Column(Integer, primary_key=True, index=True)
    fault_type = Column(String(50), nullable=False, index=True, comment="故障类型编码")
    sop_id = Column(
        Integer,
        ForeignKey("sops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联 SOP ID",
    )
    difficulty = Column(String(20), nullable=False, comment="难度: beginner/intermediate/advanced")
    priority = Column(Integer, default=1, comment="优先级（同 fault_type 多 SOP 时）")
```

- [ ] **Step 2: Create task_execution model**

```python
# app/models/task_execution.py
"""Task execution persistence models."""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base, TimestampMixin


class TaskExecution(Base, TimestampMixin):
    """Persists a student's SOP execution session."""
    __tablename__ = "task_executions"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, nullable=False, index=True, comment="学生 user ID")
    sop_id = Column(Integer, ForeignKey("sops.id", ondelete="SET NULL"), nullable=True)
    diagnosis_trace_id = Column(String(100), nullable=True, comment="诊断追踪 ID")
    fault_type = Column(String(50), nullable=True, index=True, comment="故障类型")
    status = Column(String(20), default="in_progress", nullable=False, comment="in_progress/completed/abandoned")
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    step_results = relationship("TaskStepResult", back_populates="execution", cascade="all, delete-orphan", lazy="selectin")


class TaskStepResult(Base, TimestampMixin):
    """Result of a single SOP step execution."""
    __tablename__ = "task_step_results"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("task_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    step_index = Column(Integer, nullable=False, comment="步骤序号")
    status = Column(String(20), default="completed", comment="completed/skipped/failed")
    duration_seconds = Column(Integer, nullable=True, comment="耗时秒数")
    evidence_type = Column(String(30), nullable=True, comment="photo/numeric/checkbox")
    evidence_value = Column(JSON, nullable=True, comment="证据内容")
    is_compliant = Column(Boolean, default=True, comment="是否合规")
    feedback = Column(String(500), nullable=True, comment="即时反馈")

    execution = relationship("TaskExecution", back_populates="step_results")
```

- [ ] **Step 3: Register models in `__init__.py`**

Add to `app/models/__init__.py`:
```python
from .fault_sop_mapping import FaultSOPMapping  # noqa: F401
from .task_execution import TaskExecution, TaskStepResult  # noqa: F401
```

- [ ] **Step 4: Verify models load without error**

Run: `cd r-mos-backend && python -c "from app.models.fault_sop_mapping import FaultSOPMapping; from app.models.task_execution import TaskExecution, TaskStepResult; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add app/models/fault_sop_mapping.py app/models/task_execution.py app/models/__init__.py
git commit -m "feat: add FaultSOPMapping + TaskExecution data models"
```

---

## Task 6: Knowledge Document Model + Retriever

**Files:**
- Create: `r-mos-backend/app/models/knowledge_document.py`
- Create: `r-mos-backend/app/services/knowledge/knowledge_retriever.py`
- Modify: `r-mos-backend/app/models/__init__.py`
- Test: `r-mos-backend/tests/unit/test_knowledge_retriever.py`

- [ ] **Step 1: Create knowledge_document model**

```python
# app/models/knowledge_document.py
"""Knowledge document model with tags for mixed RAG retrieval."""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from datetime import datetime
from .base import Base, TimestampMixin


class KnowledgeDocument(Base, TimestampMixin):
    """A knowledge document with fault/SOP tags and status lifecycle."""
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False, comment="文档标题")
    content = Column(Text, nullable=False, comment="文档全文")
    doc_type = Column(String(50), default="manual", comment="manual/guide/spec")
    fault_tags = Column(JSON, default=list, comment='关联故障标签 ["E001_OVERHEAT"]')
    sop_tags = Column(JSON, default=list, comment='关联SOP标签')
    status = Column(String(20), default="PENDING", index=True, comment="PENDING/APPROVED/EXPIRED")
    risk_level = Column(String(5), default="R0", comment="风险等级")
    uploaded_by = Column(Integer, nullable=True, comment="上传用户 ID")
    approved_at = Column(DateTime, nullable=True)
```

- [ ] **Step 2: Write failing test for knowledge retriever**

```python
# tests/unit/test_knowledge_retriever.py
"""Knowledge retriever tests."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.knowledge.knowledge_retriever import KnowledgeRetriever


@pytest.mark.asyncio
async def test_retrieve_by_tag_returns_matching_chunks():
    """Tag-based search returns documents matching fault_type."""
    mock_db = AsyncMock()
    # Simulate query result
    mock_doc = MagicMock()
    mock_doc.id = 1
    mock_doc.title = "关节过热维修手册"
    mock_doc.content = "过热处理步骤..."
    mock_doc.fault_tags = ["E001_OVERHEAT"]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_doc]
    mock_db.execute = AsyncMock(return_value=mock_result)

    retriever = KnowledgeRetriever(mock_db)
    results = await retriever.retrieve(query="过热怎么办", fault_type="E001_OVERHEAT")

    assert len(results) >= 1
    assert results[0].title == "关节过热维修手册"


@pytest.mark.asyncio
async def test_retrieve_without_fault_type_uses_text_search():
    """Without fault_type, retriever still returns results via text matching."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    retriever = KnowledgeRetriever(mock_db)
    results = await retriever.retrieve(query="安全规范")

    # Should not crash, returns empty for now (vector search not yet wired)
    assert isinstance(results, list)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd r-mos-backend && python -m pytest tests/unit/test_knowledge_retriever.py -v`
Expected: FAIL with import error

- [ ] **Step 4: Implement knowledge retriever**

```python
# app/services/knowledge/knowledge_retriever.py
"""Mixed knowledge retrieval: tag-based exact match + vector search (future)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_document import KnowledgeDocument

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """A retrieved knowledge chunk."""
    id: int
    title: str
    content: str
    fault_tags: list[str]
    relevance_source: str  # "tag_match" or "vector_search"


class KnowledgeRetriever:
    """Mixed retrieval: tag match (high precision) + vector search (high recall)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def retrieve(
        self,
        query: str,
        fault_type: Optional[str] = None,
        limit: int = 5,
    ) -> list[RetrievedChunk]:
        results: list[RetrievedChunk] = []

        # Path 1: Tag-based exact match
        if fault_type:
            tag_results = await self._search_by_tag(fault_type, limit=limit)
            results.extend(tag_results)

        # Path 2: Vector similarity search (placeholder — requires pgvector)
        if len(results) < limit:
            vector_results = await self._search_by_text(
                query,
                limit=limit - len(results),
                exclude_ids=[r.id for r in results],
            )
            results.extend(vector_results)

        return results[:limit]

    async def _search_by_tag(self, fault_type: str, limit: int) -> list[RetrievedChunk]:
        """Search documents by fault_tags JSON array contains."""
        stmt = (
            select(KnowledgeDocument)
            .where(KnowledgeDocument.status == "APPROVED")
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        docs = result.scalars().all()

        # Filter in Python (JSON array contains — portable across DB engines)
        matched = []
        for doc in docs:
            tags = doc.fault_tags or []
            if fault_type in tags or "*" in tags:
                matched.append(
                    RetrievedChunk(
                        id=doc.id,
                        title=doc.title,
                        content=doc.content[:2000],  # truncate for context window
                        fault_tags=tags,
                        relevance_source="tag_match",
                    )
                )
        return matched[:limit]

    async def _search_by_text(
        self, query: str, limit: int, exclude_ids: list[int]
    ) -> list[RetrievedChunk]:
        """Text-based search fallback (simple LIKE for now, vector later)."""
        stmt = (
            select(KnowledgeDocument)
            .where(
                KnowledgeDocument.status == "APPROVED",
                KnowledgeDocument.id.notin_(exclude_ids) if exclude_ids else True,
            )
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        docs = result.scalars().all()

        # Simple keyword match (will be replaced by pgvector cosine similarity)
        matched = []
        for doc in docs:
            if any(kw in (doc.content or "") for kw in query[:20].split()):
                matched.append(
                    RetrievedChunk(
                        id=doc.id,
                        title=doc.title,
                        content=doc.content[:2000],
                        fault_tags=doc.fault_tags or [],
                        relevance_source="vector_search",
                    )
                )
        return matched[:limit]
```

- [ ] **Step 5: Register model, run tests**

Add to `app/models/__init__.py`:
```python
from .knowledge_document import KnowledgeDocument  # noqa: F401
```

Run: `cd r-mos-backend && python -m pytest tests/unit/test_knowledge_retriever.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add app/models/knowledge_document.py app/services/knowledge/knowledge_retriever.py app/models/__init__.py tests/unit/test_knowledge_retriever.py
git commit -m "feat: add KnowledgeDocument model and mixed tag+text retriever"
```

---

## Task 7: Fault Diagnosis Service (Pipeline Core)

**Files:**
- Create: `r-mos-backend/app/services/pipeline/fault_diagnosis_service.py`
- Test: `r-mos-backend/tests/unit/test_fault_diagnosis_service.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_fault_diagnosis_service.py
"""Fault diagnosis pipeline service tests."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.pipeline.fault_diagnosis_service import FaultDiagnosisService


@pytest.mark.asyncio
async def test_diagnose_e001_overheat():
    """Diagnose E001 from telemetry with high temperature."""
    telemetry = {
        "joints": [
            {"joint_id": "waist", "temperature": 78, "velocity": 0.1, "torque": 1.2, "error_code": None},
        ],
        "sensors": {"voltage": {"main": 24}},
    }

    service = FaultDiagnosisService()
    result = await service.diagnose(telemetry)

    assert result["success"] is True
    assert result["fault_type"] == "E001_OVERHEAT"
    assert result["confidence"] >= 0.8
    assert "waist" in result["affected_joints"]
    assert result["recommended_sop"] is not None


@pytest.mark.asyncio
async def test_diagnose_e003_compound():
    """Diagnose E003 compound fault: voltage drop + temperature."""
    telemetry = {
        "joints": [
            {"joint_id": "shoulder", "temperature": 72, "velocity": 0.05, "torque": 2.0, "error_code": None},
            {"joint_id": "elbow", "temperature": 70, "velocity": 0.08, "torque": 1.8, "error_code": None},
        ],
        "sensors": {"voltage": {"main": 19}},
    }

    service = FaultDiagnosisService()
    result = await service.diagnose(telemetry)

    assert result["success"] is True
    assert result["fault_type"] == "E003_VOLTAGE_DROP"
    assert result["is_compound"] is True


@pytest.mark.asyncio
async def test_diagnose_no_fault():
    """Normal telemetry returns no fault."""
    telemetry = {
        "joints": [
            {"joint_id": "waist", "temperature": 42, "velocity": 1.0, "torque": 0.5, "error_code": None},
        ],
        "sensors": {"voltage": {"main": 24}},
    }

    service = FaultDiagnosisService()
    result = await service.diagnose(telemetry)

    assert result["success"] is True
    assert result["fault_type"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd r-mos-backend && python -m pytest tests/unit/test_fault_diagnosis_service.py -v`
Expected: FAIL with import error

- [ ] **Step 3: Implement fault diagnosis service**

```python
# app/services/pipeline/__init__.py
```

```python
# app/services/pipeline/fault_diagnosis_service.py
"""Fault diagnosis service — rule engine + LLM enhancement."""
from __future__ import annotations

import logging
from typing import Any, Optional

from app.services.simulation.fault_scenarios import FAULT_SCENARIOS

logger = logging.getLogger(__name__)

# Thresholds for rule-based diagnosis
TEMP_ALERT_THRESHOLD = 70.0
VOLTAGE_LOW_THRESHOLD = 20.0
POSITION_ERROR_THRESHOLD = 0.10


class FaultDiagnosisService:
    """
    Diagnoses faults from telemetry data.
    
    Strategy: rule engine first (always runs), then LLM enhancement (optional).
    """

    async def diagnose(
        self,
        telemetry: dict[str, Any],
        knowledge_context: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Analyze telemetry and return diagnosis result.
        
        Returns dict with: success, fault_type, confidence, affected_joints,
        reasoning, recommended_sop, is_compound
        """
        # Step 1: Rule-based analysis
        rule_result = self._rule_based_diagnose(telemetry)

        # Step 2: LLM enhancement (non-blocking, best-effort)
        llm_reasoning = None
        if rule_result["fault_type"]:
            try:
                llm_reasoning = await self._llm_enhance(telemetry, rule_result, knowledge_context)
            except Exception as e:
                logger.warning(f"LLM enhancement failed: {e}")

        # Step 3: Merge
        if llm_reasoning:
            rule_result["reasoning"] = llm_reasoning
            rule_result["llm_enhanced"] = True
        else:
            rule_result["llm_enhanced"] = False

        return rule_result

    def _rule_based_diagnose(self, telemetry: dict[str, Any]) -> dict[str, Any]:
        """Pure rule-based fault detection."""
        joints = telemetry.get("joints", [])
        sensors = telemetry.get("sensors", {})
        voltage = sensors.get("voltage", {}).get("main", 24.0)

        # Check voltage first (compound fault root cause)
        voltage_low = voltage < VOLTAGE_LOW_THRESHOLD
        
        # Check joints for temperature / position errors
        hot_joints = []
        loose_joints = []

        for joint in joints:
            temp = joint.get("temperature", 0)
            pos_error = joint.get("position_error", 0)
            
            if temp >= TEMP_ALERT_THRESHOLD:
                hot_joints.append(joint["joint_id"])
            if pos_error >= POSITION_ERROR_THRESHOLD:
                loose_joints.append(joint["joint_id"])

        # Decision tree
        if voltage_low and hot_joints:
            # Compound: voltage drop causing overheating
            return {
                "success": True,
                "fault_type": "E003_VOLTAGE_DROP",
                "confidence": 0.88,
                "affected_joints": hot_joints,
                "reasoning": f"电压跌落至{voltage}V导致多关节过热补偿",
                "recommended_sop": "sop-e003-e001-compound",
                "is_compound": True,
            }
        elif loose_joints:
            return {
                "success": True,
                "fault_type": "E005_LOOSE",
                "confidence": 0.85,
                "affected_joints": loose_joints,
                "reasoning": f"关节位置偏差超限，疑似机械松动",
                "recommended_sop": "sop-e005-loose",
                "is_compound": False,
            }
        elif hot_joints:
            return {
                "success": True,
                "fault_type": "E001_OVERHEAT",
                "confidence": 0.90,
                "affected_joints": hot_joints,
                "reasoning": f"关节温度超过{TEMP_ALERT_THRESHOLD}°C阈值",
                "recommended_sop": "sop-e001-overheat",
                "is_compound": False,
            }
        else:
            return {
                "success": True,
                "fault_type": None,
                "confidence": 1.0,
                "affected_joints": [],
                "reasoning": "遥测数据正常，未检测到故障",
                "recommended_sop": None,
                "is_compound": False,
            }

    async def _llm_enhance(
        self,
        telemetry: dict[str, Any],
        rule_result: dict[str, Any],
        knowledge_context: Optional[list[str]],
    ) -> Optional[str]:
        """Enhance diagnosis with LLM-generated natural language reasoning."""
        from app.services.llm.router import llm_router, LLMProvider

        fault_type = rule_result["fault_type"]
        affected = rule_result["affected_joints"]

        system_prompt = (
            "你是机器人维保诊断专家。根据遥测数据和初步诊断结果，"
            "生成简明的故障分析说明（3-5句话），包含可能原因和建议措施。"
        )
        user_content = (
            f"故障类型: {fault_type}\n"
            f"受影响关节: {affected}\n"
            f"遥测摘要: {telemetry}\n"
        )
        if knowledge_context:
            user_content += f"\n参考知识: {knowledge_context[:2]}"

        response = await llm_router.chat_with_fallback(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
        return response.content if response.content else None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd r-mos-backend && python -m pytest tests/unit/test_fault_diagnosis_service.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add app/services/pipeline/__init__.py app/services/pipeline/fault_diagnosis_service.py tests/unit/test_fault_diagnosis_service.py
git commit -m "feat: implement fault diagnosis service with rule engine + LLM enhancement"
```

---

## Task 8: Task Pipeline Service (diagnosis → task → report)

**Files:**
- Create: `r-mos-backend/app/services/pipeline/task_pipeline_service.py`
- Test: `r-mos-backend/tests/unit/test_task_pipeline_service.py`

- [ ] **Step 1: Write failing test**

```python
# tests/unit/test_task_pipeline_service.py
"""Task pipeline service tests."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.pipeline.task_pipeline_service import TaskPipelineService


@pytest.mark.asyncio
async def test_create_task_from_diagnosis():
    """Creates task + execution from diagnosis result."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    # Mock SOP query
    mock_sop = MagicMock()
    mock_sop.id = 1
    mock_sop.name = "关节过热应急处理"
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_sop
    mock_db.execute = AsyncMock(return_value=mock_result)

    service = TaskPipelineService(mock_db)
    result = await service.create_task_from_diagnosis(
        diagnosis_trace_id="trace-001",
        fault_type="E001_OVERHEAT",
        student_id=1,
    )

    assert result["sop_name"] == "关节过热应急处理"
    assert result["task_id"] is not None
    assert mock_db.add.called


@pytest.mark.asyncio
async def test_complete_step_records_result():
    """Completing a step persists evidence and duration."""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    # Mock execution query
    mock_execution = MagicMock()
    mock_execution.id = 1
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_execution
    mock_db.execute = AsyncMock(return_value=mock_result)

    service = TaskPipelineService(mock_db)
    result = await service.complete_step(
        execution_id=1,
        step_index=1,
        evidence_type="photo",
        evidence_value={"url": "https://example.com/photo.jpg"},
        duration_seconds=45,
    )

    assert result["is_compliant"] is True
    assert mock_db.add.called
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd r-mos-backend && python -m pytest tests/unit/test_task_pipeline_service.py -v`
Expected: FAIL with import error

- [ ] **Step 3: Implement task pipeline service**

```python
# app/services/pipeline/task_pipeline_service.py
"""Task pipeline: diagnosis → task creation → step tracking → report."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus
from app.models.sop import SOP
from app.models.fault_sop_mapping import FaultSOPMapping
from app.models.task_execution import TaskExecution, TaskStepResult

logger = logging.getLogger(__name__)


class TaskPipelineService:
    """Orchestrates the diagnosis → task → execution → report pipeline."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_task_from_diagnosis(
        self,
        diagnosis_trace_id: str,
        fault_type: str,
        student_id: int,
    ) -> dict[str, Any]:
        """Create a maintenance task from diagnosis result."""
        # Find SOP via fault_sop_mapping
        stmt = (
            select(FaultSOPMapping)
            .where(FaultSOPMapping.fault_type == fault_type)
            .order_by(FaultSOPMapping.priority.desc())
            .limit(1)
        )
        mapping_result = await self.db.execute(stmt)
        mapping = mapping_result.scalar_one_or_none()

        sop_id = mapping.sop_id if mapping else None
        sop_name = ""

        if sop_id:
            sop_result = await self.db.execute(select(SOP).where(SOP.id == sop_id))
            sop = sop_result.scalar_one_or_none()
            sop_name = sop.name if sop else ""

        # Create Task
        task = Task(
            title=f"维保任务: {fault_type}",
            sop_id=sop_id,
            user_id=student_id,
            status=TaskStatus.IN_PROGRESS.value,
            started_at=datetime.utcnow(),
        )
        self.db.add(task)
        await self.db.flush()

        # Create TaskExecution
        execution = TaskExecution(
            task_id=task.id,
            student_id=student_id,
            sop_id=sop_id,
            diagnosis_trace_id=diagnosis_trace_id,
            fault_type=fault_type,
            status="in_progress",
        )
        self.db.add(execution)
        await self.db.commit()

        return {
            "task_id": task.id,
            "execution_id": execution.id,
            "sop_id": sop_id,
            "sop_name": sop_name,
            "fault_type": fault_type,
        }

    async def complete_step(
        self,
        execution_id: int,
        step_index: int,
        evidence_type: Optional[str] = None,
        evidence_value: Optional[dict] = None,
        duration_seconds: Optional[int] = None,
    ) -> dict[str, Any]:
        """Record step completion with evidence."""
        step_result = TaskStepResult(
            execution_id=execution_id,
            step_index=step_index,
            status="completed",
            duration_seconds=duration_seconds,
            evidence_type=evidence_type,
            evidence_value=evidence_value,
            is_compliant=True,  # TODO: validate against SOP step criteria
        )
        self.db.add(step_result)
        await self.db.commit()

        return {
            "step_index": step_index,
            "is_compliant": step_result.is_compliant,
            "feedback": None,
        }

    async def complete_task(
        self,
        execution_id: int,
    ) -> dict[str, Any]:
        """Mark execution complete and trigger report generation."""
        stmt = select(TaskExecution).where(TaskExecution.id == execution_id)
        result = await self.db.execute(stmt)
        execution = result.scalar_one_or_none()

        if not execution:
            return {"error": "Execution not found"}

        execution.status = "completed"
        execution.completed_at = datetime.utcnow()

        # Update parent task
        task_stmt = select(Task).where(Task.id == execution.task_id)
        task_result = await self.db.execute(task_stmt)
        task = task_result.scalar_one_or_none()
        if task:
            task.status = TaskStatus.COMPLETED.value
            task.completed_at = datetime.utcnow()

        await self.db.commit()

        return {
            "execution_id": execution_id,
            "task_id": execution.task_id,
            "status": "completed",
            "report_generation": "triggered",
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd r-mos-backend && python -m pytest tests/unit/test_task_pipeline_service.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add app/services/pipeline/task_pipeline_service.py tests/unit/test_task_pipeline_service.py
git commit -m "feat: implement task pipeline service (diagnosis→task→step→complete)"
```

---

## Task 9: Pipeline API Endpoints

**Files:**
- Create: `r-mos-backend/app/api/v1/endpoints/pipeline.py`
- Modify: `r-mos-backend/app/api/v1/__init__.py`

- [ ] **Step 1: Create pipeline endpoint file**

```python
# app/api/v1/endpoints/pipeline.py
"""Pipeline API — diagnosis-to-task-to-report flow."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.pipeline.fault_diagnosis_service import FaultDiagnosisService
from app.services.pipeline.task_pipeline_service import TaskPipelineService

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


class DiagnoseRequest(BaseModel):
    telemetry: dict[str, Any]
    fault_type_hint: Optional[str] = None


class DiagnoseResponse(BaseModel):
    success: bool
    fault_type: Optional[str]
    confidence: float
    affected_joints: list[str]
    reasoning: str
    recommended_sop: Optional[str]
    is_compound: bool
    llm_enhanced: bool = False


class CreateTaskFromDiagnosisRequest(BaseModel):
    diagnosis_trace_id: str
    fault_type: str
    student_id: int


class CreateTaskFromDiagnosisResponse(BaseModel):
    task_id: int
    execution_id: int
    sop_id: Optional[int]
    sop_name: str
    fault_type: str


class StepCompleteRequest(BaseModel):
    step_index: int
    evidence_type: Optional[str] = None
    evidence_value: Optional[dict] = None
    duration_seconds: Optional[int] = None


class StepCompleteResponse(BaseModel):
    step_index: int
    is_compliant: bool
    feedback: Optional[str] = None


class TaskCompleteResponse(BaseModel):
    execution_id: int
    task_id: int
    status: str
    report_generation: str


@router.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose_fault(request: DiagnoseRequest):
    """Analyze telemetry and diagnose fault."""
    service = FaultDiagnosisService()
    result = await service.diagnose(request.telemetry)
    return DiagnoseResponse(**result)


@router.post("/tasks/from-diagnosis", response_model=CreateTaskFromDiagnosisResponse)
async def create_task_from_diagnosis(
    request: CreateTaskFromDiagnosisRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create maintenance task from diagnosis result."""
    service = TaskPipelineService(db)
    result = await service.create_task_from_diagnosis(
        diagnosis_trace_id=request.diagnosis_trace_id,
        fault_type=request.fault_type,
        student_id=request.student_id,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return CreateTaskFromDiagnosisResponse(**result)


@router.post("/executions/{execution_id}/steps/complete", response_model=StepCompleteResponse)
async def complete_step(
    execution_id: int,
    request: StepCompleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Record step completion with evidence."""
    service = TaskPipelineService(db)
    result = await service.complete_step(
        execution_id=execution_id,
        step_index=request.step_index,
        evidence_type=request.evidence_type,
        evidence_value=request.evidence_value,
        duration_seconds=request.duration_seconds,
    )
    return StepCompleteResponse(**result)


@router.post("/executions/{execution_id}/complete", response_model=TaskCompleteResponse)
async def complete_task(
    execution_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Mark task execution complete, trigger report generation."""
    service = TaskPipelineService(db)
    result = await service.complete_task(execution_id=execution_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return TaskCompleteResponse(**result)
```

- [ ] **Step 2: Register router in `__init__.py`**

Add to `app/api/v1/__init__.py`:
```python
from .endpoints.pipeline import router as pipeline_router
app.include_router(pipeline_router, prefix="/api/v1")
```

- [ ] **Step 3: Verify endpoint registration**

Run: `cd r-mos-backend && python -c "from app.api.v1.endpoints.pipeline import router; print(f'{len(router.routes)} routes registered')"`
Expected: `4 routes registered`

- [ ] **Step 4: Commit**

```bash
git add app/api/v1/endpoints/pipeline.py app/api/v1/__init__.py
git commit -m "feat: add pipeline API endpoints (diagnose, create-task, step-complete, task-complete)"
```

---

## Task 10: Seed Data — 3 SOPs + Fault Mappings + Knowledge

**Files:**
- Create: `r-mos-backend/scripts/seed_fault_sops.py`
- Create: `r-mos-backend/scripts/seed_knowledge.py`

- [ ] **Step 1: Create SOP + mapping seed script**

```python
# scripts/seed_fault_sops.py
"""Seed 3 fault-case SOPs and their fault_sop_mapping entries."""
import asyncio
import sys
sys.path.insert(0, ".")

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.sop import SOP, SOPStep
from app.models.fault_sop_mapping import FaultSOPMapping


SOPS = [
    {
        "name": "关节过热应急处理",
        "description": "单关节温度超限的应急降温和恢复流程",
        "applicable_model": "ATOM-01",
        "category": "thermal",
        "difficulty_level": "low",
        "estimated_time": 900,  # 15 minutes
        "fault_type": "E001_OVERHEAT",
        "steps": [
            {"step_index": 1, "title": "停机断电", "description": "按下急停按钮，确认电源指示灯熄灭", "expected_action": "power_off", "is_critical": True, "severity_level": "SAFETY_HALT", "timeout_seconds": 60, "tools_required": []},
            {"step_index": 2, "title": "等待降温", "description": "等待关节温度降至50°C以下，使用红外测温仪监测", "expected_action": "wait_cool", "is_critical": False, "severity_level": "WARN", "timeout_seconds": 300, "tools_required": ["红外测温仪"]},
            {"step_index": 3, "title": "检查散热风扇", "description": "检查关节散热风扇是否正常工作，清理灰尘堵塞", "expected_action": "inspect_fan", "is_critical": False, "severity_level": "WARN", "timeout_seconds": 180, "tools_required": ["手电筒", "压缩空气罐"]},
            {"step_index": 4, "title": "重启验证", "description": "重新上电，运行30秒空载测试，确认温度不再异常升高", "expected_action": "verify_restart", "is_critical": True, "severity_level": "WARN", "timeout_seconds": 120, "tools_required": []},
        ],
    },
    {
        "name": "关节松动检修",
        "description": "关节位置偏差超限的拆装校准流程",
        "applicable_model": "ATOM-01",
        "category": "mechanical",
        "difficulty_level": "medium",
        "estimated_time": 1800,  # 30 minutes
        "fault_type": "E005_LOOSE",
        "steps": [
            {"step_index": 1, "title": "断电锁定", "description": "断电并锁定关节防止意外移动", "expected_action": "power_off_lock", "is_critical": True, "severity_level": "SAFETY_HALT", "timeout_seconds": 60, "tools_required": []},
            {"step_index": 2, "title": "拆卸外壳", "description": "使用十字螺丝刀拆卸关节保护外壳（4颗M3螺丝）", "expected_action": "remove_cover", "is_critical": False, "severity_level": "WARN", "timeout_seconds": 300, "tools_required": ["十字螺丝刀PH2"]},
            {"step_index": 3, "title": "检查紧固件", "description": "目视检查所有紧固螺栓，标记松动位置", "expected_action": "inspect_bolts", "is_critical": False, "severity_level": "WARN", "timeout_seconds": 180, "tools_required": ["记号笔", "手电筒"]},
            {"step_index": 4, "title": "按标准扭矩紧固", "description": "使用扭矩扳手按规定力矩（8Nm）紧固所有螺栓", "expected_action": "torque_bolts", "is_critical": True, "severity_level": "WARN", "timeout_seconds": 300, "tools_required": ["扭矩扳手(8Nm)"]},
            {"step_index": 5, "title": "间隙测量", "description": "使用塞尺测量关节间隙，记录数值（标准: 0.02-0.05mm）", "expected_action": "measure_gap", "is_critical": True, "severity_level": "WARN", "timeout_seconds": 180, "tools_required": ["塞尺(0.02-0.10mm)"]},
            {"step_index": 6, "title": "回装校准", "description": "回装外壳，上电运行校准程序，验证位置精度恢复", "expected_action": "reassemble_calibrate", "is_critical": True, "severity_level": "WARN", "timeout_seconds": 300, "tools_required": ["十字螺丝刀PH2"]},
        ],
    },
    {
        "name": "电压跌落复合故障处理",
        "description": "电源电压跌落引发多关节过热的系统级排查",
        "applicable_model": "ATOM-01",
        "category": "electrical",
        "difficulty_level": "high",
        "estimated_time": 2700,  # 45 minutes
        "fault_type": "E003_VOLTAGE_DROP",
        "steps": [
            {"step_index": 1, "title": "全机断电", "description": "切断总电源，确认所有指示灯熄灭", "expected_action": "full_power_off", "is_critical": True, "severity_level": "SAFETY_HALT", "timeout_seconds": 60, "tools_required": []},
            {"step_index": 2, "title": "检查电源模块", "description": "打开电源舱，目视检查电源模块外观（鼓包、烧焦、异味）", "expected_action": "inspect_psu", "is_critical": False, "severity_level": "WARN", "timeout_seconds": 180, "tools_required": ["手电筒"]},
            {"step_index": 3, "title": "测量各路电压", "description": "使用万用表测量主路24V、逻辑5V、伺服48V各路输出", "expected_action": "measure_voltage", "is_critical": True, "severity_level": "WARN", "timeout_seconds": 300, "tools_required": ["数字万用表"]},
            {"step_index": 4, "title": "更换/修复电源", "description": "根据测量结果更换故障电源模块或修复接线", "expected_action": "replace_psu", "is_critical": True, "severity_level": "WARN", "timeout_seconds": 600, "tools_required": ["备用电源模块", "螺丝刀套装"]},
            {"step_index": 5, "title": "上电验证电压", "description": "重新上电，确认各路电压恢复正常范围", "expected_action": "verify_voltage", "is_critical": True, "severity_level": "WARN", "timeout_seconds": 120, "tools_required": ["数字万用表"]},
            {"step_index": 6, "title": "逐关节检查温度", "description": "逐个检查之前过热关节的当前温度", "expected_action": "check_temps", "is_critical": False, "severity_level": "WARN", "timeout_seconds": 180, "tools_required": ["红外测温仪"]},
            {"step_index": 7, "title": "冷却处理", "description": "对仍超温的关节进行辅助降温", "expected_action": "cool_joints", "is_critical": False, "severity_level": "WARN", "timeout_seconds": 300, "tools_required": ["压缩空气罐"]},
            {"step_index": 8, "title": "全系统功能验证", "description": "运行全关节自检程序，确认各关节正常运动", "expected_action": "full_system_test", "is_critical": True, "severity_level": "WARN", "timeout_seconds": 300, "tools_required": []},
        ],
    },
]


async def seed():
    async with AsyncSessionLocal() as db:
        for sop_data in SOPS:
            fault_type = sop_data.pop("fault_type")
            steps_data = sop_data.pop("steps")

            # Check if SOP already exists
            existing = await db.execute(select(SOP).where(SOP.name == sop_data["name"]))
            if existing.scalar_one_or_none():
                print(f"  Skip (exists): {sop_data['name']}")
                continue

            sop = SOP(**sop_data)
            db.add(sop)
            await db.flush()

            for step_data in steps_data:
                step = SOPStep(sop_id=sop.id, **step_data)
                db.add(step)

            # Create fault_sop_mapping
            mapping = FaultSOPMapping(
                fault_type=fault_type,
                sop_id=sop.id,
                difficulty=sop_data["difficulty_level"],
                priority=1,
            )
            db.add(mapping)

            print(f"  Seeded: {sop_data['name']} ({len(steps_data)} steps)")

        await db.commit()
        print("Done: 3 SOPs + mappings seeded.")


if __name__ == "__main__":
    asyncio.run(seed())
```

- [ ] **Step 2: Create knowledge seed script**

```python
# scripts/seed_knowledge.py
"""Seed 5 knowledge documents for 3 fault cases."""
import asyncio
import sys
sys.path.insert(0, ".")

from datetime import datetime
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.knowledge_document import KnowledgeDocument


DOCUMENTS = [
    {
        "title": "关节过热维修手册",
        "doc_type": "manual",
        "fault_tags": ["E001_OVERHEAT"],
        "sop_tags": ["sop-e001-overheat"],
        "content": """# 关节过热维修手册

## 1. 过热原因分析

ATOM-01 关节过热的常见原因：
- 散热风扇堵塞或故障（占比45%）
- 关节长时间高负载运行（占比30%）
- 环境温度过高（占比15%）
- 轴承磨损导致摩擦增大（占比10%）

## 2. 温度阈值标准

| 状态 | 温度范围 | 处理方式 |
|------|----------|----------|
| 正常 | < 55°C | 继续运行 |
| 预警 | 55-70°C | 降低负载 |
| 告警 | 70-80°C | 立即停机 |
| 危险 | > 80°C | 紧急断电 |

## 3. 降温操作步骤

1. 确认安全后按下急停按钮
2. 等待自然降温（不可使用液体冷却）
3. 使用红外测温仪确认温度降至50°C以下
4. 检查散热通道是否通畅

## 4. 传感器校准

温度传感器每6个月需要校准一次：
- 标准环境温度下偏差不超过±2°C
- 使用标准热源进行三点校准（25°C, 50°C, 75°C）
""",
    },
    {
        "title": "关节松动维修手册",
        "doc_type": "manual",
        "fault_tags": ["E005_LOOSE"],
        "sop_tags": ["sop-e005-loose"],
        "content": """# 关节松动维修手册

## 1. 松动检测方法

### 位置偏差检测
- 正常偏差范围: < 0.05 rad
- 预警阈值: 0.05 - 0.10 rad
- 告警阈值: > 0.10 rad

### 物理检测
- 手动摇晃关节，感受是否有明显间隙
- 使用塞尺测量轴承间隙（标准: 0.02-0.05mm）

## 2. 扭矩标准

ATOM-01 各关节紧固扭矩：
| 关节 | 螺栓规格 | 标准扭矩 |
|------|----------|----------|
| 肩关节 | M4 | 5 Nm |
| 肘关节 | M3 | 3 Nm |
| 腕关节 | M2.5 | 2 Nm |
| 髋关节 | M5 | 8 Nm |
| 膝关节 | M5 | 8 Nm |
| 踝关节 | M4 | 5 Nm |

## 3. 紧固流程

1. 按对角线顺序预紧（50%扭矩）
2. 再按对角线顺序终紧（100%扭矩）
3. 等待5分钟后复检（热膨胀稳定后）

## 4. 拆装顺序

拆卸: 外壳→护线管→紧固螺栓→关节模块
安装: 关节模块→紧固螺栓→护线管→外壳（逆序）
""",
    },
    {
        "title": "电压系统维修手册",
        "doc_type": "manual",
        "fault_tags": ["E003_VOLTAGE_DROP", "E001_OVERHEAT"],
        "sop_tags": ["sop-e003-e001-compound"],
        "content": """# 电压系统维修手册

## 1. 电压跌落排查流程

### 症状识别
- 主路电压低于20V（正常24V±2V）
- 多关节同时出现过热（电流补偿效应）
- 逻辑系统不稳定

### 因果关系
电压跌落 → 电机PID补偿 → 电流增大 → 发热增加 → 过热告警

**关键判断**: 如果多个关节同时过热，且伴随电压异常，根因是电压而非过热本身。

## 2. 联动故障诊断树

```
电压 < 20V?
├── 是 → 检查电源模块
│   ├── 外观异常? → 更换电源
│   └── 外观正常 → 检查接线/负载
└── 否 → 单关节过热流程
```

## 3. 安全断电流程

⚠️ 电压异常时的断电顺序：
1. 停止所有关节运动命令
2. 等待2秒（惯性停止）
3. 切断伺服电源（48V）
4. 切断主电源（24V）
5. 确认全部指示灯熄灭

**禁止**: 直接拔总电源（可能损坏控制板）

## 4. 电压测量要求

| 电路 | 正常范围 | 测量点 |
|------|----------|--------|
| 主路 | 23-25V | PSU输出端 |
| 逻辑 | 4.9-5.1V | 控制板输入 |
| 伺服 | 46-50V | 驱动器输入 |
""",
    },
    {
        "title": "安全操作通用规范",
        "doc_type": "guide",
        "fault_tags": ["*"],
        "sop_tags": [],
        "content": """# 安全操作通用规范

## 1. 通电/断电标准

### 上电流程
1. 确认周围无人员（安全距离 > 1.5m）
2. 目视检查机器人外观无异常
3. 接通主电源
4. 等待系统自检完成（约15秒）
5. 确认所有状态灯正常（绿色常亮）

### 断电流程
1. 发送停止命令
2. 等待所有关节停止运动
3. 切断伺服电源
4. 切断主电源
5. 确认指示灯全部熄灭

## 2. 防护装备要求

| 操作类型 | 必需装备 |
|----------|----------|
| 日常巡检 | 工作服、防护眼镜 |
| 关节维修 | 工作服、防护眼镜、绝缘手套 |
| 电气维修 | 工作服、防护眼镜、绝缘手套、绝缘鞋 |

## 3. 应急处理

### 急停情况
- 机器人异常运动
- 人员进入安全区域
- 冒烟、异味、火花

### 急停后操作
1. 不要立即上电
2. 排查异常原因
3. 确认安全后方可重启
""",
    },
    {
        "title": "ATOM-01 结构参数手册",
        "doc_type": "spec",
        "fault_tags": ["*"],
        "sop_tags": [],
        "content": """# ATOM-01 结构参数手册

## 1. 关节参数

| 关节 | 自由度 | 额定扭矩 | 最大温度 | 额定电压 |
|------|--------|----------|----------|----------|
| 腰部(waist) | 1 DOF | 50 Nm | 80°C | 24V |
| 肩部(shoulder) | 2 DOF | 30 Nm | 75°C | 24V |
| 肘部(elbow) | 1 DOF | 20 Nm | 70°C | 24V |
| 髋部(hip) | 2 DOF | 60 Nm | 80°C | 24V |
| 膝部(knee) | 1 DOF | 50 Nm | 80°C | 24V |
| 踝部(ankle) | 2 DOF | 25 Nm | 70°C | 24V |

## 2. 额定值范围

### 温度
- 环境温度: 0-40°C
- 关节正常工作温度: 30-55°C
- 散热器工作温度: 40-65°C

### 电气
- 主电源: 24V DC (±10%)
- 伺服电源: 48V DC (±5%)
- 逻辑电源: 5V DC (±2%)
- 单关节最大电流: 5A

## 3. 零件编号

| 部件 | 编号 | 供应商 |
|------|------|--------|
| 腰关节电机 | MOT-W-001 | 内部 |
| 肘关节减速器 | GBX-E-002 | 哈默纳科 |
| 膝关节轴承 | BRG-K-003 | NSK |
| 散热风扇 | FAN-001 | 台达 |
| 电源模块 | PSU-24V-300W | 明纬 |
""",
    },
]


async def seed():
    async with AsyncSessionLocal() as db:
        for doc_data in DOCUMENTS:
            existing = await db.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.title == doc_data["title"])
            )
            if existing.scalar_one_or_none():
                print(f"  Skip (exists): {doc_data['title']}")
                continue

            doc = KnowledgeDocument(
                **doc_data,
                status="APPROVED",
                approved_at=datetime.utcnow(),
            )
            db.add(doc)
            print(f"  Seeded: {doc_data['title']}")

        await db.commit()
        print("Done: 5 knowledge documents seeded.")


if __name__ == "__main__":
    asyncio.run(seed())
```

- [ ] **Step 3: Verify scripts parse without error**

Run: `cd r-mos-backend && python -c "import scripts.seed_fault_sops; import scripts.seed_knowledge; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add scripts/seed_fault_sops.py scripts/seed_knowledge.py
git commit -m "feat: add seed scripts for 3 SOPs + 5 knowledge documents"
```

---

## Task 11: Frontend — Pipeline API Client

**Files:**
- Create: `r-mos-frontend/src/api/pipeline.ts`

- [ ] **Step 1: Create pipeline API client**

```typescript
// src/api/pipeline.ts
import axios from 'axios'

const api = axios.create({ baseURL: '/api/v1/pipeline' })

export interface DiagnoseRequest {
  telemetry: Record<string, unknown>
  fault_type_hint?: string
}

export interface DiagnoseResponse {
  success: boolean
  fault_type: string | null
  confidence: number
  affected_joints: string[]
  reasoning: string
  recommended_sop: string | null
  is_compound: boolean
  llm_enhanced: boolean
}

export interface CreateTaskRequest {
  diagnosis_trace_id: string
  fault_type: string
  student_id: number
}

export interface CreateTaskResponse {
  task_id: number
  execution_id: number
  sop_id: number | null
  sop_name: string
  fault_type: string
}

export interface StepCompleteRequest {
  step_index: number
  evidence_type?: string
  evidence_value?: Record<string, unknown>
  duration_seconds?: number
}

export interface StepCompleteResponse {
  step_index: number
  is_compliant: boolean
  feedback: string | null
}

export interface TaskCompleteResponse {
  execution_id: number
  task_id: number
  status: string
  report_generation: string
}

export async function diagnoseFault(data: DiagnoseRequest): Promise<DiagnoseResponse> {
  const res = await api.post<DiagnoseResponse>('/diagnose', data)
  return res.data
}

export async function createTaskFromDiagnosis(data: CreateTaskRequest): Promise<CreateTaskResponse> {
  const res = await api.post<CreateTaskResponse>('/tasks/from-diagnosis', data)
  return res.data
}

export async function completeStep(executionId: number, data: StepCompleteRequest): Promise<StepCompleteResponse> {
  const res = await api.post<StepCompleteResponse>(`/executions/${executionId}/steps/complete`, data)
  return res.data
}

export async function completeTask(executionId: number): Promise<TaskCompleteResponse> {
  const res = await api.post<TaskCompleteResponse>(`/executions/${executionId}/complete`)
  return res.data
}
```

- [ ] **Step 2: Commit**

```bash
git add r-mos-frontend/src/api/pipeline.ts
git commit -m "feat: add frontend pipeline API client"
```

---

## Task 12: Frontend — FaultAlertCard on MonitorPage

**Files:**
- Create: `r-mos-frontend/src/components/Monitor/FaultAlertCard.tsx`
- Modify: `r-mos-frontend/src/pages/MonitorPage.tsx`
- Test: `r-mos-frontend/src/pages/__tests__/MonitorPage.fault-alert.test.tsx`

- [ ] **Step 1: Create FaultAlertCard component**

```tsx
// src/components/Monitor/FaultAlertCard.tsx
import { AlertTriangle, ArrowRight, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export interface FaultAlert {
  id: string
  fault_type: string
  fault_name: string
  affected_joints: string[]
  current_value: string
  threshold: string
  severity: 'warning' | 'danger'
}

interface FaultAlertCardProps {
  alert: FaultAlert
  onDiagnose: (alert: FaultAlert) => void
  onDismiss: (alertId: string) => void
}

export function FaultAlertCard({ alert, onDiagnose, onDismiss }: FaultAlertCardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border p-4 animate-in slide-in-from-top-2',
        alert.severity === 'danger'
          ? 'border-red-500/40 bg-red-500/10'
          : 'border-amber-500/40 bg-amber-500/10',
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <AlertTriangle
            className={cn(
              'h-5 w-5',
              alert.severity === 'danger' ? 'text-red-400' : 'text-amber-400',
            )}
          />
          <div>
            <div className="text-sm font-medium text-text-primary">
              {alert.fault_name}
            </div>
            <div className="text-xs text-text-muted">
              {alert.affected_joints.join(', ')} — {alert.current_value}（阈值 {alert.threshold}）
            </div>
          </div>
        </div>
        <button onClick={() => onDismiss(alert.id)} className="text-text-muted hover:text-text-primary">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="mt-3 flex gap-2">
        <Button size="sm" onClick={() => onDiagnose(alert)}>
          一键诊断 <ArrowRight className="ml-1 h-3 w-3" />
        </Button>
        <Button size="sm" variant="ghost" onClick={() => onDismiss(alert.id)}>
          忽略
        </Button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Integrate into MonitorPage**

Add to the top of `MonitorPage.tsx` (after existing imports):
```tsx
import { FaultAlertCard, type FaultAlert } from '@/components/Monitor/FaultAlertCard'
```

Add state and fault detection logic inside the MonitorPage component:
```tsx
const [faultAlerts, setFaultAlerts] = useState<FaultAlert[]>([])

// Detect faults from telemetry
useMemo(() => {
  if (!telemetryData?.joints) return
  const alerts: FaultAlert[] = []
  
  for (const joint of telemetryData.joints) {
    if ((joint.temperature ?? 0) >= 70) {
      alerts.push({
        id: `${joint.joint_id}-overheat`,
        fault_type: 'E001_OVERHEAT',
        fault_name: '关节过热告警',
        affected_joints: [joint.joint_id],
        current_value: `${joint.temperature}°C`,
        threshold: '70°C',
        severity: (joint.temperature ?? 0) >= 80 ? 'danger' : 'warning',
      })
    }
  }
  
  const voltage = telemetryData.sensors?.voltage?.main
  if (voltage && voltage < 20) {
    alerts.push({
      id: 'voltage-drop',
      fault_type: 'E003_VOLTAGE_DROP',
      fault_name: '电压跌落告警',
      affected_joints: ['system'],
      current_value: `${voltage}V`,
      threshold: '20V',
      severity: 'danger',
    })
  }
  
  setFaultAlerts(alerts)
}, [telemetryData])

const handleDiagnose = (alert: FaultAlert) => {
  navigate(`/agent/workbench?fault_type=${alert.fault_type}&joints=${alert.affected_joints.join(',')}`)
}

const handleDismissAlert = (alertId: string) => {
  setFaultAlerts(prev => prev.filter(a => a.id !== alertId))
}
```

Render alerts at the top of the page content area:
```tsx
{faultAlerts.length > 0 && (
  <div className="space-y-2 mb-4">
    {faultAlerts.map(alert => (
      <FaultAlertCard
        key={alert.id}
        alert={alert}
        onDiagnose={handleDiagnose}
        onDismiss={handleDismissAlert}
      />
    ))}
  </div>
)}
```

- [ ] **Step 3: Write test for FaultAlertCard integration**

```tsx
// src/pages/__tests__/MonitorPage.fault-alert.test.tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import { FaultAlertCard, type FaultAlert } from '@/components/Monitor/FaultAlertCard'

describe('FaultAlertCard', () => {
  const mockAlert: FaultAlert = {
    id: 'waist-overheat',
    fault_type: 'E001_OVERHEAT',
    fault_name: '关节过热告警',
    affected_joints: ['waist'],
    current_value: '78°C',
    threshold: '70°C',
    severity: 'danger',
  }

  it('renders fault info and buttons', () => {
    render(
      <FaultAlertCard alert={mockAlert} onDiagnose={vi.fn()} onDismiss={vi.fn()} />
    )
    expect(screen.getByText('关节过热告警')).toBeTruthy()
    expect(screen.getByText(/78°C/)).toBeTruthy()
    expect(screen.getByRole('button', { name: /一键诊断/ })).toBeTruthy()
  })

  it('calls onDiagnose when button clicked', async () => {
    const onDiagnose = vi.fn()
    const user = userEvent.setup()
    render(
      <FaultAlertCard alert={mockAlert} onDiagnose={onDiagnose} onDismiss={vi.fn()} />
    )
    await user.click(screen.getByRole('button', { name: /一键诊断/ }))
    expect(onDiagnose).toHaveBeenCalledWith(mockAlert)
  })
})
```

- [ ] **Step 4: Run test**

Run: `cd r-mos-frontend && npx vitest run src/pages/__tests__/MonitorPage.fault-alert.test.tsx`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add r-mos-frontend/src/components/Monitor/FaultAlertCard.tsx r-mos-frontend/src/pages/MonitorPage.tsx r-mos-frontend/src/pages/__tests__/MonitorPage.fault-alert.test.tsx
git commit -m "feat: add FaultAlertCard on MonitorPage with one-click diagnosis"
```

---

## Task 13: Frontend — AgentWorkbench "Create Task" Action

**Files:**
- Modify: `r-mos-frontend/src/pages/agent/AgentWorkbenchPage.tsx`

- [ ] **Step 1: Add task creation flow after diagnosis**

Add import at top:
```tsx
import { createTaskFromDiagnosis } from '@/api/pipeline'
```

After the existing `DiagnosisPanel` section in the render, add a new action block that appears when diagnosis returns `recommended_sop`:

```tsx
// Inside the component, add state:
const [createdTask, setCreatedTask] = useState<{ task_id: number; execution_id: number; sop_name: string } | null>(null)

// Add handler:
const handleCreateTask = async () => {
  if (!lastDiagnosisResult) return
  try {
    const result = await createTaskFromDiagnosis({
      diagnosis_trace_id: lastDiagnosisResult.trace_id,
      fault_type: lastDiagnosisResult.fault_type,
      student_id: 1, // from auth store
    })
    setCreatedTask(result)
    message.success(`维保任务已创建: ${result.sop_name}`)
    // Navigate to maintenance page
    navigate(`/maintenance?task_id=${result.task_id}&execution_id=${result.execution_id}`)
  } catch (e) {
    message.error('创建维保任务失败')
  }
}
```

Add button in the diagnosis result area:
```tsx
{lastDiagnosisResult?.recommended_sop && !createdTask && (
  <div className="mt-4 flex items-center gap-3 rounded-lg border border-blue-500/30 bg-blue-500/5 p-3">
    <div className="flex-1">
      <div className="text-sm font-medium">推荐 SOP: {lastDiagnosisResult.sop_name}</div>
      <div className="text-xs text-text-muted">预估 {lastDiagnosisResult.estimated_minutes} 分钟</div>
    </div>
    <Button onClick={handleCreateTask}>
      创建维保任务 <ArrowRight className="ml-1 h-3 w-3" />
    </Button>
  </div>
)}
```

- [ ] **Step 2: Verify compilation**

Run: `cd r-mos-frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add r-mos-frontend/src/pages/agent/AgentWorkbenchPage.tsx
git commit -m "feat: add 'create maintenance task' action in AgentWorkbench after diagnosis"
```

---

## Task 14: Frontend — SOPPlayer Step Completion Backend Sync

**Files:**
- Modify: `r-mos-frontend/src/components/Maintenance/SOPPlayerAdjudicated.tsx`

- [ ] **Step 1: Add step completion API calls**

Add import:
```tsx
import { completeStep, completeTask } from '@/api/pipeline'
```

In the step completion handler (where step status transitions to completed), add:

```tsx
// After existing step completion logic:
const searchParams = new URLSearchParams(window.location.search)
const executionId = searchParams.get('execution_id')

if (executionId) {
  completeStep(Number(executionId), {
    step_index: stepIndex,
    evidence_type: stepEvidence?.type,
    evidence_value: stepEvidence?.value,
    duration_seconds: Math.round(stepDuration / 1000),
  }).catch(console.error)  // Non-blocking
}
```

In the final step completion (all steps done), add:

```tsx
if (executionId) {
  completeTask(Number(executionId))
    .then((result) => {
      if (result.report_generation === 'triggered') {
        // Navigate to report page
        navigate(`/reports?task_id=${result.task_id}`)
      }
    })
    .catch(console.error)
}
```

- [ ] **Step 2: Verify compilation**

Run: `cd r-mos-frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add r-mos-frontend/src/components/Maintenance/SOPPlayerAdjudicated.tsx
git commit -m "feat: sync SOP step completion to backend pipeline"
```

---

## Task 15: LLM Health Check Endpoint

**Files:**
- Create: `r-mos-backend/app/api/v1/endpoints/llm_health.py`
- Modify: `r-mos-backend/app/api/v1/__init__.py`

- [ ] **Step 1: Create LLM health endpoint**

```python
# app/api/v1/endpoints/llm_health.py
"""LLM health check endpoint."""
import asyncio
import time
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from app.services.llm.router import llm_router, LLMProvider
from app.core.config import settings

router = APIRouter(prefix="/llm", tags=["llm"])


class ProviderHealth(BaseModel):
    status: str  # ok / error / unconfigured
    latency_ms: Optional[int] = None
    error: Optional[str] = None


class LLMHealthResponse(BaseModel):
    deepseek: ProviderHealth
    minimax: ProviderHealth
    mock: ProviderHealth
    active_provider: str


async def _check_provider(provider: LLMProvider, model: str) -> ProviderHealth:
    """Ping a provider with a minimal request."""
    try:
        client = llm_router._get_client(provider)
        start = time.time()
        await asyncio.wait_for(
            client.chat(
                messages=[{"role": "user", "content": "ping"}],
                model=model,
                max_tokens=5,
            ),
            timeout=5.0,
        )
        latency = int((time.time() - start) * 1000)
        return ProviderHealth(status="ok", latency_ms=latency)
    except asyncio.TimeoutError:
        return ProviderHealth(status="error", error="timeout")
    except Exception as e:
        return ProviderHealth(status="error", error=str(e)[:100])


@router.get("/health", response_model=LLMHealthResponse)
async def llm_health():
    """Check health of all LLM providers."""
    deepseek_health = ProviderHealth(status="unconfigured")
    minimax_health = ProviderHealth(status="unconfigured")

    if settings.DEEPSEEK_API_KEY:
        deepseek_health = await _check_provider(LLMProvider.DEEPSEEK, "deepseek-chat")

    if settings.MINIMAX_API_KEY:
        minimax_health = await _check_provider(LLMProvider.MINIMAX, "abab6.5-chat")

    # Determine active provider
    if deepseek_health.status == "ok":
        active = "deepseek"
    elif minimax_health.status == "ok":
        active = "minimax"
    else:
        active = "mock"

    return LLMHealthResponse(
        deepseek=deepseek_health,
        minimax=minimax_health,
        mock=ProviderHealth(status="always_available"),
        active_provider=active,
    )
```

- [ ] **Step 2: Register router**

Add to `app/api/v1/__init__.py`:
```python
from .endpoints.llm_health import router as llm_health_router
app.include_router(llm_health_router, prefix="/api/v1")
```

- [ ] **Step 3: Commit**

```bash
git add app/api/v1/endpoints/llm_health.py app/api/v1/__init__.py
git commit -m "feat: add GET /api/v1/llm/health endpoint for provider status"
```

---

## Task 16: Full Backend Test Suite Verification

**Files:** None (verification only)

- [ ] **Step 1: Run all backend tests**

Run: `cd r-mos-backend && python -m pytest tests/ -v --tb=short`
Expected: All new tests pass, no regressions in existing tests.

- [ ] **Step 2: Run frontend compilation check**

Run: `cd r-mos-frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Run frontend tests**

Run: `cd r-mos-frontend && npx vitest run`
Expected: All tests pass

- [ ] **Step 4: Commit any fixes needed**

If any test failures, fix them and commit with:
```bash
git commit -m "fix: resolve test issues from pipeline integration"
```

---

## Task 17: Database Migration

**Files:**
- Create: Alembic migration file

- [ ] **Step 1: Generate migration**

Run: `cd r-mos-backend && alembic revision --autogenerate -m "add fault_sop_mapping, task_execution, knowledge_document tables"`

- [ ] **Step 2: Review generated migration**

Read the generated migration file, verify it includes:
- `fault_sop_mappings` table
- `task_executions` table
- `task_step_results` table
- `knowledge_documents` table

- [ ] **Step 3: Run migration**

Run: `cd r-mos-backend && alembic upgrade head`
Expected: Migration applies successfully

- [ ] **Step 4: Run seed scripts**

Run: `cd r-mos-backend && python scripts/seed_fault_sops.py && python scripts/seed_knowledge.py`
Expected: "Done: 3 SOPs + mappings seeded." and "Done: 5 knowledge documents seeded."

- [ ] **Step 5: Commit**

```bash
git add alembic/versions/
git commit -m "feat: add database migration for pipeline tables"
```

---

## Task 18: End-to-End Smoke Test

**Files:** None (verification only)

- [ ] **Step 1: Start backend**

Run: `cd r-mos-backend && python main.py`

- [ ] **Step 2: Start frontend**

Run: `cd r-mos-frontend && npm run dev`

- [ ] **Step 3: Verify pipeline API**

```bash
# Diagnose with overheating telemetry
curl -X POST http://localhost:8000/api/v1/pipeline/diagnose \
  -H "Content-Type: application/json" \
  -d '{"telemetry":{"joints":[{"joint_id":"waist","temperature":78,"velocity":0.1,"torque":1.2}],"sensors":{"voltage":{"main":24}}}}'

# Expected: {"success":true,"fault_type":"E001_OVERHEAT","confidence":0.9,...}
```

- [ ] **Step 4: Verify LLM health**

```bash
curl http://localhost:8000/api/v1/llm/health
# Expected: {"deepseek":{"status":"unconfigured"},"minimax":{"status":"unconfigured"},"mock":{"status":"always_available"},"active_provider":"mock"}
```

- [ ] **Step 5: Verify frontend renders fault alert**

Open `http://localhost:5173/monitor` in browser. If WebSocket pushes telemetry with temperature > 70, a FaultAlertCard should appear.

- [ ] **Step 6: Tag release**

```bash
git tag v0.3.0-pipeline-llm-knowledge
```
