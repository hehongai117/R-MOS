"""
UF-06: SessionService tests.
"""
from __future__ import annotations

import pytest

from app.services.training.session_service import SessionService


@pytest.mark.asyncio
async def test_session_service_full_state_flow(test_db, test_user):
    service = SessionService(test_db)

    session_id = await service.create_session(
        user_id=test_user.id,
        project_id="project-001",
        project_snapshot={"estimated_time": 60},
    )

    record_id = await service.update_step(
        session_id=session_id,
        step_id="step_001",
        step_index=0,
        status="pass",
        attempt_count=1,
        tools_confirmed=[{"tool_id": "tool-1", "status": "confirmed"}],
        evidence={"photo": "ok"},
        verdict_result={"rule_result": "pass"},
        duration_sec=42,
    )
    assert record_id

    snapshot = await service.get_session_with_steps(session_id)
    assert snapshot is not None
    assert snapshot["session"].current_step == 1
    assert len(snapshot["steps"]) == 1
    assert snapshot["steps"][0].status == "pass"

    paused = await service.pause(session_id)
    assert paused is not None
    assert paused.status == "paused"

    resumed = await service.resume(session_id)
    assert resumed is not None
    assert resumed.status == "active"

    submission = await service.submit(session_id, submit_type="manual", score=88.5)
    assert submission is not None
    assert submission["status"] == "submitted"
    assert submission["submit_type"] == "manual"
    assert submission["score"] == 88.5


@pytest.mark.asyncio
async def test_session_service_resume_recovery(test_db, test_user):
    service = SessionService(test_db)
    session_id = await service.create_session(
        user_id=test_user.id,
        project_id="project-recovery",
        project_snapshot={"estimated_time": 30},
    )

    await service.pause(session_id)

    active = await service.get_user_active_session(test_user.id)
    assert active is not None
    assert active.session_id == session_id
    assert active.status == "paused"

    sessions = await service.get_user_sessions(test_user.id, limit=5)
    assert sessions
    assert sessions[0].session_id == session_id
