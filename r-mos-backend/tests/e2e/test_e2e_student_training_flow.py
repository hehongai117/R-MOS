from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.e2e.helpers import parse_sse_events, register_and_login


@pytest.mark.e2e
def test_e2e_student_training_flow(
    e2e_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = e2e_env

    async def _fake_generate(self, intent, user_id):  # noqa: ANN001
        yield {"status": "retrieving_knowledge", "message": "检索中"}
        yield {"status": "analyzing_history", "message": "分析中"}
        yield {
            "status": "completed",
            "project": SimpleNamespace(
                project_id=f"proj-{uuid4().hex[:8]}",
                title="E2E Student Flow",
                description="End-to-end training project",
                estimated_time=45,
                difficulty_cap=3,
            ),
        }

    monkeypatch.setattr(
        "app.services.training.project_generator.ProjectGenerator.generate",
        _fake_generate,
    )

    user_id, _email, login_payload = register_and_login(
        client, email_prefix="e2e_student_flow", role="student"
    )
    assert login_payload["role"] == "student"

    generate_resp = client.post(
        "/api/v1/training/projects/generate",
        json={
            "user_id": user_id,
            "robot_id": "ABB-IRB120",
            "difficulty": "medium",
            "focus_areas": ["safety", "tools"],
        },
    )
    assert generate_resp.status_code == 200

    events = parse_sse_events(generate_resp.text)
    completed = [event for event in events if event.get("status") == "completed"]
    assert completed

    project_payload = completed[-1]["project"]
    assert {"project_id", "title", "description", "estimated_time", "difficulty_cap"}.issubset(
        project_payload.keys()
    )
    project_id = completed[-1]["project_id"]

    create_session_resp = client.post(
        "/api/v1/training/sessions",
        json={
            "user_id": user_id,
            "project_id": project_id,
            "project_snapshot": {
                "title": "E2E Student Flow",
                "estimated_time": 45,
                "steps": ["step-A", "step-B", "step-C"],
                "verdict_config": {"time_limit": 60},
            },
        },
    )
    assert create_session_resp.status_code == 200
    session_id = create_session_resp.json()["session_id"]

    step_updates = [
        {
            "step_id": "step-A",
            "step_index": 0,
            "status": "pass",
            "attempt_count": 1,
            "duration_sec": 20,
            "tools_confirmed": [{"tool_id": "wrench", "status": "confirmed"}],
            "verdict_result": {"decision": "pass", "source": "adjudicator"},
        },
        {
            "step_id": "step-B",
            "step_index": 1,
            "status": "fail",
            "attempt_count": 1,
            "duration_sec": 45,
            "tools_confirmed": [{"tool_id": "multimeter", "status": "missing"}],
            "verdict_result": {"decision": "fail", "source": "adjudicator"},
        },
        {
            "step_id": "step-C",
            "step_index": 2,
            "status": "pass",
            "attempt_count": 1,
            "duration_sec": 30,
            "tools_confirmed": [{"tool_id": "caliper", "status": "confirmed"}],
            "verdict_result": {"decision": "pass", "source": "adjudicator"},
        },
    ]

    for payload in step_updates:
        update_resp = client.post(f"/api/v1/training/sessions/{session_id}/steps", json=payload)
        assert update_resp.status_code == 200

    submit_resp = client.post(
        f"/api/v1/training/sessions/{session_id}/submit",
        json={"user_id": user_id, "confirm_incomplete": True},
    )
    assert submit_resp.status_code == 200
    assert submit_resp.json()["submit_type"] == "manual"

    feedback_resp = client.get(f"/api/v1/training/feedback/{session_id}")
    assert feedback_resp.status_code == 200
    feedback_payload = feedback_resp.json()
    assert feedback_payload["session_id"] == session_id

    score_breakdown = feedback_payload["score_breakdown"]
    expected_dimensions = {
        "total_score",
        "completion_score",
        "completion_rate",
        "time_score",
        "tools_score",
        "attempt_score",
        "completed_steps",
        "failed_steps",
    }
    assert expected_dimensions.issubset(score_breakdown.keys())

    profile_resp = client.get(f"/api/v1/students/{user_id}/profile")
    assert profile_resp.status_code == 200
    assert profile_resp.json()["total_sessions"] >= 1

    weak_steps_resp = client.get(f"/api/v1/students/{user_id}/weak-steps")
    assert weak_steps_resp.status_code == 200
    weak_steps = weak_steps_resp.json()
    weak_step_map = {item["step_id"]: item for item in weak_steps}
    assert "step-B" in weak_step_map
    assert weak_step_map["step-B"]["fail_count"] >= 1
    assert weak_step_map["step-B"]["is_resolved"] is False
