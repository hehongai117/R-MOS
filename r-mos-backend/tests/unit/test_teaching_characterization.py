"""
特征测试：app/api/v1/endpoints/teaching.py
目标：行覆盖率 ≥ 80%（Phase 2 safety-net）

测试策略：
- 复用 _build_client / _register_and_login 基建（与 test_skill_governance_api.py 同款）
- 每个路由至少一条正常路径 + 关键错误路径，精确断言真实状态码和关键字段
- 覆盖 student/teacher 角色权限检查
- 覆盖 replay / evidence_card 完整函数体（两个最大未覆盖区域）
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import app.models as app_models  # noqa: F401  # 确保模型全部注册
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.models.base import Base
from app.models.evidence import EvidenceBundle
from app.models.school import School
from app.models.teaching import (
    Assignment,
    AssignmentAttempt,
    Enrollment,
    TeachingClass,
    EvidenceLink,
)
from app.models.timeline import (
    AlignmentMap,
    MultimodalTimeline,
    TimelineSegment,
)
from main import app

TEST_SCHOOL_NAME = "测试学校"


# ─────────────────────────────────────────────────────────────────────────────
# 测试基建
# ─────────────────────────────────────────────────────────────────────────────

def _build_client() -> tuple[TestClient, async_sessionmaker]:
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
    return TestClient(app), session_factory


async def _seed_attempt(
    session_factory: async_sessionmaker,
    *,
    teacher_id: int = 1,
    student_id: int = 42,
    task_id: int | None = None,
) -> tuple[int, int, int, int]:
    """
    Seed a minimal class → assignment → attempt chain.
    Returns (class_id, assignment_id, attempt_id, teacher_id).
    """
    async with session_factory() as session:
        teaching_class = TeachingClass(name="特征测试班级", teacher_id=teacher_id)
        session.add(teaching_class)
        await session.flush()

        assignment = Assignment(class_id=teaching_class.id, title="特征测试作业")
        session.add(assignment)
        await session.flush()

        attempt = AssignmentAttempt(
            assignment_id=assignment.id,
            student_id=student_id,
            task_id=task_id,
            attempt_index=1,
            status="in_progress",
        )
        session.add(attempt)
        await session.commit()
        return teaching_class.id, assignment.id, attempt.id, teacher_id


# ─────────────────────────────────────────────────────────────────────────────
# GET /guidance-policies/{policy_id}  → 404 on missing
# ─────────────────────────────────────────────────────────────────────────────

def test_get_guidance_policy_not_found_returns_404():
    """
    GET /api/v1/guidance-policies/9999 — 锁定 404 + error_type shape。
    注意: _raise_not_found 将 ResourceNotFoundError 转换为 HTTPException，
    因此 error_type 为 "HTTPException"（当前行为，特征锁定）。
    覆盖: _raise_not_found (line 84), get_guidance_policy error branch (141-145).
    """
    client, _ = _build_client()
    try:
        resp = client.get("/api/v1/guidance-policies/9999")
        assert resp.status_code == 404
        body = resp.json()
        # _raise_not_found → HTTPException → http_exception_handler → error_type="HTTPException"
        assert body["error_type"] == "ResourceNotFoundError"
        assert body["details"] is not None
        assert "9999" in str(body["details"])
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_create_guidance_policy_basic_fields():
    """
    POST /api/v1/guidance-policies — 正常创建，锁定 camelCase 返回字段。
    """
    client, _ = _build_client()
    try:
        resp = client.post(
            "/api/v1/guidance-policies",
            json={
                "name": "CharTestPolicy",
                "baseMode": "exam",
                "allowGhostHand": False,
                "allowHintButton": False,
                "showErrorDetails": False,
                "maxRetryCount": 3,
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "CharTestPolicy"
        assert body["baseMode"] == "exam"
        assert body["allowGhostHand"] is False
        assert body["allowHintButton"] is False
        assert body["showErrorDetails"] is False
        assert body["maxRetryCount"] == 3
        # id 是自增整数，只检查类型
        assert isinstance(body["id"], int)
    finally:
        client.close()
        app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# GET /classes/{class_id}  — student 角色访问控制
# ─────────────────────────────────────────────────────────────────────────────

def test_get_class_student_no_user_id_returns_404():
    """
    GET /api/v1/classes/{id} with X-RMOS-Role: student but no X-User-ID header
    → 404 ReadAccessDeniedError (invalid_actor_student_id).
    覆盖: get_class student branch lines 195-206.
    """
    client, _ = _build_client()
    try:
        # 先创建 class
        create_resp = client.post("/api/v1/classes", json={"name": "角色测试班级"})
        assert create_resp.status_code == 201
        class_id = create_resp.json()["id"]

        resp = client.get(
            f"/api/v1/classes/{class_id}",
            headers={"X-RMOS-Role": "student"},  # 无 X-User-ID
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error_type"] == "ReadAccessDeniedError"
        assert body["details"]["code"] == "READ_ACCESS_DENIED"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_get_class_student_not_enrolled_returns_404():
    """
    GET /api/v1/classes/{id} with student role but student not enrolled
    → 404 ReadAccessDeniedError (student_class_scope_mismatch).
    覆盖: get_class enrollment check lines 207-223.
    """
    client, sf = _build_client()
    try:
        create_resp = client.post("/api/v1/classes", json={"name": "未入学班级"})
        assert create_resp.status_code == 201
        class_id = create_resp.json()["id"]

        resp = client.get(
            f"/api/v1/classes/{class_id}",
            headers={"X-RMOS-Role": "student", "X-User-ID": "9001"},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error_type"] == "ReadAccessDeniedError"
        assert body["details"]["code"] == "READ_ACCESS_DENIED"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_get_class_student_enrolled_returns_200():
    """
    GET /api/v1/classes/{id} with student role who IS enrolled → 200.
    覆盖: get_class enrollment found path line 224-225.
    """
    client, sf = _build_client()
    try:
        create_resp = client.post("/api/v1/classes", json={"name": "已入学班级"})
        assert create_resp.status_code == 201
        class_id = create_resp.json()["id"]
        student_id = 7777

        # 添加 enrollment
        enroll_resp = client.post(
            "/api/v1/enrollments",
            json={"classId": class_id, "studentId": student_id},
        )
        assert enroll_resp.status_code == 201

        resp = client.get(
            f"/api/v1/classes/{class_id}",
            headers={"X-RMOS-Role": "student", "X-User-ID": str(student_id)},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == class_id
        assert body["name"] == "已入学班级"
    finally:
        client.close()
        app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /classes/{class_id}  — 权限检查 + 正常更新
# ─────────────────────────────────────────────────────────────────────────────

def test_update_class_student_role_denied():
    """
    PATCH /api/v1/classes/{id} with X-RMOS-Role: student → 403 WriteAccessDeniedError.
    覆盖: update_class role check lines 246-255.
    """
    client, _ = _build_client()
    try:
        create_resp = client.post("/api/v1/classes", json={"name": "写越权班级"})
        assert create_resp.status_code == 201
        class_id = create_resp.json()["id"]

        resp = client.patch(
            f"/api/v1/classes/{class_id}",
            headers={"X-RMOS-Role": "student", "X-User-ID": "9002"},
            json={"name": "不应修改"},
        )
        assert resp.status_code == 403
        body = resp.json()
        assert body["error_type"] == "WriteAccessDeniedError"
        assert body["details"]["code"] == "WRITE_ACCESS_DENIED"
        assert body["details"]["details"]["reason"] == "missing_role:teacher_or_admin"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_update_class_teacher_role_succeeds():
    """
    PATCH /api/v1/classes/{id} with X-RMOS-Role: teacher → 200 with updated fields.
    覆盖: update_class success path lines 256-266.
    """
    client, _ = _build_client()
    try:
        create_resp = client.post("/api/v1/classes", json={"name": "待更新班级"})
        assert create_resp.status_code == 201
        class_id = create_resp.json()["id"]

        resp = client.patch(
            f"/api/v1/classes/{class_id}",
            headers={"X-RMOS-Role": "teacher", "X-User-ID": "1"},
            json={"name": "已更新班级", "term": "2025-A"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == class_id
        assert body["name"] == "已更新班级"
        assert body["term"] == "2025-A"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_update_class_not_found_returns_404():
    """
    PATCH /api/v1/classes/9999 → 404 HTTPException (via _raise_not_found).
    覆盖: update_class not-found early branch.
    """
    client, _ = _build_client()
    try:
        resp = client.patch(
            "/api/v1/classes/9999",
            json={"name": "不存在"},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error_type"] == "ResourceNotFoundError"
        assert body["details"] is not None
        assert "9999" in str(body["details"])
    finally:
        client.close()
        app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# GET /courses  — class_id 过滤
# ─────────────────────────────────────────────────────────────────────────────

def test_list_courses_with_class_id_filter():
    """
    GET /api/v1/courses?classId=X — 锁定带过滤器的列表返回 list。
    覆盖: list_courses class_id filter branch lines 278-279.
    """
    client, _ = _build_client()
    try:
        # 创建 class
        class_resp = client.post("/api/v1/classes", json={"name": "课程过滤班级"})
        assert class_resp.status_code == 201
        class_id = class_resp.json()["id"]

        # 在 class 下创建 course
        course_resp = client.post(
            "/api/v1/courses",
            json={"classId": class_id, "name": "过滤课程"},
        )
        assert course_resp.status_code == 201

        resp = client.get(f"/api/v1/courses?classId={class_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 1
        assert body[0]["classId"] == class_id
        assert body[0]["name"] == "过滤课程"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_create_course_class_not_found_returns_404():
    """
    POST /api/v1/courses with non-existent classId → 404 HTTPException (via _raise_not_found).
    覆盖: create_course ResourceNotFoundError branch lines 296-299.
    """
    client, _ = _build_client()
    try:
        resp = client.post(
            "/api/v1/courses",
            json={"classId": 99999, "name": "孤儿课程"},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error_type"] == "ResourceNotFoundError"
        assert body["details"] is not None
        assert "99999" in str(body["details"])
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_get_course_not_found_returns_404():
    """
    GET /api/v1/courses/9999 → 404 HTTPException (via _raise_not_found).
    覆盖: get_course not-found branch lines 311-312.
    """
    client, _ = _build_client()
    try:
        resp = client.get("/api/v1/courses/9999")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error_type"] == "ResourceNotFoundError"
        assert body["details"] is not None
        assert "9999" in str(body["details"])
    finally:
        client.close()
        app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# POST /enrollments  — ResourceNotFoundError (class 不存在)
# ─────────────────────────────────────────────────────────────────────────────

def test_enroll_student_class_not_found_returns_404():
    """
    POST /api/v1/enrollments with non-existent classId → 404 HTTPException (via _raise_not_found).
    覆盖: enroll_student ResourceNotFoundError branch lines 338-341.
    """
    client, _ = _build_client()
    try:
        resp = client.post(
            "/api/v1/enrollments",
            json={"classId": 88888, "studentId": 1},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error_type"] == "ResourceNotFoundError"
        assert body["details"] is not None
        assert "88888" in str(body["details"])
    finally:
        client.close()
        app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# GET /assignments  — class_id 过滤
# ─────────────────────────────────────────────────────────────────────────────

def test_list_assignments_with_class_id_filter():
    """
    GET /api/v1/assignments?classId=X → list filtered by class.
    覆盖: list_assignments class_id filter branch lines 353-354.
    """
    client, _ = _build_client()
    try:
        class_resp = client.post("/api/v1/classes", json={"name": "作业过滤班级"})
        assert class_resp.status_code == 201
        class_id = class_resp.json()["id"]

        client.post(
            "/api/v1/assignments",
            json={"classId": class_id, "title": "过滤作业"},
        )

        resp = client.get(f"/api/v1/assignments?classId={class_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 1
        assert body[0]["classId"] == class_id
        assert body[0]["title"] == "过滤作业"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_create_assignment_class_not_found_returns_404():
    """
    POST /api/v1/assignments with non-existent classId → 404 HTTPException (via _raise_not_found).
    覆盖: create_assignment ResourceNotFoundError branch lines 383-386.
    """
    client, _ = _build_client()
    try:
        resp = client.post(
            "/api/v1/assignments",
            json={"classId": 77777, "title": "孤儿作业"},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error_type"] == "ResourceNotFoundError"
        assert body["details"] is not None
        assert "77777" in str(body["details"])
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_get_assignment_not_found_returns_404():
    """
    GET /api/v1/assignments/9999 → 404 HTTPException (via _raise_not_found).
    覆盖: get_assignment not-found branch lines 398-399.
    """
    client, _ = _build_client()
    try:
        resp = client.get("/api/v1/assignments/9999")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error_type"] == "ResourceNotFoundError"
        assert body["details"] is not None
        assert "9999" in str(body["details"])
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_list_attempts_assignment_not_found_returns_404():
    """
    GET /api/v1/assignments/9999/attempts → 404 HTTPException (via _raise_not_found).
    覆盖: list_attempts ResourceNotFoundError branch lines 408-412.
    """
    client, _ = _build_client()
    try:
        resp = client.get("/api/v1/assignments/9999/attempts")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error_type"] == "ResourceNotFoundError"
        assert body["details"] is not None
        assert "9999" in str(body["details"])
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_create_attempt_assignment_not_found_returns_404():
    """
    POST /api/v1/assignments/9999/attempts → 404 HTTPException (via _raise_not_found).
    覆盖: create_attempt ResourceNotFoundError branch lines 433-436.
    """
    client, _ = _build_client()
    try:
        resp = client.post(
            "/api/v1/assignments/9999/attempts",
            json={"studentId": 1},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error_type"] == "ResourceNotFoundError"
        assert body["details"] is not None
        assert "9999" in str(body["details"])
    finally:
        client.close()
        app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# GET /attempts/{attempt_id}  — student 角色访问控制
# ─────────────────────────────────────────────────────────────────────────────

def test_get_attempt_student_matching_returns_200():
    """
    GET /api/v1/attempts/{id} with student role whose id matches attempt.student_id → 200.
    覆盖: get_attempt student branch success path lines 454-468.
    """
    client, sf = _build_client()
    try:
        student_id = 2001
        _, _, attempt_id, _ = asyncio.run(_seed_attempt(sf, student_id=student_id))

        resp = client.get(
            f"/api/v1/attempts/{attempt_id}",
            headers={"X-RMOS-Role": "student", "X-User-ID": str(student_id)},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == attempt_id
        assert body["studentId"] == student_id
        assert body["status"] == "in_progress"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_get_attempt_student_null_user_id_returns_404():
    """
    GET /api/v1/attempts/{id} with student role and missing/invalid X-User-ID → 404.
    覆盖: get_attempt _parse_user_id(None) returns None → access denied lines 455-466.
    """
    client, sf = _build_client()
    try:
        _, _, attempt_id, _ = asyncio.run(_seed_attempt(sf, student_id=3001))

        resp = client.get(
            f"/api/v1/attempts/{attempt_id}",
            headers={"X-RMOS-Role": "student"},  # 无 X-User-ID
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error_type"] == "ReadAccessDeniedError"
        assert body["details"]["code"] == "READ_ACCESS_DENIED"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_get_attempt_student_wrong_id_returns_404():
    """
    GET /api/v1/attempts/{id} with student role but wrong student_id → 404.
    覆盖: get_attempt student_id mismatch path.
    """
    client, sf = _build_client()
    try:
        _, _, attempt_id, _ = asyncio.run(_seed_attempt(sf, student_id=4001))

        resp = client.get(
            f"/api/v1/attempts/{attempt_id}",
            headers={"X-RMOS-Role": "student", "X-User-ID": "9999"},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error_type"] == "ReadAccessDeniedError"
        assert body["details"]["code"] == "READ_ACCESS_DENIED"
    finally:
        client.close()
        app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# GET /teaching/attempts/{attempt_id}/replay  — 多路径覆盖
# ─────────────────────────────────────────────────────────────────────────────

def test_get_attempt_replay_not_found_returns_404():
    """
    GET /api/v1/teaching/attempts/9999/replay → 404 (attempt not found).
    覆盖: get_attempt_replay - ResourceNotFoundError propagates to global handler.
    """
    client, _ = _build_client()
    try:
        resp = client.get("/api/v1/teaching/attempts/9999/replay")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error_type"] == "ResourceNotFoundError"
        assert body["details"]["code"] == "RESOURCE_NOT_FOUND"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_get_attempt_replay_no_timeline_returns_insufficient_data():
    """
    GET /api/v1/teaching/attempts/{id}/replay with no timeline → 200 status="insufficient_data".
    覆盖: get_attempt_replay timeline is None branch lines 537-558.
    """
    client, sf = _build_client()
    try:
        _, _, attempt_id, _ = asyncio.run(_seed_attempt(sf, student_id=5001))

        resp = client.get(f"/api/v1/teaching/attempts/{attempt_id}/replay")
        assert resp.status_code == 200
        body = resp.json()
        assert body["attemptId"] == attempt_id
        assert body["status"] == "insufficient_data"
        assert body["failurePoint"]["failureType"] == "insufficient_data"
        assert body["evidenceRefs"] == []
        assert len(body["supplementPlan"]) == 1
        assert body["supplementPlan"][0]["dataType"] == "timeline"
        assert body["supplementPlan"][0]["reason"] == "missing_timeline_segments"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_get_attempt_replay_timeline_no_segments_returns_insufficient_data():
    """
    GET /api/v1/teaching/attempts/{id}/replay with timeline but no segments
    → 200 status="insufficient_data".
    覆盖: get_attempt_replay segments empty branch lines 567-587.
    """
    client, sf = _build_client()
    try:
        _, _, attempt_id, _ = asyncio.run(_seed_attempt(sf, student_id=5002))

        async def seed_empty_timeline():
            async with sf() as session:
                timeline = MultimodalTimeline(
                    scope_type="attempt",
                    scope_id=str(attempt_id),
                )
                session.add(timeline)
                await session.commit()

        asyncio.run(seed_empty_timeline())

        resp = client.get(f"/api/v1/teaching/attempts/{attempt_id}/replay")
        assert resp.status_code == 200
        body = resp.json()
        assert body["attemptId"] == attempt_id
        assert body["status"] == "insufficient_data"
        assert body["failurePoint"]["failureType"] == "insufficient_data"
        assert body["evidenceRefs"] == []
        assert len(body["supplementPlan"]) == 1
        assert body["supplementPlan"][0]["dataType"] == "timeline_segment"
        assert body["supplementPlan"][0]["reason"] == "missing_timeline_segments"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_get_attempt_replay_segments_no_alignment_returns_insufficient_data():
    """
    GET /api/v1/teaching/attempts/{id}/replay with timeline + segments but no alignment
    → 200 status="insufficient_data" (no evidence_refs).
    覆盖: get_attempt_replay alignment branch lines 589-629.
    """
    client, sf = _build_client()
    try:
        _, _, attempt_id, _ = asyncio.run(_seed_attempt(sf, student_id=5003))

        async def seed_timeline_with_segments():
            async with sf() as session:
                timeline = MultimodalTimeline(
                    scope_type="attempt",
                    scope_id=str(attempt_id),
                )
                session.add(timeline)
                await session.flush()

                segment = TimelineSegment(
                    timeline_id=timeline.id,
                    segment_type="event",
                    ref_id="ref-001",
                    start_ts_ms=1000,
                    end_ts_ms=2000,
                    payload={"step_id": 1, "event_id": 2, "failure_type": "step_skip"},
                )
                session.add(segment)
                await session.commit()
                return timeline.id, segment.id

        asyncio.run(seed_timeline_with_segments())

        resp = client.get(f"/api/v1/teaching/attempts/{attempt_id}/replay")
        assert resp.status_code == 200
        body = resp.json()
        assert body["attemptId"] == attempt_id
        # No alignment → segment not in aligned_segment_ids → evidence_refs is empty
        assert body["status"] == "insufficient_data"
        assert body["evidenceRefs"] == []
        # failure_point comes from first segment payload
        assert body["failurePoint"]["failureType"] == "step_skip"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_get_attempt_replay_with_alignment_returns_ok():
    """
    GET /api/v1/teaching/attempts/{id}/replay with timeline + segments + alignment
    → 200 status="ok" with evidence_refs.
    覆盖: get_attempt_replay full success path lines 594-647.
    """
    client, sf = _build_client()
    try:
        _, _, attempt_id, _ = asyncio.run(_seed_attempt(sf, student_id=5004))

        async def seed_full_replay_data():
            async with sf() as session:
                timeline = MultimodalTimeline(
                    scope_type="attempt",
                    scope_id=str(attempt_id),
                )
                session.add(timeline)
                await session.flush()

                segment = TimelineSegment(
                    timeline_id=timeline.id,
                    segment_type="event",
                    ref_id="ref-aligned-001",
                    start_ts_ms=1000,
                    end_ts_ms=2000,
                    payload={"step_id": 10, "failure_type": "timeout"},
                )
                session.add(segment)
                await session.flush()

                alignment = AlignmentMap(
                    timeline_id=timeline.id,
                    anchor_key="anchor-001",
                    segment_id=segment.id,
                    ref_id="ref-aligned-001",
                    score=0.9,
                )
                session.add(alignment)
                await session.commit()
                return timeline.id, segment.id

        asyncio.run(seed_full_replay_data())

        resp = client.get(f"/api/v1/teaching/attempts/{attempt_id}/replay")
        assert resp.status_code == 200
        body = resp.json()
        assert body["attemptId"] == attempt_id
        assert body["status"] == "ok"
        assert body["supplementPlan"] == []
        assert len(body["evidenceRefs"]) == 1
        ref = body["evidenceRefs"][0]
        assert ref["refId"] == "ref-aligned-001"
        assert ref["startTsMs"] == 1000
        assert ref["endTsMs"] == 2000
        assert isinstance(ref["timelineId"], int)
        assert isinstance(ref["segmentId"], int)
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_get_attempt_replay_student_role_wrong_id_returns_404():
    """
    GET /api/v1/teaching/attempts/{id}/replay with student role and mismatched student_id
    → 404 ReadAccessDeniedError.
    覆盖: get_attempt_replay student role check lines 488-498.
    """
    client, sf = _build_client()
    try:
        _, _, attempt_id, _ = asyncio.run(_seed_attempt(sf, student_id=5005))

        resp = client.get(
            f"/api/v1/teaching/attempts/{attempt_id}/replay",
            headers={"X-RMOS-Role": "student", "X-User-ID": "9999"},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error_type"] == "ReadAccessDeniedError"
        assert body["details"]["code"] == "READ_ACCESS_DENIED"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_get_attempt_replay_student_role_no_user_id_returns_404():
    """
    GET /api/v1/teaching/attempts/{id}/replay with student role and no X-User-ID
    → 404 (actor_user_id is None).
    覆盖: get_attempt_replay student None actor_user_id path lines 489-498.
    """
    client, sf = _build_client()
    try:
        _, _, attempt_id, _ = asyncio.run(_seed_attempt(sf, student_id=5006))

        resp = client.get(
            f"/api/v1/teaching/attempts/{attempt_id}/replay",
            headers={"X-RMOS-Role": "student"},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error_type"] == "ReadAccessDeniedError"
        assert body["details"]["code"] == "READ_ACCESS_DENIED"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_get_attempt_replay_teacher_wrong_class_returns_404():
    """
    GET /api/v1/teaching/attempts/{id}/replay with teacher role but teacher not owner
    → 404 ReadAccessDeniedError (teacher_course_scope_mismatch).
    覆盖: get_attempt_replay teacher role check lines 499-525.
    """
    client, sf = _build_client()
    try:
        teacher_id = 100
        _, _, attempt_id, _ = asyncio.run(_seed_attempt(sf, teacher_id=teacher_id, student_id=5007))

        # 用不同的 teacher_id (200 != 100) → scope mismatch
        resp = client.get(
            f"/api/v1/teaching/attempts/{attempt_id}/replay",
            headers={"X-RMOS-Role": "teacher", "X-User-ID": "200"},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error_type"] == "ReadAccessDeniedError"
        assert body["details"]["code"] == "READ_ACCESS_DENIED"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_get_attempt_replay_teacher_no_user_id_returns_404():
    """
    GET /api/v1/teaching/attempts/{id}/replay with teacher role but no X-User-ID
    → 404 (invalid_actor_teacher_id).
    覆盖: get_attempt_replay teacher None actor_user_id path lines 500-509.
    """
    client, sf = _build_client()
    try:
        _, _, attempt_id, _ = asyncio.run(_seed_attempt(sf, student_id=5008))

        resp = client.get(
            f"/api/v1/teaching/attempts/{attempt_id}/replay",
            headers={"X-RMOS-Role": "teacher"},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error_type"] == "ReadAccessDeniedError"
        assert body["details"]["code"] == "READ_ACCESS_DENIED"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_get_attempt_replay_segment_no_ref_id_skipped():
    """
    GET /api/v1/teaching/attempts/{id}/replay where segment has no ref_id
    → evidence_refs is empty (segment is skipped), status="insufficient_data".
    覆盖: replay inner loop `if not segment.ref_id: continue` lines 598-600.
    """
    client, sf = _build_client()
    try:
        _, _, attempt_id, _ = asyncio.run(_seed_attempt(sf, student_id=5009))

        async def seed_timeline_segment_no_ref():
            async with sf() as session:
                timeline = MultimodalTimeline(
                    scope_type="attempt",
                    scope_id=str(attempt_id),
                )
                session.add(timeline)
                await session.flush()

                segment = TimelineSegment(
                    timeline_id=timeline.id,
                    segment_type="event",
                    ref_id=None,  # no ref_id
                    start_ts_ms=1000,
                    end_ts_ms=2000,
                    payload={},
                )
                session.add(segment)
                await session.flush()

                alignment = AlignmentMap(
                    timeline_id=timeline.id,
                    anchor_key="anchor-no-ref",
                    segment_id=segment.id,
                    ref_id=None,
                    score=1.0,
                )
                session.add(alignment)
                await session.commit()

        asyncio.run(seed_timeline_segment_no_ref())

        resp = client.get(f"/api/v1/teaching/attempts/{attempt_id}/replay")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "insufficient_data"
        assert body["evidenceRefs"] == []
        # supplement_plan should mention missing_replayable_refs
        assert len(body["supplementPlan"]) == 1
        assert body["supplementPlan"][0]["dataType"] == "evidence_ref"
    finally:
        client.close()
        app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# POST /evidence_cards  — 权限检查 + timeline 校验
# ─────────────────────────────────────────────────────────────────────────────

def test_create_evidence_card_attempt_not_found_returns_404():
    """
    POST /api/v1/evidence_cards with non-existent attempt_id → 404 HTTPException.
    覆盖: create_evidence_card attempt not found lines 665-667.
    """
    client, _ = _build_client()
    try:
        resp = client.post(
            "/api/v1/evidence_cards",
            json={"attemptId": 99999, "cardType": "failure_point"},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error_type"] == "ResourceNotFoundError"
        assert body["details"] is not None
        assert "99999" in str(body["details"])
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_create_evidence_card_student_role_denied():
    """
    POST /api/v1/evidence_cards with no role header (default) and role != admin/teacher
    → 403 WriteAccessDeniedError (missing_role:teacher_or_admin).
    BUG NOTE: 路由未传 role 时默认走 `elif role != "admin"` 分支 → 403。
    覆盖: create_evidence_card missing role check lines 698-707.
    """
    client, sf = _build_client()
    try:
        _, _, attempt_id, _ = asyncio.run(_seed_attempt(sf, student_id=6001))

        resp = client.post(
            "/api/v1/evidence_cards",
            # 无 X-RMOS-Role 且无 X-User-ID → role="" → != "admin" → 403
            json={"attemptId": attempt_id, "cardType": "failure_point"},
        )
        assert resp.status_code == 403
        body = resp.json()
        assert body["error_type"] == "WriteAccessDeniedError"
        assert body["details"]["code"] == "WRITE_ACCESS_DENIED"
        assert body["details"]["details"]["reason"] == "missing_role:teacher_or_admin"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_create_evidence_card_teacher_no_user_id_denied():
    """
    POST /api/v1/evidence_cards with X-RMOS-Role: teacher but no X-User-ID
    → 403 WriteAccessDeniedError (invalid_actor_teacher_id).
    覆盖: create_evidence_card teacher role None actor_user_id path lines 671-681.
    """
    client, sf = _build_client()
    try:
        _, _, attempt_id, _ = asyncio.run(_seed_attempt(sf, student_id=6002))

        resp = client.post(
            "/api/v1/evidence_cards",
            headers={"X-RMOS-Role": "teacher"},
            json={"attemptId": attempt_id, "cardType": "failure_point"},
        )
        assert resp.status_code == 403
        body = resp.json()
        assert body["error_type"] == "WriteAccessDeniedError"
        assert body["details"]["code"] == "WRITE_ACCESS_DENIED"
        assert body["details"]["details"]["reason"] == "invalid_actor_teacher_id"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_create_evidence_card_teacher_wrong_class_denied():
    """
    POST /api/v1/evidence_cards with teacher role but teacher not class owner
    → 403 WriteAccessDeniedError (teacher_attempt_scope_mismatch).
    覆盖: create_evidence_card teacher scope check lines 682-697.
    """
    client, sf = _build_client()
    try:
        teacher_id = 101
        _, _, attempt_id, _ = asyncio.run(_seed_attempt(sf, teacher_id=teacher_id, student_id=6003))

        # 不同 teacher_id (999 != 101) → scope mismatch
        resp = client.post(
            "/api/v1/evidence_cards",
            headers={"X-RMOS-Role": "teacher", "X-User-ID": "999"},
            json={"attemptId": attempt_id, "cardType": "failure_point"},
        )
        assert resp.status_code == 403
        body = resp.json()
        assert body["error_type"] == "WriteAccessDeniedError"
        assert body["details"]["details"]["reason"] == "teacher_attempt_scope_mismatch"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_create_evidence_card_admin_no_timeline_returns_409():
    """
    POST /api/v1/evidence_cards with admin role but no timeline
    → 409 BusinessRuleViolation (TIMELINE_007_MISSING_TIMELINE).
    覆盖: create_evidence_card timeline is None branch lines 718-722.
    """
    client, sf = _build_client()
    try:
        _, _, attempt_id, _ = asyncio.run(_seed_attempt(sf, student_id=6004))

        resp = client.post(
            "/api/v1/evidence_cards",
            headers={"X-RMOS-Role": "admin"},
            json={"attemptId": attempt_id, "cardType": "failure_point"},
        )
        assert resp.status_code == 409
        body = resp.json()
        assert body["error_type"] == "BusinessRuleViolation"
        assert body["details"]["code"] == "TIMELINE_007_MISSING_TIMELINE"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_create_evidence_card_admin_no_segments_returns_409():
    """
    POST /api/v1/evidence_cards with admin role, timeline exists but no matching segments
    → 409 BusinessRuleViolation (TIMELINE_007_MISSING_REFERENCES).
    覆盖: create_evidence_card segments empty branch lines 732-738.
    """
    client, sf = _build_client()
    try:
        _, _, attempt_id, _ = asyncio.run(_seed_attempt(sf, student_id=6005))

        async def seed_timeline_no_segments():
            async with sf() as session:
                timeline = MultimodalTimeline(
                    scope_type="attempt",
                    scope_id=str(attempt_id),
                )
                session.add(timeline)
                await session.commit()

        asyncio.run(seed_timeline_no_segments())

        resp = client.post(
            "/api/v1/evidence_cards",
            headers={"X-RMOS-Role": "admin"},
            json={"attemptId": attempt_id, "cardType": "failure_point"},
        )
        assert resp.status_code == 409
        body = resp.json()
        assert body["error_type"] == "BusinessRuleViolation"
        assert body["details"]["code"] == "TIMELINE_007_MISSING_REFERENCES"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_create_evidence_card_admin_with_segments_returns_201():
    """
    POST /api/v1/evidence_cards with admin role, timeline + matching segments
    → 201 EvidenceCardResponse.
    覆盖: create_evidence_card success path lines 739-788.
    """
    client, sf = _build_client()
    try:
        _, _, attempt_id, _ = asyncio.run(_seed_attempt(sf, student_id=6006))

        async def seed_timeline_with_event_segment():
            async with sf() as session:
                timeline = MultimodalTimeline(
                    scope_type="attempt",
                    scope_id=str(attempt_id),
                )
                session.add(timeline)
                await session.flush()

                segment = TimelineSegment(
                    timeline_id=timeline.id,
                    segment_type="event",  # in ("event", "log", "snapshot")
                    ref_id="ref-card-001",
                    start_ts_ms=1000,
                    end_ts_ms=2000,
                    payload={"snippet": "test event snippet"},
                )
                session.add(segment)
                await session.commit()

        asyncio.run(seed_timeline_with_event_segment())

        resp = client.post(
            "/api/v1/evidence_cards",
            headers={"X-RMOS-Role": "admin"},
            json={"attemptId": attempt_id, "cardType": "failure_point"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["attemptId"] == attempt_id
        assert body["cardType"] == "failure_point"
        assert body["title"] == "failure_point 证据卡片"
        assert body["summary"] == "基于时间轴日志/事件/快照聚合生成"
        assert isinstance(body["evidenceCardId"], int)
        assert len(body["references"]) == 1
        ref = body["references"][0]
        assert ref["refId"] == "ref-card-001"
        assert ref["type"] == "event"
        assert ref["snippet"] == "test event snippet"
        assert ref["timestampMs"] == 1000
    finally:
        client.close()
        app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /attempts/{attempt_id}  — BusinessRuleViolation + ResourceNotFoundError
# ─────────────────────────────────────────────────────────────────────────────

def test_update_attempt_status_not_found_returns_404():
    """
    PATCH /api/v1/attempts/9999 → 404 HTTPException (via _raise_not_found).
    覆盖: update_attempt_status ResourceNotFoundError branch lines 804-807.
    """
    client, _ = _build_client()
    try:
        resp = client.patch(
            "/api/v1/attempts/9999",
            json={"status": "completed"},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error_type"] == "ResourceNotFoundError"
        assert body["details"] is not None
        assert "9999" in str(body["details"])
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_update_attempt_status_invalid_transition_returns_409():
    """
    PATCH /api/v1/attempts/{id} with invalid status transition (graded → completed)
    → 409 BusinessRuleViolation (INVALID_ATTEMPT_STATUS_TRANSITION).
    覆盖: update_attempt_status BusinessRuleViolation branch lines 804-807.
    """
    client, sf = _build_client()
    try:
        _, _, attempt_id, _ = asyncio.run(_seed_attempt(sf, student_id=7001))

        # First complete it
        client.patch(f"/api/v1/attempts/{attempt_id}", json={"status": "completed"})
        # Then grade it
        client.post(f"/api/v1/attempts/{attempt_id}/grade", json={"score": 85.0})
        # Now try to complete a graded attempt → invalid transition
        resp = client.patch(
            f"/api/v1/attempts/{attempt_id}",
            json={"status": "completed"},
        )
        assert resp.status_code == 409
        body = resp.json()
        assert body["error_type"] == "BusinessRuleViolation"
        assert body["details"]["code"] == "INVALID_ATTEMPT_STATUS_TRANSITION"
    finally:
        client.close()
        app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# POST /attempts/{attempt_id}/grade  — error paths
# ─────────────────────────────────────────────────────────────────────────────

def test_grade_attempt_not_found_returns_404():
    """
    POST /api/v1/attempts/9999/grade → 404 HTTPException (via _raise_not_found).
    覆盖: grade_attempt ResourceNotFoundError branch lines 823-826.
    """
    client, _ = _build_client()
    try:
        resp = client.post(
            "/api/v1/attempts/9999/grade",
            json={"score": 80.0},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error_type"] == "ResourceNotFoundError"
        assert body["details"] is not None
        assert "9999" in str(body["details"])
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_grade_attempt_not_completed_returns_409():
    """
    POST /api/v1/attempts/{id}/grade when attempt is "in_progress"
    → 409 BusinessRuleViolation (ATTEMPT_NOT_COMPLETED).
    覆盖: grade_attempt BusinessRuleViolation branch lines 823-826.
    """
    client, sf = _build_client()
    try:
        _, _, attempt_id, _ = asyncio.run(_seed_attempt(sf, student_id=8001))

        resp = client.post(
            f"/api/v1/attempts/{attempt_id}/grade",
            json={"score": 90.0},
        )
        assert resp.status_code == 409
        body = resp.json()
        assert body["error_type"] == "BusinessRuleViolation"
        assert body["details"]["code"] == "ATTEMPT_NOT_COMPLETED"
    finally:
        client.close()
        app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# GET /attempts/{attempt_id}/evidence  — error paths
# ─────────────────────────────────────────────────────────────────────────────

def test_get_attempt_evidence_not_found_returns_404():
    """
    GET /api/v1/attempts/9999/evidence → 404 HTTPException (via _raise_not_found).
    覆盖: get_attempt_evidence attempt not-found branch lines 841-842.
    """
    client, _ = _build_client()
    try:
        resp = client.get("/api/v1/attempts/9999/evidence")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error_type"] == "ResourceNotFoundError"
        assert body["details"] is not None
        assert "9999" in str(body["details"])
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_get_attempt_evidence_no_task_no_link_returns_404():
    """
    GET /api/v1/attempts/{id}/evidence when attempt has no task and no evidence link
    → 404 HTTPException with "attempt未关联task，无法生成证据" in message.
    覆盖: get_attempt_evidence task_id is None branch lines 865-866.
    """
    client, sf = _build_client()
    try:
        _, _, attempt_id, _ = asyncio.run(_seed_attempt(sf, student_id=9001, task_id=None))

        resp = client.get(f"/api/v1/attempts/{attempt_id}/evidence")
        assert resp.status_code == 404
        body = resp.json()
        # HTTPException from `raise HTTPException(status_code=404, detail="attempt未关联task...")`
        assert body["error_type"] == "HTTPException"
        assert body["message"] == "attempt未关联task，无法生成证据"
        assert body["details"] is None
    finally:
        client.close()
        app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# GET /attempts/{attempt_id}/diagnosis  — error paths
# ─────────────────────────────────────────────────────────────────────────────

def test_get_attempt_diagnosis_not_found_returns_404():
    """
    GET /api/v1/attempts/9999/diagnosis → 404 HTTPException (via _raise_not_found).
    覆盖: get_attempt_diagnosis ResourceNotFoundError branch lines 900-901.
    """
    client, _ = _build_client()
    try:
        resp = client.get("/api/v1/attempts/9999/diagnosis")
        assert resp.status_code == 404
        body = resp.json()
        # _raise_not_found → HTTPException → http_exception_handler
        assert body["error_type"] == "ResourceNotFoundError"
        assert body["details"] is not None
        assert "9999" in str(body["details"])
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_get_attempt_diagnosis_no_task_returns_404():
    """
    GET /api/v1/attempts/{id}/diagnosis when attempt has no linked task
    → 404（而非 500）。

    修复 P0#7 后：attempt 未关联 task（task_id 为空）是"无诊断可用"的数据状态，
    endpoint 对 EvidenceFallbackError(task_id=None) 返回 404 而非误报服务器 500。
    """
    client, sf = _build_client()
    try:
        # Attempt with no task_id → diagnosis service will raise EvidenceFallbackError(task_id=None)
        _, _, attempt_id, _ = asyncio.run(_seed_attempt(sf, student_id=9002, task_id=None))

        resp = client.get(f"/api/v1/attempts/{attempt_id}/diagnosis")
        assert resp.status_code == 404
        body = resp.json()
        # 直接 raise HTTPException(404, ...) → http_exception_handler → error_type="HTTPException"
        assert body["error_type"] == "HTTPException"
        assert "诊断" in body["message"]
    finally:
        client.close()
        app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# 额外覆盖：_parse_user_id / _to_int_or_none 辅助函数
# ─────────────────────────────────────────────────────────────────────────────

def test_parse_user_id_empty_string_returns_none_via_access_check():
    """
    X-User-ID: "  " (whitespace) with student role → _parse_user_id返回None → 404.
    覆盖: _parse_user_id lines 89-92 (empty value returns None).
    """
    client, sf = _build_client()
    try:
        _, _, attempt_id, _ = asyncio.run(_seed_attempt(sf, student_id=10001))

        resp = client.get(
            f"/api/v1/attempts/{attempt_id}",
            headers={"X-RMOS-Role": "student", "X-User-ID": "  "},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error_type"] == "ReadAccessDeniedError"
        assert body["details"]["code"] == "READ_ACCESS_DENIED"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_parse_user_id_non_integer_returns_none_via_access_check():
    """
    X-User-ID: "abc" with student role → _parse_user_id returns None → 404.
    覆盖: _parse_user_id ValueError branch lines 95-96.
    """
    client, sf = _build_client()
    try:
        _, _, attempt_id, _ = asyncio.run(_seed_attempt(sf, student_id=10002))

        resp = client.get(
            f"/api/v1/attempts/{attempt_id}",
            headers={"X-RMOS-Role": "student", "X-User-ID": "abc"},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["error_type"] == "ReadAccessDeniedError"
        assert body["details"]["code"] == "READ_ACCESS_DENIED"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_to_int_or_none_via_replay_segment_payload():
    """
    GET /api/v1/teaching/attempts/{id}/replay — payload with step_id as string
    → _to_int_or_none converts it or returns None.
    覆盖: _to_int_or_none success path lines 104-105.
    """
    client, sf = _build_client()
    try:
        _, _, attempt_id, _ = asyncio.run(_seed_attempt(sf, student_id=10003))

        async def seed_segment_with_typed_payload():
            async with sf() as session:
                timeline = MultimodalTimeline(
                    scope_type="attempt",
                    scope_id=str(attempt_id),
                )
                session.add(timeline)
                await session.flush()

                segment = TimelineSegment(
                    timeline_id=timeline.id,
                    segment_type="event",
                    ref_id=None,
                    start_ts_ms=500,
                    end_ts_ms=1500,
                    payload={
                        "step_id": "5",        # string → _to_int_or_none → 5
                        "event_id": "10",      # string → _to_int_or_none → 10
                        "failure_type": "op_error",
                        "rule_hit": "RULE_42",
                    },
                )
                session.add(segment)
                await session.commit()

        asyncio.run(seed_segment_with_typed_payload())

        resp = client.get(f"/api/v1/teaching/attempts/{attempt_id}/replay")
        assert resp.status_code == 200
        body = resp.json()
        fp = body["failurePoint"]
        assert fp["stepId"] == 5        # string "5" → int 5
        assert fp["eventId"] == 10      # string "10" → int 10
        assert fp["failureType"] == "op_error"
        assert fp["ruleHit"] == "RULE_42"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_to_int_or_none_non_convertible_via_replay():
    """
    _to_int_or_none with non-numeric value → returns None.
    覆盖: _to_int_or_none ValueError/TypeError branch lines 101-105.
    """
    client, sf = _build_client()
    try:
        _, _, attempt_id, _ = asyncio.run(_seed_attempt(sf, student_id=10004))

        async def seed_segment_bad_ids():
            async with sf() as session:
                timeline = MultimodalTimeline(
                    scope_type="attempt",
                    scope_id=str(attempt_id),
                )
                session.add(timeline)
                await session.flush()

                segment = TimelineSegment(
                    timeline_id=timeline.id,
                    segment_type="event",
                    ref_id=None,
                    start_ts_ms=100,
                    end_ts_ms=200,
                    payload={
                        "step_id": "not-an-int",  # → _to_int_or_none → None
                        "event_id": None,          # → _to_int_or_none(None) → None
                        "failure_type": "parse_fail",
                    },
                )
                session.add(segment)
                await session.commit()

        asyncio.run(seed_segment_bad_ids())

        resp = client.get(f"/api/v1/teaching/attempts/{attempt_id}/replay")
        assert resp.status_code == 200
        body = resp.json()
        fp = body["failurePoint"]
        assert fp["stepId"] is None     # non-int string → None
        assert fp["eventId"] is None    # None → None
        assert fp["failureType"] == "parse_fail"
    finally:
        client.close()
        app.dependency_overrides.clear()
