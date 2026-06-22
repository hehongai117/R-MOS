"""Robot business logic — file upload validation, publish state machine, asset type detection."""
import re
from pathlib import PurePosixPath

from app.models.robot_asset import AssetType
from app.models.robot_model import RobotStatus


ALLOWED_EXTENSIONS = {
    # 文档
    ".pdf", ".docx", ".doc", ".md", ".txt",
    # CAD / 3D 模型
    ".step", ".stp", ".stl", ".obj", ".dae",
    ".glb", ".gltf",
    # 机器人描述
    ".urdf", ".xacro", ".xml", ".json", ".yaml", ".yml",
    # 图片
    ".png", ".jpg", ".jpeg",
}

MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB

_CAD_EXTENSIONS = {".step", ".stp", ".stl", ".obj", ".dae"}
_MODEL_EXTENSIONS = {".glb", ".gltf"}
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


class RobotService:
    """Pure business logic — no DB dependency, easy to test."""

    @staticmethod
    def validate_filename(filename: str) -> str:
        """Validate and sanitize filename. Returns cleaned lowercase filename."""
        if not filename or not filename.strip():
            raise ValueError("文件名不能为空")
        name = filename.strip().lower()
        # sanitize: replace spaces and special chars with underscore
        name = re.sub(r"[^\w.\-]", "_", name)
        # collapse multiple underscores
        name = re.sub(r"_+", "_", name)
        ext = PurePosixPath(name).suffix
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"不支持的文件类型: {ext}，支持: {', '.join(sorted(ALLOWED_EXTENSIONS))}")
        return name

    @staticmethod
    def validate_file_size(size_bytes: int) -> None:
        """Raise ValueError if file exceeds 200MB limit."""
        if size_bytes > MAX_FILE_SIZE:
            raise ValueError(f"文件大小超过限制: {size_bytes} bytes > {MAX_FILE_SIZE} bytes (200MB)")

    @staticmethod
    def detect_asset_type(filename: str) -> AssetType:
        """Determine asset type from file extension."""
        ext = PurePosixPath(filename.lower()).suffix
        if ext in _MODEL_EXTENSIONS:
            return AssetType.MODEL_GLB
        if ext in _IMAGE_EXTENSIONS:
            return AssetType.THUMBNAIL
        return AssetType.UPLOAD_ORIGINAL

    @staticmethod
    def detect_subdirectory(asset_type: AssetType) -> str:
        """Return the storage subdirectory for an asset type."""
        mapping = {
            AssetType.MODEL_GLB: "models",
            AssetType.THUMBNAIL: "thumbnails",
            AssetType.UPLOAD_ORIGINAL: "uploads",
            AssetType.MANIFEST: "manifests",
        }
        return mapping.get(asset_type, "uploads")

    @staticmethod
    def can_publish(current_status: RobotStatus) -> bool:
        """Check if a robot can transition to published (ready) state."""
        return current_status != RobotStatus.ANALYZING
