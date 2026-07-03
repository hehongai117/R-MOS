from functools import lru_cache

from app.core.config import settings

from .file_storage import FileStorageBase, LocalFileStorage


@lru_cache(maxsize=1)
def get_storage() -> FileStorageBase:
    """按配置返回存储实现（进程内单例）。全仓唯一的实例化入口。"""
    backend = settings.STORAGE_BACKEND
    if backend == "local":
        return LocalFileStorage(base_dir=settings.STORAGE_BASE_DIR)
    raise ValueError(f"未知存储后端: {backend}（可选: local）")


__all__ = ["FileStorageBase", "LocalFileStorage", "get_storage"]
