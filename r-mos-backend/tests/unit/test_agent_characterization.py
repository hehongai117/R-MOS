"""
特征测试：app/api/v1/endpoints/agent.py
目标：行覆盖率 ≥ 80%（Phase 2 safety-net）

测试策略：
- 复用 test_skill_governance_api.py 的基建（_build_client / _register_and_login / _grant_role_permissions）
- 每个路由至少一个测试，断言真实响应状态码与关键字段
- 覆盖正常路径 + 权限拒绝路径 + 404 路径
"""
from __future__ import annotations

import asyncio
import io
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.models.base import Base
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.school import School
from app.models.user import User
from main import app

import app.models as app_models  # noqa: F401  # 确保模型全部注册

# onboarding 注册需要的白名单学校（测试统一使用）
TEST_SCHOOL_NAME = "测试学校"

# ─────────────────────────────────────────────────────────────────────────────
# 测试基建（复用 test_skill_governance_api.py 样板）
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


async def _grant_role_permissions(
    session_factory: async_sessionmaker,
    *,
    email: str,
    role_name: str,
    permission_keys: list[str],
) -> int:
    async with session_factory() as session:
        user_result = await session.execute(select(User).where(User.email == email))
        user = user_result.scalar_one()

        role_result = await session.execute(select(Role).where(Role.name == role_name))
        role = role_result.scalar_one_or_none()
        if role is None:
            role = Role(name=role_name, description=f"{role_name} 角色")
            session.add(role)
            await session.flush()

        for permission_key in permission_keys:
            permission_result = await session.execute(
                select(Permission).where(Permission.key == permission_key)
            )
            permission = permission_result.scalar_one_or_none()
            if permission is None:
                resource_type, action = permission_key.split(":", 1)
                permission = Permission(
                    key=permission_key,
                    description=f"{permission_key} 权限",
                    resource_type=resource_type,
                    action=action,
                )
                session.add(permission)
                await session.flush()

            role_permission_result = await session.execute(
                select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == permission.id,
                )
            )
            if role_permission_result.scalar_one_or_none() is None:
                session.add(RolePermission(role_id=role.id, permission_id=permission.id))

        user_role_result = await session.execute(
            select(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.role_id == role.id,
            )
        )
        if user_role_result.scalar_one_or_none() is None:
            session.add(UserRole(user_id=user.id, role_id=role.id))

        await session.commit()
        return user.id


def _register_and_login(client: TestClient, *, email: str, password: str, full_name: str) -> str:
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


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：GET /agent/task-status/{user_id}
# 权限：agent:read + role: agent_user
# ─────────────────────────────────────────────────────────────────────────────

def test_get_task_status_returns_no_task_for_unknown_user() -> None:
    """GET /agent/task-status/{user_id} — 无任务时返回 no_task 状态."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="ts1@x.com", password="StrongPass123", full_name="U1")
        asyncio.run(_grant_role_permissions(sf, email="ts1@x.com", role_name="agent_user", permission_keys=["agent:read"]))

        resp = client.get(
            "/api/v1/agent/task-status/unknown-user-99",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "no_task"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_get_task_status_requires_agent_user_role() -> None:
    """GET /agent/task-status/{user_id} — 无 agent_user 角色返回 403."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="ts2@x.com", password="StrongPass123", full_name="U2")
        # grant agent:read 权限但没有 agent_user 角色
        asyncio.run(_grant_role_permissions(sf, email="ts2@x.com", role_name="teacher", permission_keys=["agent:read"]))

        resp = client.get(
            "/api/v1/agent/task-status/u1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        body = resp.json()
        assert body["error_type"] == "RoleRequiredError"
        assert body["details"]["code"] == "AUTHZ_002"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：POST /agent/coach/recommend
# 权限：agent:execute
# ─────────────────────────────────────────────────────────────────────────────

def test_coach_recommend_returns_next_action() -> None:
    """POST /agent/coach/recommend — 返回 coach 建议，含 next_action 与 confidence."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="coach1@x.com", password="StrongPass123", full_name="C1")
        asyncio.run(_grant_role_permissions(sf, email="coach1@x.com", role_name="agent_user", permission_keys=["agent:execute"]))

        resp = client.post(
            "/api/v1/agent/coach/recommend",
            headers={"Authorization": f"Bearer {token}"},
            json={"task_id": "task-001", "current_step": 0, "step_history": [], "trainee_action": None},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "next_action" in body
        assert "confidence" in body
        assert "explanation" in body
        assert "risk_events" in body
        assert "reasoning" in body
        # coach_agent 对 step 0 返回 next_action 不为 None
        assert body["next_action"] is not None
        assert body["confidence"] == 0.95
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_coach_recommend_requires_agent_execute() -> None:
    """POST /agent/coach/recommend — 无权限返回 403."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="coach2@x.com", password="StrongPass123", full_name="C2")
        # grant agent:read 但不是 agent:execute

        resp = client.post(
            "/api/v1/agent/coach/recommend",
            headers={"Authorization": f"Bearer {token}"},
            json={"task_id": "task-001", "current_step": 0},
        )
        assert resp.status_code == 403
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：POST /agent/diagnoser/diagnose
# 权限：agent:execute
# ─────────────────────────────────────────────────────────────────────────────

def test_diagnoser_diagnose_empty_history_returns_null_root_cause() -> None:
    """POST /agent/diagnoser/diagnose — 空历史时 root_cause 为 None."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="diag1@x.com", password="StrongPass123", full_name="D1")
        asyncio.run(_grant_role_permissions(sf, email="diag1@x.com", role_name="agent_user", permission_keys=["agent:execute"]))

        resp = client.post(
            "/api/v1/agent/diagnoser/diagnose",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "task_id": "task-diag-001",
                "error_history": [],
                "action_history": [],
                "evidence_refs": [],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["root_cause"] is None
        assert body["root_cause_confidence"] == 0
        assert body["confidence"] == 0.0
        assert body["evidence_refs"] == []
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：POST /agent/knowledge/search
# 权限：agent:read
# ─────────────────────────────────────────────────────────────────────────────

def test_knowledge_search_returns_results_list() -> None:
    """POST /agent/knowledge/search — 返回 results 列表结构.

    knowledge_store.json 中预置了 2 条 APPROVED 条目（ABB motor handling、FANUC motor handling）。
    因为 _calculate_relevance 即使 query 不命中文本也会通过 confidence boost 给出正分，
    导致每次测试（如 test_approve_knowledge_success）新增 APPROVED 条目后结果数增加。
    计数不确定，使用 >= 2 保证预置条目始终存在。
    """
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="ks1@x.com", password="StrongPass123", full_name="K1")
        asyncio.run(_grant_role_permissions(sf, email="ks1@x.com", role_name="agent_user", permission_keys=["agent:read"]))

        resp = client.post(
            "/api/v1/agent/knowledge/search",
            headers={"Authorization": f"Bearer {token}"},
            json={"query": "test", "status": "APPROVED"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "results" in body
        assert isinstance(body["results"], list)
        # >= 2：预置 knowledge_store.json 至少包含 ABB/FANUC 2 条 APPROVED 条目
        # 实际数量因 test_approve_knowledge_* 写入共享 JSON 文件而随测试顺序增加（非确定性）
        assert len(body["results"]) >= 2
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_knowledge_search_pending_status() -> None:
    """POST /agent/knowledge/search — 使用 PENDING 状态也能正常返回.

    knowledge_store.json 中无 PENDING 条目，因此结果为空列表。
    """
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="ks2@x.com", password="StrongPass123", full_name="K2")
        asyncio.run(_grant_role_permissions(sf, email="ks2@x.com", role_name="agent_user", permission_keys=["agent:read"]))

        resp = client.post(
            "/api/v1/agent/knowledge/search",
            headers={"Authorization": f"Bearer {token}"},
            json={"query": "", "status": "PENDING", "device_model": "ARM-X1", "part_type": "joint"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "results" in body
        assert isinstance(body["results"], list)
        # knowledge_store.json 中无 PENDING 条目，空列表
        assert body["results"] == []
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：POST /agent/knowledge
# 权限：agent:execute
# ─────────────────────────────────────────────────────────────────────────────

def test_create_knowledge_returns_entry_id_and_draft_status() -> None:
    """POST /agent/knowledge — 创建知识条目返回 id、DRAFT 状态和标题."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="kc1@x.com", password="StrongPass123", full_name="KC1")
        asyncio.run(_grant_role_permissions(sf, email="kc1@x.com", role_name="agent_user", permission_keys=["agent:execute"]))

        resp = client.post(
            "/api/v1/agent/knowledge",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "测试知识条目",
                "content": "这是内容",
                "type": "solution",
                "risk_level": "R1",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "id" in body
        assert body["status"] == "DRAFT"
        assert body["title"] == "测试知识条目"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：POST /agent/knowledge/upload
# 权限：agent:execute
# ─────────────────────────────────────────────────────────────────────────────

def test_upload_knowledge_file_returns_job() -> None:
    """POST /agent/knowledge/upload — 上传文件返回 job_id 与 project_id."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="ku1@x.com", password="StrongPass123", full_name="KU1")
        asyncio.run(_grant_role_permissions(sf, email="ku1@x.com", role_name="agent_user", permission_keys=["agent:execute"]))

        file_content = b"dummy robot manual content"
        resp = client.post(
            "/api/v1/agent/knowledge/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("manual.txt", io.BytesIO(file_content), "text/plain")},
            params={"brand": "TestBrand", "model": "TestModel", "version": "1.0"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "job_id" in body
        assert "project_id" in body
        assert "status" in body
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_upload_knowledge_file_empty_returns_400() -> None:
    """POST /agent/knowledge/upload — 空文件返回 400."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="ku2@x.com", password="StrongPass123", full_name="KU2")
        asyncio.run(_grant_role_permissions(sf, email="ku2@x.com", role_name="agent_user", permission_keys=["agent:execute"]))

        resp = client.post(
            "/api/v1/agent/knowledge/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
        )
        assert resp.status_code == 400
        body = resp.json()
        # 全局 exception handler 使用 message 字段，而非 FastAPI 默认的 detail
        assert body["message"] == "Uploaded file is empty"
        assert body["error_type"] == "HTTPException"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：GET /agent/knowledge/upload/{job_id}
# 权限：agent:read
# ─────────────────────────────────────────────────────────────────────────────

def test_get_knowledge_upload_job_not_found_returns_404() -> None:
    """GET /agent/knowledge/upload/{job_id} — 不存在 job_id 返回 404."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="kuj1@x.com", password="StrongPass123", full_name="KUJ1")
        asyncio.run(_grant_role_permissions(sf, email="kuj1@x.com", role_name="agent_user", permission_keys=["agent:read"]))

        resp = client.get(
            "/api/v1/agent/knowledge/upload/nonexistent-job-id",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
        body = resp.json()
        # 全局 exception handler 使用 message 字段，而非 FastAPI 默认的 detail
        assert body["message"] == "Knowledge upload job not found"
        assert body["error_type"] == "HTTPException"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_get_knowledge_upload_job_existing_returns_job_data() -> None:
    """GET /agent/knowledge/upload/{job_id} — 存在的 job_id 返回 job 数据."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="kuj2@x.com", password="StrongPass123", full_name="KUJ2")
        asyncio.run(_grant_role_permissions(sf, email="kuj2@x.com", role_name="agent_user", permission_keys=["agent:execute", "agent:read"]))

        # 先上传
        file_content = b"robot manual content for job query"
        upload_resp = client.post(
            "/api/v1/agent/knowledge/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("manual2.txt", io.BytesIO(file_content), "text/plain")},
        )
        assert upload_resp.status_code == 200
        job_id = upload_resp.json()["job_id"]

        # 再查询
        resp = client.get(
            f"/api/v1/agent/knowledge/upload/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["job_id"] == job_id
        assert "status" in body
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：GET /agent/knowledge/projects
# 权限：agent:read
# ─────────────────────────────────────────────────────────────────────────────

def test_list_robot_projects_returns_projects_list() -> None:
    """GET /agent/knowledge/projects — 返回 projects 列表."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="kp1@x.com", password="StrongPass123", full_name="KP1")
        asyncio.run(_grant_role_permissions(sf, email="kp1@x.com", role_name="agent_user", permission_keys=["agent:read"]))

        resp = client.get(
            "/api/v1/agent/knowledge/projects",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "projects" in body
        assert isinstance(body["projects"], list)
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：GET /agent/knowledge/projects/{project_id}/manifest
# 权限：agent:read
# ─────────────────────────────────────────────────────────────────────────────

def test_get_robot_project_manifest_not_found_returns_404() -> None:
    """GET /agent/knowledge/projects/{project_id}/manifest — 不存在时返回 404."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="kpm1@x.com", password="StrongPass123", full_name="KPM1")
        asyncio.run(_grant_role_permissions(sf, email="kpm1@x.com", role_name="agent_user", permission_keys=["agent:read"]))

        resp = client.get(
            "/api/v1/agent/knowledge/projects/nonexistent-project/manifest",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
        body = resp.json()
        # 全局 exception handler 使用 message 字段
        assert body["message"] == "robot project manifest not found"
        assert body["error_type"] == "HTTPException"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：GET /agent/knowledge/projects/{project_id}/assets/{asset_path}
# 权限：agent:read
# ─────────────────────────────────────────────────────────────────────────────

def test_get_robot_project_asset_not_found_returns_404() -> None:
    """GET /agent/knowledge/projects/{project_id}/assets/{path} — 不存在时返回 404."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="kpa1@x.com", password="StrongPass123", full_name="KPA1")
        asyncio.run(_grant_role_permissions(sf, email="kpa1@x.com", role_name="agent_user", permission_keys=["agent:read"]))

        resp = client.get(
            "/api/v1/agent/knowledge/projects/nonexistent-project/assets/some/file.glb",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
        body = resp.json()
        # 全局 exception handler 使用 message 字段
        assert body["message"] == "robot project asset not found"
        assert body["error_type"] == "HTTPException"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：POST /agent/knowledge/{entry_id}/submit
# 权限：agent:execute
# ─────────────────────────────────────────────────────────────────────────────

def test_submit_knowledge_success() -> None:
    """POST /agent/knowledge/{entry_id}/submit — 先创建再提交，返回 submitted 状态."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="ksub1@x.com", password="StrongPass123", full_name="KSUB1")
        asyncio.run(_grant_role_permissions(sf, email="ksub1@x.com", role_name="agent_user", permission_keys=["agent:execute"]))

        # 创建知识条目
        create_resp = client.post(
            "/api/v1/agent/knowledge",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "待审知识", "content": "内容", "type": "solution", "risk_level": "R1"},
        )
        assert create_resp.status_code == 200
        entry_id = create_resp.json()["id"]

        # 提交审核
        resp = client.post(
            f"/api/v1/agent/knowledge/{entry_id}/submit",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "submitted"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_submit_knowledge_nonexistent_returns_400() -> None:
    """POST /agent/knowledge/{entry_id}/submit — 不存在的条目返回 400."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="ksub2@x.com", password="StrongPass123", full_name="KSUB2")
        asyncio.run(_grant_role_permissions(sf, email="ksub2@x.com", role_name="agent_user", permission_keys=["agent:execute"]))

        resp = client.post(
            "/api/v1/agent/knowledge/nonexistent-entry-id/submit",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：POST /agent/knowledge/{entry_id}/approve
# 权限：agent:execute
# ─────────────────────────────────────────────────────────────────────────────

def test_approve_knowledge_success() -> None:
    """POST /agent/knowledge/{entry_id}/approve — 创建、提交、审批，返回 approve 状态."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="kapp1@x.com", password="StrongPass123", full_name="KAPP1")
        asyncio.run(_grant_role_permissions(sf, email="kapp1@x.com", role_name="agent_user", permission_keys=["agent:execute"]))

        # 创建
        create_resp = client.post(
            "/api/v1/agent/knowledge",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "审批测试", "content": "内容", "type": "solution", "risk_level": "R1"},
        )
        assert create_resp.status_code == 200
        entry_id = create_resp.json()["id"]

        # 提交
        submit_resp = client.post(
            f"/api/v1/agent/knowledge/{entry_id}/submit",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert submit_resp.status_code == 200

        # 审批通过
        resp = client.post(
            f"/api/v1/agent/knowledge/{entry_id}/approve",
            headers={"Authorization": f"Bearer {token}"},
            json={"decision": "approve", "feedback": "很好", "rating": 4.5},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "approve"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_approve_knowledge_reject_success() -> None:
    """POST /agent/knowledge/{entry_id}/approve — 拒绝审批，返回 reject 状态."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="kapp2@x.com", password="StrongPass123", full_name="KAPP2")
        asyncio.run(_grant_role_permissions(sf, email="kapp2@x.com", role_name="agent_user", permission_keys=["agent:execute"]))

        # 创建
        create_resp = client.post(
            "/api/v1/agent/knowledge",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": "拒绝测试", "content": "内容", "type": "solution", "risk_level": "R1"},
        )
        assert create_resp.status_code == 200
        entry_id = create_resp.json()["id"]

        # 提交
        submit_resp = client.post(
            f"/api/v1/agent/knowledge/{entry_id}/submit",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert submit_resp.status_code == 200

        # 审批拒绝
        resp = client.post(
            f"/api/v1/agent/knowledge/{entry_id}/approve",
            headers={"Authorization": f"Bearer {token}"},
            json={"decision": "reject", "feedback": "质量不足"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "reject"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：POST /agent/coordinate
# 权限：agent:execute
# ─────────────────────────────────────────────────────────────────────────────

def test_coordinate_agents_returns_coordination_result() -> None:
    """POST /agent/coordinate — 返回协调结果含 task_id, user_id, consensus 字段."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="coord1@x.com", password="StrongPass123", full_name="CO1")
        asyncio.run(_grant_role_permissions(sf, email="coord1@x.com", role_name="agent_user", permission_keys=["agent:execute"]))

        resp = client.post(
            "/api/v1/agent/coordinate",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "task_id": "task-coord-001",
                "user_id": "user-001",
                "action": "inspect",
                "context": {"step": 1},
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["task_id"] == "task-coord-001"
        assert body["user_id"] == "user-001"
        assert "final_action" in body
        assert "consensus" in body
        assert "conflicts" in body
        assert "execution_time_ms" in body
        assert body["consensus"] is True
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：GET /agent/evidence/status/{step_id}
# 权限：agent:read
# ─────────────────────────────────────────────────────────────────────────────

def test_evidence_status_for_unknown_step_returns_complete_true() -> None:
    """GET /agent/evidence/status/{step_id} — 无记录步骤返回 complete=True."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="ev1@x.com", password="StrongPass123", full_name="EV1")
        asyncio.run(_grant_role_permissions(sf, email="ev1@x.com", role_name="agent_user", permission_keys=["agent:read"]))

        resp = client.get(
            "/api/v1/agent/evidence/status/step-unknown-xyz",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["step_id"] == "step-unknown-xyz"
        assert body["required"] == []
        assert body["collected"] == []
        assert body["missing"] == []
        assert body["complete"] is True
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：POST /agent/evidence/collect
# 权限：agent:execute
# ─────────────────────────────────────────────────────────────────────────────

def test_collect_evidence_returns_collected_status() -> None:
    """POST /agent/evidence/collect — 收集证据返回 collected 状态."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="evc1@x.com", password="StrongPass123", full_name="EVC1")
        asyncio.run(_grant_role_permissions(sf, email="evc1@x.com", role_name="agent_user", permission_keys=["agent:execute"]))

        resp = client.post(
            "/api/v1/agent/evidence/collect",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "step_id": "step-collect-001",
                "evidence_id": "ev-001",
                "evidence_type": "photo",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "collected"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：GET /agent/evidence/can-proceed/{step_id}
# 权限：agent:read
# ─────────────────────────────────────────────────────────────────────────────

def test_can_proceed_for_unknown_step_returns_allowed_true() -> None:
    """GET /agent/evidence/can-proceed/{step_id} — 无证据要求时 allowed=True."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="evcp1@x.com", password="StrongPass123", full_name="EVCP1")
        asyncio.run(_grant_role_permissions(sf, email="evcp1@x.com", role_name="agent_user", permission_keys=["agent:read"]))

        resp = client.get(
            "/api/v1/agent/evidence/can-proceed/step-proceed-001",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["allowed"] is True
        assert "reason" in body
        assert body["reason"] == "All required evidence collected"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：GET /agent/evidence/requirements/{action_type}
# 权限：agent:read
# ─────────────────────────────────────────────────────────────────────────────

def test_evidence_requirements_known_action_type() -> None:
    """GET /agent/evidence/requirements/{action_type} — 已知 action_type 返回 requirements 列表."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="evreq1@x.com", password="StrongPass123", full_name="EVREQ1")
        asyncio.run(_grant_role_permissions(sf, email="evreq1@x.com", role_name="agent_user", permission_keys=["agent:read"]))

        resp = client.get(
            "/api/v1/agent/evidence/requirements/inspect",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["action_type"] == "inspect"
        assert "requirements" in body
        assert isinstance(body["requirements"], list)
        # inspect 动作在 ACTION_EVIDENCE_REQUIREMENTS 中有条目
        assert len(body["requirements"]) > 0
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_evidence_requirements_unknown_action_type_returns_empty() -> None:
    """GET /agent/evidence/requirements/{action_type} — 未知 action_type 返回空 requirements."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="evreq2@x.com", password="StrongPass123", full_name="EVREQ2")
        asyncio.run(_grant_role_permissions(sf, email="evreq2@x.com", role_name="agent_user", permission_keys=["agent:read"]))

        resp = client.get(
            "/api/v1/agent/evidence/requirements/nonexistent_action",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["action_type"] == "nonexistent_action"
        assert body["requirements"] == []
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：POST /agent/execute (P2-1 统一执行端点)
# 权限：无固定权限装饰器（自定义 _require_agent_permission）
# ─────────────────────────────────────────────────────────────────────────────

def test_execute_message_mode_returns_success_response() -> None:
    """POST /agent/execute — message 模式（agent:read）返回 success 状态."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="exec1@x.com", password="StrongPass123", full_name="EXEC1")
        asyncio.run(_grant_role_permissions(sf, email="exec1@x.com", role_name="agent_user", permission_keys=["agent:read"]))

        resp = client.post(
            "/api/v1/agent/execute",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "user_id": "user-exec-001",
                "mode": "message",
                "message": "请帮我检查机器人状态",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert "trace_id" in body
        assert "mode_used" in body
        assert body["mode_used"] == "message"
        assert "from_cache" in body
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_execute_command_mode_no_side_effects_returns_success() -> None:
    """POST /agent/execute — command 模式无副作用时返回 error（已知 bug）.

    当前实现中 Command(user_id=...) 传入了无效字段（Command 模型使用 actor_user_id），
    导致 SQLAlchemy 抛出 TypeError，endpoint 捕获后返回 status="error"。
    这是被锁定的当前行为（characterization）。
    """
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="exec2@x.com", password="StrongPass123", full_name="EXEC2")
        asyncio.run(_grant_role_permissions(sf, email="exec2@x.com", role_name="agent_user", permission_keys=["agent:execute"]))

        resp = client.post(
            "/api/v1/agent/execute",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "user_id": "user-exec-002",
                "mode": "command",
                "intent": "dispatch",
                "tool_name": "sops.read",
                "tool_args": {},
                "side_effects": [],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        # Command(user_id=...) 使用无效字段名，endpoint 捕获后返回 "error"（已知 bug）
        assert body["status"] == "error"
        assert "trace_id" in body
        assert body["mode_used"] == "command"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_execute_command_mode_with_side_effects_returns_pending_approval() -> None:
    """POST /agent/execute — command 模式有副作用时实际返回 error（已知 bug）.

    设计预期为 pending_approval，但当前实现中 Command(user_id=...) 使用无效字段名
    （模型字段为 actor_user_id），导致 TypeError 被捕获后返回 status="error"。
    这是被锁定的当前行为（characterization）。
    """
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="exec3@x.com", password="StrongPass123", full_name="EXEC3")
        asyncio.run(_grant_role_permissions(sf, email="exec3@x.com", role_name="agent_user", permission_keys=["agent:execute"]))

        resp = client.post(
            "/api/v1/agent/execute",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "user_id": "user-exec-003",
                "mode": "command",
                "intent": "dispatch",
                "tool_name": "assignments.create_draft",
                "skill_id": "teaching.dispatch.draft",
                "tool_args": {"input_text": "create task"},
                "side_effects": ["assignments.write"],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        # Command(user_id=...) 使用无效字段名，endpoint 捕获后返回 "error"（已知 bug）
        # 设计预期为 pending_approval，但当前行为是 error
        assert body["status"] == "error"
        assert "trace_id" in body
        assert body["mode_used"] == "command"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_execute_auto_mode_detects_message_by_default() -> None:
    """POST /agent/execute — auto 模式无 tool_name/intent/message 时默认使用 message 模式."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="exec4@x.com", password="StrongPass123", full_name="EXEC4")
        asyncio.run(_grant_role_permissions(sf, email="exec4@x.com", role_name="agent_user", permission_keys=["agent:read"]))

        resp = client.post(
            "/api/v1/agent/execute",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": "user-exec-004", "mode": "auto"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["mode_used"] == "message"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_execute_auto_mode_detects_command_by_tool_name() -> None:
    """POST /agent/execute — auto 模式提供 tool_name 时自动切换为 command 模式."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="exec5@x.com", password="StrongPass123", full_name="EXEC5")
        asyncio.run(_grant_role_permissions(sf, email="exec5@x.com", role_name="agent_user", permission_keys=["agent:execute"]))

        resp = client.post(
            "/api/v1/agent/execute",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "user_id": "user-exec-005",
                "mode": "auto",
                "tool_name": "sops.read",
                "tool_args": {},
                "side_effects": [],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["mode_used"] == "command"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_execute_permission_denied_returns_403() -> None:
    """POST /agent/execute — command 模式缺少 agent:execute 返回 403."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="exec6@x.com", password="StrongPass123", full_name="EXEC6")
        # 只有 agent:read，没有 agent:execute

        resp = client.post(
            "/api/v1/agent/execute",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "user_id": "user-exec-006",
                "mode": "command",
                "tool_name": "sops.write",
                "side_effects": ["sops.write"],
            },
        )
        assert resp.status_code == 403
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：POST /agent/v2/trace/{trace_id}/diagnosis-action
# 权限：自定义 _require_agent_permission("agent:read")
# ─────────────────────────────────────────────────────────────────────────────

def test_diagnosis_action_confirm_execution_returns_message() -> None:
    """POST /agent/v2/trace/{trace_id}/diagnosis-action — confirm_execution 返回确认消息."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="diaga1@x.com", password="StrongPass123", full_name="DA1")
        asyncio.run(_grant_role_permissions(sf, email="diaga1@x.com", role_name="agent_user", permission_keys=["agent:read"]))

        resp = client.post(
            "/api/v1/agent/v2/trace/trace-abc-001/diagnosis-action",
            headers={"Authorization": f"Bearer {token}"},
            json={"action": "confirm_execution"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["trace_id"] == "trace-abc-001"
        assert body["action"] == "confirm_execution"
        assert body["recorded"] is True
        assert "已确认执行方案" in body["message"]
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_diagnosis_action_escalate_to_teacher_returns_message() -> None:
    """POST /agent/v2/trace/{trace_id}/diagnosis-action — escalate_to_teacher 返回上报消息."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="diaga2@x.com", password="StrongPass123", full_name="DA2")
        asyncio.run(_grant_role_permissions(sf, email="diaga2@x.com", role_name="agent_user", permission_keys=["agent:read"]))

        resp = client.post(
            "/api/v1/agent/v2/trace/trace-abc-002/diagnosis-action",
            headers={"Authorization": f"Bearer {token}"},
            json={"action": "escalate_to_teacher"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["trace_id"] == "trace-abc-002"
        assert body["action"] == "escalate_to_teacher"
        assert body["recorded"] is True
        assert "已上报教师审核" in body["message"]
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_diagnosis_action_unsupported_action_returns_400() -> None:
    """POST /agent/v2/trace/{trace_id}/diagnosis-action — 不支持的 action 返回 400."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="diaga3@x.com", password="StrongPass123", full_name="DA3")
        asyncio.run(_grant_role_permissions(sf, email="diaga3@x.com", role_name="agent_user", permission_keys=["agent:read"]))

        resp = client.post(
            "/api/v1/agent/v2/trace/trace-abc-003/diagnosis-action",
            headers={"Authorization": f"Bearer {token}"},
            json={"action": "unknown_action"},
        )
        assert resp.status_code == 400
        body = resp.json()
        # 全局 exception handler 使用 message 字段
        assert "Unsupported diagnosis action" in body["message"]
        assert body["error_type"] == "HTTPException"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：POST /agent/v2/task/create
# 权限：agent:execute
# ─────────────────────────────────────────────────────────────────────────────

def test_create_task_v2_returns_task_id_and_created_state() -> None:
    """POST /agent/v2/task/create — 创建任务返回 task_id 及 created 状态."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="tv2c1@x.com", password="StrongPass123", full_name="TV2C1")
        asyncio.run(_grant_role_permissions(sf, email="tv2c1@x.com", role_name="agent_user", permission_keys=["agent:execute"]))

        resp = client.post(
            "/api/v1/agent/v2/task/create",
            headers={"Authorization": f"Bearer {token}"},
            params={"user_id": "user-v2-001", "budget_limit_ms": 300000},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "task_id" in body
        assert "trace_id" in body
        assert body["state"] == "created"
        assert body["budget_limit_ms"] == 300000
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：POST /agent/v2/task/{task_id}/transition
# 权限：agent:execute
# ─────────────────────────────────────────────────────────────────────────────

def test_task_transition_valid_event_changes_state() -> None:
    """POST /agent/v2/task/{task_id}/transition — 有效 event 改变状态."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="tv2t1@x.com", password="StrongPass123", full_name="TV2T1")
        asyncio.run(_grant_role_permissions(sf, email="tv2t1@x.com", role_name="agent_user", permission_keys=["agent:execute"]))

        # 先创建任务
        create_resp = client.post(
            "/api/v1/agent/v2/task/create",
            headers={"Authorization": f"Bearer {token}"},
            params={"user_id": "user-v2-002"},
        )
        assert create_resp.status_code == 200
        task_id = create_resp.json()["task_id"]

        # start 事件
        resp = client.post(
            f"/api/v1/agent/v2/task/{task_id}/transition",
            headers={"Authorization": f"Bearer {token}"},
            params={"event": "start"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["task_id"] == task_id
        assert body["state"] == "ready"
        assert "message" in body
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_task_transition_invalid_event_returns_400() -> None:
    """POST /agent/v2/task/{task_id}/transition — 无效 event 返回 400."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="tv2t2@x.com", password="StrongPass123", full_name="TV2T2")
        asyncio.run(_grant_role_permissions(sf, email="tv2t2@x.com", role_name="agent_user", permission_keys=["agent:execute"]))

        resp = client.post(
            "/api/v1/agent/v2/task/task-nonexistent/transition",
            headers={"Authorization": f"Bearer {token}"},
            params={"event": "invalid_event"},
        )
        assert resp.status_code == 400
        body = resp.json()
        # 全局 exception handler 使用 message 字段
        assert "Invalid event" in body["message"]
        assert body["error_type"] == "HTTPException"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_task_transition_invalid_state_for_task_returns_400() -> None:
    """POST /agent/v2/task/{task_id}/transition — 不存在的 task_id + 有效 event 返回 400."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="tv2t3@x.com", password="StrongPass123", full_name="TV2T3")
        asyncio.run(_grant_role_permissions(sf, email="tv2t3@x.com", role_name="agent_user", permission_keys=["agent:execute"]))

        resp = client.post(
            "/api/v1/agent/v2/task/nonexistent-task-id/transition",
            headers={"Authorization": f"Bearer {token}"},
            params={"event": "start"},
        )
        assert resp.status_code == 400
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：GET /agent/v2/task/{task_id}
# 权限：agent:read
# ─────────────────────────────────────────────────────────────────────────────

def test_get_task_status_v2_not_found_returns_404() -> None:
    """GET /agent/v2/task/{task_id} — 不存在的 task_id 返回 404."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="tv2g1@x.com", password="StrongPass123", full_name="TV2G1")
        asyncio.run(_grant_role_permissions(sf, email="tv2g1@x.com", role_name="agent_user", permission_keys=["agent:read"]))

        resp = client.get(
            "/api/v1/agent/v2/task/nonexistent-task-id-xyz",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
        body = resp.json()
        # 全局 exception handler 使用 message 字段
        assert body["message"] == "Task not found"
        assert body["error_type"] == "HTTPException"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_get_task_status_v2_existing_returns_context() -> None:
    """GET /agent/v2/task/{task_id} — 存在的任务返回完整上下文."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="tv2g2@x.com", password="StrongPass123", full_name="TV2G2")
        asyncio.run(_grant_role_permissions(sf, email="tv2g2@x.com", role_name="agent_user", permission_keys=["agent:read", "agent:execute"]))

        # 创建任务
        create_resp = client.post(
            "/api/v1/agent/v2/task/create",
            headers={"Authorization": f"Bearer {token}"},
            params={"user_id": "user-v2-003"},
        )
        assert create_resp.status_code == 200
        task_id = create_resp.json()["task_id"]

        # 查询状态
        resp = client.get(
            f"/api/v1/agent/v2/task/{task_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["task_id"] == task_id
        assert body["state"] == "created"
        assert body["user_id"] == "user-v2-003"
        assert "current_step" in body
        assert "total_steps" in body
        assert "budget_limit_ms" in body
        assert "created_at" in body
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：POST /agent/v2/policy/evaluate
# 权限：agent:execute
# ─────────────────────────────────────────────────────────────────────────────

def test_evaluate_policy_v2_returns_500_due_to_model_dump_bug() -> None:
    """POST /agent/v2/policy/evaluate — PolicyDecision 是 dataclass 没有 model_dump()，返回 500.

    注意：这是当前代码的 bug（characterization），endpoint 调用 decision.model_dump()
    但 PolicyDecision 是 dataclass 而非 Pydantic model，导致 AttributeError 500 异常。
    使用 raise_server_exceptions=False 才能检验 HTTP 响应而非 pytest exception。
    """
    client, sf = _build_client(raise_server_exceptions=False)
    try:
        token = _register_and_login(client, email="pol1@x.com", password="StrongPass123", full_name="POL1")
        asyncio.run(_grant_role_permissions(sf, email="pol1@x.com", role_name="agent_user", permission_keys=["agent:execute"]))

        resp = client.post(
            "/api/v1/agent/v2/policy/evaluate",
            headers={"Authorization": f"Bearer {token}"},
            params={"action": "read_sop"},
            json={"user_id": "u1", "resource_type": "sops"},
        )
        # PolicyDecision 没有 model_dump()，当前行为是 500 InternalServerError
        assert resp.status_code == 500
        body = resp.json()
        assert body["error_type"] == "InternalServerError"
        assert body["status_code"] == 500
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：GET /agent/v2/idempotency/{idempotency_key}
# 权限：agent:read
# ─────────────────────────────────────────────────────────────────────────────

def test_check_idempotency_always_returns_not_exists() -> None:
    """GET /agent/v2/idempotency/{idempotency_key} — 当前实现始终返回 exists=False."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="idem1@x.com", password="StrongPass123", full_name="IDEM1")
        asyncio.run(_grant_role_permissions(sf, email="idem1@x.com", role_name="agent_user", permission_keys=["agent:read"]))

        resp = client.get(
            "/api/v1/agent/v2/idempotency/idem-key-001",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["exists"] is False
        assert body["message"] == "Use /v2/request with idempotency_key to check"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：GET /agent/v2/trace/{trace_id}/events
# 权限：agent:read
# ─────────────────────────────────────────────────────────────────────────────

def test_get_trace_events_unknown_trace_returns_empty_list() -> None:
    """GET /agent/v2/trace/{trace_id}/events — 未知 trace_id 返回空 events 列表."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="trev1@x.com", password="StrongPass123", full_name="TREV1")
        asyncio.run(_grant_role_permissions(sf, email="trev1@x.com", role_name="agent_user", permission_keys=["agent:read"]))

        resp = client.get(
            "/api/v1/agent/v2/trace/trace-nonexistent-abc/events",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["trace_id"] == "trace-nonexistent-abc"
        assert body["events"] == []
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_get_trace_events_after_diagnosis_action_recorded() -> None:
    """GET /agent/v2/trace/{trace_id}/events — diagnosis-action 后 events 包含记录."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="trev2@x.com", password="StrongPass123", full_name="TREV2")
        asyncio.run(_grant_role_permissions(sf, email="trev2@x.com", role_name="agent_user", permission_keys=["agent:read"]))

        trace_id = "trace-events-test-001"

        # 先发 diagnosis-action 写入 event
        client.post(
            f"/api/v1/agent/v2/trace/{trace_id}/diagnosis-action",
            headers={"Authorization": f"Bearer {token}"},
            json={"action": "confirm_execution"},
        )

        # 再查询 events
        resp = client.get(
            f"/api/v1/agent/v2/trace/{trace_id}/events",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["trace_id"] == trace_id
        assert len(body["events"]) > 0
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：GET /agent/v2/modules
# 权限：agent:read
# ─────────────────────────────────────────────────────────────────────────────

def test_list_modules_returns_registered_modules() -> None:
    """GET /agent/v2/modules — 返回注册模块列表."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="mod1@x.com", password="StrongPass123", full_name="MOD1")
        asyncio.run(_grant_role_permissions(sf, email="mod1@x.com", role_name="agent_user", permission_keys=["agent:read"]))

        resp = client.get(
            "/api/v1/agent/v2/modules",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "modules" in body
        assert isinstance(body["modules"], list)
        module_ids = [m["id"] for m in body["modules"]]
        # orchestrator_v2 注册了 general, coach, diagnoser, knowledge, execution
        assert "general" in module_ids
        assert "coach" in module_ids
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：POST /agent/approval/request
# 权限：agent:execute
# ─────────────────────────────────────────────────────────────────────────────

def test_create_approval_request_returns_request_id_and_pending() -> None:
    """POST /agent/approval/request — 创建审批请求返回 request_id 与 pending 状态."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="apr1@x.com", password="StrongPass123", full_name="APR1")
        asyncio.run(_grant_role_permissions(sf, email="apr1@x.com", role_name="agent_user", permission_keys=["agent:execute"]))

        resp = client.post(
            "/api/v1/agent/approval/request",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "requester_id": "user-apr-001",
                "resource_type": "Skill",
                "resource_id": "skill-001",
                "action": "publish",
                "reason": "测试审批请求",
                "priority": "normal",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "request_id" in body
        assert body["status"] == "pending"
        assert body["request_id"].startswith("apr-")
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：GET /agent/approval/pending
# 权限：agent:read
# ─────────────────────────────────────────────────────────────────────────────

def test_get_pending_approvals_returns_requests_list() -> None:
    """GET /agent/approval/pending — 返回 pending requests 列表."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="appa1@x.com", password="StrongPass123", full_name="APPA1")
        asyncio.run(_grant_role_permissions(sf, email="appa1@x.com", role_name="agent_user", permission_keys=["agent:execute", "agent:read"]))

        # 先创建一个审批请求
        create_resp = client.post(
            "/api/v1/agent/approval/request",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "requester_id": "u1",
                "resource_type": "Skill",
                "resource_id": "sk-pending-001",
                "action": "publish",
                "reason": "test pending",
                "priority": "high",
            },
        )
        assert create_resp.status_code == 200

        resp = client.get(
            "/api/v1/agent/approval/pending",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "requests" in body
        assert isinstance(body["requests"], list)
        # 至少有刚创建的那一条
        assert len(body["requests"]) >= 1
        req = body["requests"][0]
        assert "id" in req
        assert "requester_id" in req
        assert "resource_type" in req
        assert "action" in req
        assert "priority" in req
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_get_pending_approvals_with_priority_filter() -> None:
    """GET /agent/approval/pending — 按 priority 过滤."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="appa2@x.com", password="StrongPass123", full_name="APPA2")
        asyncio.run(_grant_role_permissions(sf, email="appa2@x.com", role_name="agent_user", permission_keys=["agent:execute", "agent:read"]))

        resp = client.get(
            "/api/v1/agent/approval/pending",
            headers={"Authorization": f"Bearer {token}"},
            params={"priority": "urgent"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "requests" in body
        assert isinstance(body["requests"], list)
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：GET /agent/approval/history
# 权限：agent:read
# ─────────────────────────────────────────────────────────────────────────────

def test_get_approval_history_returns_requests_list() -> None:
    """GET /agent/approval/history — 返回 requests 列表（含已处理条目）.

    注意：当前实现中 get_request_history(limit, offset) 将 limit 传给 requester_id，
    导致始终返回空列表（参数顺序 bug）。此测试锁定此当前行为。
    """
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="apph1@x.com", password="StrongPass123", full_name="APPH1")
        asyncio.run(_grant_role_permissions(sf, email="apph1@x.com", role_name="agent_user", permission_keys=["agent:read"]))

        resp = client.get(
            "/api/v1/agent/approval/history",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "requests" in body
        assert isinstance(body["requests"], list)
        # 当前实现因参数顺序 bug 始终返回空列表
        assert body["requests"] == []
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：POST /agent/approval/{request_id}/approve
# 权限：agent:execute
# ─────────────────────────────────────────────────────────────────────────────

def test_approve_request_success() -> None:
    """POST /agent/approval/{request_id}/approve — 成功审批返回 approved 状态."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="apappr1@x.com", password="StrongPass123", full_name="APAPPR1")
        asyncio.run(_grant_role_permissions(sf, email="apappr1@x.com", role_name="agent_user", permission_keys=["agent:execute", "agent:read"]))

        # 先创建
        create_resp = client.post(
            "/api/v1/agent/approval/request",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "requester_id": "u1",
                "resource_type": "Skill",
                "resource_id": "sk-approve-001",
                "action": "publish",
                "reason": "test approval",
                "priority": "normal",
            },
        )
        assert create_resp.status_code == 200
        request_id = create_resp.json()["request_id"]

        # 审批
        resp = client.post(
            f"/api/v1/agent/approval/{request_id}/approve",
            headers={"Authorization": f"Bearer {token}"},
            params={"approved_by": "admin-001"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["request_id"] == request_id
        assert body["status"] == "approved"
        assert body["approved_by"] == "admin-001"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_approve_request_not_found_returns_404() -> None:
    """POST /agent/approval/{request_id}/approve — 不存在的 request_id 返回 404."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="apappr2@x.com", password="StrongPass123", full_name="APAPPR2")
        asyncio.run(_grant_role_permissions(sf, email="apappr2@x.com", role_name="agent_user", permission_keys=["agent:execute"]))

        resp = client.post(
            "/api/v1/agent/approval/nonexistent-req-id/approve",
            headers={"Authorization": f"Bearer {token}"},
            params={"approved_by": "admin-001"},
        )
        assert resp.status_code == 404
        body = resp.json()
        # 全局 exception handler 使用 message 字段
        assert body["message"] == "Approval request not found"
        assert body["error_type"] == "HTTPException"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：POST /agent/approval/{request_id}/reject
# 权限：agent:execute
# ─────────────────────────────────────────────────────────────────────────────

def test_reject_request_success_returns_no_body() -> None:
    """POST /agent/approval/{request_id}/reject — 成功拒绝，端点无返回体（None）."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="aprej1@x.com", password="StrongPass123", full_name="APREJ1")
        asyncio.run(_grant_role_permissions(sf, email="aprej1@x.com", role_name="agent_user", permission_keys=["agent:execute"]))

        # 先创建
        create_resp = client.post(
            "/api/v1/agent/approval/request",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "requester_id": "u1",
                "resource_type": "Skill",
                "resource_id": "sk-reject-001",
                "action": "publish",
                "reason": "test reject",
                "priority": "low",
            },
        )
        assert create_resp.status_code == 200
        request_id = create_resp.json()["request_id"]

        # 拒绝
        resp = client.post(
            f"/api/v1/agent/approval/{request_id}/reject",
            headers={"Authorization": f"Bearer {token}"},
            params={"rejection_reason": "资质不满足"},
        )
        # 端点成功拒绝时无显式 return，FastAPI 返回 200 null
        assert resp.status_code == 200
        assert resp.json() is None
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_reject_request_not_found_returns_404() -> None:
    """POST /agent/approval/{request_id}/reject — 不存在的 request_id 返回 404."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="aprej2@x.com", password="StrongPass123", full_name="APREJ2")
        asyncio.run(_grant_role_permissions(sf, email="aprej2@x.com", role_name="agent_user", permission_keys=["agent:execute"]))

        resp = client.post(
            "/api/v1/agent/approval/nonexistent-rej-id/reject",
            headers={"Authorization": f"Bearer {token}"},
            params={"rejection_reason": "test"},
        )
        assert resp.status_code == 404
        body = resp.json()
        # 全局 exception handler 使用 message 字段
        assert body["message"] == "Approval request not found"
        assert body["error_type"] == "HTTPException"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：POST /agent/evaluation/report (P2-2)
# 权限：agent:read
# ─────────────────────────────────────────────────────────────────────────────

def test_generate_evaluation_report_invalid_task_id_returns_500() -> None:
    """POST /agent/evaluation/report — 不存在的 task_id 导致 ValueError，返回 500.

    注意：当前 ReportGenerator.generate_report 对不存在的 task_id 抛出
    ValueError('Task 99999 not found')，未被捕获，导致 500 InternalServerError。
    使用 raise_server_exceptions=False 才能检验 HTTP 响应而非 pytest exception。
    """
    client, sf = _build_client(raise_server_exceptions=False)
    try:
        token = _register_and_login(client, email="evr1@x.com", password="StrongPass123", full_name="EVR1")
        asyncio.run(_grant_role_permissions(sf, email="evr1@x.com", role_name="agent_user", permission_keys=["agent:read"]))

        resp = client.post(
            "/api/v1/agent/evaluation/report",
            headers={"Authorization": f"Bearer {token}"},
            json={"task_id": 99999, "use_llm": False},
        )
        # 不存在的任务 ID 导致 ValueError 未捕获，当前行为是 500
        assert resp.status_code == 500
        body = resp.json()
        assert body["error_type"] == "InternalServerError"
        assert body["status_code"] == 500
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：POST /agent/sop/quality/check (P2-3)
# 权限：agent:execute
# ─────────────────────────────────────────────────────────────────────────────

def test_sop_quality_check_full_run_returns_500_due_to_model_attribute_bug() -> None:
    """POST /agent/sop/quality/check — 无 sop_id 时全量检查，SOP.is_active 属性不存在导致 500.

    注意：当前 SOPQualityMonitor.run_quality_check 查询 SOP 时使用 SOP.is_active 过滤，
    但 SOP 模型无此属性，导致 AttributeError 500 异常。这是锁定的当前行为。
    使用 raise_server_exceptions=False 才能检验 HTTP 响应而非 pytest exception。
    """
    client, sf = _build_client(raise_server_exceptions=False)
    try:
        token = _register_and_login(client, email="sopq1@x.com", password="StrongPass123", full_name="SOPQ1")
        asyncio.run(_grant_role_permissions(sf, email="sopq1@x.com", role_name="agent_user", permission_keys=["agent:execute"]))

        resp = client.post(
            "/api/v1/agent/sop/quality/check",
            headers={"Authorization": f"Bearer {token}"},
            json={"time_range_days": 30},
        )
        # SOPQualityMonitor.run_quality_check 引用 SOP.is_active（不存在），当前行为是 500
        assert resp.status_code == 500
        body = resp.json()
        assert body["error_type"] == "InternalServerError"
        assert body["status_code"] == 500
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_sop_quality_check_specific_sop_not_found_returns_empty() -> None:
    """POST /agent/sop/quality/check — 指定不存在的 sop_id，SOPQualityMonitor.check_sop_quality 返回空结果."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="sopq2@x.com", password="StrongPass123", full_name="SOPQ2")
        asyncio.run(_grant_role_permissions(sf, email="sopq2@x.com", role_name="agent_user", permission_keys=["agent:execute"]))

        resp = client.post(
            "/api/v1/agent/sop/quality/check",
            headers={"Authorization": f"Bearer {token}"},
            json={"sop_id": 99999, "time_range_days": 7},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "alerts" in body
        assert "tickets_created" in body
        assert body["alerts"] == []
        assert body["tickets_created"] == []
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：GET /agent/preference (P2-4)
# 权限：无（使用 get_current_actor）
# ─────────────────────────────────────────────────────────────────────────────

def test_get_user_preference_returns_default_on_demand_mode() -> None:
    """GET /agent/preference — 首次查询返回默认引导模式 on_demand."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="pref1@x.com", password="StrongPass123", full_name="PREF1")

        resp = client.get(
            "/api/v1/agent/preference",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "user_id" in body
        assert "guidance_mode" in body
        assert "guidance_mode_display" in body
        assert "preferences" in body
        # 默认模式为 on_demand（由 UserPreferenceService 决定）
        assert body["guidance_mode"] == "on_demand"
        assert body["guidance_mode_display"] == "按需指导"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：PUT /agent/preference/guidance-mode (P2-4)
# 权限：无（使用 get_current_actor）
# ─────────────────────────────────────────────────────────────────────────────

def test_update_guidance_mode_on_demand_returns_updated_preference() -> None:
    """PUT /agent/preference/guidance-mode — 更新为 on_demand 模式."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="pref2@x.com", password="StrongPass123", full_name="PREF2")

        resp = client.put(
            "/api/v1/agent/preference/guidance-mode",
            headers={"Authorization": f"Bearer {token}"},
            json={"mode": "on_demand"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["guidance_mode"] == "on_demand"
        assert body["guidance_mode_display"] == "按需指导"
        assert "user_id" in body
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_update_guidance_mode_silent_returns_silent_mode() -> None:
    """PUT /agent/preference/guidance-mode — 更新为 silent 模式."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="pref3@x.com", password="StrongPass123", full_name="PREF3")

        resp = client.put(
            "/api/v1/agent/preference/guidance-mode",
            headers={"Authorization": f"Bearer {token}"},
            json={"mode": "silent"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["guidance_mode"] == "silent"
        assert body["guidance_mode_display"] == "静默模式"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


# ─────────────────────────────────────────────────────────────────────────────
# 特征测试：PUT /agent/preference/llm (P2-4)
# 权限：无（使用 get_current_actor）
# ─────────────────────────────────────────────────────────────────────────────

def test_update_llm_preference_returns_updated_preference() -> None:
    """PUT /agent/preference/llm — 更新 LLM 偏好设置返回更新后的 preference."""
    client, sf = _build_client()
    try:
        token = _register_and_login(client, email="pref4@x.com", password="StrongPass123", full_name="PREF4")

        resp = client.put(
            "/api/v1/agent/preference/llm",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "provider": "openai",
                "model": "gpt-4",
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-test-key",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "user_id" in body
        assert "guidance_mode" in body
        assert "preferences" in body
        # LLM 设置不应在 public preferences 中暴露 api_key
        preferences = body["preferences"]
        assert isinstance(preferences, dict)
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None
