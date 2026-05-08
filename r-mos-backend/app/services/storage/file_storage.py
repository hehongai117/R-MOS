"""File storage abstraction for robot assets.

LocalFileStorage stores files on local disk.
Interface is designed to be swappable with OSS/S3 later.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional


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
    def get_full_path(self, robot_model_id: int, rel_path: str) -> str:
        ...


class LocalFileStorage(FileStorageBase):
    """Local filesystem storage implementation."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or "data/robot-assets")

    def _robot_dir(self, robot_model_id: int) -> Path:
        return self.base_dir / str(robot_model_id)

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
        full_path = self._robot_dir(robot_model_id) / rel_path
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {full_path}")
        return full_path.read_bytes()

    def delete(self, robot_model_id: int, rel_path: str) -> None:
        full_path = self._robot_dir(robot_model_id) / rel_path
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

    def get_full_path(self, robot_model_id: int, rel_path: str) -> str:
        robot_dir = self._robot_dir(robot_model_id).resolve()
        full = (robot_dir / rel_path).resolve()
        if not full.is_relative_to(robot_dir):
            raise ValueError(f"Path traversal detected: {rel_path}")
        return str(full)
