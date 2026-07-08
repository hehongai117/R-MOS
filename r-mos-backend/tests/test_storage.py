"""Storage 契约测试：同一套行为断言跑所有 FileStorageBase 实现。

Task 3 在 fixture params 中加入 "s3"（moto mock）后，契约组自动双跑。
Local 特有断言（磁盘布局）与工厂测试在文件末尾独立分组。
"""
import json

import pytest

from app.services.storage import get_storage
from app.services.storage.file_storage import FileStorageBase, LocalFileStorage


@pytest.fixture(params=["local", "s3"])
def storage(request, tmp_path):
    if request.param == "local":
        yield LocalFileStorage(base_dir=str(tmp_path))
    else:
        from moto import mock_aws
        from app.services.storage.s3_storage import S3FileStorage
        with mock_aws():
            yield S3FileStorage(bucket="test-bucket", region="us-east-1")


# ============ 契约组：全实现必须通过 ============

def test_upload_returns_contract_path(storage):
    rel = storage.upload(robot_model_id=42, filename="base_link.glb", content=b"glb", subdirectory="models")
    assert rel == "42/models/base_link.glb"


def test_upload_download_roundtrip(storage):
    storage.upload(robot_model_id=42, filename="t.glb", content=b"torso data", subdirectory="models")
    assert storage.download(robot_model_id=42, rel_path="models/t.glb") == b"torso data"


def test_download_nonexistent_raises(storage):
    with pytest.raises(FileNotFoundError):
        storage.download(robot_model_id=99, rel_path="no/such/file.glb")


def test_delete_removes_file(storage):
    storage.upload(robot_model_id=42, filename="old.glb", content=b"old", subdirectory="models")
    storage.delete(robot_model_id=42, rel_path="models/old.glb")
    assert storage.exists(robot_model_id=42, rel_path="models/old.glb") is False


def test_delete_missing_is_noop(storage):
    storage.delete(robot_model_id=42, rel_path="models/never.glb")  # 不抛异常


def test_list_files(storage):
    storage.upload(robot_model_id=42, filename="a.glb", content=b"a", subdirectory="models")
    storage.upload(robot_model_id=42, filename="b.glb", content=b"b", subdirectory="models")
    files = storage.list_files(robot_model_id=42, subdirectory="models")
    assert sorted(files) == ["models/a.glb", "models/b.glb"]


def test_list_files_empty_robot(storage):
    assert storage.list_files(robot_model_id=777) == []


def test_exists_true_and_false(storage):
    storage.upload(robot_model_id=42, filename="a.glb", content=b"a", subdirectory="models")
    assert storage.exists(robot_model_id=42, rel_path="models/a.glb") is True
    assert storage.exists(robot_model_id=42, rel_path="models/missing.glb") is False


def test_open_stream_reads_content(storage):
    storage.upload(robot_model_id=42, filename="s.glb", content=b"stream-bytes", subdirectory="models")
    stream = storage.open_stream(robot_model_id=42, rel_path="models/s.glb")
    try:
        assert stream.read() == b"stream-bytes"
    finally:
        stream.close()


def test_open_stream_missing_raises(storage):
    with pytest.raises(FileNotFoundError):
        storage.open_stream(robot_model_id=42, rel_path="models/none.glb")


def test_materialize_yields_readable_path(storage):
    storage.upload(robot_model_id=42, filename="m.pdf", content=b"pdf-bytes", subdirectory="docs")
    with storage.materialize(robot_model_id=42, rel_path="docs/m.pdf") as p:
        assert p.read_bytes() == b"pdf-bytes"


def test_materialize_missing_raises(storage):
    with pytest.raises(FileNotFoundError):
        with storage.materialize(robot_model_id=42, rel_path="docs/none.pdf"):
            pass


def test_materialize_dir_contains_all_assets(storage):
    storage.upload(robot_model_id=42, filename="r.urdf", content=b"<robot/>", subdirectory="uploads")
    storage.upload(robot_model_id=42, filename="m.glb", content=b"glb", subdirectory="models")
    with storage.materialize_dir(robot_model_id=42) as d:
        assert (d / "uploads" / "r.urdf").read_bytes() == b"<robot/>"
        assert (d / "models" / "m.glb").read_bytes() == b"glb"


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


@pytest.mark.parametrize("bad_filename", ["../evil.glb", "a/b.glb", "..", "", "a\\b.glb"])
def test_upload_rejects_bad_filename(storage, bad_filename):
    with pytest.raises(ValueError):
        storage.upload(robot_model_id=42, filename=bad_filename, content=b"x", subdirectory="models")


@pytest.mark.parametrize("bad_subdir", ["../up", "a/../b", "/abs", "a\\b"])
def test_upload_rejects_bad_subdirectory(storage, bad_subdir):
    with pytest.raises(ValueError):
        storage.upload(robot_model_id=42, filename="ok.glb", content=b"x", subdirectory=bad_subdir)


# ============ Local 特有 ============

@pytest.fixture
def local_storage(tmp_path):
    return LocalFileStorage(base_dir=str(tmp_path))


def test_local_upload_writes_expected_disk_layout(local_storage, tmp_path):
    local_storage.upload(robot_model_id=42, filename="base_link.glb", content=b"glb", subdirectory="models")
    assert (tmp_path / "42" / "models" / "base_link.glb").read_bytes() == b"glb"


def test_local_get_public_url_is_none(local_storage):
    assert local_storage.get_public_url(robot_model_id=42, rel_path="models/a.glb") is None


def test_get_full_path_removed_from_interface(local_storage):
    """P1-1 完成判据：本地路径不再从接口泄漏。"""
    assert not hasattr(FileStorageBase, "get_full_path")
    assert not hasattr(local_storage, "get_full_path")


# ============ 工厂 ============

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
