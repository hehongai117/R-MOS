# 交付成熟度升级总控计划（P0–P3 分级）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按 P0→P1→P2→P3 优先级，把 R-MOS 从"测试全绿的 MVP"推进到"可交付成熟产品"（可部署 M1 → 敢承诺 M2 → 可规模化 M3）。

**Architecture:** 依据 `docs/项目交接与升级路线图.md`（2026-07-02 修订版，已与代码逐项核对）。P0 全部是小任务，本计划直接给出可执行步骤；P1/P2 每项是独立子系统改造，本计划锁定任务边界、关键设计决策与验收标准，**执行前须按项目惯例先写子计划**（Fable 5 写 plan，subagent-driven 执行）。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + PostgreSQL / React 18 + TS 5.3 + Vite / GitHub Actions / Docker

## Global Constraints

- 所有改动必须保持现有测试网全绿：后端 692 passed / 前端 465 passed（skip 数不得增加，P0-2 会减少 skip 数）
- 后端 Python 3.13、Postgres 容器统一 16；前端 tsc + eslint --max-warnings 0 全绿
- 遵循 CLAUDE.md 既有模式：AsyncSession、Pydantic v2 `model_validate/model_dump`、机器人变更需 `_require_teacher_or_admin` + owner 校验
- 过程与结果反馈使用中文；commit message 遵循 conventional commits
- P0 全部完成并 CI 绿后才启动 P1；P1 的 T1-1a 完成前禁止动 S3 实现

## 依赖关系总览

```
P0-1 主线合并 ──────────► 其余一切任务（都在新主线上开工）
P0-2 CI门禁修复 ┐
P0-3 版本对齐   ├─ 相互独立，可并行
P0-4 资产闸门   │
P0-5 租户约定   ┘
P1-1 存储抽象收紧(T1-1a) ──► P1-2 对象存储实现(T1-1b)
P1-3 CD+环境分离(T1-2)   ──► P1-4 可观测性体系(T1-3 的指标部分依赖 staging 环境)
P2-1 测试体系升级 ─ 独立
P2-2 性能基线→优化 ─ 依赖可运行全栈环境（P1-3 的 staging 最佳）
P3   战略项与优化项 ─ 依赖业务决策（S-1/S-2）
```

---

# P0 — 立即执行（本周内，全部小任务，直接按下述步骤做）

> **✅ P0 已于 2026-07-03 全部完成并通过终审**（subagent-driven 执行，逐任务 review + Fable 终审）。
> 执行实录见 `.superpowers/sdd/progress.md`。计划外新增修复（执行中暴露的真实问题）：
> - 迁移链漂移 ×2（c386b081 补 5 列；86db2b1f pgvector IF EXISTS）——主线合并后 CI 首次在全新库建库暴露
> - CI 环境根因（957770a4：CI 无 .env → validate_production 拒启 e2e；atom01 测试/脚本硬编码本机路径）
> - P0-2 范围修正（fd93782f）：全量套件在 PG env 下有 asyncpg 跨事件循环问题（Linux 必现），
>   改为"PG 门禁独立成步 + 主套件裸跑"；全量迁 PG 留给 P2-1（原计划亦如此划分）
> - 终审必修（d0dd028e）：integration-ci 同步 DEBUG env（仅 PR 触发故潜伏）+ 前端透传 FastAPI detail
> - compose 修复（63abc39a）：dev 栈诚实声明 DEBUG=true，SECRET_KEY 守卫经正反向验证保持牙齿
>
> **终审移交备注（P1 开工必读）已归档于台账**：P1-1 需把 worker.py 第 3 个 LocalFileStorage 实例纳入工厂收敛；
> P1-2 注意 compose 无资产卷挂载；P1-3 建议引入显式 ENVIRONMENT=production 开关并保持两条 CI env 同步；
> P1-4 的第一个真实用例是 worker 回落 DRAFT 的教师可见通知。Defer 的 Minor 清单见台账分诊表。

## Task P0-1: 主线合并（先于一切）

**已核实事实：** `main` 落后 `quality-hardening-phase2` 70 个提交、**零分叉**（`git log quality-hardening-phase2..main` 为空），可 fast-forward，无冲突风险。

**Files:**
- 无代码改动，纯 git 操作

**Interfaces:**
- Produces: 新主线 `main` 包含全部质量硬化成果，后续所有任务基于它开分支

- [ ] **Step 1: 确认工作树干净**

```bash
cd /Users/xuhehong/Desktop/r-mos
git status --porcelain
```
Expected: 仅 `?? .claude/projects/`（本地记忆目录，不入库，可忽略）。若有其他未提交改动，先处理完再继续。

- [ ] **Step 2: fast-forward 合并到 main**

```bash
git checkout main
git merge --ff-only quality-hardening-phase2
```
Expected: `Fast-forward`，无冲突。若 `--ff-only` 失败说明 main 有新提交，停下来人工确认（按已核实状态不应发生）。

- [ ] **Step 3: 推送并确认 CI**

```bash
git push origin main
gh run list --branch main --limit 3
```
Expected: push 成功；等待 backend-ci / frontend-ci / integration-ci 在 main 上全绿（`gh run watch <run-id>` 跟踪）。

- [ ] **Step 4: 归档旧分支（打 tag 后删除本地分支）**

```bash
git tag archive/quality-hardening-phase1 quality-hardening-phase1
git tag archive/codex-publish-current-state codex/publish-current-state
git tag archive/feat-sop-adj-structure feat/sop-adj-structure
git branch -D quality-hardening-phase1 codex/publish-current-state feat/sop-adj-structure
# quality-hardening-phase2 与 main 指向同一提交，保留或删除均可；建议保留至 P0 全部完成
```
Expected: tag 存在（`git tag -l 'archive/*'` 列出 3 个），分支删除。tag 保底，操作可逆。

- [ ] **Step 5: 回写文档**

`CLAUDE.md` 与 `docs/项目交接与升级路线图.md` 1.4 节中关于分支的描述改为：主线为 `main`，硬化成果已合入。提交：

```bash
git add CLAUDE.md docs/项目交接与升级路线图.md
git commit -m "docs: 主线合并完成，更新分支说明"
git push origin main
```

## Task P0-2: CI 门禁修复 — pytest 切到已有的 Postgres 服务

**已核实事实：** `backend-ci.yml` 起了 Postgres 16 服务并先跑 `alembic upgrade head`（DB 为 `rmos_ci`），但 pytest 步骤 `DATABASE_URL` 指向 `sqlite+aiosqlite:///./rmos_main.db`，导致 `tests/unit/test_audit_query_index_gate.py` 等直接读环境变量的门禁测试被 skip。**单元/e2e 测试的数据库是 conftest 里硬编码的 `sqlite+aiosqlite:///:memory:`，不受此环境变量影响**——改动风险很低。

**Files:**
- Modify: `.github/workflows/backend-ci.yml`（两个 pytest 步骤的 env）

**Interfaces:**
- Produces: CI 中 Postgres 门禁测试真实运行；`rmos_ci` 库经 alembic 迁移后含 `audit_events` 全部索引

- [ ] **Step 1: 排查所有直接读 DATABASE_URL 的测试**

```bash
grep -rn 'getenv("DATABASE_URL")' r-mos-backend/tests/
```
把命中的每个文件记下来——它们就是本次会从 skip 变为运行的测试，逐个确认其断言对象（索引、执行计划等）在 alembic 迁移后的库中成立。

- [ ] **Step 2: 本地用 Postgres 预演门禁测试**

```bash
cd r-mos-backend && source venv/bin/activate
DATABASE_URL="postgresql+asyncpg://$(whoami)@localhost:5432/rmos" \
  pytest tests/unit/test_audit_query_index_gate.py -v
```
Expected: 2 passed（不再 skip）。该测试插入一条探针审计记录并在 finally 中删除，对本地库无残留。若失败，按 systematic-debugging 排查后再动 CI。

- [ ] **Step 3: 修改 backend-ci.yml**

把文件中每一处

```yaml
        env:
          DATABASE_URL: sqlite+aiosqlite:///./rmos_main.db
```

改为

```yaml
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/rmos_ci
```

（共两个 pytest 步骤：`Pytest core 14 services coverage gate` 与全量 `--cov=app` 步骤；若第二个步骤原本没有 env 块，为其补上同样的 env。）

- [ ] **Step 4: 提交并观察 CI**

```bash
git add .github/workflows/backend-ci.yml
git commit -m "ci: pytest 使用工作流内 Postgres 服务，解锁 DB 门禁测试"
git push origin main
gh run watch $(gh run list --branch main --workflow backend-ci.yml --limit 1 --json databaseId -q '.[0].databaseId')
```
Expected: backend-ci 绿，且日志中 `test_audit_query_index_gate` 为 PASSED 非 SKIPPED；passed 总数 ≥ 694。

- [ ] **Step 5: 回写记忆与测试规划文档**

`docs/2026-07-02-full-test-plan.md` 中 P3（Postgres 门禁）标记已修复。提交。

## Task P0-3: 版本漂移对齐（Python 3.13 / Postgres 16）

**已核实事实：** 本地 venv 与 CI 均为 Python 3.13，仅 `r-mos-backend/Dockerfile` 是 `python:3.11-slim`；CI 用 `postgres:16`，`docker-compose.yml` 用 `postgres:14-alpine`。

**Files:**
- Modify: `r-mos-backend/Dockerfile:1`
- Modify: `docker-compose.yml`（postgres image 行）

- [ ] **Step 1: 改 Dockerfile 基础镜像**

`r-mos-backend/Dockerfile` 第 1 行：

```dockerfile
FROM python:3.13-slim
```

- [ ] **Step 2: 改 compose 的 Postgres 版本**

`docker-compose.yml`：

```yaml
    image: postgres:16-alpine
```

- [ ] **Step 3: 验证镜像可构建、栈可启动**

```bash
docker build -t rmos-backend-test r-mos-backend/
# 注意：旧 pgdata 卷是 PG14 初始化的，PG16 无法直接挂载。
# 该卷仅是本机开发容器数据（可由种子脚本重建），删除仅影响容器卷，不影响本机 Homebrew PostgreSQL：
docker compose down -v
docker compose up -d
docker compose ps
curl -sf http://localhost:8000/api/v1/health
```
Expected: 构建成功；`docker compose ps` 两个服务 healthy/running；health 返回 200。若 `pip install` 在 3.13 下有包编译失败，逐个查该包是否需要升级版本（venv 已在 3.13 下装过同一份 requirements，预期无问题）。

- [ ] **Step 4: 提交**

```bash
git add r-mos-backend/Dockerfile docker-compose.yml
git commit -m "chore: 容器镜像对齐运行时版本(Python 3.13/Postgres 16)"
git push origin main
```

## Task P0-4: 机器人资产完整性校验闸门（原 T1-4，TDD）

**已核实事实：** 机器人置 READY 有两条路径——`PUT /robots/{id}/publish`（`robots.py:340`，经 `RobotService.can_publish` 只挡"分析中"）与分析 worker 自动置位（`app/services/analysis/worker.py:81`）。前端 3D 加载依赖 `manifests/assembly_manifest.json` 的 `mesh_catalog: dict[str, str]`（mesh_id → 如 `models/base_link.glb` 的相对路径），经 `GET /api/v1/robots/{id}/assets/{path}` 取文件。灵犀X1（id=3）只有 `models/ uploads/` 目录、无 manifest，是现成的"发布态缺资产"反例。

**Files:**
- Create: `r-mos-backend/app/services/robot_asset_validator.py`
- Create: `r-mos-backend/tests/unit/test_robot_asset_validator.py`
- Modify: `r-mos-backend/app/api/v1/endpoints/robots.py:355-361`（publish 闸门）
- Modify: `r-mos-backend/app/services/analysis/worker.py:63-82`（自动 READY 闸门）

**Interfaces:**
- Consumes: `FileStorageBase.download(robot_model_id, rel_path)` / `list_files(robot_model_id)`（`app/services/storage/file_storage.py`）
- Produces: `validate_robot_assets(robot_model_id: int, storage: FileStorageBase) -> list[str]`（返回缺失项相对路径列表，空列表=校验通过；P1-1 收紧存储抽象时此函数签名不变）

- [ ] **Step 1: 写失败测试**

```python
# r-mos-backend/tests/unit/test_robot_asset_validator.py
"""资产完整性校验闸门（T1-4）单元测试。"""
import json

import pytest

from app.services.robot_asset_validator import (
    MANIFEST_REL_PATH,
    validate_robot_assets,
)
from app.services.storage.file_storage import LocalFileStorage


@pytest.fixture
def storage(tmp_path) -> LocalFileStorage:
    return LocalFileStorage(base_dir=str(tmp_path))


def _write_manifest(storage: LocalFileStorage, robot_id: int, mesh_catalog: dict) -> None:
    manifest = {"version": "1.0", "mesh_catalog": mesh_catalog, "nodes": []}
    storage.upload(
        robot_id,
        "assembly_manifest.json",
        json.dumps(manifest).encode("utf-8"),
        subdirectory="manifests",
    )


def test_missing_manifest_reported(storage):
    assert validate_robot_assets(99, storage) == [MANIFEST_REL_PATH]


def test_invalid_manifest_json_reported(storage):
    storage.upload(7, "assembly_manifest.json", b"not-json", subdirectory="manifests")
    missing = validate_robot_assets(7, storage)
    assert len(missing) == 1
    assert MANIFEST_REL_PATH in missing[0]


def test_missing_mesh_reported(storage):
    _write_manifest(storage, 7, {"m1": "models/a.glb", "m2": "models/b.glb"})
    storage.upload(7, "a.glb", b"glb-bytes", subdirectory="models")
    assert validate_robot_assets(7, storage) == ["models/b.glb"]


def test_complete_assets_pass(storage):
    _write_manifest(storage, 7, {"m1": "models/a.glb"})
    storage.upload(7, "a.glb", b"glb-bytes", subdirectory="models")
    assert validate_robot_assets(7, storage) == []


def test_empty_mesh_catalog_passes_with_manifest(storage):
    _write_manifest(storage, 7, {})
    assert validate_robot_assets(7, storage) == []
```

- [ ] **Step 2: 跑测试确认失败**

```bash
cd r-mos-backend && source venv/bin/activate
pytest tests/unit/test_robot_asset_validator.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.robot_asset_validator'`

- [ ] **Step 3: 实现校验器**

```python
# r-mos-backend/app/services/robot_asset_validator.py
"""机器人资产完整性校验（发布闸门，T1-4）。

置 READY 前校验 assembly manifest 存在且 mesh_catalog 引用的文件齐全，
根治"发布态机器人 3D 打不开"。
"""
import json

from app.services.storage.file_storage import FileStorageBase

MANIFEST_REL_PATH = "manifests/assembly_manifest.json"


def validate_robot_assets(robot_model_id: int, storage: FileStorageBase) -> list[str]:
    """返回缺失资产的相对路径列表；空列表表示校验通过。"""
    try:
        manifest_bytes = storage.download(robot_model_id, MANIFEST_REL_PATH)
    except FileNotFoundError:
        return [MANIFEST_REL_PATH]

    try:
        manifest = json.loads(manifest_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return [f"{MANIFEST_REL_PATH} (JSON 解析失败)"]

    mesh_catalog: dict = manifest.get("mesh_catalog") or {}
    existing = set(storage.list_files(robot_model_id))
    return [rel_path for rel_path in mesh_catalog.values() if rel_path not in existing]
```

- [ ] **Step 4: 跑测试确认通过**

```bash
pytest tests/unit/test_robot_asset_validator.py -v
```
Expected: 5 passed

- [ ] **Step 5: 提交校验器**

```bash
git add app/services/robot_asset_validator.py tests/unit/test_robot_asset_validator.py
git commit -m "feat: 机器人资产完整性校验器(发布闸门 T1-4)"
```

- [ ] **Step 6: 写发布端点闸门的失败测试（追加到同一测试文件）**

```python
# 追加到 r-mos-backend/tests/unit/test_robot_asset_validator.py
from fastapi import HTTPException

from app.models.robot_model import RobotModel, RobotStatus, RobotVisibility
from app.services.authz_guard import ActorContext


@pytest.mark.asyncio
async def test_publish_blocked_when_assets_missing(test_db, tmp_path, monkeypatch):
    """资产不全的机器人发布应被 409 阻断，且报错指明缺失文件。"""
    from app.api.v1.endpoints import robots as robots_ep

    monkeypatch.setattr(robots_ep, "_storage", LocalFileStorage(base_dir=str(tmp_path)))

    robot = RobotModel(
        brand="Test", model_name="NoAssets", owner_teacher_id=1,
        visibility=RobotVisibility.PRIVATE, status=RobotStatus.DRAFT,
    )
    test_db.add(robot)
    await test_db.commit()
    await test_db.refresh(robot)

    actor = ActorContext(user_id=1, email="t@rmos.test", roles={"teacher"}, permissions=set())
    with pytest.raises(HTTPException) as exc:
        await robots_ep.publish_robot(robot.id, db=test_db, actor=actor)
    assert exc.value.status_code == 409
    assert MANIFEST_REL_PATH in exc.value.detail

    await test_db.refresh(robot)
    assert robot.status == RobotStatus.DRAFT


@pytest.mark.asyncio
async def test_publish_allowed_when_assets_complete(test_db, tmp_path, monkeypatch):
    from app.api.v1.endpoints import robots as robots_ep

    local = LocalFileStorage(base_dir=str(tmp_path))
    monkeypatch.setattr(robots_ep, "_storage", local)

    robot = RobotModel(
        brand="Test", model_name="FullAssets", owner_teacher_id=1,
        visibility=RobotVisibility.PRIVATE, status=RobotStatus.DRAFT,
    )
    test_db.add(robot)
    await test_db.commit()
    await test_db.refresh(robot)

    _write_manifest(local, robot.id, {"m1": "models/a.glb"})
    local.upload(robot.id, "a.glb", b"glb-bytes", subdirectory="models")

    actor = ActorContext(user_id=1, email="t@rmos.test", roles={"teacher"}, permissions=set())
    result = await robots_ep.publish_robot(robot.id, db=test_db, actor=actor)
    assert result.status == RobotStatus.READY
```

- [ ] **Step 7: 跑测试确认失败**

```bash
pytest tests/unit/test_robot_asset_validator.py -v
```
Expected: `test_publish_blocked_when_assets_missing` FAIL（当前 publish 不校验资产，机器人被置 READY，不抛 409）

- [ ] **Step 8: 在 publish 端点接入闸门**

`r-mos-backend/app/api/v1/endpoints/robots.py`，顶部 import 区加：

```python
from app.services.robot_asset_validator import validate_robot_assets
```

`publish_robot` 中（原 355-361 行）改为：

```python
    if robot.status == RobotStatus.READY:
        # 取消发布
        robot.status = RobotStatus.DRAFT
    else:
        if not RobotService.can_publish(robot.status):
            raise HTTPException(status_code=409, detail="当前状态不允许发布（分析进行中）")
        missing = validate_robot_assets(robot_id, _storage)
        if missing:
            shown = "、".join(missing[:10])
            suffix = f" 等共 {len(missing)} 项" if len(missing) > 10 else ""
            raise HTTPException(
                status_code=409,
                detail=f"资产不完整，无法发布。缺失：{shown}{suffix}",
            )
        robot.status = RobotStatus.READY
```

- [ ] **Step 9: 跑测试确认通过**

```bash
pytest tests/unit/test_robot_asset_validator.py -v
```
Expected: 7 passed

- [ ] **Step 10: 在分析 worker 自动置位处接入闸门**

先查现有 worker 测试，改动会让"分析完成但资产不全"的机器人回落 DRAFT 而非 READY：

```bash
grep -rn "_update_robot_status\|RobotStatus.READY" tests/ --include="*.py"
```

`app/services/analysis/worker.py` 顶部 import 区加（若无 logger 则一并加）：

```python
import logging

from app.services.robot_asset_validator import validate_robot_assets
from app.services.storage.file_storage import LocalFileStorage

logger = logging.getLogger(__name__)
_storage = LocalFileStorage()
```

`_update_robot_status` 中（原 80-82 行）改为：

```python
            if not pending_result.scalar_one_or_none():
                missing = validate_robot_assets(robot.id, _storage)
                if missing:
                    robot.status = RobotStatus.DRAFT
                    logger.warning(
                        "机器人 %s 分析完成但资产不完整（缺 %d 项），置为 DRAFT 待教师处理",
                        robot.id, len(missing),
                    )
                else:
                    robot.status = RobotStatus.READY
                await db.commit()
```

若 Step 10 的 grep 命中了断言"分析完成即 READY"的既有测试，按新规格更新其断言（补齐夹具资产使其 READY，或改断言为 DRAFT）——这是行为规格变更，不是测试迁就。

- [ ] **Step 11: 全量回归**

```bash
pytest
```
Expected: ≥ 699 passed（692 + 本任务新增 7），0 failed。skip 数不增。

- [ ] **Step 12: 验收演示（对灵犀X1）并提交**

后端跑起来后（`python main.py`），以 teacher 身份调用：

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"teacher1@rmos.demo","password":"Teacher@123"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
curl -s -X PUT http://localhost:8000/api/v1/robots/3/publish -H "Authorization: Bearer $TOKEN"
```
Expected: 409，detail 指明缺失 `manifests/assembly_manifest.json`。

```bash
git add app/api/v1/endpoints/robots.py app/services/analysis/worker.py tests/
git commit -m "feat: 发布与自动置位双路径接入资产完整性闸门"
git push origin main
```

**注意：** 数据库中已处于 READY 但资产不全的存量机器人（如灵犀X1若已发布）不会被本闸门自动降级——闸门只拦截新的置位动作。存量数据清理放 P2-1 或由教师手动取消发布。

## Task P0-5: 多租户预防约定制度化（S-2 零成本预防）

**Files:**
- Modify: `CLAUDE.md`（Key Technical Patterns 节）

- [ ] **Step 1: 在 CLAUDE.md 的 Key Technical Patterns 追加一行**

```markdown
- **Multi-tenancy prep**: 所有新建表必须带租户维度字段（当前用 `school_id`/`school_name`，建外键优先）；新查询禁止写跨租户逻辑。正式租户隔离方案见路线图 S-2。
```

- [ ] **Step 2: 提交**

```bash
git add CLAUDE.md
git commit -m "docs: 新表强制租户维度字段(S-2 预防约定)"
git push origin main
```

---

# P1 — 生产化地基（M1，接第一个真实客户前必须；每项先写子计划）

> 执行顺序：P1-1 → P1-2 严格串行；P1-3、P1-4 可与 P1-1/1-2 并行。

## Task P1-1: 存储抽象收紧（T1-1a，S3 化前置）

**目标：** 在纯本地存储下消灭 `FileStorageBase` 的本地路径语义泄漏，使 P1-2 只需"新增实现类"。

**已锁定的设计决策：**
1. `get_full_path()` 从接口移除对 HTTP 层的暴露：资产下发端点（`robots.py:523-539` 的 `FileResponse`）改为流式响应（`StreamingResponse` 包 `storage.download`），接口预留 `get_public_url() -> str | None`（本地实现返回 None → 走流式；S3 实现返回预签名 URL → 302 重定向）。
2. 分析管线（`cad_converter.py`、`pdf_extractor.py`、`manifest_generator.py`）需要真实本地文件，改用显式模式：新增 `storage.materialize(robot_model_id, rel_path) -> ContextManager[Path]`（本地实现直接给原路径；S3 实现下载到临时目录、退出时清理）。
3. 清理两处绕过抽象的硬编码：`app/api/v1/endpoints/robots.py:471` 与 `app/services/training/workbench_draft_generator.py:72` 的 `Path("data/robot-assets")`，统一走 storage 实例。
4. 接口异步化暂不做（避免大面积传染），S3 实现内部用 `anyio.to_thread` 包住阻塞 IO——决策记录进子计划。
5. storage 实例从各处模块级 `LocalFileStorage()` 收敛为 `app/services/storage/__init__.py` 的工厂函数（按配置返回实现），全仓库单一入口。

**范围（触及文件）：** `app/services/storage/file_storage.py`、`robots.py`、`worker.py`（P0-4 新增的 `_storage`）、三个分析服务、`workbench_draft_generator.py`、对应测试。

**验收标准：**
- `grep -rn 'Path("data/robot-assets")' app/` 零命中
- 接口不再向 HTTP 层返回本地路径；`FileResponse(full_path)` 消失
- 现有全量测试保持全绿（`test_storage.py` 按新接口更新属规格变更）
- P0-4 的 `validate_robot_assets` 签名不变、测试不改仍绿

**子计划要求：** TDD 逐文件迁移；先加新接口方法（带 Local 实现+测试），再逐调用点切换，最后删旧暴露。

## Task P1-2: 对象存储实现（T1-1b，依赖 P1-1）

**目标：** `S3FileStorage`（兼容 S3/阿里云 OSS/MinIO 协议），配置一键切换。

**已锁定的设计决策：** 用 `boto3` + 自定义 endpoint（MinIO/OSS 均兼容）；桶内 key 布局与本地目录结构一致（`{robot_model_id}/models/...`）；资产下发优先预签名 URL（`get_public_url`），大文件不过后端；`materialize` 下载到 `tempfile.TemporaryDirectory`。

**验收标准（照抄路线图）：** 本地 MinIO 容器下走通"教师上传 → AI 分析 → 学生 3D 加载"全链路；配置切回本地存储所有测试仍绿；docker-compose 增加 minio 服务供开发/CI 用。

## Task P1-3: CD + 环境分离 + 前端容器化（T1-2 剩余部分）

**目标：** 推 tag 自动构建镜像并部署 staging；dev/staging/prod 配置分离；生产校验在启动时生效。

**已锁定的设计决策：**
1. 前端补 Dockerfile（多阶段：node build → nginx 静态托管 + `/api` 反代后端）；compose 增加 frontend 服务，形成一条命令起全栈。
2. GitHub Actions 新增 `release.yml`：push tag `v*` → 构建前后端镜像 → 推镜像仓库 → 部署 staging（部署目标待用户提供：自有服务器 ssh / 云厂商，子计划前需确认）。
3. 生产校验接入：`SECRET_KEY` 非默认值、`DATABASE_URL` 必须 Postgres——代码已有校验逻辑，确保 `DEBUG=false` 时启动即强制（fail fast），并在 compose 的 prod profile 中验证。
4. 环境配置用 `.env.dev/.env.staging/.env.prod` 模板 + compose profiles，不引入新配置系统。

**验收标准（照抄路线图）：** 推 tag 自动出镜像并部署 staging；staging 用非默认密钥 + Postgres 通过启动校验；干净机器 `docker compose up` 10 分钟内可演示。

**阻塞项：** 部署目标（服务器/云）与镜像仓库选择需用户决定后才能写子计划。

## Task P1-4: 可观测性（T1-3）

**目标：** 先有错误告警（速赢），再有结构化日志与指标。

**已锁定的设计决策：**
1. **速赢（半天）**：Sentry 前端（`@sentry/react`，挂 ErrorBoundary/RouteErrorBoundary 上报）+ 后端（`sentry-sdk[fastapi]`，挂全局异常处理器）。DSN 走环境变量，未配置时完全禁用（本地开发零影响）。**阻塞项：需用户提供 Sentry 账号/DSN（或选 self-hosted）。**
2. 结构化日志：后端 `logging` 切 JSON formatter（自写 formatter，不引重依赖），请求级 trace_id 贯穿（已有审计 trace_id 体系可复用）。
3. 指标：把 `PERF_TIMING` 计时中间件升级为 Prometheus `/metrics` 端点（`prometheus-fastapi-instrumentator`），staging 起 Prometheus + Grafana（compose profile）。
4. 顺手修（路线图低优债，属本任务范围）：Viewer3DErrorBoundary 切换机器人不自动恢复——在 robotId 变化时 reset error state。

**验收标准（照抄路线图）：** staging 人为抛错 5 分钟内收到告警；核心 API P95 时延有仪表盘。

---

# P2 — 交付质量体系（M2，决定敢不敢书面承诺给学校）

## Task P2-1: 测试体系升级（T2-1 剩余部分；CI Postgres 已在 P0-2 完成）

**目标：** 规格测试体系 + 浏览器级 E2E。

**已锁定的设计决策：**
1. 测试分类标注：pytest marker `@pytest.mark.characterization`（锁现状）vs 默认规格测试；8 个已修 P0 bug 建 `tests/regression/` 回归集（每 bug 一个测试，文件名含 bug 编号）。
2. Playwright E2E：新建 `r-mos-frontend/e2e/`，覆盖黄金路径（教师登录→机器人管理→发布；学生登录→选机器人→实操→提交→看报告），跑在 CI（复用 integration-ci 的 Postgres + 种子数据，起真实前后端）。
3. 后端 e2e 的 conftest 从内存 SQLite 迁到 Postgres（testcontainers 或环境变量指向 CI 服务），消除方言差异——按"以当前最新状态为准"原则，迁移中暴露的方言 bug 修产品代码而非测试。
4. 存量数据校验：对库中全部 READY 机器人跑一遍 P0-4 的 `validate_robot_assets`，出报告，资产不全者取消发布（配合闸门形成闭环）。

**验收标准（照抄路线图）：** CI 无因数据库原因 skip 的测试；黄金路径 E2E 进 CI 连续 10 次无 flake。

## Task P2-2: 性能基线 → 针对性优化（T2-2）

**目标：** 用 Phase 4 已备好的工具采基线，依数据定位真实瓶颈再优化。

**执行方式：** 按 `docs/superpowers/plans/phase4-baseline-collection-cheatsheet.md` 采集（Lighthouse 首屏/关键路由、WS 5Hz 探针、3D trace、`PERF_TIMING=1` AI 管线计时），回填 `phase4-baseline.md` 四段。**采完基线后再写优化子计划（phase4b），无数据不优化。**

**依赖：** 可运行全栈环境；建议等 P1-3 的 staging 就绪后在 staging 上采（比本机数据更接近真实）。

**验收标准：** 基线数据回填完成；每项优化有 before/after 对比数据。

---

# P3 — 战略项与锦上添花（依业务决策与规模节奏）

## P3-0: 战略决策点（非工程任务，需业务对齐后才拆解）

- **S-1 真机接入 vs 纯数字孪生**：决定后若接真机 → 写 Real/Gazebo 适配器 initiative（最大工程块，基于 `BaseRobotAdapter` 扩展点）；若纯孪生 → 孪生体验深化 initiative。
- **S-2 多租户隔离**：若定多校 SaaS → 租户隔离 initiative（`school_name` 字符串 → 外键 + 行级安全或分 schema）。P0-5 的约定已在止血。

## P3-1: 优化项清单（规模稳定后逐项立项）

| 项 | 说明 |
|----|------|
| AI 内容质量评测 | 不同机型 SOP 生成质量的自动评测机制 |
| 裁决引擎 IP 化 | `src/adjudication/` 补测试、文档化、可对外输出 |
| 国际化 | 界面文字外置（现写死中文） |
| 设计系统 | 前端组件库统一沉淀 |
| 依赖债 | dev 构建链 12 漏洞破坏性升级；Pydantic V2 class-based Config 弃用清理 |
| WS 初连抖动 | 遥测首连一次抖动后自愈，低优排查 |

---

# 执行约定

1. **P 级严格串行推进**：P0 全绿 → P1 → P2 → P3；同级内按各节标注的依赖并行。
2. **P0 按本计划直接执行**（subagent-driven，每 Task 一个 subagent，任务间 review）；**P1/P2 每 Task 先写子计划**（Fable 5 编写，含 TDD 步骤），落地前过 brainstorm 确认阻塞项（P1-3 部署目标、P1-4 Sentry 账号）。
3. **每完成一个 P 级**：回写本计划勾选、`CLAUDE.md`、`docs/项目交接与升级路线图.md` 与记忆（feedback_update_after_phase 约定）。
4. **测试网不可破**：任何任务导致既有测试红即停，按 systematic-debugging 处理；行为规格变更须在 commit message 中说明。
