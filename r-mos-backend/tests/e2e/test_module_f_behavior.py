"""RMOS-S3-004 模块 F：教学路由覆盖盘点与当前行为安全网。

本文件只通过真实 HTTP 请求或 AST 盘点固定当前事实；第一步不修改生产代码。
疑似缺陷按当前返回结果断言，留待模块 F 后续改造处置。
"""
from __future__ import annotations

import ast
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.evidence import EvidenceBundle
from app.models.teaching import EvidenceLink
from main import app
from tests.e2e.helpers import register_and_login


pytestmark = [pytest.mark.e2e, pytest.mark.characterization]

MODULE_F_ROUTES = {
    ("GET", "/api/v1/guidance-policies"),
    ("POST", "/api/v1/guidance-policies"),
    ("GET", "/api/v1/guidance-policies/{policy_id}"),
    ("GET", "/api/v1/classes"),
    ("POST", "/api/v1/classes"),
    ("GET", "/api/v1/classes/{class_id}"),
    ("PATCH", "/api/v1/classes/{class_id}"),
    ("GET", "/api/v1/courses"),
    ("POST", "/api/v1/courses"),
    ("GET", "/api/v1/courses/{course_id}"),
    ("GET", "/api/v1/enrollments"),
    ("POST", "/api/v1/enrollments"),
    ("GET", "/api/v1/assignments"),
    ("POST", "/api/v1/assignments"),
    ("GET", "/api/v1/assignments/{assignment_id}"),
    ("GET", "/api/v1/assignments/{assignment_id}/attempts"),
    ("POST", "/api/v1/assignments/{assignment_id}/attempts"),
    ("GET", "/api/v1/attempts/{attempt_id}"),
    ("PATCH", "/api/v1/attempts/{attempt_id}"),
    ("POST", "/api/v1/attempts/{attempt_id}/grade"),
    ("GET", "/api/v1/attempts/{attempt_id}/evidence"),
    ("GET", "/api/v1/attempts/{attempt_id}/diagnosis"),
    ("GET", "/api/v1/teaching/attempts/{attempt_id}/replay"),
    ("POST", "/api/v1/evidence_cards"),
}


def _act_as(client: TestClient, login: dict) -> None:
    client.headers["Authorization"] = f"Bearer {login['access_token']}"


@pytest.fixture()
def cross_class_context(
    e2e_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> dict:
    client, session_factory = e2e_env
    teacher_a_id, _, teacher_a_login = register_and_login(
        client, email_prefix="module_f_teacher_a"
    )
    teacher_b_id, _, teacher_b_login = register_and_login(
        client, email_prefix="module_f_teacher_b"
    )
    student_id, _, student_login = register_and_login(
        client,
        email_prefix="module_f_student_b",
        role="student",
        teacher_id=teacher_b_id,
    )

    _act_as(client, teacher_b_login)
    class_response = client.post(
        "/api/v1/classes",
        json={"name": "教师 B 的班级", "teacherId": teacher_b_id},
    )
    assert class_response.status_code == 201
    class_body = class_response.json()
    assert class_body["name"] == "教师 B 的班级"
    assert class_body["teacherId"] == teacher_b_id
    class_id = class_body["id"]
    course_response = client.post(
        "/api/v1/courses",
        json={"classId": class_id, "name": "教师 B 的课程"},
    )
    assert course_response.status_code == 201
    course_body = course_response.json()
    assert course_body["classId"] == class_id
    assert course_body["name"] == "教师 B 的课程"
    enrollment_response = client.post(
        "/api/v1/enrollments",
        json={"classId": class_id, "studentId": student_id},
    )
    assert enrollment_response.status_code == 201
    assert enrollment_response.json()["classId"] == class_id
    assert enrollment_response.json()["studentId"] == student_id
    assignment_response = client.post(
        "/api/v1/assignments",
        json={"classId": class_id, "title": "教师 B 的作业"},
    )
    assert assignment_response.status_code == 201
    assignment_body = assignment_response.json()
    assert assignment_body["classId"] == class_id
    assert assignment_body["title"] == "教师 B 的作业"

    _act_as(client, student_login)
    attempt_response = client.post(
        f"/api/v1/assignments/{assignment_body['id']}/attempts",
        json={"studentId": student_id},
    )
    assert attempt_response.status_code == 201
    attempt_body = attempt_response.json()
    assert attempt_body["assignmentId"] == assignment_body["id"]
    assert attempt_body["studentId"] == student_id

    async def _seed_evidence() -> str:
        async with session_factory() as session:
            bundle_id = str(uuid4())
            bundle = EvidenceBundle(
                id=bundle_id,
                bundle_type="sop_execution",
                bundle_hash="f" * 64,
                bundle_hash_algo="sha256",
                observed_time_start=datetime.now(timezone.utc),
                ingest_time=datetime.now(timezone.utc),
                is_sealed=True,
                sealed_at=datetime.now(timezone.utc),
                machine_tags={"error_count": 0, "skip_count": 0, "duration_ms": 0},
            )
            session.add(bundle)
            await session.flush()
            session.add(
                EvidenceLink(
                    bundle_id=bundle_id,
                    attempt_id=attempt_body["id"],
                    student_id=student_id,
                    class_id=class_id,
                )
            )
            await session.commit()
            return bundle_id

    bundle_id = asyncio.run(_seed_evidence())
    return {
        "client": client,
        "teacher_a_id": teacher_a_id,
        "teacher_a_login": teacher_a_login,
        "teacher_b_id": teacher_b_id,
        "teacher_b_login": teacher_b_login,
        "student_id": student_id,
        "student_login": student_login,
        "class_id": class_id,
        "course_id": course_body["id"],
        "assignment_id": assignment_body["id"],
        "attempt_id": attempt_body["id"],
        "bundle_id": bundle_id,
    }


def test_module_f_route_census_uses_runtime_app() -> None:
    """从 main:app 的 APIRoute 枚举，锁定模块 F 当前真实注册的 24 条路由。"""
    actual = {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        and route.endpoint.__module__
        in {"app.api.v1.endpoints.teaching", "app.api.v1.endpoints.teaching_roster"}
        for method in route.methods
    }
    assert actual == MODULE_F_ROUTES


def test_timeline_tables_still_have_no_application_writer_by_ast() -> None:
    """S1-001 裁决二：三张时间线表当前仍无应用写入路径，状态为尚未实现。"""
    app_root = Path(__file__).parents[2] / "app"
    model_names = {"AlignmentMap", "MultimodalTimeline", "TimelineSegment"}
    writer_calls: set[tuple[str, str]] = set()
    attribute_writes: set[tuple[str, str]] = set()

    for source_path in app_root.rglob("*.py"):
        if source_path.parts[-2] == "models":
            continue
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        relative_path = source_path.relative_to(app_root.parent).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call_text = ast.unparse(node.func)
                call_name = call_text.rsplit(".", 1)[-1]
                if call_name in model_names:
                    writer_calls.add((relative_path, call_name))
                if call_name in {"insert", "update", "delete"} and any(
                    model_name in ast.unparse(node) for model_name in model_names
                ):
                    writer_calls.add((relative_path, ast.unparse(node)))
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if not isinstance(target, ast.Attribute):
                        continue
                    root = ast.unparse(target.value).lower()
                    if root in {"timeline", "segment", "alignment"}:
                        attribute_writes.add((relative_path, ast.unparse(target)))

    assert writer_calls == set()
    assert attribute_writes == set()


def test_assignment_attempt_writer_census_uses_ast() -> None:
    """S1-001 §2.3：assignment_attempts 当前仍由两个服务文件直接写。"""
    app_root = Path(__file__).parents[2] / "app"
    writes: set[tuple[str, str, str]] = set()

    for source_path in app_root.rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        if "AssignmentAttempt" not in source or source_path.parts[-2] == "models":
            continue
        relative_path = source_path.relative_to(app_root.parent).as_posix()
        tree = ast.parse(source)
        scope: list[str] = []

        class WriterVisitor(ast.NodeVisitor):
            def _visit_scope(
                self, node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
            ) -> None:
                scope.append(node.name)
                self.generic_visit(node)
                scope.pop()

            visit_ClassDef = _visit_scope
            visit_FunctionDef = _visit_scope
            visit_AsyncFunctionDef = _visit_scope

            def visit_Call(self, node: ast.Call) -> None:
                if ast.unparse(node.func).rsplit(".", 1)[-1] == "AssignmentAttempt":
                    writes.add((relative_path, ".".join(scope), "construct"))
                self.generic_visit(node)

            def visit_Assign(self, node: ast.Assign) -> None:
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and ast.unparse(target.value) == "attempt":
                        writes.add((relative_path, ".".join(scope), ast.unparse(target)))
                self.generic_visit(node)

        WriterVisitor().visit(tree)

    assert writes == {
        ("app/services/teaching_service.py", "TeachingService.create_attempt", "construct"),
        (
            "app/services/teaching_service.py",
            "TeachingService.update_attempt_status",
            "attempt.status",
        ),
        (
            "app/services/teaching_service.py",
            "TeachingService.update_attempt_status",
            "attempt.abandoned_at",
        ),
        (
            "app/services/teaching_service.py",
            "TeachingService.grade_attempt",
            "attempt.status",
        ),
        (
            "app/services/teaching_service.py",
            "TeachingService.grade_attempt",
            "attempt.score",
        ),
        (
            "app/services/teaching_service.py",
            "TeachingService.grade_attempt",
            "attempt.graded_at",
        ),
        (
            "app/services/evidence_engine.py",
            "EvidenceEngine._create_link",
            "attempt.evidence_bundle_id",
        ),
    }


def test_get_guidance_policy_returns_created_content(e2e_env) -> None:
    """补齐此前只有列表成功和详情 404、没有详情成功响应内容的缺口。"""
    client, _ = e2e_env
    created = client.post(
        "/api/v1/guidance-policies",
        json={"name": "模块 F 详情策略", "baseMode": "exam", "maxRetryCount": 2},
    )
    assert created.status_code == 201

    response = client.get(f"/api/v1/guidance-policies/{created.json()['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "模块 F 详情策略"
    assert response.json()["baseMode"] == "exam"
    assert response.json()["maxRetryCount"] == 2


def test_get_class_missing_returns_404(e2e_env) -> None:
    """补齐 GET 班级详情此前没有真实不存在编号边界的缺口。"""
    client, _ = e2e_env
    response = client.get("/api/v1/classes/99999999")
    assert response.status_code == 404
    assert response.json()["error_type"] == "ResourceNotFoundError"


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    (
        ("post", "/api/v1/guidance-policies", {}),
        ("post", "/api/v1/classes", {}),
        ("patch", "/api/v1/classes/99999999", {"teacherId": "not-an-integer"}),
        ("post", "/api/v1/courses", {"classId": "not-an-integer"}),
        ("post", "/api/v1/enrollments", {"classId": 1, "studentId": "not-an-integer"}),
        ("post", "/api/v1/assignments", {"classId": 1}),
        (
            "post",
            "/api/v1/assignments/99999999/attempts",
            {"studentId": "not-an-integer"},
        ),
        ("patch", "/api/v1/attempts/99999999", {"status": ["completed"]}),
        ("post", "/api/v1/attempts/99999999/grade", {"score": "not-a-number"}),
    ),
)
def test_teaching_write_route_rejects_invalid_body_with_422(
    e2e_env, method: str, path: str, payload: dict
) -> None:
    """补齐九条写路由的非法输入边界；证据卡片的 422 已由模块 H 覆盖。"""
    client, _ = e2e_env
    response = getattr(client, method)(path, json=payload)
    assert response.status_code == 422, response.text
    assert response.json()["error_type"] == "ValidationError"


def test_attempt_status_rejects_other_student_and_allows_owner(cross_class_context) -> None:
    """PATCH attempt 同时具备拒绝与放行证据，防止守卫被写成无条件拒绝。"""
    context = cross_class_context
    client = context["client"]
    _, _, outsider_login = register_and_login(
        client,
        email_prefix="module_f_status_outsider",
        role="student",
        teacher_id=context["teacher_a_id"],
    )

    _act_as(client, outsider_login)
    denied = client.patch(
        f"/api/v1/attempts/{context['attempt_id']}", json={"status": "completed"}
    )
    assert denied.status_code == 403
    assert denied.json()["error_type"] == "WriteAccessDeniedError"

    _act_as(client, context["student_login"])
    allowed = client.patch(
        f"/api/v1/attempts/{context['attempt_id']}", json={"status": "completed"}
    )
    assert allowed.status_code == 200
    assert allowed.json()["id"] == context["attempt_id"]
    assert allowed.json()["status"] == "completed"


def test_other_teacher_can_read_foreign_class_course_and_roster_current_behavior(
    cross_class_context,
) -> None:
    """这是当前行为，疑似缺陷 F-AUTH-01，待模块 F 改造时处置。

    同校但不带该班的教师当前可读取他人班级、课程和名单；按真实行为断言 200。
    """
    context = cross_class_context
    client = context["client"]
    _act_as(client, context["teacher_a_login"])

    classes = client.get("/api/v1/classes")
    assert classes.status_code == 200
    assert any(item["id"] == context["class_id"] for item in classes.json())

    teaching_class = client.get(f"/api/v1/classes/{context['class_id']}")
    assert teaching_class.status_code == 200
    assert teaching_class.json()["teacherId"] == context["teacher_b_id"]

    courses = client.get("/api/v1/courses", params={"class_id": context["class_id"]})
    assert courses.status_code == 200
    assert [item["id"] for item in courses.json()] == [context["course_id"]]

    course = client.get(f"/api/v1/courses/{context['course_id']}")
    assert course.status_code == 200
    assert course.json()["classId"] == context["class_id"]

    enrollments = client.get(
        "/api/v1/enrollments", params={"class_id": context["class_id"]}
    )
    assert enrollments.status_code == 200
    assert [item["studentId"] for item in enrollments.json()] == [context["student_id"]]


def test_other_teacher_can_read_foreign_assignment_and_attempt_current_behavior(
    cross_class_context,
) -> None:
    """这是当前行为，疑似缺陷 F-AUTH-02，待模块 F 改造时处置。

    同校但不带该班的教师当前可读取他人班级的作业和尝试；按真实行为断言 200。
    """
    context = cross_class_context
    client = context["client"]
    _act_as(client, context["teacher_a_login"])

    assignments = client.get(
        "/api/v1/assignments", params={"class_id": context["class_id"]}
    )
    assert assignments.status_code == 200
    assert [item["id"] for item in assignments.json()] == [context["assignment_id"]]

    assignment = client.get(f"/api/v1/assignments/{context['assignment_id']}")
    assert assignment.status_code == 200
    assert assignment.json()["classId"] == context["class_id"]

    attempts = client.get(
        f"/api/v1/assignments/{context['assignment_id']}/attempts"
    )
    assert attempts.status_code == 200
    assert [item["id"] for item in attempts.json()] == [context["attempt_id"]]
    assert attempts.json()[0]["studentId"] == context["student_id"]

    attempt = client.get(f"/api/v1/attempts/{context['attempt_id']}")
    assert attempt.status_code == 200
    assert attempt.json()["studentId"] == context["student_id"]


def test_other_teacher_can_read_foreign_evidence_and_diagnosis_current_behavior(
    cross_class_context,
) -> None:
    """这是当前行为，疑似缺陷 F-AUTH-03，待模块 F 改造时处置。

    证据读取只校验同校，诊断读取没有对象归属校验；按真实行为断言 200。
    """
    context = cross_class_context
    client = context["client"]
    _act_as(client, context["teacher_a_login"])

    evidence = client.get(f"/api/v1/attempts/{context['attempt_id']}/evidence")
    assert evidence.status_code == 200
    assert evidence.json()["bundleId"] == context["bundle_id"]
    assert evidence.json()["attemptId"] == context["attempt_id"]

    diagnosis = client.get(f"/api/v1/attempts/{context['attempt_id']}/diagnosis")
    assert diagnosis.status_code == 200
    assert diagnosis.json()["attemptId"] == context["attempt_id"]
    assert diagnosis.json()["diagnosisCode"] == "OK"


def test_teacher_can_grade_foreign_class_attempt_when_student_is_in_any_owned_class(
    cross_class_context,
) -> None:
    """这是当前行为，疑似缺陷 F-AUTH-04，待模块 F 改造时处置。

    评分只核实教师是否在任一自有班级带过该学生，没有绑定目标尝试所属班级。
    """
    context = cross_class_context
    client = context["client"]

    _act_as(client, context["teacher_a_login"])
    teacher_a_class = client.post(
        "/api/v1/classes",
        json={"name": "教师 A 的班级", "teacherId": context["teacher_a_id"]},
    )
    assert teacher_a_class.status_code == 201
    enrolled = client.post(
        "/api/v1/enrollments",
        json={
            "classId": teacher_a_class.json()["id"],
            "studentId": context["student_id"],
        },
    )
    assert enrolled.status_code == 201

    _act_as(client, context["student_login"])
    completed = client.patch(
        f"/api/v1/attempts/{context['attempt_id']}", json={"status": "completed"}
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"

    _act_as(client, context["teacher_a_login"])
    graded = client.post(
        f"/api/v1/attempts/{context['attempt_id']}/grade", json={"score": 91}
    )
    assert graded.status_code == 200
    assert graded.json()["status"] == "graded"
    assert graded.json()["score"] == 91
