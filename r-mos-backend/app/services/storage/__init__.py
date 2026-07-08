from functools import lru_cache

from app.core.config import settings

from .file_storage import FileStorageBase, LocalFileStorage


@lru_cache(maxsize=1)
def get_storage() -> FileStorageBase:
    """按配置返回存储实现（进程内单例）。全仓唯一的实例化入口。"""
    backend = settings.STORAGE_BACKEND
    if backend == "local":
        return LocalFileStorage(base_dir=settings.STORAGE_BASE_DIR)
    if backend == "s3":
        from .s3_storage import S3FileStorage

        return S3FileStorage(
            bucket=settings.S3_BUCKET,
            endpoint_url=settings.S3_ENDPOINT_URL,
            public_endpoint_url=settings.S3_PUBLIC_ENDPOINT_URL,
            access_key=settings.S3_ACCESS_KEY_ID,
            secret_key=settings.S3_SECRET_ACCESS_KEY,
            region=settings.S3_REGION,
            presign_expire=settings.S3_PRESIGN_EXPIRE_SECONDS,
        )
    raise ValueError(f"未知存储后端: {backend}（可选: local / s3）")


__all__ = ["FileStorageBase", "LocalFileStorage", "get_storage"]
