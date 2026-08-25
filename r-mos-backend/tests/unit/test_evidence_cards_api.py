"""Gate-3 I-003：evidence_cards 生成最小闭环测试。"""
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
from app.models.timeline import MultimodalTimeline, TimelineSegment
from app.services.teaching_service import TeachingService
from main import app
from app.models.school import School
from tests.e2e.helpers import E2E_SCHOOL_NAME, register_and_login  # 复用既有登录基建


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
            await conn.execute(School.__table__.insert().values(name=E2E_SCHOOL_NAME))

    asyncio.run(init_models())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.state.test_sessionmaker = session_factory

    with TestClient(app) as test_client:
        # AUTH-101 默认拒绝网关 + AUTH-104 身份只来自令牌：
        # 预置一位默认教师作为客户端默认身份；需要学生身份的用例用
        # register_and_login(client, ..., role="student") 切换。
        register_and_login(test_client, email_prefix="evidence_cards_actor")
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
        service = TeachingService(session)
        teaching_class = await service.create_class(name="I-003 班级", teacher_id=teacher_id)
        assignment = await service.create_assignment(class_id=teaching_class.id, title="I-003 作业")
        await service.enroll_student(class_id=teaching_class.id, student_id=student_id)
        attempt = await service.create_attempt(assignment_id=assignment.id, student_id=student_id, task_id=None)
        return attempt.id


async def _seed_timeline_segments(
    session_factory: async_sessionmaker,
    *,
    attempt_id: int,
) -> list[str]:
    async with session_factory() as session:
        timeline = MultimodalTimeline(
            scope_type="attempt",
            scope_id=str(attempt_id),
            trace_id=f"i003-trace-{attempt_id}",
            created_by_user_id="7001",
        )
        session.add(timeline)
        await session.flush()

        refs: list[str] = []
        for segment_type in ("event", "log", "snapshot"):
            ref_id = f"{segment_type}-{uuid4().hex[:8]}"
            refs.append(ref_id)
            segment = TimelineSegment(
                timeline_id=timeline.id,
                segment_type=segment_type,
                ref_id=ref_id,
                start_ts_ms=1000,
                end_ts_ms=1500,
                payload={"snippet": f"{segment_type}-snippet"},
            )
            session.add(segment)

        await session.commit()
        return refs


async def _latest_audit(
    session_factory: async_sessionmaker,
    *,
    action: str,
    decision: str,
    resource_type: str,
    resource_id: str,
) -> AuditEvent | None:
    async with session_factory() as session:
        result = await session.execute(
            select(AuditEvent)
            .where(
                AuditEvent.action == action,
                AuditEvent.decision == decision,
                AuditEvent.resource_type == resource_type,
                AuditEvent.resource_id == resource_id,
            )
            .order_by(AuditEvent.id.desc())
        )
        return result.scalars().first()


def _register_actors(client: TestClient) -> dict:
    """注册真实的教师/学生账号（AUTH-104：角色与主体只来自令牌）。"""
    teacher_id, _, teacher_login = register_and_login(client, email_prefix="ec_owner_teacher")
    _other_teacher_id, _, other_teacher_login = register_and_login(
        client, email_prefix="ec_other_teacher"
    )
    student_id, _, student_login = register_and_login(
        client, email_prefix="ec_owner_student", role="student", teacher_id=teacher_id
    )
    return {
        "teacher_id": teacher_id,
        "teacher_token": teacher_login["access_token"],
        "other_teacher_token": other_teacher_login["access_token"],
        "student_id": student_id,
        "student_token": student_login["access_token"],
    }


def _act_as(client: TestClient, token: str) -> None:
    client.headers["Authorization"] = f"Bearer {token}"


def test_evidence_card_teacher_can_create_and_record_allow_audit(client: TestClient) -> None:
    session_factory = client.app.state.test_sessionmaker
    actors = _register_actors(client)
    attempt_id = asyncio.run(
        _seed_attempt(
            session_factory,
            teacher_id=actors["teacher_id"],
            student_id=actors["student_id"],
        )
    )
    refs = asyncio.run(_seed_timeline_segments(session_factory, attempt_id=attempt_id))

    # 带该班的真实教师
    _act_as(client, actors["teacher_token"])
    response = client.post(
        "/api/v1/evidence_cards",
        json={"attemptId": attempt_id, "cardType": "failure_point"},
        headers={"X-Trace-ID": "i003-teacher-allow"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["attemptId"] == attempt_id
    assert payload["cardType"] == "failure_point"
    response_refs = payload["references"]
    assert len(response_refs) == 3
    assert {item["refId"] for item in response_refs} == set(refs)

    event = asyncio.run(
        _latest_audit(
            session_factory,
            action="evidence_card_created",
            decision="allow",
            resource_type="EvidenceCard",
            resource_id=str(payload["evidenceCardId"]),
        )
    )
    assert event is not None
    assert event.trace_id == "i003-teacher-allow"


def test_evidence_card_student_write_denied_403_and_records_real_attempt_id(client: TestClient) -> None:
    session_factory = client.app.state.test_sessionmaker
    actors = _register_actors(client)
    attempt_id = asyncio.run(
        _seed_attempt(
            session_factory,
            teacher_id=actors["teacher_id"],
            student_id=actors["student_id"],
        )
    )
    asyncio.run(_seed_timeline_segments(session_factory, attempt_id=attempt_id))

    # 真实学生：无写权限
    _act_as(client, actors["student_token"])
    response = client.post(
        "/api/v1/evidence_cards",
        json={"attemptId": attempt_id, "cardType": "failure_point"},
    )
    assert response.status_code == 403
    payload = response.json()
    assert payload["error_type"] == "WriteAccessDeniedError"
    assert payload["details"]["code"] == "WRITE_ACCESS_DENIED"

    event = asyncio.run(
        _latest_audit(
            session_factory,
            action="write_access_denied",
            decision="deny",
            resource_type="AssignmentAttempt",
            resource_id=str(attempt_id),
        )
    )
    assert event is not None
    assert event.reason == "missing_role:teacher_or_admin"


def test_evidence_card_teacher_out_of_scope_denied_403_and_records_real_attempt_id(client: TestClient) -> None:
    session_factory = client.app.state.test_sessionmaker
    actors = _register_actors(client)
    attempt_id = asyncio.run(
        _seed_attempt(
            session_factory,
            teacher_id=actors["teacher_id"],
            student_id=actors["student_id"],
        )
    )
    asyncio.run(_seed_timeline_segments(session_factory, attempt_id=attempt_id))

    # 另一名真实教师：不带这个班
    _act_as(client, actors["other_teacher_token"])
    response = client.post(
        "/api/v1/evidence_cards",
        json={"attemptId": attempt_id, "cardType": "failure_point"},
    )
    assert response.status_code == 403
    payload = response.json()
    assert payload["error_type"] == "WriteAccessDeniedError"
    assert payload["details"]["code"] == "WRITE_ACCESS_DENIED"

    event = asyncio.run(
        _latest_audit(
            session_factory,
            action="write_access_denied",
            decision="deny",
            resource_type="AssignmentAttempt",
            resource_id=str(attempt_id),
        )
    )
    assert event is not None
    assert event.reason == "teacher_attempt_scope_mismatch"
