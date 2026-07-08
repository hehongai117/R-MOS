"""P1-1 Task 3：资产下发端点不再依赖本地路径语义。"""
import json

import pytest
from fastapi import HTTPException

from app.models.robot_model import RobotModel, RobotStatus, RobotVisibility
from app.services.storage.file_storage import LocalFileStorage


@pytest.fixture
def local_storage(tmp_path):
    return LocalFileStorage(base_dir=str(tmp_path))


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
async def test_asset_served_as_streaming_response(test_db, local_storage, monkeypatch):
    from app.api.v1.endpoints import robots as robots_ep
    from starlette.responses import StreamingResponse

    monkeypatch.setattr(robots_ep, "_storage", local_storage)
    robot = await _make_robot(test_db)
    local_storage.upload(robot.id, "part.glb", b"glb-binary", subdirectory="models")

    resp = await robots_ep.get_robot_asset(robot.id, "models/part.glb", db=test_db)
    assert isinstance(resp, StreamingResponse)
    assert resp.media_type == "model/gltf-binary"


@pytest.mark.asyncio
async def test_asset_missing_returns_404(test_db, local_storage, monkeypatch):
    from app.api.v1.endpoints import robots as robots_ep

    monkeypatch.setattr(robots_ep, "_storage", local_storage)
    robot = await _make_robot(test_db)
    with pytest.raises(HTTPException) as exc:
        await robots_ep.get_robot_asset(robot.id, "models/none.glb", db=test_db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_asset_traversal_returns_400(test_db, local_storage, monkeypatch):
    from app.api.v1.endpoints import robots as robots_ep

    monkeypatch.setattr(robots_ep, "_storage", local_storage)
    robot = await _make_robot(test_db)
    with pytest.raises(HTTPException) as exc:
        await robots_ep.get_robot_asset(robot.id, "../../etc/passwd", db=test_db)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_asset_redirects_when_public_url_available(test_db, local_storage, monkeypatch):
    from app.api.v1.endpoints import robots as robots_ep
    from starlette.responses import RedirectResponse

    monkeypatch.setattr(robots_ep, "_storage", local_storage)
    monkeypatch.setattr(
        local_storage, "get_public_url", lambda robot_model_id, rel_path: "https://cdn.example/x.glb"
    )
    robot = await _make_robot(test_db)
    local_storage.upload(robot.id, "x.glb", b"glb", subdirectory="models")

    resp = await robots_ep.get_robot_asset(robot.id, "models/x.glb", db=test_db)
    assert isinstance(resp, RedirectResponse)
    assert resp.status_code == 307
    assert resp.headers["location"] == "https://cdn.example/x.glb"


@pytest.mark.asyncio
async def test_asset_streaming_closes_handle_via_background(test_db, local_storage, monkeypatch):
    from app.api.v1.endpoints import robots as robots_ep

    monkeypatch.setattr(robots_ep, "_storage", local_storage)
    robot = await _make_robot(test_db)
    local_storage.upload(robot.id, "part.glb", b"glb-binary", subdirectory="models")

    resp = await robots_ep.get_robot_asset(robot.id, "models/part.glb", db=test_db)
    assert resp.background is not None  # BackgroundTask(stream.close)


@pytest.mark.asyncio
async def test_robot_tools_read_via_storage(test_db, local_storage, monkeypatch):
    from app.api.v1.endpoints import robots as robots_ep

    monkeypatch.setattr(robots_ep, "_storage", local_storage)
    robot = await _make_robot(test_db)
    manifest = {"tools": [{"id": "screwdriver_m3"}]}
    local_storage.upload(
        robot.id, "assembly_manifest.json",
        json.dumps(manifest).encode("utf-8"), subdirectory="manifests",
    )

    result = await robots_ep.get_robot_tools(robot.id, db=test_db)
    assert result["tools"] == [{"id": "screwdriver_m3"}]


@pytest.mark.asyncio
async def test_robot_tools_empty_when_no_manifest(test_db, local_storage, monkeypatch):
    from app.api.v1.endpoints import robots as robots_ep

    monkeypatch.setattr(robots_ep, "_storage", local_storage)
    robot = await _make_robot(test_db)
    result = await robots_ep.get_robot_tools(robot.id, db=test_db)
    assert result == {"robot_id": robot.id, "tools": []}
