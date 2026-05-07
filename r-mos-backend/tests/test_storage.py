"""Tests for FileStorageService (local filesystem implementation)."""
import pytest
from app.services.storage.file_storage import LocalFileStorage


@pytest.fixture
def storage(tmp_path):
    return LocalFileStorage(base_dir=str(tmp_path))


def test_upload_file(storage, tmp_path):
    content = b"fake GLB binary content"
    rel_path = storage.upload(robot_model_id=42, filename="base_link.glb", content=content, subdirectory="models")
    assert rel_path == "42/models/base_link.glb"
    full_path = tmp_path / "42" / "models" / "base_link.glb"
    assert full_path.exists()
    assert full_path.read_bytes() == content


def test_download_file(storage, tmp_path):
    (tmp_path / "42" / "models").mkdir(parents=True)
    (tmp_path / "42" / "models" / "torso.glb").write_bytes(b"torso data")
    content = storage.download(robot_model_id=42, rel_path="models/torso.glb")
    assert content == b"torso data"


def test_download_nonexistent_raises(storage):
    with pytest.raises(FileNotFoundError):
        storage.download(robot_model_id=99, rel_path="no/such/file.glb")


def test_delete_file(storage, tmp_path):
    (tmp_path / "42" / "models").mkdir(parents=True)
    target = tmp_path / "42" / "models" / "old.glb"
    target.write_bytes(b"old data")
    storage.delete(robot_model_id=42, rel_path="models/old.glb")
    assert not target.exists()


def test_list_files(storage, tmp_path):
    base = tmp_path / "42" / "models"
    base.mkdir(parents=True)
    (base / "a.glb").write_bytes(b"a")
    (base / "b.glb").write_bytes(b"b")
    files = storage.list_files(robot_model_id=42, subdirectory="models")
    assert sorted(files) == ["models/a.glb", "models/b.glb"]


def test_get_full_path(storage, tmp_path):
    full = storage.get_full_path(robot_model_id=42, rel_path="models/base.glb")
    assert full == str(tmp_path / "42" / "models" / "base.glb")
