"""
T-03-d knowledge API tests (current endpoint capability).
"""
from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.api.v1.endpoints.agent as agent_endpoints
import app.models as app_models  # noqa: F401  # ensure metadata is fully loaded
from app.core.database import get_db
from app.models.base import Base
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User
from main import app


@pytest.fixture(scope="module")
def knowledge_api_env() -> tuple[TestClient, async_sessionmaker[AsyncSession]]:
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
            "full_name": "Knowledge API User",
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


async def _get_user_id(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    email: str,
) -> int:
    async with session_factory() as session:
        user_result = await session.execute(select(User.id).where(User.email == email))
        user_id = user_result.scalar_one()
        return int(user_id)


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_knowledge_submit_and_status_query(
    knowledge_api_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = knowledge_api_env
    agent_endpoints.knowledge_governance._knowledge_store.clear()
    agent_endpoints.knowledge_upload_jobs.clear()

    email = f"knowledge_status_{uuid4().hex[:8]}@example.com"
    token = _register_and_login(client, email=email)
    user_id = asyncio.run(_get_user_id(session_factory, email=email))
    asyncio.run(
        _grant_role_permissions(
            session_factory,
            email=email,
            role_name="knowledge_editor",
            permission_keys=["agent:execute", "agent:read"],
        )
    )

    create_resp = client.post(
        "/api/v1/agent/knowledge",
        headers=_auth_headers(token),
        json={
            "type": "document",
            "title": "Knowledge Draft",
            "content": "draft content",
            "scope": {"device_model": ["ABB-IRB120"]},
            "risk_level": "R1",
        },
    )
    assert create_resp.status_code == 200
    payload = create_resp.json()
    entry_id = payload["id"]
    assert payload["status"] == "DRAFT"
    assert agent_endpoints.knowledge_governance._knowledge_store[entry_id].created_by == str(user_id)

    submit_resp = client.post(
        f"/api/v1/agent/knowledge/{entry_id}/submit",
        headers=_auth_headers(token),
    )
    assert submit_resp.status_code == 200
    assert submit_resp.json()["status"] == "submitted"

    query_pending_resp = client.post(
        "/api/v1/agent/knowledge/search",
        headers=_auth_headers(token),
        json={"query": "Knowledge", "status": "PENDING"},
    )
    assert query_pending_resp.status_code == 200
    results = query_pending_resp.json()["results"]
    assert any(item["id"] == entry_id for item in results)


def test_knowledge_search_respects_brand_filter(
    knowledge_api_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = knowledge_api_env
    agent_endpoints.knowledge_governance._knowledge_store.clear()
    agent_endpoints.knowledge_upload_jobs.clear()

    email = f"knowledge_filter_{uuid4().hex[:8]}@example.com"
    token = _register_and_login(client, email=email)
    user_id = asyncio.run(_get_user_id(session_factory, email=email))
    asyncio.run(
        _grant_role_permissions(
            session_factory,
            email=email,
            role_name="knowledge_reviewer",
            permission_keys=["agent:execute", "agent:read"],
        )
    )

    abb_resp = client.post(
        "/api/v1/agent/knowledge",
        headers=_auth_headers(token),
        json={
            "type": "solution",
            "title": "ABB motor handling",
            "content": "ABB only",
            "scope": {"device_model": ["ABB-IRB120"]},
            "risk_level": "R1",
        },
    )
    fanuc_resp = client.post(
        "/api/v1/agent/knowledge",
        headers=_auth_headers(token),
        json={
            "type": "solution",
            "title": "FANUC motor handling",
            "content": "FANUC only",
            "scope": {"device_model": ["FANUC-M10"]},
            "risk_level": "R1",
        },
    )
    assert abb_resp.status_code == 200
    assert fanuc_resp.status_code == 200
    abb_id = abb_resp.json()["id"]
    fanuc_id = fanuc_resp.json()["id"]

    for entry_id in (abb_id, fanuc_id):
        submit_resp = client.post(
            f"/api/v1/agent/knowledge/{entry_id}/submit",
            headers=_auth_headers(token),
        )
        assert submit_resp.status_code == 200

        approve_resp = client.post(
            f"/api/v1/agent/knowledge/{entry_id}/approve",
            headers=_auth_headers(token),
            json={"decision": "approve", "feedback": "ok", "rating": 5.0},
        )
        assert approve_resp.status_code == 200
        assert agent_endpoints.knowledge_governance._knowledge_store[entry_id].approved_by == str(user_id)

    fanuc_query_resp = client.post(
        "/api/v1/agent/knowledge/search",
        headers=_auth_headers(token),
        json={
            "query": "motor",
            "device_model": "FANUC-M10",
            "status": "APPROVED",
        },
    )
    assert fanuc_query_resp.status_code == 200
    result_ids = {item["id"] for item in fanuc_query_resp.json()["results"]}
    assert fanuc_id in result_ids
    assert abb_id not in result_ids


def test_knowledge_upload_creates_job_and_supports_status_query(
    knowledge_api_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = knowledge_api_env
    agent_endpoints.knowledge_governance._knowledge_store.clear()
    agent_endpoints.knowledge_upload_jobs.clear()

    email = f"knowledge_upload_{uuid4().hex[:8]}@example.com"
    token = _register_and_login(client, email=email)
    asyncio.run(
        _grant_role_permissions(
            session_factory,
            email=email,
            role_name="knowledge_uploader",
            permission_keys=["agent:execute", "agent:read"],
        )
    )

    tiny_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
    upload_resp = client.post(
        "/api/v1/agent/knowledge/upload?brand=ABB",
        headers=_auth_headers(token),
        files={"file": ("tiny.pdf", tiny_pdf, "application/pdf")},
    )
    assert upload_resp.status_code == 200
    upload_payload = upload_resp.json()
    assert upload_payload["status"] == "completed"
    assert upload_payload["filename"] == "tiny.pdf"
    assert upload_payload["brand"] == "ABB"
    job_id = upload_payload["job_id"]

    status_resp = client.get(
        f"/api/v1/agent/knowledge/upload/{job_id}",
        headers=_auth_headers(token),
    )
    assert status_resp.status_code == 200
    status_payload = status_resp.json()
    assert status_payload["job_id"] == job_id
    assert status_payload["status"] == "completed"
