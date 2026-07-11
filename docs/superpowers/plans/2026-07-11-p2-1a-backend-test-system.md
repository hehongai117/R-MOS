# P2-1a 后端测试体系升级 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把后端测试网从"全绿"升级到"可承诺"：测试分类可辨（特征 vs 规格）、8 个历史 P0 bug 有命名回归集、e2e 可跑真 Postgres（消除方言盲区）、存量发布数据经过资产审计、一路积累的测试欠账清零。

**Architecture:** 五个独立小任务：(1) marker 分类 + CI alembic check 门禁；(2) `tests/regression/` P0 回归集（走真实 HTTP 端点）；(3) e2e conftest 双后端化（`TEST_DATABASE_URL` 环境变量切 PG，NullPool 规避 asyncpg 跨事件循环）+ CI 独立 e2e-on-PG 步骤；(4) 存量 READY 机器人资产审计脚本 + 本地实跑；(5) 六笔测试欠账清理包。

**Tech Stack:** pytest markers、FastAPI TestClient、asyncpg + NullPool、moto、trimesh

## Global Constraints

- 基线：**772 passed / 3 skipped**（裸 pytest，P1-2 后）；每任务后 0 failed；**skip 不增**（Task 5 先 `pip install -r requirements.txt` 补齐本地 venv 缺失的 trimesh，避免 importorskip 增 skip）
- 已知历史障碍（勿踩）：**全量套件在 PG env 下 asyncpg 跨事件循环 Linux 必现**（P0-2 教训，记录于 backend-ci.yml 注释）——本计划只迁 e2e 目录且用 per-test engine + NullPool，不动全量套件的运行方式
- e2e 本地默认行为不变（无 `TEST_DATABASE_URL` 时仍是内存 SQLite）；资产/HTTP 契约零改动；本计划**不改产品代码**（例外：Task 5d 给 `list_files` 补子目录校验——P1-2 终审 Minor C 明确授权）
- 每 commit 尾部：`Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` + `Claude-Session: https://claude.ai/code/session_017NYSjrARdtgRbQxW5TCv7N`；不 push（控制器统一推送）
- 命令在 `r-mos-backend/` 下、venv 激活后执行

## 已勘察事实（执行前置知识）

- 特征测试仅 3 个文件：`tests/unit/test_training_characterization.py`、`test_teaching_characterization.py`、`test_agent_characterization.py`
- `pytest.ini` 已有 `markers = e2e: ...`；`addopts = -q`
- e2e conftest（47 行）：per-test 内存 SQLite + StaticPool + `asyncio.run` 初始化 + School 种子 + TestClient
- CI（backend-ci.yml）：PG16 服务 + `alembic upgrade head`（rmos_ci）→ PG 门禁步 → 两个裸跑套件步；ubuntu-latest 自带 psql 客户端
- 8 个 P0 bug 清单在 `docs/2026-07-02-full-test-plan.md` §"P0"表（端点/现象/根因），修复时已把对应特征测试断言改为正确行为
- 本地 venv 缺 trimesh（requirements.txt 有 `trimesh>=4.0.0` 但未安装）；CI 每次装 requirements 故有

---

### Task 1: 测试分类 marker + CI alembic check 门禁

**Files:**
- Modify: `pytest.ini`（markers 区）
- Modify: `tests/unit/test_training_characterization.py`、`tests/unit/test_teaching_characterization.py`、`tests/unit/test_agent_characterization.py`（各加一行 pytestmark）
- Modify: `.github/workflows/backend-ci.yml`（alembic 步骤后加 check）

**Interfaces:**
- Produces: marker `characterization`（锁现状的特征测试）、`regression`（Task 2 消费）

- [ ] **Step 1: pytest.ini 注册 markers**

`markers =` 区追加两行：

```ini
    characterization: 特征测试(锁定现状行为,重构安全网;修 bug 时按新规格更新断言)
    regression: 已修复 bug 的回归测试(断言正确行为,永不放松)
```

- [ ] **Step 2: 三个特征测试文件标注**

每个文件 import 区之后加（若已有其他 pytestmark 则合并为列表）：

```python
pytestmark = pytest.mark.characterization
```

- [ ] **Step 3: 验证分类可筛选**

```bash
pytest -m characterization --collect-only -q 2>/dev/null | tail -2
pytest -m "not characterization" --collect-only -q 2>/dev/null | tail -2
```
Expected: characterization 收集数 >0（三文件用例总和）；两者相加等于全量收集数；无 unknown marker 警告

- [ ] **Step 4: CI 加 alembic check（schema 与迁移链漂移的持久化门禁）**

`.github/workflows/backend-ci.yml` 的 `Alembic upgrade head (PostgreSQL)` 步骤 run 改为：

```yaml
        run: |
          alembic upgrade head
          alembic check
```

（P0 时已验证当前链干净——alembic check 输出 "No new upgrade operations detected"；此后任何"改了 ORM 忘写迁移"在 CI 立刻红。）

- [ ] **Step 5: 全量回归 + Commit**

Run: `pytest -q`（预期 772 passed / 3 skipped）

```bash
git add pytest.ini tests/unit/test_*_characterization.py .github/workflows/backend-ci.yml
git commit -m "test: 特征/回归测试 marker 分类 + CI alembic check 门禁"
```

### Task 2: tests/regression/ — 8 个历史 P0 bug 回归集

**Files:**
- Create: `tests/regression/__init__.py`（空文件）
- Create: `tests/regression/test_p0_bugs_2026_07.py`

**Interfaces:**
- Consumes: Task 1 的 `regression` marker；`tests/e2e/conftest.py` 的 `e2e_env` fixture（TestClient + session_factory）与 `tests/e2e/helpers.py` 的登录/建数据工具

**设计约定：** 回归测试走**真实 HTTP 端点**（e2e_env），每个测试 docstring 注明 bug 编号与根因；断言"正确行为"（修复后的行为），与特征测试独立——特征测试将来重构/重写都不影响回归集。conftest 共享：`tests/regression/conftest.py` 不新建，直接 `from tests.e2e.conftest import *` 不可行（fixture 发现机制）——改为在测试文件顶部 `pytest_plugins` 或最简单：新建 `tests/regression/conftest.py` 一行导入。

- [ ] **Step 1: 建 conftest 桥接**

```python
# tests/regression/conftest.py
"""复用 e2e 环境 fixture（真实 HTTP 端点是回归断言的锚点）。"""
from tests.e2e.conftest import e2e_env  # noqa: F401
```

- [ ] **Step 2: 写回归测试（完整框架 + 两个全码示例 + 六个规格）**

文件框架与两个完整示例：

```python
# tests/regression/test_p0_bugs_2026_07.py
"""2026-07 全量测试规划暴露的 8 个 P0 真实 bug 的回归集。

来源：docs/2026-07-02-full-test-plan.md §P0 表。
每个测试断言修复后的正确行为；这些断言永不放松（regression marker）。
夹具构造参照对应特征测试（test_agent/training/teaching_characterization.py）
与 tests/e2e/helpers.py。
"""
import pytest

from tests.e2e import helpers

pytestmark = pytest.mark.regression


def test_p0_1_policy_evaluate_returns_200_not_500(e2e_env):
    """Bug#1: POST /agent/v2/policy/evaluate 曾因 dataclass 调 .model_dump() 而 500。"""
    client, session_factory = e2e_env
    token = helpers.login_as_teacher(client, session_factory)
    resp = client.post(
        "/api/v1/agent/v2/policy/evaluate",
        json={"intent": "diagnose", "target": "knee_right", "context": {}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert "decision" in resp.json()


def test_p0_2_evaluation_report_invalid_task_returns_4xx_not_500(e2e_env):
    """Bug#2: POST /agent/evaluation/report 对无效 task_id 曾 500（ValueError 未捕获）。"""
    client, session_factory = e2e_env
    token = helpers.login_as_teacher(client, session_factory)
    resp = client.post(
        "/api/v1/agent/evaluation/report",
        json={"task_id": 999999},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (400, 404, 422), resp.text  # 明确的客户端错误,绝不是 500
```

其余六个按同一模式实现，规格如下（端点与断言为硬要求；请求体/夹具从对应特征测试搬——它们修复时已断言正确行为，搬其构造即可）：

| 测试名 | 端点 | 必须断言的正确行为 | 夹具来源 |
|--------|------|-------------------|---------|
| `test_p0_3_sop_quality_full_scan_no_500` | `POST /api/v1/agent/sop/quality/check`（全扫模式） | ≠500；返回结构含扫描结果 | test_agent_characterization |
| `test_p0_4_approval_history_returns_records` | `GET /api/v1/agent/approval/history` | 建 1 条审批后查询**非空**（曾恒空：参数错位） | test_agent_characterization |
| `test_p0_5_agent_execute_command_mode_succeeds` | `POST /api/v1/agent/execute`（command 模式） | 非 error 结果（曾恒 error：Command kwarg 用错） | test_agent_characterization |
| `test_p0_6_workbench_draft_bad_json_returns_400` | training workbench draft 端点 | 坏 JSON → 400（曾因 except 顺序死代码） | test_training_characterization |
| `test_p0_7_diagnosis_null_task_id_no_500` | `GET /api/v1/teaching/attempts/{id}/diagnosis`（attempt 无 task_id） | ≠500，结构化错误或降级响应 | test_teaching_characterization |
| `test_p0_8_not_found_error_type_is_resource_not_found` | 任一 teaching 404 路径 | 响应体 `error_type` 为资源未找到类型，**不是** `'HTTPException'` | test_teaching_characterization |

若某端点路径/请求体与表格假设不符，以对应特征测试中的实际调用为准，并在报告登记差异。helpers 中若无 `login_as_teacher` 等函数，用 helpers 里实际存在的登录/建用户函数替代（打开 tests/e2e/helpers.py 核对后使用，报告登记实际函数名）。

- [ ] **Step 3: 跑回归集确认全绿**

Run: `pytest tests/regression/ -v`
Expected: 8 passed（这些 bug 已修复，回归集首跑即绿——红的话说明夹具/路径构造错了或 bug 复发，逐个排查）

- [ ] **Step 4: 全量回归 + Commit**

Run: `pytest -q`（预期 780 passed / 3 skipped）

```bash
git add tests/regression/
git commit -m "test: 8 个历史 P0 bug 回归集(真实 HTTP 端点,regression marker)"
```

### Task 3: e2e conftest 双后端化 + CI e2e-on-PG 步骤

**Files:**
- Modify: `tests/e2e/conftest.py`（engine 构造改为环境驱动）
- Modify: `.github/workflows/backend-ci.yml`（新步骤）

**Interfaces:**
- Produces: 环境变量 `TEST_DATABASE_URL`——未设=内存 SQLite（本地默认，行为不变）；设为 PG URL=真 Postgres（CI/本地可选）

- [ ] **Step 1: conftest 改造（engine 构造与清理替换）**

`tests/e2e/conftest.py` 整文件替换：

```python
from __future__ import annotations

import asyncio
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, StaticPool

import app.models as app_models  # noqa: F401  # ensure metadata loaded
from app.core.database import get_db
from app.models.base import Base
from app.models.school import School
from main import app
from tests.e2e.helpers import E2E_SCHOOL_NAME


def _make_engine():
    """默认内存 SQLite；TEST_DATABASE_URL 设为 PG 时跑真 Postgres。

    PG 分支用 NullPool：每个 asyncio.run 是新事件循环，asyncpg 连接绑定
    事件循环，连接池跨循环复用会炸 "Event loop is closed"（P0-2 已知障碍）。
    NullPool 每次新建连接，彻底规避。
    """
    url = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    if url.startswith("sqlite"):
        return create_async_engine(
            url, connect_args={"check_same_thread": False}, poolclass=StaticPool
        ), False
    return create_async_engine(url, poolclass=NullPool), True


@pytest.fixture()
def e2e_env() -> tuple[TestClient, async_sessionmaker[AsyncSession]]:
    """Per-test isolated app+DB environment for E2E API tests."""
    engine, is_pg = _make_engine()

    async def _init_models() -> None:
        async with engine.begin() as conn:
            if is_pg:
                # PG 库跨测试持久，先清干净再建，保证每测试隔离
                await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(School.__table__.insert().values(name=E2E_SCHOOL_NAME))

    asyncio.run(_init_models())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    app.state.test_sessionmaker = session_factory

    with TestClient(app) as client:
        yield client, session_factory

    app.dependency_overrides.clear()
    app.state.test_sessionmaker = None

    async def _teardown() -> None:
        if is_pg:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    asyncio.run(_teardown())
```

- [ ] **Step 2: 本地双后端验证**

```bash
# 默认路径（SQLite）——行为不变
pytest tests/e2e/ -q
# PG 路径——临时库
createdb rmos_e2e_local
TEST_DATABASE_URL="postgresql+asyncpg://$(whoami)@localhost:5432/rmos_e2e_local" pytest tests/e2e/ -q
dropdb rmos_e2e_local
```
Expected: 两轮都 0 failed（e2e 共 29 个）。**PG 轮如出现方言差异导致的失败：这正是本任务要暴露的 bug——按"以当前最新状态为准"原则修产品代码/测试数据（不是改回 SQLite），逐个修复并在报告详述。**

- [ ] **Step 3: CI 新步骤（放在 "Postgres DB gate tests" 之后、套件步之前）**

```yaml
      # e2e 在真 Postgres 上跑（消除 SQLite 方言盲区）。独立数据库避免
      # 污染 rmos_ci（alembic/门禁在用）；per-test drop/create_all 自隔离。
      - name: E2E on Postgres
        env:
          TEST_DATABASE_URL: postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/rmos_e2e
          DEBUG: "true"
        run: |
          PGPASSWORD=postgres psql -h 127.0.0.1 -U postgres -c "CREATE DATABASE rmos_e2e" || true
          pytest tests/e2e/ -q
```

- [ ] **Step 4: 全量回归 + Commit**

Run: `pytest -q`（默认 SQLite 路径，772+8=780 passed / 3 skipped 不变）

```bash
git add tests/e2e/conftest.py .github/workflows/backend-ci.yml
git commit -m "test(e2e): TEST_DATABASE_URL 双后端化(NullPool 规避跨循环)+CI e2e-on-PG 步骤"
```

### Task 4: 存量 READY 机器人资产审计脚本 + 实跑

**Files:**
- Create: `scripts/audit_published_assets.py`

**Interfaces:**
- Consumes: `validate_robot_assets(robot_model_id, storage)`、`get_storage()`

- [ ] **Step 1: 写审计脚本**

```python
# scripts/audit_published_assets.py
"""存量发布态机器人资产审计（P0-4 闸门的存量闭环）。

闸门只拦截新的置位动作；本脚本审计已处于 READY 的存量机器人。
用法：
    python scripts/audit_published_assets.py            # 只读报告
    python scripts/audit_published_assets.py --unpublish --yes  # 资产不全者置回 DRAFT
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.models.robot_model import RobotModel, RobotStatus  # noqa: E402
from app.services.robot_asset_validator import validate_robot_assets  # noqa: E402
from app.services.storage import get_storage  # noqa: E402


async def main(unpublish: bool) -> int:
    engine = create_async_engine(settings.DATABASE_URL)
    storage = get_storage()
    incomplete = []
    try:
        async with async_sessionmaker(engine)() as session:
            result = await session.execute(
                select(RobotModel).where(RobotModel.status == RobotStatus.READY)
            )
            robots = list(result.scalars().all())
            print(f"== 审计 {len(robots)} 个 READY 机器人 ==")
            for robot in robots:
                missing = validate_robot_assets(robot.id, storage)
                if missing:
                    incomplete.append((robot, missing))
                    shown = "、".join(missing[:5])
                    more = f" 等共 {len(missing)} 项" if len(missing) > 5 else ""
                    print(f"  [缺资产] id={robot.id} {robot.brand}/{robot.model_name}: {shown}{more}")
                else:
                    print(f"  [完整]   id={robot.id} {robot.brand}/{robot.model_name}")

            if incomplete and unpublish:
                for robot, _ in incomplete:
                    robot.status = RobotStatus.DRAFT
                await session.commit()
                print(f"== 已将 {len(incomplete)} 个资产不全的机器人置回 DRAFT ==")
    finally:
        await engine.dispose()

    print(f"== 结果: {len(incomplete)} 个不完整 / {len(robots)} 个已发布 ==")
    return 1 if (incomplete and not unpublish) else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--unpublish", action="store_true", help="资产不全者置回 DRAFT")
    parser.add_argument("--yes", action="store_true", help="确认执行写操作")
    args = parser.parse_args()
    if args.unpublish and not args.yes:
        print("写操作需同时传 --yes 确认", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(asyncio.run(main(args.unpublish and args.yes)))
```

- [ ] **Step 2: 本地只读实跑并把完整输出写入报告**

Run: `python scripts/audit_published_assets.py`
Expected: 列出本地 rmos 库所有 READY 机器人及各自资产完整性。**不执行 --unpublish**（存量数据处置由用户决定），把输出原文写进任务报告。

- [ ] **Step 3: Commit**

```bash
git add scripts/audit_published_assets.py
git commit -m "feat: 存量发布机器人资产审计脚本(P0-4 闸门存量闭环)"
```

### Task 5: 测试欠账清理包（六笔）

**Files:**
- Modify: `app/services/storage/file_storage.py` + `app/services/storage/s3_storage.py`（仅 5d：list_files 子目录校验）
- Modify: `tests/test_storage.py`（5a symlink、5d 契约、5f 删 import json）
- Modify: `tests/test_s3_storage.py`（5e trimesh eager-load）
- Modify: `tests/unit/test_robot_asset_validator.py`（5b worker 回落、5c 409 截断）

- [ ] **Step 0: 补齐本地依赖（trimesh 在 requirements 但 venv 缺失）**

Run: `pip install -r requirements.txt && python -c "import trimesh; print(trimesh.__version__)"`
Expected: 版本号输出（5e 依赖它；不许用 importorskip——会增 skip 违反全局约束）

- [ ] **Step 1 (5a): Local symlink 逃逸测试（追加到 tests/test_storage.py Local 特有组）**

```python
def test_local_symlink_escape_blocked(tmp_path):
    """目录内符号链接指向目录外：resolve 跟随后被 is_relative_to 拒绝。"""
    base = tmp_path / "assets"
    outside = tmp_path / "outside"
    (base / "42").mkdir(parents=True)
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_bytes(b"secret")
    (base / "42" / "link.txt").symlink_to(secret)

    storage = LocalFileStorage(base_dir=str(base))
    with pytest.raises(ValueError):
        storage.download(robot_model_id=42, rel_path="link.txt")
```

- [ ] **Step 2 (5b+5c): worker 回落路径 + 409 截断测试（追加到 tests/unit/test_robot_asset_validator.py）**

```python
@pytest.mark.asyncio
async def test_worker_demotes_to_draft_when_assets_missing(test_db, tmp_path, monkeypatch):
    """P0-4 worker 路径：分析全部完成但资产不全 → 回落 DRAFT（此前只测了 publish 路径）。"""
    from app.models.analysis_task import AnalysisTask, AnalysisTaskStatus, AnalysisTaskType
    from app.services.analysis import worker as worker_mod

    monkeypatch.setattr(worker_mod, "_storage", LocalFileStorage(base_dir=str(tmp_path)))
    robot = RobotModel(
        brand="T", model_name="WorkerFall", owner_teacher_id=1,
        visibility=RobotVisibility.PRIVATE, status=RobotStatus.ANALYZING,
    )
    test_db.add(robot)
    await test_db.commit()
    await test_db.refresh(robot)
    task = AnalysisTask(
        robot_model_id=robot.id,
        task_type=AnalysisTaskType.FULL,
        status=AnalysisTaskStatus.COMPLETED,
    )
    test_db.add(task)
    await test_db.commit()
    await test_db.refresh(task)

    await worker_mod.analysis_worker._update_robot_status(task, test_db)
    await test_db.refresh(robot)
    assert robot.status == RobotStatus.DRAFT


@pytest.mark.asyncio
async def test_worker_promotes_to_ready_when_assets_complete(test_db, tmp_path, monkeypatch):
    from app.models.analysis_task import AnalysisTask, AnalysisTaskStatus, AnalysisTaskType
    from app.services.analysis import worker as worker_mod

    local = LocalFileStorage(base_dir=str(tmp_path))
    monkeypatch.setattr(worker_mod, "_storage", local)
    robot = RobotModel(
        brand="T", model_name="WorkerUp", owner_teacher_id=1,
        visibility=RobotVisibility.PRIVATE, status=RobotStatus.ANALYZING,
    )
    test_db.add(robot)
    await test_db.commit()
    await test_db.refresh(robot)
    _write_manifest(local, robot.id, {"m1": "models/a.glb"})
    local.upload(robot.id, "a.glb", b"glb", subdirectory="models")
    task = AnalysisTask(
        robot_model_id=robot.id,
        task_type=AnalysisTaskType.FULL,
        status=AnalysisTaskStatus.COMPLETED,
    )
    test_db.add(task)
    await test_db.commit()
    await test_db.refresh(task)

    await worker_mod.analysis_worker._update_robot_status(task, test_db)
    await test_db.refresh(robot)
    assert robot.status == RobotStatus.READY


@pytest.mark.asyncio
async def test_publish_409_detail_truncates_over_ten_missing(test_db, tmp_path, monkeypatch):
    """409 detail 的 >10 项截断分支（P0-4 遗留无测试）。"""
    from app.api.v1.endpoints import robots as robots_ep

    local = LocalFileStorage(base_dir=str(tmp_path))
    monkeypatch.setattr(robots_ep, "_storage", local)
    robot = RobotModel(
        brand="T", model_name="ManyMissing", owner_teacher_id=1,
        visibility=RobotVisibility.PRIVATE, status=RobotStatus.DRAFT,
    )
    test_db.add(robot)
    await test_db.commit()
    await test_db.refresh(robot)
    catalog = {f"m{i}": f"models/part_{i}.glb" for i in range(12)}
    _write_manifest(local, robot.id, catalog)  # 12 个 mesh 全缺失

    actor = ActorContext(user_id=1, email="t@rmos.test", roles={"teacher"}, permissions=set())
    with pytest.raises(HTTPException) as exc:
        await robots_ep.publish_robot(robot.id, db=test_db, actor=actor)
    assert exc.value.status_code == 409
    assert "等共 12 项" in exc.value.detail
```

（AnalysisTask 构造字段若与实际模型不符，参照 tests/unit/test_analysis_worker.py 现有构造调整，语义不变。文件顶部按需补 import。）

- [ ] **Step 3 (5d): list_files 子目录校验（双实现产品代码 + 契约测试）**

`file_storage.py` `LocalFileStorage.list_files` 开头与 `s3_storage.py` `S3FileStorage.list_files` 开头各加：

```python
        if subdirectory:
            _assert_safe_subdirectory(subdirectory)
```

（s3_storage.py 已 import 该函数；file_storage.py 同文件内直接可用。）

契约测试（追加到 tests/test_storage.py 契约组）：

```python
@pytest.mark.parametrize("bad_subdir", ["../43", "a/../b", "/abs"])
def test_list_files_rejects_bad_subdirectory(storage, bad_subdir):
    with pytest.raises(ValueError):
        storage.list_files(robot_model_id=42, subdirectory=bad_subdir)
```

- [ ] **Step 4 (5e): trimesh eager-load 集成测试（追加到 tests/test_s3_storage.py）**

```python
def test_trimesh_eager_load_survives_materialize_exit(s3_storage):
    """manifest_generator 依赖：trimesh 对 GLB eager-load，
    materialize 临时文件清理后仍可访问已加载对象（P1-1/P1-2 终审两度登记的欠账）。"""
    import trimesh

    glb_bytes = trimesh.creation.box(extents=(1, 1, 1)).export(file_type="glb")
    s3_storage.upload(robot_model_id=1, filename="box.glb", content=glb_bytes, subdirectory="models")

    with s3_storage.materialize(robot_model_id=1, rel_path="models/box.glb") as p:
        loaded = trimesh.load(str(p), force="scene")
        temp_path = p
    assert not temp_path.exists()  # 临时文件已清理
    # 块外访问已加载对象——eager-load 保证不再触盘
    assert len(loaded.geometry) >= 1
    for mesh in loaded.geometry.values():
        assert mesh.vertices.shape[0] > 0
```

- [ ] **Step 5 (5f): 删 tests/test_storage.py 顶部无用 `import json`**

- [ ] **Step 6: 全量回归 + Commit**

Run: `pytest -q`
Expected: ≥787 passed（780 + 本任务 ~7 项参数化后实际更多，报告登记）/ 3 skipped / 0 failed

```bash
git add app/services/storage/ tests/
git commit -m "test: 清理六笔测试欠账(symlink/worker回落/409截断/list_files校验/trimesh eager-load/死import)"
```

---

## Self-Review 记录

1. **范围覆盖**：总控计划 P2-1 五项中四项在本计划（分类+回归集/e2e 迁 PG/存量审计/欠账），Playwright 独立为 P2-1b；台账累积欠账六笔全部入 Task 5；M-3 schema parity 以 CI `alembic check` 门禁形式落地（Task 1）。
2. **占位符扫描**：Task 2 六个回归测试以"规格表+统一模式+夹具来源"给出（完整请求体依赖既有特征测试内容，两个全码示例已示范模式）；Task 5 AnalysisTask 构造留了实际模型核对的余地——均为锚点明确的指令，非 TBD。
3. **类型一致性**：`e2e_env` 返回 `(TestClient, session_factory)` 与现状一致；`_write_manifest`/`ActorContext`/`LocalFileStorage` 在 test_robot_asset_validator.py 中已存在（P0-4 建立）；marker 名 Task 1 定义、Task 2 消费一致。
