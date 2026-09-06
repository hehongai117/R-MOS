"""
T-03-d knowledge API tests (current endpoint capability).
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.api.v1.endpoints.agent as agent_endpoints
import app.api.v1.endpoints.agent_knowledge as knowledge_endpoints
import app.models as app_models  # noqa: F401  # ensure metadata is fully loaded
from app.core.database import get_db
from app.models.base import Base
from app.models.knowledge_chunk import AIKnowledgeChunk
from app.models.knowledge_document import KnowledgeDocument
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.robot_project_file import RobotProjectFile
from app.models.school import School
from app.models.user import User
from main import app

# onboarding 注册需要的白名单学校（测试统一使用）
TEST_SCHOOL_NAME = "测试学校"
OTHER_TEST_SCHOOL_NAME = "另一所测试学校"


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
            await conn.execute(
                School.__table__.insert(),
                [
                    {"name": TEST_SCHOOL_NAME},
                    {"name": OTHER_TEST_SCHOOL_NAME},
                ],
            )

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


def _register_and_login(
    client: TestClient,
    *,
    email: str,
    school_name: str = TEST_SCHOOL_NAME,
) -> str:
    register_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPass123",
            "full_name": "Knowledge API User",
            "role": "teacher",
            "school_name": school_name,
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


async def _retrieval_record_counts(
    session_factory: async_sessionmaker[AsyncSession],
) -> tuple[int, int]:
    async with session_factory() as session:
        chunk_count = await session.scalar(select(func.count()).select_from(AIKnowledgeChunk))
        document_count = await session.scalar(select(func.count()).select_from(KnowledgeDocument))
        return int(chunk_count or 0), int(document_count or 0)


async def _project_file_and_chunks(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    project_id: str,
) -> tuple[RobotProjectFile, list[AIKnowledgeChunk]]:
    async with session_factory() as session:
        project_file = (
            await session.execute(
                select(RobotProjectFile).where(RobotProjectFile.project_id == project_id)
            )
        ).scalar_one()
        chunks = (
            await session.execute(
                select(AIKnowledgeChunk).where(
                    AIKnowledgeChunk.metadata_json["robot_project_id"].as_string() == project_id
                )
            )
        ).scalars().all()
        return project_file, list(chunks)


def test_knowledge_create_persists_without_touching_tracked_store(
    knowledge_api_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = knowledge_api_env
    agent_endpoints.knowledge_governance._knowledge_store.clear()

    tracked_store_path = Path(__file__).parents[2] / "data" / "knowledge_store.json"
    tracked_store_before = tracked_store_path.read_bytes()

    email = f"knowledge_store_{uuid4().hex[:8]}@example.com"
    token = _register_and_login(client, email=email)
    asyncio.run(
        _grant_role_permissions(
            session_factory,
            email=email,
            role_name="knowledge_store_editor",
            permission_keys=["agent:execute"],
        )
    )

    create_resp = client.post(
        "/api/v1/agent/knowledge",
        headers=_auth_headers(token),
        json={
            "type": "document",
            "title": "Isolated knowledge store",
            "content": "persisted outside the tracked worktree data file",
            "risk_level": "R1",
        },
    )

    assert create_resp.status_code == 200
    entry_id = create_resp.json()["id"]
    persisted_store = json.loads(
        agent_endpoints.knowledge_governance._store_path.read_text(encoding="utf-8")
    )
    assert entry_id in persisted_store
    assert agent_endpoints.knowledge_governance._store_path.resolve().is_relative_to(
        Path("/tmp").resolve()
    )
    assert tracked_store_path.read_bytes() == tracked_store_before


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
    """这是当前行为，疑似缺陷 C-AUTH-02：作者可自批，待模块 C 改造时处置。"""
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
    assert upload_payload["status"] == "uploaded"
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
    assert status_payload["status"] == "ready"


@pytest.mark.parametrize(
    ("method", "path", "request_kwargs"),
    [
        ("POST", "/api/v1/agent/knowledge/search", {"json": {"query": "motor"}}),
        (
            "POST",
            "/api/v1/agent/knowledge",
            {"json": {"title": "denied", "content": "denied", "type": "solution"}},
        ),
        (
            "POST",
            "/api/v1/agent/knowledge/upload",
            {"files": {"file": ("denied.txt", b"denied", "text/plain")}},
        ),
        ("GET", "/api/v1/agent/knowledge/upload/missing-job", {}),
        ("GET", "/api/v1/agent/knowledge/projects", {}),
        ("GET", "/api/v1/agent/knowledge/projects/missing-project/manifest", {}),
        (
            "GET",
            "/api/v1/agent/knowledge/projects/missing-project/assets/manual.txt",
            {},
        ),
        ("POST", "/api/v1/agent/knowledge/missing-entry/submit", {}),
        (
            "POST",
            "/api/v1/agent/knowledge/missing-entry/approve",
            {"json": {"decision": "approve"}},
        ),
    ],
    ids=[
        "search",
        "create",
        "upload",
        "upload-job",
        "projects",
        "manifest",
        "asset",
        "submit",
        "approve",
    ],
)
def test_knowledge_routes_reject_user_without_required_permission(
    knowledge_api_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
    method: str,
    path: str,
    request_kwargs: dict,
) -> None:
    """九条路由都有真实 HTTP 权限拒绝断言，防止守卫退化为只测放行。"""
    client, _ = knowledge_api_env
    token = _register_and_login(
        client,
        email=f"knowledge_denied_{uuid4().hex[:8]}@example.com",
    )

    response = client.request(
        method,
        path,
        headers=_auth_headers(token),
        **request_kwargs,
    )

    assert response.status_code == 403
    assert response.json()["details"]["code"] == "AUTHZ_001"


@pytest.mark.parametrize(
    ("path", "request_kwargs"),
    [
        ("/api/v1/agent/knowledge", {"json": {"content": "missing title"}}),
        ("/api/v1/agent/knowledge/upload", {}),
        ("/api/v1/agent/knowledge/missing-entry/approve", {"json": {}}),
    ],
    ids=["create-missing-title", "upload-missing-file", "approve-missing-decision"],
)
def test_knowledge_write_routes_reject_missing_required_input(
    knowledge_api_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
    path: str,
    request_kwargs: dict,
) -> None:
    client, session_factory = knowledge_api_env
    email = f"knowledge_invalid_{uuid4().hex[:8]}@example.com"
    token = _register_and_login(client, email=email)
    asyncio.run(
        _grant_role_permissions(
            session_factory,
            email=email,
            role_name=f"knowledge_invalid_{uuid4().hex[:8]}",
            permission_keys=["agent:execute"],
        )
    )

    response = client.post(path, headers=_auth_headers(token), **request_kwargs)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "invalid_fields",
    [
        {"type": "unknown-type"},
        {"risk_level": "unknown-risk"},
    ],
    ids=["unknown-type", "unknown-risk"],
)
def test_create_invalid_enum_returns_server_error_current_behavior(
    knowledge_api_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
    invalid_fields: dict[str, str],
) -> None:
    """这是当前行为，疑似缺陷 C-VALID-01：非法枚举返回 500，待模块 C 改造时处置。"""
    _, session_factory = knowledge_api_env
    email = f"knowledge_enum_{uuid4().hex[:8]}@example.com"

    client = TestClient(app, raise_server_exceptions=False)
    try:
        token = _register_and_login(client, email=email)
        asyncio.run(
            _grant_role_permissions(
                session_factory,
                email=email,
                role_name=f"knowledge_enum_{uuid4().hex[:8]}",
                permission_keys=["agent:execute"],
            )
        )
        payload = {
            "title": "invalid enum",
            "content": "invalid enum",
            "type": "document",
            "risk_level": "R1",
            **invalid_fields,
        }

        response = client.post(
            "/api/v1/agent/knowledge",
            headers=_auth_headers(token),
            json=payload,
        )
    finally:
        client.close()

    assert response.status_code == 500


def test_cross_school_user_can_search_other_school_knowledge_current_behavior(
    knowledge_api_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    """这是当前行为，疑似缺陷 C-AUTH-01：跨校可读知识，待模块 C 改造时处置。"""
    client, session_factory = knowledge_api_env
    agent_endpoints.knowledge_governance._knowledge_store.clear()

    owner_email = f"knowledge_owner_{uuid4().hex[:8]}@example.com"
    owner_token = _register_and_login(client, email=owner_email)
    asyncio.run(
        _grant_role_permissions(
            session_factory,
            email=owner_email,
            role_name=f"knowledge_owner_{uuid4().hex[:8]}",
            permission_keys=["agent:execute"],
        )
    )
    unique_title = f"cross-school-{uuid4().hex}"
    create_response = client.post(
        "/api/v1/agent/knowledge",
        headers=_auth_headers(owner_token),
        json={"title": unique_title, "content": unique_title, "type": "document"},
    )
    assert create_response.status_code == 200
    entry_id = create_response.json()["id"]
    assert client.post(
        f"/api/v1/agent/knowledge/{entry_id}/submit",
        headers=_auth_headers(owner_token),
    ).status_code == 200
    assert client.post(
        f"/api/v1/agent/knowledge/{entry_id}/approve",
        headers=_auth_headers(owner_token),
        json={"decision": "approve"},
    ).status_code == 200

    reader_email = f"knowledge_reader_{uuid4().hex[:8]}@example.com"
    reader_token = _register_and_login(
        client,
        email=reader_email,
        school_name=OTHER_TEST_SCHOOL_NAME,
    )
    asyncio.run(
        _grant_role_permissions(
            session_factory,
            email=reader_email,
            role_name=f"knowledge_reader_{uuid4().hex[:8]}",
            permission_keys=["agent:read"],
        )
    )

    search_response = client.post(
        "/api/v1/agent/knowledge/search",
        headers=_auth_headers(reader_token),
        json={"query": unique_title, "status": "APPROVED"},
    )

    assert search_response.status_code == 200
    assert entry_id in {item["id"] for item in search_response.json()["results"]}


def test_knowledge_approval_does_not_create_retrieval_records_current_behavior(
    knowledge_api_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    """这是当前行为，疑似缺陷 C-DATA-01（M-23），待模块 C 改造时处置。"""
    client, session_factory = knowledge_api_env
    agent_endpoints.knowledge_governance._knowledge_store.clear()
    counts_before = asyncio.run(_retrieval_record_counts(session_factory))

    email = f"knowledge_m23_{uuid4().hex[:8]}@example.com"
    token = _register_and_login(client, email=email)
    asyncio.run(
        _grant_role_permissions(
            session_factory,
            email=email,
            role_name=f"knowledge_m23_{uuid4().hex[:8]}",
            permission_keys=["agent:execute"],
        )
    )
    create_response = client.post(
        "/api/v1/agent/knowledge",
        headers=_auth_headers(token),
        json={
            "title": "M-23 approved knowledge",
            "content": "must become retrieval material",
            "type": "document",
        },
    )
    assert create_response.status_code == 200
    entry_id = create_response.json()["id"]
    assert client.post(
        f"/api/v1/agent/knowledge/{entry_id}/submit",
        headers=_auth_headers(token),
    ).status_code == 200
    approve_response = client.post(
        f"/api/v1/agent/knowledge/{entry_id}/approve",
        headers=_auth_headers(token),
        json={"decision": "approve"},
    )

    assert approve_response.status_code == 200
    assert asyncio.run(_retrieval_record_counts(session_factory)) == counts_before


def test_other_school_user_can_submit_foreign_draft_current_behavior(
    knowledge_api_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    """这是当前行为，疑似缺陷 C-AUTH-04：跨校可提交他人草稿，待模块 C 改造时处置。"""
    client, session_factory = knowledge_api_env
    agent_endpoints.knowledge_governance._knowledge_store.clear()

    owner_email = f"draft_owner_{uuid4().hex[:8]}@example.com"
    owner_token = _register_and_login(client, email=owner_email)
    asyncio.run(
        _grant_role_permissions(
            session_factory,
            email=owner_email,
            role_name=f"draft_owner_{uuid4().hex[:8]}",
            permission_keys=["agent:execute"],
        )
    )
    create_response = client.post(
        "/api/v1/agent/knowledge",
        headers=_auth_headers(owner_token),
        json={"title": "foreign draft", "content": "private", "type": "document"},
    )
    assert create_response.status_code == 200
    entry_id = create_response.json()["id"]

    foreign_email = f"draft_foreign_{uuid4().hex[:8]}@example.com"
    foreign_token = _register_and_login(
        client,
        email=foreign_email,
        school_name=OTHER_TEST_SCHOOL_NAME,
    )
    asyncio.run(
        _grant_role_permissions(
            session_factory,
            email=foreign_email,
            role_name=f"draft_foreign_{uuid4().hex[:8]}",
            permission_keys=["agent:execute"],
        )
    )

    submit_response = client.post(
        f"/api/v1/agent/knowledge/{entry_id}/submit",
        headers=_auth_headers(foreign_token),
    )

    assert submit_response.status_code == 200
    assert submit_response.json() == {"status": "submitted"}


def test_approve_accepts_unknown_decision_as_rejection_current_behavior(
    knowledge_api_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    """这是当前行为，疑似缺陷 C-APPROVAL-01：非法决定被当作拒绝，待模块 C 改造时处置。"""
    client, session_factory = knowledge_api_env
    agent_endpoints.knowledge_governance._knowledge_store.clear()

    email = f"knowledge_decision_{uuid4().hex[:8]}@example.com"
    token = _register_and_login(client, email=email)
    asyncio.run(
        _grant_role_permissions(
            session_factory,
            email=email,
            role_name=f"knowledge_decision_{uuid4().hex[:8]}",
            permission_keys=["agent:execute"],
        )
    )
    create_response = client.post(
        "/api/v1/agent/knowledge",
        headers=_auth_headers(token),
        json={"title": "invalid decision", "content": "content", "type": "document"},
    )
    assert create_response.status_code == 200
    entry_id = create_response.json()["id"]
    assert client.post(
        f"/api/v1/agent/knowledge/{entry_id}/submit",
        headers=_auth_headers(token),
    ).status_code == 200

    approve_response = client.post(
        f"/api/v1/agent/knowledge/{entry_id}/approve",
        headers=_auth_headers(token),
        json={"decision": "publish"},
    )

    assert approve_response.status_code == 200
    assert approve_response.json() == {"status": "publish"}
    assert agent_endpoints.knowledge_governance._knowledge_store[entry_id].status.value == "REJECTED"


def test_upload_accepts_parent_path_and_unsupported_type_current_behavior(
    knowledge_api_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """这是当前行为，疑似缺陷 C-UPLOAD-01：路径与类型未拦截，待模块 C 改造时处置。"""
    client, session_factory = knowledge_api_env
    storage_root = tmp_path / "projects"
    monkeypatch.setattr(knowledge_endpoints.project_ingest_service, "storage_root", storage_root)

    email = f"knowledge_path_{uuid4().hex[:8]}@example.com"
    token = _register_and_login(client, email=email)
    asyncio.run(
        _grant_role_permissions(
            session_factory,
            email=email,
            role_name=f"knowledge_path_{uuid4().hex[:8]}",
            permission_keys=["agent:execute"],
        )
    )

    response = client.post(
        "/api/v1/agent/knowledge/upload",
        headers=_auth_headers(token),
        files={"file": ("../../escaped.exe", b"MZ-current-behavior", "application/x-msdownload")},
    )

    assert response.status_code == 200
    project_id = response.json()["project_id"]
    project_file, chunks = asyncio.run(
        _project_file_and_chunks(session_factory, project_id=project_id)
    )
    assert project_file.relative_path == "../../escaped.exe"
    assert Path(project_file.storage_path).resolve() == (tmp_path / "escaped.exe").resolve()
    assert Path(project_file.storage_path).read_bytes() == b"MZ-current-behavior"
    assert chunks == []


def test_upload_accepts_multi_megabyte_file_without_limit_current_behavior(
    knowledge_api_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """这是当前行为，疑似缺陷 C-UPLOAD-02：上传未设大小上限，待模块 C 改造时处置。"""
    client, session_factory = knowledge_api_env
    monkeypatch.setattr(
        knowledge_endpoints.project_ingest_service,
        "storage_root",
        tmp_path / "projects",
    )

    email = f"knowledge_large_{uuid4().hex[:8]}@example.com"
    token = _register_and_login(client, email=email)
    asyncio.run(
        _grant_role_permissions(
            session_factory,
            email=email,
            role_name=f"knowledge_large_{uuid4().hex[:8]}",
            permission_keys=["agent:execute"],
        )
    )
    content = b"x" * (2 * 1024 * 1024)

    response = client.post(
        "/api/v1/agent/knowledge/upload",
        headers=_auth_headers(token),
        files={"file": ("large.txt", content, "text/plain")},
    )

    assert response.status_code == 200
    assert response.json()["size_bytes"] == len(content)


def test_other_school_can_read_uploaded_robot_project_current_behavior(
    knowledge_api_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """这是当前行为，疑似缺陷 C-AUTH-03：机器人项目跨校可读，待模块 C 改造时处置。"""
    client, session_factory = knowledge_api_env
    monkeypatch.setattr(
        knowledge_endpoints.project_ingest_service,
        "storage_root",
        tmp_path / "projects",
    )

    owner_email = f"project_owner_{uuid4().hex[:8]}@example.com"
    owner_token = _register_and_login(client, email=owner_email)
    asyncio.run(
        _grant_role_permissions(
            session_factory,
            email=owner_email,
            role_name=f"project_owner_{uuid4().hex[:8]}",
            permission_keys=["agent:execute"],
        )
    )
    content = b"cross-school robot project manual"
    upload_response = client.post(
        "/api/v1/agent/knowledge/upload",
        headers=_auth_headers(owner_token),
        files={"file": ("manual.txt", content, "text/plain")},
    )
    assert upload_response.status_code == 200
    project_id = upload_response.json()["project_id"]

    reader_email = f"project_reader_{uuid4().hex[:8]}@example.com"
    reader_token = _register_and_login(
        client,
        email=reader_email,
        school_name=OTHER_TEST_SCHOOL_NAME,
    )
    asyncio.run(
        _grant_role_permissions(
            session_factory,
            email=reader_email,
            role_name=f"project_reader_{uuid4().hex[:8]}",
            permission_keys=["agent:read"],
        )
    )
    headers = _auth_headers(reader_token)

    job_response = client.get(f"/api/v1/agent/knowledge/upload/{project_id}", headers=headers)
    projects_response = client.get("/api/v1/agent/knowledge/projects", headers=headers)
    manifest_response = client.get(
        f"/api/v1/agent/knowledge/projects/{project_id}/manifest",
        headers=headers,
    )
    asset_response = client.get(
        f"/api/v1/agent/knowledge/projects/{project_id}/assets/manual.txt",
        headers=headers,
    )
    _, chunks = asyncio.run(_project_file_and_chunks(session_factory, project_id=project_id))

    assert job_response.status_code == 200
    assert projects_response.status_code == 200
    assert project_id in {
        project["project_id"] for project in projects_response.json()["projects"]
    }
    assert manifest_response.status_code == 200
    assert manifest_response.json()["project_id"] == project_id
    assert asset_response.status_code == 200
    assert asset_response.content == content
    assert chunks
    assert all(chunk.owner_user_id is None for chunk in chunks)
