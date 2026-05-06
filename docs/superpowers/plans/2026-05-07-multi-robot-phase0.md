# 多机器人平台 Phase 0：数据模型 + 存储服务 + atom01 迁移

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立多机器人平台的数据基础——新增 RobotModel/RobotAsset/TeacherRobotBinding/AnalysisTask 四张表，实现文件存储服务，将现有 atom01 硬编码数据迁移为第一个 RobotModel，项目瘦身 1.6GB。

**Architecture:** 在现有 SQLAlchemy 2.0+ 模型层新增四个 ORM 模型，扩展三个现有模型加 `robot_model_id` 外键。新增 `FileStorageService` 抽象层（先 LocalFileStorage 实现）。通过 Alembic 迁移和数据迁移脚本完成 atom01 的无损迁入。前端 `robots.ts` 配置改为从 API 动态获取。

**Tech Stack:** SQLAlchemy 2.0+ (AsyncSession), Alembic, Pydantic 2.x, FastAPI, pytest, React/TypeScript

**Design Spec:** `docs/superpowers/specs/2026-05-07-multi-robot-platform-design.md`

---

## File Structure

### 新增文件

| 文件 | 职责 |
|------|------|
| `r-mos-backend/app/models/robot_model.py` | RobotModel + TeacherRobotBinding ORM |
| `r-mos-backend/app/models/robot_asset.py` | RobotAsset ORM |
| `r-mos-backend/app/models/analysis_task.py` | AnalysisTask ORM |
| `r-mos-backend/app/schemas/robot_model.py` | RobotModel Pydantic schemas |
| `r-mos-backend/app/services/storage/file_storage.py` | FileStorageService 抽象 + LocalFileStorage 实现 |
| `r-mos-backend/app/api/v1/endpoints/robots.py` | 机器人 CRUD API（Phase 0 只做基础 CRUD） |
| `r-mos-backend/scripts/migrate_atom01.py` | atom01 数据迁移脚本 |
| `r-mos-backend/tests/test_models_robot.py` | RobotModel 模型测试 |
| `r-mos-backend/tests/test_storage.py` | FileStorageService 测试 |
| `r-mos-backend/tests/test_api_robots.py` | 机器人 API 测试 |

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `r-mos-backend/app/models/__init__.py` | 导出新模型 |
| `r-mos-backend/app/models/sop.py` | 加 `robot_model_id` 字段 |
| `r-mos-backend/app/models/knowledge_document.py` | 加 `robot_model_id` + `generation_status` 字段 |
| `r-mos-backend/app/models/fault_sop_mapping.py` | 加 `robot_model_id` 字段 |
| `r-mos-backend/alembic/env.py` | 导入新模型 |
| `r-mos-frontend/src/config/robots.ts` | 支持动态 robot 列表 |
| `.gitignore` | 加 `/data/robot-assets/` |

---

## Task 1: 新增 RobotModel + TeacherRobotBinding 模型

**Files:**
- Create: `r-mos-backend/app/models/robot_model.py`
- Create: `r-mos-backend/tests/test_models_robot.py`

- [ ] **Step 1: Write the failing test**

```python
# r-mos-backend/tests/test_models_robot.py
"""Tests for RobotModel and TeacherRobotBinding ORM models."""
import pytest
from sqlalchemy import select
from app.models.robot_model import RobotModel, TeacherRobotBinding, RobotVisibility, RobotStatus


@pytest.mark.asyncio
async def test_create_robot_model(db_session):
    """RobotModel can be created with required fields."""
    robot = RobotModel(
        brand="R-MOS",
        model_name="ATOM-01",
        version="1.0",
        visibility=RobotVisibility.PRIVATE,
        status=RobotStatus.DRAFT,
    )
    db_session.add(robot)
    await db_session.commit()
    await db_session.refresh(robot)

    assert robot.id is not None
    assert robot.brand == "R-MOS"
    assert robot.model_name == "ATOM-01"
    assert robot.visibility == RobotVisibility.PRIVATE
    assert robot.status == RobotStatus.DRAFT
    assert robot.owner_teacher_id is None  # system built-in
    assert robot.created_at is not None


@pytest.mark.asyncio
async def test_create_teacher_binding(db_session):
    """TeacherRobotBinding links a teacher to a robot model."""
    robot = RobotModel(brand="宇树", model_name="H1", version="2.0")
    db_session.add(robot)
    await db_session.commit()
    await db_session.refresh(robot)

    binding = TeacherRobotBinding(
        teacher_id=1,
        robot_model_id=robot.id,
        binding_type="owner",
    )
    db_session.add(binding)
    await db_session.commit()
    await db_session.refresh(binding)

    assert binding.id is not None
    assert binding.teacher_id == 1
    assert binding.robot_model_id == robot.id
    assert binding.binding_type == "owner"


@pytest.mark.asyncio
async def test_robot_model_shared_visibility(db_session):
    """RobotModel visibility can be set to shared."""
    robot = RobotModel(
        brand="优必选",
        model_name="Walker X",
        version="1.0",
        visibility=RobotVisibility.SHARED,
        status=RobotStatus.READY,
        description="通用人形机器人",
    )
    db_session.add(robot)
    await db_session.commit()

    result = await db_session.execute(
        select(RobotModel).where(RobotModel.visibility == RobotVisibility.SHARED)
    )
    found = result.scalar_one()
    assert found.brand == "优必选"
    assert found.status == RobotStatus.READY
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd r-mos-backend && source venv/bin/activate && pytest tests/test_models_robot.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.models.robot_model'`

- [ ] **Step 3: Write the RobotModel and TeacherRobotBinding models**

```python
# r-mos-backend/app/models/robot_model.py
"""RobotModel and TeacherRobotBinding ORM models."""
import enum
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class RobotVisibility(str, enum.Enum):
    PRIVATE = "private"
    SHARED = "shared"


class RobotStatus(str, enum.Enum):
    DRAFT = "draft"
    ANALYZING = "analyzing"
    READY = "ready"


class RobotModel(Base, TimestampMixin):
    """机器人型号目录表。每条记录代表一个品牌+型号的机器人。"""
    __tablename__ = "robot_models"

    id = Column(Integer, primary_key=True, index=True)
    brand = Column(String(100), nullable=False, index=True, comment="品牌")
    model_name = Column(String(200), nullable=False, index=True, comment="型号名称")
    version = Column(String(50), default="1.0", comment="版本号")
    owner_teacher_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        comment="创建者教师 ID（null 表示系统内置）",
    )
    visibility = Column(
        Enum(RobotVisibility), default=RobotVisibility.PRIVATE,
        nullable=False, comment="可见性: private/shared",
    )
    status = Column(
        Enum(RobotStatus), default=RobotStatus.DRAFT,
        nullable=False, comment="状态: draft/analyzing/ready",
    )
    description = Column(Text, nullable=True, comment="机器人描述")
    thumbnail_path = Column(String(500), nullable=True, comment="缩略图相对路径")

    # relationships
    assets = relationship("RobotAsset", back_populates="robot_model", cascade="all, delete-orphan")
    bindings = relationship("TeacherRobotBinding", back_populates="robot_model", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<RobotModel(id={self.id}, brand={self.brand}, model={self.model_name})>"


class TeacherRobotBinding(Base, TimestampMixin):
    """教师与机器人的绑定关系（选配表）。"""
    __tablename__ = "teacher_robot_bindings"
    __table_args__ = (
        UniqueConstraint("teacher_id", "robot_model_id", name="uq_teacher_robot"),
    )

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="教师用户 ID",
    )
    robot_model_id = Column(
        Integer, ForeignKey("robot_models.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="机器人型号 ID",
    )
    binding_type = Column(
        String(20), nullable=False, default="owner",
        comment="绑定类型: owner/shared_ref",
    )

    # relationships
    robot_model = relationship("RobotModel", back_populates="bindings")

    def __repr__(self):
        return f"<TeacherRobotBinding(teacher={self.teacher_id}, robot={self.robot_model_id})>"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd r-mos-backend && pytest tests/test_models_robot.py -v`
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add r-mos-backend/app/models/robot_model.py r-mos-backend/tests/test_models_robot.py
git commit -m "feat: add RobotModel and TeacherRobotBinding ORM models"
```

---

## Task 2: 新增 RobotAsset + AnalysisTask 模型

**Files:**
- Create: `r-mos-backend/app/models/robot_asset.py`
- Create: `r-mos-backend/app/models/analysis_task.py`
- Modify: `r-mos-backend/tests/test_models_robot.py` (追加测试)

- [ ] **Step 1: Write failing tests**

追加到 `tests/test_models_robot.py`:

```python
from app.models.robot_asset import RobotAsset, AssetType
from app.models.analysis_task import AnalysisTask, AnalysisTaskType, AnalysisTaskStatus


@pytest.mark.asyncio
async def test_create_robot_asset(db_session):
    """RobotAsset stores a file reference for a robot model."""
    robot = RobotModel(brand="R-MOS", model_name="ATOM-01", version="1.0")
    db_session.add(robot)
    await db_session.commit()
    await db_session.refresh(robot)

    asset = RobotAsset(
        robot_model_id=robot.id,
        asset_type=AssetType.MODEL_GLB,
        file_path="models/base_link.glb",
        file_size=1_100_000,
        metadata={"vertices": 12000, "faces": 8000},
    )
    db_session.add(asset)
    await db_session.commit()
    await db_session.refresh(asset)

    assert asset.id is not None
    assert asset.asset_type == AssetType.MODEL_GLB
    assert asset.file_size == 1_100_000
    assert asset.metadata["vertices"] == 12000


@pytest.mark.asyncio
async def test_create_analysis_task(db_session):
    """AnalysisTask tracks an AI analysis job."""
    robot = RobotModel(brand="宇树", model_name="H1", version="2.0")
    db_session.add(robot)
    await db_session.commit()
    await db_session.refresh(robot)

    task = AnalysisTask(
        robot_model_id=robot.id,
        task_type=AnalysisTaskType.PDF_EXTRACT,
        status=AnalysisTaskStatus.PENDING,
        input_document_ids=[1, 2, 3],
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    assert task.id is not None
    assert task.status == AnalysisTaskStatus.PENDING
    assert task.input_document_ids == [1, 2, 3]
    assert task.completed_at is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd r-mos-backend && pytest tests/test_models_robot.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write RobotAsset model**

```python
# r-mos-backend/app/models/robot_asset.py
"""RobotAsset ORM model — tracks files belonging to a robot model."""
import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class AssetType(str, enum.Enum):
    MODEL_GLB = "model_glb"
    MANIFEST = "manifest"
    THUMBNAIL = "thumbnail"
    UPLOAD_ORIGINAL = "upload_original"


class RobotAsset(Base, TimestampMixin):
    """机器人资产文件记录。"""
    __tablename__ = "robot_assets"

    id = Column(Integer, primary_key=True, index=True)
    robot_model_id = Column(
        Integer, ForeignKey("robot_models.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    asset_type = Column(Enum(AssetType), nullable=False, comment="资产类型")
    file_path = Column(String(500), nullable=False, comment="相对存储路径")
    file_size = Column(Integer, nullable=True, comment="文件大小（字节）")
    metadata = Column(JSON, nullable=True, comment="元数据（顶点数、节点数等）")

    # relationships
    robot_model = relationship("RobotModel", back_populates="assets")

    def __repr__(self):
        return f"<RobotAsset(id={self.id}, type={self.asset_type}, path={self.file_path})>"
```

- [ ] **Step 4: Write AnalysisTask model**

```python
# r-mos-backend/app/models/analysis_task.py
"""AnalysisTask ORM model — tracks AI analysis jobs for robot models."""
import enum
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum, DateTime, JSON
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class AnalysisTaskType(str, enum.Enum):
    PDF_EXTRACT = "pdf_extract"
    CAD_PARSE = "cad_parse"
    SOP_GENERATE = "sop_generate"
    FULL = "full"


class AnalysisTaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisTask(Base, TimestampMixin):
    """AI 分析任务记录。"""
    __tablename__ = "analysis_tasks"

    id = Column(Integer, primary_key=True, index=True)
    robot_model_id = Column(
        Integer, ForeignKey("robot_models.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    task_type = Column(Enum(AnalysisTaskType), nullable=False, comment="任务类型")
    status = Column(
        Enum(AnalysisTaskStatus), default=AnalysisTaskStatus.PENDING,
        nullable=False, index=True, comment="任务状态",
    )
    input_document_ids = Column(JSON, default=list, comment="输入文档 ID 列表")
    output_summary = Column(JSON, nullable=True, comment="分析结果摘要")
    error_message = Column(Text, nullable=True, comment="失败原因")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")

    # relationships
    robot_model = relationship("RobotModel")

    def __repr__(self):
        return f"<AnalysisTask(id={self.id}, type={self.task_type}, status={self.status})>"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd r-mos-backend && pytest tests/test_models_robot.py -v`
Expected: 5 tests PASS

- [ ] **Step 6: Commit**

```bash
git add r-mos-backend/app/models/robot_asset.py r-mos-backend/app/models/analysis_task.py r-mos-backend/tests/test_models_robot.py
git commit -m "feat: add RobotAsset and AnalysisTask ORM models"
```

---

## Task 3: 扩展现有模型 + 注册到 __init__.py

**Files:**
- Modify: `r-mos-backend/app/models/sop.py`
- Modify: `r-mos-backend/app/models/knowledge_document.py`
- Modify: `r-mos-backend/app/models/fault_sop_mapping.py`
- Modify: `r-mos-backend/app/models/__init__.py`

- [ ] **Step 1: Add robot_model_id to SOP model**

在 `r-mos-backend/app/models/sop.py` 的 `SOP` 类中，`estimated_time` 字段之后添加：

```python
    robot_model_id = Column(
        Integer, ForeignKey("robot_models.id", ondelete="SET NULL"),
        nullable=True, index=True, comment="关联机器人型号 ID",
    )
```

需要在文件顶部确保 `ForeignKey` 已在 import 中（已存在）。

- [ ] **Step 2: Add robot_model_id + generation_status to KnowledgeDocument model**

在 `r-mos-backend/app/models/knowledge_document.py` 的 `KnowledgeDocument` 类中，`approved_at` 字段之后添加：

```python
    robot_model_id = Column(
        Integer, ForeignKey("robot_models.id", ondelete="SET NULL"),
        nullable=True, index=True, comment="关联机器人型号 ID",
    )
    generation_status = Column(
        String(20), default="manual",
        comment="生成状态: manual/ai_draft/published",
    )
```

需要在文件顶部 import 中添加 `ForeignKey`：

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
```

- [ ] **Step 3: Add robot_model_id to FaultSOPMapping model**

在 `r-mos-backend/app/models/fault_sop_mapping.py` 的 `FaultSOPMapping` 类中，`priority` 字段之后添加：

```python
    robot_model_id = Column(
        Integer, ForeignKey("robot_models.id", ondelete="SET NULL"),
        nullable=True, index=True, comment="关联机器人型号 ID",
    )
```

`ForeignKey` 已在 import 中。

- [ ] **Step 4: Register new models in __init__.py**

在 `r-mos-backend/app/models/__init__.py` 的 import 区域末尾添加：

```python
from app.models.robot_model import RobotModel, RobotVisibility, RobotStatus, TeacherRobotBinding
from app.models.robot_asset import RobotAsset, AssetType
from app.models.analysis_task import AnalysisTask, AnalysisTaskType, AnalysisTaskStatus
```

在 `__all__` 列表末尾添加：

```python
    # Robot platform
    "RobotModel",
    "RobotVisibility",
    "RobotStatus",
    "TeacherRobotBinding",
    "RobotAsset",
    "AssetType",
    "AnalysisTask",
    "AnalysisTaskType",
    "AnalysisTaskStatus",
```

- [ ] **Step 5: Run full model tests**

Run: `cd r-mos-backend && pytest tests/test_models_robot.py -v`
Expected: 5 tests PASS

- [ ] **Step 6: Commit**

```bash
git add r-mos-backend/app/models/sop.py r-mos-backend/app/models/knowledge_document.py r-mos-backend/app/models/fault_sop_mapping.py r-mos-backend/app/models/__init__.py
git commit -m "feat: extend SOP/KnowledgeDocument/FaultSOPMapping with robot_model_id"
```

---

## Task 4: Alembic 迁移

**Files:**
- Modify: `r-mos-backend/alembic/env.py`
- Create: new migration file (auto-generated)

- [ ] **Step 1: Update alembic env.py to import new models**

在 `r-mos-backend/alembic/env.py` 的 import 区域，现有 `from app.models import (...)` 块中添加：

```python
from app.models import (
    Base,
    SOP, SOPStep,
    Task,
    Event,
    Snapshot,
    FaultCase,
    Incident,
    Observation,
    EvidenceBundle, EvidenceItem,
    AssessmentProvider, ExternalAssessment, AssessmentAuditEvent,
    RobotModel, TeacherRobotBinding,
    RobotAsset,
    AnalysisTask,
)
```

- [ ] **Step 2: Generate migration**

Run:
```bash
cd r-mos-backend && source venv/bin/activate && alembic revision --autogenerate -m "add_robot_platform_tables"
```

Expected: 新迁移文件生成在 `alembic/versions/` 下，包含：
- `create_table robot_models`
- `create_table teacher_robot_bindings`
- `create_table robot_assets`
- `create_table analysis_tasks`
- `add_column sops.robot_model_id`
- `add_column knowledge_documents.robot_model_id`
- `add_column knowledge_documents.generation_status`
- `add_column fault_sop_mappings.robot_model_id`

- [ ] **Step 3: Review generated migration file**

打开生成的迁移文件，检查 `upgrade()` 和 `downgrade()` 函数是否正确包含所有新表和新字段。

- [ ] **Step 4: Run migration**

Run:
```bash
cd r-mos-backend && alembic upgrade head
```

Expected: 迁移成功，无报错

- [ ] **Step 5: Verify tables exist**

Run:
```bash
cd r-mos-backend && python -c "
import asyncio
from sqlalchemy import text
from app.core.database import engine

async def check():
    async with engine.begin() as conn:
        for table in ['robot_models', 'teacher_robot_bindings', 'robot_assets', 'analysis_tasks']:
            result = await conn.execute(text(f\"SELECT COUNT(*) FROM {table}\"))
            print(f'{table}: OK (count={result.scalar()})')
        # check new columns
        result = await conn.execute(text('SELECT robot_model_id FROM sops LIMIT 0'))
        print('sops.robot_model_id: OK')
        result = await conn.execute(text('SELECT robot_model_id, generation_status FROM knowledge_documents LIMIT 0'))
        print('knowledge_documents.robot_model_id + generation_status: OK')

asyncio.run(check())
"
```

- [ ] **Step 6: Commit**

```bash
git add r-mos-backend/alembic/env.py r-mos-backend/alembic/versions/
git commit -m "feat: add robot platform tables migration"
```

---

## Task 5: FileStorageService 实现

**Files:**
- Create: `r-mos-backend/app/services/storage/file_storage.py`
- Create: `r-mos-backend/app/services/storage/__init__.py`
- Create: `r-mos-backend/tests/test_storage.py`

- [ ] **Step 1: Write the failing tests**

```python
# r-mos-backend/tests/test_storage.py
"""Tests for FileStorageService (local filesystem implementation)."""
import pytest
import os
import tempfile
from pathlib import Path
from app.services.storage.file_storage import LocalFileStorage


@pytest.fixture
def storage(tmp_path):
    """Create a LocalFileStorage with a temp directory."""
    return LocalFileStorage(base_dir=str(tmp_path))


def test_upload_file(storage, tmp_path):
    """upload() saves file and returns relative path."""
    content = b"fake GLB binary content"
    rel_path = storage.upload(
        robot_model_id=42,
        filename="base_link.glb",
        content=content,
        subdirectory="models",
    )

    assert rel_path == "42/models/base_link.glb"
    full_path = tmp_path / "42" / "models" / "base_link.glb"
    assert full_path.exists()
    assert full_path.read_bytes() == content


def test_download_file(storage, tmp_path):
    """download() returns file content."""
    # setup
    (tmp_path / "42" / "models").mkdir(parents=True)
    (tmp_path / "42" / "models" / "torso.glb").write_bytes(b"torso data")

    content = storage.download(robot_model_id=42, rel_path="models/torso.glb")
    assert content == b"torso data"


def test_download_nonexistent_raises(storage):
    """download() raises FileNotFoundError for missing files."""
    with pytest.raises(FileNotFoundError):
        storage.download(robot_model_id=99, rel_path="no/such/file.glb")


def test_delete_file(storage, tmp_path):
    """delete() removes a file."""
    (tmp_path / "42" / "models").mkdir(parents=True)
    target = tmp_path / "42" / "models" / "old.glb"
    target.write_bytes(b"old data")

    storage.delete(robot_model_id=42, rel_path="models/old.glb")
    assert not target.exists()


def test_list_files(storage, tmp_path):
    """list_files() returns all files under a robot's directory."""
    base = tmp_path / "42" / "models"
    base.mkdir(parents=True)
    (base / "a.glb").write_bytes(b"a")
    (base / "b.glb").write_bytes(b"b")

    files = storage.list_files(robot_model_id=42, subdirectory="models")
    assert sorted(files) == ["models/a.glb", "models/b.glb"]


def test_get_full_path(storage, tmp_path):
    """get_full_path() returns absolute path for serving files."""
    full = storage.get_full_path(robot_model_id=42, rel_path="models/base.glb")
    assert full == str(tmp_path / "42" / "models" / "base.glb")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd r-mos-backend && pytest tests/test_storage.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write FileStorageService**

```python
# r-mos-backend/app/services/storage/__init__.py
from .file_storage import FileStorageBase, LocalFileStorage

__all__ = ["FileStorageBase", "LocalFileStorage"]
```

```python
# r-mos-backend/app/services/storage/file_storage.py
"""File storage abstraction for robot assets.

LocalFileStorage stores files on local disk.
Interface is designed to be swappable with OSS/S3 later.
"""
import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

from app.core.config import settings


class FileStorageBase(ABC):
    """Abstract file storage interface."""

    @abstractmethod
    def upload(self, robot_model_id: int, filename: str, content: bytes, subdirectory: str = "") -> str:
        """Save file content. Returns relative path."""
        ...

    @abstractmethod
    def download(self, robot_model_id: int, rel_path: str) -> bytes:
        """Read file content. Raises FileNotFoundError if missing."""
        ...

    @abstractmethod
    def delete(self, robot_model_id: int, rel_path: str) -> None:
        """Delete a file."""
        ...

    @abstractmethod
    def list_files(self, robot_model_id: int, subdirectory: str = "") -> List[str]:
        """List relative paths under a robot's subdirectory."""
        ...

    @abstractmethod
    def get_full_path(self, robot_model_id: int, rel_path: str) -> str:
        """Get absolute filesystem path (for serving via API)."""
        ...


class LocalFileStorage(FileStorageBase):
    """Local filesystem storage implementation."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or getattr(settings, "ROBOT_ASSETS_DIR", "data/robot-assets"))

    def _robot_dir(self, robot_model_id: int) -> Path:
        return self.base_dir / str(robot_model_id)

    def upload(self, robot_model_id: int, filename: str, content: bytes, subdirectory: str = "") -> str:
        target_dir = self._robot_dir(robot_model_id)
        if subdirectory:
            target_dir = target_dir / subdirectory
        target_dir.mkdir(parents=True, exist_ok=True)

        target_file = target_dir / filename
        target_file.write_bytes(content)

        # return relative path: "{robot_model_id}/{subdirectory}/{filename}"
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
        return str(self._robot_dir(robot_model_id) / rel_path)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd r-mos-backend && pytest tests/test_storage.py -v`
Expected: 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add r-mos-backend/app/services/storage/ r-mos-backend/tests/test_storage.py
git commit -m "feat: add FileStorageService with local filesystem implementation"
```

---

## Task 6: Pydantic Schemas for RobotModel

**Files:**
- Create: `r-mos-backend/app/schemas/robot_model.py`

- [ ] **Step 1: Write the schemas**

```python
# r-mos-backend/app/schemas/robot_model.py
"""Pydantic schemas for RobotModel CRUD operations."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class RobotModelCreate(BaseModel):
    """Request body for creating a new RobotModel."""
    brand: str = Field(..., max_length=100, description="机器人品牌")
    model_name: str = Field(..., max_length=200, description="型号名称")
    version: str = Field(default="1.0", max_length=50, description="版本号")
    description: Optional[str] = Field(default=None, description="描述")


class RobotModelUpdate(BaseModel):
    """Request body for updating a RobotModel."""
    brand: Optional[str] = Field(default=None, max_length=100)
    model_name: Optional[str] = Field(default=None, max_length=200)
    version: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = None
    visibility: Optional[str] = Field(default=None, pattern="^(private|shared)$")


class RobotModelResponse(BaseModel):
    """Response body for a RobotModel."""
    id: int
    brand: str
    model_name: str
    version: str
    owner_teacher_id: Optional[int] = None
    visibility: str
    status: str
    description: Optional[str] = None
    thumbnail_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RobotModelListResponse(BaseModel):
    """Paginated list of RobotModels."""
    items: List[RobotModelResponse]
    total: int


class RobotAssetResponse(BaseModel):
    """Response body for a RobotAsset."""
    id: int
    robot_model_id: int
    asset_type: str
    file_path: str
    file_size: Optional[int] = None
    metadata: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Commit**

```bash
git add r-mos-backend/app/schemas/robot_model.py
git commit -m "feat: add Pydantic schemas for RobotModel CRUD"
```

---

## Task 7: 基础 Robot CRUD API

**Files:**
- Create: `r-mos-backend/app/api/v1/endpoints/robots.py`
- Create: `r-mos-backend/tests/test_api_robots.py`

- [ ] **Step 1: Write failing API tests**

```python
# r-mos-backend/tests/test_api_robots.py
"""Tests for robot CRUD API endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_robot(async_client: AsyncClient, teacher_token: str):
    """POST /api/v1/robots creates a new robot model."""
    resp = await async_client.post(
        "/api/v1/robots",
        json={"brand": "宇树", "model_name": "H1", "version": "2.0"},
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["brand"] == "宇树"
    assert data["model_name"] == "H1"
    assert data["status"] == "draft"
    assert data["visibility"] == "private"


@pytest.mark.asyncio
async def test_list_robots(async_client: AsyncClient, teacher_token: str):
    """GET /api/v1/robots returns teacher's robots."""
    # create one first
    await async_client.post(
        "/api/v1/robots",
        json={"brand": "优必选", "model_name": "Walker X"},
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    resp = await async_client.get(
        "/api/v1/robots",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_get_robot_detail(async_client: AsyncClient, teacher_token: str):
    """GET /api/v1/robots/{id} returns robot details."""
    create_resp = await async_client.post(
        "/api/v1/robots",
        json={"brand": "达闼", "model_name": "XR4"},
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    robot_id = create_resp.json()["id"]

    resp = await async_client.get(
        f"/api/v1/robots/{robot_id}",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["brand"] == "达闼"


@pytest.mark.asyncio
async def test_student_cannot_create_robot(async_client: AsyncClient, student_token: str):
    """Students should not be able to create robots."""
    resp = await async_client.post(
        "/api/v1/robots",
        json={"brand": "Test", "model_name": "Bot"},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 403
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd r-mos-backend && pytest tests/test_api_robots.py -v`
Expected: FAIL (endpoint doesn't exist)

- [ ] **Step 3: Write the API endpoint**

```python
# r-mos-backend/app/api/v1/endpoints/robots.py
"""Robot model CRUD API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.robot_model import RobotModel, RobotVisibility, RobotStatus, TeacherRobotBinding
from app.models.user import User
from app.schemas.robot_model import (
    RobotModelCreate,
    RobotModelUpdate,
    RobotModelResponse,
    RobotModelListResponse,
)

router = APIRouter(prefix="/robots", tags=["robots"])


def _require_teacher_or_admin(user: User):
    """Raise 403 if user is not teacher or admin."""
    if user.role not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="教师或管理员权限才能操作机器人")


@router.post("", response_model=RobotModelResponse, status_code=status.HTTP_201_CREATED)
async def create_robot(
    body: RobotModelCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建新机器人型号。"""
    _require_teacher_or_admin(current_user)

    robot = RobotModel(
        brand=body.brand,
        model_name=body.model_name,
        version=body.version,
        description=body.description,
        owner_teacher_id=current_user.id,
        visibility=RobotVisibility.PRIVATE,
        status=RobotStatus.DRAFT,
    )
    db.add(robot)

    # auto-create owner binding
    binding = TeacherRobotBinding(
        teacher_id=current_user.id,
        robot_model_id=robot.id,
        binding_type="owner",
    )
    db.add(binding)

    await db.commit()
    await db.refresh(robot)
    return robot


@router.get("", response_model=RobotModelListResponse)
async def list_robots(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出当前教师名下的机器人（自有 + 引用）。"""
    _require_teacher_or_admin(current_user)

    stmt = (
        select(RobotModel)
        .join(TeacherRobotBinding, TeacherRobotBinding.robot_model_id == RobotModel.id)
        .where(TeacherRobotBinding.teacher_id == current_user.id)
    )
    result = await db.execute(stmt)
    items = list(result.scalars().all())

    return RobotModelListResponse(items=items, total=len(items))


@router.get("/{robot_id}", response_model=RobotModelResponse)
async def get_robot(
    robot_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取机器人详情。"""
    result = await db.execute(select(RobotModel).where(RobotModel.id == robot_id))
    robot = result.scalar_one_or_none()
    if not robot:
        raise HTTPException(status_code=404, detail="机器人不存在")
    return robot


@router.put("/{robot_id}", response_model=RobotModelResponse)
async def update_robot(
    robot_id: int,
    body: RobotModelUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新机器人信息（仅 owner）。"""
    _require_teacher_or_admin(current_user)

    result = await db.execute(select(RobotModel).where(RobotModel.id == robot_id))
    robot = result.scalar_one_or_none()
    if not robot:
        raise HTTPException(status_code=404, detail="机器人不存在")
    if robot.owner_teacher_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="只有创建者或管理员可以编辑")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(robot, key, value)

    await db.commit()
    await db.refresh(robot)
    return robot


@router.delete("/{robot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_robot(
    robot_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除机器人（仅 owner）。"""
    _require_teacher_or_admin(current_user)

    result = await db.execute(select(RobotModel).where(RobotModel.id == robot_id))
    robot = result.scalar_one_or_none()
    if not robot:
        raise HTTPException(status_code=404, detail="机器人不存在")
    if robot.owner_teacher_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="只有创建者或管理员可以删除")

    await db.delete(robot)
    await db.commit()
```

- [ ] **Step 4: Register router in the app**

在 API 路由注册处（通常是 `app/api/v1/__init__.py` 或 `main.py`），添加：

```python
from app.api.v1.endpoints.robots import router as robots_router
app.include_router(robots_router, prefix="/api/v1")
```

查找具体的路由注册文件并添加。

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd r-mos-backend && pytest tests/test_api_robots.py -v`
Expected: 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add r-mos-backend/app/api/v1/endpoints/robots.py r-mos-backend/tests/test_api_robots.py
git commit -m "feat: add robot CRUD API endpoints"
```

---

## Task 8: atom01 数据迁移脚本

**Files:**
- Create: `r-mos-backend/scripts/migrate_atom01.py`

- [ ] **Step 1: Write the migration script**

```python
# r-mos-backend/scripts/migrate_atom01.py
"""
Migrate ATOM-01 from hardcoded assets to RobotModel data-driven architecture.

This script:
1. Creates a RobotModel record for ATOM-01 (system built-in)
2. Updates existing SOPs with robot_model_id
3. Updates existing KnowledgeDocuments with robot_model_id
4. Updates existing FaultSOPMappings with robot_model_id
5. Copies 3D model files from public/models/ to data/robot-assets/{id}/

Usage:
    cd r-mos-backend
    source venv/bin/activate
    python scripts/migrate_atom01.py
"""
import asyncio
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select, update
from app.core.database import async_session
from app.models.robot_model import RobotModel, RobotVisibility, RobotStatus
from app.models.sop import SOP
from app.models.knowledge_document import KnowledgeDocument
from app.models.fault_sop_mapping import FaultSOPMapping
from app.models.robot_asset import RobotAsset, AssetType

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent  # r-mos/
FRONTEND_MODELS = PROJECT_ROOT / "r-mos-frontend" / "public" / "models"
ASSETS_BASE = PROJECT_ROOT / "data" / "robot-assets"


async def main():
    async with async_session() as db:
        # 1. Check if ATOM-01 already exists
        result = await db.execute(
            select(RobotModel).where(
                RobotModel.brand == "R-MOS",
                RobotModel.model_name == "ATOM-01",
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            print(f"ATOM-01 already migrated (id={existing.id}). Skipping DB migration.")
            robot_id = existing.id
        else:
            # 2. Create RobotModel
            robot = RobotModel(
                brand="R-MOS",
                model_name="ATOM-01",
                version="1.0",
                owner_teacher_id=None,  # system built-in
                visibility=RobotVisibility.SHARED,
                status=RobotStatus.READY,
                description="R-MOS 原型人形机器人",
            )
            db.add(robot)
            await db.flush()
            robot_id = robot.id
            print(f"Created RobotModel ATOM-01 (id={robot_id})")

            # 3. Update existing records
            sop_result = await db.execute(
                update(SOP)
                .where(SOP.robot_model_id.is_(None))
                .values(robot_model_id=robot_id)
            )
            print(f"Updated {sop_result.rowcount} SOPs")

            kd_result = await db.execute(
                update(KnowledgeDocument)
                .where(KnowledgeDocument.robot_model_id.is_(None))
                .values(robot_model_id=robot_id, generation_status="published")
            )
            print(f"Updated {kd_result.rowcount} KnowledgeDocuments")

            fsm_result = await db.execute(
                update(FaultSOPMapping)
                .where(FaultSOPMapping.robot_model_id.is_(None))
                .values(robot_model_id=robot_id)
            )
            print(f"Updated {fsm_result.rowcount} FaultSOPMappings")

            await db.commit()

        # 4. Copy model files
        dest_dir = ASSETS_BASE / str(robot_id)
        src_robot = FRONTEND_MODELS / "robots" / "atom01"
        src_parts = FRONTEND_MODELS / "parts"

        if src_robot.exists() and not (dest_dir / "models").exists():
            dest_models = dest_dir / "models"
            print(f"Copying robot models: {src_robot} -> {dest_models}")
            shutil.copytree(src_robot, dest_models)

            # Copy assembly manifest if exists
            manifest_src = src_robot / "assembly_manifest.json"
            if manifest_src.exists():
                manifest_dest = dest_dir / "manifests"
                manifest_dest.mkdir(parents=True, exist_ok=True)
                shutil.copy2(manifest_src, manifest_dest / "assembly_manifest.json")
                print("Copied assembly_manifest.json")

            explode_src = src_robot / "explode_manifest.json"
            if explode_src.exists():
                shutil.copy2(explode_src, manifest_dest / "explode_manifest.json")
                print("Copied explode_manifest.json")
        else:
            print(f"Robot models already migrated or source not found: {src_robot}")

        if src_parts.exists() and not (dest_dir / "models" / "parts").exists():
            dest_parts = dest_dir / "models" / "parts"
            print(f"Copying parts catalog: {src_parts} -> {dest_parts}")
            print("This may take a while (1.6GB)...")
            shutil.copytree(src_parts, dest_parts)
            print("Parts catalog copied")
        else:
            print(f"Parts already migrated or source not found: {src_parts}")

        # 5. Register assets in DB
        async with async_session() as db2:
            existing_assets = await db2.execute(
                select(RobotAsset).where(RobotAsset.robot_model_id == robot_id)
            )
            if not existing_assets.scalars().first():
                models_dir = dest_dir / "models"
                if models_dir.exists():
                    for glb_file in models_dir.glob("*.glb"):
                        asset = RobotAsset(
                            robot_model_id=robot_id,
                            asset_type=AssetType.MODEL_GLB,
                            file_path=f"models/{glb_file.name}",
                            file_size=glb_file.stat().st_size,
                        )
                        db2.add(asset)
                    await db2.commit()
                    print("Registered GLB assets in database")

        print("\n=== Migration complete ===")
        print(f"RobotModel ID: {robot_id}")
        print(f"Assets directory: {dest_dir}")
        print(f"\nNext steps:")
        print(f"  1. Verify: ls {dest_dir}/models/")
        print(f"  2. After verification, delete: rm -rf {FRONTEND_MODELS}/robots/atom01 {FRONTEND_MODELS}/parts")
        print(f"  3. Update .gitignore to include /data/robot-assets/")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Update .gitignore**

在项目根目录 `.gitignore` 末尾添加：

```
# Robot asset storage (managed by backend, not tracked in git)
/data/robot-assets/
```

- [ ] **Step 3: Commit (script only, don't run yet)**

```bash
git add r-mos-backend/scripts/migrate_atom01.py .gitignore
git commit -m "feat: add atom01 migration script and update .gitignore"
```

---

## Task 9: 资产文件 API 端点

**Files:**
- Modify: `r-mos-backend/app/api/v1/endpoints/robots.py`

- [ ] **Step 1: Add asset serving endpoint to robots.py**

在 `robots.py` 末尾追加：

```python
from fastapi.responses import FileResponse
from app.services.storage.file_storage import LocalFileStorage

# Initialize storage (will be replaced with DI later)
_storage = LocalFileStorage()


@router.get("/{robot_id}/assets/{file_path:path}")
async def get_robot_asset(
    robot_id: int,
    file_path: str,
    db: AsyncSession = Depends(get_db),
):
    """获取机器人资产文件（3D 模型、manifest 等）。"""
    # verify robot exists
    result = await db.execute(select(RobotModel).where(RobotModel.id == robot_id))
    robot = result.scalar_one_or_none()
    if not robot:
        raise HTTPException(status_code=404, detail="机器人不存在")

    full_path = _storage.get_full_path(robot_model_id=robot_id, rel_path=file_path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    # Determine content type
    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
    content_types = {
        "glb": "model/gltf-binary",
        "gltf": "model/gltf+json",
        "json": "application/json",
        "png": "image/png",
        "jpg": "image/jpeg",
    }
    media_type = content_types.get(ext, "application/octet-stream")

    return FileResponse(full_path, media_type=media_type)
```

需要在文件顶部添加 `import os`。

- [ ] **Step 2: Run existing tests to ensure no regression**

Run: `cd r-mos-backend && pytest tests/test_api_robots.py tests/test_storage.py tests/test_models_robot.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add r-mos-backend/app/api/v1/endpoints/robots.py
git commit -m "feat: add robot asset file serving endpoint"
```

---

## Task 10: 前端 robots.ts 支持动态加载

**Files:**
- Modify: `r-mos-frontend/src/config/robots.ts`

- [ ] **Step 1: Update robots.ts to support API-driven robot catalog**

当前内容是硬编码 atom01，改为支持 API 动态获取，同时保持向后兼容（fallback 到硬编码）。

```typescript
// r-mos-frontend/src/config/robots.ts
export type RobotId = string;  // was "atom01" literal, now dynamic

const MODEL_BASE_URL = import.meta.env.VITE_MODEL_BASE_URL || "/models";
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

/** Static fallback catalog for backward compatibility. */
export const STATIC_ROBOT_CATALOG: Record<string, { label: string; basePath: string }> = {
  atom01: {
    label: "ATOM01",
    basePath: `${MODEL_BASE_URL}/robots/atom01`,
  },
};

/**
 * Get the base URL for loading a robot's 3D model assets.
 *
 * For migrated robots (with numeric IDs), serves from the API.
 * For legacy robots (atom01), falls back to static paths.
 */
export const getRobotModelBase = (robotId: RobotId): string => {
  // Legacy static path for atom01 (fallback during migration)
  if (STATIC_ROBOT_CATALOG[robotId]) {
    return STATIC_ROBOT_CATALOG[robotId].basePath;
  }
  // API-driven path for new robots
  return `${API_BASE_URL}/api/v1/robots/${robotId}/assets/models`;
};

/**
 * Get the URL for a robot's manifest file.
 */
export const getRobotManifestUrl = (robotId: RobotId, manifestName: string): string => {
  if (STATIC_ROBOT_CATALOG[robotId]) {
    return `${STATIC_ROBOT_CATALOG[robotId].basePath}/${manifestName}`;
  }
  return `${API_BASE_URL}/api/v1/robots/${robotId}/assets/manifests/${manifestName}`;
};
```

- [ ] **Step 2: Verify frontend builds**

Run: `cd r-mos-frontend && npx tsc --noEmit`
Expected: No type errors

- [ ] **Step 3: Commit**

```bash
git add r-mos-frontend/src/config/robots.ts
git commit -m "feat: update robots.ts to support API-driven robot catalog"
```

---

## Summary

| Task | 内容 | 产出 |
|------|------|------|
| 1 | RobotModel + TeacherRobotBinding ORM | 2 models, 3 tests |
| 2 | RobotAsset + AnalysisTask ORM | 2 models, 2 tests |
| 3 | 扩展现有模型 + 注册 | 3 files modified |
| 4 | Alembic 迁移 | 4 new tables, 3 new columns |
| 5 | FileStorageService | 1 service, 6 tests |
| 6 | Pydantic Schemas | 5 schemas |
| 7 | Robot CRUD API | 5 endpoints, 4 tests |
| 8 | atom01 迁移脚本 | 1 script |
| 9 | 资产文件 API | 1 endpoint |
| 10 | 前端 robots.ts 动态化 | 1 file updated |

**完成后的状态：**
- 4 张新表 + 3 个扩展字段就绪
- 文件存储服务可用
- 机器人 CRUD API 可用
- atom01 可通过脚本迁移为第一个 RobotModel
- 前端准备好从 API 加载机器人资产
- 项目准备好删除 1.6GB 硬编码模型文件
