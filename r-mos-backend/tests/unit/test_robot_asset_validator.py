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
