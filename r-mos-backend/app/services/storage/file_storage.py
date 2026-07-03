"""File storage abstraction for robot assets.

LocalFileStorage stores files on local disk.
接口以"S3/OSS 可等价实现"为设计边界：
- 不向调用方返回本地路径（materialize/materialize_dir 例外——它们是
  分析管线显式声明"需要真实本地文件"的受控出口，S3 实现将下载到临时目录）
- get_public_url 供实现决定是否走预签名 URL 直连（本地返回 None → 走流式）
- 接口保持同步（决策记录：避免 async 传染；S3 实现内部用 anyio.to_thread）
"""
from abc import ABC, abstractmethod
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
from typing import BinaryIO, Iterator, List, Optional


class FileStorageBase(ABC):
    """Abstract file storage interface."""

    @abstractmethod
    def upload(self, robot_model_id: int, filename: str, content: bytes, subdirectory: str = "") -> str:
        ...

    @abstractmethod
    def download(self, robot_model_id: int, rel_path: str) -> bytes:
        ...

    @abstractmethod
    def delete(self, robot_model_id: int, rel_path: str) -> None:
        ...

    @abstractmethod
    def list_files(self, robot_model_id: int, subdirectory: str = "") -> List[str]:
        ...

    @abstractmethod
    def exists(self, robot_model_id: int, rel_path: str) -> bool:
        ...

    @abstractmethod
    def open_stream(self, robot_model_id: int, rel_path: str) -> BinaryIO:
        """打开只读二进制流（HTTP 下发用）。不存在抛 FileNotFoundError。"""
        ...

    @abstractmethod
    def get_public_url(self, robot_model_id: int, rel_path: str) -> Optional[str]:
        """返回可直连的公开 URL（如 S3 预签名）；返回 None 表示走 open_stream。"""
        ...

    @abstractmethod
    def materialize(self, robot_model_id: int, rel_path: str) -> AbstractContextManager[Path]:
        """确保文件在本地可读并 yield 其 Path（分析管线用）。不存在抛 FileNotFoundError。"""
        ...

    @abstractmethod
    def materialize_dir(self, robot_model_id: int) -> AbstractContextManager[Path]:
        """确保机器人全部资产在本地目录可读并 yield 目录 Path（URDF 装配管线用）。"""
        ...


class LocalFileStorage(FileStorageBase):
    """Local filesystem storage implementation."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or "data/robot-assets")

    def _robot_dir(self, robot_model_id: int) -> Path:
        return self.base_dir / str(robot_model_id)

    def _resolve(self, robot_model_id: int, rel_path: str) -> Path:
        """robot 目录内解析相对路径，统一路径穿越防护。"""
        robot_dir = self._robot_dir(robot_model_id).resolve()
        full = (robot_dir / rel_path).resolve()
        if not full.is_relative_to(robot_dir):
            raise ValueError(f"Path traversal detected: {rel_path}")
        return full

    def upload(self, robot_model_id: int, filename: str, content: bytes, subdirectory: str = "") -> str:
        target_dir = self._robot_dir(robot_model_id)
        if subdirectory:
            target_dir = target_dir / subdirectory
        target_dir.mkdir(parents=True, exist_ok=True)

        target_file = target_dir / filename
        target_file.write_bytes(content)

        rel = str(robot_model_id)
        if subdirectory:
            rel = f"{rel}/{subdirectory}"
        return f"{rel}/{filename}"

    def download(self, robot_model_id: int, rel_path: str) -> bytes:
        full_path = self._resolve(robot_model_id, rel_path)
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {full_path}")
        return full_path.read_bytes()

    def delete(self, robot_model_id: int, rel_path: str) -> None:
        full_path = self._resolve(robot_model_id, rel_path)
        if full_path.exists():
            full_path.unlink()

    def list_files(self, robot_model_id: int, subdirectory: str = "") -> List[str]:
        target_dir = self._robot_dir(robot_model_id)
        if subdirectory:
            target_dir = target_dir / subdirectory

        if not target_dir.exists():
            return []

        results = []
        for f in target_dir.rglob("*"):
            if f.is_file():
                rel = str(f.relative_to(self._robot_dir(robot_model_id)))
                results.append(rel)
        return sorted(results)

    def exists(self, robot_model_id: int, rel_path: str) -> bool:
        return self._resolve(robot_model_id, rel_path).is_file()

    def open_stream(self, robot_model_id: int, rel_path: str) -> BinaryIO:
        full_path = self._resolve(robot_model_id, rel_path)
        if not full_path.is_file():
            raise FileNotFoundError(f"File not found: {full_path}")
        return full_path.open("rb")

    def get_public_url(self, robot_model_id: int, rel_path: str) -> Optional[str]:
        return None

    @contextmanager
    def _materialize_impl(self, robot_model_id: int, rel_path: str) -> Iterator[Path]:
        full_path = self._resolve(robot_model_id, rel_path)
        if not full_path.is_file():
            raise FileNotFoundError(f"File not found: {full_path}")
        yield full_path

    def materialize(self, robot_model_id: int, rel_path: str) -> AbstractContextManager[Path]:
        return self._materialize_impl(robot_model_id, rel_path)

    @contextmanager
    def _materialize_dir_impl(self, robot_model_id: int) -> Iterator[Path]:
        robot_dir = self._robot_dir(robot_model_id)
        robot_dir.mkdir(parents=True, exist_ok=True)
        yield robot_dir

    def materialize_dir(self, robot_model_id: int) -> AbstractContextManager[Path]:
        return self._materialize_dir_impl(robot_model_id)

    def get_full_path(self, robot_model_id: int, rel_path: str) -> str:
        """已弃用：仅在迁移期保留，Task 6 删除。"""
        return str(self._resolve(robot_model_id, rel_path))
