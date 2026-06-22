# R-MOS 质量硬化升级 — 设计 Spec

> 日期：2026-06-22
> 类型：质量升级（重构 + 测试 + 工程化 + 性能硬化，**不新增产品功能**）
> 状态：设计已确认，待生成实施计划

## 1. 背景

R-MOS 已进入功能成熟期：后端 211 个 Python 文件 / ~3.4 万行 + 389 个测试文件；前端 236 个 TS/TSX 文件 / ~3.8 万行 + 75 个测试。多机器人平台、通用 3D 查看器、模块化改造等大型 Phase 均已完成。

随之出现典型的「成熟期债务」：巨型文件、仓库卫生退化、前端测试覆盖失衡、性能未系统测量。本次升级聚焦**质量与可维护性**，不扩展产品功能范围（新功能另走独立 spec）。

CI 现状（已存在，非从零搭建）：
- 后端 `backend-ci.yml`：alembic 迁移 + pytest + **14 个核心服务**覆盖率门禁
- 前端 `frontend-ci.yml`：`tsc --noEmit` + eslint(`--max-warnings 0`) + vitest + build
- `integration-ci.yml`：集成测试

## 2. 目标与非目标

**目标**
1. 拆解巨型文件，降低维护成本，理清模块边界
2. 为待重构文件建立测试安全网，并扩大 CI 覆盖率门禁
3. 清理仓库卫生（根目录杂物、历史文档、遗留分支、文档结构）
4. 系统测量并优化性能 / 健壮性（3D 查看器、WebSocket、AI 管线、首屏）

**非目标**
- 不新增产品功能
- 不改动产品对外行为（重构须保持行为等价）
- 不做与本次目标无关的大范围重构

## 3. 核心原则：测试先于重构

1600+ 行的文件在缺乏测试保护时重构 = 引入回归的最快路径。因此**测试安全网（Phase 2）是重构（Phase 3）的硬前置**。整体顺序遵循「清理 → 织网 → 重构 → 优化」的安全优先路线（方案 A）。

被否决的备选：
- 方案 B（重构优先）：缺安全网，回归风险高
- 方案 C（并行分轨）：最快但协调成本高，重构仍无测试保护

## 4. 分阶段设计

> 执行规范遵循 CLAUDE.md：Plan 用 Opus；Task 用 Subagent 驱动、任务间 review；每个 Phase 完成后更新 CLAUDE.md + 总控计划 + 记忆。

### Phase 1 · 仓库工程化与卫生（低风险，快速见效）

- **根目录清理**：将 `R-MOS 数字孪生维保智能体功能介绍.docx`、`全国高校名单.xls`、`reorder_pptx.py`、`reorder_slides.py`、`add_rmos_to_ppt.py`、根级 `__pycache__/`、以及散落在根目录的多份重构方案（`R-MOS-前端重构方案-v1.0.md`、`R-MOS_Frontend_Redesign_Plan.md`、`R-MOS_Review_Test_Cleanup_Plan.md`、`R-MOS_Transformation_Plan_V1.0.md` 等）归档进 `docs-archive/` 或删除（逐一确认后处理，未自创的产物以核实为先）。
- **大日志治理**：`DEVELOPMENT_LOG.md`（583KB）拆分按时间归档或移入 `docs-archive/`。
- **遗留分支清理**：核实 8 个本地分支（`mvp-skeleton`、`feat/phase1-teaching-p0`、`feat/sop-adj-structure`、`feat/sopScripts-adj`、`chore-run-and-clean`、`codex/*`）已合并后删除。
- **文档结构统一**：校正 CLAUDE.md 中过期/失效的文件指向，确认 `docs/` 与 `docs-archive/` 边界清晰。
- **gitignore 加固**：确保 `__pycache__`、构建产物、临时文件不再入库。

**验收**：根目录仅保留必要工程文件；`git status` 干净；CLAUDE.md 链接全部有效。

### Phase 2 · 测试安全网（重构前置）

- 为 Phase 3 待重构的巨型文件补**特征测试 / characterization tests**（锁定当前行为，而非重新设计行为）：
  - 前端：`SOPMaintenancePage.tsx`、`Atom01Interactive.tsx`、`SOPPlayerAdjudicated.tsx`
  - 后端：`agent.py`、`training.py`、`teaching.py` 端点的关键路径
- 将上述目标纳入 CI 覆盖率门禁（扩展 `backend-ci.yml` 覆盖列表 + 前端覆盖阈值）。
- 全量跑通前后端测试，修复挂掉/不稳定的用例，确认基线全绿。

**验收**：目标文件具备可回归的特征测试；CI 覆盖率门禁纳入新目标；前后端测试全绿且稳定。

### Phase 3 · 巨型文件重构（在测试保护下）

- **前端**（拆为子组件 + 自定义 hooks，保持行为等价）：
  - `SOPMaintenancePage.tsx`（1615）
  - `Atom01Interactive.tsx`（1207）
  - `SOPPlayerAdjudicated.tsx`（895）
- **后端**（端点瘦身，业务逻辑下沉至 service 层）：
  - `agent.py`（1214）
  - `training.py`（1038）
  - `teaching.py`（901）
  - `orchestrator_v2.py`（772）视情况一并梳理
- 顺带清理残留的 ATOM-01 硬编码债务（与多机器人目标收尾）。

**验收**：单文件行数显著下降、职责单一；Phase 2 测试全绿（行为等价）；无新增 lint/type 错误。

### Phase 4 · 性能与健壮性硬化（先测量后优化）

- **先测量基线**：用 Lighthouse / 性能 trace 采集 3D 查看器渲染、首屏加载、WebSocket（5Hz 遥测）、AI 管线的当前指标。
- **再针对性优化**：依据基线定位真实瓶颈再动手，避免臆测式优化。
- **健壮性**：补充错误边界、请求超时/重试、降级与失败提示策略。

**验收**：关键路径有可对比的「优化前/后」性能数据；健壮性改进有测试或可复现验证覆盖。

## 5. 关键路径与依赖

```
Phase 1 (卫生) ──▶ Phase 2 (测试网) ──▶ Phase 3 (重构)
                                    └──▶ Phase 4 (性能) 可与 Phase 3 部分并行
```

- Phase 2 是 Phase 3 的硬前置。
- Phase 1 无强依赖，可最先快速完成以降噪。
- Phase 4 的测量可在 Phase 2 后启动，优化实施可与 Phase 3 错峰并行。

## 6. 风险

| 风险 | 缓解 |
|------|------|
| 重构引入回归 | 测试先行（Phase 2 硬前置）+ 行为等价验收 |
| 清理误删有价值产物 | 逐一核实，倾向归档而非删除；未自创产物先核实再处理 |
| 性能臆测式优化 | 先测量基线，依据数据定位瓶颈 |
| 巨型文件拆分边界不清 | 重构前先在测试中固化对外接口/行为 |

## 7. 验收总览

- 根目录与文档结构整洁，遗留分支清理完毕
- 巨型文件具备特征测试并纳入 CI 门禁，测试全绿
- 目标巨型文件完成拆分、行为等价
- 关键性能路径具备「优化前/后」对比数据，健壮性改进可验证
