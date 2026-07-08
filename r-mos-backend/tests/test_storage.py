"""Tests for FileStorageService (local filesystem implementation)."""
import pytest
from app.services.storage.file_storage import FileStorageBase, LocalFileStorage


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


def test_get_full_path_removed_from_interface(storage):
    """P1-1 完成判据：本地路径不再从接口泄漏。"""
    assert not hasattr(FileStorageBase, "get_full_path")
    assert not hasattr(storage, "get_full_path")


# --- P1-1 新原语测试 ---

def test_exists_true_and_false(storage, tmp_path):
    (tmp_path / "42" / "models").mkdir(parents=True)
    (tmp_path / "42" / "models" / "a.glb").write_bytes(b"a")
    assert storage.exists(robot_model_id=42, rel_path="models/a.glb") is True
    assert storage.exists(robot_model_id=42, rel_path="models/missing.glb") is False


def test_open_stream_reads_content(storage, tmp_path):
    (tmp_path / "42" / "models").mkdir(parents=True)
    (tmp_path / "42" / "models" / "s.glb").write_bytes(b"stream-bytes")
    stream = storage.open_stream(robot_model_id=42, rel_path="models/s.glb")
    try:
        assert stream.read() == b"stream-bytes"
    finally:
        stream.close()


def test_open_stream_missing_raises(storage):
    with pytest.raises(FileNotFoundError):
        storage.open_stream(robot_model_id=42, rel_path="models/none.glb")


def test_get_public_url_is_none_for_local(storage):
    assert storage.get_public_url(robot_model_id=42, rel_path="models/a.glb") is None


def test_materialize_yields_readable_path(storage, tmp_path):
    (tmp_path / "42" / "docs").mkdir(parents=True)
    (tmp_path / "42" / "docs" / "m.pdf").write_bytes(b"pdf-bytes")
    with storage.materialize(robot_model_id=42, rel_path="docs/m.pdf") as p:
        assert p.read_bytes() == b"pdf-bytes"


def test_materialize_missing_raises(storage):
    with pytest.raises(FileNotFoundError):
        with storage.materialize(robot_model_id=42, rel_path="docs/none.pdf"):
            pass


def test_materialize_dir_yields_robot_dir(storage, tmp_path):
    (tmp_path / "42" / "uploads").mkdir(parents=True)
    (tmp_path / "42" / "uploads" / "r.urdf").write_bytes(b"<robot/>")
    with storage.materialize_dir(robot_model_id=42) as d:
        assert (d / "uploads" / "r.urdf").exists()


def test_materialize_dir_creates_when_missing(storage):
    with storage.materialize_dir(robot_model_id=77) as d:
        assert d.is_dir()


@pytest.mark.parametrize("method,args", [
    ("download", ("../evil",)),
    ("delete", ("../evil",)),
    ("exists", ("../evil",)),
    ("open_stream", ("../evil",)),
])
def test_path_traversal_blocked_everywhere(storage, method, args):
    with pytest.raises(ValueError):
        getattr(storage, method)(42, *args)


def test_materialize_traversal_blocked(storage):
    with pytest.raises(ValueError):
        with storage.materialize(42, "../evil"):
            pass


# --- 工厂测试 ---
from app.services.storage import get_storage


def test_get_storage_returns_singleton_local():
    get_storage.cache_clear()
    s1 = get_storage()
    s2 = get_storage()
    assert isinstance(s1, LocalFileStorage)
    assert s1 is s2
    get_storage.cache_clear()


def test_get_storage_unknown_backend_raises(monkeypatch):
    from app.core.config import settings
    get_storage.cache_clear()
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "gcs")
    with pytest.raises(ValueError, match="gcs"):
        get_storage()
    get_storage.cache_clear()


# --- P1-2 Task 1: upload 侧防护 ---

@pytest.mark.parametrize("bad_filename", ["../evil.glb", "a/b.glb", "..", "", "a\\b.glb"])
def test_upload_rejects_bad_filename(storage, bad_filename):
    with pytest.raises(ValueError):
        storage.upload(robot_model_id=42, filename=bad_filename, content=b"x", subdirectory="models")


@pytest.mark.parametrize("bad_subdir", ["../up", "a/../b", "/abs", "a\\b"])
def test_upload_rejects_bad_subdirectory(storage, bad_subdir):
    with pytest.raises(ValueError):
        storage.upload(robot_model_id=42, filename="ok.glb", content=b"x", subdirectory=bad_subdir)


def test_upload_still_accepts_normal_input(storage):
    rel = storage.upload(robot_model_id=42, filename="ok.glb", content=b"x", subdirectory="models")
    assert rel == "42/models/ok.glb"
