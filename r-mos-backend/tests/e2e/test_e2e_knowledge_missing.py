from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.e2e.helpers import parse_sse_events, register_and_login


@pytest.mark.e2e
def test_e2e_knowledge_missing(
    e2e_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = e2e_env

    async def _fake_retrieve_knowledge(self, intent):  # noqa: ANN001
        return [{"title": "insufficient", "content": "single doc"}]

    monkeypatch.setattr(
        "app.services.training.project_generator.ProjectGenerator._retrieve_knowledge",
        _fake_retrieve_knowledge,
    )

    user_id, _email, _login_payload = register_and_login(client, email_prefix="e2e_knowledge_missing")

    resp = client.post(
        "/api/v1/training/projects/generate",
        json={
            "user_id": user_id,
            "robot_id": "UNKNOWN-ROBOT",
            "difficulty": "medium",
            "focus_areas": ["maintenance"],
        },
    )
    assert resp.status_code == 200

    events = parse_sse_events(resp.text)
    assert events
    assert events[0]["status"] == "retrieving_knowledge"
    assert events[-1]["status"] == "error"
    assert events[-1]["error"] == "knowledge_missing"
    assert "project_id" not in events[-1]
