from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.e2e.helpers import register_and_login


def test_e2e_resume_training(
    e2e_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, _ = e2e_env

    user_id, email, _login_payload = register_and_login(client, email_prefix="e2e_resume")

    create_session_resp = client.post(
        "/api/v1/training/sessions",
        json={
            "user_id": user_id,
            "project_id": "proj-resume-e2e",
            "project_snapshot": {
                "title": "Resume Flow",
                "estimated_time": 30,
                "steps": ["step-1", "step-2", "step-3", "step-4"],
            },
        },
    )
    assert create_session_resp.status_code == 200
    session_id = create_session_resp.json()["session_id"]

    step1_resp = client.post(
        f"/api/v1/training/sessions/{session_id}/steps",
        json={
            "step_id": "step-1",
            "step_index": 0,
            "status": "pass",
            "attempt_count": 1,
            "tools_confirmed": [{"tool_id": "tool-a", "status": "confirmed"}],
        },
    )
    assert step1_resp.status_code == 200

    step2_resp = client.post(
        f"/api/v1/training/sessions/{session_id}/steps",
        json={
            "step_id": "step-2",
            "step_index": 1,
            "status": "pass",
            "attempt_count": 2,
            "tools_confirmed": [{"tool_id": "tool-b", "status": "confirmed"}],
        },
    )
    assert step2_resp.status_code == 200

    pause_resp = client.patch(f"/api/v1/training/sessions/{session_id}/pause")
    assert pause_resp.status_code == 200
    assert pause_resp.json()["status"] == "paused"

    relogin_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert relogin_resp.status_code == 200
    relogin_payload = relogin_resp.json()
    assert relogin_payload["unfinished_session"]["session_id"] == session_id

    resume_resp = client.patch(f"/api/v1/training/sessions/{session_id}/resume")
    assert resume_resp.status_code == 200
    assert resume_resp.json()["status"] == "active"
    assert resume_resp.json()["current_step"] == 2

    detail_resp = client.get(f"/api/v1/training/sessions/{session_id}/detail")
    assert detail_resp.status_code == 200
    steps = detail_resp.json()["steps"]
    step2 = next(item for item in steps if item["step_id"] == "step-2")
    assert step2["attempt_count"] == 2

    step3_resp = client.post(
        f"/api/v1/training/sessions/{session_id}/steps",
        json={
            "step_id": "step-3",
            "step_index": 2,
            "status": "in_progress",
            "attempt_count": 1,
            "tools_confirmed": [{"tool_id": "tool-c", "status": "confirmed"}],
        },
    )
    assert step3_resp.status_code == 200

    session_resp = client.get(f"/api/v1/training/sessions/{session_id}")
    assert session_resp.status_code == 200
    assert session_resp.json()["current_step"] == 3
