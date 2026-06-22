from __future__ import annotations

import asyncio
from io import BytesIO
import zipfile
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models as app_models  # noqa: F401
from app.core.database import get_db
from app.models.base import Base
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.robot_project import RobotProject
from app.models.robot_project_file import RobotProjectFile
from app.models.school import School
from app.models.user import User
from main import app

# onboarding 注册需要的白名单学校（测试统一使用）
TEST_SCHOOL_NAME = "测试学校"


@pytest.fixture(scope="module")
def robot_project_api_env() -> tuple[TestClient, async_sessionmaker[AsyncSession]]:
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

    with TestClient(app) as client:
        yield client, session_factory

    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _build_robot_project_zip() -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("docs/maintenance.md", "# Fourier N1\n肘关节执行器检查步骤")
        archive.writestr("structure/N1.urdf", "<robot name='FourierN1'></robot>")
        archive.writestr("viewer/elbow.glb", b"glb")
    return buffer.getvalue()


def _register_and_login(client: TestClient, *, email: str) -> str:
    register_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPass123",
            "full_name": "Robot Project User",
            "role": "teacher",
            "school_name": TEST_SCHOOL_NAME,
        },
    )
    assert register_resp.status_code == 201

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert login_resp.status_code == 200
    return login_resp.json()["access_token"]


async def _grant_permissions(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    email: str,
) -> None:
    async with session_factory() as session:
        user = (
            await session.execute(select(User).where(User.email == email))
        ).scalar_one()

        role = Role(name=f"robot_project_editor_{uuid4().hex[:6]}", description="robot project editor")
        permission_keys = ["agent:execute", "agent:read"]
        session.add(role)
        await session.flush()

        for permission_key in permission_keys:
            permission = (
                await session.execute(select(Permission).where(Permission.key == permission_key))
            ).scalar_one_or_none()
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

            session.add(RolePermission(role_id=role.id, permission_id=permission.id))

        session.add(UserRole(user_id=user.id, role_id=role.id))
        await session.commit()


@pytest.mark.asyncio
async def test_upload_knowledge_file_persists_robot_project_job(
    robot_project_api_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = robot_project_api_env
    email = f"robot_upload_{uuid4().hex[:8]}@example.com"
    token = _register_and_login(client, email=email)
    await _grant_permissions(session_factory, email=email)

    response = client.post(
        "/api/v1/agent/knowledge/upload?brand=Fourier&model=N1&version=v1",
        headers=_auth_headers(token),
        files={"file": ("FourierN1.zip", BytesIO(_build_robot_project_zip()), "application/zip")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "uploaded"
    assert payload["project_id"] == payload["job_id"]
    assert payload["filename"] == "FourierN1.zip"

    async with session_factory() as session:
        project = (
            await session.execute(select(RobotProject).where(RobotProject.id == payload["project_id"]))
        ).scalar_one()
        project_files = (
            await session.execute(select(RobotProjectFile).where(RobotProjectFile.project_id == project.id))
        ).scalars().all()

    assert project.brand == "Fourier"
    assert project.model == "N1"
    assert project.version == "v1"
    assert any(project_file.filename == "FourierN1.zip" for project_file in project_files)

    status_resp = client.get(
        f"/api/v1/agent/knowledge/upload/{payload['job_id']}",
        headers=_auth_headers(token),
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["project_id"] == project.id
    assert status_resp.json()["status"] == "ready"

    list_resp = client.get(
        "/api/v1/agent/knowledge/projects",
        headers=_auth_headers(token),
    )
    assert list_resp.status_code == 200
    list_payload = list_resp.json()
    assert len(list_payload["projects"]) == 1
    assert list_payload["projects"][0]["project_id"] == project.id
    assert list_payload["projects"][0]["status"] == "ready"
    assert list_payload["projects"][0]["ingest_summary"]["files_total"] >= 3

    manifest_resp = client.get(
        f"/api/v1/agent/knowledge/projects/{project.id}/manifest",
        headers=_auth_headers(token),
    )
    assert manifest_resp.status_code == 200
    manifest_payload = manifest_resp.json()
    assert manifest_payload["viewer_manifest"]["parts"] == ["viewer/elbow.glb"]

    asset_resp = client.get(
        f"/api/v1/agent/knowledge/projects/{project.id}/assets/viewer/elbow.glb",
        headers=_auth_headers(token),
    )
    assert asset_resp.status_code == 200
    assert asset_resp.content == b"glb"
