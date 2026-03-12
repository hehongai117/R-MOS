from __future__ import annotations

import asyncio
import io
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
from main import app


@pytest.fixture(scope="module")
def training_execution_env() -> tuple[TestClient, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async def init_models() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

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
            "full_name": "Training Execution User",
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


def _seed_llm_preference(client: TestClient, token: str) -> None:
    response = client.put(
        "/api/v1/agent/preference/llm",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "provider": "openai",
            "model": "MiniMax-M2.5",
            "base_url": "https://api.minimaxi.com/v1",
            "api_key": "sk-training-execution",
        },
    )
    assert response.status_code == 200


def _create_workbench_session(client: TestClient, token: str, monkeypatch: pytest.MonkeyPatch) -> dict:
    async def _fake_chat(*, messages, provider, model, temperature, max_tokens, api_key=None, base_url=None, tools=None):  # noqa: ANN001
        return SimpleNamespace(
            content=json.dumps(
                {
                    "project": {
                        "title": "ATOM01 执行态训练",
                        "summary": "用于训练工作台执行闭环测试。",
                    },
                    "steps": [
                        {
                            "id": "step_prepare",
                            "title": "步骤 1: 准备工位",
                            "instruction": "确认断电、穿戴 PPE、准备工具。",
                            "evidence_hint": "上传工位照片。",
                            "model_targets": ["torso_link"],
                            "tools": [
                                {"name": "绝缘手套", "spec": "A级绝缘", "is_critical": True},
                                {"name": "扭矩扳手", "spec": "5-25Nm", "is_critical": True},
                            ],
                        },
                        {
                            "id": "step_remove",
                            "title": "步骤 2: 拆卸电机盖",
                            "instruction": "按顺序拆下盖板固定件。",
                            "evidence_hint": "上传拆卸照片。",
                            "model_targets": ["left_knee_link"],
                            "tools": [
                                {"name": "六角扳手", "spec": "4mm", "is_critical": True},
                                {"name": "零件托盘", "spec": "分区托盘", "is_critical": False},
                            ],
                        },
                    ],
                    "messages": [
                        {"role": "assistant", "content": "先确认安全，再逐项执行。"},
                        {"role": "teacher", "content": "证据必须覆盖工位与关键动作。"},
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
            "task_summary": "关节电机盖拆装",
            "focus_prompt": "强调证据上传、正式提交与 3D 高亮",
        },
    )
    assert draft_resp.status_code == 200
    return draft_resp.json()


def test_upload_evidence_and_submit_step(
    training_execution_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _session_factory = training_execution_env
    _user_id, token = _register_and_login(client, email=f"execution_{uuid4().hex[:8]}@example.com")
    _seed_llm_preference(client, token)
    draft_payload = _create_workbench_session(client, token, monkeypatch)

    upload_resp = client.post(
        "/api/v1/training/workbench/evidence",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("station.jpg", io.BytesIO(b"fake-image-content"), "image/jpeg")},
        data={
            "session_id": draft_payload["project"]["session_id"],
            "step_id": "step_prepare",
            "note": "工位检查已完成",
        },
    )
    assert upload_resp.status_code == 201
    upload_payload = upload_resp.json()
    assert upload_payload["evidence_bundle_id"]
    assert upload_payload["filename"] == "station.jpg"

    async def _fake_verdict_chat(*, messages, provider, model, temperature, max_tokens, api_key=None, base_url=None, tools=None):  # noqa: ANN001
        return SimpleNamespace(
            content="关键工具已确认，证据齐全，可判定通过。",
            provider=provider,
            model=model,
            tokens_in=80,
            tokens_out=60,
            raw_response={"ok": True},
            prompt_hash="prompt",
            response_hash="response",
        )

    monkeypatch.setattr("app.services.training.workbench_execution_service.llm_router.chat", _fake_verdict_chat)

    submit_resp = client.post(
        f"/api/v1/training/workbench/sessions/{draft_payload['project']['session_id']}/steps/step_prepare/submit",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "step_index": 0,
            "note": "工具、工位和断电状态均已确认",
            "evidence_bundle_id": upload_payload["evidence_bundle_id"],
            "tools_confirmed": [
                {"tool_id": draft_payload["steps"][0]["tools"][0]["id"], "status": "CONFIRMED"},
                {"tool_id": draft_payload["steps"][0]["tools"][1]["id"], "status": "CONFIRMED"},
            ],
        },
    )
    assert submit_resp.status_code == 200
    submit_payload = submit_resp.json()
    assert submit_payload["status"] == "pass"
    assert submit_payload["verdict"]["result"] == "PASS"
    assert "通过" in submit_payload["verdict"]["details"]

    step_records_resp = client.get(f"/api/v1/training/sessions/{draft_payload['project']['session_id']}/steps")
    assert step_records_resp.status_code == 200
    step_records = step_records_resp.json()
    step_prepare = next(item for item in step_records if item["step_id"] == "step_prepare")
    assert step_prepare["status"] == "pass"


def test_training_workbench_ai_follow_up(
    training_execution_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _session_factory = training_execution_env
    _user_id, token = _register_and_login(client, email=f"execution_ask_{uuid4().hex[:8]}@example.com")
    _seed_llm_preference(client, token)
    draft_payload = _create_workbench_session(client, token, monkeypatch)

    async def _fake_ask_chat(*, messages, provider, model, temperature, max_tokens, api_key=None, base_url=None, tools=None):  # noqa: ANN001
        return SimpleNamespace(
            content="建议先再次核对扭矩扳手量程，再继续拆卸。",
            provider=provider,
            model=model,
            tokens_in=75,
            tokens_out=55,
            raw_response={"ok": True},
            prompt_hash="prompt",
            response_hash="response",
        )

    monkeypatch.setattr("app.services.training.workbench_execution_service.llm_router.chat", _fake_ask_chat)

    ask_resp = client.post(
        "/api/v1/training/workbench/ask",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "session_id": draft_payload["project"]["session_id"],
            "step_id": "step_prepare",
            "question": "如果扭矩扳手读数不稳定该怎么办？",
            "messages": [
                {"role": "assistant", "content": "先确认安全，再逐项执行。"},
                {"role": "user", "content": "如果扭矩扳手读数不稳定该怎么办？"},
            ],
        },
    )
    assert ask_resp.status_code == 200
    ask_payload = ask_resp.json()
    assert ask_payload["role"] == "assistant"
    assert "扭矩扳手" in ask_payload["content"]
