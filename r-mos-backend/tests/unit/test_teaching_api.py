"""
Teaching domain API tests.
"""
import asyncio
from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from app.core.database import get_db
from app.models.base import Base
from app.models.audit_event import AuditEvent
from app.models.evidence import EvidenceBundle
from app.models.teaching import EvidenceLink
import app.models as app_models  # noqa: F401  # Ensure models are registered
from app.schemas.sop import SOPCreate
from app.schemas.task import TaskCreate, StepExecutionRequest
from app.services.sop_service import SOPService
from app.services.task_service import TaskService
from app.services.teaching_service import TeachingService


@pytest.fixture
def client():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async def init_models():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_models())

    Session = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.state.test_sessionmaker = Session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    app.state.test_sessionmaker = None
    asyncio.run(engine.dispose())


def test_list_guidance_policies(client):
    resp = client.get("/api/v1/guidance-policies")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_guidance_policy(client):
    payload = {
        "name": "Level 1",
        "baseMode": "teaching",
        "allowGhostHand": True,
        "allowHintButton": True,
        "showErrorDetails": True,
        "maxRetryCount": -1,
    }
    resp = client.post("/api/v1/guidance-policies", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Level 1"
    assert data["baseMode"] == "teaching"
    assert data["allowGhostHand"] is True
    assert data["allowHintButton"] is True
    assert data["showErrorDetails"] is True
    assert data["maxRetryCount"] == -1


def test_create_class_and_get(client):
    resp = client.post("/api/v1/classes", json={"name": "Class A"})
    assert resp.status_code == 201
    class_id = resp.json()["id"]

    resp = client.get(f"/api/v1/classes/{class_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == class_id


def test_create_course_and_get(client):
    class_resp = client.post("/api/v1/classes", json={"name": "Class A"})
    class_id = class_resp.json()["id"]

    resp = client.post(
        "/api/v1/courses",
        json={"classId": class_id, "name": "Course 1"},
    )
    assert resp.status_code == 201
    course_id = resp.json()["id"]

    resp = client.get(f"/api/v1/courses/{course_id}")
    assert resp.status_code == 200
    assert resp.json()["classId"] == class_id


def test_enroll_student_duplicate(client):
    class_resp = client.post("/api/v1/classes", json={"name": "Class A"})
    class_id = class_resp.json()["id"]

    resp = client.post(
        "/api/v1/enrollments",
        json={"classId": class_id, "studentId": 1},
    )
    assert resp.status_code == 201

    resp = client.post(
        "/api/v1/enrollments",
        json={"classId": class_id, "studentId": 1},
    )
    assert resp.status_code == 409
    assert resp.json()["details"]["code"] == "ALREADY_ENROLLED"


def test_create_assignment_and_get(client):
    class_resp = client.post("/api/v1/classes", json={"name": "Class A"})
    class_id = class_resp.json()["id"]

    resp = client.post(
        "/api/v1/assignments",
        json={"classId": class_id, "title": "Assignment 1"},
    )
    assert resp.status_code == 201
    assignment_id = resp.json()["id"]

    resp = client.get(f"/api/v1/assignments/{assignment_id}")
    assert resp.status_code == 200
    assert resp.json()["classId"] == class_id


def test_create_attempts_increment_index(client):
    class_resp = client.post("/api/v1/classes", json={"name": "Class A"})
    class_id = class_resp.json()["id"]
    assignment_resp = client.post(
        "/api/v1/assignments",
        json={"classId": class_id, "title": "Assignment 1"},
    )
    assignment_id = assignment_resp.json()["id"]

    resp1 = client.post(
        f"/api/v1/assignments/{assignment_id}/attempts",
        json={"studentId": 10},
    )
    assert resp1.status_code == 201
    assert resp1.json()["attemptIndex"] == 1

    resp2 = client.post(
        f"/api/v1/assignments/{assignment_id}/attempts",
        json={"studentId": 10},
    )
    assert resp2.status_code == 201
    assert resp2.json()["attemptIndex"] == 2


def test_attempt_status_transitions(client):
    class_resp = client.post("/api/v1/classes", json={"name": "Class A"})
    class_id = class_resp.json()["id"]
    assignment_resp = client.post(
        "/api/v1/assignments",
        json={"classId": class_id, "title": "Assignment 1"},
    )
    assignment_id = assignment_resp.json()["id"]

    attempt_resp = client.post(
        f"/api/v1/assignments/{assignment_id}/attempts",
        json={"studentId": 42},
    )
    attempt_id = attempt_resp.json()["id"]

    resp = client.patch(
        f"/api/v1/attempts/{attempt_id}",
        json={"status": "completed"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"

    resp = client.post(
        f"/api/v1/attempts/{attempt_id}/grade",
        json={"score": 90.0},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "graded"
    assert resp.json()["score"] == 90.0

    resp = client.patch(
        f"/api/v1/attempts/{attempt_id}",
        json={"status": "completed"},
    )
    assert resp.status_code in (400, 409)


def test_audit_access_denied_records_real_resource_id(client):
    missing_attempt_id = 9999
    resp = client.get(f"/api/v1/attempts/{missing_attempt_id}")
    assert resp.status_code == 404

    Session = client.app.state.test_sessionmaker

    async def assert_audit_event():
        async with Session() as session:
            result = await session.execute(
                select(AuditEvent)
                .where(
                    AuditEvent.action == "access_denied",
                    AuditEvent.resource_type == "AssignmentAttempt",
                    AuditEvent.resource_id == str(missing_attempt_id),
                    AuditEvent.decision == "deny",
                )
                .order_by(AuditEvent.id.desc())
            )
            event = result.scalars().first()
            assert event is not None

    asyncio.run(assert_audit_event())


def test_audit_permission_denied_records_deny_event(client):
    class_resp = client.post("/api/v1/classes", json={"name": "权限班级"})
    class_id = class_resp.json()["id"]

    resp = client.post(
        "/api/v1/assignments",
        headers={"X-RMOS-Role": "student", "X-User-ID": "1001"},
        json={"classId": class_id, "title": "不应创建成功"},
    )
    assert resp.status_code == 403

    Session = client.app.state.test_sessionmaker

    async def assert_audit_event():
        async with Session() as session:
            result = await session.execute(
                select(AuditEvent)
                .where(
                    AuditEvent.action == "permission_denied",
                    AuditEvent.resource_type == "Assignment",
                    AuditEvent.decision == "deny",
                )
                .order_by(AuditEvent.id.desc())
            )
            event = result.scalars().first()
            assert event is not None
            assert event.actor_user_id == "1001"
            assert event.reason == "missing_role:teacher_or_admin"

    asyncio.run(assert_audit_event())


def test_get_attempt_evidence(client):
    Session = client.app.state.test_sessionmaker

    async def setup_data():
        async with Session() as session:
            sop_service = SOPService(session)
            sop = await sop_service.create_sop(
                SOPCreate(
                    name="测试SOP",
                    description="用于证据接口测试",
                    applicable_model="MOCK_HUMANOID_V1",
                    category="unit-test",
                    difficulty_level="low",
                    estimated_time=120,
                    steps=[
                        {
                            "step_index": 1,
                            "title": "步骤一",
                            "description": "第一个步骤",
                            "target_part": "knee_right",
                            "expected_action": "inspect",
                            "is_critical": True,
                            "timeout_seconds": 60,
                            "allow_skip": False,
                        },
                        {
                            "step_index": 2,
                            "title": "步骤二",
                            "description": "第二个步骤",
                            "target_part": "knee_right",
                            "expected_action": "execute",
                            "is_critical": False,
                            "timeout_seconds": 60,
                            "allow_skip": False,
                        },
                    ],
                )
            )

            teaching_service = TeachingService(session)
            teaching_class = await teaching_service.create_class(name="班级一")
            assignment = await teaching_service.create_assignment(
                class_id=teaching_class.id,
                title="作业一",
            )

            task_service = TaskService(session)
            task = await task_service.create_task(
                TaskCreate(title="任务一", sop_id=sop.id, user_id=1, pass_score=70)
            )
            task.assignment_id = assignment.id
            await session.commit()

            attempt = await teaching_service.create_attempt(
                assignment_id=assignment.id,
                student_id=101,
                task_id=task.id,
            )

            await task_service.start_task(task.id)
            await task_service.execute_step(
                task.id,
                StepExecutionRequest(step_index=1, action="execute", parameters={}),
            )
            await task_service.execute_step(
                task.id,
                StepExecutionRequest(step_index=2, action="execute", parameters={}),
            )

            return attempt.id, task.id

    attempt_id, task_id = asyncio.run(setup_data())

    resp = client.get(f"/api/v1/attempts/{attempt_id}/evidence")
    assert resp.status_code == 200
    data = resp.json()
    assert data["attemptId"] == attempt_id
    assert data["taskId"] == task_id
    assert data["bundleId"]
    summary = data["summary"]
    assert summary is not None
    assert "total_steps" in summary
    assert "skip_count" in summary
    assert "error_count" in summary
    assert "duration_ms" in summary


def test_get_attempt_evidence_link_not_found(client):
    Session = client.app.state.test_sessionmaker

    async def setup_data():
        async with Session() as session:
            teaching_service = TeachingService(session)
            teaching_class = await teaching_service.create_class(name="班级二")
            assignment = await teaching_service.create_assignment(
                class_id=teaching_class.id,
                title="作业二",
            )
            attempt = await teaching_service.create_attempt(
                assignment_id=assignment.id,
                student_id=102,
                task_id=None,
            )
            return attempt.id

    attempt_id = asyncio.run(setup_data())

    resp = client.get(f"/api/v1/attempts/{attempt_id}/evidence")
    assert resp.status_code == 404


async def _setup_completed_attempt(session, *, set_task_assignment: bool) -> tuple[int, int]:
    sop_service = SOPService(session)
    sop = await sop_service.create_sop(
        SOPCreate(
            name="证据兜底SOP",
            description="用于证据兜底测试",
            applicable_model="MOCK_HUMANOID_V1",
            category="unit-test",
            difficulty_level="low",
            estimated_time=120,
            steps=[
                {
                    "step_index": 1,
                    "title": "步骤一",
                    "description": "第一个步骤",
                    "target_part": "knee_right",
                    "expected_action": "inspect",
                    "is_critical": True,
                    "timeout_seconds": 60,
                    "allow_skip": False,
                },
                {
                    "step_index": 2,
                    "title": "步骤二",
                    "description": "第二个步骤",
                    "target_part": "knee_right",
                    "expected_action": "execute",
                    "is_critical": False,
                    "timeout_seconds": 60,
                    "allow_skip": False,
                },
            ],
        )
    )

    teaching_service = TeachingService(session)
    teaching_class = await teaching_service.create_class(name="证据兜底班级")
    assignment = await teaching_service.create_assignment(
        class_id=teaching_class.id,
        title="证据兜底作业",
    )

    task_service = TaskService(session)
    task = await task_service.create_task(
        TaskCreate(title="证据兜底任务", sop_id=sop.id, user_id=1, pass_score=70)
    )
    if set_task_assignment:
        task.assignment_id = assignment.id
        await session.commit()

    attempt = await teaching_service.create_attempt(
        assignment_id=assignment.id,
        student_id=201,
        task_id=task.id,
    )

    await task_service.start_task(task.id)
    await task_service.execute_step(
        task.id,
        StepExecutionRequest(step_index=1, action="inspect", parameters={}),
    )
    await task_service.execute_step(
        task.id,
        StepExecutionRequest(step_index=2, action="execute", parameters={}),
    )

    await teaching_service.update_attempt_status(attempt.id, "completed")
    return attempt.id, task.id


def test_evidence_completed_attempt_without_link_returns_200(client):
    Session = client.app.state.test_sessionmaker

    async def setup_data():
        async with Session() as session:
            attempt_id, task_id = await _setup_completed_attempt(
                session, set_task_assignment=False
            )
            # 模拟历史数据缺失 EvidenceLink 的场景
            await session.execute(delete(EvidenceLink).where(EvidenceLink.attempt_id == attempt_id))
            await session.commit()
            return attempt_id, task_id

    attempt_id, task_id = asyncio.run(setup_data())

    resp = client.get(f"/api/v1/attempts/{attempt_id}/evidence")
    assert resp.status_code == 200
    data = resp.json()
    assert data["attemptId"] == attempt_id
    assert data["taskId"] == task_id
    assert data["bundleId"]
    summary = data["summary"]
    assert summary is not None
    assert "total_steps" in summary
    assert "error_count" in summary
    assert "skip_count" in summary
    assert "duration_ms" in summary


def test_report_then_evidence_creates_link_and_returns_200(client):
    Session = client.app.state.test_sessionmaker

    async def setup_data():
        async with Session() as session:
            attempt_id, task_id = await _setup_completed_attempt(
                session, set_task_assignment=False
            )
            await session.execute(delete(EvidenceLink).where(EvidenceLink.attempt_id == attempt_id))
            await session.commit()
            return attempt_id, task_id

    attempt_id, task_id = asyncio.run(setup_data())

    report_resp = client.get(f"/api/v1/tasks/{task_id}/report")
    assert report_resp.status_code == 200
    evidence_resp = client.get(f"/api/v1/attempts/{attempt_id}/evidence")
    assert evidence_resp.status_code == 200

    Session = client.app.state.test_sessionmaker

    async def assert_link_exists():
        async with Session() as session:
            links = (
                await session.execute(
                    select(EvidenceLink).where(EvidenceLink.attempt_id == attempt_id)
                )
            ).scalars().all()
            assert links, "应至少存在一条 EvidenceLink"

    asyncio.run(assert_link_exists())


def test_report_and_evidence_are_idempotent(client):
    Session = client.app.state.test_sessionmaker

    async def setup_data():
        async with Session() as session:
            attempt_id, task_id = await _setup_completed_attempt(
                session, set_task_assignment=False
            )
            await session.execute(delete(EvidenceLink).where(EvidenceLink.attempt_id == attempt_id))
            await session.commit()
            return attempt_id, task_id

    attempt_id, task_id = asyncio.run(setup_data())

    # 首次触发
    assert client.get(f"/api/v1/tasks/{task_id}/report").status_code == 200
    first_evidence = client.get(f"/api/v1/attempts/{attempt_id}/evidence")
    assert first_evidence.status_code == 200

    # 重复触发，仍应稳定返回 200
    assert client.get(f"/api/v1/tasks/{task_id}/report").status_code == 200
    second_evidence = client.get(f"/api/v1/attempts/{attempt_id}/evidence")
    assert second_evidence.status_code == 200

    summary = second_evidence.json().get("summary") or {}
    for key in ("total_steps", "error_count", "skip_count", "duration_ms"):
        assert key in summary


async def _setup_attempt_with_evidence(session, *, summary: dict) -> int:
    teaching_service = TeachingService(session)
    teaching_class = await teaching_service.create_class(name="诊断班级")
    assignment = await teaching_service.create_assignment(
        class_id=teaching_class.id,
        title="诊断作业",
    )
    attempt = await teaching_service.create_attempt(
        assignment_id=assignment.id,
        student_id=101,
        task_id=None,
    )

    bundle = EvidenceBundle(
        id=str(uuid4()),
        bundle_type="sop_execution",
        bundle_hash="hash",
        bundle_hash_algo="sha256",
        observed_time_start=datetime.utcnow(),
        ingest_time=datetime.utcnow(),
        is_sealed=True,
        sealed_at=datetime.utcnow(),
        machine_tags=summary,
    )
    session.add(bundle)
    await session.flush()

    link = EvidenceLink(
        bundle_id=bundle.id,
        attempt_id=attempt.id,
    )
    session.add(link)
    await session.commit()
    return attempt.id


def test_get_attempt_diagnosis_error_count_rule(client):
    Session = client.app.state.test_sessionmaker

    async def setup_data():
        async with Session() as session:
            return await _setup_attempt_with_evidence(
                session,
                summary={"error_count": 1, "skip_count": 0, "duration_ms": 1000},
            )

    attempt_id = asyncio.run(setup_data())

    resp = client.get(f"/api/v1/attempts/{attempt_id}/diagnosis")
    assert resp.status_code == 200
    data = resp.json()
    assert data["diagnosisCode"] == "E_ERROR_OCCURRED"
    assert data["ruleId"] == "R-DIAG-001"
    assert data["severity"] == "HIGH"
    assert "findings" in data
    assert "recommendations" in data


def test_get_attempt_diagnosis_no_match(client):
    Session = client.app.state.test_sessionmaker

    async def setup_data():
        async with Session() as session:
            return await _setup_attempt_with_evidence(
                session,
                summary={"error_count": 0, "skip_count": 0, "duration_ms": 5000},
            )

    attempt_id = asyncio.run(setup_data())

    resp = client.get(f"/api/v1/attempts/{attempt_id}/diagnosis")
    assert resp.status_code == 200
    data = resp.json()
    assert data["diagnosisCode"] == "OK"
    assert data["ruleId"] == "R-DIAG-000"
    assert data["severity"] == "LOW"


def test_get_attempt_diagnosis_fallback_generates_evidence(client):
    Session = client.app.state.test_sessionmaker

    async def setup_data():
        async with Session() as session:
            attempt_id, _task_id = await _setup_completed_attempt(
                session, set_task_assignment=False
            )
            await session.execute(delete(EvidenceLink).where(EvidenceLink.attempt_id == attempt_id))
            await session.commit()
            return attempt_id

    attempt_id = asyncio.run(setup_data())

    resp = client.get(f"/api/v1/attempts/{attempt_id}/diagnosis")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("sourceRefs", {}).get("attemptEvidenceId")


def test_get_attempt_diagnosis_idempotent(client):
    Session = client.app.state.test_sessionmaker

    async def setup_data():
        async with Session() as session:
            return await _setup_attempt_with_evidence(
                session,
                summary={"error_count": 0, "skip_count": 1, "duration_ms": 1000},
            )

    attempt_id = asyncio.run(setup_data())

    first = client.get(f"/api/v1/attempts/{attempt_id}/diagnosis")
    second = client.get(f"/api/v1/attempts/{attempt_id}/diagnosis")
    third = client.get(f"/api/v1/attempts/{attempt_id}/diagnosis")
    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 200
    assert first.json()["diagnosisCode"] == second.json()["diagnosisCode"] == third.json()["diagnosisCode"]
