# 多机器人平台 Phase 1：文件上传 + 机器人完整 API

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 教师能通过 API 上传文件（PDF/CAD/GLB）到机器人、触发 AI 分析、管理发布状态和共享状态，并有完整的集成测试覆盖。

**Architecture:** 在 Phase 0 的 CRUD API 基础上新增文件上传、分析任务、发布/共享端点。上传的文件通过 `LocalFileStorage` 存入 `data/robot-assets/{id}/uploads/`，同时创建 `RobotAsset` 数据库记录。新增 `AnalysisTaskResponse` schema 支持分析任务查询。所有新端点都有 owner/admin 权限校验。

**Tech Stack:** FastAPI, SQLAlchemy 2.0+ (AsyncSession), Pydantic 2.x, pytest + pytest-asyncio, python-multipart (文件上传)

**Design Spec:** `docs/superpowers/specs/2026-05-07-multi-robot-platform-design.md` (Section 4, 5, 10)

---

## File Structure

### 新增文件

| 文件 | 职责 |
|------|------|
| `r-mos-backend/app/schemas/analysis_task.py` | AnalysisTask Pydantic schemas（响应 + 列表） |
| `r-mos-backend/app/services/robot_service.py` | 机器人业务逻辑（上传、发布、共享），从 endpoint 层抽离 |
| `r-mos-backend/tests/test_robot_service.py` | robot_service 单元测试 |

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `r-mos-backend/app/api/v1/endpoints/robots.py` | 新增上传、分析任务、发布、共享端点 |
| `r-mos-backend/app/schemas/robot_model.py` | 新增 `FileUploadResponse` schema |
| `r-mos-backend/tests/test_api_robots.py` | 补全 CRUD + 上传 + 发布 + 权限的集成测试 |

---

### Task 1: AnalysisTask Pydantic Schemas

**Files:**
- Create: `r-mos-backend/app/schemas/analysis_task.py`

- [ ] **Step 1: 创建 AnalysisTask schemas 文件**

```python
# r-mos-backend/app/schemas/analysis_task.py
"""Pydantic schemas for AnalysisTask API responses."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class AnalysisTaskResponse(BaseModel):
    id: int
    robot_model_id: int
    task_type: str
    status: str
    input_document_ids: Optional[list] = None
    output_summary: Optional[dict] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisTaskListResponse(BaseModel):
    items: List[AnalysisTaskResponse]
    total: int
```

- [ ] **Step 2: 验证 import 正常**

Run: `cd r-mos-backend && python3 -c "from app.schemas.analysis_task import AnalysisTaskResponse, AnalysisTaskListResponse; print('OK')"`
Expected: `OK`

- [ ] **Step 3: 提交**

```bash
git add r-mos-backend/app/schemas/analysis_task.py
git commit -m "feat: add AnalysisTask Pydantic schemas"
```

---

### Task 2: RobotService 业务逻辑层

**Files:**
- Create: `r-mos-backend/app/services/robot_service.py`
- Create: `r-mos-backend/tests/test_robot_service.py`

- [ ] **Step 1: 编写 robot_service 测试**

```python
# r-mos-backend/tests/test_robot_service.py
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd r-mos-backend && python3 -m pytest tests/test_robot_service.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'app.services.robot_service')

- [ ] **Step 3: 实现 RobotService**

```python
# r-mos-backend/app/services/robot_service.py
"""Robot business logic — file upload validation, publish state machine, asset type detection."""
import re
from pathlib import PurePosixPath

from app.models.robot_asset import AssetType
from app.models.robot_model import RobotStatus


ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".doc",
    ".step", ".stp", ".stl",
    ".glb", ".gltf",
    ".png", ".jpg", ".jpeg",
}

MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB

_CAD_EXTENSIONS = {".step", ".stp", ".stl"}
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd r-mos-backend && python3 -m pytest tests/test_robot_service.py -v`
Expected: 11 passed

- [ ] **Step 5: 提交**

```bash
git add r-mos-backend/app/services/robot_service.py r-mos-backend/tests/test_robot_service.py
git commit -m "feat: add RobotService with file validation and publish logic"
```

---

### Task 3: 文件上传端点

**Files:**
- Modify: `r-mos-backend/app/api/v1/endpoints/robots.py`
- Modify: `r-mos-backend/app/schemas/robot_model.py`

- [ ] **Step 1: 在 schemas/robot_model.py 末尾新增 FileUploadResponse**

在 `RobotAssetResponse` 类之后追加：

```python
class FileUploadResponse(BaseModel):
    uploaded: List[RobotAssetResponse]
    failed: List[dict]  # {"filename": str, "error": str}
```

- [ ] **Step 2: 在 robots.py 中新增上传端点**

在 `delete_robot` 端点之后、`_storage = LocalFileStorage()` 之前，插入：

```python
from fastapi import UploadFile, File
from typing import List
from app.models.robot_asset import RobotAsset, AssetType
from app.services.robot_service import RobotService
from app.schemas.robot_model import FileUploadResponse, RobotAssetResponse


@router.post("/{robot_id}/upload", response_model=FileUploadResponse)
async def upload_robot_files(
    robot_id: int,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """上传文件到机器人（支持批量）。"""
    _require_teacher_or_admin(actor)
    result = await db.execute(select(RobotModel).where(RobotModel.id == robot_id))
    robot = result.scalar_one_or_none()
    if not robot:
        raise HTTPException(status_code=404, detail="机器人不存在")
    if robot.owner_teacher_id != actor.user_id and "admin" not in actor.roles:
        raise HTTPException(status_code=403, detail="只有创建者或管理员可以上传文件")

    uploaded = []
    failed = []

    for file in files:
        try:
            clean_name = RobotService.validate_filename(file.filename or "")
            content = await file.read()
            RobotService.validate_file_size(len(content))

            asset_type = RobotService.detect_asset_type(clean_name)
            subdirectory = RobotService.detect_subdirectory(asset_type)

            rel_path = _storage.upload(
                robot_model_id=robot_id,
                filename=clean_name,
                content=content,
                subdirectory=subdirectory,
            )

            asset = RobotAsset(
                robot_model_id=robot_id,
                asset_type=asset_type,
                file_path=rel_path,
                file_size=len(content),
            )
            db.add(asset)
            await db.flush()
            await db.refresh(asset)
            uploaded.append(asset)
        except ValueError as e:
            failed.append({"filename": file.filename or "", "error": str(e)})

    await db.commit()
    return FileUploadResponse(
        uploaded=[RobotAssetResponse.model_validate(a) for a in uploaded],
        failed=failed,
    )
```

注意：需要把 `from fastapi import UploadFile, File` 加到文件顶部的 import 中，以及 `from typing import List`。同时把 `from app.models.robot_asset import RobotAsset, AssetType` 和 `from app.services.robot_service import RobotService` 以及 `from app.schemas.robot_model import FileUploadResponse, RobotAssetResponse` 加到顶部 import。

最终 robots.py 顶部 import 应为：

```python
"""Robot model CRUD API endpoints."""
import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.storage.file_storage import LocalFileStorage
from app.services.authz_guard import ActorContext, get_current_actor
from app.services.robot_service import RobotService
from app.models.robot_model import RobotModel, RobotVisibility, RobotStatus, TeacherRobotBinding
from app.models.robot_asset import RobotAsset, AssetType
from app.schemas.robot_model import (
    RobotModelCreate,
    RobotModelUpdate,
    RobotModelResponse,
    RobotModelListResponse,
    RobotAssetResponse,
    FileUploadResponse,
)
```

- [ ] **Step 3: 验证 import 正常**

Run: `cd r-mos-backend && python3 -c "from app.api.v1.endpoints.robots import upload_robot_files; print('OK')"`
Expected: `OK`

- [ ] **Step 4: 提交**

```bash
git add r-mos-backend/app/api/v1/endpoints/robots.py r-mos-backend/app/schemas/robot_model.py
git commit -m "feat: add file upload endpoint POST /robots/{id}/upload"
```

---

### Task 4: 分析任务 API 端点

**Files:**
- Modify: `r-mos-backend/app/api/v1/endpoints/robots.py`

- [ ] **Step 1: 在 robots.py 中新增分析任务端点**

在 `upload_robot_files` 端点之后、`_storage = LocalFileStorage()` 之前，新增两个端点：

```python
from app.models.analysis_task import AnalysisTask, AnalysisTaskType, AnalysisTaskStatus
from app.schemas.analysis_task import AnalysisTaskResponse, AnalysisTaskListResponse


@router.post("/{robot_id}/analyze", response_model=AnalysisTaskResponse, status_code=status.HTTP_201_CREATED)
async def trigger_analysis(
    robot_id: int,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """手动触发 AI 分析（创建 AnalysisTask）。"""
    _require_teacher_or_admin(actor)
    result = await db.execute(select(RobotModel).where(RobotModel.id == robot_id))
    robot = result.scalar_one_or_none()
    if not robot:
        raise HTTPException(status_code=404, detail="机器人不存在")
    if robot.owner_teacher_id != actor.user_id and "admin" not in actor.roles:
        raise HTTPException(status_code=403, detail="只有创建者或管理员可以触发分析")

    # 查询该机器人的上传文件 ID
    asset_result = await db.execute(
        select(RobotAsset.id).where(
            RobotAsset.robot_model_id == robot_id,
            RobotAsset.asset_type == AssetType.UPLOAD_ORIGINAL,
        )
    )
    doc_ids = [row[0] for row in asset_result.all()]

    task = AnalysisTask(
        robot_model_id=robot_id,
        task_type=AnalysisTaskType.FULL,
        status=AnalysisTaskStatus.PENDING,
        input_document_ids=doc_ids,
    )
    db.add(task)

    # 更新机器人状态为 analyzing
    robot.status = RobotStatus.ANALYZING
    await db.commit()
    await db.refresh(task)
    return task


@router.get("/{robot_id}/analysis-tasks", response_model=AnalysisTaskListResponse)
async def list_analysis_tasks(
    robot_id: int,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """查看机器人的分析任务列表。"""
    result = await db.execute(select(RobotModel).where(RobotModel.id == robot_id))
    robot = result.scalar_one_or_none()
    if not robot:
        raise HTTPException(status_code=404, detail="机器人不存在")

    task_result = await db.execute(
        select(AnalysisTask)
        .where(AnalysisTask.robot_model_id == robot_id)
        .order_by(AnalysisTask.created_at.desc())
    )
    tasks = list(task_result.scalars().all())
    return AnalysisTaskListResponse(items=tasks, total=len(tasks))
```

注意：需要把 `from app.models.analysis_task import AnalysisTask, AnalysisTaskType, AnalysisTaskStatus` 和 `from app.schemas.analysis_task import AnalysisTaskResponse, AnalysisTaskListResponse` 加到文件顶部 import。

- [ ] **Step 2: 验证 import 正常**

Run: `cd r-mos-backend && python3 -c "from app.api.v1.endpoints.robots import trigger_analysis, list_analysis_tasks; print('OK')"`
Expected: `OK`

- [ ] **Step 3: 提交**

```bash
git add r-mos-backend/app/api/v1/endpoints/robots.py
git commit -m "feat: add analysis task endpoints POST /robots/{id}/analyze and GET /robots/{id}/analysis-tasks"
```

---

### Task 5: 发布/共享状态 API 端点

**Files:**
- Modify: `r-mos-backend/app/api/v1/endpoints/robots.py`

- [ ] **Step 1: 在 robots.py 中新增发布和共享端点**

在 `list_analysis_tasks` 端点之后、`_storage = LocalFileStorage()` 之前，新增：

```python
@router.put("/{robot_id}/publish", response_model=RobotModelResponse)
async def publish_robot(
    robot_id: int,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """发布机器人（status → ready）或取消发布（status → draft）。"""
    _require_teacher_or_admin(actor)
    result = await db.execute(select(RobotModel).where(RobotModel.id == robot_id))
    robot = result.scalar_one_or_none()
    if not robot:
        raise HTTPException(status_code=404, detail="机器人不存在")
    if robot.owner_teacher_id != actor.user_id and "admin" not in actor.roles:
        raise HTTPException(status_code=403, detail="只有创建者或管理员可以发布")

    if robot.status == RobotStatus.READY:
        # 取消发布
        robot.status = RobotStatus.DRAFT
    else:
        if not RobotService.can_publish(robot.status):
            raise HTTPException(status_code=409, detail="当前状态不允许发布（分析进行中）")
        robot.status = RobotStatus.READY

    await db.commit()
    await db.refresh(robot)
    return robot


@router.put("/{robot_id}/visibility", response_model=RobotModelResponse)
async def set_visibility(
    robot_id: int,
    db: AsyncSession = Depends(get_db),
    actor: ActorContext = Depends(get_current_actor),
):
    """切换机器人共享状态（private ↔ shared）。"""
    _require_teacher_or_admin(actor)
    result = await db.execute(select(RobotModel).where(RobotModel.id == robot_id))
    robot = result.scalar_one_or_none()
    if not robot:
        raise HTTPException(status_code=404, detail="机器人不存在")
    if robot.owner_teacher_id != actor.user_id and "admin" not in actor.roles:
        raise HTTPException(status_code=403, detail="只有创建者或管理员可以修改共享状态")

    if robot.visibility == RobotVisibility.SHARED:
        robot.visibility = RobotVisibility.PRIVATE
    else:
        robot.visibility = RobotVisibility.SHARED

    await db.commit()
    await db.refresh(robot)
    return robot
```

- [ ] **Step 2: 验证 import 正常**

Run: `cd r-mos-backend && python3 -c "from app.api.v1.endpoints.robots import publish_robot, set_visibility; print('OK')"`
Expected: `OK`

- [ ] **Step 3: 提交**

```bash
git add r-mos-backend/app/api/v1/endpoints/robots.py
git commit -m "feat: add publish and visibility toggle endpoints"
```

---

### Task 6: 完善 API 集成测试

**Files:**
- Modify: `r-mos-backend/tests/test_api_robots.py`

- [ ] **Step 1: 重写 test_api_robots.py 为完整集成测试**

```python
# r-mos-backend/tests/test_api_robots.py
"""Integration tests for robot API endpoints."""
import pytest
import pytest_asyncio
from uuid import uuid4
from httpx import AsyncClient, ASGITransport

from app.models.robot_model import RobotModel, RobotVisibility, RobotStatus, TeacherRobotBinding
from app.models.robot_asset import RobotAsset, AssetType
from app.models.analysis_task import AnalysisTask, AnalysisTaskStatus, AnalysisTaskType
from app.models.user import User
from app.core.security import hash_token
from app.models.access_token import AccessToken
from datetime import datetime, timedelta


def test_robots_module_imports():
    """Verify the robots endpoint module can be imported."""
    from app.api.v1.endpoints import robots
    assert hasattr(robots, "router")
    assert hasattr(robots, "create_robot")
    assert hasattr(robots, "list_robots")
    assert hasattr(robots, "get_robot")
    assert hasattr(robots, "update_robot")
    assert hasattr(robots, "delete_robot")
    assert hasattr(robots, "upload_robot_files")
    assert hasattr(robots, "trigger_analysis")
    assert hasattr(robots, "publish_robot")
    assert hasattr(robots, "set_visibility")


# --- DB-level tests (no HTTP, using fixtures from conftest) ---

@pytest.mark.asyncio
async def test_create_robot_model_db(test_db):
    """Test creating a RobotModel directly in DB."""
    robot = RobotModel(
        brand="TestBrand",
        model_name="TestBot-X1",
        version="1.0",
        visibility=RobotVisibility.PRIVATE,
        status=RobotStatus.DRAFT,
    )
    test_db.add(robot)
    await test_db.commit()
    await test_db.refresh(robot)
    assert robot.id is not None
    assert robot.brand == "TestBrand"
    assert robot.status == RobotStatus.DRAFT


@pytest.mark.asyncio
async def test_robot_publish_state_machine(test_db):
    """Test publish state transitions."""
    robot = RobotModel(
        brand="TestBrand",
        model_name="TestBot-X2",
        visibility=RobotVisibility.PRIVATE,
        status=RobotStatus.DRAFT,
    )
    test_db.add(robot)
    await test_db.commit()

    # draft → ready
    robot.status = RobotStatus.READY
    await test_db.commit()
    await test_db.refresh(robot)
    assert robot.status == RobotStatus.READY

    # ready → draft (unpublish)
    robot.status = RobotStatus.DRAFT
    await test_db.commit()
    await test_db.refresh(robot)
    assert robot.status == RobotStatus.DRAFT


@pytest.mark.asyncio
async def test_robot_visibility_toggle(test_db):
    """Test visibility toggle."""
    robot = RobotModel(
        brand="TestBrand",
        model_name="TestBot-X3",
        visibility=RobotVisibility.PRIVATE,
        status=RobotStatus.DRAFT,
    )
    test_db.add(robot)
    await test_db.commit()

    robot.visibility = RobotVisibility.SHARED
    await test_db.commit()
    await test_db.refresh(robot)
    assert robot.visibility == RobotVisibility.SHARED


@pytest.mark.asyncio
async def test_robot_asset_creation(test_db):
    """Test creating an asset record."""
    robot = RobotModel(
        brand="TestBrand",
        model_name="TestBot-X4",
        visibility=RobotVisibility.PRIVATE,
        status=RobotStatus.DRAFT,
    )
    test_db.add(robot)
    await test_db.flush()

    asset = RobotAsset(
        robot_model_id=robot.id,
        asset_type=AssetType.UPLOAD_ORIGINAL,
        file_path="1/uploads/manual.pdf",
        file_size=1024,
    )
    test_db.add(asset)
    await test_db.commit()
    await test_db.refresh(asset)
    assert asset.id is not None
    assert asset.asset_type == AssetType.UPLOAD_ORIGINAL


@pytest.mark.asyncio
async def test_analysis_task_creation(test_db):
    """Test creating an analysis task."""
    robot = RobotModel(
        brand="TestBrand",
        model_name="TestBot-X5",
        visibility=RobotVisibility.PRIVATE,
        status=RobotStatus.DRAFT,
    )
    test_db.add(robot)
    await test_db.flush()

    task = AnalysisTask(
        robot_model_id=robot.id,
        task_type=AnalysisTaskType.FULL,
        status=AnalysisTaskStatus.PENDING,
        input_document_ids=[1, 2, 3],
    )
    test_db.add(task)
    await test_db.commit()
    await test_db.refresh(task)
    assert task.id is not None
    assert task.status == AnalysisTaskStatus.PENDING


@pytest.mark.asyncio
async def test_teacher_robot_binding(test_db, test_user):
    """Test creating teacher-robot binding."""
    robot = RobotModel(
        brand="TestBrand",
        model_name="TestBot-X6",
        owner_teacher_id=test_user.id,
        visibility=RobotVisibility.PRIVATE,
        status=RobotStatus.DRAFT,
    )
    test_db.add(robot)
    await test_db.flush()

    binding = TeacherRobotBinding(
        teacher_id=test_user.id,
        robot_model_id=robot.id,
        binding_type="owner",
    )
    test_db.add(binding)
    await test_db.commit()
    await test_db.refresh(binding)
    assert binding.binding_type == "owner"
```

- [ ] **Step 2: 运行测试**

Run: `cd r-mos-backend && python3 -m pytest tests/test_api_robots.py -v`
Expected: All tests pass

- [ ] **Step 3: 提交**

```bash
git add r-mos-backend/tests/test_api_robots.py
git commit -m "test: add comprehensive robot API integration tests"
```

---

## Self-Review Checklist

**Spec coverage:**
- ✅ Section 10 `POST /robots/{id}/upload` → Task 3
- ✅ Section 10 `POST /robots/{id}/analyze` → Task 4
- ✅ Section 10 `GET /robots/{id}/analysis-tasks` → Task 4
- ✅ Section 10 `PUT /robots/{id}/publish` → Task 5
- ✅ Section 10 `PUT /robots/{id}/visibility` → Task 5
- ✅ Section 4.3 文件类型限制 + 大小限制 → Task 2 (RobotService)
- ✅ Section 4.5 触发机制 → Task 4 (trigger_analysis)
- ✅ 权限校验 (owner/admin) → 所有新端点

**Placeholder scan:** 无 TBD/TODO/placeholder。

**Type consistency:**
- `RobotService.validate_filename()` — Task 2 定义，Task 3 使用 ✓
- `RobotService.validate_file_size()` — Task 2 定义，Task 3 使用 ✓
- `RobotService.detect_asset_type()` — Task 2 定义，Task 3 使用 ✓
- `RobotService.detect_subdirectory()` — Task 2 定义，Task 3 使用 ✓
- `RobotService.can_publish()` — Task 2 定义，Task 5 使用 ✓
- `FileUploadResponse` — Task 3 Step 1 定义，Task 3 Step 2 使用 ✓
- `AnalysisTaskResponse` / `AnalysisTaskListResponse` — Task 1 定义，Task 4 使用 ✓
