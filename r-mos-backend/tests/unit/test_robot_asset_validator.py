"""资产完整性校验闸门（T1-4）单元测试。"""
import json

import pytest

from app.services.robot_asset_validator import (
    MANIFEST_REL_PATH,
    validate_robot_assets,
)
from app.services.storage.file_storage import LocalFileStorage


@pytest.fixture
def storage(tmp_path) -> LocalFileStorage:
    return LocalFileStorage(base_dir=str(tmp_path))


def _write_manifest(storage: LocalFileStorage, robot_id: int, mesh_catalog: dict) -> None:
    manifest = {"version": "1.0", "mesh_catalog": mesh_catalog, "nodes": []}
    storage.upload(
        robot_id,
        "assembly_manifest.json",
        json.dumps(manifest).encode("utf-8"),
        subdirectory="manifests",
    )


def test_missing_manifest_reported(storage):
    assert validate_robot_assets(99, storage) == [MANIFEST_REL_PATH]


def test_invalid_manifest_json_reported(storage):
    storage.upload(7, "assembly_manifest.json", b"not-json", subdirectory="manifests")
    missing = validate_robot_assets(7, storage)
    assert len(missing) == 1
    assert MANIFEST_REL_PATH in missing[0]


def test_missing_mesh_reported(storage):
    _write_manifest(storage, 7, {"m1": "models/a.glb", "m2": "models/b.glb"})
    storage.upload(7, "a.glb", b"glb-bytes", subdirectory="models")
    assert validate_robot_assets(7, storage) == ["models/b.glb"]


def test_complete_assets_pass(storage):
    _write_manifest(storage, 7, {"m1": "models/a.glb"})
    storage.upload(7, "a.glb", b"glb-bytes", subdirectory="models")
    assert validate_robot_assets(7, storage) == []


def test_empty_mesh_catalog_passes_with_manifest(storage):
    _write_manifest(storage, 7, {})
    assert validate_robot_assets(7, storage) == []


# --- 发布端点闸门测试 ---

from fastapi import HTTPException

from app.models.robot_model import RobotModel, RobotStatus, RobotVisibility
from app.services.authz_guard import ActorContext


@pytest.mark.asyncio
async def test_publish_blocked_when_assets_missing(test_db, tmp_path, monkeypatch):
    """资产不全的机器人发布应被 409 阻断，且报错指明缺失文件。"""
    from app.api.v1.endpoints import robots as robots_ep

    monkeypatch.setattr(robots_ep, "_storage", LocalFileStorage(base_dir=str(tmp_path)))

    robot = RobotModel(
        brand="Test", model_name="NoAssets", owner_teacher_id=1,
        visibility=RobotVisibility.PRIVATE, status=RobotStatus.DRAFT,
    )
    test_db.add(robot)
    await test_db.commit()
    await test_db.refresh(robot)

    actor = ActorContext(user_id=1, email="t@rmos.test", roles={"teacher"}, permissions=set())
    with pytest.raises(HTTPException) as exc:
        await robots_ep.publish_robot(robot.id, db=test_db, actor=actor)
    assert exc.value.status_code == 409
    assert MANIFEST_REL_PATH in exc.value.detail

    await test_db.refresh(robot)
    assert robot.status == RobotStatus.DRAFT


@pytest.mark.asyncio
async def test_publish_allowed_when_assets_complete(test_db, tmp_path, monkeypatch):
    from app.api.v1.endpoints import robots as robots_ep

    local = LocalFileStorage(base_dir=str(tmp_path))
    monkeypatch.setattr(robots_ep, "_storage", local)

    robot = RobotModel(
        brand="Test", model_name="FullAssets", owner_teacher_id=1,
        visibility=RobotVisibility.PRIVATE, status=RobotStatus.DRAFT,
    )
    test_db.add(robot)
    await test_db.commit()
    await test_db.refresh(robot)

    _write_manifest(local, robot.id, {"m1": "models/a.glb"})
    local.upload(robot.id, "a.glb", b"glb-bytes", subdirectory="models")

    actor = ActorContext(user_id=1, email="t@rmos.test", roles={"teacher"}, permissions=set())
    result = await robots_ep.publish_robot(robot.id, db=test_db, actor=actor)
    assert result.status == RobotStatus.READY
