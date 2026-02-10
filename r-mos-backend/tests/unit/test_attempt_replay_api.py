"""Gate-3 I-002：attempt replay 接口最小闭环测试。"""
from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models as app_models  # noqa: F401  # 确保模型注册
from app.core.database import get_db
from app.models.audit_event import AuditEvent
from app.models.base import Base
from app.models.timeline import AlignmentMap, MultimodalTimeline, TimelineSegment
from app.services.teaching_service import TeachingService
from main import app


@pytest.fixture
def client() -> TestClient:
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

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    app.state.test_sessionmaker = None
    asyncio.run(engine.dispose())


async def _seed_attempt(
    session_factory: async_sessionmaker,
    *,
    teacher_id: int,
    student_id: int,
) -> int:
    async with session_factory() as session:
        teaching_service = TeachingService(session)
        teaching_class = await teaching_service.create_class(name="I-002 班级", teacher_id=teacher_id)
        assignment = await teaching_service.create_assignment(
            class_id=teaching_class.id,
            title="I-002 作业",
        )
        await teaching_service.enroll_student(class_id=teaching_class.id, student_id=student_id)
        attempt = await teaching_service.create_attempt(
            assignment_id=assignment.id,
            student_id=student_id,
            task_id=None,
        )
        return attempt.id


async def _seed_timeline_for_attempt(
    session_factory: async_sessionmaker,
    *,
    attempt_id: int,
) -> tuple[int, int, str]:
    async with session_factory() as session:
        timeline = MultimodalTimeline(
            scope_type="attempt",
            scope_id=str(attempt_id),
            trace_id=f"replay-trace-{attempt_id}",
            created_by_user_id="7001",
        )
        session.add(timeline)
        await session.flush()

        ref_id = f"ref-{uuid4().hex[:8]}"
        segment = TimelineSegment(
            timeline_id=timeline.id,
            segment_type="event",
            ref_id=ref_id,
            start_ts_ms=1200,
            end_ts_ms=1800,
            payload={"step_id": 2, "event_id": 21, "failure_type": "E_ERROR_OCCURRED", "rule_hit": "R-DIAG-001"},
        )
        session.add(segment)
        await session.flush()

        alignment = AlignmentMap(
            timeline_id=timeline.id,
            anchor_key="failure_point",
            segment_id=segment.id,
            ref_id=ref_id,
            score=0.92,
        )
        session.add(alignment)
        await session.commit()
        return timeline.id, segment.id, ref_id


async def _latest_audit(
    session_factory: async_sessionmaker,
    *,
    action: str,
    decision: str,
    resource_id: str,
) -> AuditEvent | None:
    async with session_factory() as session:
        result = await session.execute(
            select(AuditEvent)
            .where(
                AuditEvent.action == action,
                AuditEvent.decision == decision,
                AuditEvent.resource_type == "AssignmentAttempt",
                AuditEvent.resource_id == resource_id,
            )
            .order_by(AuditEvent.id.desc())
        )
        return result.scalars().first()


def test_attempt_replay_student_self_returns_replayable_refs_and_allow_audit(client: TestClient) -> None:
    session_factory = client.app.state.test_sessionmaker
    attempt_id = asyncio.run(_seed_attempt(session_factory, teacher_id=7001, student_id=2001))
    timeline_id, segment_id, ref_id = asyncio.run(_seed_timeline_for_attempt(session_factory, attempt_id=attempt_id))

    trace_id = "i002-trace-student-self"
    response = client.get(
        f"/api/v1/teaching/attempts/{attempt_id}/replay",
        headers={
            "X-RMOS-Role": "student",
            "X-User-ID": "2001",
            "X-Trace-ID": trace_id,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["attemptId"] == attempt_id
    assert payload["status"] == "ok"
    assert payload["failurePoint"]["stepId"] == 2
    assert payload["failurePoint"]["eventId"] == 21
    assert payload["failurePoint"]["failureType"] == "E_ERROR_OCCURRED"
    assert payload["failurePoint"]["ruleHit"] == "R-DIAG-001"
    assert len(payload["evidenceRefs"]) == 1
    assert payload["evidenceRefs"][0]["refId"] == ref_id
    assert payload["evidenceRefs"][0]["timelineId"] == timeline_id
    assert payload["evidenceRefs"][0]["segmentId"] == segment_id

    event = asyncio.run(
        _latest_audit(
            session_factory,
            action="replay_requested",
            decision="allow",
            resource_id=str(attempt_id),
        )
    )
    assert event is not None
    assert event.trace_id == trace_id


def test_attempt_replay_student_cross_scope_returns_404_and_records_deny(client: TestClient) -> None:
    session_factory = client.app.state.test_sessionmaker
    attempt_id = asyncio.run(_seed_attempt(session_factory, teacher_id=7001, student_id=2001))
    asyncio.run(_seed_timeline_for_attempt(session_factory, attempt_id=attempt_id))

    response = client.get(
        f"/api/v1/teaching/attempts/{attempt_id}/replay",
        headers={
            "X-RMOS-Role": "student",
            "X-User-ID": "2002",
        },
    )
    assert response.status_code == 404
    payload = response.json()
    assert payload["error_type"] == "ReadAccessDeniedError"
    assert payload["details"]["code"] == "READ_ACCESS_DENIED"

    event = asyncio.run(
        _latest_audit(
            session_factory,
            action="access_denied",
            decision="deny",
            resource_id=str(attempt_id),
        )
    )
    assert event is not None
    assert event.reason == "student_attempt_scope_mismatch"


def test_attempt_replay_teacher_out_of_scope_returns_404_and_records_deny(client: TestClient) -> None:
    session_factory = client.app.state.test_sessionmaker
    attempt_id = asyncio.run(_seed_attempt(session_factory, teacher_id=7001, student_id=2001))
    asyncio.run(_seed_timeline_for_attempt(session_factory, attempt_id=attempt_id))

    response = client.get(
        f"/api/v1/teaching/attempts/{attempt_id}/replay",
        headers={
            "X-RMOS-Role": "teacher",
            "X-User-ID": "7002",
        },
    )
    assert response.status_code == 404
    payload = response.json()
    assert payload["error_type"] == "ReadAccessDeniedError"
    assert payload["details"]["code"] == "READ_ACCESS_DENIED"

    event = asyncio.run(
        _latest_audit(
            session_factory,
            action="access_denied",
            decision="deny",
            resource_id=str(attempt_id),
        )
    )
    assert event is not None
    assert event.reason == "teacher_course_scope_mismatch"


def test_attempt_replay_without_timeline_returns_insufficient_data(client: TestClient) -> None:
    session_factory = client.app.state.test_sessionmaker
    attempt_id = asyncio.run(_seed_attempt(session_factory, teacher_id=7001, student_id=2001))

    response = client.get(
        f"/api/v1/teaching/attempts/{attempt_id}/replay",
        headers={
            "X-RMOS-Role": "student",
            "X-User-ID": "2001",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["attemptId"] == attempt_id
    assert payload["status"] == "insufficient_data"
    assert payload["evidenceRefs"] == []
    assert payload["supplementPlan"]
