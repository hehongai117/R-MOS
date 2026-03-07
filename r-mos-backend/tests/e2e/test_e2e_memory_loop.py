from __future__ import annotations

from types import SimpleNamespace
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.e2e.helpers import parse_sse_events, register_and_login, set_user_hint_level


@pytest.mark.e2e
def test_e2e_memory_loop(
    e2e_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = e2e_env

    user_id, _email, _login_payload = register_and_login(client, email_prefix="e2e_memory")

    import asyncio

    asyncio.run(set_user_hint_level(session_factory, user_id=user_id, hint_level=3))

    create_session_resp = client.post(
        "/api/v1/training/sessions",
        json={
            "user_id": user_id,
            "project_id": "proj-memory-1",
            "project_snapshot": {
                "title": "Memory Loop Session 1",
                "estimated_time": 45,
                "steps": ["step-A", "step-B"],
            },
        },
    )
    assert create_session_resp.status_code == 200
    session_id = create_session_resp.json()["session_id"]

    step_a_resp = client.post(
        f"/api/v1/training/sessions/{session_id}/steps",
        json={
            "step_id": "step-A",
            "step_index": 0,
            "status": "pass",
            "attempt_count": 3,
            "duration_sec": 80,
            "tools_confirmed": [{"tool_id": "gauge", "status": "confirmed"}],
        },
    )
    assert step_a_resp.status_code == 200

    step_b_resp = client.post(
        f"/api/v1/training/sessions/{session_id}/steps",
        json={
            "step_id": "step-B",
            "step_index": 1,
            "status": "fail",
            "attempt_count": 1,
            "duration_sec": 90,
            "tools_confirmed": [{"tool_id": "caliper", "status": "missing"}],
        },
    )
    assert step_b_resp.status_code == 200

    submit_resp = client.post(
        f"/api/v1/training/sessions/{session_id}/submit",
        json={"user_id": user_id, "confirm_incomplete": True},
    )
    assert submit_resp.status_code == 200

    weak_steps_resp = client.get(f"/api/v1/students/{user_id}/weak-steps")
    assert weak_steps_resp.status_code == 200
    weak_step_map = {item["step_id"]: item for item in weak_steps_resp.json()}

    assert weak_step_map["step-A"]["fail_count"] == 2
    assert weak_step_map["step-B"]["fail_count"] == 1
    assert weak_step_map["step-B"]["is_resolved"] is False

    captured_prompt: dict[str, str] = {}

    async def _fake_retrieve_knowledge(self, intent):  # noqa: ANN001
        return [{"title": f"doc-{i}", "content": "knowledge"} for i in range(6)]

    async def _fake_chat(**kwargs):  # noqa: ANN001
        captured_prompt["content"] = kwargs["messages"][0]["content"]
        return SimpleNamespace(
            content=json.dumps(
                {
                    "project_id": "proj-memory-2",
                    "title": "Memory Loop Session 2",
                    "description": "强化薄弱步骤",
                    "steps": [
                        {
                            "step_id": "step-B",
                            "title": "重点强化步骤",
                            "description": "重复薄弱环节",
                            "model_highlight": ["joint"],
                            "required_tools": ["caliper"],
                            "ref_ids": ["ref-memory"],
                            "required_level": 1,
                        }
                    ],
                    "tools_checklist": [
                        {
                            "tool_id": "tool-1",
                            "name": "caliper",
                            "spec": "standard",
                            "is_critical": True,
                        }
                    ],
                    "verdict_config": {"mode": "guided", "time_limit": 60, "max_attempts": 3},
                    "robot": {"asset_id": "rb-memory", "brand": "ABB", "model": "IRB120"},
                    "estimated_time": 60,
                    "difficulty_cap": 3,
                }
            )
        )

    monkeypatch.setattr(
        "app.services.training.project_generator.ProjectGenerator._retrieve_knowledge",
        _fake_retrieve_knowledge,
    )
    monkeypatch.setattr("app.services.training.project_generator.llm_router.chat", _fake_chat)

    generate_resp = client.post(
        "/api/v1/training/projects/generate",
        json={
            "user_id": user_id,
            "robot_id": "ABB-IRB120",
            "difficulty": "medium",
            "focus_areas": ["weakness"],
        },
    )
    assert generate_resp.status_code == 200
    events = parse_sse_events(generate_resp.text)

    completed = [event for event in events if event.get("status") == "completed"]
    assert completed
    assert completed[-1]["project_id"] == "proj-memory-2"

    prompt = captured_prompt.get("content", "")
    assert "step-B" in prompt
    assert "建议提示等级: L4" in prompt
