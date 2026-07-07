"""P1-1 Task 4：workbench 草稿生成器的 manifest 读取走存储抽象。"""
import json

from app.services.storage.file_storage import LocalFileStorage
from app.services.training.workbench_draft_generator import TrainingWorkbenchDraftGenerator


def _manifest_bytes() -> bytes:
    return json.dumps({
        "nodes": [
            {"link_name": "torso_link", "mesh_id": "torso_mesh"},
            {"link_name": "no_mesh_link"},
        ],
        "display_names": {"torso_link": "躯干"},
    }).encode("utf-8")


def test_load_robot_manifest_via_storage(tmp_path, monkeypatch):
    import app.services.training.workbench_draft_generator as wdg

    local = LocalFileStorage(base_dir=str(tmp_path))
    local.upload(5, "assembly_manifest.json", _manifest_bytes(), subdirectory="manifests")
    monkeypatch.setattr(wdg, "get_storage", lambda: local)

    link_names, display_names = TrainingWorkbenchDraftGenerator._load_robot_manifest(5)
    assert link_names == ["torso_link"]
    assert display_names == {"torso_link": "躯干"}


def test_load_robot_manifest_missing_returns_empty(tmp_path, monkeypatch):
    import app.services.training.workbench_draft_generator as wdg

    local = LocalFileStorage(base_dir=str(tmp_path))
    monkeypatch.setattr(wdg, "get_storage", lambda: local)

    assert TrainingWorkbenchDraftGenerator._load_robot_manifest(999) == ([], {})


def test_load_robot_manifest_none_id_returns_empty():
    assert TrainingWorkbenchDraftGenerator._load_robot_manifest(None) == ([], {})
