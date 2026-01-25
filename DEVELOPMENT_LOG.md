# Development Log

## 2026-01-24 — P0 / P1 / P2 交付记录（裁决级重构）

> 目的：让任何接手工程师快速理解已做事项、设计取舍、验证方式与后续风险。

### 总览
- **P0**：裁决强制阻断（B.2）、三元完成判定、执行器零信任、工具匹配数据源统一为 PartRegistry。
- **P1**：不可逆步骤与致命错误（FAILED_FATAL）落地，执行器锁死与回滚阻断。
- **P2**：SOP 脚本升级为裁决级、UI 接驳裁决级组件，页面替换完成。

---

### P0 — 裁决不可绕行与完成判定落地

**目标**
- 落实规范 B.2：ACTIVE 约束必须 BLOCKED。
- 落实三元完成判定：语义 && 约束 && 几何。
- 执行器零信任：执行前/完成前都必须裁决。
- 工具匹配数据源：逻辑层只从 PartRegistry 读取（禁止 toolData.ts）。

**核心改动**
- `r-mos-frontend/src/adjudication/core/decisionEngine.ts`
  - 新增约束影响范围计算：父子链 + 约束链扩展（间接影响）。
  - 强制阻断：返回 `AdjudicationResult.BLOCKED` + `reasonCode=ERR_CONSTRAINT`。
  - 新增 `validateActionCompletion`（三元公理：语义 && 约束 && 几何）。
- `r-mos-frontend/src/adjudication/core/geometryJudge.ts`
  - 工具匹配改为 `getPartById(...).screwSpec.requiredTool`。
- `r-mos-frontend/src/adjudication/executor/sopExecutor.ts`
  - 执行前裁决、完成前验证（零信任）。
- `r-mos-frontend/src/adjudication/data/partRegistry.ts`
  - 合并螺丝实例进入 `PART_SCHEMA_REGISTRY`，逻辑层统一数据源。
- `r-mos-frontend/src/adjudication/__tests__/decisionEngine.test.ts`
  - TC-001 强制阻断校验（`BLOCKED + ERR_CONSTRAINT`）。

**设计要点**
- 约束阻断不允许降级为 WARNING。
- 完成判定统一由 `validateActionCompletion` 输出。

---

### P1 — 不可逆步骤与致命错误

**目标**
- 引入 `FAILED_FATAL`，一旦触发系统锁死，仅允许 reset。
- 不可逆步骤：执行后禁止回滚。

**核心改动**
- `r-mos-frontend/src/adjudication/types/adjudication.ts`
  - `SystemState` 新增 `FAILED_FATAL`
  - `SOPStepAdjudication` 新增 `isIrreversible?`, `fatalOnFailure?`
- `r-mos-frontend/src/adjudication/executor/sopExecutor.ts`
  - 任何执行/验证入口若 `FAILED_FATAL` → 直接 BLOCKED。
  - `fatalOnFailure` 触发时设置 `SystemState.FAILED_FATAL`。
  - `goToStep` 中阻止不可逆步骤回滚（执行/完成后禁止回退）。
- `r-mos-frontend/src/adjudication/__tests__/sopExecutor.test.ts`
  - 新增致命错误锁死测试（失败即 FAILED_FATAL，后续步骤不可执行）。

---

### P2 — SOP 脚本升级与 UI 接驳

**目标**
- 让裁决能力真实进入界面流程。
- SOP 脚本升级为裁决级结构（preconditions/validations/failureReasons）。

**核心改动**
- `r-mos-frontend/src/data/sopScripts.ts`
  - 升级为 `SOPScriptAdjudication` 格式。
  - 引入 preconditions/validations/failureReasons。
  - 选定步骤标记 `isIrreversible: true` & `fatalOnFailure: true`。
  - 保留 Legacy 结构（旧 UI 仍可用，避免回滚困难）。
- `r-mos-frontend/src/pages/SOPMaintenancePage.tsx`
  - 替换为 `SOPPlayerAdjudicated` 与 `DisassemblyDemoAdjudicated`。
  - `useAdjudicationStore` 贯通工具选择与裁决。
- `r-mos-frontend/src/components/Maintenance/SOPPlayer.tsx`
  - 标记 `@deprecated`，继续保留兼容。
- `r-mos-frontend/src/components/Viewer3D/DisassemblyDemo.tsx`
  - 标记 `@deprecated`，继续保留兼容。

---

### 文档与位置调整
- 规范文档已移动至：`docs/specs/R-MOS 机器人数字孪生维保系统｜裁决级规范文档.md`
- 说明：`robot/` 是独立 git 仓库（submodule 结构），顶层无法直接追踪文件。
- 已同步引用路径：
  - `Codex交接提示词.md`
  - `裁决级系统重构开发计划.md`

---

### 构建与验证
- 已执行 `npm run build`（`r-mos-frontend/`）✅ 通过
- 仅提示 chunk size warning（性能优化项，非阻断）

---

### 当前未解决/待确认事项
- `docs/specs/...` 规范文档已追踪，但如果后续需要同步到 `robot/` 子仓库，请明确流程。
- `sopScripts.ts` 中使用了示例螺丝 ID（如 `screw_torso_m4x12_001`），若未在数据层注册，需补充或映射。
- 关键部件表新增：`r-mos-frontend/src/adjudication/data/criticalParts.ts`（目前为空，需业务补全）。

---

### 接手建议（下一步）
1. **补齐真实 SOP 数据**：用真实零件/螺丝 ID 替换示例数据。
2. **扩展约束图**：从脚部扩展到躯干/手臂等模块。
3. **完善关键部件表**：填充关键部件清单与原因。
4. **测试补齐**：补充 SOP 失败路径、不可逆步骤回滚阻断场景。
5. **UI 反馈**：将 `FAILED_FATAL` 状态在 UI 层清晰提示并提供重置入口。

---

### 关键文件清单（便于快速定位）
- 规范：`docs/specs/R-MOS 机器人数字孪生维保系统｜裁决级规范文档.md`
- 裁决引擎：`r-mos-frontend/src/adjudication/core/decisionEngine.ts`
- SOP 执行器：`r-mos-frontend/src/adjudication/executor/sopExecutor.ts`
- 裁决级 SOP：`r-mos-frontend/src/data/sopScripts.ts`
- 入口页面：`r-mos-frontend/src/pages/SOPMaintenancePage.tsx`
- 测试：`r-mos-frontend/src/adjudication/__tests__/decisionEngine.test.ts`、`r-mos-frontend/src/adjudication/__tests__/sopExecutor.test.ts`

## 2026-01-24 (P0)
- [Feature] 裁决引擎落地：实现 B.2 强制阻断规则。
- [Refactor] 工具匹配逻辑迁移至 PartRegistry。
- [Core] 确立完成判定三元公理 (Semantic + Constraint + Geometry)。
- [Security] SOP 执行器实现零信任检查。

---

## 2026-01-25 — P3 / P4 交付记录（覆盖扩展 + 多模式落地）

> 目的：让任何接手工程师理解 P3/P4 的扩展范围、测试体系与 UI/逻辑联动细节。

### P3 — 约束扩展 + 核心测试

**目标**
- 扩展到躯干约束图（胸腔夹板 + 8 颗 M3×10）。
- 增加核心逻辑单测覆盖（B.2、C.2、FAILED_FATAL）。
- 形成统一测试入口 `npm test`。

**核心改动**
- `r-mos-frontend/src/adjudication/data/constraintGraph.ts`
  - 新增 `TORSO_CONSTRAINTS`：`frame_torso_chest` 被 8 颗 `M3×10` 固定；
  - `torso_motor`、`torso_pcb_main` 被胸腔夹板覆盖；
  - 合并 `ALL_CONSTRAINTS`，`getAllConstraints()` 使用全量数据。
- `r-mos-frontend/src/adjudication/data/partRegistry.ts`
  - 新增 `frame_torso_chest`、`torso_motor`、`torso_pcb_main`；
  - 脚部 + 躯干螺丝合并到 `PART_SCHEMA_REGISTRY`；
  - `PART_SCREWS_REGISTRY` 增加 `frame_torso_chest` 8 螺丝映射。
- `r-mos-frontend/src/adjudication/data/screwInstances.ts`
  - 新增 `TORSO_SCREW_INSTANCES`（8 颗 `M3×10`），并合并到 `ALL_SCREW_INSTANCES`。
- `r-mos-frontend/src/adjudication/core/decisionEngine.ts`
  - 父子链影响范围修正为“只追溯父链 + 自身子树”，避免兄弟链过度阻断。
- `r-mos-frontend/src/adjudication/__tests__/core_logic.test.ts`
  - 新增三条核心测试：B.2 强制阻断、C.2 不可逆回滚、FAILED_FATAL 熔断。
- `r-mos-frontend/src/adjudication/__tests__/run-adjudication-tests.ts`
  - 集中执行全部裁决相关测试。
- `r-mos-frontend/scripts/run-adjudication-tests.mjs`
  - 使用 esbuild 执行 TS 测试入口（无需额外依赖）。

**验证结果**
- `npm test` 全绿（P3 Core Logic + Decision Engine Slice + SOP Fatal）。

---

### P4 — 多模式落地（教学 / 考试 / 维保）

**目标**
- 教学模式：提示气泡 + 允许重试。
- 考试模式：扣分、禁止重试、致命熔断结算。
- 维保模式：保持严格阻断。
- 结果页：致命错误自动展示 reasonCode 与最终分数。
- 模式切换：带确认，重置 SOP 与评分。

**核心逻辑改动**
- `r-mos-frontend/src/adjudication/types/adjudication.ts`
  - `AdjudicationReport` 新增 `hint?`、`allowRetry?`、`shouldSummarize?`。
- `r-mos-frontend/src/adjudication/executor/sopExecutor.ts`
  - 新增 `retryStep()`：教学模式失败后回到 IDLE。
  - `handleFailure`：
    - 教学：读取 `failureReasons[].teachingResponse.hintContent` + `allowRetry=true`；
    - 考试：调用 `scoringEngine.deduct(...)`，`allowContinue=false` 时 `finalize` + `shouldSummarize=true`；
    - fatalOnFailure：强制 `shouldSummarize=true`。
- `r-mos-frontend/src/adjudication/ui/examHeader.ts`
  - 考试倒计时格式化与紧急阈值判定（<5 分钟变红）。
- `r-mos-frontend/src/adjudication/core/scoringEngine.ts`
  - 评分引擎：`reset / deduct / getState / finalize / subscribe`。
- `r-mos-frontend/src/adjudication/ui/examHeader.ts`
  - 考试倒计时格式化与紧急判定工具。
- `r-mos-frontend/src/adjudication/core/stateManager.ts`
  - `persist` 使用注入存储 + Node 内存存储兜底，消除测试警告。
- `r-mos-frontend/src/adjudication/__tests__/test-setup.ts`
  - 注入内存存储并设置 `__RMOS_TEST_STORAGE_READY__`。
- `r-mos-frontend/src/adjudication/__tests__/p4_mode.test.ts`
  - 教学提示 + 重试、倒计时格式测试。
- `r-mos-frontend/src/adjudication/__tests__/examMode.test.ts`
  - 考试扣分、强制修正、致命熔断、禁止重试。

**UI 落地**
- `r-mos-frontend/src/components/Maintenance/SOPPlayerAdjudicated.tsx`
  - 教学提示气泡（蓝色 Info Alert + 灯泡图标 + 重试按钮）。
  - 失败态兼容（FAILED 也显示红色错误信息）。
  - `onSummarize` 回调用于致命结算。
- `r-mos-frontend/src/pages/SOPMaintenancePage.tsx`
  - 顶部考试栏：倒计时 + 得分闪烁反馈。
  - 模式切换 Select + 二次确认，切换后 reset SOP 与评分。
  - 结果遮罩：全屏显示 reasonCode 与最终得分。

**验证结果**
- `npm test` 全绿。
- 考试扣分日志示例：`currentScore 100 -> 90`（见测试输出）。
- 额外覆盖：`allowContinue=false` 直接熔断并置 `FAILED_FATAL`。

**注意事项**
- 结果遮罩为 MVP（非路由页），后续可升级为 `/report` 页面。
- UI 提示与考试栏依赖 `operationMode`，切换时会重置评分与 SOP。
- `retryStep` 仅在 `FAILED` 状态生效（教学模式失败后）。

---

### 关键文件清单（P3/P4）
- 约束：`r-mos-frontend/src/adjudication/data/constraintGraph.ts`
- 评分：`r-mos-frontend/src/adjudication/core/scoringEngine.ts`
- 执行器：`r-mos-frontend/src/adjudication/executor/sopExecutor.ts`
- UI 页面：`r-mos-frontend/src/pages/SOPMaintenancePage.tsx`
- SOP 播放器：`r-mos-frontend/src/components/Maintenance/SOPPlayerAdjudicated.tsx`
- P4 测试：`r-mos-frontend/src/adjudication/__tests__/p4_mode.test.ts`、`r-mos-frontend/src/adjudication/__tests__/examMode.test.ts`
