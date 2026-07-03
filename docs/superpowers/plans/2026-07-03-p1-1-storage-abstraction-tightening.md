# P1-1 存储抽象收紧（T1-1a）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在纯本地存储下消灭 `FileStorageBase` 的全部本地路径语义泄漏，使 P1-2 的 S3 化只需"新增一个实现类"。

**Architecture:** 三步走——(1) 接口补齐 S3 可实现的原语（exists/open_stream/get_public_url/materialize/materialize_dir），路径穿越防护统一到所有方法；(2) 配置驱动工厂 `get_storage()` 收敛全仓 6 个 `LocalFileStorage()` 实例化点；(3) 逐调用点迁移（HTTP 资产下发→流式/重定向；分析管线→materialize 显式落地；两处 `Path("data/robot-assets")` 硬编码与一处 `storage.base_dir` 属性泄漏清除），最后从 ABC 删除 `get_full_path`。

**Tech Stack:** FastAPI（StreamingResponse/RedirectResponse）、contextlib.contextmanager、pytest + tmp_path

## Global Constraints

- 现有测试网全绿：基线 **699 passed / 3 skipped**（裸 `pytest`，P0-4 后），任何任务后 0 failed、skip 不增
- `validate_robot_assets(robot_model_id: int, storage: FileStorageBase) -> list[str]` 签名与行为不变（其内部只用 download/list_files，本计划不触碰）
- 接口保持**同步**（决策记录：避免 async 大面积传染；S3 实现在 P1-2 内部用 `anyio.to_thread` 包阻塞 IO）
- 资产 URL 对前端不变：`GET /api/v1/robots/{id}/assets/{path}`（Three.js GLTFLoader 直接 fetch、无认证头，本地实现继续 200 响应体返回；重定向仅在 get_public_url 非 None 时启用）
- 完成判据（来自总控计划）：`grep -rn 'Path("data/robot-assets")' app/` 零命中；HTTP 层不再获得本地路径；`get_full_path` 从公共 ABC 消失
- 每个 commit 尾部：`Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` + `Claude-Session: https://claude.ai/code/session_017NYSjrARdtgRbQxW5TCv7N`；不 push（控制器统一推送）
- 所有命令在 `r-mos-backend/` 下、venv 激活后执行

## 已勘察的泄漏全景（执行前置知识）

| 泄漏点 | 位置 | 迁移目标 |
|--------|------|---------|
| `FileResponse(get_full_path(...))` | `app/api/v1/endpoints/robots.py:532-548` | get_public_url 重定向 或 open_stream 流式 |
| `Path("data/robot-assets")` 硬编码 ×2 | `robots.py:480`（get_robot_tools）、`app/services/training/workbench_draft_generator.py:72` | storage.download |
| `get_full_path` 分析管线 ×4 处 | `pdf_extractor.py:54`、`cad_converter.py:149,172`、`manifest_generator.py:96` | materialize / download |
| `storage.base_dir` 属性泄漏 | `app/services/analysis/assembly_builder.py:28`（+direct 写 models_dir） | materialize_dir + upload |
| `LocalFileStorage()` 模块级/构造器实例化 ×6 | robots.py:32、worker.py:16、cad_converter.py:54、pdf_extractor.py:26、manifest_generator.py:20、assembly_builder.py:22 | 工厂 get_storage() |
| 穿越防护只在 get_full_path | `file_storage.py:84-89`（download/delete/list_files 无防护） | 统一 `_resolve()` |

---

### Task 1: 接口扩展 + LocalFileStorage 新原语 + 穿越防护统一

**Files:**
- Modify: `app/services/storage/file_storage.py`
- Test: `tests/test_storage.py`（追加）

**Interfaces:**
- Consumes: 无（本任务是地基）
- Produces（后续所有任务依赖，签名逐字使用）:
  - `exists(self, robot_model_id: int, rel_path: str) -> bool`
  - `open_stream(self, robot_model_id: int, rel_path: str) -> BinaryIO`（文件不存在抛 `FileNotFoundError`，穿越抛 `ValueError`）
  - `get_public_url(self, robot_model_id: int, rel_path: str) -> Optional[str]`（本地实现恒返回 `None`）
  - `materialize(self, robot_model_id: int, rel_path: str) -> AbstractContextManager[Path]`（yield 本地可读 `Path`；不存在抛 `FileNotFoundError`）
  - `materialize_dir(self, robot_model_id: int) -> AbstractContextManager[Path]`（yield 机器人全目录本地 `Path`，目录不存在则创建）
  - `download/delete` 行为不变但获得穿越防护（`ValueError`）

- [ ] **Step 1: 写失败测试（追加到 tests/test_storage.py 末尾）**

```python
# --- P1-1 新原语测试 ---

def test_exists_true_and_false(storage, tmp_path):
    (tmp_path / "42" / "models").mkdir(parents=True)
    (tmp_path / "42" / "models" / "a.glb").write_bytes(b"a")
    assert storage.exists(robot_model_id=42, rel_path="models/a.glb") is True
    assert storage.exists(robot_model_id=42, rel_path="models/missing.glb") is False


def test_open_stream_reads_content(storage, tmp_path):
    (tmp_path / "42" / "models").mkdir(parents=True)
    (tmp_path / "42" / "models" / "s.glb").write_bytes(b"stream-bytes")
    stream = storage.open_stream(robot_model_id=42, rel_path="models/s.glb")
    try:
        assert stream.read() == b"stream-bytes"
    finally:
        stream.close()


def test_open_stream_missing_raises(storage):
    with pytest.raises(FileNotFoundError):
        storage.open_stream(robot_model_id=42, rel_path="models/none.glb")


def test_get_public_url_is_none_for_local(storage):
    assert storage.get_public_url(robot_model_id=42, rel_path="models/a.glb") is None


def test_materialize_yields_readable_path(storage, tmp_path):
    (tmp_path / "42" / "docs").mkdir(parents=True)
    (tmp_path / "42" / "docs" / "m.pdf").write_bytes(b"pdf-bytes")
    with storage.materialize(robot_model_id=42, rel_path="docs/m.pdf") as p:
        assert p.read_bytes() == b"pdf-bytes"


def test_materialize_missing_raises(storage):
    with pytest.raises(FileNotFoundError):
        with storage.materialize(robot_model_id=42, rel_path="docs/none.pdf"):
            pass


def test_materialize_dir_yields_robot_dir(storage, tmp_path):
    (tmp_path / "42" / "uploads").mkdir(parents=True)
    (tmp_path / "42" / "uploads" / "r.urdf").write_bytes(b"<robot/>")
    with storage.materialize_dir(robot_model_id=42) as d:
        assert (d / "uploads" / "r.urdf").exists()


def test_materialize_dir_creates_when_missing(storage):
    with storage.materialize_dir(robot_model_id=77) as d:
        assert d.is_dir()


@pytest.mark.parametrize("method,args", [
    ("download", ("../evil",)),
    ("delete", ("../evil",)),
    ("exists", ("../evil",)),
    ("open_stream", ("../evil",)),
])
def test_path_traversal_blocked_everywhere(storage, method, args):
    with pytest.raises(ValueError):
        getattr(storage, method)(42, *args)


def test_materialize_traversal_blocked(storage):
    with pytest.raises(ValueError):
        with storage.materialize(42, "../evil"):
            pass
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_storage.py -v`
Expected: 新增用例 FAIL（`AttributeError: ... has no attribute 'exists'` 等）；原有 7 个用例 PASS

- [ ] **Step 3: 实现（整文件替换 app/services/storage/file_storage.py）**

```python
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
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/test_storage.py -v`
Expected: 全部 PASS（原 7 + 新 12 = 19）

- [ ] **Step 5: 全量回归（防 download/delete 新增防护破坏既有调用）**

Run: `pytest -q`
Expected: ≥699 passed / 3 skipped / 0 failed。若有测试因穿越防护变红：检查该调用传入的 rel_path 是否真的合法（带 `robot_model_id/` 前缀的老格式路径会被 `_resolve` 判为合法子路径，不受影响；真穿越才抛）。

- [ ] **Step 6: Commit**

```bash
git add app/services/storage/file_storage.py tests/test_storage.py
git commit -m "feat(storage): 接口补齐 S3 可实现原语，穿越防护统一到全部方法"
```

### Task 2: 配置驱动工厂 get_storage() + 全仓 6 实例化点收敛

**Files:**
- Modify: `app/core/config.py`（Settings 加 2 字段）
- Modify: `app/services/storage/__init__.py`
- Modify: `app/api/v1/endpoints/robots.py:32`、`app/services/analysis/worker.py:16`、`app/services/analysis/cad_converter.py:54`、`app/services/analysis/pdf_extractor.py:26`、`app/services/analysis/manifest_generator.py:20`、`app/services/analysis/assembly_builder.py:22`
- Test: `tests/test_storage.py`（追加）

**Interfaces:**
- Consumes: Task 1 的 `FileStorageBase` / `LocalFileStorage`
- Produces: `get_storage() -> FileStorageBase`（进程内单例，`get_storage.cache_clear()` 可重置——测试用）

- [ ] **Step 1: 写失败测试（追加到 tests/test_storage.py）**

```python
# --- 工厂测试 ---
from app.services.storage import get_storage


def test_get_storage_returns_singleton_local():
    get_storage.cache_clear()
    s1 = get_storage()
    s2 = get_storage()
    assert isinstance(s1, LocalFileStorage)
    assert s1 is s2
    get_storage.cache_clear()


def test_get_storage_unknown_backend_raises(monkeypatch):
    from app.core.config import settings
    get_storage.cache_clear()
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "gcs")
    with pytest.raises(ValueError, match="gcs"):
        get_storage()
    get_storage.cache_clear()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_storage.py -v -k get_storage`
Expected: FAIL — `ImportError: cannot import name 'get_storage'`

- [ ] **Step 3: 实现配置与工厂**

`app/core/config.py` 在 `ROBOT_MODE` 字段后追加：

```python
    # 存储后端配置
    STORAGE_BACKEND: str = "local"  # local / s3（P1-2 实现）
    STORAGE_BASE_DIR: str = "data/robot-assets"
```

`app/services/storage/__init__.py` 整文件替换：

```python
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
```

- [ ] **Step 4: 跑工厂测试确认通过**

Run: `pytest tests/test_storage.py -v -k get_storage`
Expected: 2 passed

- [ ] **Step 5: 收敛 6 个实例化点（逐处替换，import 一并调整）**

`app/api/v1/endpoints/robots.py`（第 10 行 import、第 32 行）：

```python
from app.services.storage import get_storage
```
```python
_storage = get_storage()
```

`app/services/analysis/worker.py`（import 与第 16 行同理）：

```python
from app.services.storage import get_storage
```
```python
_storage = get_storage()
```

`app/services/analysis/cad_converter.py`、`pdf_extractor.py`、`manifest_generator.py`、`assembly_builder.py` 四个构造器（import 改为 `from app.services.storage import get_storage`，原 `from app.services.storage.file_storage import LocalFileStorage` 删除）：

```python
        self.storage = get_storage()
```

注意：monkeypatch `robots_ep._storage`（P0-4 的两个测试）与既有 mock 均不受影响（模块级变量名不变）。

- [ ] **Step 6: 全仓断言收敛完成 + 全量回归**

Run: `grep -rn "LocalFileStorage(" app/ | grep -v file_storage.py; pytest -q`
Expected: grep 零输出；≥701 passed / 3 skipped / 0 failed

- [ ] **Step 7: Commit**

```bash
git add app/core/config.py app/services/storage/__init__.py app/api/v1/endpoints/robots.py app/services/analysis/ tests/test_storage.py
git commit -m "feat(storage): 配置驱动工厂 get_storage()，全仓 6 实例化点收敛"
```

### Task 3: 资产下发端点迁移（FileResponse → 重定向/流式；tools 端点走抽象）

**Files:**
- Modify: `app/api/v1/endpoints/robots.py`（`get_robot_asset` 515-548、`get_robot_tools` 471-485）
- Test: `tests/unit/test_robot_asset_serving.py`（新建）

**Interfaces:**
- Consumes: Task 1 的 `open_stream/get_public_url/download`；Task 2 的 `_storage = get_storage()`
- Produces: 无（对外 HTTP 契约不变）

- [ ] **Step 1: 写失败测试（新建 tests/unit/test_robot_asset_serving.py）**

```python
"""P1-1 Task 3：资产下发端点不再依赖本地路径语义。"""
import json

import pytest
from fastapi import HTTPException

from app.models.robot_model import RobotModel, RobotStatus, RobotVisibility
from app.services.storage.file_storage import LocalFileStorage


@pytest.fixture
def local_storage(tmp_path):
    return LocalFileStorage(base_dir=str(tmp_path))


async def _make_robot(test_db) -> RobotModel:
    robot = RobotModel(
        brand="T", model_name="ServeBot", owner_teacher_id=1,
        visibility=RobotVisibility.PRIVATE, status=RobotStatus.DRAFT,
    )
    test_db.add(robot)
    await test_db.commit()
    await test_db.refresh(robot)
    return robot


@pytest.mark.asyncio
async def test_asset_served_as_streaming_response(test_db, local_storage, monkeypatch):
    from app.api.v1.endpoints import robots as robots_ep
    from starlette.responses import StreamingResponse

    monkeypatch.setattr(robots_ep, "_storage", local_storage)
    robot = await _make_robot(test_db)
    local_storage.upload(robot.id, "part.glb", b"glb-binary", subdirectory="models")

    resp = await robots_ep.get_robot_asset(robot.id, "models/part.glb", db=test_db)
    assert isinstance(resp, StreamingResponse)
    assert resp.media_type == "model/gltf-binary"


@pytest.mark.asyncio
async def test_asset_missing_returns_404(test_db, local_storage, monkeypatch):
    from app.api.v1.endpoints import robots as robots_ep

    monkeypatch.setattr(robots_ep, "_storage", local_storage)
    robot = await _make_robot(test_db)
    with pytest.raises(HTTPException) as exc:
        await robots_ep.get_robot_asset(robot.id, "models/none.glb", db=test_db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_asset_traversal_returns_400(test_db, local_storage, monkeypatch):
    from app.api.v1.endpoints import robots as robots_ep

    monkeypatch.setattr(robots_ep, "_storage", local_storage)
    robot = await _make_robot(test_db)
    with pytest.raises(HTTPException) as exc:
        await robots_ep.get_robot_asset(robot.id, "../../etc/passwd", db=test_db)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_asset_redirects_when_public_url_available(test_db, local_storage, monkeypatch):
    from app.api.v1.endpoints import robots as robots_ep
    from starlette.responses import RedirectResponse

    monkeypatch.setattr(robots_ep, "_storage", local_storage)
    monkeypatch.setattr(
        local_storage, "get_public_url", lambda robot_model_id, rel_path: "https://cdn.example/x.glb"
    )
    robot = await _make_robot(test_db)

    resp = await robots_ep.get_robot_asset(robot.id, "models/x.glb", db=test_db)
    assert isinstance(resp, RedirectResponse)
    assert resp.status_code == 307
    assert resp.headers["location"] == "https://cdn.example/x.glb"


@pytest.mark.asyncio
async def test_robot_tools_read_via_storage(test_db, local_storage, monkeypatch):
    from app.api.v1.endpoints import robots as robots_ep

    monkeypatch.setattr(robots_ep, "_storage", local_storage)
    robot = await _make_robot(test_db)
    manifest = {"tools": [{"id": "screwdriver_m3"}]}
    local_storage.upload(
        robot.id, "assembly_manifest.json",
        json.dumps(manifest).encode("utf-8"), subdirectory="manifests",
    )

    result = await robots_ep.get_robot_tools(robot.id, db=test_db)
    assert result["tools"] == [{"id": "screwdriver_m3"}]


@pytest.mark.asyncio
async def test_robot_tools_empty_when_no_manifest(test_db, local_storage, monkeypatch):
    from app.api.v1.endpoints import robots as robots_ep

    monkeypatch.setattr(robots_ep, "_storage", local_storage)
    robot = await _make_robot(test_db)
    result = await robots_ep.get_robot_tools(robot.id, db=test_db)
    assert result == {"robot_id": robot.id, "tools": []}
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/unit/test_robot_asset_serving.py -v`
Expected: streaming/redirect/tools 用例 FAIL（当前实现返回 FileResponse、读硬编码路径）；404/400 用例可能已过（行为兼容），属正常

- [ ] **Step 3: 迁移两个端点**

`robots.py` 顶部 import 区：删除 `import os`（若仅此处使用）与 `FileResponse` import，加：

```python
from fastapi.responses import RedirectResponse, StreamingResponse
```

`get_robot_tools`（原 471-485 行）函数体替换：

```python
    """获取机器人工具列表（从 assembly_manifest.json 中读取）。"""
    import json

    try:
        manifest = json.loads(
            _storage.download(robot_model_id=robot_id, rel_path="manifests/assembly_manifest.json")
        )
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        return {"robot_id": robot_id, "tools": []}
    return {"robot_id": robot_id, "tools": manifest.get("tools", [])}
```

`get_robot_asset`（原 526-548 行）机器人 404 检查之后替换：

```python
    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
    content_types = {
        "glb": "model/gltf-binary",
        "gltf": "model/gltf+json",
        "json": "application/json",
        "png": "image/png",
        "jpg": "image/jpeg",
    }
    media_type = content_types.get(ext, "application/octet-stream")

    try:
        public_url = _storage.get_public_url(robot_model_id=robot_id, rel_path=file_path)
        if public_url:
            return RedirectResponse(public_url, status_code=307)
        stream = _storage.open_stream(robot_model_id=robot_id, rel_path=file_path)
    except ValueError:
        raise HTTPException(status_code=400, detail="非法文件路径")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="文件不存在")

    return StreamingResponse(stream, media_type=media_type)
```

- [ ] **Step 4: 跑测试确认通过 + 全量回归**

Run: `pytest tests/unit/test_robot_asset_serving.py -v && pytest -q`
Expected: 6 passed；全量 ≥707 passed / 0 failed

- [ ] **Step 5: 手工冒烟（真实资产走新链路）**

后端起本地（8000 空闲时）：`python main.py &`，然后：

```bash
curl -sf -o /dev/null -w "%{http_code} %{content_type}\n" http://localhost:8000/api/v1/robots/1/assets/models/base_link.glb
curl -sf http://localhost:8000/api/v1/robots/1/tools | head -c 120; echo
kill %1
```
Expected: `200 model/gltf-binary`；tools 返回 JSON（robot 1 是资产完整的 ATOM-01）

- [ ] **Step 6: Commit**

```bash
git add app/api/v1/endpoints/robots.py tests/unit/test_robot_asset_serving.py
git commit -m "refactor(storage): 资产下发走流式/重定向，tools 端点走存储抽象"
```

### Task 4: workbench_draft_generator 迁移

**Files:**
- Modify: `app/services/training/workbench_draft_generator.py:67-86`（`_load_robot_manifest`）
- Test: `tests/unit/test_workbench_manifest_loading.py`（新建）

**Interfaces:**
- Consumes: Task 1 `download`；Task 2 `get_storage()`

- [ ] **Step 1: 写失败测试（新建 tests/unit/test_workbench_manifest_loading.py）**

```python
"""P1-1 Task 4：workbench 草稿生成器的 manifest 读取走存储抽象。"""
import json

from app.services.storage.file_storage import LocalFileStorage
from app.services.training.workbench_draft_generator import WorkbenchDraftGenerator


def _manifest_bytes() -> bytes:
    return json.dumps({
        "nodes": [
            {"link_name": "torso_link", "mesh_id": "torso_mesh"},
            {"link_name": "no_mesh_link"},
        ],
        "display_names": {"torso_link": "躯干"},
    }).encode("utf-8")


def test_load_robot_manifest_via_storage(tmp_path, monkeypatch):
    import app.services.training.workbench_draft_generator as wdg

    local = LocalFileStorage(base_dir=str(tmp_path))
    local.upload(5, "assembly_manifest.json", _manifest_bytes(), subdirectory="manifests")
    monkeypatch.setattr(wdg, "get_storage", lambda: local)

    link_names, display_names = WorkbenchDraftGenerator._load_robot_manifest(5)
    assert link_names == ["torso_link"]
    assert display_names == {"torso_link": "躯干"}


def test_load_robot_manifest_missing_returns_empty(tmp_path, monkeypatch):
    import app.services.training.workbench_draft_generator as wdg

    local = LocalFileStorage(base_dir=str(tmp_path))
    monkeypatch.setattr(wdg, "get_storage", lambda: local)

    assert WorkbenchDraftGenerator._load_robot_manifest(999) == ([], {})


def test_load_robot_manifest_none_id_returns_empty():
    assert WorkbenchDraftGenerator._load_robot_manifest(None) == ([], {})
```

（若 `WorkbenchDraftGenerator` 类名不同，以 `workbench_draft_generator.py` 中包含 `_load_robot_manifest` 的实际类名为准，测试同步调整。）

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/unit/test_workbench_manifest_loading.py -v`
Expected: FAIL — `wdg` 模块无 `get_storage` 属性（monkeypatch 报 AttributeError），或走硬编码路径读不到 tmp_path 数据

- [ ] **Step 3: 迁移实现**

`workbench_draft_generator.py`：顶部加 `from app.services.storage import get_storage`（若 `Path` 仅此方法使用则删其 import），`_load_robot_manifest` 方法体替换：

```python
    @staticmethod
    def _load_robot_manifest(robot_id: int | None) -> tuple[list[str], dict[str, str]]:
        """从 assembly_manifest.json 加载 link 名称和 display_names。"""
        if not robot_id:
            return [], {}
        try:
            data = json.loads(
                get_storage().download(robot_model_id=robot_id, rel_path="manifests/assembly_manifest.json")
            )
        except (FileNotFoundError, ValueError, json.JSONDecodeError, KeyError):
            return [], {}
        nodes = data.get("nodes", [])
        link_names = [
            n["link_name"] for n in nodes
            if n.get("link_name") and n.get("mesh_id")
        ]
        display_names = data.get("display_names", {})
        return link_names, display_names
```

- [ ] **Step 4: 跑测试确认通过 + 相关既有测试**

Run: `pytest tests/unit/test_workbench_manifest_loading.py tests/unit/test_training_workbench_draft_api.py -v`
Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/training/workbench_draft_generator.py tests/unit/test_workbench_manifest_loading.py
git commit -m "refactor(storage): workbench manifest 读取走存储抽象"
```

### Task 5: 分析管线迁移（materialize / materialize_dir）

**Files:**
- Modify: `app/services/analysis/pdf_extractor.py:50-56`
- Modify: `app/services/analysis/cad_converter.py:146-180`
- Modify: `app/services/analysis/manifest_generator.py:94-99`
- Modify: `app/services/analysis/assembly_builder.py:25-101`
- Test: `tests/unit/test_pdf_extractor.py`、`tests/unit/test_cad_converter.py`、`tests/unit/test_manifest_generator.py`、`tests/services/analysis/test_assembly_builder.py`（既有测试保持绿；assembly_builder 私有方法签名变化处同步更新）

**Interfaces:**
- Consumes: Task 1 `materialize/materialize_dir/download/exists/upload`；Task 2 `get_storage()`

- [ ] **Step 1: pdf_extractor 迁移（54-56 行区域）**

```python
                rel = asset.file_path.split("/", 1)[-1]
                with self.storage.materialize(asset.robot_model_id, rel) as local_path:
                    chunks = self._extract_text_from_pdf(str(local_path))
```

注意：原代码把"路径解析"与"提取"分成两个 try——合并后异常处理保持两类日志语义（`FileNotFoundError/ValueError` → "路径解析失败" warning + continue；其他异常 → "PDF 提取失败" warning + continue）。实现示例：

```python
        for asset in pdf_assets:
            rel = asset.file_path.split("/", 1)[-1]
            try:
                with self.storage.materialize(asset.robot_model_id, rel) as local_path:
                    chunks = self._extract_text_from_pdf(str(local_path))
            except (FileNotFoundError, ValueError) as exc:
                logger.warning("跳过资产 %s，路径解析失败：%s", asset.file_path, exc)
                continue
            except Exception as exc:
                logger.warning("PDF 提取失败 %s：%s", asset.file_path, exc)
                continue
```

- [ ] **Step 2: cad_converter 迁移**

`_copy_glb_asset`（146-153 行）——直接用 download/upload，不再拿路径：

```python
    def _copy_glb_asset(self, asset: RobotAsset) -> dict:
        """将 GLB 文件复制到 models/ 子目录，返回新的存储信息。"""
        rel = asset.file_path.split("/", 1)[-1]  # "uploads/robot.glb"
        content = self.storage.download(asset.robot_model_id, rel)
        filename = rel.rsplit("/", 1)[-1]
        rel_path = self.storage.upload(asset.robot_model_id, filename, content, subdirectory="models")
        return {"file_path": rel_path, "file_size": len(content)}
```

`_convert_cad_to_glb`（168-180 行区域）——materialize 源文件（trimesh 需要真实路径）：

```python
        rel = asset.file_path.split("/", 1)[-1]
        try:
            with self.storage.materialize(asset.robot_model_id, rel) as src_path:
                return self._do_convert(asset, src_path)
        except FileNotFoundError:
            logger.error("源文件不存在: %s", asset.file_path)
            return None
        except ValueError as exc:
            logger.error("路径遍历检测: %s", exc)
            return None
```

其中 `_do_convert(asset, src_path)` 是把原方法 materialize 点之后的转换逻辑（trimesh 加载→导出 GLB bytes→`self.storage.upload(...)`）原样抽成的私有方法，签名 `def _do_convert(self, asset: RobotAsset, src_path: Path) -> Optional[dict]:`。转换输出若原实现是先写本地再读，改为 trimesh `export(file_type="glb")` 拿 bytes 直接 upload；若原实现已经 upload bytes 则保持。

- [ ] **Step 3: manifest_generator 迁移（94-99 行）**

```python
        rel = asset.file_path.split("/", 1)[-1]  # e.g. "models/robot.glb"
        with self.storage.materialize(asset.robot_model_id, rel) as full_path:
            loaded = trimesh.load(str(full_path))
        return self._build_node_tree(loaded)
```

- [ ] **Step 4: assembly_builder 迁移（消灭 base_dir 属性泄漏 + 输出走 upload）**

`process` 方法改造要点（完整替换 25-101 行区域的路径逻辑）：

```python
    async def process(self, task: AnalysisTask, db: AsyncSession) -> dict:
        robot_model_id = task.robot_model_id
        with self.storage.materialize_dir(robot_model_id) as robot_dir:
            return await self._process_in_dir(task, db, robot_model_id, robot_dir)

    async def _process_in_dir(
        self, task: AnalysisTask, db: AsyncSession, robot_model_id: int, robot_dir: Path
    ) -> dict:
        # 1. Find URDF —— 原逻辑不变，robot_dir 由 materialize_dir 提供
        urdf_files = self._find_urdf_files(str(robot_dir))
        ...
```

- `_find_urdf_files/_resolve_mesh_files` 签名不变（收 `str` 目录），仅数据来源变为 materialize_dir 的 yield。
- mesh 转换输出改为：转换到 `tempfile.TemporaryDirectory()` 下的 `{link.name}.glb`，成功后 `content = output_path.read_bytes()`，`rel_path = self.storage.upload(robot_model_id, f"{link.name}.glb", content, subdirectory="models")`（upload 返回值即入库的 `file_path`，不再手工拼 `f"{robot_model_id}/models/..."`）。
- "已存在跳过"判断 `output_glb.exists()` 改为 `self.storage.exists(robot_model_id, f"models/{link.name}.glb")`。
- manifest 上传（103-108 行）已走 `storage.upload`，不动。

- [ ] **Step 5: 跑分析管线相关测试 + 全量回归**

Run: `pytest tests/unit/test_pdf_extractor.py tests/unit/test_cad_converter.py tests/unit/test_manifest_generator.py tests/services/analysis/test_assembly_builder.py -v && pytest -q`
Expected: 相关测试全绿（assembly_builder 测试若引用私有方法签名，按新签名同步修改断言，行为语义不变）；全量 0 failed

- [ ] **Step 6: Commit**

```bash
git add app/services/analysis/ tests/
git commit -m "refactor(storage): 分析管线经 materialize/materialize_dir 显式落地，输出统一走 upload"
```

### Task 6: 删除 get_full_path + 零残留断言 + 文档回写

**Files:**
- Modify: `app/services/storage/file_storage.py`（删 `get_full_path`）
- Modify: `tests/test_storage.py`（删 `test_get_full_path`，改为断言接口不含该方法）
- Modify: `CLAUDE.md`（Key Technical Patterns 的 Storage 行）
- Modify: `docs/项目交接与升级路线图.md`（T1-1a 勾选）

**Interfaces:**
- Consumes: Task 3/4/5 已消灭全部调用点

- [ ] **Step 1: 断言无调用残留**

Run: `grep -rn "get_full_path" app/ tests/ --include="*.py" | grep -v "test_storage\|file_storage"`
Expected: 零输出。若有残留，先迁移该调用点（按 Task 3-5 同样手法）再继续。

- [ ] **Step 2: 删除方法与旧测试，加防回归断言**

`file_storage.py`：删除 `get_full_path` 方法（LocalFileStorage 末尾整段）。
`tests/test_storage.py`：删除 `test_get_full_path`，原位替换为：

```python
def test_get_full_path_removed_from_interface(storage):
    """P1-1 完成判据：本地路径不再从接口泄漏。"""
    assert not hasattr(FileStorageBase, "get_full_path")
    assert not hasattr(storage, "get_full_path")
```

（文件顶部 import 需含 `FileStorageBase`：`from app.services.storage.file_storage import FileStorageBase, LocalFileStorage`。）

- [ ] **Step 3: 完成判据三连 + 全量回归**

```bash
grep -rn 'Path("data/robot-assets")' app/ --include="*.py"; \
grep -rn "get_full_path" app/ --include="*.py"; \
grep -rn "\.base_dir" app/ --include="*.py" | grep -v file_storage.py; \
pytest -q
```
Expected: 三个 grep 全部零输出；全量 0 failed、skip 不增

- [ ] **Step 4: 文档回写**

`CLAUDE.md` Key Technical Patterns 中 Storage 行替换为：

```markdown
- **Storage**: `FileStorageBase` ABC → 工厂 `get_storage()`（配置 `STORAGE_BACKEND`，全仓唯一实例化入口）。本地路径零泄漏：HTTP 下发走 `open_stream`/`get_public_url`，分析管线走 `materialize`/`materialize_dir`，穿越防护统一在 `_resolve`。S3 实现见 P1-2。
```

`docs/项目交接与升级路线图.md` T1-1a 小节标题追加 `✅ 完成（日期）`，验收行追加 ✅。

- [ ] **Step 5: Commit**

```bash
git add app/services/storage/file_storage.py tests/test_storage.py CLAUDE.md "docs/项目交接与升级路线图.md"
git commit -m "refactor(storage): 移除 get_full_path，本地路径零泄漏(T1-1a 完成)"
```

---

## Self-Review 记录

1. **Spec 覆盖**：总控计划 T1-1a 四条设计决策——流式/重定向（Task 3）、materialize（Task 5）、两处硬编码清理（Task 3 的 tools + Task 4）、工厂收敛（Task 2，含终审移交备注要求的 worker.py 第 6 实例）——全部有对应任务；终审移交的 download/delete 穿越防护缺口在 Task 1；勘察新发现的 `base_dir` 属性泄漏在 Task 5 Step 4。验收判据在 Task 6 Step 3 以 grep 三连固化。
2. **占位符扫描**：Task 5 assembly_builder 采用"改造要点+关键代码"而非整文件替换（原文件 175 行、diff 面大，整贴反而增加转录错误风险）；要点中每处变更都给了精确签名与代码，非占位。其余任务代码完整。
3. **类型一致性**：`get_storage()` 签名在 Task 2 定义、Task 3/4/5 消费一致；`materialize` yield `Path`（Task 5 各处以 `str(local_path)` 传给需要 str 的下游）；测试中 `monkeypatch.setattr(wdg, "get_storage", ...)` 与实现的模块级 import 方式匹配（`from ... import get_storage` 使名字绑定在模块命名空间，可被 monkeypatch）。
