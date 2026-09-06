"""RMOS-S3-006 模块 B：机器人资产路由覆盖与当前行为安全网。

本文件通过真实 HTTP 请求、运行时路由枚举、AST 或 ORM 元数据固定模块 B 行为；
第二步已将确认的 G1-G3 缺陷断言反转为目标契约，B-FUNC-01 仍只登记不实施。
"""
from __future__ import annotations

import asyncio
import ast
import inspect
import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models as app_models  # noqa: F401  # ensure metadata is fully loaded
from app.api.v1.endpoints import robots as robot_endpoints
from app.core.database import get_db
from app.models.analysis_task import AnalysisTask
from app.models.audit_event import AuditEvent
from app.models.base import Base
from app.models.robot_asset import AssetType, RobotAsset
from app.models.robot_model import (
    RobotModel,
    RobotStatus,
    RobotVisibility,
    TeacherRobotBinding,
)
from app.models.robot_part_manifest import RobotPartManifest
from app.models.robot_project import RobotProject
from app.models.robot_project_file import RobotProjectFile
from app.models.school import School
from app.services.storage.file_storage import LocalFileStorage
from main import app


pytestmark = [pytest.mark.e2e, pytest.mark.characterization]

TEST_SCHOOL_NAME = "测试学校"
OTHER_SCHOOL_NAME = "模块B外校"

MODULE_B_AGENT_ENDPOINTS = {
    "upload_knowledge_file",
    "get_knowledge_upload_job",
    "list_robot_projects",
    "get_robot_project_manifest",
    "get_robot_project_asset",
}

MODULE_B_ROUTES = {
    ("POST", "/api/v1/robots"),
    ("GET", "/api/v1/robots"),
    ("GET", "/api/v1/robots/shared"),
    ("GET", "/api/v1/robots/{robot_id}"),
    ("PUT", "/api/v1/robots/{robot_id}"),
    ("DELETE", "/api/v1/robots/{robot_id}"),
    ("POST", "/api/v1/robots/{robot_id}/upload"),
    ("POST", "/api/v1/robots/{robot_id}/analyze"),
    ("GET", "/api/v1/robots/{robot_id}/analysis-tasks"),
    ("PUT", "/api/v1/robots/{robot_id}/publish"),
    ("PUT", "/api/v1/robots/{robot_id}/visibility"),
    ("POST", "/api/v1/robots/{robot_id}/bind"),
    ("DELETE", "/api/v1/robots/{robot_id}/bind"),
    ("GET", "/api/v1/robots/{robot_id}/tools"),
    ("GET", "/api/v1/robots/{robot_id}/assets"),
    ("GET", "/api/v1/robots/{robot_id}/assets/{file_path:path}"),
    ("GET", "/api/v1/onboarding/robots"),
    ("POST", "/api/v1/onboarding/robots"),
    ("POST", "/api/v1/agent/knowledge/upload"),
    ("GET", "/api/v1/agent/knowledge/upload/{job_id}"),
    ("GET", "/api/v1/agent/knowledge/projects"),
    ("GET", "/api/v1/agent/knowledge/projects/{project_id}/manifest"),
    ("GET", "/api/v1/agent/knowledge/projects/{project_id}/assets/{asset_path:path}"),
}


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register_and_login(
    client: TestClient,
    *,
    email_prefix: str,
    school_name: str,
    role: str = "teacher",
    teacher_id: int | None = None,
) -> tuple[int, str]:
    email = f"{email_prefix}_{uuid4().hex[:8]}@example.com"
    payload: dict[str, object] = {
        "email": email,
        "password": "StrongPass123",
        "full_name": "Module B User",
        "role": role,
        "school_name": school_name,
    }
    if teacher_id is not None:
        payload["teacher_id"] = teacher_id

    register_response = client.post("/api/v1/auth/register", json=payload)
    assert register_response.status_code == 201, register_response.text
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert login_response.status_code == 200, login_response.text
    return int(register_response.json()["user_id"]), login_response.json()["access_token"]


@pytest.fixture(scope="module")
def module_b_env() -> dict:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async def _init_models() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
            await connection.execute(
                School.__table__.insert(),
                [{"name": TEST_SCHOOL_NAME}, {"name": OTHER_SCHOOL_NAME}],
            )

    asyncio.run(_init_models())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    app.state.test_sessionmaker = session_factory
    client = TestClient(app)

    owner_id, owner_token = _register_and_login(
        client, email_prefix="module_b_owner", school_name=TEST_SCHOOL_NAME
    )
    peer_id, peer_token = _register_and_login(
        client, email_prefix="module_b_peer", school_name=TEST_SCHOOL_NAME
    )
    foreign_id, foreign_token = _register_and_login(
        client, email_prefix="module_b_foreign", school_name=OTHER_SCHOOL_NAME
    )
    student_id, student_token = _register_and_login(
        client,
        email_prefix="module_b_student",
        school_name=TEST_SCHOOL_NAME,
        role="student",
        teacher_id=owner_id,
    )

    try:
        yield {
            "client": client,
            "session_factory": session_factory,
            "owner_id": owner_id,
            "owner_token": owner_token,
            "peer_id": peer_id,
            "peer_token": peer_token,
            "foreign_id": foreign_id,
            "foreign_token": foreign_token,
            "student_id": student_id,
            "student_token": student_token,
        }
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None
        asyncio.run(engine.dispose())


async def _seed_robot(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    owner_teacher_id: int | None,
    visibility: RobotVisibility = RobotVisibility.PRIVATE,
    status: RobotStatus = RobotStatus.DRAFT,
    with_owner_binding: bool = True,
) -> int:
    async with session_factory() as session:
        robot = RobotModel(
            brand=f"ModuleB-{uuid4().hex[:6]}",
            model_name=f"Robot-{uuid4().hex[:6]}",
            owner_teacher_id=owner_teacher_id,
            visibility=visibility,
            status=status,
        )
        session.add(robot)
        await session.flush()
        if with_owner_binding and owner_teacher_id is not None:
            session.add(
                TeacherRobotBinding(
                    teacher_id=owner_teacher_id,
                    robot_model_id=robot.id,
                    binding_type="owner",
                )
            )
        await session.commit()
        return robot.id


def _create_robot(client: TestClient, token: str, *, suffix: str) -> dict:
    response = client.post(
        "/api/v1/robots",
        headers=_auth_headers(token),
        json={
            "brand": f"ModuleB-{suffix}",
            "model_name": f"Robot-{uuid4().hex[:6]}",
            "version": "1.0",
            "description": f"{suffix} behavior fixture",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_module_b_route_census_uses_runtime_app() -> None:
    """从 main:app 的 APIRoute 枚举，锁定模块 B 当前真实注册的 23 条路由。"""
    actual: set[tuple[str, str]] = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        endpoint_module = route.endpoint.__module__
        if endpoint_module in {
            "app.api.v1.endpoints.robots",
            "app.api.v1.endpoints.onboarding",
        } or (
            endpoint_module == "app.api.v1.endpoints.agent_knowledge"
            and route.endpoint.__name__ in MODULE_B_AGENT_ENDPOINTS
        ):
            actual.update((method, route.path) for method in route.methods)

    assert actual == MODULE_B_ROUTES


def test_four_tables_without_owner_columns_derive_scope_from_owned_parents() -> None:
    """四张无直接归属字段的表都能沿强制外键回到带归属字段的父对象。"""
    cases = (
        (RobotAsset, "robot_model_id", "robot_models.id", RobotModel, {"owner_teacher_id"}),
        (AnalysisTask, "robot_model_id", "robot_models.id", RobotModel, {"owner_teacher_id"}),
        (
            RobotProjectFile,
            "project_id",
            "robot_projects.id",
            RobotProject,
            {"created_by_user_id", "school_name"},
        ),
        (
            RobotPartManifest,
            "project_id",
            "robot_projects.id",
            RobotProject,
            {"created_by_user_id", "school_name"},
        ),
    )
    for child, foreign_key_name, target, parent, owner_columns in cases:
        column = child.__table__.columns[foreign_key_name]
        assert column.nullable is False
        assert {key.target_fullname for key in column.foreign_keys} == {target}
        assert owner_columns <= set(parent.__table__.columns.keys())


def test_robot_crud_allows_owner_and_rejects_non_owner(module_b_env: dict) -> None:
    """创建、修改、删除均同时固定正常响应内容与越权拒绝。"""
    client = module_b_env["client"]
    student_denied = client.post(
        "/api/v1/robots",
        headers=_auth_headers(module_b_env["student_token"]),
        json={"brand": "Denied", "model_name": "StudentBot"},
    )
    assert student_denied.status_code == 403

    created = _create_robot(client, module_b_env["owner_token"], suffix="crud")
    robot_id = created["id"]
    assert created["owner_teacher_id"] == module_b_env["owner_id"]
    assert created["visibility"] == "private"
    assert created["status"] == "draft"

    peer_headers = _auth_headers(module_b_env["peer_token"])
    update_denied = client.put(
        f"/api/v1/robots/{robot_id}",
        headers=peer_headers,
        json={"description": "foreign update"},
    )
    assert update_denied.status_code == 403

    owner_headers = _auth_headers(module_b_env["owner_token"])
    updated = client.put(
        f"/api/v1/robots/{robot_id}",
        headers=owner_headers,
        json={"description": "owner update"},
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "owner update"

    delete_denied = client.delete(f"/api/v1/robots/{robot_id}", headers=peer_headers)
    assert delete_denied.status_code == 403
    deleted = client.delete(f"/api/v1/robots/{robot_id}", headers=owner_headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/robots/{robot_id}", headers=owner_headers).status_code == 404


def test_robot_lists_and_private_detail_use_read_denial_contract(module_b_env: dict) -> None:
    """B-AUTH-01：详情读取复用唯一可见性实现，越权不泄露存在性。"""
    client = module_b_env["client"]
    created = _create_robot(client, module_b_env["owner_token"], suffix="read")
    robot_id = created["id"]
    owner_headers = _auth_headers(module_b_env["owner_token"])

    listing = client.get("/api/v1/robots", headers=owner_headers)
    assert listing.status_code == 200
    listed = {item["id"]: item for item in listing.json()["items"]}
    assert listed[robot_id]["binding_type"] == "owner"

    detail = client.get(f"/api/v1/robots/{robot_id}", headers=owner_headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == robot_id

    denied = client.get(
        f"/api/v1/robots/{robot_id}",
        headers=_auth_headers(module_b_env["peer_token"]),
    )
    assert denied.status_code == 404


def test_all_robot_id_read_endpoints_use_single_visibility_guard() -> None:
    """B-AUTH-01：所有按机器人编号读取的 HTTP 端点都调用唯一可见性守卫。"""
    read_endpoints = (
        robot_endpoints.get_robot,
        robot_endpoints.list_analysis_tasks,
        robot_endpoints.get_robot_tools,
        robot_endpoints.list_robot_assets,
        robot_endpoints.get_robot_asset,
    )

    for endpoint in read_endpoints:
        tree = ast.parse(inspect.getsource(endpoint))
        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert "_get_audited_visible_robot_or_404" in calls, endpoint.__name__

    wrapper_tree = ast.parse(inspect.getsource(robot_endpoints._get_audited_visible_robot_or_404))
    wrapper_calls = {
        node.func.id
        for node in ast.walk(wrapper_tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "get_visible_robot_or_404" in wrapper_calls


def test_upload_and_analysis_allow_owner_reject_peer_and_return_content(
    module_b_env: dict,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """上传与分析入口具备正常、拒绝和响应内容证据。"""
    client = module_b_env["client"]
    created = _create_robot(client, module_b_env["owner_token"], suffix="analysis")
    robot_id = created["id"]
    owner_headers = _auth_headers(module_b_env["owner_token"])
    peer_headers = _auth_headers(module_b_env["peer_token"])
    local_storage = LocalFileStorage(base_dir=str(tmp_path / "robot-assets"))
    monkeypatch.setattr(robot_endpoints, "_storage", local_storage)

    async def _skip_knowledge_sync(*args, **kwargs) -> None:
        return None

    monkeypatch.setattr(
        robot_endpoints.project_ingest_service,
        "sync_project_for_robot_model",
        _skip_knowledge_sync,
    )
    files = {"files": ("manual.pdf", b"module-b-manual", "application/pdf")}

    upload_denied = client.post(
        f"/api/v1/robots/{robot_id}/upload", headers=peer_headers, files=files
    )
    assert upload_denied.status_code == 403
    uploaded = client.post(
        f"/api/v1/robots/{robot_id}/upload", headers=owner_headers, files=files
    )
    assert uploaded.status_code == 200, uploaded.text
    upload_body = uploaded.json()
    assert upload_body["failed"] == []
    assert len(upload_body["uploaded"]) == 1
    assert upload_body["uploaded"][0]["asset_type"] == "upload_original"

    analyze_denied = client.post(
        f"/api/v1/robots/{robot_id}/analyze", headers=peer_headers
    )
    assert analyze_denied.status_code == 403
    analyzed = client.post(f"/api/v1/robots/{robot_id}/analyze", headers=owner_headers)
    assert analyzed.status_code == 201, analyzed.text
    assert analyzed.json()["robot_model_id"] == robot_id
    assert analyzed.json()["status"] == "pending"
    assert analyzed.json()["input_document_ids"] == [upload_body["uploaded"][0]["id"]]


def test_uploaded_asset_response_path_can_be_downloaded(
    module_b_env: dict,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """B-STORAGE-01：上传响应给出的相对路径可直接用于资产下载。"""
    client = module_b_env["client"]
    created = _create_robot(client, module_b_env["owner_token"], suffix="path-contract")
    robot_id = created["id"]
    headers = _auth_headers(module_b_env["owner_token"])
    local_storage = LocalFileStorage(base_dir=str(tmp_path / "robot-assets"))
    monkeypatch.setattr(robot_endpoints, "_storage", local_storage)

    async def _skip_knowledge_sync(*args, **kwargs) -> None:
        return None

    monkeypatch.setattr(
        robot_endpoints.project_ingest_service,
        "sync_project_for_robot_model",
        _skip_knowledge_sync,
    )
    uploaded = client.post(
        f"/api/v1/robots/{robot_id}/upload",
        headers=headers,
        files={"files": ("manual.pdf", b"download-me", "application/pdf")},
    )
    assert uploaded.status_code == 200
    returned_path = uploaded.json()["uploaded"][0]["file_path"]
    assert returned_path == "uploads/manual.pdf"

    returned_path_response = client.get(
        f"/api/v1/robots/{robot_id}/assets/{returned_path}", headers=headers
    )
    assert returned_path_response.status_code == 200
    assert returned_path_response.content == b"download-me"


def test_publish_and_visibility_allow_owner_and_reject_peer(
    module_b_env: dict,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """发布与共享切换均固定正常状态变化和非所有者拒绝。"""
    client = module_b_env["client"]
    created = _create_robot(client, module_b_env["owner_token"], suffix="publish")
    robot_id = created["id"]
    owner_headers = _auth_headers(module_b_env["owner_token"])
    peer_headers = _auth_headers(module_b_env["peer_token"])
    local_storage = LocalFileStorage(base_dir=str(tmp_path / "robot-assets"))
    local_storage.upload(
        robot_id,
        "assembly_manifest.json",
        json.dumps({"mesh_catalog": {}}).encode(),
        subdirectory="manifests",
    )
    monkeypatch.setattr(robot_endpoints, "_storage", local_storage)

    publish_denied = client.put(f"/api/v1/robots/{robot_id}/publish", headers=peer_headers)
    assert publish_denied.status_code == 403
    published = client.put(f"/api/v1/robots/{robot_id}/publish", headers=owner_headers)
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "ready"

    visibility_denied = client.put(
        f"/api/v1/robots/{robot_id}/visibility", headers=peer_headers
    )
    assert visibility_denied.status_code == 403
    shared = client.put(f"/api/v1/robots/{robot_id}/visibility", headers=owner_headers)
    assert shared.status_code == 200
    assert shared.json()["visibility"] == "shared"


def test_analysis_tasks_are_visible_only_through_parent_robot_owner(module_b_env: dict) -> None:
    """无归属字段的分析任务经机器人父对象拒绝他人读取，并放行所有者。"""
    client = module_b_env["client"]
    robot_id = asyncio.run(
        _seed_robot(
            module_b_env["session_factory"], owner_teacher_id=module_b_env["owner_id"]
        )
    )

    async def _seed_task() -> int:
        async with module_b_env["session_factory"]() as session:
            task = AnalysisTask(robot_model_id=robot_id, task_type="full", status="completed")
            session.add(task)
            await session.commit()
            await session.refresh(task)
            return task.id

    task_id = asyncio.run(_seed_task())
    denied = client.get(
        f"/api/v1/robots/{robot_id}/analysis-tasks",
        headers=_auth_headers(module_b_env["peer_token"]),
    )
    assert denied.status_code == 404

    allowed = client.get(
        f"/api/v1/robots/{robot_id}/analysis-tasks",
        headers=_auth_headers(module_b_env["owner_token"]),
    )
    assert allowed.status_code == 200
    assert allowed.json()["total"] == 1
    assert allowed.json()["items"][0]["id"] == task_id


def test_bind_and_unbind_allow_teacher_reject_student_or_missing_binding(
    module_b_env: dict,
) -> None:
    """引用和取消引用同时具备放行、角色拒绝及不存在关系边界。"""
    client = module_b_env["client"]
    robot_id = asyncio.run(
        _seed_robot(
            module_b_env["session_factory"],
            owner_teacher_id=module_b_env["owner_id"],
            visibility=RobotVisibility.SHARED,
            status=RobotStatus.READY,
        )
    )
    student_headers = _auth_headers(module_b_env["student_token"])
    assert client.post(f"/api/v1/robots/{robot_id}/bind", headers=student_headers).status_code == 403

    peer_headers = _auth_headers(module_b_env["peer_token"])
    bound = client.post(f"/api/v1/robots/{robot_id}/bind", headers=peer_headers)
    assert bound.status_code == 201
    assert bound.json()["detail"] == "引用成功"

    owner_headers = _auth_headers(module_b_env["owner_token"])
    assert client.delete(f"/api/v1/robots/{robot_id}/bind", headers=owner_headers).status_code == 404
    unbound = client.delete(f"/api/v1/robots/{robot_id}/bind", headers=peer_headers)
    assert unbound.status_code == 204


def test_shared_robot_stays_visible_in_school_and_is_hidden_across_schools(
    module_b_env: dict,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """B-AUTH-02：SHARED 只在校内共享；同校放行、跨校拒绝。"""
    client = module_b_env["client"]
    robot_id = asyncio.run(
        _seed_robot(
            module_b_env["session_factory"],
            owner_teacher_id=module_b_env["owner_id"],
            visibility=RobotVisibility.SHARED,
            status=RobotStatus.READY,
        )
    )
    local_storage = LocalFileStorage(base_dir=str(tmp_path / "robot-assets"))
    local_storage.upload(robot_id, "cross.glb", b"cross-school", subdirectory="models")
    monkeypatch.setattr(robot_endpoints, "_storage", local_storage)

    async def _seed_asset() -> None:
        async with module_b_env["session_factory"]() as session:
            session.add(
                RobotAsset(
                    robot_model_id=robot_id,
                    asset_type=AssetType.MODEL_GLB,
                    file_path=f"{robot_id}/models/cross.glb",
                    file_size=12,
                )
            )
            await session.commit()

    asyncio.run(_seed_asset())
    peer_headers = _auth_headers(module_b_env["peer_token"])
    same_school_detail = client.get(f"/api/v1/robots/{robot_id}", headers=peer_headers)
    assert same_school_detail.status_code == 200
    same_school_shared = client.get("/api/v1/robots/shared", headers=peer_headers)
    assert robot_id in {item["id"] for item in same_school_shared.json()["items"]}
    same_school_assets = client.get(f"/api/v1/robots/{robot_id}/assets", headers=peer_headers)
    assert same_school_assets.status_code == 200

    headers = _auth_headers(module_b_env["foreign_token"])

    detail = client.get(f"/api/v1/robots/{robot_id}", headers=headers)
    assert detail.status_code == 404
    shared = client.get("/api/v1/robots/shared", headers=headers)
    assert shared.status_code == 200
    assert robot_id not in {item["id"] for item in shared.json()["items"]}
    assets = client.get(f"/api/v1/robots/{robot_id}/assets", headers=headers)
    assert assets.status_code == 404
    downloaded = client.get(
        f"/api/v1/robots/{robot_id}/assets/models/cross.glb", headers=headers
    )
    assert downloaded.status_code == 404

    bound = client.post(f"/api/v1/robots/{robot_id}/bind", headers=headers)
    assert bound.status_code == 404

    async def _seed_legacy_cross_school_binding() -> None:
        async with module_b_env["session_factory"]() as session:
            session.add(
                TeacherRobotBinding(
                    teacher_id=module_b_env["foreign_id"],
                    robot_model_id=robot_id,
                    binding_type="shared_ref",
                )
            )
            await session.commit()

    asyncio.run(_seed_legacy_cross_school_binding())
    own_listing = client.get("/api/v1/robots", headers=headers)
    assert own_listing.status_code == 200
    assert robot_id not in {item["id"] for item in own_listing.json()["items"]}


def test_onboarding_uses_visibility_and_school_boundary(
    module_b_env: dict,
) -> None:
    """B-AUTH-03：首次选择只列出并绑定对当前教师可见的机器人。"""
    client = module_b_env["client"]
    robot_id = asyncio.run(
        _seed_robot(
            module_b_env["session_factory"],
            owner_teacher_id=module_b_env["owner_id"],
            visibility=RobotVisibility.PRIVATE,
            status=RobotStatus.READY,
        )
    )
    foreign_headers = _auth_headers(module_b_env["foreign_token"])
    listed = client.get("/api/v1/onboarding/robots", headers=foreign_headers)
    assert listed.status_code == 200
    assert robot_id not in {item["id"] for item in listed.json()["items"]}

    selected = client.post(
        "/api/v1/onboarding/robots",
        headers=foreign_headers,
        json={"robot_ids": [robot_id]},
    )
    assert selected.status_code == 404

    shared_robot_id = asyncio.run(
        _seed_robot(
            module_b_env["session_factory"],
            owner_teacher_id=module_b_env["owner_id"],
            visibility=RobotVisibility.SHARED,
            status=RobotStatus.READY,
        )
    )
    peer_headers = _auth_headers(module_b_env["peer_token"])
    peer_listing = client.get("/api/v1/onboarding/robots", headers=peer_headers)
    assert shared_robot_id in {item["id"] for item in peer_listing.json()["items"]}
    same_school_selected = client.post(
        "/api/v1/onboarding/robots",
        headers=peer_headers,
        json={"robot_ids": [shared_robot_id]},
    )
    assert same_school_selected.status_code == 200
    assert same_school_selected.json() == {"message": "机器人选择完成", "bound_count": 1}

    student_headers = _auth_headers(module_b_env["student_token"])
    assert client.get("/api/v1/onboarding/robots", headers=student_headers).status_code == 403
    assert client.post(
        "/api/v1/onboarding/robots",
        headers=student_headers,
        json={"robot_ids": [robot_id]},
    ).status_code == 403


def test_system_shared_robot_remains_available_without_a_school_owner(
    module_b_env: dict,
) -> None:
    """SHARED 语义：无 owner 的系统内置机器人不被错误归入任一学校。"""
    robot_id = asyncio.run(
        _seed_robot(
            module_b_env["session_factory"],
            owner_teacher_id=None,
            visibility=RobotVisibility.SHARED,
            status=RobotStatus.READY,
            with_owner_binding=False,
        )
    )

    response = module_b_env["client"].get(
        "/api/v1/onboarding/robots",
        headers=_auth_headers(module_b_env["foreign_token"]),
    )
    assert response.status_code == 200
    assert robot_id in {item["id"] for item in response.json()["items"]}


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    (
        ("post", "/api/v1/robots", {"json": {"brand": "missing-model"}}),
        ("put", "/api/v1/robots/not-an-integer", {"json": {}}),
        ("delete", "/api/v1/robots/not-an-integer", {}),
        (
            "post",
            "/api/v1/robots/not-an-integer/upload",
            {"files": {"files": ("manual.pdf", b"x", "application/pdf")}},
        ),
        ("post", "/api/v1/robots/not-an-integer/analyze", {}),
        ("put", "/api/v1/robots/not-an-integer/publish", {}),
        ("put", "/api/v1/robots/not-an-integer/visibility", {}),
        ("post", "/api/v1/robots/not-an-integer/bind", {}),
        ("delete", "/api/v1/robots/not-an-integer/bind", {}),
        ("post", "/api/v1/onboarding/robots", {"json": {"robot_ids": []}}),
    ),
)
def test_module_b_write_routes_reject_invalid_input_with_422(
    module_b_env: dict, method: str, path: str, kwargs: dict
) -> None:
    """补齐十条写路由的非法输入边界。"""
    response = getattr(module_b_env["client"], method)(
        path,
        headers=_auth_headers(module_b_env["owner_token"]),
        **kwargs,
    )
    assert response.status_code == 422, response.text


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    (
        ("get", "/api/v1/robots/99999999", {}),
        ("put", "/api/v1/robots/99999999", {"json": {"description": "missing"}}),
        ("delete", "/api/v1/robots/99999999", {}),
        (
            "post",
            "/api/v1/robots/99999999/upload",
            {"files": {"files": ("manual.pdf", b"x", "application/pdf")}},
        ),
        ("post", "/api/v1/robots/99999999/analyze", {}),
        ("get", "/api/v1/robots/99999999/analysis-tasks", {}),
        ("put", "/api/v1/robots/99999999/publish", {}),
        ("put", "/api/v1/robots/99999999/visibility", {}),
        ("post", "/api/v1/robots/99999999/bind", {}),
        ("delete", "/api/v1/robots/99999999/bind", {}),
    ),
)
def test_module_b_robot_id_routes_return_404_for_missing_id(
    module_b_env: dict, method: str, path: str, kwargs: dict
) -> None:
    """补齐所有尚未覆盖的机器人编号不存在边界。"""
    response = getattr(module_b_env["client"], method)(
        path,
        headers=_auth_headers(module_b_env["owner_token"]),
        **kwargs,
    )
    assert response.status_code == 404, response.text


def test_onboarding_missing_robot_returns_404(module_b_env: dict) -> None:
    """B-HTTP-01：首次选择不存在的机器人返回 404。"""
    response = module_b_env["client"].post(
        "/api/v1/onboarding/robots",
        headers=_auth_headers(module_b_env["owner_token"]),
        json={"robot_ids": [99999999]},
    )
    assert response.status_code == 404


def test_robot_asset_http_path_traversal_is_blocked(
    module_b_env: dict,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """真实 HTTP 入口不得用编码后的父目录片段读出机器人目录外文件。"""
    client = module_b_env["client"]
    created = _create_robot(client, module_b_env["owner_token"], suffix="traversal")
    robot_id = created["id"]
    storage_root = tmp_path / "robot-assets"
    local_storage = LocalFileStorage(base_dir=str(storage_root))
    (storage_root / str(robot_id)).mkdir(parents=True)
    secret = tmp_path / "secret.txt"
    secret.write_bytes(b"must-not-leak")
    monkeypatch.setattr(robot_endpoints, "_storage", local_storage)

    response = client.get(
        f"/api/v1/robots/{robot_id}/assets/%2E%2E%2F%2E%2E%2Fsecret.txt",
        headers=_auth_headers(module_b_env["owner_token"]),
    )
    assert response.status_code == 400
    assert b"must-not-leak" not in response.content


def test_analysis_tasks_have_no_cancel_route_current_behavior() -> None:
    """登记 B-FUNC-01：分析任务可创建和查看，但本批不新增取消入口。"""
    analysis_routes = {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute)
        and route.endpoint.__module__ == "app.api.v1.endpoints.robots"
        and ("analysis" in route.path or "analyze" in route.path)
        for method in route.methods
    }
    assert analysis_routes == {
        ("POST", "/api/v1/robots/{robot_id}/analyze"),
        ("GET", "/api/v1/robots/{robot_id}/analysis-tasks"),
    }


def test_robot_asset_denial_writes_audit_record(module_b_env: dict) -> None:
    """B-AUDIT-01：资产越权拒绝记录真实机器人编号与调用者。"""
    robot_id = asyncio.run(
        _seed_robot(
            module_b_env["session_factory"], owner_teacher_id=module_b_env["owner_id"]
        )
    )
    response = module_b_env["client"].get(
        f"/api/v1/robots/{robot_id}/assets",
        headers=_auth_headers(module_b_env["foreign_token"]),
    )
    assert response.status_code == 404

    async def _audit_rows() -> list[AuditEvent]:
        async with module_b_env["session_factory"]() as session:
            result = await session.execute(
                select(AuditEvent).where(AuditEvent.resource_id == str(robot_id))
            )
            return list(result.scalars().all())

    audit_rows = asyncio.run(_audit_rows())
    assert len(audit_rows) == 1
    assert audit_rows[0].decision == "deny"
    assert audit_rows[0].action == "list_robot_assets"
    assert audit_rows[0].resource_type == "robot_model"
    assert audit_rows[0].resource_id == str(robot_id)
    assert audit_rows[0].actor_user_id == str(module_b_env["foreign_id"])
