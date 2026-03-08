# Frontend Refactor Alignment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在不改动 3D 场景和 adjudication 业务逻辑的前提下，让 `MonitorPage`、`SOPMaintenancePage`、`DiagnosisPanel` 与当前仓库已落地的 `AgentWorkbenchPage` 视觉语言和测试门禁对齐。

**Architecture:** 先校正设计基线，再做页面重构。设计系统以当前仓库已经存在的 token、Tailwind 映射和 `common/` 组件为准，不引入新字体依赖，不把本轮“样式重构”膨胀成“重建整套 UI 基础库”。`MonitorPage` 先全量去 Ant Design 可视层；`SOPMaintenancePage` 采用“状态不动、渲染拆壳”的外科式重构；`DiagnosisPanel` 只做样式收口与回归测试补强。

**Tech Stack:** React 18, TypeScript 5, Vite 5, TailwindCSS 3, Ant Design 5, Zustand, React Three Fiber, Vitest, Testing Library

## Alignment Review

### 已对齐的前提

- `MonitorPage` 当前仍重度依赖 `antd` 卡片/标签/统计组件，适合作为第一个页面重构目标。
- `SOPMaintenancePage` 当前文件体量为 `1554` 行，且 UI 与状态逻辑耦合严重，必须采用拆壳而不是一次性推倒重写。
- `DiagnosisPanel` 已存在生产实现与测试，说明它不是“待新建组件”，而是“待精修组件”。
- “3D 层不动”“adjudication 状态机不动”的边界判断正确，必须保留。

### 必须修正的错误前提

- 设计 token 基线不是方案文档中的 amber + Rajdhani 体系；当前真实基线在 `r-mos-frontend/src/styles/tokens.css` 与 `r-mos-frontend/tailwind.config.js`，主色是 `--color-primary`，字体是 `Inter` + `JetBrains Mono`。
- 仓库当前没有 `shadcn Select`、`Slider`、`Switch` 组件；若照原方案直接执行，会把页面重构扩大成基础组件库建设。
- `DiagnosisPanel` 并非“样式未定义”；它已使用当前 token 体系，并已有 `DiagnosisPanel.test.tsx` 覆盖关键交互。
- 文档状态存在漂移：`AGENTS.md` 的 2026-03-05 快照写“下一步进入 T-06”，但 `R-MOS_Review_Test_Cleanup_Plan.md` 在 2026-03-08 已把 `T-06` 全部勾选完成。后续重构任务不能再挂到旧的 `T-06` 名下。

### 本轮执行决策

- 不新增字体依赖；继续使用当前 `font-sans` / `font-mono`。
- 不重命名现有 token；只允许按需补语义别名，且别名必须映射到当前 palette。
- 不预设新增 `Select` / `Slider` / `Switch`；优先复用现有能力，确有必要再单独立项补组件。
- `MonitorPage` 作为视觉基准落地页；`SOPMaintenancePage` 以“拆 presentational shell + 保留 state orchestration”的方式推进。

## Acceptance Contract

- Gate: 遵循 `docs/testing/ACCEPTANCE_CHARTER.md` 第 1 节和第 5 节，至少提供可复现命令、输出摘要、最小前端回归。
- Minimum regression:
  - `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npm test -- <targeted tests>`
  - `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npm run build`
- Evidence:
  - 更新 `DEVELOPMENT_LOG.md`
  - 输出 `git diff --name-only`
  - 记录失败处理，不允许“假设通过”

## Task 1: Freeze The Visual Contract

**Files:**
- Modify: `r-mos-frontend/src/styles/tokens.css`
- Modify: `r-mos-frontend/tailwind.config.js`
- Modify: `r-mos-frontend/src/components/common/PageHeader.tsx`
- Modify: `r-mos-frontend/src/components/common/SectionCard.tsx`
- Modify: `r-mos-frontend/src/components/common/DataCard.tsx`

**Steps:**
1. 核对并固定“当前真实设计基线”，禁止把方案文档中的新 token 名直接替换进现有页面。
2. 仅在确实降低页面改造成本时补充语义 alias，例如 `warning/error/info` 到现有 palette；不得修改现有 `primary/danger/success` 的视觉含义。
3. 先复用 `PageHeader`、`SectionCard`、`DataCard`、`StatusBadge`，只对共性样式缺口做最小增强。
4. 运行 `npm run build`，确认 alias 不导致 Tailwind class 回归。
5. Commit: `git commit -m "refactor: align frontend visual contract"`

**Expected verification:**
- `npm run build`
- 结果：PASS，无新增 Tailwind class 解析错误

## Task 2: Refactor MonitorPage First

**Files:**
- Modify: `r-mos-frontend/src/pages/MonitorPage.tsx`
- Create: `r-mos-frontend/src/pages/__tests__/MonitorPage.test.tsx`
- Reuse: `r-mos-frontend/src/components/common/*`
- Reuse: `r-mos-frontend/src/components/Viewer3D/RobotViewer.tsx`

**Steps:**
1. 写 `MonitorPage` 测试，覆盖 4 个关键状态：连接中、断线告警、故障列表、关节错误高亮。
2. 删除页面内 `antd` 的 `Card/Row/Col/Statistic/Tag/Alert/Typography/Space` 可视层依赖，改为 Tailwind + 现有 common 组件。
3. 保留 `useWebSocket()`、`RobotViewer`、`Viewer3DErrorBoundary`、`joints3D` 数据整形逻辑不变。
4. 把所有内联颜色迁移到 token class，清理 `var(--error-color)` 这类当前 token 体系外的值。
5. 运行定向测试和构建，再提交。

**Expected verification:**
- `npm test -- src/pages/__tests__/MonitorPage.test.tsx`
- `npm run build`
- 结果：PASS，页面无 `antd` 可视组件残留

## Task 3: Decompose SOPMaintenancePage Without Rewriting Logic

**Files:**
- Modify: `r-mos-frontend/src/pages/SOPMaintenancePage.tsx`
- Create: `r-mos-frontend/src/pages/sop-maintenance/MaintenanceHeader.tsx`
- Create: `r-mos-frontend/src/pages/sop-maintenance/MaintenanceLeftRail.tsx`
- Create: `r-mos-frontend/src/pages/sop-maintenance/MaintenanceRightRail.tsx`
- Create: `r-mos-frontend/src/pages/sop-maintenance/MaintenanceExamOverlay.tsx`
- Create: `r-mos-frontend/src/pages/sop-maintenance/__tests__/MaintenanceHeader.test.tsx`
- Create: `r-mos-frontend/src/pages/sop-maintenance/__tests__/MaintenanceRightRail.test.tsx`

**Steps:**
1. 先从 `SOPMaintenancePage.tsx` 中抽出纯展示区块，不移动 `useState/useEffect/useMemo/useCallback` 和 3D scene orchestration。
2. 第一批只拆顶部头部、左栏面板、右栏详情面板、考试结束覆盖层；中间 3D 区域原样保留。
3. 对仍必须保留的 `antd` 组件单独列白名单；默认只允许 `Modal`、`message`，其余控件逐步替换。
4. 删除 `GROUP_COLORS` 这类硬编码色值渲染入口，改成基于现有 token 的 class map；不要引入方案文档中的新彩色体系。
5. 运行提取组件测试、页面相关既有测试和构建，再提交。

**Expected verification:**
- `npm test -- src/pages/sop-maintenance/__tests__/MaintenanceHeader.test.tsx src/pages/sop-maintenance/__tests__/MaintenanceRightRail.test.tsx src/components/DiagnosisPanel/__tests__/DiagnosisPanel.test.tsx`
- `npm run build`
- 结果：PASS，`SOPMaintenancePage.tsx` 行数明显下降，3D 与 adjudication 行为不回归

## Task 4: Polish DiagnosisPanel As A Shared Inspector Panel

**Files:**
- Modify: `r-mos-frontend/src/components/DiagnosisPanel/DiagnosisPanel.tsx`
- Modify: `r-mos-frontend/src/components/DiagnosisPanel/__tests__/DiagnosisPanel.test.tsx`

**Steps:**
1. 基于当前实现补齐视觉收口，而不是按原方案重写数据结构。
2. 固定加载态、空态、验证失败态、主管审核禁用态的视觉层级。
3. 只修样式和可测试性，不改 `DiagnosisResult/MaintenancePlan/VerificationResult` 数据契约。
4. 扩充测试，覆盖“无结果空态”“verification failed”“requires supervisor”。
5. 提交独立 commit。

**Expected verification:**
- `npm test -- src/components/DiagnosisPanel/__tests__/DiagnosisPanel.test.tsx src/pages/agent/__tests__/AgentWorkbenchPage.test.tsx`
- `npm run build`
- 结果：PASS

## Task 5: Close The Loop With Docs And Evidence

**Files:**
- Modify: `docs/testing/TEST_PLAN.md`
- Modify: `docs/testing/TEST_REPORT.md`
- Modify: `DEVELOPMENT_LOG.md`

**Steps:**
1. 在 `TEST_PLAN.md` 增补 `MonitorPage`、`SOPMaintenancePage`、`DiagnosisPanel` 的重构后验证点和 N/A 说明。
2. 在 `TEST_REPORT.md` 记录本轮最小回归命令、结果摘要、失败处置。
3. 在 `DEVELOPMENT_LOG.md` 记录每个任务的文件范围、命令、结果与风险。
4. 输出 `git diff --name-only` 并整理提交白名单。
5. Commit: `git commit -m "docs: record frontend refactor evidence"`

**Expected verification:**
- `git diff --name-only`
- `npm test -- <all newly added frontend tests>`
- `npm run build`
- 结果：PASS，证据完整可复现

## Risks To Watch

- `SOPMaintenancePage` 当前工作区已经存在用户未提交改动，实施时必须按文件白名单暂存，不能误带其他脏改。
- 如果执行者坚持引入 Rajdhani 或补新的 Radix/shadcn 表单控件，将触发“新增依赖”决策点，需要先评估是否要补 ADR。
- `R-MOS_Review_Test_Cleanup_Plan.md` 中关于 `StepPanel/ToolPanel/VerdictPanel` 的落地描述与当前仓库文件树不一致，实施时必须以真实文件存在性为准，不能照旧文档硬对。

## Out Of Scope

- 不改 `useWebSocket()` 协议与后端接口
- 不改 three.js / R3F 组件实现
- 不改 adjudication 核心状态机与评分逻辑
- 不做字体体系切换
- 不引入新的外部依赖
