"""
T-03-b training API flow tests.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models as app_models  # noqa: F401  # ensure metadata is fully loaded
from app.core.database import get_db
from app.models.base import Base
from app.models.school import School
from app.models.training import SessionStepRecord, TrainingSession
from app.models.training_submission import TrainingSubmission
from app.services.training.submission_service import SubmissionService
from main import app

# onboarding 注册需要的白名单学校（测试统一使用）
TEST_SCHOOL_NAME = "测试学校"


@pytest.fixture(scope="module")
def training_flow_env() -> tuple[TestClient, async_sessionmaker[AsyncSession]]:
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
    app.state.test_sessionmaker = session_factory

    with TestClient(app) as client:
        yield client, session_factory

    app.dependency_overrides.clear()
    app.state.test_sessionmaker = None
    asyncio.run(engine.dispose())


def _register_and_login(client: TestClient, *, email: str) -> tuple[int, str]:
    register_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPass123",
            "full_name": "Training API User",
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


def _parse_sse_events(raw_text: str) -> list[dict]:
    events: list[dict] = []
    for line in raw_text.splitlines():
        if not line.startswith("data: "):
            continue
        payload = line.removeprefix("data: ").strip()
        if not payload:
            continue
        events.append(json.loads(payload))
    return events


async def _get_step_record(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    session_id: str,
    step_id: str,
) -> SessionStepRecord | None:
    async with session_factory() as session:
        result = await session.execute(
            select(SessionStepRecord).where(
                SessionStepRecord.session_id == session_id,
                SessionStepRecord.step_id == step_id,
            )
        )
        return result.scalar_one_or_none()


async def _set_session_total_duration(
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


async def _get_session_and_submission(
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


def test_training_api_full_flow(
    training_flow_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = training_flow_env

    async def _fake_generate(self, intent, user_id):  # noqa: ANN001
        yield {
            "status": "completed",
            "project": SimpleNamespace(
                project_id=f"proj-{uuid4().hex[:8]}",
                title="Mock Training Project",
                description="Generated by test",
                estimated_time=45,
                difficulty_cap="medium",
            ),
        }

    monkeypatch.setattr("app.services.training.project_generator.ProjectGenerator.generate", _fake_generate)

    user_id, _token = _register_and_login(
        client,
        email=f"training_flow_{uuid4().hex[:8]}@example.com",
    )

    generate_resp = client.post(
        "/api/v1/training/projects/generate",
        json={
            "user_id": user_id,
            "robot_id": "ABB-IRB120",
            "difficulty": "medium",
            "focus_areas": ["safety"],
        },
    )
    assert generate_resp.status_code == 200

    events = _parse_sse_events(generate_resp.text)
    completed = [event for event in events if event.get("status") == "completed"]
    assert completed, f"missing completed event: {generate_resp.text[:300]}"
    project_id = completed[-1]["project_id"]
    assert project_id

    create_session_resp = client.post(
        "/api/v1/training/sessions",
        json={
            "user_id": user_id,
            "project_id": project_id,
            "project_snapshot": {"estimated_time": 45, "verdict_config": {"time_limit": 60}},
        },
    )
    assert create_session_resp.status_code == 200
    session_id = create_session_resp.json()["session_id"]

    update_step_resp = client.post(
        f"/api/v1/training/sessions/{session_id}/steps",
        json={
            "step_id": "step-1",
            "step_index": 0,
            "status": "pass",
            "attempt_count": 1,
            "tools_confirmed": [{"tool_id": "wrench", "status": "confirmed"}],
            "duration_sec": 30,
        },
    )
    assert update_step_resp.status_code == 200

    submit_resp = client.post(
        f"/api/v1/training/sessions/{session_id}/submit",
        json={"user_id": user_id, "confirm_incomplete": True},
    )
    assert submit_resp.status_code == 200
    submit_payload = submit_resp.json()
    assert submit_payload["submit_type"] == "manual"

    feedback_resp = client.get(f"/api/v1/training/feedback/{session_id}")
    assert feedback_resp.status_code == 200
    feedback_payload = feedback_resp.json()
    assert feedback_payload["session_id"] == session_id
    assert "overall_score" in feedback_payload


def test_tools_confirmed_is_idempotent_on_repeat_update(
    training_flow_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = training_flow_env
    user_id, _token = _register_and_login(
        client,
        email=f"tools_idempotent_{uuid4().hex[:8]}@example.com",
    )

    create_session_resp = client.post(
        "/api/v1/training/sessions",
        json={
            "user_id": user_id,
            "project_id": f"proj-{uuid4().hex[:8]}",
            "project_snapshot": {"estimated_time": 30},
        },
    )
    assert create_session_resp.status_code == 200
    session_id = create_session_resp.json()["session_id"]

    payload = {
        "step_id": "step-tools",
        "step_index": 0,
        "status": "in_progress",
        "attempt_count": 1,
        "tools_confirmed": [{"tool_id": "multimeter", "status": "confirmed"}],
    }
    first = client.post(f"/api/v1/training/sessions/{session_id}/steps", json=payload)
    second = client.post(f"/api/v1/training/sessions/{session_id}/steps", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200

    record = asyncio.run(
        _get_step_record(session_factory, session_id=session_id, step_id="step-tools")
    )
    assert record is not None
    assert isinstance(record.tools_confirmed, list)
    assert len(record.tools_confirmed) == 1
    assert record.tools_confirmed[0]["tool_id"] == "multimeter"


def test_timeout_submission_sets_submit_type_timeout(
    training_flow_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = training_flow_env
    user_id, _token = _register_and_login(
        client,
        email=f"timeout_submit_{uuid4().hex[:8]}@example.com",
    )

    create_session_resp = client.post(
        "/api/v1/training/sessions",
        json={
            "user_id": user_id,
            "project_id": f"proj-{uuid4().hex[:8]}",
            "project_snapshot": {"estimated_time": 1, "verdict_config": {"time_limit": 0.01}},
        },
    )
    assert create_session_resp.status_code == 200
    session_id = create_session_resp.json()["session_id"]

    client.post(
        f"/api/v1/training/sessions/{session_id}/steps",
        json={
            "step_id": "step-timeout",
            "step_index": 0,
            "status": "pass",
            "attempt_count": 1,
            "duration_sec": 120,
        },
    )

    asyncio.run(_set_session_total_duration(session_factory, session_id=session_id, total_duration=120))

    async def _trigger_timeout_submit() -> int:
        async with session_factory() as session:
            service = SubmissionService(session)
            return await service.check_and_submit_timeouts()

    submitted_count = asyncio.run(_trigger_timeout_submit())
    assert submitted_count >= 1

    training_session, submission = asyncio.run(
        _get_session_and_submission(session_factory, session_id=session_id)
    )
    assert training_session is not None
    assert training_session.submit_type == "timeout"
    assert submission is not None
    assert submission.submit_type == "timeout"
