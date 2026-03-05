"""
UF-08: SubmissionService tests.
"""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.training import SessionStepRecord, TrainingSession
from app.models.user import User
from app.services.training.submission_service import SubmissionService


def _step(
    *,
    session_id: str,
    step_id: str,
    step_index: int,
    status: str,
    attempt_count: int = 1,
    duration_sec: int = 60,
) -> SessionStepRecord:
    now = datetime.utcnow()
    return SessionStepRecord(
        record_id=str(uuid4()),
        session_id=session_id,
        step_id=step_id,
        step_index=step_index,
        status=status,
        attempt_count=attempt_count,
        tools_confirmed=[{"tool_id": "tool-1", "status": "confirmed"}],
        evidence={"note": "ok"},
        verdict_result={"rule_result": status},
        duration_sec=duration_sec,
        started_at=now,
        completed_at=now if status in {"pass", "fail", "skip"} else None,
    )


@pytest.mark.asyncio
async def test_submission_service_manual_submission_payload_complete(test_db, test_user, test_session):
    service = SubmissionService(test_db)

    test_db.add_all(
        [
            _step(session_id=test_session.session_id, step_id="step_001", step_index=0, status="pass"),
            _step(session_id=test_session.session_id, step_id="step_002", step_index=1, status="fail", attempt_count=2),
        ]
    )
    await test_db.commit()

    submission = await service.submit_manual(
        session_id=test_session.session_id,
        user_id=test_user.id,
        confirm_incomplete=True,
    )

    assert submission is not None
    assert submission.submit_type == "manual"
    payload = submission.payload
    required = {
        "session_id",
        "project_id",
        "user_id",
        "submit_type",
        "submitted_at",
        "total_steps",
        "completed_steps",
        "failed_steps",
        "total_duration",
        "total_attempts",
        "score",
        "project_snapshot",
        "steps_summary",
        "conversation_summary",
        "interaction_log",
    }
    assert required.issubset(set(payload.keys()))

    session = await test_db.scalar(
        select(TrainingSession).where(TrainingSession.session_id == test_session.session_id)
    )
    assert session is not None
    assert session.status == "submitted"
    assert session.submit_type == "manual"


@pytest.mark.asyncio
async def test_submission_service_timeout_submission(test_db, test_session):
    service = SubmissionService(test_db)

    test_session.status = "active"
    test_session.total_duration = 3700
    test_session.project_snapshot = {"verdict_config": {"time_limit": 1}, "estimated_time": 60}
    test_db.add(_step(session_id=test_session.session_id, step_id="step_001", step_index=0, status="pass"))
    await test_db.commit()

    submission = await service.submit_timeout(test_session.session_id)
    assert submission is not None
    assert submission.submit_type == "timeout"
    assert submission.payload["submit_type"] == "timeout"


@pytest.mark.asyncio
async def test_submission_service_teacher_forced_submission(test_db, test_session):
    service = SubmissionService(test_db)

    teacher = User(
        email=f"teacher_{uuid4().hex[:8]}@example.com",
        password_hash="pbkdf2_sha256$fixture",
        full_name="Fixture Teacher",
        role="teacher",
        hint_level=3,
    )
    test_db.add(teacher)
    test_db.add(_step(session_id=test_session.session_id, step_id="step_001", step_index=0, status="pass"))
    await test_db.commit()
    await test_db.refresh(teacher)

    submission = await service.submit_by_teacher(
        session_id=test_session.session_id,
        teacher_id=teacher.id,
    )
    assert submission is not None
    assert submission.submit_type == "teacher"
    assert submission.payload["submitted_by"] == teacher.id


@pytest.mark.asyncio
async def test_submission_service_abandon(test_db, test_session):
    service = SubmissionService(test_db)

    ok = await service.abandon(test_session.session_id)
    assert ok is True

    session = await test_db.scalar(
        select(TrainingSession).where(TrainingSession.session_id == test_session.session_id)
    )
    assert session is not None
    assert session.status == "abandoned"
    assert session.submit_type == "abandoned"
