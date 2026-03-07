"""
Phase2 training API contract tests.
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime
from decimal import Decimal
from types import ModuleType, SimpleNamespace


if "anthropic" not in sys.modules:
    anthropic_stub = ModuleType("anthropic")

    class _DummyAsyncAnthropic:
        def __init__(self, *args, **kwargs):
            pass

    anthropic_stub.AsyncAnthropic = _DummyAsyncAnthropic
    sys.modules["anthropic"] = anthropic_stub

if "psutil" not in sys.modules:
    psutil_stub = ModuleType("psutil")

    class _Mem:
        percent = 10.0

    class _Disk:
        percent = 20.0

    class _Net:
        bytes_sent = 0
        bytes_recv = 0

    psutil_stub.cpu_percent = lambda interval=0.1: 5.0
    psutil_stub.virtual_memory = lambda: _Mem()
    psutil_stub.disk_usage = lambda path: _Disk()
    psutil_stub.net_io_counters = lambda: _Net()
    sys.modules["psutil"] = psutil_stub

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.models.base import Base
from app.models.skill_profile import StudentSkillProfile, StudentWeakStep
from app.models.training import SessionStepRecord, TrainingSession
from app.models.training_submission import TrainingSubmission
from app.models.user import User
from main import app
import app.models as app_models  # noqa: F401  # Ensure all models are registered
import app.api.v1.endpoints.training as training_endpoints


def _build_client() -> tuple[TestClient, async_sessionmaker]:
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
    app.state.test_sessionmaker = session_factory
    return TestClient(app), session_factory


def _seed_phase2_data(session_factory: async_sessionmaker) -> dict:
    async def _seed() -> dict:
        async with session_factory() as session:
            user = User(
                email="phase2_student@example.com",
                password_hash="pbkdf2_sha256$dummy",
                full_name="Phase2 Student",
                role="student",
            )
            session.add(user)
            await session.flush()

            training_session = TrainingSession(
                session_id="sess-phase2-001",
                project_id="project-phase2-001",
                user_id=user.id,
                status="active",
                current_step=1,
                project_snapshot={"estimated_time": 60},
                total_duration=900,
                started_at=datetime.utcnow(),
            )
            session.add(training_session)

            step_record = SessionStepRecord(
                record_id="step-record-001",
                session_id=training_session.session_id,
                step_id="step-1",
                step_index=0,
                status="pass",
                attempt_count=1,
                tools_confirmed=[{"tool_id": "wrench", "status": "confirmed"}],
                duration_sec=120,
            )
            session.add(step_record)

            profile = StudentSkillProfile(
                user_id=user.id,
                overall_level=2,
                total_sessions=3,
                total_duration=3600,
                score_safety=Decimal("85.00"),
                score_procedure=Decimal("82.00"),
                score_precision=Decimal("80.00"),
                score_efficiency=Decimal("78.00"),
                score_tools=Decimal("88.00"),
            )
            session.add(profile)

            weak_step = StudentWeakStep(
                user_id=user.id,
                step_id="step-weak-1",
                sop_id="SOP-100",
                fail_count=4,
                is_resolved=False,
                fail_tags=["tool_error"],
            )
            session.add(weak_step)

            submission = TrainingSubmission(
                submission_id="sub-phase2-001",
                session_id=training_session.session_id,
                user_id=user.id,
                submit_type="manual",
                submitted_at=datetime.utcnow(),
                payload={
                    "session_id": training_session.session_id,
                    "steps_summary": [{"step_id": "step-1", "status": "pass", "attempt_count": 1}],
                    "total_duration": 900,
                    "project_snapshot": {"estimated_time": 60},
                },
                score=Decimal("88.50"),
                total_steps=1,
                completed_steps=1,
                failed_steps=0,
                total_duration=900,
                feedback={
                    "overall_score": 88.5,
                    "score_breakdown": {"total_score": 88.5},
                    "suggestions": ["继续巩固"],
                    "next_learning_plan": "进阶训练",
                },
                feedback_generated_at=datetime.utcnow(),
            )
            session.add(submission)

            await session.commit()
            return {
                "user_id": user.id,
                "session_id": training_session.session_id,
                "submission_id": submission.submission_id,
            }

    return asyncio.run(_seed())


def test_submit_session_uses_submission_service_manual(monkeypatch) -> None:
    client, session_factory = _build_client()
    try:
        data = _seed_phase2_data(session_factory)

        async def _fake_check_submit_ready(self, session_id: str):
            return SimpleNamespace(can_submit=True, message="ok", incomplete_steps=[])

        async def _fake_submit_manual(
            self,
            session_id: str,
            user_id: int,
            confirm_incomplete: bool = False,
        ):
            return SimpleNamespace(
                submission_id="sub-new-001",
                session_id=session_id,
                user_id=user_id,
                submit_type="manual",
                payload={"score": 91.2},
            )

        async def _legacy_submit_should_not_be_called(self, session_id: str, submit_type: str = "manual", score=None):
            raise AssertionError("SessionService.submit must not be used by submit endpoint")

        monkeypatch.setattr(training_endpoints.SubmissionService, "check_submit_ready", _fake_check_submit_ready)
        monkeypatch.setattr(training_endpoints.SubmissionService, "submit_manual", _fake_submit_manual)
        monkeypatch.setattr(training_endpoints.SessionService, "submit", _legacy_submit_should_not_be_called)

        response = client.post(
            f"/api/v1/training/sessions/{data['session_id']}/submit",
            json={"user_id": data["user_id"], "confirm_incomplete": True},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["session_id"] == data["session_id"]
        assert payload["submission_id"] == "sub-new-001"
        assert payload["submit_type"] == "manual"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_get_training_feedback_by_session_id() -> None:
    client, session_factory = _build_client()
    try:
        data = _seed_phase2_data(session_factory)
        response = client.get(f"/api/v1/training/feedback/{data['session_id']}")
        assert response.status_code == 200
        payload = response.json()
        assert payload["session_id"] == data["session_id"]
        assert payload["submission_id"] == data["submission_id"]
        assert "overall_score" in payload
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_get_student_skill_profile() -> None:
    client, session_factory = _build_client()
    try:
        data = _seed_phase2_data(session_factory)
        response = client.get(f"/api/v1/students/{data['user_id']}/profile")
        assert response.status_code == 200
        payload = response.json()
        assert payload["user_id"] == data["user_id"]
        assert payload["overall_level"] == 2
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_get_student_weak_steps() -> None:
    client, session_factory = _build_client()
    try:
        data = _seed_phase2_data(session_factory)
        response = client.get(f"/api/v1/students/{data['user_id']}/weak-steps")
        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, list)
        assert len(payload) == 1
        assert payload[0]["step_id"] == "step-weak-1"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None
