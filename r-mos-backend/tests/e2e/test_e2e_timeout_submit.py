from __future__ import annotations

import asyncio
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.training import TrainingSession
from app.models.training_submission import TrainingSubmission
from app.services.training.submission_service import SubmissionService
from tests.e2e.helpers import register_and_login


async def _set_total_duration(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    session_id: str,
    total_duration: int,
) -> None:
    async with session_factory() as session:
        result = await session.execute(
            select(TrainingSession).where(TrainingSession.session_id == session_id)
        )
        training_session = result.scalar_one()
        training_session.total_duration = total_duration
        training_session.started_at = datetime.utcnow()
        training_session.status = "active"
        await session.commit()


async def _trigger_timeout_submit(
    session_factory: async_sessionmaker[AsyncSession],
) -> int:
    async with session_factory() as session:
        service = SubmissionService(session)
        return await service.check_and_submit_timeouts()


async def _get_timeout_submission(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    session_id: str,
) -> tuple[TrainingSession | None, TrainingSubmission | None]:
    async with session_factory() as session:
        session_result = await session.execute(
            select(TrainingSession).where(TrainingSession.session_id == session_id)
        )
        training_session = session_result.scalar_one_or_none()

        submission_result = await session.execute(
            select(TrainingSubmission)
            .where(TrainingSubmission.session_id == session_id)
            .order_by(TrainingSubmission.submitted_at.desc())
        )
        submission = submission_result.scalars().first()
        return training_session, submission


def test_e2e_timeout_submit(
    e2e_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = e2e_env

    user_id, _email, _login_payload = register_and_login(client, email_prefix="e2e_timeout")

    create_session_resp = client.post(
        "/api/v1/training/sessions",
        json={
            "user_id": user_id,
            "project_id": "proj-timeout-e2e",
            "project_snapshot": {
                "estimated_time": 1,
                "steps": ["step-timeout"],
                "verdict_config": {"time_limit": 0.01},
            },
        },
    )
    assert create_session_resp.status_code == 200
    session_id = create_session_resp.json()["session_id"]

    step_resp = client.post(
        f"/api/v1/training/sessions/{session_id}/steps",
        json={
            "step_id": "step-timeout",
            "step_index": 0,
            "status": "pass",
            "attempt_count": 1,
            "duration_sec": 120,
        },
    )
    assert step_resp.status_code == 200

    asyncio.run(_set_total_duration(session_factory, session_id=session_id, total_duration=120))

    submitted_count = asyncio.run(_trigger_timeout_submit(session_factory))
    assert submitted_count >= 1

    training_session, submission = asyncio.run(
        _get_timeout_submission(session_factory, session_id=session_id)
    )
    assert training_session is not None
    assert training_session.submit_type == "timeout"
    assert submission is not None
    assert submission.submit_type == "timeout"
