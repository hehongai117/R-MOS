# app/services/storage/s3_storage.py
"""S3 兼容对象存储实现（AWS S3 / MinIO / 阿里云 OSS S3 协议）。

契约来源：docs/superpowers/plans/2026-07-08-p1-2-s3-handoff-notes.md
- key 布局与本地目录一致：{robot_model_id}/{subdirectory}/{filename}
- 同步接口（异步边界由调用方 anyio.to_thread 承担，见 ABC docstring）
- rel_path 含 ".." 一律 ValueError（与 Local 的 HTTP 层 400 契约对齐）
"""
import tempfile
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Iterator, List, Optional

from .file_storage import (
    FileStorageBase,
    _assert_safe_filename,
    _assert_safe_subdirectory,
)


def _assert_safe_rel_path(rel_path: str) -> None:
    if rel_path.startswith(("/", "\\")) or "\\" in rel_path:
        raise ValueError(f"Path traversal detected: {rel_path}")
    if ".." in PurePosixPath(rel_path).parts:
        raise ValueError(f"Path traversal detected: {rel_path}")


class S3FileStorage(FileStorageBase):
    """S3 协议存储。endpoint_url=None 时走 AWS；MinIO/OSS 传自定义 endpoint。"""

    def __init__(
        self,
        bucket: str,
        endpoint_url: Optional[str] = None,
        public_endpoint_url: Optional[str] = None,
        access_key: str = "",
        secret_key: str = "",
        region: str = "us-east-1",
        presign_expire: int = 900,
    ):
        import boto3

        self._bucket = bucket
        self._presign_expire = presign_expire
        cred = {}
        if access_key:
            cred = {"aws_access_key_id": access_key, "aws_secret_access_key": secret_key}
        self._client = boto3.client("s3", endpoint_url=endpoint_url, region_name=region, **cred)
        # 预签名 URL 的 host 参与签名——浏览器可达域名与内网域名不同时必须分开建 client
        if public_endpoint_url and public_endpoint_url != endpoint_url:
            self._presign_client = boto3.client(
                "s3", endpoint_url=public_endpoint_url, region_name=region, **cred
            )
        else:
            self._presign_client = self._client
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        from botocore.exceptions import ClientError

        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("NoSuchBucket", "404"):
                self._client.create_bucket(Bucket=self._bucket)
            else:
                raise

    def _key(self, robot_model_id: int, rel_path: str) -> str:
        _assert_safe_rel_path(rel_path)
        return f"{robot_model_id}/{rel_path}"

    # ---- 写 ----

    def upload(self, robot_model_id: int, filename: str, content: bytes, subdirectory: str = "") -> str:
        _assert_safe_filename(filename)
        if subdirectory:
            _assert_safe_subdirectory(subdirectory)
        rel = f"{subdirectory}/{filename}" if subdirectory else filename
        key = f"{robot_model_id}/{rel}"
        self._client.put_object(Bucket=self._bucket, Key=key, Body=content)
        return key

    def delete(self, robot_model_id: int, rel_path: str) -> None:
        key = self._key(robot_model_id, rel_path)
        self._client.delete_object(Bucket=self._bucket, Key=key)  # S3 删除天然幂等

    # ---- 读 ----

    def download(self, robot_model_id: int, rel_path: str) -> bytes:
        from botocore.exceptions import ClientError

        key = self._key(robot_model_id, rel_path)
        try:
            resp = self._client.get_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
                raise FileNotFoundError(f"File not found: {key}") from exc
            raise
        return resp["Body"].read()

    def list_files(self, robot_model_id: int, subdirectory: str = "") -> List[str]:
        if subdirectory:
            _assert_safe_subdirectory(subdirectory)
        prefix = f"{robot_model_id}/"
        if subdirectory:
            prefix = f"{prefix}{subdirectory}/"
        results: List[str] = []
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                results.append(obj["Key"].split("/", 1)[1])
        return sorted(results)

    def exists(self, robot_model_id: int, rel_path: str) -> bool:
        from botocore.exceptions import ClientError

        key = self._key(robot_model_id, rel_path)
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
                return False
            raise

    def open_stream(self, robot_model_id: int, rel_path: str) -> BinaryIO:
        from botocore.exceptions import ClientError

        key = self._key(robot_model_id, rel_path)
        try:
            resp = self._client.get_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
                raise FileNotFoundError(f"File not found: {key}") from exc
            raise
        return resp["Body"]  # botocore StreamingBody: read()/close() 兼容

    def get_public_url(self, robot_model_id: int, rel_path: str) -> Optional[str]:
        key = self._key(robot_model_id, rel_path)
        return self._presign_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=self._presign_expire,
        )

    # ---- 落地 ----

    @contextmanager
    def _materialize_impl(self, robot_model_id: int, rel_path: str) -> Iterator[Path]:
        content = self.download(robot_model_id, rel_path)  # 缺失在此抛 FileNotFoundError
        suffix = Path(rel_path).suffix
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        try:
            tmp.write(content)
            tmp.close()
            yield Path(tmp.name)
        finally:
            Path(tmp.name).unlink(missing_ok=True)

    def materialize(self, robot_model_id: int, rel_path: str) -> AbstractContextManager[Path]:
        return self._materialize_impl(robot_model_id, rel_path)

    @contextmanager
    def _materialize_dir_impl(self, robot_model_id: int) -> Iterator[Path]:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for rel in self.list_files(robot_model_id):
                target = root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(self.download(robot_model_id, rel))
            yield root

    def materialize_dir(self, robot_model_id: int) -> AbstractContextManager[Path]:
        return self._materialize_dir_impl(robot_model_id)
