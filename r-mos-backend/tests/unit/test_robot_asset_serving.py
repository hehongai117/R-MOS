"""P1-1 Task 3：资产下发端点不再依赖本地路径语义。"""
import json

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.models.robot_model import RobotModel, RobotStatus, RobotVisibility
from app.services.authz_guard import ActorContext
from app.services.storage.file_storage import LocalFileStorage


@pytest.fixture
def local_storage(tmp_path):
    return LocalFileStorage(base_dir=str(tmp_path))


@pytest.fixture
def owner_actor() -> ActorContext:
    """AUTH-103 之后资产端点要求认证 + 可见性校验。

    这些用例直接调用端点函数（不走 HTTP），因此必须显式传入身份。
    用 `_make_robot` 里的 `owner_teacher_id=1` 作为归属方——本文件验证的是
    存储层语义，不是访问控制，归属校验本身由
    `tests/unit/test_robot_asset_boundary.py` 覆盖。
    """
    return ActorContext(
        user_id=1,
        email="asset-owner@example.com",
        roles=set(),
        permissions=set(),
        account_role="teacher",
        school_name=None,
    )


@pytest.fixture
def http_request(owner_actor: ActorContext) -> Request:
    """直接调用端点时补齐真实 HTTP 会提供的请求上下文。"""
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
    request.state.actor = owner_actor
    return request


async def _make_robot(test_db) -> RobotModel:
    robot = RobotModel(
        brand="T", model_name="ServeBot", owner_teacher_id=1,
        visibility=RobotVisibility.PRIVATE, status=RobotStatus.DRAFT,
    )
    test_db.add(robot)
    await test_db.commit()
    await test_db.refresh(robot)
    return robot


@pytest.mark.asyncio
async def test_asset_served_as_streaming_response(
    test_db, local_storage, monkeypatch, owner_actor, http_request
):
    from app.api.v1.endpoints import robots as robots_ep
    from starlette.responses import StreamingResponse

    monkeypatch.setattr(robots_ep, "_storage", local_storage)
    robot = await _make_robot(test_db)
    local_storage.upload(robot.id, "part.glb", b"glb-binary", subdirectory="models")

    resp = await robots_ep.get_robot_asset(
        robot.id, "models/part.glb", http_request, db=test_db, actor=owner_actor
    )
    assert isinstance(resp, StreamingResponse)
    assert resp.media_type == "model/gltf-binary"


@pytest.mark.asyncio
async def test_asset_missing_returns_404(
    test_db, local_storage, monkeypatch, owner_actor, http_request
):
    from app.api.v1.endpoints import robots as robots_ep

    monkeypatch.setattr(robots_ep, "_storage", local_storage)
    robot = await _make_robot(test_db)
    with pytest.raises(HTTPException) as exc:
        await robots_ep.get_robot_asset(
            robot.id, "models/none.glb", http_request, db=test_db, actor=owner_actor
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_asset_traversal_returns_400(
    test_db, local_storage, monkeypatch, owner_actor, http_request
):
    from app.api.v1.endpoints import robots as robots_ep

    monkeypatch.setattr(robots_ep, "_storage", local_storage)
    robot = await _make_robot(test_db)
    with pytest.raises(HTTPException) as exc:
        await robots_ep.get_robot_asset(
            robot.id, "../../etc/passwd", http_request, db=test_db, actor=owner_actor
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_asset_redirects_when_public_url_available(
    test_db, local_storage, monkeypatch, owner_actor, http_request
):
    from app.api.v1.endpoints import robots as robots_ep
    from starlette.responses import RedirectResponse

    monkeypatch.setattr(robots_ep, "_storage", local_storage)
    monkeypatch.setattr(
        local_storage, "get_public_url", lambda robot_model_id, rel_path: "https://cdn.example/x.glb"
    )
    robot = await _make_robot(test_db)
    local_storage.upload(robot.id, "x.glb", b"glb", subdirectory="models")

    resp = await robots_ep.get_robot_asset(
        robot.id, "models/x.glb", http_request, db=test_db, actor=owner_actor
    )
    assert isinstance(resp, RedirectResponse)
    assert resp.status_code == 307
    assert resp.headers["location"] == "https://cdn.example/x.glb"


@pytest.mark.asyncio
async def test_asset_streaming_closes_handle_via_background(
    test_db, local_storage, monkeypatch, owner_actor, http_request
):
    from app.api.v1.endpoints import robots as robots_ep

    monkeypatch.setattr(robots_ep, "_storage", local_storage)
    robot = await _make_robot(test_db)
    local_storage.upload(robot.id, "part.glb", b"glb-binary", subdirectory="models")

    resp = await robots_ep.get_robot_asset(
        robot.id, "models/part.glb", http_request, db=test_db, actor=owner_actor
    )
    assert resp.background is not None  # BackgroundTask(stream.close)


@pytest.mark.asyncio
async def test_robot_tools_read_via_storage(
    test_db, local_storage, monkeypatch, owner_actor, http_request
):
    from app.api.v1.endpoints import robots as robots_ep

    monkeypatch.setattr(robots_ep, "_storage", local_storage)
    robot = await _make_robot(test_db)
    manifest = {"tools": [{"id": "screwdriver_m3"}]}
    local_storage.upload(
        robot.id, "assembly_manifest.json",
        json.dumps(manifest).encode("utf-8"), subdirectory="manifests",
    )

    result = await robots_ep.get_robot_tools(
        robot.id, http_request, db=test_db, actor=owner_actor
    )
    assert result["tools"] == [{"id": "screwdriver_m3"}]


@pytest.mark.asyncio
async def test_robot_tools_empty_when_no_manifest(
    test_db, local_storage, monkeypatch, owner_actor, http_request
):
    from app.api.v1.endpoints import robots as robots_ep

    monkeypatch.setattr(robots_ep, "_storage", local_storage)
    robot = await _make_robot(test_db)
    result = await robots_ep.get_robot_tools(
        robot.id, http_request, db=test_db, actor=owner_actor
    )
    assert result == {"robot_id": robot.id, "tools": []}
