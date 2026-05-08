"""Tests for RobotService business logic."""
import pytest
import pytest_asyncio
import tempfile
from pathlib import Path
from app.services.robot_service import RobotService
from app.services.storage.file_storage import LocalFileStorage
from app.models.robot_model import RobotModel, RobotStatus, RobotVisibility
from app.models.robot_asset import RobotAsset, AssetType
from app.models.analysis_task import AnalysisTask, AnalysisTaskType, AnalysisTaskStatus


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".step", ".stp", ".stl", ".glb", ".gltf", ".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB


class TestFileValidation:
    """Test file upload validation logic (no DB needed)."""

    def test_allowed_extension_pdf(self):
        assert RobotService.validate_filename("manual.pdf") == "manual.pdf"

    def test_allowed_extension_glb(self):
        assert RobotService.validate_filename("model.glb") == "model.glb"

    def test_allowed_extension_step(self):
        assert RobotService.validate_filename("assembly.STEP") == "assembly.step"

    def test_rejected_extension(self):
        with pytest.raises(ValueError, match="不支持的文件类型"):
            RobotService.validate_filename("malware.exe")

    def test_empty_filename(self):
        with pytest.raises(ValueError, match="文件名不能为空"):
            RobotService.validate_filename("")

    def test_filename_sanitization(self):
        result = RobotService.validate_filename("my file (1).pdf")
        assert " " not in result
        assert "(" not in result

    def test_file_size_ok(self):
        RobotService.validate_file_size(100 * 1024 * 1024)  # 100MB, should not raise

    def test_file_size_too_large(self):
        with pytest.raises(ValueError, match="文件大小超过限制"):
            RobotService.validate_file_size(300 * 1024 * 1024)  # 300MB

    def test_detect_asset_type_pdf(self):
        assert RobotService.detect_asset_type("manual.pdf") == AssetType.UPLOAD_ORIGINAL

    def test_detect_asset_type_glb(self):
        assert RobotService.detect_asset_type("model.glb") == AssetType.MODEL_GLB

    def test_detect_asset_type_png(self):
        assert RobotService.detect_asset_type("thumb.png") == AssetType.THUMBNAIL


class TestPublishValidation:
    """Test publish state machine logic (no DB needed)."""

    def test_can_publish_from_draft(self):
        assert RobotService.can_publish(RobotStatus.DRAFT) is True

    def test_can_publish_from_ready(self):
        assert RobotService.can_publish(RobotStatus.READY) is True

    def test_cannot_publish_while_analyzing(self):
        assert RobotService.can_publish(RobotStatus.ANALYZING) is False
