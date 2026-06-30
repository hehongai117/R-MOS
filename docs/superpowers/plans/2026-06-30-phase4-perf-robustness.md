# Phase 4：性能与健壮性硬化（先测量后优化）— 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development（逐 Task 派发 + 任务间 review）实施。健壮性 Task 走 TDD（先红后绿）；测量 Task 产出可运行脚本 + runbook；优化在基线就绪后另起子计划。步骤用 checkbox（`- [ ]`）跟踪。
>
> 设计 Spec：`docs/superpowers/specs/2026-06-22-quality-hardening-upgrade-design.md`（Phase 4）
> 总控计划：`docs/superpowers/plans/2026-06-22-quality-hardening-master-plan.md`
> 用户决策（2026-06-30）：**健壮性优先**；性能测量做成"可在真实环境运行的工具 + runbook"，由用户跑出基线后再写优化子计划（避免臆测式优化）。

**Goal:** 在不改变正确功能的前提下，(A) 补齐前端健壮性短板（路由级错误边界、API 瞬时失败重试、3D 视图降级、AI 管线失败态），(B) 交付一套可复现的性能测量工具与 runbook + 基线文档骨架，(C) 把"依据基线的针对性优化"留作基线就绪后的子计划。

**Architecture:** 健壮性是**附加式**改动（新增 fallback/retry/降级 UI），复用既有 `ErrorBoundary`/`Viewer3DErrorBoundary` 与 axios 拦截器，走 TDD。测量是**新增脚本/文档**，不改产品代码：Lighthouse CLI、chrome-devtools trace runbook、WebSocket 时延探针、AI 管线计时，统一写入基线文档模板。优化任务在拿到真实基线后才具体化。

**Tech Stack:** 前端 React + TypeScript + vitest + @testing-library；axios；测量用 Lighthouse CLI / `@vitest` 无关的独立 node 脚本 / chrome-devtools；后端可选 timing 中间件（FastAPI）。

## 现状事实（执行前已核实，2026-06-30）

- **已有健壮性基建**（复用，勿重造）：
  - `src/components/common/ErrorBoundary.tsx`：`ErrorBoundary`（props `fallbackTitle`/`fallbackMessage`/`onError`，有"重试"按钮重置 state）+ `Viewer3DErrorBoundary`（3D/WebGL 文案预置）。
  - `src/hooks/useWebSocket.ts`：**已很健壮**（指数退避+jitter、ping/pong、stale 检测、`WS_MAX_RETRIES=10`、手动 `reconnect`）。WebSocket 健壮性**无需再做**，仅纳入测量。
  - `src/api/client.ts`：axios 实例 `timeout:30000`；响应拦截器有 **401 刷新重试**（`_retry` 一次性）+ 错误 `message.error`（区分 response/request/config）。**无瞬时失败(5xx/网络)重试与退避**。
  - `src/App.tsx`：路由用 `withSuspense`（懒加载 Suspense fallback `RouteFallback`），**但无任何 ErrorBoundary**——任一页面渲染抛错 = **整页白屏**。
- **健壮性短板**（本 Phase 目标）：
  1. App/路由级无 ErrorBoundary（白屏风险）——最高优先。
  2. API 客户端无瞬时失败重试/退避。
  3. SOP 维护页 3D 视图（`SOPViewerScene`/`Atom01Interactive`/`InteractiveManifestViewer`）未被 `Viewer3DErrorBoundary` 包裹（只有 `MonitorPage` 包了）。
  4. AI 管线调用（`src/api/{training,aiAssistant,pipeline,agent}.ts`）失败/超时态需审计补齐。
- **测量现状**：仓库**无任何** perf/lighthouse 脚本；前端 vitest setup 在 `src/test-setup.ts`。
- **基线全绿**：前端 432 passed/2 skipped（含 Phase 2/3 特征测试）；后端 657 passed/3 skipped。本 Phase 不得打破。

## Global Constraints

- **不破坏既有行为与测试**：前端全量 `vitest` + 后端 `pytest tests/ --ignore=tests/e2e` 必须保持全绿；Phase 2/3 的 6 套特征测试断言一字不改。
- **健壮性 = 附加式 + TDD**：每个健壮性 Task 先写失败测试（红）→ 实现到绿。新增降级 UI/重试不得改变成功路径的可观测行为（成功响应仍照常渲染）。
- **测量不改产品代码**：测量 Task 只新增 `scripts/` 脚本、runbook、文档；如需后端 timing，用可开关的中间件且默认关闭，不影响现有响应体。
- **先测量后优化（硬约束）**：本计划**不含**具体优化代码。优化在用户跑出基线、Task C1 checkpoint 分析后，另起 `docs/superpowers/plans/<date>-phase4b-optimizations.md` 子计划。任何"顺手优化"都属违规臆测。
- **前端 coverage 门禁**：本 Phase 新增的产品代码（错误边界 wiring、retry 逻辑）若落在已门禁文件外，按 Phase 3 惯例评估是否纳入 `vitest.config.ts`（新工具/降级组件可不纳入，逻辑性 util 建议纳入）。
- 提交信息中文，结尾 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。
- 分支：`quality-hardening-phase4`（从当前 `quality-hardening-phase2` HEAD 创建——Phase 3 已并入该分支）。

---

## Track A — 健壮性硬化（TDD）

### Task A1：App/路由级错误边界（消除白屏）

**Files:**
- Create: `src/components/common/__tests__/RouteErrorBoundary.test.tsx`
- Create: `src/components/common/RouteErrorBoundary.tsx`（薄封装 `ErrorBoundary`，含 useLocation key 重置 + 友好文案 + 返回首页/重试）
- Modify: `src/App.tsx`（用边界包裹路由内容）

**Interfaces:**
- Produces: `export const RouteErrorBoundary: React.FC<{ children: ReactNode }>`——内部用既有 `ErrorBoundary`，并以 `useLocation().pathname` 作 `key` 使导航到新路由时自动清除错误态。
- Consumes: 既有 `ErrorBoundary`。

- [ ] **Step 1：写失败测试（红）**
```tsx
// RouteErrorBoundary.test.tsx
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { RouteErrorBoundary } from '../RouteErrorBoundary'

const Boom = () => { throw new Error('boom') }

it('renders fallback (not a blank screen) when a child throws', () => {
  render(<MemoryRouter><RouteErrorBoundary><Boom /></RouteErrorBoundary></MemoryRouter>)
  expect(screen.getByText(/暂时无法显示|加载失败|出错/)).toBeTruthy()
})
it('renders children normally when no error', () => {
  render(<MemoryRouter><RouteErrorBoundary><div>正常内容</div></RouteErrorBoundary></MemoryRouter>)
  expect(screen.getByText('正常内容')).toBeTruthy()
})
```
- [ ] **Step 2：运行确认红** — `npx vitest run src/components/common/__tests__/RouteErrorBoundary.test.tsx` → FAIL（模块不存在）。
- [ ] **Step 3：实现 `RouteErrorBoundary.tsx`**——封装 `ErrorBoundary`，`key={useLocation().pathname}`，`fallbackTitle="页面出错了"`/`fallbackMessage` 友好文案。（先跑测试看 ErrorBoundary 实际渲染文案，断言对齐真实文案。）
- [ ] **Step 4：接入 App.tsx**——在 `AppLayout` 的内容区（`<Outlet/>` 外层）包一层 `RouteErrorBoundary`，使页面崩溃时保留侧栏/导航、内容区显示 fallback；登录/注册等无布局路由各自包裹。不改路由路径与守卫逻辑。
- [ ] **Step 5：绿 + 全量回归** — `npx vitest run`（全量）+ `npx tsc --noEmit` + `npx eslint src/components/common/RouteErrorBoundary.tsx src/App.tsx --max-warnings 0`。全绿。
- [ ] **Step 6：提交** — `feat(phase4): 路由级错误边界,页面崩溃降级而非白屏`（结尾 Co-Authored-By）。

**验收**：抛错子组件渲染出 fallback；正常子组件照常渲染；全量测试绿；App 路由行为不变。

---

### Task A2：API 客户端瞬时失败重试（指数退避，幂等请求）

**Files:**
- Create: `src/api/__tests__/retry.test.ts`
- Create: `src/api/retry.ts`（重试判定 + 退避计算的纯函数 + axios 安装函数）
- Modify: `src/api/client.ts`（接入重试拦截器，**不影响**既有 401 刷新流程）

**Interfaces:**
- Produces:
  - `export function shouldRetry(error: AxiosError, attempt: number, opts: RetryOptions): boolean`——仅对**幂等方法**（GET/HEAD/OPTIONS，或显式 `config.retry===true`）且状态 ∈ {502,503,504} 或网络错误（无 `error.response`、非 cancel）且 `attempt < maxRetries` 时返回 true。
  - `export function backoffDelay(attempt: number, base=300, cap=4000): number`——指数退避 + jitter。
  - `export function installRetry(client: AxiosInstance, opts?: RetryOptions): void`。
  - `RetryOptions = { maxRetries?: number /*默认2*/, methods?: string[], statuses?: number[] }`。
- Consumes: axios 既有实例与 `RequestConfig`。
- **与 401 流程隔离**：重试拦截器只处理瞬时网络/5xx；401 仍由既有刷新逻辑处理（重试拦截器对 401 直接放行给后续/既有处理）。

- [ ] **Step 1：写失败测试（红）**——用 `axios-mock-adapter` 或手写 mock，断言：(a) GET 遇 503 重试到成功；(b) 超过 maxRetries 抛错；(c) POST 默认不重试；(d) 401 不被重试拦截器吞掉；(e) `backoffDelay` 单调有界。
```ts
// retry.test.ts（示意，断言以真实实现为准）
it('retries idempotent GET on 503 then succeeds', async () => { /* mock 503,503,200 → resolves */ })
it('does not retry POST by default', async () => { /* mock 503 → rejects, 1 call */ })
it('stops after maxRetries', async () => { /* mock all 503 → rejects after maxRetries+1 calls */ })
```
- [ ] **Step 2：运行确认红**。
- [ ] **Step 3：实现 `retry.ts`** 三个函数。
- [ ] **Step 4：接入 `client.ts`**——`installRetry(apiClient)`，放在 401 拦截器之外/之前不与之冲突（重试只在 `!error.response || status∈{502,503,504}` 且幂等时生效；401 短路交还既有逻辑）。保持 `timeout:30000` 不变。
- [ ] **Step 5：绿 + 全量回归 + tsc + eslint**。**特别确认** `src/api/**/__tests__` 既有测试与依赖 apiClient 的组件测试不回归。
- [ ] **Step 6：纳入门禁 + 提交**——`retry.ts` 是逻辑性 util，加入 `vitest.config.ts` `coverage.include` + threshold（lines 80，纯函数应高覆盖）。提交 `feat(phase4): API 幂等请求瞬时失败重试(指数退避),隔离401流程`。

**验收**：幂等 GET 5xx/网络抖动自动重试并成功；非幂等默认不重试；401 流程不受影响；`retry.ts` ≥80%；全量绿。

---

### Task A3：SOP 维护页 3D 视图错误边界

**Files:**
- Modify: `src/pages/sopMaintenance/SOPViewerScene.tsx`（或其在 `SOPMaintenancePage.tsx` 的挂载点）——用既有 `Viewer3DErrorBoundary` 包裹 3D 场景，使 WebGL/模型加载失败时该区域降级而非崩整页。
- Modify/Reference: `src/pages/__tests__/SOPMaintenancePage.characterization.test.tsx`（**断言不改**；仅确认仍绿。若需为降级路径加用例，新增独立用例，不动现有 44 例。）

**Interfaces:**
- Consumes: `Viewer3DErrorBoundary`（既有）。
- **行为约束**：成功路径（特征测试覆盖的 44 例）DOM 不变——`Viewer3DErrorBoundary` 仅在子树抛错时介入，正常时透传 children。

- [ ] **Step 1：定位 3D 挂载点**——确认 SOP 页 3D 场景（Canvas/Atom01Interactive/InteractiveManifestViewer）当前未被任何 ErrorBoundary 包裹（`grep -n 'Viewer3DErrorBoundary\|ErrorBoundary' src/pages/sopMaintenance src/pages/SOPMaintenancePage.tsx`）。
- [ ] **Step 2：写一个降级特征测试（新增,不改现有）**——在 `SOPMaintenancePage.characterization.test.tsx` 新增一个 `it`：mock 3D 子组件（如 `SOPViewerScene` 内部）首次渲染抛错，断言出现 3D 降级文案（`/3D 视图不可用|WebGL/`），且页面其余区域（标题/SOP 列表）仍在。
- [ ] **Step 3：确认红**（未包裹时抛错会冒泡使整页测试崩，或无降级文案）。
- [ ] **Step 4：用 `Viewer3DErrorBoundary` 包裹 3D 场景** → 绿。
- [ ] **Step 5：全量回归**——现有 44 例 + 新增例全绿；`vitest run --coverage` 门禁仍过；tsc/eslint 绿。
- [ ] **Step 6：提交** — `feat(phase4): SOP 维护页 3D 视图错误边界,WebGL 失败区域降级`。

**验收**：3D 区域抛错时局部降级、页面其余可用；现有 44 特征例不变且绿；门禁过。

---

### Task A4：AI 管线调用失败/超时态审计与补齐

**Files:**
- Audit: `src/api/{training,aiAssistant,pipeline,agent}.ts` + 其调用方组件（AIAssistantPanel、项目生成、反馈、workbench）
- Create/Modify: 视审计结果——为缺失失败/超时/降级提示的调用点补齐（loading→error→重试 affordance），可复用 antd `message`/`Alert`/`Result`。
- Create: `src/api/__tests__/aiPipelineRobustness.test.ts`（针对补齐点）

**Interfaces:**
- 复用 Task A2 的 `apiClient`（已带重试）；LLM 长调用如需更长超时，按调用点传 `timeout` 覆盖（不改全局）。
- **行为约束**：成功路径不变；仅补"失败时有可见反馈 + 可重试"。

- [ ] **Step 1：审计清单**——逐个 AI 调用点记录：是否有 loading 态？失败是否有用户可见反馈（非仅 console）？是否可重试？是否会因长耗时撞 30s 全局 timeout？产出一张"调用点 × 现状 × 缺口"表写入报告。
- [ ] **Step 2：挑出真实缺口**（有缺口才补；已有 `message.error` 兜底的算覆盖）。对每个缺口先写失败测试（mock 拒绝，断言出现可见错误/重试 UI）。
- [ ] **Step 3：确认红 → 实现 → 绿**（逐缺口）。长调用超时按需在该调用点传更大 `timeout`。
- [ ] **Step 4：全量回归 + tsc + eslint**。
- [ ] **Step 5：提交** — `feat(phase4): AI 管线调用失败/超时降级与重试补齐`。

**验收**：每个 AI 调用点失败时有可见反馈与重试路径；无长调用被全局 30s 误杀；全量绿。（若审计发现现状已足够健壮，记录结论、零改动亦可接受。）

---

## Track B — 性能测量工具 + Runbook（用户在真实环境运行）

> 这些 Task 产出**可运行脚本 + 操作手册 + 基线文档骨架**，不改产品代码。基线数字由用户在能起全栈（含 Postgres、真实浏览器）的环境跑出后回填。

### Task B1：首屏 / 关键路由 Lighthouse 脚本

**Files:**
- Create: `r-mos-frontend/scripts/perf/lighthouse.mjs`（用 `lighthouse` + `chrome-launcher`，对 `BASE_URL` 的 N 个关键路由跑，输出 json + 摘要表）
- Create: `r-mos-frontend/scripts/perf/README.md`（前置：`npm i -D lighthouse chrome-launcher`；用法：`BASE_URL=http://localhost:5173 node scripts/perf/lighthouse.mjs`）
- Modify: `r-mos-frontend/package.json`（`"perf:lighthouse": "node scripts/perf/lighthouse.mjs"`）

- [ ] **Step 1**：写 `lighthouse.mjs`——读取 `BASE_URL` + 路由列表（登录后置 token 或测公开页 + 截 FCP/LCP/TBT/CLS/TTI），输出 `docs/superpowers/plans/phase4-baseline.md` 可粘贴的表格行 + 原始 json 落 `scripts/perf/out/`。
- [ ] **Step 2**：README 写清前置依赖、如何起 `npm run preview`（产物模式更接近真实）、如何登录态测受保护路由。
- [ ] **Step 3**：本地 dry-run（若环境允许起 preview）：`BASE_URL=... npm run perf:lighthouse` 至少对登录页跑通，确认脚本不报错、产出表格行。环境不允许则在 README 标注"需用户环境运行"。
- [ ] **Step 4**：提交 `chore(phase4): Lighthouse 首屏/关键路由测量脚本 + runbook`。

**验收**：脚本可对给定 BASE_URL 产出标准化指标表；README 可复现；package.json 有 `perf:lighthouse`。

---

### Task B2：3D 查看器渲染 trace runbook

**Files:**
- Create: `r-mos-frontend/scripts/perf/3d-viewer-trace-runbook.md`

- [ ] **Step 1**：写 runbook——用 chrome-devtools Performance（或 MCP `performance_start_trace`/`performance_stop_trace`）采集 SOP 维护页/Monitor 页 3D 渲染：明确操作脚本（打开页→进入隔离态→爆炸图→旋转）、采集指标（FPS、长任务、GPU、首个可交互 3D 帧、`useFrame` 帧成本、GLB 加载瀑布）、记录位置（基线文档 3D 段）。
- [ ] **Step 2**：列出"可疑热点假设"供基线印证（不预先优化）：如 17 个 `InteractiveLinkMesh` 各自 `useGLTF`、爆炸态子零件并发加载、`useFrame` 内逐帧 traverse 材质。
- [ ] **Step 3**：提交 `docs(phase4): 3D 查看器渲染 trace runbook`。

**验收**：runbook 可被照做采出 3D 渲染指标；列出待印证热点（不含优化动作）。

---

### Task B3：WebSocket 遥测时延/吞吐探针

**Files:**
- Create: `r-mos-frontend/scripts/perf/ws-probe.mjs`（node `ws` 客户端连 `/ws/robot/status`，统计消息间隔分布、5Hz 达成率、ping→pong RTT、丢帧）
- Modify: `package.json`（`"perf:ws": "node scripts/perf/ws-probe.mjs"`）

- [ ] **Step 1**：写 `ws-probe.mjs`——读 `WS_URL`，连接 N 秒，输出：均值/ P50/P95 间隔、相对 200ms(5Hz) 偏差、pong RTT、断连次数；表格行写基线文档 WS 段。
- [ ] **Step 2**：README 补充 WS 用法（需后端运行）。
- [ ] **Step 3**：提交 `chore(phase4): WebSocket 遥测时延/吞吐测量探针`。

**验收**：探针对运行中的后端 WS 产出 5Hz 达成率与时延分布。

---

### Task B4：AI 管线端到端计时

**Files:**
- Create: `r-mos-backend/app/core/timing_middleware.py`（**默认关闭**的 ASGI 计时中间件，env `PERF_TIMING=1` 开启，按路由记录 server 处理耗时到日志/响应头 `X-Process-Time`）
- Create: `r-mos-backend/scripts/perf/ai_pipeline_timing.md`（runbook：开启 timing → 触发项目生成/反馈/workbench → 从日志/响应头读各阶段耗时；含 LLM 调用耗时定位）
- Modify: `r-mos-backend/app/main.py`（条件注册中间件，env 关闭时零开销/不改响应）

- [ ] **Step 1**：写中间件——`if os.getenv("PERF_TIMING")=="1"` 才 `add_middleware`；记录 `X-Process-Time` 响应头 + 结构化日志。默认不启用，**不改既有响应体**。
- [ ] **Step 2**：条件注册到 main.py；跑 `pytest tests/ --ignore=tests/e2e` 确认默认关闭时全量不回归。
- [ ] **Step 3**：写 runbook（如何开启、触发哪些端点、读哪些数字）。
- [ ] **Step 4**：提交 `chore(phase4): AI 管线计时中间件(默认关闭)+ runbook`。

**验收**：`PERF_TIMING=1` 时端点耗时可观测；默认关闭时后端全量测试不变绿。

---

### Task B5：基线文档骨架 + 采集 checkpoint

**Files:**
- Create: `docs/superpowers/plans/phase4-baseline.md`（四段：首屏/关键路由、3D 渲染、WebSocket、AI 管线；每段含指标表头 + "目标/阈值待定" + "采集命令"）

- [ ] **Step 1**：建骨架文档，把 B1-B4 的命令与表头填好，数字列留空标注"待用户环境采集"。
- [ ] **Step 2**：提交 `docs(phase4): 性能基线文档骨架(待真实环境回填)`。
- [ ] **⏸ Checkpoint（用户动作）**：用户在可起全栈+浏览器的环境运行 B1-B4，回填 `phase4-baseline.md` 四段真实数字。**在数字回填前，不进入 Track C。**

**验收**：基线文档骨架就绪、命令可复现；明确标注"等待用户回填"。

---

## Track C — 针对性优化（基线就绪后）

### Task C1（Checkpoint，非代码）：基线分析 → 优化子计划

> **硬前置：** `phase4-baseline.md` 四段已有真实数字。

- [ ] **Step 1**：读基线，按"影响×可行性"排序真实瓶颈（如 LCP 主因、3D 首帧、5Hz 偏差、某 LLM 阶段耗时）。
- [ ] **Step 2**：用 superpowers:writing-plans 另写 `docs/superpowers/plans/<date>-phase4b-optimizations.md`：每个优化 Task 必须含"优化前数字 → 措施 → 优化后复测命令 → 期望改善"，且复测用 B 轨工具。
- [ ] **Step 3**：交付该子计划，按 subagent-driven 执行（独立于本计划）。

**验收**：优化子计划每项有可对比的前/后测量定义；无"臆测式优化"。

---

## Phase 4 收尾（Track A 完成 + Track B 工具就绪后）

- [ ] 全量复验：前端 `vitest run --coverage` 全绿达阈值 + `tsc`/`eslint` 绿；后端 `pytest tests/ --ignore=tests/e2e` 全绿。
- [ ] 健壮性改进有测试覆盖（A1-A4 各自的红→绿用例）。
- [ ] 测量工具可复现 + 基线文档骨架就位（数字待用户回填）。
- [ ] 更新总控计划：Phase 4 → 🚧（Track A/B 完成、Track C 待基线）或 ✅（若基线+优化也在本轮完成）。更新 CLAUDE.md（如新增 `scripts/perf/`）+ 记忆。
- [ ] 中文汇报：健壮性补齐项 + 测量工具清单 + 下一步（用户跑基线 → C1 优化子计划）。

## 自检（计划编写完成后）

- **Spec 覆盖**：Spec Phase 4「先测量基线」→ Track B（B1-B5）；「再针对性优化」→ Track C（C1，基线门控）；「健壮性：错误边界/超时重试/降级失败提示」→ Track A（A1 边界/A2 重试/A3 3D 降级/A4 AI 失败态）。验收「关键路径有前/后对比 + 健壮性可验证」→ B 轨工具产出对比 + A 轨 TDD 用例。
- **占位符**：A 轨给出可运行的红→绿测试样例 + 接口签名 + 接入点；B 轨给出脚本职责/输入输出/package 脚本名/runbook 内容纲要；无 TBD（基线数字本就该由真实环境产出，已显式标注为用户 checkpoint）。
- **一致性**：复用既有 `ErrorBoundary`/`Viewer3DErrorBoundary`/`apiClient`/`useWebSocket`，不重造；测量统一回填 `phase4-baseline.md`；"先测量后优化"在 Global Constraints 与 Track C 门控双重落实。
- **关键风险**：(a) 健壮性改动误伤成功路径 → TDD + 全量回归 + 特征测试断言不改；(b) 重试与 401 刷新冲突 → A2 显式隔离；(c) timing 中间件污染响应 → 默认关闭 + 后端全量回归；(d) 优化臆测 → C1 硬门控基线。
