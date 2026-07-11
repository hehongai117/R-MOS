"""
特征测试：app/api/v1/endpoints/training.py
目标：行覆盖率 ≥ 80%（Phase 2 safety-net）

测试策略：
- 复用 test_skill_governance_api.py 的基建（_build_client / _register_and_login）
- 每个路由至少一个测试，断言真实响应状态码与关键字段
- 覆盖正常路径 + 错误路径（404/400/409/500）
- 对 workbench 路由（需调 LLM/外部服务）注入 monkeypatch 锁定当前行为
"""
from __future__ import annotations

import asyncio
import io
import json
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.characterization
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models as app_models  # noqa: F401  # 确保模型全部注册
import app.api.v1.endpoints.training as training_endpoints
from app.core.database import get_db
from app.models.base import Base
from app.models.school import School
from app.models.skill_profile import StudentSkillProfile, StudentWeakStep
from app.models.training import SessionStepRecord, TrainingSession
from app.models.training_submission import TrainingSubmission
from app.models.user import User
from main import app

# onboarding 注册需要的白名单学校（测试统一使用）
TEST_SCHOOL_NAME = "测试学校"


# ─────────────────────────────────────────────────────────────────────────────
# 测试基建
# ─────────────────────────────────────────────────────────────────────────────

def _build_client(
    *, raise_server_exceptions: bool = True
) -> tuple[TestClient, async_sessionmaker]:
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
    return TestClient(app, raise_server_exceptions=raise_server_exceptions), session_factory


def _register_and_login(
    client: TestClient, *, email: str, password: str = "StrongPass123", full_name: str
) -> str:
    register_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
            "role": "teacher",
            "school_name": TEST_SCHOOL_NAME,
        },
    )
    assert register_resp.status_code == 201

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200
    return login_resp.json()["access_token"]


def _register_and_login_with_id(
    client: TestClient, *, email: str, password: str = "StrongPass123", full_name: str
) -> tuple[int, str]:
    """Register and login, return (user_id, token)."""
    register_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
            "role": "teacher",
            "school_name": TEST_SCHOOL_NAME,
        },
    )
    assert register_resp.status_code == 201
    user_id = int(register_resp.json()["user_id"])

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200
    return user_id, login_resp.json()["access_token"]


def _seed_training_data(session_factory: async_sessionmaker) -> dict:
    """Seed a user, session, step record, submission, and skill profile."""
    async def _seed() -> dict:
        async with session_factory() as session:
            user = User(
                email="char_student@example.com",
                password_hash="pbkdf2_sha256$dummy",
                full_name="Char Student",
                role="student",
            )
            session.add(user)
            await session.flush()

            training_session = TrainingSession(
                session_id="char-sess-001",
                project_id="char-proj-001",
                user_id=user.id,
                status="active",
                current_step=1,
                project_snapshot={"estimated_time": 60, "verdict_config": {"time_limit": 60}},
                total_duration=600,
                started_at=datetime.utcnow(),
            )
            session.add(training_session)

            step_record = SessionStepRecord(
                record_id="char-step-001",
                session_id=training_session.session_id,
                step_id="step-char-1",
                step_index=0,
                status="pass",
                attempt_count=1,
                tools_confirmed=[{"tool_id": "wrench", "status": "confirmed"}],
                duration_sec=120,
            )
            session.add(step_record)

            profile = StudentSkillProfile(
                user_id=user.id,
                overall_level=1,
                total_sessions=2,
                total_duration=1800,
                score_safety=Decimal("75.00"),
                score_procedure=Decimal("80.00"),
                score_precision=Decimal("70.00"),
                score_efficiency=Decimal("65.00"),
                score_tools=Decimal("85.00"),
            )
            session.add(profile)

            weak_step = StudentWeakStep(
                user_id=user.id,
                step_id="step-char-weak-1",
                sop_id="SOP-CHAR-01",
                fail_count=3,
                is_resolved=False,
                fail_tags=["missed_tool"],
            )
            session.add(weak_step)

            submission = TrainingSubmission(
                submission_id="char-sub-001",
                session_id=training_session.session_id,
                user_id=user.id,
                submit_type="manual",
                submitted_at=datetime.utcnow(),
                payload={
                    "session_id": training_session.session_id,
                    "steps_summary": [{"step_id": "step-char-1", "status": "pass", "attempt_count": 1}],
                    "total_duration": 600,
                    "project_snapshot": {"estimated_time": 60},
                },
                score=Decimal("82.00"),
                total_steps=1,
                completed_steps=1,
                failed_steps=0,
                total_duration=600,
                feedback={
                    "overall_score": 82.0,
                    "score_breakdown": {"total_score": 82.0},
                    "suggestions": ["巩固工具确认步骤"],
                    "next_learning_plan": "继续进阶",
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


# ─────────────────────────────────────────────────────────────────────────────
# POST /training/projects/generate — SSE 流式项目生成
# ─────────────────────────────────────────────────────────────────────────────

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


def test_generate_project_streams_completed_event(monkeypatch) -> None:
    """POST /training/projects/generate — 正常路径返回 200 + completed SSE 事件."""
    client, sf = _build_client()
    try:
        user_id, _token = _register_and_login_with_id(client, email="gen1@x.com", full_name="GEN1")

        async def _fake_generate(self, intent, uid):  # noqa: ANN001
            yield {
                "status": "completed",
                "project": SimpleNamespace(
                    project_id="proj-char-001",
                    title="模拟项目",
                    description="生成的项目",
                    estimated_time=30,
                    difficulty_cap="medium",
                ),
            }

        monkeypatch.setattr(
            "app.services.training.project_generator.ProjectGenerator.generate",
            _fake_generate,
        )

        resp = client.post(
            "/api/v1/training/projects/generate",
            json={
                "user_id": user_id,
                "robot_id": "ABB-IRB120",
                "difficulty": "medium",
                "focus_areas": ["safety"],
            },
        )
        assert resp.status_code == 200
        # SSE 流：Content-Type 应为 text/event-stream
        assert "text/event-stream" in resp.headers.get("content-type", "")
        events = _parse_sse_events(resp.text)
        completed_events = [e for e in events if e.get("status") == "completed"]
        assert len(completed_events) == 1
        assert completed_events[0]["project_id"] == "proj-char-001"
        assert completed_events[0]["project"]["title"] == "模拟项目"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_generate_project_exception_yields_error_event(monkeypatch) -> None:
    """POST /training/projects/generate — 生成器抛出异常时 SSE 流包含 status=error 事件（锁定当前行为）.

    覆盖 lines 355-357：except Exception 块中的 logger.error + error yield.
    """
    client, sf = _build_client()
    try:
        user_id, _token = _register_and_login_with_id(client, email="gen2@x.com", full_name="GEN2")

        async def _fake_generate_error(self, intent, uid):  # noqa: ANN001
            raise RuntimeError("模拟生成失败")
            yield  # make it a generator

        monkeypatch.setattr(
            "app.services.training.project_generator.ProjectGenerator.generate",
            _fake_generate_error,
        )

        resp = client.post(
            "/api/v1/training/projects/generate",
            json={"user_id": user_id, "difficulty": "easy"},
        )
        # 外层 StreamingResponse 仍返回 200（HTTP 头已发出），错误在 SSE 事件中体现
        assert resp.status_code == 200
        events = _parse_sse_events(resp.text)
        error_events = [e for e in events if e.get("status") == "error"]
        assert len(error_events) == 1
        # 错误消息包含原始异常文本
        assert "模拟生成失败" in error_events[0]["error"]
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# POST /training/workbench/draft — 需要 auth
# ─────────────────────────────────────────────────────────────────────────────

def test_generate_workbench_draft_success(monkeypatch) -> None:
    """POST /training/workbench/draft — 正常路径返回工作台草案（覆盖 lines 383-399）."""
    client, sf = _build_client()
    try:
        user_id, token = _register_and_login_with_id(client, email="wb1@x.com", full_name="WB1")

        fake_draft_payload = {
            "project": {
                "project_id": "wb-proj-001",
                "title": "工作台草案测试",
                "summary": "测试摘要",
                "progress_percent": 0,
                # session_id 将在 endpoint 中注入
            },
            "steps": [
                {
                    "id": "wb-step-001",
                    "step_index": 0,
                    "title": "安全检查",
                    "status": "pending",
                    "instruction": "检查电源",
                    "evidence_hint": "拍照记录",
                    "model_targets": [],
                    "tools": [],
                }
            ],
            "messages": [],
        }

        async def _fake_draft_generate(self, *, user_id, robot_model, robot_id, task_summary, focus_prompt):
            return fake_draft_payload

        monkeypatch.setattr(
            "app.services.training.workbench_draft_generator.TrainingWorkbenchDraftGenerator.generate",
            _fake_draft_generate,
        )

        resp = client.post(
            "/api/v1/training/workbench/draft",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "robot_model": "ABB-IRB120",
                "task_summary": "关节电机盖拆装",
                "focus_prompt": "强调工具确认",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        # project 字段：包含 session_id（由 endpoint 注入）、project_id、title、summary
        assert "project" in body
        assert body["project"]["project_id"] == "wb-proj-001"
        assert body["project"]["title"] == "工作台草案测试"
        # session_id 由 endpoint 创建后注入（非确定性 UUID，断言存在+非空）
        assert "session_id" in body["project"]
        assert body["project"]["session_id"]  # not empty
        # steps 返回列表
        assert "steps" in body
        assert len(body["steps"]) == 1
        assert body["steps"][0]["title"] == "安全检查"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_generate_workbench_draft_value_error_returns_400(monkeypatch) -> None:
    """POST /training/workbench/draft — ValueError 时返回 400（覆盖 line 392）."""
    client, sf = _build_client()
    try:
        user_id, token = _register_and_login_with_id(client, email="wb2@x.com", full_name="WB2")

        async def _fake_draft_value_error(self, *, user_id, robot_model, robot_id, task_summary, focus_prompt):
            raise ValueError("robot_model 不合法")

        monkeypatch.setattr(
            "app.services.training.workbench_draft_generator.TrainingWorkbenchDraftGenerator.generate",
            _fake_draft_value_error,
        )

        resp = client.post(
            "/api/v1/training/workbench/draft",
            headers={"Authorization": f"Bearer {token}"},
            json={"robot_model": "INVALID", "task_summary": "x", "focus_prompt": "y"},
        )
        assert resp.status_code == 400
        body = resp.json()
        # 全局异常处理器使用 message 字段
        assert "robot_model 不合法" in body["message"]
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_generate_workbench_draft_json_decode_error_returns_502(monkeypatch) -> None:
    """POST /training/workbench/draft — JSONDecodeError 时返回 502.

    修复 P0#6 后：except json.JSONDecodeError 排在 except ValueError 之前，
    AI 结果解析失败正确归为 502（网关级错误），而非误判为 400 输入错误。
    """
    client, sf = _build_client()
    try:
        user_id, token = _register_and_login_with_id(client, email="wb3@x.com", full_name="WB3")

        async def _fake_draft_json_error(self, *, user_id, robot_model, robot_id, task_summary, focus_prompt):
            raise json.JSONDecodeError("invalid json", "", 0)

        monkeypatch.setattr(
            "app.services.training.workbench_draft_generator.TrainingWorkbenchDraftGenerator.generate",
            _fake_draft_json_error,
        )

        resp = client.post(
            "/api/v1/training/workbench/draft",
            headers={"Authorization": f"Bearer {token}"},
            json={"robot_model": "ABB", "task_summary": "x", "focus_prompt": "y"},
        )
        # 修复后：JSONDecodeError → 502
        assert resp.status_code == 502
        body = resp.json()
        assert "训练草案" in body["message"]
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_generate_workbench_draft_generic_exception_returns_502(monkeypatch) -> None:
    """POST /training/workbench/draft — 其他异常时返回 502（覆盖 lines 395-397）."""
    client, sf = _build_client()
    try:
        user_id, token = _register_and_login_with_id(client, email="wb4@x.com", full_name="WB4")

        async def _fake_draft_exception(self, *, user_id, robot_model, robot_id, task_summary, focus_prompt):
            raise ConnectionError("LLM 服务不可用")

        monkeypatch.setattr(
            "app.services.training.workbench_draft_generator.TrainingWorkbenchDraftGenerator.generate",
            _fake_draft_exception,
        )

        resp = client.post(
            "/api/v1/training/workbench/draft",
            headers={"Authorization": f"Bearer {token}"},
            json={"robot_model": "ABB", "task_summary": "x", "focus_prompt": "y"},
        )
        assert resp.status_code == 502
        body = resp.json()
        assert "训练草案生成失败" in body["message"]
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_generate_workbench_draft_requires_auth() -> None:
    """POST /training/workbench/draft — 无 token 返回 401."""
    client, sf = _build_client()
    try:
        resp = client.post(
            "/api/v1/training/workbench/draft",
            json={"robot_model": "ABB", "task_summary": "x", "focus_prompt": "y"},
        )
        assert resp.status_code == 401
        body = resp.json()
        # 验证响应体格式和准确的错误消息
        assert body["message"] == "未登录，请先登录后重试"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# POST /training/workbench/evidence — 证据上传 (line 425)
# ─────────────────────────────────────────────────────────────────────────────

def test_upload_workbench_evidence_success(monkeypatch) -> None:
    """POST /training/workbench/evidence — 正常路径返回 201（覆盖 line 425）."""
    client, sf = _build_client()
    try:
        user_id, token = _register_and_login_with_id(client, email="ev1@x.com", full_name="EV1")

        async def _fake_upload_evidence(self, *, user_id, session_id, step_id, note, file):
            return {
                "evidence_bundle_id": "bundle-ev-001",
                "filename": "photo.jpg",
                "content_uri": "local://training-evidence/char-sess/photo.jpg",
                "human_summary": "证据上传",
            }

        monkeypatch.setattr(
            "app.services.training.workbench_execution_service.TrainingWorkbenchExecutionService.upload_evidence",
            _fake_upload_evidence,
        )

        resp = client.post(
            "/api/v1/training/workbench/evidence",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "session_id": "char-sess-001",
                "step_id": "step-char-1",
                "note": "测试证据",
            },
            files={"file": ("photo.jpg", io.BytesIO(b"fake image data"), "image/jpeg")},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["evidence_bundle_id"] == "bundle-ev-001"
        assert body["filename"] == "photo.jpg"
        assert "content_uri" in body
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# POST /training/workbench/sessions/{session_id}/steps/{step_id}/submit (line 451)
# ─────────────────────────────────────────────────────────────────────────────

def test_submit_workbench_step_success(monkeypatch) -> None:
    """POST /workbench/sessions/.../steps/.../submit — 正常路径返回步骤提交结果（覆盖 line 451）."""
    client, sf = _build_client()
    try:
        user_id, token = _register_and_login_with_id(client, email="ws1@x.com", full_name="WS1")

        async def _fake_submit_step(
            self, *, user_id, session_id, step_id, step_index, note, evidence_bundle_id, tools_confirmed
        ):
            return {
                "record_id": "ws-record-001",
                "status": "pass",
                "verdict": {
                    "result": "pass",
                    "summary": "步骤通过",
                    "details": "工具确认正确",
                    "missing_critical_tools": [],
                    "anomaly_tools": [],
                    "evidence_bundle_id": None,
                },
                "next_step_id": "step-2",
                "session_submitted": False,
                "feedback": None,
                "evidence_bundle_id": None,
            }

        monkeypatch.setattr(
            "app.services.training.workbench_execution_service.TrainingWorkbenchExecutionService.submit_step",
            _fake_submit_step,
        )

        resp = client.post(
            "/api/v1/training/workbench/sessions/char-sess-001/steps/step-char-1/submit",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "step_index": 0,
                "note": "步骤完成",
                "tools_confirmed": [{"tool_id": "wrench", "status": "confirmed"}],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["record_id"] == "ws-record-001"
        assert body["status"] == "pass"
        assert body["verdict"]["result"] == "pass"
        assert body["session_submitted"] is False
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# POST /training/workbench/ask (line 473)
# ─────────────────────────────────────────────────────────────────────────────

def test_ask_workbench_assistant_success(monkeypatch) -> None:
    """POST /training/workbench/ask — 正常路径返回助手消息（覆盖 line 473）."""
    client, sf = _build_client()
    try:
        user_id, token = _register_and_login_with_id(client, email="ask1@x.com", full_name="ASK1")

        async def _fake_ask_follow_up(self, *, user_id, session_id, step_id, question, messages):
            return {
                "id": "msg-ask-001",
                "role": "assistant",
                "content": "请检查工具是否就绪",
                "created_at": "2026-01-01T00:00:00",
            }

        monkeypatch.setattr(
            "app.services.training.workbench_execution_service.TrainingWorkbenchExecutionService.ask_follow_up",
            _fake_ask_follow_up,
        )

        resp = client.post(
            "/api/v1/training/workbench/ask",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "session_id": "char-sess-001",
                "step_id": "step-char-1",
                "question": "请问下一步怎么做？",
                "messages": [],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == "msg-ask-001"
        assert body["role"] == "assistant"
        assert body["content"] == "请检查工具是否就绪"
        assert "created_at" in body
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# POST /training/sessions — 创建会话
# ─────────────────────────────────────────────────────────────────────────────

def test_create_session_returns_session_id() -> None:
    """POST /training/sessions — 正常创建会话返回 session_id 和 active 状态."""
    client, sf = _build_client()
    try:
        user_id, _token = _register_and_login_with_id(client, email="cs1@x.com", full_name="CS1")

        resp = client.post(
            "/api/v1/training/sessions",
            json={
                "user_id": user_id,
                "project_id": "proj-cs-001",
                "project_snapshot": {"estimated_time": 30},
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        # session_id 是非确定性 UUID，断言存在且非空
        assert "session_id" in body
        assert body["session_id"]
        assert body["project_id"] == "proj-cs-001"
        assert body["user_id"] == user_id
        assert body["status"] == "active"
        assert body["current_step"] == 0
        assert body["total_duration"] == 0
        assert body["score"] is None
        assert body["submit_type"] is None
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_create_session_with_ab_group() -> None:
    """POST /training/sessions — 带 ab_group 字段也能正常创建."""
    client, sf = _build_client()
    try:
        user_id, _token = _register_and_login_with_id(client, email="cs2@x.com", full_name="CS2")

        resp = client.post(
            "/api/v1/training/sessions",
            json={
                "user_id": user_id,
                "project_id": "proj-cs-002",
                "project_snapshot": {"estimated_time": 45},
                "ab_group": "group_b",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "active"
        assert "session_id" in body
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# GET /training/sessions/{session_id} — 获取会话状态 (lines 530-533)
# ─────────────────────────────────────────────────────────────────────────────

def test_get_session_success() -> None:
    """GET /training/sessions/{session_id} — 存在的会话返回会话详情."""
    client, sf = _build_client()
    try:
        data = _seed_training_data(sf)

        resp = client.get(f"/api/v1/training/sessions/{data['session_id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == data["session_id"]
        assert body["project_id"] == "char-proj-001"
        assert body["user_id"] == data["user_id"]
        assert body["status"] == "active"
        assert body["current_step"] == 1
        assert body["total_duration"] == 600
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_get_session_not_found_returns_404() -> None:
    """GET /training/sessions/{session_id} — 不存在的会话返回 404（覆盖 lines 530-531）."""
    client, sf = _build_client()
    try:
        resp = client.get("/api/v1/training/sessions/nonexistent-session-id")
        assert resp.status_code == 404
        body = resp.json()
        assert body["message"] == "Session not found"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# GET /training/sessions/{session_id}/detail — 获取会话详情 (lines 562-568)
# ─────────────────────────────────────────────────────────────────────────────

def test_get_session_detail_success() -> None:
    """GET /training/sessions/{session_id}/detail — 返回会话详情含步骤记录（覆盖 lines 562-568）."""
    client, sf = _build_client()
    try:
        data = _seed_training_data(sf)

        resp = client.get(f"/api/v1/training/sessions/{data['session_id']}/detail")
        assert resp.status_code == 200
        body = resp.json()
        assert "session" in body
        assert "steps" in body
        assert body["session"]["session_id"] == data["session_id"]
        assert body["session"]["status"] == "active"
        assert isinstance(body["steps"], list)
        assert len(body["steps"]) == 1
        assert body["steps"][0]["step_id"] == "step-char-1"
        assert body["steps"][0]["status"] == "pass"
        assert body["steps"][0]["attempt_count"] == 1
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_get_session_detail_not_found_returns_404() -> None:
    """GET /training/sessions/{session_id}/detail — 不存在时返回 404（覆盖 lines 562-563）."""
    client, sf = _build_client()
    try:
        resp = client.get("/api/v1/training/sessions/nonexistent-detail-id/detail")
        assert resp.status_code == 404
        body = resp.json()
        assert body["message"] == "Session not found"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /training/sessions/{session_id}/pause — 暂停会话 (lines 616-619)
# ─────────────────────────────────────────────────────────────────────────────

def test_pause_session_success() -> None:
    """PATCH /training/sessions/{session_id}/pause — 正常暂停会话返回 paused 状态."""
    client, sf = _build_client()
    try:
        data = _seed_training_data(sf)

        resp = client.patch(f"/api/v1/training/sessions/{data['session_id']}/pause")
        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == data["session_id"]
        assert body["status"] == "paused"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_pause_session_not_found_returns_404() -> None:
    """PATCH /training/sessions/{session_id}/pause — 不存在的会话返回 404（覆盖 lines 616-617）."""
    client, sf = _build_client()
    try:
        resp = client.patch("/api/v1/training/sessions/nonexistent-pause-id/pause")
        assert resp.status_code == 404
        body = resp.json()
        assert body["message"] == "Session not found"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /training/sessions/{session_id}/resume — 恢复会话 (lines 648-651)
# ─────────────────────────────────────────────────────────────────────────────

def test_resume_session_success() -> None:
    """PATCH /training/sessions/{session_id}/resume — 先暂停再恢复，返回 active 状态."""
    client, sf = _build_client()
    try:
        data = _seed_training_data(sf)

        # 先暂停
        pause_resp = client.patch(f"/api/v1/training/sessions/{data['session_id']}/pause")
        assert pause_resp.status_code == 200
        assert pause_resp.json()["status"] == "paused"

        # 再恢复
        resp = client.patch(f"/api/v1/training/sessions/{data['session_id']}/resume")
        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == data["session_id"]
        assert body["status"] == "active"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_resume_session_not_found_returns_404() -> None:
    """PATCH /training/sessions/{session_id}/resume — 不存在的会话返回 404（覆盖 lines 648-649）."""
    client, sf = _build_client()
    try:
        resp = client.patch("/api/v1/training/sessions/nonexistent-resume-id/resume")
        assert resp.status_code == 404
        body = resp.json()
        assert body["message"] == "Session not found"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /training/sessions/{session_id}/abandon — 放弃会话 (lines 676-682)
# ─────────────────────────────────────────────────────────────────────────────

def test_abandon_session_success() -> None:
    """PATCH /training/sessions/{session_id}/abandon — 正常放弃返回 message（覆盖 lines 676-682）."""
    client, sf = _build_client()
    try:
        data = _seed_training_data(sf)

        resp = client.patch(f"/api/v1/training/sessions/{data['session_id']}/abandon")
        assert resp.status_code == 200
        body = resp.json()
        assert body["message"] == "Session abandoned"
        assert body["session_id"] == data["session_id"]
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_abandon_session_not_found_returns_404() -> None:
    """PATCH /training/sessions/{session_id}/abandon — 不存在时返回 404（覆盖 lines 679-680）."""
    client, sf = _build_client()
    try:
        resp = client.patch("/api/v1/training/sessions/nonexistent-abandon-id/abandon")
        assert resp.status_code == 404
        body = resp.json()
        assert body["message"] == "Session not found"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# POST /training/sessions/{session_id}/submit — 手动提交 (lines 700-721)
# ─────────────────────────────────────────────────────────────────────────────

def test_submit_session_session_not_found_returns_404(monkeypatch) -> None:
    """POST /training/sessions/{session_id}/submit — 会话不存在时返回 404（覆盖 lines 700-701）."""
    client, sf = _build_client()
    try:
        async def _fake_check_not_found(self, session_id: str):
            return SimpleNamespace(can_submit=False, message="会话不存在", incomplete_steps=[])

        monkeypatch.setattr(training_endpoints.SubmissionService, "check_submit_ready", _fake_check_not_found)

        resp = client.post(
            "/api/v1/training/sessions/nonexistent-submit-id/submit",
            json={"user_id": 1, "confirm_incomplete": False},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["message"] == "Session not found"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_submit_session_cannot_submit_returns_400(monkeypatch) -> None:
    """POST /training/sessions/{session_id}/submit — 其他不可提交原因返回 400（覆盖 line 702）."""
    client, sf = _build_client()
    try:
        async def _fake_check_not_ready(self, session_id: str):
            return SimpleNamespace(can_submit=False, message="会话已提交", incomplete_steps=[])

        monkeypatch.setattr(training_endpoints.SubmissionService, "check_submit_ready", _fake_check_not_ready)

        resp = client.post(
            "/api/v1/training/sessions/some-session-id/submit",
            json={"user_id": 1, "confirm_incomplete": False},
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["message"] == "会话已提交"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_submit_session_incomplete_without_confirm_returns_409(monkeypatch) -> None:
    """POST /training/sessions/{session_id}/submit — 有未完成步骤且未确认时返回 409（覆盖 lines 704-712）."""
    client, sf = _build_client()
    try:
        async def _fake_check_incomplete(self, session_id: str):
            return SimpleNamespace(
                can_submit=True,
                message="有步骤未完成",
                incomplete_steps=["step-1", "step-2"],
            )

        monkeypatch.setattr(training_endpoints.SubmissionService, "check_submit_ready", _fake_check_incomplete)

        resp = client.post(
            "/api/v1/training/sessions/some-session-id/submit",
            json={"user_id": 1, "confirm_incomplete": False},
        )
        assert resp.status_code == 409
        body = resp.json()
        # 全局异常处理器将 HTTPException detail(dict) 序列化到 message 字段
        assert body["message"]["message"] == "有步骤未完成"
        assert body["message"]["incomplete_steps"] == ["step-1", "step-2"]
        assert body["message"]["requires_confirmation"] is True
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_submit_session_submit_failed_returns_400(monkeypatch) -> None:
    """POST /training/sessions/{session_id}/submit — submit_manual 返回 None 时返回 400（覆盖 line 721）."""
    client, sf = _build_client()
    try:
        async def _fake_check_ready(self, session_id: str):
            return SimpleNamespace(can_submit=True, message="ok", incomplete_steps=[])

        async def _fake_submit_none(self, session_id, user_id, confirm_incomplete=False):
            return None

        monkeypatch.setattr(training_endpoints.SubmissionService, "check_submit_ready", _fake_check_ready)
        monkeypatch.setattr(training_endpoints.SubmissionService, "submit_manual", _fake_submit_none)

        resp = client.post(
            "/api/v1/training/sessions/some-session-id/submit",
            json={"user_id": 1, "confirm_incomplete": True},
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["message"] == "Submit failed"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# POST /training/sessions/{session_id}/force-submit — 教师强制提交 (lines 745-777)
# ─────────────────────────────────────────────────────────────────────────────

def test_force_submit_session_not_found_returns_404() -> None:
    """POST /training/sessions/{session_id}/force-submit — 会话不存在时返回 404（覆盖 lines 745-746）."""
    client, sf = _build_client()
    try:
        resp = client.post(
            "/api/v1/training/sessions/nonexistent-force-submit/force-submit",
            json={"teacher_id": 1},
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["message"] == "Session not found"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_force_submit_teacher_no_scope_returns_403(monkeypatch) -> None:
    """POST /training/sessions/{session_id}/force-submit — teacher 无管辖权时返回 403（覆盖 lines 753-754）."""
    client, sf = _build_client()
    try:
        data = _seed_training_data(sf)

        async def _fake_no_scope(self, teacher_id, student_id):
            return False

        monkeypatch.setattr(training_endpoints.ClassMembershipService, "teacher_has_student_scope", _fake_no_scope)

        resp = client.post(
            f"/api/v1/training/sessions/{data['session_id']}/force-submit",
            json={"teacher_id": 999},
        )
        assert resp.status_code == 403
        body = resp.json()
        assert body["message"] == "Teacher has no scope for this student"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_force_submit_success_records_audit_event(monkeypatch) -> None:
    """POST /training/sessions/{session_id}/force-submit — 有管辖权时成功提交并记录审计事件（覆盖 lines 756-783）."""
    client, sf = _build_client()
    try:
        data = _seed_training_data(sf)

        async def _fake_has_scope(self, teacher_id, student_id):
            return True

        async def _fake_submit_by_teacher(self, session_id, teacher_id):
            return SimpleNamespace(
                submission_id="sub-force-001",
                session_id=session_id,
                user_id=data["user_id"],
                submit_type="teacher",
                payload={"score": 75.0},
            )

        monkeypatch.setattr(training_endpoints.ClassMembershipService, "teacher_has_student_scope", _fake_has_scope)
        monkeypatch.setattr(training_endpoints.SubmissionService, "submit_by_teacher", _fake_submit_by_teacher)

        resp = client.post(
            f"/api/v1/training/sessions/{data['session_id']}/force-submit",
            json={"teacher_id": 42},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["submission_id"] == "sub-force-001"
        assert body["session_id"] == data["session_id"]
        assert body["submit_type"] == "teacher"
        assert body["score"] == 75.0
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_force_submit_submit_failed_returns_400(monkeypatch) -> None:
    """POST /training/sessions/{session_id}/force-submit — submit_by_teacher 返回 None 时 400（覆盖 line 762）."""
    client, sf = _build_client()
    try:
        data = _seed_training_data(sf)

        async def _fake_has_scope(self, teacher_id, student_id):
            return True

        async def _fake_submit_none(self, session_id, teacher_id):
            return None

        monkeypatch.setattr(training_endpoints.ClassMembershipService, "teacher_has_student_scope", _fake_has_scope)
        monkeypatch.setattr(training_endpoints.SubmissionService, "submit_by_teacher", _fake_submit_none)

        resp = client.post(
            f"/api/v1/training/sessions/{data['session_id']}/force-submit",
            json={"teacher_id": 42},
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["message"] == "Force submit failed"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# POST /training/sessions/{session_id}/steps — 更新步骤 (line 810)
# ─────────────────────────────────────────────────────────────────────────────

def test_update_step_returns_record_id() -> None:
    """POST /training/sessions/{session_id}/steps — 更新步骤返回 record_id（覆盖 line 810）."""
    client, sf = _build_client()
    try:
        data = _seed_training_data(sf)

        resp = client.post(
            f"/api/v1/training/sessions/{data['session_id']}/steps",
            json={
                "step_id": "step-char-2",
                "step_index": 1,
                "status": "pass",
                "attempt_count": 2,
                "tools_confirmed": [{"tool_id": "torque_wrench", "status": "confirmed"}],
                "duration_sec": 90,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "record_id" in body
        assert body["record_id"]  # non-empty
        assert body["session_id"] == data["session_id"]
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# GET /training/sessions/{session_id}/steps — 获取步骤记录列表 (lines 826-830)
# ─────────────────────────────────────────────────────────────────────────────

def test_get_step_records_success() -> None:
    """GET /training/sessions/{session_id}/steps — 返回步骤列表."""
    client, sf = _build_client()
    try:
        data = _seed_training_data(sf)

        resp = client.get(f"/api/v1/training/sessions/{data['session_id']}/steps")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 1
        assert body[0]["step_id"] == "step-char-1"
        assert body[0]["status"] == "pass"
        assert body[0]["session_id"] == data["session_id"]
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_get_step_records_not_found_returns_404() -> None:
    """GET /training/sessions/{session_id}/steps — 不存在的会话返回 404（覆盖 lines 826-827）."""
    client, sf = _build_client()
    try:
        resp = client.get("/api/v1/training/sessions/nonexistent-steps-id/steps")
        assert resp.status_code == 404
        body = resp.json()
        assert body["message"] == "Session not found"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# GET /training/users/{user_id}/sessions — 获取用户会话列表 (lines 861-864)
# ─────────────────────────────────────────────────────────────────────────────

def test_get_user_sessions_returns_list() -> None:
    """GET /training/users/{user_id}/sessions — 返回会话列表（覆盖 lines 861-864）."""
    client, sf = _build_client()
    try:
        data = _seed_training_data(sf)

        resp = client.get(f"/api/v1/training/users/{data['user_id']}/sessions")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 1
        assert body[0]["session_id"] == data["session_id"]
        assert body[0]["status"] == "active"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_get_user_sessions_with_status_filter() -> None:
    """GET /training/users/{user_id}/sessions?status=active — 状态过滤返回正确会话."""
    client, sf = _build_client()
    try:
        data = _seed_training_data(sf)

        resp = client.get(
            f"/api/v1/training/users/{data['user_id']}/sessions",
            params={"status": "active"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        # 应包含 active 状态会话（种子数据生成确定性的 1 个 active 会话）
        active_sessions = [s for s in body if s["status"] == "active"]
        assert len(active_sessions) == 1


    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_get_user_sessions_empty_for_unknown_user() -> None:
    """GET /training/users/{user_id}/sessions — 未知用户返回空列表."""
    client, sf = _build_client()
    try:
        resp = client.get("/api/v1/training/users/99999/sessions")
        assert resp.status_code == 200
        body = resp.json()
        assert body == []
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# GET /training/users/{user_id}/active-session — 获取活跃会话 (lines 893-899)
# ─────────────────────────────────────────────────────────────────────────────

def test_get_active_session_success() -> None:
    """GET /training/users/{user_id}/active-session — 有活跃会话时返回会话详情（覆盖 lines 899-912）."""
    client, sf = _build_client()
    try:
        data = _seed_training_data(sf)

        resp = client.get(f"/api/v1/training/users/{data['user_id']}/active-session")
        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == data["session_id"]
        assert body["status"] == "active"
        assert body["user_id"] == data["user_id"]
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_get_active_session_not_found_returns_404() -> None:
    """GET /training/users/{user_id}/active-session — 无活跃会话时返回 404（覆盖 lines 893-897）."""
    client, sf = _build_client()
    try:
        resp = client.get("/api/v1/training/users/99999/active-session")
        assert resp.status_code == 404
        body = resp.json()
        assert body["message"] == "No active session found"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# GET /training/feedback/{session_id} — 获取训练反馈 (lines 931-965)
# ─────────────────────────────────────────────────────────────────────────────

def test_get_training_feedback_with_cached_feedback() -> None:
    """GET /training/feedback/{session_id} — 提交有缓存 feedback 时直接返回（覆盖 line 963）."""
    client, sf = _build_client()
    try:
        data = _seed_training_data(sf)

        resp = client.get(f"/api/v1/training/feedback/{data['session_id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == data["session_id"]
        assert body["submission_id"] == data["submission_id"]
        assert body["overall_score"] == 82.0
        assert body["score_breakdown"] == {"total_score": 82.0}
        assert body["suggestions"] == ["巩固工具确认步骤"]
        assert body["next_learning_plan"] == "继续进阶"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_get_training_feedback_not_found_returns_404() -> None:
    """GET /training/feedback/{session_id} — 无提交记录时返回 404."""
    client, sf = _build_client()
    try:
        resp = client.get("/api/v1/training/feedback/nonexistent-session-for-feedback")
        assert resp.status_code == 404
        body = resp.json()
        assert body["message"] == "Submission not found"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_get_training_feedback_generates_when_no_cache(monkeypatch) -> None:
    """GET /training/feedback/{session_id} — 无缓存时调用 FeedbackGenerator（覆盖 lines 931-961）."""
    client, sf = _build_client()
    try:
        # 创建一个没有 feedback 的 submission
        async def _seed_no_feedback() -> dict:
            async with sf() as session:
                user = User(
                    email="no_cache_student@example.com",
                    password_hash="pbkdf2_sha256$dummy",
                    full_name="No Cache Student",
                    role="student",
                )
                session.add(user)
                await session.flush()

                training_session = TrainingSession(
                    session_id="no-cache-sess-001",
                    project_id="no-cache-proj-001",
                    user_id=user.id,
                    status="submitted",
                    current_step=1,
                    project_snapshot={"estimated_time": 30},
                    total_duration=300,
                    started_at=datetime.utcnow(),
                )
                session.add(training_session)

                submission = TrainingSubmission(
                    submission_id="no-cache-sub-001",
                    session_id=training_session.session_id,
                    user_id=user.id,
                    submit_type="manual",
                    submitted_at=datetime.utcnow(),
                    payload={
                        "session_id": training_session.session_id,
                        "steps_summary": [],
                        "total_duration": 300,
                        "project_snapshot": {"estimated_time": 30},
                    },
                    score=Decimal("70.00"),
                    total_steps=1,
                    completed_steps=0,
                    failed_steps=1,
                    total_duration=300,
                    feedback=None,  # 无缓存反馈
                )
                session.add(submission)

                await session.commit()
                return {"user_id": user.id, "session_id": training_session.session_id}

        data = asyncio.run(_seed_no_feedback())

        # 模拟 FeedbackGenerator.generate 返回假反馈
        fake_step_analysis = SimpleNamespace(
            step_id="step-nc-1",
            step_index=0,
            status="fail",
            attempt_count=2,
            analysis="分析内容",
            suggestions=["注意工具"],
            ref_ids=[],
        )
        fake_feedback = SimpleNamespace(
            overall_score=70.0,
            score_breakdown={"total_score": 70.0},
            step_analyses=[fake_step_analysis],
            suggestions=["改进建议"],
            next_learning_plan="巩固基础",
            teaching_diagnosis=None,
            ranking_percentile=None,
            hint_level_suggestion=None,
        )

        async def _fake_generate(self, submission_id, role):
            return fake_feedback

        monkeypatch.setattr(training_endpoints.FeedbackGenerator, "generate", _fake_generate)

        resp = client.get(f"/api/v1/training/feedback/{data['session_id']}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == data["session_id"]
        assert body["overall_score"] == 70.0
        assert body["score_breakdown"] == {"total_score": 70.0}
        assert body["suggestions"] == ["改进建议"]
        assert len(body["step_analyses"]) == 1
        assert body["step_analyses"][0]["step_id"] == "step-nc-1"
        assert body["step_analyses"][0]["status"] == "fail"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_get_training_feedback_teacher_role(monkeypatch) -> None:
    """GET /training/feedback/{session_id}?role=teacher — teacher 角色触发不同 FeedbackRole（覆盖 line 939）."""
    client, sf = _build_client()
    try:
        # 创建无缓存 submission
        async def _seed_teacher_feedback() -> dict:
            async with sf() as session:
                user = User(
                    email="teacher_fb_student@example.com",
                    password_hash="pbkdf2_sha256$dummy",
                    full_name="Teacher FB Student",
                    role="student",
                )
                session.add(user)
                await session.flush()

                training_session = TrainingSession(
                    session_id="teacher-fb-sess-001",
                    project_id="teacher-fb-proj-001",
                    user_id=user.id,
                    status="submitted",
                    current_step=0,
                    project_snapshot={"estimated_time": 20},
                    total_duration=200,
                    started_at=datetime.utcnow(),
                )
                session.add(training_session)

                submission = TrainingSubmission(
                    submission_id="teacher-fb-sub-001",
                    session_id=training_session.session_id,
                    user_id=user.id,
                    submit_type="manual",
                    submitted_at=datetime.utcnow(),
                    payload={"session_id": training_session.session_id, "steps_summary": [], "total_duration": 200, "project_snapshot": {}},
                    score=Decimal("65.00"),
                    total_steps=0,
                    completed_steps=0,
                    failed_steps=0,
                    total_duration=200,
                    feedback=None,  # 无缓存
                )
                session.add(submission)
                await session.commit()
                return {"session_id": training_session.session_id}

        data = asyncio.run(_seed_teacher_feedback())

        received_roles = []

        async def _fake_generate_with_role(self, submission_id, role):
            received_roles.append(role)
            return SimpleNamespace(
                overall_score=65.0,
                score_breakdown={"total_score": 65.0},
                step_analyses=[],
                suggestions=["教师建议"],
                next_learning_plan="强化练习",
                teaching_diagnosis="学员需要更多辅导",
                ranking_percentile=25.0,
                hint_level_suggestion=2,
            )

        monkeypatch.setattr(training_endpoints.FeedbackGenerator, "generate", _fake_generate_with_role)

        resp = client.get(
            f"/api/v1/training/feedback/{data['session_id']}",
            params={"role": "teacher"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["overall_score"] == 65.0
        assert body["teaching_diagnosis"] == "学员需要更多辅导"
        assert body["ranking_percentile"] == 25.0
        assert body["hint_level_suggestion"] == 2
        # 确认 FeedbackRole.TEACHER 被传入
        from app.services.training.feedback_generator import FeedbackRole
        assert len(received_roles) == 1
        assert received_roles[0] == FeedbackRole.TEACHER
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# GET /students/{user_id}/profile — 技能画像
# ─────────────────────────────────────────────────────────────────────────────

def test_get_student_skill_profile_success() -> None:
    """GET /students/{user_id}/profile — 返回完整技能画像字段."""
    client, sf = _build_client()
    try:
        data = _seed_training_data(sf)

        resp = client.get(f"/api/v1/students/{data['user_id']}/profile")
        assert resp.status_code == 200
        body = resp.json()
        assert body["user_id"] == data["user_id"]
        assert body["overall_level"] == 1
        assert body["total_sessions"] == 2
        assert body["total_duration"] == 1800
        assert body["score_safety"] == 75.0
        assert body["score_procedure"] == 80.0
        assert body["score_precision"] == 70.0
        assert body["score_efficiency"] == 65.0
        assert body["score_tools"] == 85.0
        assert body["cert_l1_passed"] is False
        assert body["cert_l2_passed"] is False
        assert body["cert_l3_eligible"] is False
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_get_student_skill_profile_creates_if_not_exist() -> None:
    """GET /students/{user_id}/profile — 画像不存在时自动创建（get_or_create_profile）."""
    client, sf = _build_client()
    try:
        # 使用不存在的用户 ID（skill profile 会自动创建）
        resp = client.get("/api/v1/students/88888/profile")
        assert resp.status_code == 200
        body = resp.json()
        assert body["user_id"] == 88888
        assert body["overall_level"] == 1  # 默认初始等级
        assert body["total_sessions"] == 0
        assert body["score_safety"] is None
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# GET /students/{user_id}/weak-steps — 薄弱步骤
# ─────────────────────────────────────────────────────────────────────────────

def test_get_student_weak_steps_success() -> None:
    """GET /students/{user_id}/weak-steps — 返回薄弱步骤列表."""
    client, sf = _build_client()
    try:
        data = _seed_training_data(sf)

        resp = client.get(f"/api/v1/students/{data['user_id']}/weak-steps")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 1
        assert body[0]["step_id"] == "step-char-weak-1"
        assert body[0]["sop_id"] == "SOP-CHAR-01"
        assert body[0]["fail_count"] == 3
        assert body[0]["is_resolved"] is False
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_get_student_weak_steps_empty_for_unknown_user() -> None:
    """GET /students/{user_id}/weak-steps — 未知用户返回空列表."""
    client, sf = _build_client()
    try:
        resp = client.get("/api/v1/students/77777/weak-steps")
        assert resp.status_code == 200
        body = resp.json()
        assert body == []
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_get_student_weak_steps_unresolved_only_filter() -> None:
    """GET /students/{user_id}/weak-steps?unresolved_only=true — 只返回未解决步骤."""
    client, sf = _build_client()
    try:
        data = _seed_training_data(sf)

        resp = client.get(
            f"/api/v1/students/{data['user_id']}/weak-steps",
            params={"unresolved_only": True, "limit": 5},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 1
        assert body[0]["is_resolved"] is False
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None
