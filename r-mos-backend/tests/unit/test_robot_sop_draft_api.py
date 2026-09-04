from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models as app_models  # noqa: F401
from app.core.database import get_db
from app.api.v1.endpoints.maintenance import _approved_status_tokens
from app.models.base import Base
from app.models.robot_part_manifest import RobotPartManifest
from app.models.robot_project import RobotProject, RobotProjectStatus
from app.models.school import School
from main import app
from tests.e2e.helpers import E2E_SCHOOL_NAME, register_and_login, set_user_role  # 复用既有登录基建（该模块与 e2e 无耦合，只是造用户/拿令牌）


@pytest.fixture(scope="module")
def maintenance_api_env() -> tuple[TestClient, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async def init_models() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(School.__table__.insert().values(name=E2E_SCHOOL_NAME))

    asyncio.run(init_models())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        # AUTH-101 默认拒绝网关生效后，/api/v1 调用一律需要令牌；
        # 预置一位默认教师作为客户端默认身份。
        register_and_login(client, email_prefix="robot_sop_draft_actor")
        yield client, session_factory

    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


async def _seed_project(session_factory: async_sessionmaker[AsyncSession], project_id: str) -> None:
    async with session_factory() as session:
        session.add(
            RobotProject(
                id=project_id,
                robot_key=f"{project_id}-robot",
                brand="Fourier",
                model="N1",
                version="v1",
                status=RobotProjectStatus.READY,
                source_package_path="/tmp/fourier-n1.zip",
            )
        )
        session.add(
            RobotPartManifest(
                project_id=project_id,
                manifest_version="1.0",
                tree_json={"nodes": [{"id": "elbow"}]},
                mapping_json={"elbow": {"source_paths": ["viewer/elbow.glb"]}},
                viewer_manifest_json={
                    "robotId": f"{project_id}-robot",
                    "parts": ["viewer/elbow.glb"],
                    "needs_review_nodes": [],
                },
            )
        )
        await session.commit()


def _patch_generators(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_generate(self, *, db, project, maintenance_goal, focus_area=None):  # noqa: ANN001
        return {
            "draft": {
                "title": f"{project.brand} {maintenance_goal}",
                "maintenance_goal": maintenance_goal,
                "steps": [
                    {
                        "step_id": "step_001",
                        "title": "检查肘关节",
                        "description": "确认部件状态",
                        "required_tools": ["hex-key"],
                        "model_targets": ["elbow"],
                        "preconditions": ["robot_power_off"],
                    }
                ],
                "tools": ["hex-key"],
                "citations": [{"chunk_id": "chunk-1", "title": "doc", "score": 0.9, "source": "semantic"}],
                "model_targets": ["elbow"],
                "review_notes": [],
            },
            "citations": [{"chunk_id": "chunk-1", "title": "doc", "score": 0.9, "source": "semantic"}],
            "viewer_manifest": {"robotId": "fourier-n1", "parts": ["viewer/elbow.glb"], "needs_review_nodes": []},
            "manifest_tree": {"nodes": [{"id": "elbow"}]},
            "manifest_mapping": {"elbow": {"source_paths": ["viewer/elbow.glb"]}},
        }

    monkeypatch.setattr(
        "app.api.v1.endpoints.maintenance.SOPDraftGenerator.generate",
        fake_generate,
    )


def test_robot_sop_draft_api_lifecycle(
    maintenance_api_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = maintenance_api_env
    asyncio.run(_seed_project(session_factory, "project-lifecycle"))
    _patch_generators(monkeypatch)

    create_resp = client.post(
        "/api/v1/maintenance/drafts",
        json={"project_id": "project-lifecycle", "maintenance_goal": "执行器维护", "focus_area": "肘关节"},
    )
    assert create_resp.status_code == 200
    draft_id = create_resp.json()["draft_id"]
    assert create_resp.json()["review_status"] == "draft_pending_review"

    update_resp = client.patch(
        f"/api/v1/maintenance/drafts/{draft_id}",
        json={"title": "人工修订标题", "review_notes": ["补充校验说明"]},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["draft"]["title"] == "人工修订标题"

    submit_resp = client.post(f"/api/v1/maintenance/drafts/{draft_id}/submit-review")
    assert submit_resp.status_code == 200
    assert submit_resp.json()["review_status"] == "draft_pending_review"

    # 裁定 §9-2 后语义已变：教师**可以**审批，但**作者本人不得批准自己的草稿**
    # （M-13 职责分离，管理员亦不豁免）。此处这位教师正是草稿作者，故仍是 403——
    # 断言结果不变，理由已不同：由「角色不足」变为「不得自批」。
    author_denied = client.post(f"/api/v1/maintenance/drafts/{draft_id}/approve")
    assert author_denied.status_code == 403, "作者不应能批准自己的草稿"

    # 注册接口只接受 student/teacher（管理员不可自助注册），故注册后改 users.role
    admin_id, _, admin_login = register_and_login(client, email_prefix="robot_sop_draft_admin")
    asyncio.run(set_user_role(session_factory, user_id=admin_id, role="admin"))
    client.headers["Authorization"] = f"Bearer {admin_login['access_token']}"
    approve_resp = client.post(f"/api/v1/maintenance/drafts/{draft_id}/approve")
    assert approve_resp.status_code == 200
    assert approve_resp.json()["review_status"] == "approved"

    executable_resp = client.get("/api/v1/maintenance/projects/project-lifecycle/executable-draft")
    assert executable_resp.status_code == 200
    assert executable_resp.json()["draft_id"] == draft_id


def test_robot_sop_draft_api_rejects_non_executable_draft(
    maintenance_api_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = maintenance_api_env
    asyncio.run(_seed_project(session_factory, "project-rejected"))
    _patch_generators(monkeypatch)

    create_resp = client.post(
        "/api/v1/maintenance/drafts",
        json={"project_id": "project-rejected", "maintenance_goal": "腕关节复核"},
    )
    assert create_resp.status_code == 200
    draft_id = create_resp.json()["draft_id"]

    admin_id, _, admin_login = register_and_login(client, email_prefix="robot_sop_reject_admin")
    asyncio.run(set_user_role(session_factory, user_id=admin_id, role="admin"))
    client.headers["Authorization"] = f"Bearer {admin_login['access_token']}"
    reject_resp = client.post(
        f"/api/v1/maintenance/drafts/{draft_id}/reject",
        json={"reason": "模型映射不完整"},
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["review_status"] == "rejected"

    executable_resp = client.get("/api/v1/maintenance/projects/project-rejected/executable-draft")
    assert executable_resp.status_code == 404


def test_robot_sop_draft_api_accepts_uppercase_approved_status_from_pg(
    maintenance_api_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session_factory = maintenance_api_env
    asyncio.run(_seed_project(session_factory, "project-uppercase"))
    _patch_generators(monkeypatch)

    create_resp = client.post(
        "/api/v1/maintenance/drafts",
        json={"project_id": "project-uppercase", "maintenance_goal": "执行器维护"},
    )
    assert create_resp.status_code == 200
    draft_id = create_resp.json()["draft_id"]

    asyncio.run(_force_uppercase_status(session_factory, draft_id))

    executable_resp = client.get("/api/v1/maintenance/projects/project-uppercase/executable-draft")
    assert executable_resp.status_code == 200
    assert executable_resp.json()["draft_id"] == draft_id


async def _force_uppercase_status(
    session_factory: async_sessionmaker[AsyncSession],
    draft_id: str,
) -> None:
    async with session_factory() as session:
        await session.execute(
            text("UPDATE robot_sop_drafts SET review_status='APPROVED' WHERE id=:draft_id"),
            {"draft_id": draft_id},
        )
        await session.commit()


def test_approved_status_tokens_include_pg_uppercase_storage() -> None:
    assert _approved_status_tokens() == ("approved", "APPROVED")


# ---------------------------------------------------------------------------
# 职责分离（审计 M-13 / 董事会裁定 §9-2）
#
# 补齐 `created_by_user_id` 前，草稿审批被**收紧为仅管理员**——因为无作者字段
# 时无从判断「批准者是否即提交者」。字段补齐后按原注释所述放宽为：
# 教师与管理员均可审批，但作者本人一律不得批准自己的草稿（管理员不豁免）。
#
# 下面两条是新旧语义的分界：旧口径下「另一位教师可批准」必然 403。
# ---------------------------------------------------------------------------


def test_draft_approval_allows_non_author_teacher(
    maintenance_api_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """非作者的教师可以审批——证明放宽确实生效，而非仍是 admin-only。"""
    client, session_factory = maintenance_api_env
    asyncio.run(_seed_project(session_factory, "project-sod-teacher"))
    _patch_generators(monkeypatch)

    register_and_login(client, email_prefix="sod_draft_author")
    create_resp = client.post(
        "/api/v1/maintenance/drafts",
        json={"project_id": "project-sod-teacher", "maintenance_goal": "肩关节复核"},
    )
    assert create_resp.status_code == 200
    draft_id = create_resp.json()["draft_id"]

    # 换成另一位教师（非作者）
    register_and_login(client, email_prefix="sod_draft_reviewer")
    approve_resp = client.post(f"/api/v1/maintenance/drafts/{draft_id}/approve")
    assert approve_resp.status_code == 200, (
        f"非作者教师无法审批，放宽未生效: {approve_resp.status_code} {approve_resp.text}"
    )
    assert approve_resp.json()["review_status"] == "approved"


def test_draft_approval_denies_admin_author(
    maintenance_api_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """**管理员也不豁免**：自己提交的草稿自己不能批。

    若把职责分离写成「admin 一律放行」，这条会绿不了——而那正是最容易写出的版本。
    """
    client, session_factory = maintenance_api_env
    asyncio.run(_seed_project(session_factory, "project-sod-admin"))
    _patch_generators(monkeypatch)

    admin_id, _, admin_login = register_and_login(client, email_prefix="sod_admin_author")
    asyncio.run(set_user_role(session_factory, user_id=admin_id, role="admin"))
    client.headers["Authorization"] = f"Bearer {admin_login['access_token']}"

    create_resp = client.post(
        "/api/v1/maintenance/drafts",
        json={"project_id": "project-sod-admin", "maintenance_goal": "踝关节复核"},
    )
    assert create_resp.status_code == 200
    draft_id = create_resp.json()["draft_id"]

    approve_resp = client.post(f"/api/v1/maintenance/drafts/{draft_id}/approve")
    assert approve_resp.status_code == 403, (
        f"管理员批准了自己提交的草稿: {approve_resp.status_code} {approve_resp.text}"
    )
