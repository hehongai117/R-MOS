"""S3FileStorage 特有行为（契约行为在 test_storage.py 双跑覆盖）。"""
import urllib.parse

import pytest
from moto import mock_aws

from app.services.storage.s3_storage import S3FileStorage


@pytest.fixture
def s3_storage():
    with mock_aws():
        yield S3FileStorage(bucket="test-bucket", region="us-east-1")


def test_bucket_auto_created(s3_storage):
    """构造时 bucket 不存在则创建（幂等）。"""
    s3_storage.upload(robot_model_id=1, filename="a.glb", content=b"x", subdirectory="models")
    assert s3_storage.exists(1, "models/a.glb")


def test_get_public_url_returns_presigned(s3_storage):
    s3_storage.upload(robot_model_id=1, filename="a.glb", content=b"x", subdirectory="models")
    url = s3_storage.get_public_url(robot_model_id=1, rel_path="models/a.glb")
    assert url is not None
    parsed = urllib.parse.urlparse(url)
    assert "1/models/a.glb" in parsed.path
    assert "X-Amz-Signature" in url or "Signature" in url


def test_public_endpoint_used_for_presign():
    """浏览器可达域名与后端内网域名分离：presign 必须用 public endpoint。"""
    with mock_aws():
        s = S3FileStorage(
            bucket="test-bucket", region="us-east-1",
            endpoint_url=None,
            public_endpoint_url="http://public.example:9000",
        )
        s.upload(robot_model_id=1, filename="a.glb", content=b"x", subdirectory="models")
        url = s.get_public_url(robot_model_id=1, rel_path="models/a.glb")
        assert url.startswith("http://public.example:9000")


def test_open_stream_body_has_close(s3_storage):
    """open_stream 返回对象必须支持 read/close（端点 background close 依赖）。"""
    s3_storage.upload(robot_model_id=1, filename="a.glb", content=b"stream-me", subdirectory="models")
    body = s3_storage.open_stream(robot_model_id=1, rel_path="models/a.glb")
    assert body.read() == b"stream-me"
    body.close()  # 不抛即可


def test_materialize_cleans_up_tempfile(s3_storage):
    s3_storage.upload(robot_model_id=1, filename="m.pdf", content=b"pdf", subdirectory="docs")
    with s3_storage.materialize(robot_model_id=1, rel_path="docs/m.pdf") as p:
        temp_path = p
        assert p.read_bytes() == b"pdf"
    assert not temp_path.exists()


def test_materialize_dir_cleans_up(s3_storage):
    s3_storage.upload(robot_model_id=1, filename="a.glb", content=b"x", subdirectory="models")
    with s3_storage.materialize_dir(robot_model_id=1) as d:
        kept = d
        assert (d / "models" / "a.glb").exists()
    assert not kept.exists()


def test_factory_builds_s3_backend(monkeypatch):
    from app.core.config import settings
    from app.services.storage import get_storage

    get_storage.cache_clear()
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "s3")
    monkeypatch.setattr(settings, "S3_BUCKET", "factory-bucket")
    with mock_aws():
        s = get_storage()
        assert isinstance(s, S3FileStorage)
    get_storage.cache_clear()


def test_ensure_bucket_reraises_non_404():
    """权限类错误不得被吞成 create_bucket。"""
    from unittest.mock import MagicMock
    from botocore.exceptions import ClientError

    with mock_aws():
        s = S3FileStorage(bucket="test-bucket", region="us-east-1")
    err_403 = ClientError({"Error": {"Code": "403", "Message": "Forbidden"}}, "HeadBucket")
    s._client = MagicMock()
    s._client.head_bucket.side_effect = err_403
    with pytest.raises(ClientError):
        s._ensure_bucket()
    s._client.create_bucket.assert_not_called()
