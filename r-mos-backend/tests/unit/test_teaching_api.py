"""
Teaching domain API tests.
"""
import asyncio
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from app.core.database import get_db
from app.models.base import Base
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
