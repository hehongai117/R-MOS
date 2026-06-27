# Phase 3：巨型文件重构（测试保护下）— 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development（推荐，逐 Task 派发 + 任务间 review）实施本计划。步骤用 checkbox（`- [ ]`）跟踪。
>
> 设计 Spec：`docs/superpowers/specs/2026-06-22-quality-hardening-upgrade-design.md`（Phase 3）
> 总控计划：`docs/superpowers/plans/2026-06-22-quality-hardening-master-plan.md`
> 前置：Phase 2（`2026-06-25-phase2-test-safety-net.md`）✅ 已建立特征测试安全网

**Goal:** 在 Phase 2 特征测试保护下，拆解 6 个（+1 可选）巨型文件，使单文件职责单一、行数显著下降，**对外行为完全等价**（特征测试与全量测试保持绿）。

**Architecture:** 纯结构性重构，零行为变化。前端：把状态机/回调桥/派生计算抽成自定义 hooks，把渲染片段下沉到既有 Shell 子组件，把常量/类型抽到 config 模块；3D 组件按既有子组件边界拆文件。后端：把内联 Pydantic schema 抽到 `app/schemas/`，把按业务域分组的路由拆成 sub-router 模块并 `include_router` 回原 router——**保持 URL 路径与响应完全不变**。

**Tech Stack:** 前端 React + TypeScript + Vite + vitest；后端 FastAPI APIRouter + Pydantic 2.x + pytest。

## Global Constraints

- **行为等价是硬约束**：本 Phase **不改任何对外可观测行为**（HTTP 路径/状态码/响应体；前端渲染 DOM/交互回调）。判据 = Phase 2 特征测试 + 全量测试**全程保持绿**，断言**一字不改**。若某测试在重构后失败，说明重构破坏了行为 → 回退该步，不得修改测试去迁就。
- **纯移动优先**：抽取以**逐字移动现有代码**为主（symbol 整体搬到新文件 + 修正 import/export），不顺手改写逻辑、不重命名对外符号、不"优化"。需要的小适配（如把模块级常量改成 hook 参数）必须最小化并在 commit message 注明。
- **安全网随代码移动**：当受 Phase 2 门禁守护的代码被移出原文件，**必须同步更新门禁范围**，否则被移动代码的覆盖率不再被守护：
  - 后端：`.github/workflows/backend-ci.yml` 的 `God-file endpoint coverage gate` 步骤 `--include` glob 要覆盖新 sub-router 文件（用 `*/app/api/v1/endpoints/agent*.py` 等通配，或显式追加新文件）。
  - 前端：`r-mos-frontend/vitest.config.ts` 的 `coverage.include` 与 `thresholds` 要追加新抽出的 hook/component 文件（阈值 ≥ 抽出后实测值，建议沿用对应巨型文件的原阈值档：页面/播放器 70、3D 55）。
- **逐文件验证四件套**（每个 Task 收尾必跑且全绿）：
  1. 对应特征测试：前端 `npx vitest run <char-test>`；后端 `python -m pytest tests/unit/<char-test> -o addopts='' -q`
  2. 类型/词法：前端 `npx tsc --noEmit` + `npx eslint <changed> --max-warnings 0`；后端 `python -m pytest`（全量，确认无 import 破裂）
  3. 行数下降：`wc -l <原文件>` 较重构前显著下降（各 Task 给出目标）
  4. 覆盖率门禁仍通过（前端 `npx vitest run --coverage`；后端见上方 gate 命令）
- **后端 segfault 规避（Phase 2 已知坑）**：测后端覆盖率时**不要**把 `app.api.v1.endpoints.*` 单列为 `--cov` 目标（py3.13 下触发 asyncpg/aiosqlite 原生 segfault）；用 `--cov=app --cov-config=.coveragerc` 采集后 `coverage report --include=...` 读取。
- 提交信息中文，结尾 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。
- 分支：`quality-hardening-phase3`（从当前 `quality-hardening-phase2` HEAD 创建）。
- 顺序原则：先后端（路由/schema 拆分，seam 清晰、风险低）→ 再前端（hooks 抽取，状态耦合多、风险高），最后可选的 orchestrator + ATOM-01 债务清理。

## 现状事实（执行前已核实，2026-06-27）

| 文件 | 行数 | 重构前覆盖率 | 既有抽取/服务 |
|------|------|------------|--------------|
| `app/api/v1/endpoints/agent.py` | 1214 | 87% | 8 内联 schema + 36 路由（coach/diagnoser/knowledge/evidence/coordinate/execute v2）；handler 多为薄委托 |
| `app/api/v1/endpoints/training.py` | 1038 | 99% | ~25 内联 schema + 20 路由（workbench/session/feedback）；委托 submission_service 等 |
| `app/api/v1/endpoints/teaching.py` | 901 | 94% | 4 schema + 4 helper + 24 路由（guidance/classes/courses/enrollments/assignments/attempts）|
| `src/components/Viewer3D/Atom01Interactive.tsx` | 1207 | 84% | 子组件 SubPartMesh/SubPartsGroup/InteractiveLinkMesh + Atom01Interactive 同文件；大量常量/几何 helper |
| `src/pages/SOPMaintenancePage.tsx` | 1615 | 77% | 表现层已抽到 `SOPMaintenanceShell.tsx`（Header/LeftRail/RightRail/ExamOverlay）；页面仍留状态机+回调+派生 memo+渲染片段 builder |
| `src/components/Maintenance/SOPPlayerAdjudicated.tsx` | 895 | 76% | 执行器生命周期 + action 解析 + 同步 + 控制 handler 全内联 |
| `app/services/orchestrator_v2.py` | 772 | —（Phase2 14-service 门禁内）| TaskFSMState/TaskEventType/TaskContext/ModuleDispatchResult/ModuleRegistry/IdempotencyCache/OrchestratorV2 同文件 |

- Phase 2 特征测试文件：
  - 后端 `tests/unit/test_agent_characterization.py` / `test_training_characterization.py` / `test_teaching_characterization.py`
  - 前端 `src/pages/__tests__/SOPMaintenancePage.characterization.test.tsx` / `src/components/Viewer3D/__tests__/Atom01Interactive.characterization.test.tsx` / `src/components/Maintenance/__tests__/SOPPlayerAdjudicated.characterization.test.tsx`
- 后端门禁：`backend-ci.yml` → `God-file endpoint coverage gate`（`coverage report --include='*/app/api/v1/endpoints/{agent,training,teaching}.py' --fail-under=80`）。
- 前端门禁：`vitest.config.ts` → `coverage.include` + per-file `thresholds`（SOPMaintenancePage 70 / Atom01Interactive 55 / SOPPlayerAdjudicated 70）。

---

### Task 1：`agent.py` 端点瘦身（schema 外置 + 域路由拆分）

**Files:**
- Create: `r-mos-backend/app/schemas/agent.py`（内联请求/响应 schema）
- Create: `r-mos-backend/app/api/v1/endpoints/agent_knowledge.py`（knowledge 域路由 sub-router）
- Create: `r-mos-backend/app/api/v1/endpoints/agent_evidence.py`（evidence 域路由 sub-router）
- Modify: `r-mos-backend/app/api/v1/endpoints/agent.py`（保留 coach/diagnoser/coordinate/execute；include 两个 sub-router）
- Modify: `.github/workflows/backend-ci.yml`（gate `--include` glob 覆盖 `agent*.py`）
- Reference: `tests/unit/test_agent_characterization.py`（安全网）

**Interfaces:**
- Produces: `agent_knowledge.router` / `agent_evidence.router`（`APIRouter()`，**不带 prefix**，沿用各 route 原有的完整路径如 `@router.post("/knowledge/search")`），由 `agent.py` 用 `router.include_router(agent_knowledge.router)` 聚合，**保证最终 URL 与重构前逐字相同**。
- Consumes: 无。

- [ ] **Step 1：重构前建基线**

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
wc -l app/api/v1/endpoints/agent.py
python -m pytest tests/unit/test_agent_characterization.py -o addopts='' -p no:warnings -q
```
Expected: 记录行数（1214）；特征测试全 passed。这是"重构前绿"基准。

- [ ] **Step 2：抽出内联 schema 到 `app/schemas/agent.py`**

把 agent.py 中的内联 `BaseModel` 子类**逐字移动**到新文件 `app/schemas/agent.py`：`CoachRecommendRequest`、`DiagnoseRequest`、`KnowledgeSearchRequest`、`KnowledgeCreateRequest`、`KnowledgeApproveRequest`、`CoordinateRequest`、`EvidenceCollectRequest`、`AgentExecuteMode`(enum)、`AgentExecuteRequest`（以 `grep -nE '^class .*(BaseModel|enum.Enum)' app/api/v1/endpoints/agent.py` 实得清单为准）。新文件顶部补齐它们引用的 import（`pydantic.BaseModel`、`typing`、`enum` 等）。在 `agent.py` 顶部改为 `from app.schemas.agent import (CoachRecommendRequest, ...)`，删除原内联定义。

- [ ] **Step 3：跑特征测试确认行为等价**

Run: `python -m pytest tests/unit/test_agent_characterization.py -o addopts='' -p no:warnings -q`
Expected: 全 passed（schema 仅换了定义位置，行为不变）。

- [ ] **Step 4：拆出 knowledge / evidence sub-router**

新建 `agent_knowledge.py`：`router = APIRouter()`，把 agent.py 中所有 `@router.<m>("/knowledge...")` 路由函数（search/create/upload/upload job/projects/manifest/asset/submit/approve）**逐字移动**过来（连同它们用到的 import 与依赖如 `require_permission`、`get_db`、相关 service）。`agent_evidence.py` 同法收纳 `/evidence/...` 路由。在 `agent.py` 中删除这些函数，改为：
```python
from app.api.v1.endpoints import agent_knowledge, agent_evidence
router.include_router(agent_knowledge.router)
router.include_router(agent_evidence.router)
```
（`agent.py` 仍 `router = APIRouter(...)`，prefix/tags 不变；sub-router 不设 prefix，路径写全。）

- [ ] **Step 5：跑特征测试 + 全量后端测试**

Run:
```bash
python -m pytest tests/unit/test_agent_characterization.py -o addopts='' -p no:warnings -q
python -m pytest -q
```
Expected: 两者全 passed（路径未变 → 特征测试不变即通过；全量确认无 import 破裂）。`wc -l app/api/v1/endpoints/agent.py` 应显著下降（目标 ≤ 600 行）。

- [ ] **Step 6：更新后端覆盖率门禁 glob + 本地验门禁**

在 `.github/workflows/backend-ci.yml` 的 `God-file endpoint coverage gate` 把 agent 项改为通配，确保 sub-router 也被守护：
```yaml
        coverage report \
          --include='*/app/api/v1/endpoints/agent*.py,*/app/api/v1/endpoints/training.py,*/app/api/v1/endpoints/teaching.py' \
          --fail-under=80
```
Run（本地复刻 CI gate，规避 segfault）：
```bash
python -m pytest tests/ -o addopts='' -p no:warnings -q --cov=app --cov-config=.coveragerc >/dev/null 2>&1
coverage report --include='*/app/api/v1/endpoints/agent*.py,*/app/api/v1/endpoints/training.py,*/app/api/v1/endpoints/teaching.py' --fail-under=80
```
Expected: EXIT 0，agent 系列合计仍 ≥80%。

- [ ] **Step 7：提交**

```bash
cd /Users/xuhehong/Desktop/r-mos
git add r-mos-backend/app/schemas/agent.py r-mos-backend/app/api/v1/endpoints/agent.py r-mos-backend/app/api/v1/endpoints/agent_knowledge.py r-mos-backend/app/api/v1/endpoints/agent_evidence.py .github/workflows/backend-ci.yml
git commit -m "refactor(phase3): agent.py 端点瘦身(schema 外置 + knowledge/evidence 拆 sub-router)

行为等价：URL/响应不变，特征测试全绿；门禁 glob 覆盖 agent*.py。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

**验收**：`agent.py` ≤600 行；`test_agent_characterization.py` 全绿；全量后端绿；门禁 ≥80% 且 glob 含 sub-router。

---

### Task 2：`training.py` 端点瘦身（workbench schema 外置 + 路由分域）

**Files:**
- Create: `r-mos-backend/app/schemas/training_workbench.py`（内联 workbench/session/feedback schema）
- Create: `r-mos-backend/app/api/v1/endpoints/training_workbench.py`（workbench 域路由 sub-router）
- Modify: `r-mos-backend/app/api/v1/endpoints/training.py`（保留 session/feedback；include workbench sub-router）
- Modify: `.github/workflows/backend-ci.yml`（gate glob 覆盖 `training*.py`）
- Reference: `tests/unit/test_training_characterization.py`

**Interfaces:**
- Produces: `training_workbench.router`（`APIRouter()` 无 prefix，路径写全），由 `training.py` include。
- Consumes: 无。

- [ ] **Step 1：重构前基线**

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
wc -l app/api/v1/endpoints/training.py
python -m pytest tests/unit/test_training_characterization.py -o addopts='' -p no:warnings -q
```
Expected: 记录 1038；特征测试全 passed。

- [ ] **Step 2：抽出内联 schema 到 `app/schemas/training_workbench.py`**

把 training.py 顶部约 25 个内联 `BaseModel`（`Session*`/`StepRecordResponse`/`StepUpdateRequest`/`Project*`/`Workbench*`/`SubmitSession*`/`SkillProfileResponse`/`WeakStepResponse`/`FeedbackResponse` 等——以 `grep -nE '^class .*BaseModel' app/api/v1/endpoints/training.py` 实得清单为准）**逐字移动**到新 schema 文件，补 import；`training.py` 改为 `from app.schemas.training_workbench import (...)`。保留模块级私有 helper `_build_workbench_project_snapshot` 暂留 training.py（除非它只被 workbench 路由用，则随 Step 4 一起搬）。

- [ ] **Step 3：跑特征测试**

Run: `python -m pytest tests/unit/test_training_characterization.py -o addopts='' -p no:warnings -q`
Expected: 全 passed。

- [ ] **Step 4：拆出 workbench sub-router**

新建 `training_workbench.py`：`router = APIRouter()`，移动 `@router.post("/.../workbench...")` 系列路由（generate draft / upload evidence / submit step / ask assistant 等，以 `grep -n 'workbench' app/api/v1/endpoints/training.py` 定位）+ 它们独占的 helper（如 `_build_workbench_project_snapshot`，若仅 workbench 用）。`training.py` 删除并 `router.include_router(training_workbench.router)`。

- [ ] **Step 5：特征测试 + 全量**

Run:
```bash
python -m pytest tests/unit/test_training_characterization.py -o addopts='' -p no:warnings -q
python -m pytest -q
```
Expected: 全 passed；`wc -l training.py` 目标 ≤ 600 行。

- [ ] **Step 6：更新门禁 glob + 验证**

`backend-ci.yml` gate `--include` 把 training 项改 `*/app/api/v1/endpoints/training*.py`。本地：
```bash
python -m pytest tests/ -o addopts='' -p no:warnings -q --cov=app --cov-config=.coveragerc >/dev/null 2>&1
coverage report --include='*/app/api/v1/endpoints/agent*.py,*/app/api/v1/endpoints/training*.py,*/app/api/v1/endpoints/teaching.py' --fail-under=80
```
Expected: EXIT 0。

- [ ] **Step 7：提交**

```bash
git add r-mos-backend/app/schemas/training_workbench.py r-mos-backend/app/api/v1/endpoints/training.py r-mos-backend/app/api/v1/endpoints/training_workbench.py .github/workflows/backend-ci.yml
git commit -m "refactor(phase3): training.py 端点瘦身(schema 外置 + workbench 拆 sub-router)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

**验收**：`training.py` ≤600 行；特征测试全绿；全量绿；门禁 ≥80% 含 training*.py。

---

### Task 3：`teaching.py` 端点瘦身（schema/helper 外置 + 路由分域）

**Files:**
- Create: `r-mos-backend/app/schemas/teaching.py`（内联 schema：`AttemptCreateRequest`/`AttemptStatusUpdateRequest`/`AttemptGradeRequest`/`ClassUpdateRequest`）
- Create: `r-mos-backend/app/api/v1/endpoints/teaching_roster.py`（classes/courses/enrollments/assignments/attempts 路由）
- Modify: `r-mos-backend/app/api/v1/endpoints/teaching.py`（保留 guidance policy 路由 + 共享 helper；include roster sub-router）
- Modify: `.github/workflows/backend-ci.yml`（gate glob 覆盖 `teaching*.py`）
- Reference: `tests/unit/test_teaching_characterization.py`

**Interfaces:**
- Produces: `teaching_roster.router`（`APIRouter()` 无 prefix，路径写全）。
- Consumes: 共享 helper `_raise_business_error`/`_raise_not_found`/`_parse_user_id`/`_to_int_or_none` —— 移到 `teaching.py` 顶部并 `from app.api.v1.endpoints.teaching import _raise_business_error, ...` 供 roster 用；或更干净地放到新建 `app/api/v1/endpoints/teaching_common.py` 由两边 import（推荐后者，避免循环）。

- [ ] **Step 1：重构前基线**

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
wc -l app/api/v1/endpoints/teaching.py
python -m pytest tests/unit/test_teaching_characterization.py -o addopts='' -p no:warnings -q
```
Expected: 记录 901；全 passed。

- [ ] **Step 2：抽 schema + 共享 helper**

4 个内联 `BaseModel` → `app/schemas/teaching.py`。4 个 helper（`_raise_business_error`/`_raise_not_found`/`_parse_user_id`/`_to_int_or_none`）→ 新建 `app/api/v1/endpoints/teaching_common.py`。`teaching.py` 改 import 引用两者。

- [ ] **Step 3：特征测试**

Run: `python -m pytest tests/unit/test_teaching_characterization.py -o addopts='' -p no:warnings -q`
Expected: 全 passed。

- [ ] **Step 4：拆 roster sub-router**

新建 `teaching_roster.py`：移动 classes/courses/enrollments/assignments/attempts 全部路由（保留 guidance policy 三个路由在 `teaching.py`），从 `teaching_common` import helper。`teaching.py` 删除并 `router.include_router(teaching_roster.router)`。

- [ ] **Step 5：特征测试 + 全量**

Run:
```bash
python -m pytest tests/unit/test_teaching_characterization.py -o addopts='' -p no:warnings -q
python -m pytest -q
```
Expected: 全 passed；`wc -l teaching.py` 目标 ≤ 450 行。

- [ ] **Step 6：门禁 glob + 验证**

`backend-ci.yml` gate `--include` 改 `*/app/api/v1/endpoints/teaching*.py`（注意 `teaching_common.py` 也被包含——它含 helper，覆盖率高，无碍）。本地：
```bash
python -m pytest tests/ -o addopts='' -p no:warnings -q --cov=app --cov-config=.coveragerc >/dev/null 2>&1
coverage report --include='*/app/api/v1/endpoints/agent*.py,*/app/api/v1/endpoints/training*.py,*/app/api/v1/endpoints/teaching*.py' --fail-under=80
```
Expected: EXIT 0。

- [ ] **Step 7：提交**

```bash
git add r-mos-backend/app/schemas/teaching.py r-mos-backend/app/api/v1/endpoints/teaching.py r-mos-backend/app/api/v1/endpoints/teaching_roster.py r-mos-backend/app/api/v1/endpoints/teaching_common.py .github/workflows/backend-ci.yml
git commit -m "refactor(phase3): teaching.py 端点瘦身(schema/helper 外置 + roster 拆 sub-router)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

**验收**：`teaching.py` ≤450 行；特征测试全绿；全量绿；门禁 ≥80% 含 teaching*.py。

---

### Task 4：`Atom01Interactive.tsx` 按子组件边界拆分

**Files:**
- Create: `src/components/Viewer3D/atom01/atom01Constants.ts`（PART_METADATA、tuning 表、EXPLODE_OFFSETS、JOINTS/JOINTS_AXIS_FALLBACK、阈值常量）
- Create: `src/components/Viewer3D/atom01/atom01Geometry.ts`（`clamp01`/`smoothstep`/`getLinkExplodeAxis` 等纯函数 + `CATEGORY_PRIORITY`）
- Create: `src/components/Viewer3D/atom01/SubPartMesh.tsx`、`SubPartsGroup.tsx`、`InteractiveLinkMesh.tsx`
- Modify: `src/components/Viewer3D/Atom01Interactive.tsx`（仅保留 `Atom01Interactive` 主组件 + `PartInfo`/`Atom01InteractiveProps` + re-export `PART_METADATA`）
- Modify: `r-mos-frontend/vitest.config.ts`（coverage.include + thresholds 追加新文件）
- Reference: `src/components/Viewer3D/__tests__/Atom01Interactive.characterization.test.tsx`

**Interfaces:**
- Produces:
  - `atom01Constants.ts`: `export const PART_METADATA`、`EXPLODE_OFFSETS`、`JOINTS`、`JOINTS_AXIS_FALLBACK`、`DEFAULT_SUBPART_TUNING`、`LINK_SUBPART_TUNING`、`SUBPART_OUTLIER_ABS_MAX_DIM`、`CORE_OUTLIER_ABS_MAX_DIM`、`PARTS_GLB_BASE`
  - `atom01Geometry.ts`: `export const clamp01`、`smoothstep`、`CATEGORY_PRIORITY`；`export function getLinkExplodeAxis`
  - `SubPartMesh.tsx`: `export const SubPartMesh`（props 形状逐字保留：`{ part: DetailPart, gltf: any, isHovered: boolean, opacity: number }`）
  - `SubPartsGroup.tsx`: `export const SubPartsGroup`（props 逐字保留）
  - `InteractiveLinkMesh.tsx`: `export const InteractiveLinkMesh`（props 逐字保留）
- Consumes: `Atom01Interactive.tsx` 从上述模块 import；`src/components/Viewer3D/manifestHelpers`、`./partsManifest`、`./hooks/useAtom01AssemblyData`、`./Atom01AssemblyRenderer` 等既有依赖保持不变。
- **对外契约不变**：`Atom01Interactive.tsx` 仍 `export const Atom01Interactive`、`export default Atom01Interactive`、`export { PART_METADATA }`（从 constants re-export），`export interface PartInfo`、`Atom01InteractiveProps`。外部 import 路径不变。

- [ ] **Step 1：重构前基线**

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend
wc -l src/components/Viewer3D/Atom01Interactive.tsx
npx vitest run src/components/Viewer3D/__tests__/Atom01Interactive.characterization.test.tsx
```
Expected: 记录 1207；测试全 passed。

- [ ] **Step 2：抽常量与几何纯函数**

把常量（PART_METADATA 等，见 Interfaces 清单）逐字移到 `atom01/atom01Constants.ts`，纯函数移到 `atom01/atom01Geometry.ts`。`Atom01Interactive.tsx` 顶部改为 `import { ... } from './atom01/atom01Constants'` / `'./atom01/atom01Geometry'`，并在文件尾保持 `export { PART_METADATA }`（re-export，维持外部契约）。

- [ ] **Step 3：跑测试（常量/函数搬迁后）**

Run: `npx vitest run src/components/Viewer3D/__tests__/Atom01Interactive.characterization.test.tsx`
Expected: 全 passed（注意特征测试 mock 的是 `@/components/Viewer3D/Atom01Interactive` 的 `PART_METADATA` re-export，仍有效）。

- [ ] **Step 4：抽三个子组件**

`SubPartMesh`（原 166-232）、`SubPartsGroup`（原 243-510）、`InteractiveLinkMesh`（原 539-748）逐字移到各自 `.tsx`，补 import（THREE、drei `useGLTF`/`Line`、fiber `useFrame`/`ThreeEvent`、constants、geometry、partsManifest 等）。`Atom01Interactive.tsx` 改为 `import { InteractiveLinkMesh } from './atom01/InteractiveLinkMesh'`（主组件只直接用 InteractiveLinkMesh 与 SubPartsGroup；SubPartMesh 由 SubPartsGroup 内部 import）。

- [ ] **Step 5：测试 + tsc + eslint**

Run:
```bash
npx vitest run src/components/Viewer3D/__tests__/Atom01Interactive.characterization.test.tsx
npx tsc --noEmit
npx eslint src/components/Viewer3D/Atom01Interactive.tsx src/components/Viewer3D/atom01 --max-warnings 0
```
Expected: 全绿；`wc -l Atom01Interactive.tsx` 目标 ≤ 450 行。

- [ ] **Step 6：更新前端覆盖率门禁 + 验证**

在 `vitest.config.ts` 的 `coverage.include` 追加新文件，`thresholds` 给新子组件/几何文件加行阈值（3D 渲染件沿用 55；纯函数 `atom01Geometry.ts` 可设 80）：
```ts
      include: [
        'src/pages/SOPMaintenancePage.tsx',
        'src/components/Viewer3D/Atom01Interactive.tsx',
        'src/components/Viewer3D/atom01/SubPartMesh.tsx',
        'src/components/Viewer3D/atom01/SubPartsGroup.tsx',
        'src/components/Viewer3D/atom01/InteractiveLinkMesh.tsx',
        'src/components/Viewer3D/atom01/atom01Geometry.ts',
        'src/components/Maintenance/SOPPlayerAdjudicated.tsx',
      ],
      thresholds: {
        'src/pages/SOPMaintenancePage.tsx': { lines: 70 },
        'src/components/Viewer3D/Atom01Interactive.tsx': { lines: 55 },
        'src/components/Viewer3D/atom01/SubPartMesh.tsx': { lines: 55 },
        'src/components/Viewer3D/atom01/SubPartsGroup.tsx': { lines: 55 },
        'src/components/Viewer3D/atom01/InteractiveLinkMesh.tsx': { lines: 55 },
        'src/components/Viewer3D/atom01/atom01Geometry.ts': { lines: 80 },
        'src/components/Maintenance/SOPPlayerAdjudicated.tsx': { lines: 70 },
      },
```
Run: `npx vitest run --coverage`（全量）
Expected: EXIT 0，各阈值通过。**若某子组件实测 < 55**：在特征测试里补 1-2 个针对该子组件路径的渲染/回调用例（仍属 Phase 3 安全网维护），不得下调阈值掩盖。

- [ ] **Step 7：提交**

```bash
cd /Users/xuhehong/Desktop/r-mos
git add r-mos-frontend/src/components/Viewer3D/Atom01Interactive.tsx r-mos-frontend/src/components/Viewer3D/atom01 r-mos-frontend/vitest.config.ts
git commit -m "refactor(phase3): Atom01Interactive 按子组件边界拆分(常量/几何/3子组件)

行为等价：对外 export 契约不变，特征测试全绿。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

**验收**：`Atom01Interactive.tsx` ≤450 行；特征测试全绿；tsc/eslint 绿；门禁含新文件且通过。

---

### Task 5：`SOPMaintenancePage.tsx` 抽 hooks + 渲染下沉

**Files:**
- Create: `src/pages/sopMaintenance/sopMaintenanceConfig.ts`（常量/类型：相机 preset、`GROUP_NAMES`、`UPPER_BODY_CORE_LINKS`/`REMAINING_CORE_LINKS`、`WORKSPACE_CHROME`、`SOP_EXECUTION_STATE_*`、`buildLinkGroupsFromManifest`、`resolveScrewSpecIdFromDetailPart`、类型 `ViewState`/`BreadcrumbItem`/`WorkspaceVariant`/`MaintenanceLayoutMode`）
- Create: `src/pages/sopMaintenance/useSOPViewState.ts`（视图/隔离态状态机 hook）
- Create: `src/pages/sopMaintenance/useSOPPlaybackBridge.ts`（SOP 播放器回调桥 + 考试总结 hook）
- Create: `src/pages/sopMaintenance/useRuntimeDraft.ts`（runtime 草案/manifest hook）
- Modify: `src/pages/SOPMaintenancePage.tsx`（消费三个 hook + 组装 Shell；渲染片段 builder 尽量内联精简或下沉到 Shell 子组件）
- Modify: `r-mos-frontend/vitest.config.ts`（coverage.include + thresholds 追加三 hook）
- Reference: `src/pages/__tests__/SOPMaintenancePage.characterization.test.tsx`

**Interfaces:**
- Produces（hook 返回值即对页面的契约；页面行为不变，故 hook 须暴露页面当前所有用到的 state/函数）：
  - `useSOPViewState(partMetadata, manifestLinkGroups, isolationSets)` → `{ viewState, isolationLevel, selectedOverviewNode, breadcrumbPath, selectedPart, hoveredPart, l2TargetLink, l2SelectedPartIdx, viewMode, explodeAmount, cameraPreset, focusTarget, enterIsolation, enterL2, resetToOverview, navigateBreadcrumb, handlePartSelect, handleSubPartSelect, handlePartHover, handleSubPartHover, handlePartDoubleClick, handleVisibleBoundsChange, setViewMode, setExplodeAmount, ... }`（以页面实际使用面为准，逐一搬迁对应 `useState`/`useCallback`/`useMemo`）
  - `useSOPPlaybackBridge({ viewState, selectedOverviewNode, enterIsolation, resetToOverview, partMetadata, sopSceneSync, runtimeManifest, ... })` → `{ handleSOPChange, handleSOPStepChange, handleSOPContextChange, handleSOPBlocked, handleSOPPartSelect, handleSOPToolRequired, handleSummarize, handleResetExam, examSummaryReport, scoreState, applySOPIntent, ... }`
  - `useRuntimeDraft(workspaceVariant)` → `{ runtimeDraft, runtimeManifest, runtimeSopScript, runtimeTargetIds, runtimeSelectedAssetPath, applyRuntimeDraft, runtimePreviewAssetPath, runtimePreviewAssetUrl }`
- Consumes: `sopMaintenanceConfig` 常量；既有 `@/adjudication`、`useSOPSceneSync`、`useSOPScripts`、`useAssemblyManifest`、`SOPMaintenanceShell` 等保持不变。
- **对外契约不变**：`SOPMaintenancePage` 仍 `export default`、props `{ workspaceVariant?, layoutMode? }` 不变。

> **重构注意（高耦合）**：本页面 state 互相依赖（如 `applySOPIntent` 调 `enterIsolation`；`handleVisibleBoundsChange` 读 `viewState`/`selectedOverviewNode`）。抽 hook 时按"数据流向"切：`useSOPViewState` 是底座（被别人依赖），`useSOPPlaybackBridge` 依赖它（通过参数注入 enterIsolation/resetToOverview 等）。**逐个 hook 抽、每抽一个就跑特征测试**，避免一次性大改难定位回归。

- [ ] **Step 1：重构前基线**

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend
wc -l src/pages/SOPMaintenancePage.tsx
npx vitest run src/pages/__tests__/SOPMaintenancePage.characterization.test.tsx
```
Expected: 记录 1615；测试全 passed。

- [ ] **Step 2：抽 config 模块**

常量/类型/纯函数（见 Files 清单）逐字移到 `sopMaintenance/sopMaintenanceConfig.ts`，页面改 import。跑特征测试确认绿。
Run: `npx vitest run src/pages/__tests__/SOPMaintenancePage.characterization.test.tsx` → 全 passed。

- [ ] **Step 3：抽 `useRuntimeDraft`（最独立，先抽）**

把 runtime 相关 `useState` + `applyRuntimeDraft` + `runtimeSopScript`/`availableSopScripts` 中 runtime 部分 + 资产路径 `useMemo` 搬进 hook，页面改用返回值。跑特征测试 → 全 passed。

- [ ] **Step 4：抽 `useSOPViewState`（底座状态机）**

把 viewState/isolation 全套 `useState` + enterIsolation/enterL2/resetToOverview/navigateBreadcrumb/handlePartSelect/handleSubPart*/handlePartHover/handlePartDoubleClick/handleVisibleBoundsChange + 相关派生 `useMemo`（visibleLinks/clickableLinks/.../l2DetailParts/isolationSets）搬进 hook。页面以 `const view = useSOPViewState(...)` 消费。跑特征测试 → 全 passed（此 Task 风险最高，务必单独跑确认）。

- [ ] **Step 5：抽 `useSOPPlaybackBridge`**

把 handleSOP*（Change/StepChange/ContextChange/Blocked/PartSelect/ToolRequired）+ applySOPIntent + handleSummarize/handleResetExam + 考试计时/总结 state 搬进 hook（依赖 Step 4 的 enterIsolation/resetToOverview 经参数注入）。跑特征测试 → 全 passed。

- [ ] **Step 6：精简渲染片段 + tsc/eslint**

页面剩余的 render builder（`headerViewModeControl`/`quickSelectControl`/`diagnosisContent`/`partPanel`/`leftRail*Content`）：能直接内联进 return 的内联，逻辑较重的（如 `partPanel`）可作为页面内 `const` 保留——目标是页面文件聚焦"组装"。
Run:
```bash
npx vitest run src/pages/__tests__/SOPMaintenancePage.characterization.test.tsx
npx tsc --noEmit
npx eslint src/pages/SOPMaintenancePage.tsx src/pages/sopMaintenance --max-warnings 0
```
Expected: 全绿；`wc -l SOPMaintenancePage.tsx` 目标 ≤ 700 行。

- [ ] **Step 7：更新前端门禁 + 验证 + 提交**

`vitest.config.ts` 的 `coverage.include`/`thresholds` 追加三 hook（页面阈值仍 70；hook 文件设 70）。
Run: `npx vitest run --coverage` → EXIT 0（若某 hook < 70，补特征测试用例，不下调阈值）。
```bash
cd /Users/xuhehong/Desktop/r-mos
git add r-mos-frontend/src/pages/SOPMaintenancePage.tsx r-mos-frontend/src/pages/sopMaintenance r-mos-frontend/vitest.config.ts
git commit -m "refactor(phase3): SOPMaintenancePage 抽 hooks(viewState/playbackBridge/runtimeDraft)+config

行为等价：对外 props/默认行为不变，特征测试全绿。

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

**验收**：`SOPMaintenancePage.tsx` ≤700 行；特征测试全绿；tsc/eslint 绿；门禁含三 hook 且通过。

---

### Task 6：`SOPPlayerAdjudicated.tsx` 抽执行器桥 + action 解析

**Files:**
- Create: `src/components/Maintenance/sopPlayer/sopPlayerConfig.ts`（`StepIcon`/`ExecutionStateColor`/`ExecutionStateText`/`PART_TARGET_ALIASES`/`buildPartTargetAliases`/`difficultyColor`）
- Create: `src/components/Maintenance/sopPlayer/useSOPExecutorBridge.ts`（执行器生命周期 + context + 回调发射 hook）
- Create: `src/components/Maintenance/sopPlayer/useSOPActionResolver.ts`（`normalizeSpec`/`resolveScrewTargetId`/`resolvePartTargetId`/`handleActionEvent` + action 事件 effect）
- Modify: `src/components/Maintenance/SOPPlayerAdjudicated.tsx`（消费两个 hook + 渲染 + 控制 handler）
- Modify: `r-mos-frontend/vitest.config.ts`（coverage.include + thresholds 追加两 hook）
- Reference: `src/components/Maintenance/__tests__/SOPPlayerAdjudicated.characterization.test.tsx`

**Interfaces:**
- Produces:
  - `sopPlayerConfig.ts`: `export const StepIcon`、`ExecutionStateColor`、`ExecutionStateText`、`PART_TARGET_ALIASES`、`difficultyColor`；`export function buildPartTargetAliases`（保持现有 export，外部若引用不破）
  - `useSOPExecutorBridge(props 回调集 + operationMode)` → `{ selectedSOP, executor, context, lastReport, showBlockedModal, setShowBlockedModal, createExecutor, clearSelection, handleSelectSOP, setLastReport, ... }`
  - `useSOPActionResolver({ currentStep })` → `{ handleActionEvent, resolveScrewTargetId, resolvePartTargetId, normalizeSpec }`（action 事件推进 effect 留在组件或随 executor bridge，以最小耦合为准）
- Consumes: `sopPlayerConfig`；既有 `@/adjudication`（createSOPExecutor 等）、`@/api/pipeline`、`@/components/AIAssistant/AIAssistantPanel` 不变。
- **对外契约不变**：`SOPPlayerAdjudicated` 仍 `export const SOPPlayerAdjudicated`、props 接口 `SOPPlayerAdjudicatedProps` 与 `SOPActionEvent`/`SOPActionEventType` 类型 export 不变。

- [ ] **Step 1：重构前基线**

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend
wc -l src/components/Maintenance/SOPPlayerAdjudicated.tsx
npx vitest run src/components/Maintenance/__tests__/SOPPlayerAdjudicated.characterization.test.tsx
```
Expected: 记录 895；全 passed。

- [ ] **Step 2：抽 config**

常量/别名表/`buildPartTargetAliases`/`difficultyColor` 逐字移到 `sopPlayer/sopPlayerConfig.ts`，组件改 import。跑特征测试 → 全 passed。

- [ ] **Step 3：抽 `useSOPActionResolver`**

`normalizeSpec`/`resolveScrewTargetId`/`resolvePartTargetId`/`handleActionEvent` 搬进 hook（依赖 `commitScrewExtraction` 等从 `@/adjudication` import 进 hook 文件）。组件消费返回的 `handleActionEvent`。跑特征测试 → 全 passed。

- [ ] **Step 4：抽 `useSOPExecutorBridge`**

`selectedSOP`/`executor`/`context`/`lastReport`/`showBlockedModal` state + `createExecutor`/`clearSelection`/`handleSelectSOP` + 相关 `useEffect`（selectedSOPId 同步、initialSopId 自动选择）搬进 hook，回调（onStepChange/onBlocked/...）经参数注入。组件 `const player = useSOPExecutorBridge(...)` 消费。跑特征测试 → 全 passed（含阻断/EXECUTING 用例）。

- [ ] **Step 5：tsc + eslint + 行数**

Run:
```bash
npx vitest run src/components/Maintenance/__tests__/SOPPlayerAdjudicated.characterization.test.tsx
npx tsc --noEmit
npx eslint src/components/Maintenance/SOPPlayerAdjudicated.tsx src/components/Maintenance/sopPlayer --max-warnings 0
```
Expected: 全绿；`wc -l SOPPlayerAdjudicated.tsx` 目标 ≤ 450 行。

- [ ] **Step 6：门禁 + 验证 + 提交**

`vitest.config.ts` 追加两 hook（阈值 70）。`npx vitest run --coverage` → EXIT 0。
```bash
cd /Users/xuhehong/Desktop/r-mos
git add r-mos-frontend/src/components/Maintenance/SOPPlayerAdjudicated.tsx r-mos-frontend/src/components/Maintenance/sopPlayer r-mos-frontend/vitest.config.ts
git commit -m "refactor(phase3): SOPPlayerAdjudicated 抽 hooks(executorBridge/actionResolver)+config

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

**验收**：`SOPPlayerAdjudicated.tsx` ≤450 行；特征测试全绿；tsc/eslint 绿；门禁含两 hook 且通过。

---

### Task 7（可选）：`orchestrator_v2.py` 模块梳理

> Spec 标注"视情况一并梳理"。若 Task 1-6 后时间/风险可控则做；否则可推迟到 Phase 4 后。orchestrator_v2 在 Phase 2 的 14-service 门禁内（≥70%），重构后须保持该门禁。

**Files:**
- Create: `r-mos-backend/app/services/orchestration/fsm.py`（`TaskFSMState`/`TaskEventType`/`TaskContext`/`ModuleDispatchResult`）
- Create: `r-mos-backend/app/services/orchestration/module_registry.py`（`ModuleRegistry`）
- Create: `r-mos-backend/app/services/orchestration/idempotency.py`（`IdempotencyCache`）
- Modify: `r-mos-backend/app/services/orchestrator_v2.py`（仅留 `OrchestratorV2`，从上述模块 import；保持 `from app.services.orchestrator_v2 import OrchestratorV2` 等外部 import 路径有效）

**Interfaces:**
- Produces: 各类型/类逐字移动，名称不变；`orchestrator_v2.py` re-export 以维持现有 import 路径（`from app.services.orchestrator_v2 import TaskFSMState` 仍可用——在 orchestrator_v2.py 顶部 `from app.services.orchestration.fsm import TaskFSMState, ...`）。
- Consumes: 现有调用方不改。

- [ ] **Step 1：基线**

Run: `cd r-mos-backend && wc -l app/services/orchestrator_v2.py && python -m pytest -q -k orchestrat`
Expected: 记录 772；相关测试全 passed。

- [ ] **Step 2：抽 fsm/registry/idempotency 三模块**

逐字移动对应类，`orchestrator_v2.py` 顶部 re-export 维持外部 import 路径。

- [ ] **Step 3：全量 + 14-service 门禁**

Run:
```bash
python -m pytest -q
python -m pytest tests/ -o addopts='' -q --cov=app.services.orchestrator_v2 --cov-fail-under=70 2>&1 | tail -3
```
Expected: 全 passed；orchestrator_v2 覆盖率 ≥70%（注意：现门禁按模块名 `app.services.orchestrator_v2` 计，类移出后该模块只剩 OrchestratorV2，覆盖率可能变化——若 <70%，把 `orchestration.*` 三模块一并加入 `backend-ci.yml` 14-service gate 的 `--cov=` 列表，使整体守护不缩水）。`wc -l orchestrator_v2.py` 目标 ≤ 450 行。

- [ ] **Step 4：提交**

```bash
git add r-mos-backend/app/services/orchestrator_v2.py r-mos-backend/app/services/orchestration .github/workflows/backend-ci.yml
git commit -m "refactor(phase3): orchestrator_v2 拆分(fsm/registry/idempotency 模块)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

**验收**：`orchestrator_v2.py` ≤450 行；全量绿；orchestration 模块纳入 14-service 门禁且 ≥70%。

---

### Task 8：ATOM-01 硬编码债务清理 + Phase 3 收尾

> Spec："顺带清理残留的 ATOM-01 硬编码债务（与多机器人目标收尾）"。范围限定为**重构期顺手发现、且可安全删除/参数化的**残留硬编码（如已被 manifest 替代的 `@deprecated` 兜底常量、写死的 `robotId === 1` 分支）。不扩大为新功能。

**Files:**
- Modify: 视实际发现而定（候选：Task 4/5 抽出的 `atom01Constants.ts`、`sopMaintenanceConfig.ts` 中标 `@deprecated` 的 fallback；`SOPPlayerAdjudicated` 的 `PART_TARGET_ALIASES`）
- Modify: `CLAUDE.md`、`docs/superpowers/plans/2026-06-22-quality-hardening-master-plan.md`、记忆

- [ ] **Step 1：盘点残留硬编码**

Run:
```bash
cd /Users/xuhehong/Desktop/r-mos
grep -rnE '@deprecated|ATOM-01|atom01|robotId === 1|hardcod|硬编码' r-mos-frontend/src r-mos-backend/app --include='*.ts' --include='*.tsx' --include='*.py' | grep -iE 'deprecated|硬编码|fallback|hardcod' | head -40
```
逐条判断：**已被 manifest/config 取代且无引用** → 删；**仍是必要 fallback** → 保留并确认注释准确。**不删有真实引用的兜底**（多机器人 manifest 尚不完整时仍需）。

- [ ] **Step 2：执行可安全清理项 + 全量验证**

仅清理确认无引用的死代码。每删一处跑相关特征测试：
```bash
cd r-mos-frontend && npx vitest run && npx tsc --noEmit && npx eslint src/ --ext .ts,.tsx --max-warnings 0
cd ../r-mos-backend && python -m pytest -q
```
Expected: 全绿（删的是死代码，行为不变）。

- [ ] **Step 3：Phase 3 收尾文档 + 记忆**

- 更新总控计划 `2026-06-22-quality-hardening-master-plan.md`：Phase 3 → ✅ Done。
- 更新 `CLAUDE.md`：如有文件路径指向变化（新增 `app/schemas/agent.py`、`atom01/`、`sopMaintenance/`、`sopPlayer/` 等），校正"Key Files"链接。
- 更新记忆 `project_quality_hardening.md`：Phase 3 完成、各文件行数前/后。

- [ ] **Step 4：提交**

```bash
git add -A
git commit -m "chore(phase3): ATOM-01 硬编码债务清理 + Phase 3 收尾(文档/记忆)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

**验收**：无新增死代码告警；全量前后端绿；总控计划/CLAUDE.md/记忆已更新。

---

## Phase 3 收尾（最后一个 Task 完成后）

- [ ] 全量复验：后端 `pytest -q` 全绿 + 两个覆盖率门禁通过；前端 `vitest run --coverage` 达阈值 + `tsc`/`eslint` 绿。
- [ ] 6（+1）文件行数前/后对比表（目标：endpoints 各 ≤600/≤450；Atom01 ≤450；SOPMaintenancePage ≤700；SOPPlayer ≤450；orchestrator ≤450）。
- [ ] 更新总控计划 Phase 3 → ✅ Done；更新记忆。
- [ ] 中文汇报：行数下降 + 行为等价（特征测试全程绿）+ 安全网门禁随代码迁移已扩展，可进入 Phase 4（性能硬化）。

## 自检（计划编写完成后）

- **Spec 覆盖**：Spec Phase 3 前端三文件 → Task 4/5/6；后端 agent/training/teaching → Task 1/2/3；orchestrator_v2"视情况" → Task 7（可选）；"ATOM-01 硬编码债务" → Task 8。验收"行数下降+职责单一+测试全绿+无新增 lint/type" → 每 Task 四件套验证 + 收尾复验。
- **占位符**：无 TBD。重构类步骤以"逐字移动指定 symbol + 修正 import + 跑特征测试"为可执行单元，给出每个 symbol 名/原始行段/目标文件/验证命令/行数目标。
- **一致性**：特征测试文件名、门禁命令（前端 vitest thresholds、后端 coverage report --include glob）、segfault 规避方式跨 Task 一致；"安全网随代码移动"在 Global Constraints 与每个迁移 Task 的门禁更新步骤双重落实。
- **关键风险已显式处理**：(a) 路由拆分必须保持 URL 逐字不变（sub-router 无 prefix、路径写全）；(b) 代码移出门禁文件必须同步扩展门禁 glob/include，否则安全网缩水；(c) 后端覆盖率采集禁用端点单列 --cov（segfault）；(d) SOPMaintenancePage 高耦合 → 按数据流向逐 hook 抽、每抽即测。
