"""
T-03-a API auth boundary tests.
"""
from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models as app_models  # noqa: F401  # ensure metadata is fully loaded
from app.core.database import get_db
from app.models.base import Base
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User
from app.services.authz_guard import get_current_actor
from main import app


def _has_auth_dependency(dependant) -> bool:
    if dependant.call == get_current_actor:
        return True
    return any(_has_auth_dependency(child) for child in dependant.dependencies)


def _sample_path(path: str) -> str:
    replacements = {
        "{ref_id}": "ref-1",
        "{trace_id}": "trace-1",
        "{id}": "1",
        "{user_id}": "1",
        "{task_id}": "task-1",
        "{entry_id}": "entry-1",
        "{step_id}": "step-1",
        "{action_type}": "inspect",
        "{flag_name}": "feature-a",
        "{evidence_id}": "ev-1",
        "{plan_id}": "plan-1",
        "{request_id}": "req-1",
        "{decision_id}": "dec-1",
        "{metric_id}": "metric-1",
        "{alert_id}": "alert-1",
        "{idempotency_key}": "idem-1",
    }
    output = path
    for raw, sample in replacements.items():
        output = output.replace(raw, sample)
    return output


def _collect_protected_endpoints() -> list[tuple[str, str]]:
    endpoints: list[tuple[str, str]] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith("/api/v1"):
            continue
        if not _has_auth_dependency(route.dependant):
            continue

        for method in sorted(m for m in route.methods if m in {"GET", "POST", "PUT", "PATCH", "DELETE"}):
            endpoints.append((method, route.path))

    return sorted(endpoints, key=lambda item: (item[0], item[1]))


PROTECTED_ENDPOINTS = _collect_protected_endpoints()


@pytest.fixture(scope="module")
def auth_boundary_env() -> tuple[TestClient, async_sessionmaker[AsyncSession]]:
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

    with TestClient(app) as client:
        yield client, session_factory

    app.dependency_overrides.clear()
    app.state.test_sessionmaker = None
    asyncio.run(engine.dispose())


def _register_and_login(client: TestClient, *, email: str) -> str:
    register_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPass123",
            "full_name": "Auth Boundary",
        },
    )
    assert register_resp.status_code == 201

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert login_resp.status_code == 200
    return login_resp.json()["access_token"]


async def _grant_role_permissions(
    session_factory: async_sessionmaker[AsyncSession],
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
            role = Role(name=role_name, description=f"{role_name} role")
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
                    description=f"{permission_key} permission",
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


@pytest.mark.parametrize(("method", "path"), PROTECTED_ENDPOINTS)
def test_protected_endpoints_require_token(
    auth_boundary_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
    method: str,
    path: str,
) -> None:
    client, _ = auth_boundary_env
    kwargs = {"json": {}} if method in {"POST", "PUT", "PATCH"} else {}
    response = client.request(method, _sample_path(path), **kwargs)
    assert response.status_code == 401, (
        f"Expected 401 without token, got {response.status_code} for {method} {path}: {response.text[:200]}"
    )


def test_student_token_cannot_update_admin_role(
    auth_boundary_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = auth_boundary_env
    email = f"student_boundary_{uuid4().hex[:8]}@example.com"
    token = _register_and_login(client, email=email)

    asyncio.run(
        _grant_role_permissions(
            session_factory,
            email=email,
            role_name="student",
            permission_keys=["agent:read"],
        )
    )

    response = client.post(
        "/api/v1/admin/users/1/role",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": "teacher"},
    )
    assert response.status_code == 403
    payload = response.json()
    assert payload["error_type"] in {"RoleRequiredError", "PermissionDeniedError"}


def test_removed_legacy_ai_endpoints_return_404(
    auth_boundary_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, _ = auth_boundary_env
    email = f"deprecated_boundary_{uuid4().hex[:8]}@example.com"
    token = _register_and_login(client, email=email)
    headers = {"Authorization": f"Bearer {token}"}

    command_resp = client.post(
        "/api/v1/ai/commands",
        headers=headers,
        json={
            "intent": "get_robot_structure",
            "skill_id": "robot.read.structure",
            "tool_name": "robot.get_structure",
            "tool_args": {"robot_id": "R-001"},
            "side_effects": [],
        },
    )
    assert command_resp.status_code == 404

    rag_resp = client.post(
        "/api/v1/ai/rag/query",
        headers=headers,
        json={"input_text": "电机异常如何排查", "tool_args": {"query": "电机异常"}},
    )
    assert rag_resp.status_code == 404
