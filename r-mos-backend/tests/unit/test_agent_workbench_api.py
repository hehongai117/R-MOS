"""
AI 工作台 API 最小回归测试。
"""
from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.models.audit_event import AuditEvent
from app.models.base import Base
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.school import School
from app.models.user import User
from main import app
import app.models as app_models  # noqa: F401  # 确保模型全部注册

# onboarding 注册需要的白名单学校（测试统一使用）
TEST_SCHOOL_NAME = "测试学校"


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


async def _grant_role(
    session_factory: async_sessionmaker,
    *,
    email: str,
    role_name: str,
    permission_keys: list[str],
) -> None:
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

            existing_role_permission = await session.execute(
                select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == permission.id,
                )
            )
            if existing_role_permission.scalar_one_or_none() is None:
                session.add(RolePermission(role_id=role.id, permission_id=permission.id))

        existing_user_role = await session.execute(
            select(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.role_id == role.id,
            )
        )
        if existing_user_role.scalar_one_or_none() is None:
            session.add(UserRole(user_id=user.id, role_id=role.id))

        await session.commit()


async def _get_diagnosis_action_denial(
    session_factory: async_sessionmaker,
    *,
    actor_user_id: int,
    trace_id: str,
) -> AuditEvent | None:
    async with session_factory() as session:
        result = await session.execute(
            select(AuditEvent)
            .where(
                AuditEvent.actor_user_id == str(actor_user_id),
                AuditEvent.action == "diagnosis_action",
                AuditEvent.resource_type == "diagnosis_trace",
                AuditEvent.resource_id == trace_id,
                AuditEvent.decision == "deny",
            )
            .order_by(AuditEvent.id.desc())
        )
        return result.scalars().first()


def _register_and_login(client: TestClient, *, email: str) -> tuple[int, str]:
    register_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPass123",
            "full_name": "AI Workbench User",
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


def test_student_message_mode_allows_ai_workbench_requests() -> None:
    client, session_factory = _build_client()
    try:
        user_id, token = _register_and_login(client, email="student_workbench@example.com")
        asyncio.run(
            _grant_role(
                session_factory,
                email="student_workbench@example.com",
                role_name="student",
                permission_keys=["agent:read"],
            )
        )

        response = client.post(
            "/api/v1/agent/execute",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "user_id": str(user_id),
                "mode": "message",
                "message": "查看我当前进行中的任务和状态。",
                "intent_classification": "general",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["mode_used"] == "message"
        assert payload["status"] == "success"
        assert payload["result"]["success"] is True
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_student_command_mode_still_requires_execute_permission() -> None:
    client, session_factory = _build_client()
    try:
        user_id, token = _register_and_login(client, email="student_command@example.com")
        asyncio.run(
            _grant_role(
                session_factory,
                email="student_command@example.com",
                role_name="student",
                permission_keys=["agent:read"],
            )
        )

        response = client.post(
            "/api/v1/agent/execute",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "user_id": str(user_id),
                "mode": "command",
                "intent": "dispatch",
                "tool_name": "assignments.create_draft",
                "tool_args": {"input_text": "创建任务"},
            },
        )

        assert response.status_code == 403
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_student_can_record_diagnosis_action_on_trace() -> None:
    client, session_factory = _build_client()
    try:
        user_id, token = _register_and_login(client, email="student_diagnosis_action@example.com")
        asyncio.run(
            _grant_role(
                session_factory,
                email="student_diagnosis_action@example.com",
                role_name="student",
                permission_keys=["agent:read"],
            )
        )

        trace_id = "trace-123"
        execute_response = client.post(
            "/api/v1/agent/execute",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "user_id": str(user_id),
                "mode": "message",
                "message": "检查当前状态。",
                "intent_classification": "general",
                "trace_id": trace_id,
            },
        )
        assert execute_response.status_code == 200

        response = client.post(
            f"/api/v1/agent/v2/trace/{trace_id}/diagnosis-action",
            headers={"Authorization": f"Bearer {token}"},
            json={"action": "escalate_to_teacher"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["trace_id"] == trace_id
        assert payload["action"] == "escalate_to_teacher"
        assert "教师审核" in payload["message"]
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_diagnosis_action_rejects_other_user_and_allows_trace_owner() -> None:
    client, session_factory = _build_client()
    try:
        owner_id, owner_token = _register_and_login(
            client, email="diagnosis_trace_owner@example.com"
        )
        other_id, other_token = _register_and_login(
            client, email="diagnosis_trace_other@example.com"
        )
        for email in (
            "diagnosis_trace_owner@example.com",
            "diagnosis_trace_other@example.com",
        ):
            asyncio.run(
                _grant_role(
                    session_factory,
                    email=email,
                    role_name="student",
                    permission_keys=["agent:read"],
                )
            )

        trace_id = "trace-diagnosis-owned-001"
        execute_response = client.post(
            "/api/v1/agent/execute",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={
                "user_id": str(owner_id),
                "mode": "message",
                "message": "检查当前状态。",
                "intent_classification": "general",
                "trace_id": trace_id,
            },
        )
        assert execute_response.status_code == 200
        assert execute_response.json()["trace_id"] == trace_id

        denied_response = client.post(
            f"/api/v1/agent/v2/trace/{trace_id}/diagnosis-action",
            headers={"Authorization": f"Bearer {other_token}"},
            json={"action": "confirm_execution"},
        )
        assert denied_response.status_code == 403
        denial = asyncio.run(
            _get_diagnosis_action_denial(
                session_factory,
                actor_user_id=other_id,
                trace_id=trace_id,
            )
        )
        assert denial is not None
        assert denial.reason == "not_object_owner"

        allowed_response = client.post(
            f"/api/v1/agent/v2/trace/{trace_id}/diagnosis-action",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"action": "confirm_execution"},
        )
        assert allowed_response.status_code == 200
        assert allowed_response.json()["recorded"] is True
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_diagnosis_action_rejects_unknown_trace_for_non_admin() -> None:
    client, session_factory = _build_client()
    try:
        user_id, token = _register_and_login(
            client, email="diagnosis_unknown_trace@example.com"
        )
        asyncio.run(
            _grant_role(
                session_factory,
                email="diagnosis_unknown_trace@example.com",
                role_name="student",
                permission_keys=["agent:read"],
            )
        )

        trace_id = "trace-diagnosis-unknown-001"
        response = client.post(
            f"/api/v1/agent/v2/trace/{trace_id}/diagnosis-action",
            headers={"Authorization": f"Bearer {token}"},
            json={"action": "confirm_execution"},
        )
        assert response.status_code == 403
        denial = asyncio.run(
            _get_diagnosis_action_denial(
                session_factory,
                actor_user_id=user_id,
                trace_id=trace_id,
            )
        )
        assert denial is not None
        assert denial.reason == "unowned_object"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_diagnosis_action_allows_admin_for_unknown_trace() -> None:
    client, session_factory = _build_client()
    try:
        _user_id, token = _register_and_login(
            client, email="diagnosis_unknown_trace_admin@example.com"
        )
        asyncio.run(
            _grant_role(
                session_factory,
                email="diagnosis_unknown_trace_admin@example.com",
                role_name="admin",
                permission_keys=["agent:read"],
            )
        )

        response = client.post(
            "/api/v1/agent/v2/trace/trace-diagnosis-unknown-admin/diagnosis-action",
            headers={"Authorization": f"Bearer {token}"},
            json={"action": "escalate_to_teacher"},
        )
        assert response.status_code == 200
        assert response.json()["recorded"] is True
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None
