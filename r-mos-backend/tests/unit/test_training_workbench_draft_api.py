from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models as app_models  # noqa: F401
from app.core.database import get_db
from app.models.base import Base
from app.models.school import School
from main import app

# onboarding 注册需要的白名单学校（测试统一使用）
TEST_SCHOOL_NAME = "测试学校"


@pytest.fixture(scope="module")
def training_workbench_env() -> tuple[TestClient, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async def init_models() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(School.__table__.insert().values(name=TEST_SCHOOL_NAME))

    asyncio.run(init_models())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client, session_factory

    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def _register_and_login(client: TestClient, *, email: str) -> tuple[int, str]:
    register_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPass123",
            "full_name": "Training Draft User",
            "role": "teacher",
            "school_name": TEST_SCHOOL_NAME,
        },
    )
    assert register_resp.status_code == 201
    user_id = int(register_resp.json()["user_id"])

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert login_resp.status_code == 200
    return user_id, login_resp.json()["access_token"]


def test_training_workbench_draft_uses_user_llm_preferences(
    training_workbench_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _session_factory = training_workbench_env
    _user_id, token = _register_and_login(client, email=f"draft_{uuid4().hex[:8]}@example.com")

    save_pref_resp = client.put(
        "/api/v1/agent/preference/llm",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "provider": "openai",
            "model": "MiniMax-M2.5",
            "base_url": "https://api.minimaxi.com/v1",
            "api_key": "sk-training-1234567890",
        },
    )
    assert save_pref_resp.status_code == 200

    captured: dict[str, str] = {}

    async def _fake_chat(*, messages, provider, model, temperature, max_tokens, api_key=None, base_url=None, tools=None):  # noqa: ANN001
        captured["provider"] = provider.value
        captured["model"] = model
        captured["api_key"] = api_key
        captured["base_url"] = base_url
        captured["prompt"] = messages[-1]["content"]
        return SimpleNamespace(
            content=json.dumps(
                {
                    "project": {
                        "title": "ATOM01 关节盖拆装训练",
                        "summary": "围绕关节盖拆装进行的演示训练。",
                    },
                    "steps": [
                        {
                            "id": "step_prepare",
                            "title": "步骤 1: 准备工位",
                            "instruction": "确认 PPE、断电和工具摆位。",
                            "evidence_hint": "上传工位全景照片。",
                            "model_targets": ["torso_link"],
                            "tools": [
                                {
                                    "name": "绝缘手套",
                                    "spec": "A级绝缘",
                                    "is_critical": True,
                                }
                            ],
                        }
                    ],
                    "messages": [
                        {"role": "assistant", "content": "先确认绝缘手套和断电挂牌。"},
                        {"role": "teacher", "content": "证据必须覆盖工位和工具状态。"},
                    ],
                }
            ),
            provider=provider,
            model=model,
            tokens_in=120,
            tokens_out=180,
            raw_response={"ok": True},
            prompt_hash="prompt",
            response_hash="response",
        )

    monkeypatch.setattr("app.services.training.workbench_draft_generator.llm_router.chat", _fake_chat)

    draft_resp = client.post(
        "/api/v1/training/workbench/draft",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "robot_model": "ATOM01",
            "task_summary": "髋关节电机盖拆装",
            "focus_prompt": "强调工具确认、证据留存和 AI 提示",
        },
    )

    assert draft_resp.status_code == 200
    payload = draft_resp.json()
    assert payload["project"]["title"] == "ATOM01 关节盖拆装训练"
    assert payload["steps"][0]["status"] == "active"
    assert payload["steps"][0]["model_targets"] == ["torso_link"]
    assert payload["steps"][0]["tools"][0]["name"] == "绝缘手套"
    assert payload["messages"][0]["role"] == "assistant"
    assert captured["provider"] == "openai"
    assert captured["model"] == "MiniMax-M2.5"
    assert captured["api_key"] == "sk-training-1234567890"
    assert captured["base_url"] == "https://api.minimaxi.com/v1"
    assert "髋关节电机盖拆装" in captured["prompt"]

    session_detail_resp = client.get(f"/api/v1/training/sessions/{payload['project']['session_id']}/detail")
    assert session_detail_resp.status_code == 200
    detail_payload = session_detail_resp.json()
    assert detail_payload["session"]["project_snapshot"]["title"] == "ATOM01 关节盖拆装训练"
    assert detail_payload["steps"][0]["step_id"] == "step_prepare"


def test_training_workbench_draft_falls_back_when_llm_returns_plain_text(
    training_workbench_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _session_factory = training_workbench_env
    _user_id, token = _register_and_login(client, email=f"draft_fallback_{uuid4().hex[:8]}@example.com")

    save_pref_resp = client.put(
        "/api/v1/agent/preference/llm",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "provider": "openai",
            "model": "MiniMax-M2.5",
            "base_url": "https://api.minimaxi.com/v1",
            "api_key": "sk-training-plain-text",
        },
    )
    assert save_pref_resp.status_code == 200

    async def _fake_chat(*, messages, provider, model, temperature, max_tokens, api_key=None, base_url=None, tools=None):  # noqa: ANN001
        return SimpleNamespace(
            content="建议先完成断电挂牌，再依次检查绝缘手套、扭矩扳手和现场留证。",
            provider=provider,
            model=model,
            tokens_in=88,
            tokens_out=64,
            raw_response={"ok": True},
            prompt_hash="prompt",
            response_hash="response",
        )

    monkeypatch.setattr("app.services.training.workbench_draft_generator.llm_router.chat", _fake_chat)

    draft_resp = client.post(
        "/api/v1/training/workbench/draft",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "robot_model": "ATOM01",
            "task_summary": "关节电机盖拆装",
            "focus_prompt": "强调工具确认与证据留存",
        },
    )

    assert draft_resp.status_code == 200
    payload = draft_resp.json()
    assert payload["project"]["title"] == "ATOM01 关节电机盖拆装"
    assert len(payload["steps"]) == 3
    assert payload["steps"][0]["model_targets"]
    assert payload["messages"][0]["content"].startswith("建议先完成断电挂牌")
