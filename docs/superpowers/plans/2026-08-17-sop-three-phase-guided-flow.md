# SOP 三段式引导改造 实施计划

> **For agentic workers:** 本计划由 **Codex CLI** 逐 Task 执行，**Claude 监督验收**。步骤使用 checkbox（`- [ ]`）语法跟踪。每个 Task 必须走完自己的测试循环并通过 Claude 的验收门才能进入下一个。

---

## 📍 当前状态（接手先读这里）

**最后更新：** 2026-08-21 10:20 CST ｜ **分支：** `feat/sop-three-phase-flow` ｜ **未 push**

**下一步：** **Phase 1-4 已全部收官**。进入 **Phase 5 验收**，Task 5.1（E2E 与记录落库）。

> 📌 **待用户实机确认**：T4.2 的 22 步相机位是基于 `camera_presets` 标定值的**推导值**，未经逐步目视。用户需启动前后端打开维保工作台走一遍膝关节 SOP，对不满意的步骤提出调整。

> ⚠️ **Phase 4 与前三个 Phase 性质不同**：4.1/4.2 是**内容编排**（改 `seed_adjudication_sops.py`，22 步的分段、BOM、相机位全是手工活），不是写引擎代码。§7 已把「内容编排成本被低估」列为**最大风险**，T4.2 完成后需记录实际耗时，据此决定是否要做可视化编排器。**本轮只打穿膝关节这一条 SOP，不要扩大到其余 30 个。**

| Task | 名称 | 状态 | Commit | 备注 |
|---|---|---|---|---|
| 1.1 | `sop_steps` 四列 + 迁移 + ADR | ✅ 已验收 | `50f15ed9` | 3 passed；迁移已 upgrade 到 head |
| 1.2 | 前端裁决类型扩展 | ✅ 已验收 | `390f8104` | 4 passed；build PASS；由 Claude 实现（用户当时选定） |
| 2.1 | 装配方向裁决 | ✅ 已验收 | `616c9ca5` | Codex 实现；7 passed；含方向反转变异测试验证判别力 |
| 2.2 | 三个新 validation 分支 | ✅ 已验收 | `61c222ca` | Codex 实现；齐套+验收各正反 2 例，定向 8 passed |
| 2.3 | 螺丝对角紧固顺序判定 | ✅ 已验收 | `679f9f1b` | Codex 实现；定向 11 passed；变异测试证明顺序检测有判别力 |
| 2.4 | 阶段门 | ✅ 已验收 | `6db40437` | Codex 实现；定向 14 passed；变异测试证明门禁有效 |
| 3.1 | 三段进度条 | ✅ 已验收 | `0363e5c9` | Codex 实现；组件 66 行；单阶段守卫经变异测试验证 |
| 3.2 | 齐套检查面板 | ✅ 已验收 | `033af6d3` | Codex 实现；77 行；变异测试验证计数逻辑 |
| 3.3 | 验收记录面板 | ✅ 已验收 | `ad52ed71` | Codex 实现；55 行；两面板状态独立不串档 |
| 3.4 | `useSOPSceneSync` 读 `stepView` | ✅ 已验收 | `0cad4662` | Codex 实现；bindStep 陷阱已避开，经变异验证 |
| 4.1 | 膝关节 SOP 重编排为 22 步 | ✅ 已验收 | `603b48bf` | 22 步实证 4+14+4；存量 30 个 SOP 步骤数零变化 |
| 4.2 | 补 `step_view` 与 `required_parts` | ✅ 已验收 | `b940f9bf` | 相机位基于 camera_presets 标定值推导；**未经目视确认**，待用户实机查看 |
| 5.1 | E2E 与记录落库 | ⬜ 未开始 | — | **下一个**；Phase 5 收官在即 |
| 5.2 | 报告页两节 | ⬜ 未开始 | — | |

**当前基线（每次回归对齐这两个数，不要用文中其他地方的旧数字）：**

| 项 | 数值 | 测定时间 |
|---|---|---|
| 前端 `npm test` | **509 passed / 2 skipped**（68 files） | 2026-08-21，含 T3.4 新增 3 个 |
| 前端基线（不含本计划新增） | **477 passed / 2 skipped** | 2026-08-18 实测；计划初稿所写 465 已作废 |
| 后端 `pytest -k sop` | **41 passed** | 2026-08-21，T4.2 后 |

**已知遗留问题（不在本计划范围，勿顺手修）：**

- `src/adjudication/__tests__/` 下 8 个 `.test.ts` 不是 vitest 测试，从未执行，无外部调用方。存量 SOP 实际**没有**回归安全网。详见 §2.4 第 7 条。是否重写为独立工作项，**待决策**。
- **勾选结果直接 mutate SOP 脚本对象**：T3.2 的 `handleKitChange` 直接写 `kitValidation.params.confirmedItems`（T2.2/计划 §3.2 的设计就是让 executor 从这里读，故符合规格）。风险：若 SOP 脚本被 `useSOPScripts` 一类 hook 缓存或跨会话共享，勾选状态可能残留污染。T3.3 已同构实现并确认两面板状态互相独立、不串档；但「离开再返回同一 SOP 时历史勾选残留」仍**未验证，待观察**；若 Phase 3 联调发现串档，考虑改为 executor 侧的独立勾选状态。
- **存量兼容为间接覆盖**：T2.4 阶段门对单阶段 SOP 不触发，依据是条件 `nextStep.phase !== currentPhase` 恒为 false + 全量 498 绿（含 45 个走真实 SOP 流程的 characterization 测试），**无独立用例**。若将来修改阶段门触发条件，需补一个「单阶段 SOP 连续推进不被阻断」的显式用例。
- `AGENTS.md:6` 引用的 `docs/testing/ACCEPTANCE_CHARTER.md` **不存在**（该目录下只有 `TEST_PLAN.md` 与一份 acceptance-matrix）。悬空引用会让每个新执行会话反复困惑。修不修**待决策**，本计划的验收门禁以任务书 + §8 为准。

---

**Goal:** 参照 Menlo Asimov-1 手册的分步引导体验，把 R-MOS 维保 SOP 改造成「准备 → 执行 → 验证」三段式门禁流程，每步配作者化 3D 展示，每步做对才能进下一步。

**Architecture:** 复用现有裁决引擎，**不新建表、不新建状态机**。准备段与验证段本质上就是特殊步骤，走同一个 `SOPExecutor` 门禁。数据层只给 `sop_steps` 加 4 列；齐套与验收记录复用 `TaskStepResult` 现有证据字段。

**Tech Stack:** FastAPI + SQLAlchemy 2.0 (AsyncSession) + Alembic + PostgreSQL；React + TypeScript + Zustand + react-three-fiber；pytest + Vitest + Playwright。

**Spec:** 无独立 spec 文件——设计在对话中与用户逐条确认并批准，完整设计依据见本文档 §1「背景与目标」与 §2「现状核查结论」。

---

## Global Constraints

以下约束对**每一个** Task 隐式生效，不再逐 Task 重复：

- 仓库根目录：`/Users/xuhehong/Desktop/r-mos`
- Python 环境：**`r-mos-backend/venv`**（不是 `.venv`，不得用系统 Python）
- 后端测试：`cd r-mos-backend && source venv/bin/activate && pytest <路径> -v`
- 前端测试：`cd r-mos-frontend && npm test`（Vitest）；构建：`npm run build`
- 本机 HTTP 调用必须 `curl --noproxy 127.0.0.1,localhost`
- `DATABASE_URL` / CORS 配置**不得擅改**
- 允许 `git commit`（小步提交，一个 commit 只做一件事）；**未经用户许可严禁 `git push`**
- **严禁编造测试结果**，严禁写「应该通过」「看起来没问题」——必须贴真实命令与真实输出
- 每个 Task 结束必须向 `docs-archive/DEVELOPMENT_LOG.md` 追加一条记录，固定 8 字段：
  `DateTime` / `Task` / `Scope (files changed)` / `Commands Run` / `Tests` / `Result` / `Risks/Notes` / `Next Step`
- **每个 Task 结束必须同步更新本文档的 §📍 当前状态**（与提交同一批，不要留到最后）：
  1. 该 Task 行的**状态**改为 ✅ 已验收 / ⚠️ 有条件通过 / 🔄 进行中，填入 **Commit** 短哈希
  2. **下一步** 一行改成实际的下一个 Task，并写明动手前必读的注意事项
  3. **最后更新** 时间戳
  4. 若回归基线数字变化（新增/删除测试），更新**当前基线**表并注明测定时间
  5. 该 Task 章节内的 `- [ ]` 逐条改为 `- [x]`
  > 目的：任何人（或任何新会话）接手时，读 §📍 一节即可直接开工，无需重新审阅代码与 git log 来推断进度。**状态未更新的 Task 视为未完成。**
- **向后兼容是硬约束**：现有 31 个 SOP（其中 30 个为 `focus_step` 占位型）必须零改动照常运行。每个 Task 的验收都包含这一条回归。

---

## 1. 背景与目标

参照 Menlo Asimov-1 开源机器人手册（https://docs.menlo.ai/asimov/1）的分步引导式装配体验。其实际结构为三段线性门禁：

| 段 | 内容 | 出口条件 |
|---|---|---|
| **Parts Preparations** | 选路径(套件/自采购) → 开箱清点 → 验证出厂预处理 → 电子件&电池检查 → Module Kitting(按模块分料) → Final Readiness Check | 料、工具、软件、电机 ID 全部就位 |
| **Assemble** | Module(躯干/骨盆/臂/腿/头) → 每模块一张 Preparation 页(BOM 表 + 紧固件汇总 + 子装配划分) → Sub-assembly A/B/C → Step N | 装配完成 |
| **Verification** | 不带电（装配记录复核/机械安装/线束/电子电池）→ 不带电验证记录 → 带电（发现 25 个电机 → 电机归零 → 首次设置完成） | 通过端检 |

单步页格式：`Parts Needed` 表（件号 + 数量）→ 分段指令 → 上一步/下一步导航。

教学法要点：「You will only ever need to go forward」、「information appears before it is needed」、每段有明确 exit condition、Required 页（带 acceptance check）与 Reference 页分离、每段末尾有 **Record 页**沉淀记录。

**目标**：把这套结构落到 R-MOS 上，并利用 R-MOS 相对纯文档手册的优势——真几何判定 + 真约束图 + 真扣分，让「每步做对才能进下一步」是软件强制的，而非靠人自觉。

---

## 2. 现状核查结论

以下结论已逐条读代码核实，file:line 均准确可跳转。

### 2.1 引擎层——已具备，是本项目的核心资产

| 能力 | 位置 |
|---|---|
| `SOPStepAdjudication` 已有 preconditions / validations / requiredTool / failureReasons(teaching+exam 双响应) / onSuccess.stateTransition / isIrreversible / fatalOnFailure | `r-mos-frontend/src/adjudication/types/adjudication.ts:339` |
| `SOPExecutor` 状态机 IDLE→PRECONDITION_CHECK→EXECUTING→VALIDATION→COMPLETE/FAILED/BLOCKED；`canExecuteStep()` 硬门禁；`goToStep()` 只允许回跳已完成步骤，不可逆步骤禁止回滚 | `r-mos-frontend/src/adjudication/executor/sopExecutor.ts:296,607` |
| 约束图 6 类：fastened_by / covered_by / blocked_by / locked_by / wired_to / plugged_to | `adjudication.ts:56` |
| `SCREW_GEOMETRY_CONDITIONS`：按 M3×10 等规格给最小 Z 位移与旋转圈数 | `adjudication.ts:410` |
| `handleFailure()` 三模式 teaching/exam/maintenance，含扣分与致命锁定 | `sopExecutor.ts:708` |
| 后端已通链路：`/pipeline/diagnose` → `/tasks/from-diagnosis` → `/executions/{id}/steps/complete` → `/complete` → 自动出报告 | `r-mos-backend/app/api/v1/endpoints/pipeline.py:64-107` |
| 前端落库（从 URL query `execution_id` 取） | `r-mos-frontend/src/components/Maintenance/SOPPlayerAdjudicated.tsx:216` |
| `TaskStepResult` 已有 `evidence_type` / `evidence_value`(JSON) / `is_compliant` / `duration_seconds` | `r-mos-backend/app/models/task_execution.py:29` |
| 裁决格式 API 与映射器 | `sops.py:58` → `sop_service.py:255,308` |

### 2.2 四个真实缺口

1. **内容空。** `r-mos-backend/scripts/seed_adjudication_sops.py:315-450` —— 31 个 SOP 里 30 个是 `focus_step()` 拼的「定位检查点 1/2/3…结束确认」，action 全是 `FOCUS_CAMERA`，无真实前置/验证。只有 `knee-bearing-replace`（同文件 `:712`）是 6 步半真实流程。「回装」目前只是 `focus_step("回装定位", ...)` 相机移动，**没有任何装配方向的裁决**（对角紧固顺序、扭矩、复位对齐均无判定）。
2. **无准备阶段。** 全仓 grep 无 BOM/备件/物料概念（仅 `Part.bomCode` 字段与 `r-mos-frontend/src/data/toolData.ts` 注释出现字样）。有 `ToolSelector`（选单个工具）与 `SOPStep.tools_required`，但没有「作业前齐套检查门」。
3. **每步 3D 是启发式猜的。** `r-mos-frontend/src/adjudication/ui/useSOPSceneSync.ts:100-144` —— `deriveExplodeAmount()` 靠正则从步骤标题/描述文本里找 `%`、匹配关键词 `/收起|恢复正常|复位/` 推断爆炸系数；`resolveTargetPart()` 取 `targetParts` 第一个可解析项。无作者化的相机位/可见集/高亮。
4. **无模块→子装配层级，无 Record 页。** SOP → 扁平步骤；有考试结算与报告页，但没有结构化验收记录表。

**结论：可行，是「补齐」不是「重建」。**

### 2.3 已确认可以省掉的工作

`r-mos-frontend/src/api/sopScripts.ts` 把响应直接断言为 `SOPScriptAdjudication[]`，是纯类型透传。扩展 TS 类型后新字段自动流过，**不需要单独的 API 客户端改造 Task**。

### 2.4 执行期核查更正（2026-08-18，Claude 监督）

本计划初稿的若干技术前提经读码核实为**不成立**，已就地更正到对应 Task。列此备查，避免后续 Task 再次沿用错误前提。

| # | 计划原文断言 | 实际情况 | 影响 |
|---|---|---|---|
| 1 | 装配依赖取 `getBlockingConstraints(partId).map(c => c.constrainingPart)` | **方向相反**。该式查的是「谁压着本件」＝更外层、应后装的件。正确依赖是 `constrainingPart === partId` 的约束的 `constrainedPart` | T2.1 致命：照原文写门禁恒放行（最外层件依赖集为空） |
| 2 | store 有 `setPartState(id, {...})` | 只有 `setPartRemoved(id)` / `setPartDetached(id)`（`stateManager.ts:33-37`）；初始态全部件 `isRemoved: false` | T2.1 测试夹具 |
| 3 | 夹具用 `torso_link` 作 `frame_torso_chest` 的依赖 | 约束图中二者无关系；真实依赖为 `torso_motor` / `torso_pcb_main`（`constraintGraph.ts:273-298`） | T2.1 测试夹具 |
| 4 | `getScrewInstance` 已在 `decisionEngine.ts` 可用 | 存在于 `data/screwInstances.ts:12`，但 `decisionEngine.ts` **未导入** | T2.1 需加 import |
| 5 | 手写 `screw.screwSpec?.requiredTool` 比较工具 | `checkToolMatch(toolId, screwId)` 已存在且已导入（`geometryJudge.ts:252`） | T2.1 应复用 |
| 6 | 测试放 `src/adjudication/__tests__/` 即会执行 | 该目录在 `vitest.config.ts` 是**单文件白名单**，非 glob | T1.2 / T2.1 均需显式加行 |
| 7 | `decisionEngine.test.ts`、`hardwareSopsFlow.test.ts` 守护 30 个存量 SOP | 该目录 9 个 `.test.ts` 中 **8 个不是 vitest 测试**（`describe/it/test` 计数为 0），导出 `runTC001()` 一类手写断言函数，属自制 runner 遗留物，已 grep 确认无外部调用方，从未执行 | **存量 SOP 无安全网**；T2.1 回归口径需改 |
| 8 | 前端测试基线 465 | 实测 **477 passed / 2 skipped**（62 files，T1.2 前） | 各 Task 回归口径 |
| 9 | `RequiredPart.bomCode`（驼峰） | 后端 `requiredParts` 原样透传 `required_parts` JSON，不做 key 转换，实际为 **`bom_code`** | T1.2 已按 snake_case 落地 |
| 10 | 约束图里的零件/螺丝 ID 在测试中可直接查到 | **不成立**。`partRegistry` 是 manifest 注入层（默认 `null`），`constraintGraph` 是静态硬编码，两者数据源不同。不注入 manifest 则 `getScrewInstance()` 恒为 `undefined` | T2.1 螺丝用例全判 `UNKNOWN_SCREW`；**已由 Codex 执行时发现并上报** |
| 11 | `resetState()` 会重建 `partStates` | **不成立**。`INITIAL_STATE` 是模块级常量（`stateManager.ts:141`），import 时求值一次；`getAllPartIds()` 无 manifest 时返回 `[]`，故 `partStates` 恒为 `{}`，注入 manifest 也改不了 | T2.1 首轮 4 个「通过」中有 2 个是 `undefined` 巧合造成的**假阳性** |

| 12 | T4.1 测试 `from ... import build_knee_bearing_sop` | **该函数不存在**。膝关节 SOP 是模块级字典常量 `SOP_KNEE_BEARING`（`:711`），步骤由 `_make_knee_step(:680)` 构造，后者把 `expected_action` 写死为 `focus_camera`、`validations` 写死为 `[]` | T4.1 需改为 import 常量，并扩展 `_make_knee_step` 参数 |

| 13 | T5.1「`StepCompleteRequest` 增 `evidence_type` / `evidence_value` / `is_compliant`，写入 `TaskStepResult`」 | 前两个字段**端点层已存在**（`pipeline.py:46-47`，连同 `duration_seconds`），只缺 `is_compliant`；且真正的落库在 `services/pipeline/task_pipeline_service.py:97`，那里把 `is_compliant=True` **硬编码**。只改端点层无法落 `False` | T5.1 授权清单需加 `task_pipeline_service.py`；**由 Codex 执行时发现并上报** |

| 14 | T5.1 E2E 场景「螺丝乱序拧紧被拒」可在 UI 上复现 | **不可行**。`ScrewInfo.tsx:60-90` 的 `screwData` 是**按规格聚合**的（标题显示「N 种」，每项显示 `×quantity`），`item.screwId` 只是该规格的代表性 ID，UI 上**没有单颗螺丝粒度**，无法表达「先拧第 1 颗再拧第 2 颗」。加 `data-testid` 也无济于事——数据本身就没有这个维度 | **该 E2E 场景已裁决剔除**（见下）；由 Codex 执行时发现并上报 |

> **第 14 项的裁决（2026-08-21，Claude）**：E2E **不覆盖**「螺丝乱序被拒」场景，其余三个场景照常覆盖。理由：① 该判定已由 T2.3 的 3 个单测覆盖，并经方向变异测试（移除错位检测 → 用例变红）证明有判别力，E2E 重复测它属冗余；② E2E 的价值在验证集成链路（前端→后端→落库），不在重复裁决逻辑；③ 改造 `ScrewInfo` 支持单颗螺丝交互会改变 UI 与数据结构，属产品决策，不应塞进验收 Task。
>
> **遗留**：若将来要做真正的「对角紧固」交互教学（让学生逐颗点击），必须先让 `ScrewInfo` 支持单颗粒度——当前引擎侧 `SCREW_ORDER_MATCHED` 已就绪，缺的是 UI 与数据。**待决策**。

> 第 10、11 项是 §2.4 首轮核查（第 1-9 项）**遗漏**的：当时核对了函数签名与约束数据，但未验证测试运行时这些 ID 是否真能被解析。教训：**验签名不等于验数据可达性**，涉及注入式 registry 的测试要单独确认夹具注入路径。

> 第 7 项衍生出一个**计划外独立工作项**：是否把这 8 个遗留文件重写为 vitest 测试，从而真正建立存量 SOP 安全网。工作量未评估，需单独决策，不在本计划范围内。

---

## 3. 设计决策

### 3.1 数据模型：4 列，0 新表

`sop_steps` 表（`r-mos-backend/app/models/sop.py` 的 `SOPStep`）增 4 列：

| 列 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `phase` | `String(20)` | `'execute'` | `prep` / `execute` / `verify`。默认 `execute` 使 30 个老 SOP 自动归入执行段，向后兼容 |
| `group_path` | `String(200)` | `NULL` | 如 `torso/sub_a`，模块→子装配两级 |
| `step_view` | `JSON` | `NULL` | 作者化 3D 构图；为空时回落现有启发式 |
| `required_parts` | `JSON` | `NULL` | `[{bom_code, name, qty, note}]`；SOP 级 BOM 由前端聚合，不建表 |

`step_view` 结构：

```json
{
  "camera": { "position": [1.2, 0.8, 1.5], "target": [0, 0.4, 0], "fov": 45 },
  "visibleLinks": ["left_knee_link", "left_thigh_pitch_link"],
  "highlight": ["left_knee_link"],
  "explode": 0.45,
  "screwFocus": ["screw_left_knee_m4x8_001"]
}
```

字段全部可选，缺省项回落到现有行为。

### 3.2 三段式为什么不需要新状态机

准备段与验证段的每一项本质上就是一个步骤，只是 action 类型不同：

- 齐套确认 → `ActionType.CONFIRM_KIT` + `ValidationType.KIT_CONFIRMED`
- 验收勾选 → `ActionType.VERIFY_CHECK` + `ValidationType.CHECKLIST_CONFIRMED`

它们走同一个 `SOPExecutor.canExecuteStep() → executeStep() → validateAndAdvance()` 循环，完全复用既有门禁。**引擎唯一的真改动是装配方向裁决**（T2.1）。

### 3.3 记录沉淀复用现有字段

齐套勾选结果与验收清单结果直接写入 `TaskStepResult.evidence_value`（JSON），`evidence_type` 分别取 `kit_checklist` / `verify_checklist`，`is_compliant` 记录是否全部通过。零新增持久化。

---

## 4. File Structure

### 新建

| 文件 | 职责 |
|---|---|
| `r-mos-backend/alembic/versions/20260817_sop_three_phase_columns.py` | 4 列迁移 |
| `docs/adr/ADR-2026-08-17-sop-three-phase-schema.md` | 表结构变更 ADR（AGENTS.md §6 触发） |
| `r-mos-backend/tests/test_sop_three_phase.py` | 后端字段与映射测试 |
| `r-mos-frontend/src/components/Maintenance/KitChecklistPanel.tsx` | 齐套检查面板（工具 + 备件勾选） |
| `r-mos-frontend/src/components/Maintenance/VerifyChecklistPanel.tsx` | 验收记录面板 |
| `r-mos-frontend/src/adjudication/__tests__/threePhase.test.ts` | 阶段门 + 齐套 + 顺序判定测试 |
| `r-mos-frontend/src/adjudication/__tests__/assemblyDirection.test.ts` | 装配方向裁决测试 |

### 修改

| 文件 | 改动 |
|---|---|
| `r-mos-backend/app/models/sop.py` | `SOPStep` 加 4 列 |
| `r-mos-backend/app/schemas/sop.py` | `SOPStepBase` + `SOPAdjudicationStepResponse` 加 4 字段 |
| `r-mos-backend/app/services/sop_service.py:255` | `_sop_to_adjudication` 映射 4 字段 |
| `r-mos-backend/scripts/seed_adjudication_sops.py` | 膝关节 SOP 重编排为 22 步三段式 |
| `r-mos-frontend/src/adjudication/types/adjudication.ts` | `StepView` 类型、`SOPStepAdjudication` 4 字段、4 个 `ActionType`、3 个 `ValidationType` |
| `r-mos-frontend/src/adjudication/core/decisionEngine.ts` | 装配方向裁决 |
| `r-mos-frontend/src/adjudication/executor/sopExecutor.ts` | 3 个 validation 分支 + 阶段门 |
| `r-mos-frontend/src/adjudication/ui/useSOPSceneSync.ts:146` | `buildIntent()` 优先读 `stepView` |
| `r-mos-frontend/src/components/Maintenance/SOPPlayerAdjudicated.tsx` | 三段进度条 + 两个面板挂载 |
| `r-mos-frontend/src/pages/ReportPage.tsx` | 齐套记录 + 验收记录两节 |

---

## Phase 1 — 数据与类型

### Task 1.1: `sop_steps` 四列 + 迁移 + ADR

**Files:**
- Modify: `r-mos-backend/app/models/sop.py`（`SOPStep` 类，当前 `tools_required` 之后）
- Modify: `r-mos-backend/app/schemas/sop.py:10-23`（`SOPStepBase`）、`:147-161`（`SOPAdjudicationStepResponse`）
- Modify: `r-mos-backend/app/services/sop_service.py:281-296`（`_sop_to_adjudication` 的 `adj_steps.append`）
- Create: `r-mos-backend/alembic/versions/20260817_sop_three_phase_columns.py`
- Create: `docs/adr/ADR-2026-08-17-sop-three-phase-schema.md`
- Test: `r-mos-backend/tests/test_sop_three_phase.py`

**Interfaces:**
- Produces：`SOPAdjudicationStepResponse` 新增 4 个字段，供前端 `SOPStepAdjudication` 消费（T1.2）：
  - `phase: str = "execute"`
  - `groupPath: Optional[str] = None`
  - `stepView: Optional[Dict[str, Any]] = None`
  - `requiredParts: List[Dict[str, Any]] = []`

- [x] **Step 1: 写失败测试**

创建 `r-mos-backend/tests/test_sop_three_phase.py`：

```python
"""SOP 三段式字段的模型与映射测试。"""
import pytest
from app.models.sop import SOP, SOPStep
from app.services.sop_service import SOPService


def _make_step(**overrides):
    defaults = dict(
        id=1, sop_id=1, step_index=1, title="齐套确认",
        description="确认工具与备件齐套", expected_action="confirm_kit",
    )
    defaults.update(overrides)
    return SOPStep(**defaults)


def test_sop_step_phase_defaults_to_execute():
    """老数据不带 phase 时必须落在 execute 段，保证 30 个存量 SOP 不受影响。"""
    step = _make_step()
    assert step.phase is None or step.phase == "execute"


def test_sop_step_accepts_three_phase_columns():
    step = _make_step(
        phase="prep",
        group_path="knee/sub_a",
        step_view={"camera": {"position": [1.0, 0.5, 1.2], "target": [0, 0.4, 0], "fov": 45},
                   "highlight": ["left_knee_link"], "explode": 0.4},
        required_parts=[{"bom_code": "6205-2RS", "name": "深沟球轴承", "qty": 1, "note": "更换件"}],
    )
    assert step.phase == "prep"
    assert step.group_path == "knee/sub_a"
    assert step.step_view["explode"] == 0.4
    assert step.required_parts[0]["bom_code"] == "6205-2RS"


def test_adjudication_mapper_emits_three_phase_fields():
    """映射器必须把 4 个新字段透传到裁决格式，缺省时给安全默认值。"""
    sop = SOP(id=7, name="测试 SOP", applicable_model="ATOM-01",
              version="1.0", target_module="knee", difficulty_level="medium",
              estimated_time=600)
    sop.steps = [
        _make_step(id=11, phase="prep", group_path="knee/sub_a",
                   step_view={"explode": 0.4},
                   required_parts=[{"bom_code": "6205-2RS", "name": "轴承", "qty": 1}]),
        _make_step(id=12, step_index=2, title="老步骤", phase=None),
    ]
    result = SOPService.__new__(SOPService)._sop_to_adjudication(sop)
    assert result.steps[0].phase == "prep"
    assert result.steps[0].groupPath == "knee/sub_a"
    assert result.steps[0].stepView == {"explode": 0.4}
    assert result.steps[0].requiredParts[0]["bom_code"] == "6205-2RS"
    # 存量步骤：phase 缺省回落 execute，其余为空
    assert result.steps[1].phase == "execute"
    assert result.steps[1].groupPath is None
    assert result.steps[1].stepView is None
    assert result.steps[1].requiredParts == []
```

- [x] **Step 2: 跑测试确认失败**

```bash
cd r-mos-backend && source venv/bin/activate && pytest tests/test_sop_three_phase.py -v
```

Expected: FAIL —— `TypeError: 'phase' is an invalid keyword argument for SOPStep`

- [x] **Step 3: 加模型列**

在 `r-mos-backend/app/models/sop.py` 的 `SOPStep` 类中，`tools_required` 之后追加：

```python
    # 三段式引导（2026-08-17）
    phase = Column(String(20), nullable=False, server_default="execute",
                   comment="阶段：prep/execute/verify")
    group_path = Column(String(200), nullable=True, comment="模块/子装配路径，如 torso/sub_a")
    step_view = Column(JSON, nullable=True, comment="作者化 3D 构图（相机/可见集/高亮/爆炸）")
    required_parts = Column(JSON, nullable=True, comment="本步所需物料 [{bom_code,name,qty,note}]")
```

- [x] **Step 4: 加 Pydantic 字段**

`r-mos-backend/app/schemas/sop.py` 的 `SOPStepBase`（`tools_required` 之后）追加：

```python
    phase: str = Field("execute", description="阶段：prep/execute/verify")
    group_path: Optional[str] = Field(None, max_length=200, description="模块/子装配路径")
    step_view: Optional[Dict[str, Any]] = Field(None, description="作者化 3D 构图")
    required_parts: Optional[List[Dict[str, Any]]] = Field(None, description="本步所需物料")
```

同文件 `SOPAdjudicationStepResponse`（`fatalOnFailure` 之后）追加：

```python
    phase: str = "execute"
    groupPath: Optional[str] = None
    stepView: Optional[Dict[str, Any]] = None
    requiredParts: List[Dict[str, Any]] = Field(default_factory=list)
```

- [x] **Step 5: 改映射器**

`r-mos-backend/app/services/sop_service.py` 的 `_sop_to_adjudication`，在 `adj_steps.append(SOPAdjudicationStepResponse(...))` 里 `fatalOnFailure=step.is_critical,` 之后追加：

```python
                phase=step.phase or "execute",
                groupPath=step.group_path,
                stepView=step.step_view,
                requiredParts=step.required_parts or [],
```

- [x] **Step 6: 写 Alembic 迁移**

创建 `r-mos-backend/alembic/versions/20260817_sop_three_phase_columns.py`。**先确认当前 head**：

```bash
cd r-mos-backend && source venv/bin/activate && alembic heads
```

把输出的 revision 填进 `down_revision`：

```python
"""add three-phase columns to sop_steps

Revision ID: 20260817_sop_three_phase
Revises: <把 alembic heads 的输出填这里>
"""
import sqlalchemy as sa
from alembic import op

revision = "20260817_sop_three_phase"
down_revision = "<把 alembic heads 的输出填这里>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sop_steps", sa.Column("phase", sa.String(20), nullable=False,
                                         server_default="execute"))
    op.add_column("sop_steps", sa.Column("group_path", sa.String(200), nullable=True))
    op.add_column("sop_steps", sa.Column("step_view", sa.JSON(), nullable=True))
    op.add_column("sop_steps", sa.Column("required_parts", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("sop_steps", "required_parts")
    op.drop_column("sop_steps", "step_view")
    op.drop_column("sop_steps", "group_path")
    op.drop_column("sop_steps", "phase")
```

> `server_default="execute"` 是向后兼容的关键：存量 31 个 SOP 的所有步骤自动落入执行段。

- [x] **Step 7: 跑测试确认通过**

```bash
cd r-mos-backend && source venv/bin/activate && pytest tests/test_sop_three_phase.py -v
```

Expected: 3 passed

- [x] **Step 8: 跑迁移并验证**

```bash
cd r-mos-backend && source venv/bin/activate && alembic upgrade head && alembic current
```

Expected: 当前 revision 为 `20260817_sop_three_phase`

- [x] **Step 9: 存量 SOP 回归（必做）**

```bash
cd r-mos-backend && source venv/bin/activate && pytest tests/ -v -k "sop"
```

Expected: 全绿，无因新字段导致的失败

- [x] **Step 10: 写 ADR**

创建 `docs/adr/ADR-2026-08-17-sop-three-phase-schema.md`，按 AGENTS.md §6 要求含六节：**背景**（Asimov-1 三段式引导改造需要阶段与构图元数据）、**决策**（`sop_steps` 加 4 列，不新建表）、**备选**（新建 `sop_phases` + `sop_step_views` 关联表 / 全部塞进现有 `action_params` JSON）、**影响**（后端模型/schema/映射器、前端类型、31 个存量 SOP）、**迁移策略**（`server_default="execute"` 使存量数据自动归位，无需数据回填）、**回滚策略**（`alembic downgrade -1` 直接删 4 列，无数据损失，因存量数据不使用这些列）。

- [x] **Step 11: 提交**

```bash
git add r-mos-backend/app/models/sop.py r-mos-backend/app/schemas/sop.py \
        r-mos-backend/app/services/sop_service.py \
        r-mos-backend/alembic/versions/20260817_sop_three_phase_columns.py \
        r-mos-backend/tests/test_sop_three_phase.py \
        docs/adr/ADR-2026-08-17-sop-three-phase-schema.md
git commit -m "feat(sop): sop_steps 增加三段式引导四列（phase/group_path/step_view/required_parts）"
```

- [x] **Step 12: 追加开发日志**

按 8 字段格式追加到 `docs-archive/DEVELOPMENT_LOG.md`。

---

### Task 1.2: 前端裁决类型扩展

**Files:**
- Modify: `r-mos-frontend/src/adjudication/types/adjudication.ts`（`ActionType` `:134`、`ValidationType` `:293`、`SOPStepAdjudication` `:339`）
- Test: `r-mos-frontend/src/adjudication/__tests__/threePhase.test.ts`（新建，本 Task 只写类型相关用例）

**Interfaces:**
- Consumes：T1.1 产出的 `SOPAdjudicationStepResponse` 4 字段（JSON 经 `sopScripts.ts` 纯类型透传直达）
- Produces（后续 Task 全部依赖这些精确名称）：
  - `export interface StepView`
  - `SOPStepAdjudication.phase: SOPPhase`、`.groupPath?: string`、`.stepView?: StepView`、`.requiredParts?: RequiredPart[]`
  - `ActionType.CONFIRM_KIT = 'confirm_kit'`、`.INSTALL_PART = 'install_part'`、`.TIGHTEN_SCREW = 'tighten_screw'`、`.VERIFY_CHECK = 'verify_check'`
  - `ValidationType.KIT_CONFIRMED = 'kit_confirmed'`、`.SCREW_ORDER_MATCHED = 'screw_order_matched'`、`.CHECKLIST_CONFIRMED = 'checklist_confirmed'`

- [x] **Step 1: 写失败测试**

创建 `r-mos-frontend/src/adjudication/__tests__/threePhase.test.ts`：

```typescript
import { describe, it, expect } from 'vitest';
import {
    ActionType,
    ValidationType,
    type StepView,
    type SOPStepAdjudication,
} from '../types/adjudication';

describe('三段式类型扩展', () => {
    it('新增四个 ActionType', () => {
        expect(ActionType.CONFIRM_KIT).toBe('confirm_kit');
        expect(ActionType.INSTALL_PART).toBe('install_part');
        expect(ActionType.TIGHTEN_SCREW).toBe('tighten_screw');
        expect(ActionType.VERIFY_CHECK).toBe('verify_check');
    });

    it('新增三个 ValidationType', () => {
        expect(ValidationType.KIT_CONFIRMED).toBe('kit_confirmed');
        expect(ValidationType.SCREW_ORDER_MATCHED).toBe('screw_order_matched');
        expect(ValidationType.CHECKLIST_CONFIRMED).toBe('checklist_confirmed');
    });

    it('StepView 全字段可选，允许只给 explode', () => {
        const minimal: StepView = { explode: 0.4 };
        const full: StepView = {
            camera: { position: [1, 0.5, 1.2], target: [0, 0.4, 0], fov: 45 },
            visibleLinks: ['left_knee_link'],
            highlight: ['left_knee_link'],
            explode: 0.45,
            screwFocus: ['screw_left_knee_m4x8_001'],
        };
        expect(minimal.explode).toBe(0.4);
        expect(full.camera?.fov).toBe(45);
    });

    it('SOPStepAdjudication 携带 phase 与物料，groupPath/stepView 可缺省', () => {
        const step = {
            phase: 'prep',
            requiredParts: [{ bomCode: '6205-2RS', name: '深沟球轴承', qty: 1 }],
        } as Partial<SOPStepAdjudication>;
        expect(step.phase).toBe('prep');
        expect(step.requiredParts?.[0].bomCode).toBe('6205-2RS');
    });
});
```

- [x] **Step 2: 跑测试确认失败**

```bash
cd r-mos-frontend && npx vitest run src/adjudication/__tests__/threePhase.test.ts
```

Expected: FAIL —— `ActionType.CONFIRM_KIT` undefined

- [x] **Step 3: 扩展枚举**

`r-mos-frontend/src/adjudication/types/adjudication.ts` 的 `ActionType`（`FOCUS_CAMERA` 之后）追加：

```typescript
  // 准备/装配/验证（三段式引导）
  CONFIRM_KIT = 'confirm_kit',           // 齐套确认（工具+备件）
  INSTALL_PART = 'install_part',         // 装回零件
  TIGHTEN_SCREW = 'tighten_screw',       // 拧紧螺丝
  VERIFY_CHECK = 'verify_check'          // 验收勾选
```

`ValidationType`（`STATE_CHECK` 之后）追加：

```typescript
  KIT_CONFIRMED = 'kit_confirmed',               // 齐套项全部勾选
  SCREW_ORDER_MATCHED = 'screw_order_matched',   // 螺丝紧固顺序匹配
  CHECKLIST_CONFIRMED = 'checklist_confirmed'    // 验收清单全部勾选
```

- [x] **Step 4: 加类型**

同文件，在 `SOPStepAdjudication` 定义之前插入：

```typescript
/** 步骤所属阶段 */
export type SOPPhase = 'prep' | 'execute' | 'verify';

/** 作者化 3D 构图；全字段可选，缺省项回落到启发式推断 */
export interface StepView {
  camera?: {
    position: [number, number, number];
    target: [number, number, number];
    fov: number;
  };
  visibleLinks?: string[];   // 本步可见的 link 白名单
  highlight?: string[];      // 高亮零件
  explode?: number;          // 爆炸系数 0~1
  screwFocus?: string[];     // 聚焦螺丝实例
}

/** 本步所需物料（BOM 行） */
export interface RequiredPart {
  bomCode: string;
  name: string;
  qty: number;
  note?: string;
}
```

在 `SOPStepAdjudication` 里 `fatalOnFailure?: boolean;` 之后追加：

```typescript
  // 三段式引导
  phase: SOPPhase;                       // 缺省由后端给 'execute'
  groupPath?: string;                    // "torso/sub_a"
  stepView?: StepView;                   // 为空则回落启发式
  requiredParts?: RequiredPart[];        // 齐套检查数据源
```

> ⚠️ `phase` 为必填。后端 `SOPAdjudicationStepResponse.phase` 有默认值 `"execute"`，恒有值。若 TS 编译报现有构造缺 `phase`，说明有硬编码的 SOP 脚本对象——给它们补 `phase: 'execute'`，**不要**把字段改成可选。

- [x] **Step 5: 跑测试确认通过**

```bash
cd r-mos-frontend && npx vitest run src/adjudication/__tests__/threePhase.test.ts
```

Expected: 4 passed

- [x] **Step 6: 全量类型检查 + 存量回归（必做）**

```bash
cd r-mos-frontend && npm run build && npm test
```

Expected: build PASS；`npm test` 全绿（基线 465）

- [x] **Step 7: 提交 + 追加开发日志**

```bash
git add r-mos-frontend/src/adjudication/types/adjudication.ts \
        r-mos-frontend/src/adjudication/__tests__/threePhase.test.ts
git commit -m "feat(adjudication): 扩展三段式类型（StepView/SOPPhase/RequiredPart + 7 个枚举）"
```

---

## Phase 2 — 引擎

### Task 2.1: 装配方向裁决

这是本轮**唯一的真引擎改动**。现有 `decisionEngine.ts` 只判拆卸方向：「要拆 A，A 上的约束是否已解除」。装配是它的逆：「要装 A，A 依赖的件是否已就位」。

**Files:**
- Modify: `r-mos-frontend/src/adjudication/core/decisionEngine.ts`（在 `canDetachPart` `:389` 之后新增；`adjudicateAction` `:458` 加分支）
- Test: `r-mos-frontend/src/adjudication/__tests__/assemblyDirection.test.ts`（新建）

**Interfaces:**
- Consumes：T1.2 的 `ActionType.INSTALL_PART` / `ActionType.TIGHTEN_SCREW`
- Produces：
  - `export function canInstallPart(partId: string): AdjudicationReport`
  - `export function canTightenScrew(screwId: string, toolId: string | null): AdjudicationReport`

> ⚠️ **本 Task 规格已按代码核查结果整体更正（2026-08-18，Claude 监督核查）。** 原文的依赖方向、store API、测试夹具三处均与实际代码不符，照原文写必然产出错误实现。以下为核对过 file:line 的版本，**请以此为准**。核查明细见 §2.4。
>
> **不要**参照 `decisionEngine.test.ts` 抄夹具写法——该文件不是 vitest 测试（见 T2.1 Step 6 的更正说明）。

- [x] **Step 1: 写失败测试**

创建 `r-mos-frontend/src/adjudication/__tests__/assemblyDirection.test.ts`。

**夹具必须基于真实约束数据**（`constraintGraph.ts:273-298`）：

```
constrainedPart: torso_motor       constrainingPart: frame_torso_chest   (COVERED_BY)
constrainedPart: torso_pcb_main    constrainingPart: frame_torso_chest   (COVERED_BY)
constrainedPart: frame_torso_chest constrainingPart: screw_torso_m3x10_001 (FASTENED_BY)
```

读作：胸甲 `frame_torso_chest` 压着电机与主板；螺丝 `screw_torso_m3x10_001` 固定胸甲。故装胸甲前电机与主板须先就位；拧该螺丝前胸甲须先就位。

**store 写接口**：实际暴露的是 `setPartRemoved(partId)` / `setPartDetached(partId)`（`stateManager.ts:33-37`），**没有** `setPartState`。「未就位」场景用 `setPartRemoved` 主动构造。

> 🛑 **必须注入 manifest 夹具，否则测试是假的（2026-08-18 第二轮更正）。**
>
> `partRegistry.ts` 是 **manifest 注入层**（`:11-32`），`_manifestPartRegistry` 默认 `null`；`constraintGraph.ts` 则是**纯静态硬编码**（`ALL_CONSTRAINTS`，`:317`，无注入层）。二者数据来源不同：**约束图里写着某个螺丝，不代表注册表能查到它**。不注入 manifest 时 `getScrewInstance()` 恒返回 `undefined`，所有螺丝用例被判 `UNKNOWN_SCREW`。
>
> 更隐蔽的一点：`getAllPartIds()` 在无 manifest 时返回 `[]`（`partRegistry.ts:77`），于是 `createInitialPartStates()` 产出**空对象**。而 `INITIAL_STATE` 是**模块级常量**（`stateManager.ts:141`），在 import 时求值一次，`resetState()` 恢复的就是它——**注入 manifest 也不会让 `partStates` 长出数据**。
>
> 由此，本测试中「零件在位」由**未对其调用 `setPartRemoved`** 表达（`partStates[id]` 为 `undefined`，实现里 `!== true` 视为在位），而非由 `isRemoved: false` 表达。这是既有设计，**不要为此改生产代码**。

**夹具 ID 必须与静态约束图一致**，并用 `spec.required_tool` 固定工具值（从而无需猜测 `hex_2.5` 还是别的）：

```typescript
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { injectManifestPartRegistry, clearManifestPartRegistry } from '../data/partRegistry';
import type { RobotDataManifest } from '@/components/Viewer3D/assemblyManifest';

/** 最小夹具：ID 与 constraintGraph.ts:273-298 的静态约束对齐 */
function makeTorsoManifest(): RobotDataManifest {
    const part = (id: string, category: string) => ({
        id, category, bom_code: `BOM-${id}`, display_name: id,
        parent_id: null, mesh_id: null,
        local_position: [0, 0, 0], local_rotation: [0, 0, 0], group: 'torso',
    });
    return {
        version: '1.0', robotId: '42', rootNodeId: 'base_link',
        mesh_catalog: {}, nodes: [], fastener_instances: [],
        parts_registry: [
            part('frame_torso_chest', 'frame'),
            part('torso_motor', 'motor'),
            part('torso_pcb_main', 'pcb'),
        ],
        screw_instances: [{
            id: 'screw_torso_m3x10_001',
            bom_code: 'SCR-M3x10',
            parent_id: 'frame_torso_chest',
            position: [0, 0, 0], axis: [0, 0, 1],
            spec: {
                type: 'M3×10', pitch: 0.5, thread_length: 10,
                required_tool: 'hex_2.5', torque_nm: 1.2,
            },
        }],
    } as unknown as RobotDataManifest;
}

beforeEach(() => {
    injectManifestPartRegistry(makeTorsoManifest());
    useAdjudicationStore.getState().resetState();
});

afterEach(() => {
    clearManifestPartRegistry();   // 防止污染同进程其它测试
});
```

夹具已把 `required_tool` 定为 `hex_2.5`，故「工具匹配」用例传 `'hex_2.5'`、「工具不匹配」用例传 `'hex_3'`，无需再核对真实数据。

```typescript
import { describe, it, expect, beforeEach } from 'vitest';
import { canInstallPart, canTightenScrew } from '../core/decisionEngine';
import { useAdjudicationStore } from '../core/stateManager';
import { AdjudicationResult } from '../types/adjudication';

describe('装配方向裁决', () => {
    beforeEach(() => {
        useAdjudicationStore.getState().resetState();
    });

    it('零件已在位时无需重复安装', () => {
        const report = canInstallPart('frame_torso_chest');
        expect(report.result).toBe(AdjudicationResult.INCOMPLETE);
        expect(report.reasonCode).toBe('ALREADY_INSTALLED');
    });

    it('依赖件未就位时，禁止安装', () => {
        const store = useAdjudicationStore.getState();
        store.setPartRemoved('frame_torso_chest');   // 胸甲已拆，待装回
        store.setPartRemoved('torso_motor');         // 但它压着的电机还没装回

        const report = canInstallPart('frame_torso_chest');
        expect(report.result).toBe(AdjudicationResult.BLOCKED);
        expect(report.reasonCode).toBe('INSTALL_ORDER_VIOLATION');
        expect(report.reason).toContain('torso_motor');
        expect(report.requiredActions.length).toBeGreaterThan(0);
    });

    it('依赖件全部就位后，允许安装', () => {
        const store = useAdjudicationStore.getState();
        store.setPartRemoved('frame_torso_chest');   // 只有胸甲待装，内层件均在位

        const report = canInstallPart('frame_torso_chest');
        expect(report.result).toBe(AdjudicationResult.ALLOWED);
    });

    it('拧紧螺丝要求所固定的零件已就位', () => {
        const store = useAdjudicationStore.getState();
        store.setPartRemoved('frame_torso_chest');

        const report = canTightenScrew('screw_torso_m3x10_001', 'hex_2.5');
        expect(report.result).toBe(AdjudicationResult.BLOCKED);
        expect(report.reasonCode).toBe('HOST_NOT_INSTALLED');
        expect(report.reason).toContain('frame_torso_chest');
    });

    it('宿主零件在位时允许拧紧', () => {
        const report = canTightenScrew('screw_torso_m3x10_001', 'hex_2.5');
        expect(report.result).toBe(AdjudicationResult.ALLOWED);
    });

    it('工具不匹配时拧紧被拒', () => {
        const report = canTightenScrew('screw_torso_m3x10_001', 'hex_3');
        expect(report.result).toBe(AdjudicationResult.TOOL_MISMATCH);
    });

    it('未知螺丝被拒', () => {
        const report = canTightenScrew('screw_does_not_exist', 'hex_2.5');
        expect(report.result).toBe(AdjudicationResult.BLOCKED);
        expect(report.reasonCode).toBe('UNKNOWN_SCREW');
    });
});
```

> ✅ 工具值不再需要核对：夹具的 `spec.required_tool` 已固定为 `hex_2.5`（见上方 manifest 夹具）。

- [x] **Step 1b: 把测试文件纳入 vitest include（否则不会被执行）**

`vitest.config.ts` 的 `include` 对 `src/adjudication/__tests__/` 是**单文件白名单**，不是 glob。仿照 T1.2 已加的 `threePhase.test.ts` 追加一行：

```typescript
      "src/adjudication/__tests__/assemblyDirection.test.ts",
```

**不要**改成 `src/adjudication/__tests__/**/*.test.{ts,tsx}`——那会拖进 8 个非 vitest 的遗留文件，全部报 "No test suite found"。

- [x] **Step 2: 跑测试确认失败**

```bash
cd r-mos-frontend && npx vitest run src/adjudication/__tests__/assemblyDirection.test.ts
```

Expected: FAIL —— `canInstallPart is not a function`

- [x] **Step 3: 实现装配方向裁决**

在 `decisionEngine.ts` 的 `canDetachPart`（`:389`）之后追加。

> 🛑 **原文此处的依赖方向是错的，已更正。** 原文让依赖取 `getBlockingConstraints(partId, DETACH_PART).map(c => c.constrainingPart)`——那查的是「**谁压着我、挡着我被拆下来**」，即比本件更外层、应当**在本件之后**才安装的零件。照此实现会要求外层件先就位，把装配顺序颠倒成拆卸顺序，与本 Task 目标恰好相反。
>
> **正确方向**：装 X 的依赖 = 「**X 压着谁、固定着谁**」，即所有 `constrainingPart === X` 的约束的 `constrainedPart`。
>
> 以真实数据验证：`frame_torso_chest` 作为 `constrainingPart` 覆盖 `torso_motor` 与 `torso_pcb_main`。装胸甲前，电机与主板必须先就位 ✓。而原文写法会取到「覆盖胸甲的件」，胸甲是最外层，结果为空集，任何时候都放行——门禁完全失效。

核心逻辑：**装配依赖 = 本件在约束图中作为「施加约束方」所指向的那些被约束件**，要求它们全部已就位（`isRemoved !== true`）。

`canInstallPart` 与 `canTightenScrew` 共用同一条规则（螺丝在 `FASTENED_BY` 里正是 `constrainingPart`），故抽一个私有 helper，不要写两遍：

```typescript
/**
 * 装配依赖：本件在约束图中压着/固定着的那些零件，必须先于本件就位。
 *
 * 拆卸问「谁挡着我」（constrainedPart === X 的约束），
 * 装配问「我压着谁」（constrainingPart === X 的约束）——二者互为逆序。
 */
function getInstallDependencies(partId: string): string[] {
    return getAllConstraints()
        .filter((c) => c.constrainingPart === partId)
        .map((c) => c.constrainedPart);
}
```

`getAllConstraints` 已在 `decisionEngine.ts:24` 导入，无需新增。

```typescript
/**
 * 装配方向：判断零件能否装回。
 *
 * 拆卸判「约束是否已解除」，装配判「依赖件是否已就位」。
 */
export function canInstallPart(partId: string): AdjudicationReport {
    const store = useAdjudicationStore.getState();

    if (store.partStates[partId]?.isRemoved !== true) {
        return createReport(AdjudicationResult.INCOMPLETE, partId,
            '该零件已在位', 'ALREADY_INSTALLED');
    }

    const missing = getInstallDependencies(partId).filter(
        (depId) => store.partStates[depId]?.isRemoved === true
    );

    if (missing.length > 0) {
        return createReport(
            AdjudicationResult.BLOCKED, partId,
            `装配顺序错误：需先装回 ${missing.join('、')}`,
            'INSTALL_ORDER_VIOLATION', [],
            missing.map((id) => `先装回 ${id}`),
        );
    }

    return createReport(AdjudicationResult.ALLOWED, partId, '可以安装', 'OK');
}

/**
 * 装配方向：判断螺丝能否拧紧。
 * 工具必须匹配，且螺丝所固定的零件必须已在位。
 */
export function canTightenScrew(screwId: string, toolId: string | null): AdjudicationReport {
    if (!getScrewInstance(screwId)) {
        return createReport(AdjudicationResult.BLOCKED, screwId,
            '未知螺丝实例', 'UNKNOWN_SCREW');
    }

    // 复用既有工具匹配判定，不要手写 screwSpec 比较
    const toolCheck = checkToolMatch(toolId, screwId);
    if (!toolCheck.matched) {
        return createReport(AdjudicationResult.TOOL_MISMATCH, screwId,
            toolCheck.message, 'TOOL_MISMATCH', [],
            toolCheck.requiredTool ? [`选择 ${toolCheck.requiredTool}`] : []);
    }

    const store = useAdjudicationStore.getState();
    const missing = getInstallDependencies(screwId).filter(
        (hostId) => store.partStates[hostId]?.isRemoved === true
    );
    if (missing.length > 0) {
        return createReport(AdjudicationResult.BLOCKED, screwId,
            `需先装回 ${missing.join('、')} 才能紧固`, 'HOST_NOT_INSTALLED', [],
            missing.map((id) => `先装回 ${id}`));
    }

    return createReport(AdjudicationResult.ALLOWED, screwId, '可以紧固', 'OK');
}
```

**已核对的签名与事实**（照抄前无需再查，但改动前请自行复核）：

| 事项 | 结论 |
|---|---|
| `createReport(result, targetPart, reason, reasonCode, blockingConstraints=[], requiredActions=[])` | `decisionEngine.ts:44`；后两参有默认值，可省 |
| `AdjudicationResult` | `ALLOWED` / `BLOCKED` / `WARNING` / `TOOL_MISMATCH` / `INCOMPLETE`（`adjudication.ts:188`） |
| `getScrewInstance(screwId): Part \| undefined` | `data/screwInstances.ts:12`——**`decisionEngine.ts` 尚未导入，需新增 import** |
| `checkToolMatch(toolId, screwId): { matched, requiredTool, message }` | `core/geometryJudge.ts:252`——**已导入**（`decisionEngine.ts:31`），直接用 |
| `Constraint.constrainedPart` / `.constrainingPart` | 均为 `string`，非可选（`adjudication.ts:116-117`），无需 `.filter(Boolean)` |
| 螺丝宿主 | 用 `getInstallDependencies(screwId)` 从 `FASTENED_BY` 反查，不要用 `screw.parentId`（与零件路径共用一条规则） |

> 原文让依赖用 `.filter((id): id is string => Boolean(id))` 收窄类型——`constrainingPart` 本就是必填 `string`，该守卫是多余的，已去掉。

- [x] **Step 4: 接入 `adjudicateAction` 分发**

在 `decisionEngine.ts:458` 的 `adjudicateAction` switch 中加两个分支：

```typescript
        case ActionType.INSTALL_PART:
            return canInstallPart(targetId);
        case ActionType.TIGHTEN_SCREW:
            return canTightenScrew(targetId, toolId ?? null);
```

- [x] **Step 5: 跑测试确认通过**

```bash
cd r-mos-frontend && npx vitest run src/adjudication/__tests__/assemblyDirection.test.ts
```

Expected: 7 passed（更正后的用例数）

- [x] **Step 6: 存量回归（必做）**

```bash
cd r-mos-frontend && npm test
```

Expected: 全绿，基线 **477 passed | 2 skipped** 不退化。

> ⚠️ **计划原文已更正（2026-08-18 核查）**：原文写「特别关注 `decisionEngine.test.ts` 与 `hardwareSopsFlow.test.ts`，它们守护 30 个存量 SOP」——**该前提不成立**。这两个文件连同 `src/adjudication/__tests__/` 下另外 6 个 `.test.ts`，`describe/it/test` 计数均为 0，导出的是 `runTC001()` 一类手写断言函数，属另一套自制 runner 的遗留物；已 grep 确认**无任何外部调用方**。它们不在 vitest include 内，从未执行，纳入后只报 "No test suite found"。
>
> 结论：存量 SOP 目前**没有**这层安全网。T2.1 的回归以实际在跑的 477 为准。是否重写这 8 个文件为 vitest 格式，属计划外独立工作项，另行决策。

- [x] **Step 7: 提交 + 追加开发日志**

```bash
git add r-mos-frontend/src/adjudication/core/decisionEngine.ts \
        r-mos-frontend/src/adjudication/__tests__/assemblyDirection.test.ts \
        r-mos-frontend/vitest.config.ts \
        docs-archive/DEVELOPMENT_LOG.md
git commit -m "feat(adjudication): 新增装配方向裁决（canInstallPart/canTightenScrew）"
```

> `vitest.config.ts` 必须一并提交（Step 1b 的 include 行），否则新测试在别人机器上不执行。
> **不要** `git add` `r-mos-backend/data/knowledge_store.json`——那是用户的本地改动，与本计划无关。

---

### Task 2.2: 三个新 validation 分支

**Files:**
- Modify: `r-mos-frontend/src/adjudication/executor/sopExecutor.ts:160-206`（`checkValidation` 的 switch）
- Test: `r-mos-frontend/src/adjudication/__tests__/threePhase.test.ts`（追加 describe 块）

**Interfaces:**
- Consumes：T1.2 的 `ValidationType.KIT_CONFIRMED` / `.CHECKLIST_CONFIRMED`（`.SCREW_ORDER_MATCHED` 在 T2.3 实现）
- Produces：`checkValidation` 支持读取 `validation.params.confirmedItems` 与 `.requiredItems`

**验证语义**：齐套/验收面板把用户勾选结果写进 `validation.params.confirmedItems: string[]`，与 `params.requiredItems: string[]` 比对，必须全覆盖才通过。

- [x] **Step 1: 写失败测试**

追加到 `threePhase.test.ts`：

```typescript
import { validateStepCompletion } from '../executor/sopExecutor';
import { ValidationType, ActionType, type SOPStepAdjudication } from '../types/adjudication';

function kitStep(confirmed: string[]): SOPStepAdjudication {
    return {
        stepId: 'step_kit', stepIndex: 1, title: '齐套确认', description: '',
        action: ActionType.CONFIRM_KIT, targetParts: [], requiredTool: null,
        preconditions: [], failureReasons: [],
        onSuccess: { nextStepId: 'step_002', stateTransition: null },
        onFailure: { action: 'block', message: '齐套未完成' },
        phase: 'prep',
        validations: [{
            type: ValidationType.KIT_CONFIRMED,
            params: { requiredItems: ['hex_2.5', 'hex_3', '6205-2RS'], confirmedItems: confirmed },
            isRequired: true,
        }],
    } as SOPStepAdjudication;
}

describe('齐套与验收 validation', () => {
    it('齐套项未勾满时不通过', () => {
        const r = validateStepCompletion(kitStep(['hex_2.5']));
        expect(r.allPassed).toBe(false);
        expect(r.failedValidations[0].message).toContain('齐套');
    });

    it('齐套项全部勾选后通过', () => {
        const r = validateStepCompletion(kitStep(['hex_2.5', 'hex_3', '6205-2RS']));
        expect(r.allPassed).toBe(true);
    });
});
```

- [x] **Step 2: 跑测试确认失败**

```bash
cd r-mos-frontend && npx vitest run src/adjudication/__tests__/threePhase.test.ts
```

Expected: FAIL —— 未知 validation 类型走 `default` 返回 `passed: true`，第一个用例断言失败

- [x] **Step 3: 实现两个分支**

在 `sopExecutor.ts` 的 `checkValidation` switch 中，`STATE_CHECK` 之后、`default` 之前插入：

```typescript
        case ValidationType.KIT_CONFIRMED: {
            const required = (validation.params.requiredItems as string[]) ?? [];
            const confirmed = new Set((validation.params.confirmedItems as string[]) ?? []);
            const missing = required.filter((item) => !confirmed.has(item));
            return {
                passed: missing.length === 0,
                message: missing.length === 0 ? '' : `齐套未完成，缺：${missing.join('、')}`,
            };
        }

        case ValidationType.CHECKLIST_CONFIRMED: {
            const required = (validation.params.requiredItems as string[]) ?? [];
            const confirmed = new Set((validation.params.confirmedItems as string[]) ?? []);
            const missing = required.filter((item) => !confirmed.has(item));
            return {
                passed: missing.length === 0,
                message: missing.length === 0 ? '' : `验收项未完成，缺：${missing.join('、')}`,
            };
        }
```

- [x] **Step 4: 跑测试确认通过 + 存量回归**

```bash
cd r-mos-frontend && npx vitest run src/adjudication/__tests__/threePhase.test.ts && npm test
```

Expected: 新用例全过；全量 465 基线不退化

- [x] **Step 5: 提交 + 追加开发日志**

```bash
git add r-mos-frontend/src/adjudication/executor/sopExecutor.ts \
        r-mos-frontend/src/adjudication/__tests__/threePhase.test.ts
git commit -m "feat(adjudication): 齐套与验收清单 validation 分支"
```

---

### Task 2.3: 螺丝对角紧固顺序判定

**Files:**
- Modify: `r-mos-frontend/src/adjudication/executor/sopExecutor.ts`（`checkValidation` 加 `SCREW_ORDER_MATCHED` 分支）
- Test: `r-mos-frontend/src/adjudication/__tests__/threePhase.test.ts`（追加）

**Interfaces:**
- Consumes：`useAdjudicationStore.getState().actionHistory`（`ActionRecord[]`，见 `adjudication.ts:237`）、`ValidationType.SCREW_ORDER_MATCHED`
- Produces：`validation.params.expectedOrder: string[]` 语义——按对角顺序列出螺丝 ID

**判定语义**：从 `actionHistory` 里筛出 `action === ActionType.TIGHTEN_SCREW` 且结果为 `ALLOWED` 的记录，按时间序取其 `targetParts[0]`，与 `expectedOrder` 逐位比对。**只比对已发生的部分**（前缀匹配），这样中途校验不会误报；全部拧完才要求长度相等。

- [x] **Step 1: 写失败测试**

```typescript
import { AdjudicationResult } from '../types/adjudication';

function orderStep(expected: string[]): SOPStepAdjudication {
    return {
        ...kitStep([]),
        stepId: 'step_tighten', title: '对角拧紧',
        action: ActionType.TIGHTEN_SCREW, phase: 'execute',
        validations: [{
            type: ValidationType.SCREW_ORDER_MATCHED,
            params: { expectedOrder: expected },
            isRequired: true,
        }],
    } as SOPStepAdjudication;
}

function pushTighten(screwId: string) {
    // 实际 API 是 addActionRecord，签名为
    // Omit<ActionRecord, 'id' | 'timestamp' | 'stateSnapshot'>（stateManager.ts:52,241）
    // ——id / timestamp / stateSnapshot 由 store 自动生成，不要传
    useAdjudicationStore.getState().addActionRecord({
        action: ActionType.TIGHTEN_SCREW,
        targetParts: [screwId],
        toolId: 'hex_3',
        result: AdjudicationResult.ALLOWED,
    });
}

describe('对角紧固顺序', () => {
    const DIAGONAL = ['screw_a1', 'screw_a3', 'screw_a2', 'screw_a4'];

    beforeEach(() => useAdjudicationStore.getState().resetState());

    it('顺序错误时不通过', () => {
        pushTighten('screw_a1');
        pushTighten('screw_a2');   // 应该是 a3
        const r = validateStepCompletion(orderStep(DIAGONAL));
        expect(r.allPassed).toBe(false);
        expect(r.failedValidations[0].message).toContain('顺序');
    });

    it('部分完成且顺序正确时不报错（前缀匹配），但未拧完仍不通过', () => {
        pushTighten('screw_a1');
        pushTighten('screw_a3');
        const r = validateStepCompletion(orderStep(DIAGONAL));
        expect(r.allPassed).toBe(false);
        expect(r.failedValidations[0].message).not.toContain('顺序错误');
    });

    it('全部按对角顺序拧完后通过', () => {
        DIAGONAL.forEach(pushTighten);
        const r = validateStepCompletion(orderStep(DIAGONAL));
        expect(r.allPassed).toBe(true);
    });
});
```

> ✅ 已核实（2026-08-20）：store 没有 `recordAction`，实际是 `addActionRecord`，上面的夹具已用正确 API。不要新增 store API。
>
> 另注：`checkValidation` 开头已有 `const store = useAdjudicationStore.getState();`（`sopExecutor.ts:164`），实现 `SCREW_ORDER_MATCHED` 时直接用该变量即可，无需重复取。`ActionType` 与 `AdjudicationResult` 也都已导入（`:20-21`）。

- [x] **Step 2: 跑测试确认失败**

```bash
cd r-mos-frontend && npx vitest run src/adjudication/__tests__/threePhase.test.ts -t 对角紧固顺序
```

Expected: FAIL

- [x] **Step 3: 实现**

在 `checkValidation` 中追加：

```typescript
        case ValidationType.SCREW_ORDER_MATCHED: {
            const expected = (validation.params.expectedOrder as string[]) ?? [];
            const actual = useAdjudicationStore.getState().actionHistory
                .filter((r) => r.action === ActionType.TIGHTEN_SCREW
                    && r.result === AdjudicationResult.ALLOWED)
                .map((r) => r.targetParts[0])
                .filter(Boolean);

            // 前缀匹配：只校验已发生的部分，避免中途误报
            const mismatchAt = actual.findIndex((id, i) => id !== expected[i]);
            if (mismatchAt !== -1) {
                return {
                    passed: false,
                    message: `紧固顺序错误：第 ${mismatchAt + 1} 颗应为 ${expected[mismatchAt]}，实际为 ${actual[mismatchAt]}`,
                };
            }
            if (actual.length < expected.length) {
                return {
                    passed: false,
                    message: `还需紧固 ${expected.length - actual.length} 颗螺丝`,
                };
            }
            return { passed: true, message: '' };
        }
```

需要在 `sopExecutor.ts` 顶部的 import 中补上 `AdjudicationResult`（若尚未导入）。

- [x] **Step 4: 跑测试确认通过 + 存量回归**

```bash
cd r-mos-frontend && npx vitest run src/adjudication/__tests__/threePhase.test.ts && npm test
```

- [x] **Step 5: 提交 + 追加开发日志**

```bash
git add r-mos-frontend/src/adjudication/executor/sopExecutor.ts \
        r-mos-frontend/src/adjudication/__tests__/threePhase.test.ts
git commit -m "feat(adjudication): 螺丝对角紧固顺序判定"
```

---

### Task 2.4: 阶段门

**Files:**
- Modify: `r-mos-frontend/src/adjudication/executor/sopExecutor.ts`（`SOPExecutor` 类加方法；`validateAndAdvance` `:449` 推进处加校验）
- Test: `r-mos-frontend/src/adjudication/__tests__/threePhase.test.ts`（追加）

**Interfaces:**
- Produces（T3.1 进度条依赖这两个方法的精确签名）：
  - `SOPExecutor.getCurrentPhase(): SOPPhase | null`
  - `SOPExecutor.getPhaseProgress(): Array<{ phase: SOPPhase; total: number; completed: number; unlocked: boolean }>`

**门禁语义**：跨段推进时（下一步的 `phase` 与当前步不同），必须当前段所有步骤的 `stepId` 都在 `context.completedSteps` 里，否则返回 `BLOCKED` / `reasonCode: 'PHASE_GATE'`。

- [x] **Step 1: 写失败测试**

```typescript
import { createSOPExecutor } from '../executor/sopExecutor';

function threePhaseSop() {
    const mk = (id: string, phase: 'prep' | 'execute' | 'verify') => ({
        ...kitStep(['hex_2.5', 'hex_3', '6205-2RS']),
        stepId: id, phase, action: ActionType.FOCUS_CAMERA,
        validations: [], targetParts: [],
    }) as SOPStepAdjudication;

    return {
        sopId: 'sop-test-3phase', title: '三段式测试', version: '1.0',
        targetModule: 'knee', estimatedTime: 600, difficulty: 'intermediate',
        steps: [mk('p1', 'prep'), mk('p2', 'prep'), mk('e1', 'execute'), mk('v1', 'verify')],
    };
}

describe('阶段门', () => {
    beforeEach(() => useAdjudicationStore.getState().resetState());

    it('getCurrentPhase 返回当前步所在段', () => {
        const ex = createSOPExecutor();
        ex.loadSOP(threePhaseSop() as never);
        expect(ex.getCurrentPhase()).toBe('prep');
    });

    it('getPhaseProgress 给出三段的解锁与完成情况', () => {
        const ex = createSOPExecutor();
        ex.loadSOP(threePhaseSop() as never);
        const p = ex.getPhaseProgress();
        expect(p.map((x) => x.phase)).toEqual(['prep', 'execute', 'verify']);
        expect(p[0]).toMatchObject({ total: 2, completed: 0, unlocked: true });
        expect(p[1].unlocked).toBe(false);   // prep 未完成，execute 段锁定
    });

    it('prep 段未做完不能跨到 execute 段', () => {
        const ex = createSOPExecutor();
        ex.loadSOP(threePhaseSop() as never);
        ex.executeStep();
        const r = ex.validateAndAdvance();       // p1 完成，下一步 p2 同段，放行
        expect(r.result).toBe(AdjudicationResult.ALLOWED);
        expect(ex.getCurrentPhase()).toBe('prep');
    });
});
```

- [x] **Step 2: 跑测试确认失败**

```bash
cd r-mos-frontend && npx vitest run src/adjudication/__tests__/threePhase.test.ts -t 阶段门
```

Expected: FAIL —— `getCurrentPhase is not a function`

- [x] **Step 3: 实现两个方法**

在 `SOPExecutor` 类中（`getExecutionReport` 之后）追加：

```typescript
    /** 当前步骤所属阶段 */
    getCurrentPhase(): SOPPhase | null {
        return this.getCurrentStep()?.phase ?? null;
    }

    /** 三段进度：供 UI 渲染进度条与锁定态 */
    getPhaseProgress(): Array<{
        phase: SOPPhase; total: number; completed: number; unlocked: boolean;
    }> {
        const order: SOPPhase[] = ['prep', 'execute', 'verify'];
        const steps = this.currentSOP?.steps ?? [];
        const done = new Set(this.context?.completedSteps ?? []);

        let prevComplete = true;
        return order
            .map((phase) => {
                const inPhase = steps.filter((s) => s.phase === phase);
                const completed = inPhase.filter((s) => done.has(s.stepId)).length;
                const unlocked = prevComplete;
                prevComplete = prevComplete && inPhase.length === completed;
                return { phase, total: inPhase.length, completed, unlocked };
            })
            .filter((p) => p.total > 0);
    }
```

- [x] **Step 4: 在推进处加阶段门**

在 `validateAndAdvance()` 的「推进到下一步」之前（`sopExecutor.ts:586` 的 `this.context.currentStepIndex = nextIndex;` 之前）插入：

```typescript
        // 阶段门：跨段推进前，当前段必须全部完成
        const nextStep = this.currentSOP?.steps[nextIndex];
        const currentPhase = step.phase;
        if (nextStep && nextStep.phase !== currentPhase) {
            const unfinished = (this.currentSOP?.steps ?? [])
                .filter((s) => s.phase === currentPhase
                    && !this.context!.completedSteps.includes(s.stepId));
            if (unfinished.length > 0) {
                const report: AdjudicationReport = {
                    result: AdjudicationResult.BLOCKED,
                    targetPart: '',
                    reason: `${currentPhase} 阶段尚有 ${unfinished.length} 步未完成，不能进入下一阶段`,
                    reasonCode: 'PHASE_GATE',
                    blockingConstraints: [],
                    requiredActions: unfinished.map((s) => `完成「${s.title}」`),
                    timestamp: Date.now(),
                };
                this.context.lastReport = report;
                this.context.executionState = SOPExecutionState.BLOCKED;
                this.notifyStateChange();
                this.onBlocked?.(report);
                return report;
            }
        }
```

需在文件顶部 import 中补 `SOPPhase` 类型。

> ⚠️ 存量 SOP 全部步骤 `phase === 'execute'`，永不触发跨段分支，行为完全不变——这是向后兼容的保证点，回归必须验到。

- [x] **Step 5: 跑测试确认通过 + 存量回归（重点）**

```bash
cd r-mos-frontend && npx vitest run src/adjudication/__tests__/ && npm test
```

Expected: 全绿。`sopExecutor.test.ts` / `hardwareSopsFlow.test.ts` / `examMode.test.ts` 一个都不能红。

- [x] **Step 6: 提交 + 追加开发日志**

```bash
git add r-mos-frontend/src/adjudication/executor/sopExecutor.ts \
        r-mos-frontend/src/adjudication/__tests__/threePhase.test.ts
git commit -m "feat(adjudication): 三段式阶段门（getCurrentPhase/getPhaseProgress + 跨段校验）"
```

---

## Phase 3 — 前端

### Task 3.1: 三段进度条

**Files:**
- Modify: `r-mos-frontend/src/components/Maintenance/sopPlayer/SOPPlayerView.tsx`
- Modify: `r-mos-frontend/src/components/Maintenance/SOPPlayerAdjudicated.tsx`（把 `getPhaseProgress()` 结果传下去）
- Test: `r-mos-frontend/src/components/Maintenance/__tests__/PhaseProgress.test.tsx`（新建）

**Interfaces:**
- Consumes：T2.4 的 `SOPExecutor.getPhaseProgress()`
- Produces：`SOPPlayerView` 新 prop `phaseProgress?: Array<{phase, total, completed, unlocked}>`

**动手前先读** `SOPPlayerView.tsx` 与 `sopPlayerConfig.ts`，沿用其既有 Ant Design 用法与配色，不要引入新 UI 库。

- [x] **Step 1: 写失败测试**

```tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { PhaseProgress } from '../sopPlayer/PhaseProgress';

describe('三段进度条', () => {
    const progress = [
        { phase: 'prep' as const, total: 4, completed: 4, unlocked: true },
        { phase: 'execute' as const, total: 14, completed: 3, unlocked: true },
        { phase: 'verify' as const, total: 4, completed: 0, unlocked: false },
    ];

    it('渲染三段中文标签与完成计数', () => {
        render(<PhaseProgress progress={progress} currentPhase="execute" />);
        expect(screen.getByText('准备')).toBeInTheDocument();
        expect(screen.getByText('执行')).toBeInTheDocument();
        expect(screen.getByText('验证')).toBeInTheDocument();
        expect(screen.getByText('3/14')).toBeInTheDocument();
    });

    it('未解锁段标记为锁定', () => {
        render(<PhaseProgress progress={progress} currentPhase="execute" />);
        expect(screen.getByLabelText('验证 阶段未解锁')).toBeInTheDocument();
    });
});
```

- [x] **Step 2: 跑测试确认失败**

```bash
cd r-mos-frontend && npx vitest run src/components/Maintenance/__tests__/PhaseProgress.test.tsx
```

- [x] **Step 3: 实现 `PhaseProgress` 组件**

创建 `r-mos-frontend/src/components/Maintenance/sopPlayer/PhaseProgress.tsx`。要求：三段横向排列；当前段高亮；已完成段打勾；`unlocked === false` 的段置灰且 `aria-label={`${标签} 阶段未解锁`}`；标签映射 `{ prep: '准备', execute: '执行', verify: '验证' }`；每段显示 `completed/total`。单文件不超过 80 行。

- [x] **Step 4: 挂到 SOPPlayer**

`SOPPlayerAdjudicated.tsx` 从 executor 取 `getPhaseProgress()` 与 `getCurrentPhase()`，经 `SOPPlayerView` 传给 `PhaseProgress`。只有当 `phaseProgress.length > 1` 时才渲染——**存量单段 SOP 不显示进度条，UI 零变化**。

- [x] **Step 5: 跑测试 + 构建 + 存量回归**

```bash
cd r-mos-frontend && npx vitest run src/components/Maintenance/__tests__/PhaseProgress.test.tsx && npm test && npm run build
```

- [x] **Step 6: 提交 + 追加开发日志**

```bash
git commit -m "feat(maintenance): SOP 三段进度条"
```

---

### Task 3.2: 齐套检查面板

> ⚠️ **规格已更正（2026-08-20 预检）**：原文测试夹具与 Props 注释使用驼峰 `bomCode`，与 T1.2 落地的 `RequiredPart.bom_code` 不符（§2.4 第 9 条），照原文写会 TS 编译失败。下方已改为 snake_case。
>
> `src/components/Maintenance/index.ts` 已存在（导出 ToolSelector / ScrewInfo / SOPMaintenanceShell 四件），追加导出即可，注意其中既有 `export { default as X }` 与具名导出两种风格，按新组件的导出方式选择对应写法。

**Files:**
- Create: `r-mos-frontend/src/components/Maintenance/KitChecklistPanel.tsx`
- Modify: `r-mos-frontend/src/components/Maintenance/index.ts`（导出）
- Modify: `r-mos-frontend/src/components/Maintenance/SOPPlayerAdjudicated.tsx`（`action === CONFIRM_KIT` 时渲染）
- Test: `r-mos-frontend/src/components/Maintenance/__tests__/KitChecklistPanel.test.tsx`

**Interfaces:**
- Consumes：T1.2 的 `RequiredPart`、`SOPStepAdjudication.requiredParts`、`.requiredTool`；`ActionType.CONFIRM_KIT`
- Produces：
  ```typescript
  export interface KitChecklistPanelProps {
    tools: string[];                 // 工具 ID 列表
    parts: RequiredPart[];           // 备件列表
    confirmed: string[];             // 已勾选项（工具 ID 或 bom_code）
    onChange: (confirmed: string[]) => void;
  }
  ```

- [x] **Step 1: 写失败测试**

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { KitChecklistPanel } from '../KitChecklistPanel';

// ⚠️ bom_code 是 snake_case（§2.4 第 9 条）——后端原样透传 JSON，不做 key 转换
const parts = [
    { bom_code: '6205-2RS', name: '深沟球轴承', qty: 1 },
    { bom_code: 'GREASE-01', name: '润滑脂', qty: 1, note: '薄层涂抹' },
];

describe('齐套检查面板', () => {
    it('列出工具与备件，显示数量', () => {
        render(<KitChecklistPanel tools={['hex_3']} parts={parts} confirmed={[]} onChange={() => {}} />);
        expect(screen.getByText('深沟球轴承')).toBeInTheDocument();
        expect(screen.getByText('×1')).toBeTruthy();
    });

    it('勾选后回调携带该项标识', () => {
        const onChange = vi.fn();
        render(<KitChecklistPanel tools={['hex_3']} parts={parts} confirmed={[]} onChange={onChange} />);
        fireEvent.click(screen.getByLabelText('确认 6205-2RS 已备齐'));
        expect(onChange).toHaveBeenCalledWith(['6205-2RS']);
    });

    it('未全部勾选时显示待确认数量', () => {
        render(<KitChecklistPanel tools={['hex_3']} parts={parts} confirmed={['hex_3']} onChange={() => {}} />);
        expect(screen.getByText(/还有 2 项待确认/)).toBeInTheDocument();
    });
});
```

- [x] **Step 2: 跑测试确认失败** → **Step 3: 实现组件** → **Step 4: 挂载**

组件要求：工具区 + 备件区两组 checkbox；每项 `aria-label={`确认 ${标识} 已备齐`}`；底部显示剩余待确认数；全部勾选时显示「齐套完成」。沿用 Ant Design `Checkbox` / `Card`，单文件不超过 120 行。

挂载：`SOPPlayerAdjudicated` 在当前步 `action === ActionType.CONFIRM_KIT` 时渲染此面板，把勾选结果写进该步 validation 的 `params.confirmedItems`，使 T2.2 的 `KIT_CONFIRMED` 能读到。

- [x] **Step 5: 跑测试 + 构建 + 存量回归**

```bash
cd r-mos-frontend && npm test && npm run build
```

- [x] **Step 6: 提交 + 追加开发日志**

---

### Task 3.3: 验收记录面板

**Files:**
- Create: `r-mos-frontend/src/components/Maintenance/VerifyChecklistPanel.tsx`
- Modify: `r-mos-frontend/src/components/Maintenance/index.ts`、`SOPPlayerAdjudicated.tsx`
- Test: `r-mos-frontend/src/components/Maintenance/__tests__/VerifyChecklistPanel.test.tsx`

**Interfaces:**
- Consumes：`ActionType.VERIFY_CHECK`、`ValidationType.CHECKLIST_CONFIRMED`
- Produces：
  ```typescript
  export interface VerifyItem { key: string; label: string; expected?: string; }
  export interface VerifyChecklistPanelProps {
    items: VerifyItem[];
    confirmed: string[];
    onChange: (confirmed: string[]) => void;
  }
  ```

结构与 T3.2 同构，差别：每项可带 `expected`（期望值，如「间隙 ≤ 0.5mm」「扭矩 2.5N·m」）显示在标签右侧；勾选结果最终落 `TaskStepResult.evidence_value`（T5.1 接线）。

- [x] **Step 1-6**：同 T3.2 节奏（写失败测试 → 确认失败 → 实现 → 挂载 → 测试+构建+回归 → 提交+日志）。测试至少覆盖：渲染 expected 值、勾选回调、全勾时显示「验收完成」。

---

### Task 3.4: `useSOPSceneSync` 读 `stepView`

**Files:**
- Modify: `r-mos-frontend/src/adjudication/ui/useSOPSceneSync.ts:13-17`（`SOPSceneIntent`）、`:146-154`（`buildIntent`）
- Test: `r-mos-frontend/src/adjudication/__tests__/sceneSyncStepView.test.ts`（新建）

**Interfaces:**
- Consumes：T1.2 的 `StepView`
- Produces：`SOPSceneIntent` 扩展为
  ```typescript
  export interface SOPSceneIntent {
    targetPart: string | null;
    explodeAmount: number;
    requiredTool: string | null;
    camera?: StepView['camera'];      // 新增
    visibleLinks?: string[];          // 新增
    highlight?: string[];             // 新增
  }
  ```

**核心要求**：`stepView` 有值时优先用它；**任何缺省字段回落到现有启发式**。这是存量 30 个 SOP 零影响的保证点。

- [x] **Step 1: 写失败测试**

```typescript
import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSOPSceneSync } from '../ui/useSOPSceneSync';
import { ActionType, type SOPStepAdjudication } from '../types/adjudication';

const base = {
    stepId: 's1', stepIndex: 1, description: '', targetParts: [],
    requiredTool: null, preconditions: [], validations: [], failureReasons: [],
    onSuccess: { nextStepId: 'end', stateTransition: null },
    onFailure: { action: 'block' as const, message: '' },
    phase: 'execute' as const,
};

describe('stepView 优先于启发式', () => {
    it('stepView 给了 explode 就用它，不再解析文本里的百分比', () => {
        const step = { ...base, title: '爆炸到 90%', action: ActionType.FOCUS_CAMERA,
                       stepView: { explode: 0.35 } } as SOPStepAdjudication;
        const { result } = renderHook(() => useSOPSceneSync());
        let intent: ReturnType<typeof result.current.bindStep>;
        act(() => { intent = result.current.bindStep(step, 0); });
        expect(intent!.explodeAmount).toBe(0.35);
    });

    it('stepView 缺省时回落到现有启发式（文本百分比）', () => {
        const step = { ...base, title: '爆炸到 90%', action: ActionType.FOCUS_CAMERA }
            as SOPStepAdjudication;
        const { result } = renderHook(() => useSOPSceneSync());
        let intent: ReturnType<typeof result.current.bindStep>;
        act(() => { intent = result.current.bindStep(step, 0); });
        expect(intent!.explodeAmount).toBeCloseTo(0.9);
    });

    it('stepView 只给 camera 时，explode 仍走启发式', () => {
        const step = { ...base, title: '定位', action: ActionType.REMOVE_PART,
                       stepView: { camera: { position: [1, 1, 1] as [number, number, number],
                                             target: [0, 0, 0] as [number, number, number], fov: 50 } } }
            as SOPStepAdjudication;
        const { result } = renderHook(() => useSOPSceneSync());
        let intent: ReturnType<typeof result.current.bindStep>;
        act(() => { intent = result.current.bindStep(step, 0); });
        expect(intent!.camera?.fov).toBe(50);
        expect(intent!.explodeAmount).toBeCloseTo(0.62);   // REMOVE_PART 的启发式默认值
    });
});
```

- [x] **Step 2: 跑测试确认失败**

```bash
cd r-mos-frontend && npx vitest run src/adjudication/__tests__/sceneSyncStepView.test.ts
```

- [x] **Step 3: 改 `buildIntent`**

```typescript
function buildIntent(step: SOPStepAdjudication | null): SOPSceneIntent {
    if (!step) return DEFAULT_INTENT;
    const heuristicTarget = resolveTargetPart(step);
    const view = step.stepView;

    return {
        // stepView 优先，逐字段回落——缺省项走原有启发式，保证存量 SOP 行为不变
        targetPart: view?.highlight?.[0] ?? heuristicTarget,
        explodeAmount: view?.explode ?? deriveExplodeAmount(step, heuristicTarget),
        requiredTool: step.requiredTool ?? null,
        camera: view?.camera,
        visibleLinks: view?.visibleLinks,
        highlight: view?.highlight,
    };
}
```

- [x] **Step 4: 消费端接线**

`r-mos-frontend/src/pages/sopMaintenance/useSOPPlaybackBridge.ts` 里，当 intent 带 `camera` 时套用相机预设，带 `visibleLinks` 时收敛可见集。**先读该文件确认既有的相机与可见集设置入口**，复用它们，不要新增并行通路。

- [x] **Step 5: 跑测试 + 构建 + 存量回归（重点）**

```bash
cd r-mos-frontend && npx vitest run src/adjudication/ && npm test && npm run build
```

Expected: 全绿。第二个用例（回落启发式）是存量兼容的守门测试，必须过。

- [x] **Step 6: 提交 + 追加开发日志**

---

## Phase 4 — 标杆内容

### Task 4.1: 膝关节轴承更换 SOP 重编排为 22 步

> ⚠️ **规格已更正（2026-08-21 预检）**：计划原文的测试 `from scripts.seed_adjudication_sops import build_knee_bearing_sop` —— **该函数不存在**。膝关节 SOP 是模块级字典常量 `SOP_KNEE_BEARING`（`seed_adjudication_sops.py:711`），步骤由 `_make_knee_step(...)` 构造。
>
> **不要**为迎合测试新建一个 `build_knee_bearing_sop()` 包装函数（无谓抽象）。测试直接 import 常量：
>
> ```python
> from scripts.seed_adjudication_sops import SOP_KNEE_BEARING
> steps = SOP_KNEE_BEARING["steps"]
> ```
>
> `_make_knee_step` 现签名（`:680`）为
> `(step_id, step_index, title, description, target_parts, next_step_id)`，
> 内部把 `expected_action` 硬编码为 `"focus_camera"`、`validations` 硬编码为 `[]`。22 步需要多种 action 与 validation，**需扩展该辅助函数的参数**（加 `phase` / `group_path` / `step_view` / `required_parts` / `expected_action` / `validations` 等，给默认值以保持现有调用兼容）。

**Files:**
- Modify: `r-mos-backend/scripts/seed_adjudication_sops.py`（膝关节 SOP 段落，当前 `:712` 起）
- Test: `r-mos-backend/tests/test_sop_three_phase.py`（追加 seed 结构校验）

**Interfaces:**
- Consumes：T1.1 的 4 列；T1.2 的 7 个新枚举值

**22 步结构**（严格按此编排）：

**准备段 `phase="prep"`，4 步：**
1. 故障确认 —— `action=focus_camera`，读诊断轨迹，`group_path="knee/prep"`
2. 断电隔离确认 —— `action=verify_check`，`CHECKLIST_CONFIRMED`，项：主电源已断开 / 挂牌上锁 / 余电释放
3. 工具齐套 —— `action=confirm_kit`，`KIT_CONFIRMED`，`requiredItems=["hex_2.5","hex_3","bearing_puller","torque_wrench"]`
4. 备件齐套 —— `action=confirm_kit`，`required_parts=[{6205-2RS 轴承×1},{润滑脂×1},{螺纹胶×1}]`

**执行段 `phase="execute"`，14 步：**
5. 定位膝关节作业区 —— `focus_camera`
6. 选择 3mm 内六角 —— `select_tool`
7. 拆膝部覆盖件螺丝组（4 颗 M4×8）—— `rotate_screw` + `ALL_SCREWS_EXTRACTED`
8. 移除膝部覆盖件 —— `remove_part`
9. 选择拔取器 —— `select_tool`
10. 拆轴承座固定螺丝（4 颗 M4×8）—— `rotate_screw` + `ALL_SCREWS_EXTRACTED`
11. 分离轴承座 —— `detach_part`
12. 拔取旧轴承 —— `remove_part`，`is_critical=True`（垂直用力，避免损伤轴座）
13. 清洁轴座配合面 —— `focus_camera`
14. 新轴承涂抹润滑脂 —— `focus_camera`
15. 压入新轴承 6205-2RS —— `install_part`
16. 装回轴承座 —— `install_part`
17. 对角拧紧轴承座 4 颗螺丝 —— `tighten_screw` + `SCREW_ORDER_MATCHED`，`expectedOrder` 按对角序（1→3→2→4）
18. 装回膝部覆盖件 —— `install_part`

**验证段 `phase="verify"`，4 步：**
19. 外观间隙复核 —— `verify_check`，expected「间隙 ≤ 0.5mm」
20. 紧固扭矩复核 —— `verify_check`，expected「2.5 N·m」
21. 通电 —— `verify_check`，expected「低速空载 5 分钟无异响」
22. ±90° 全行程活动度测试 —— `verify_check`，`CHECKLIST_CONFIRMED`

- [x] **Step 1: 写失败测试**

追加到 `r-mos-backend/tests/test_sop_three_phase.py`：

```python
def test_knee_bearing_sop_is_three_phase_22_steps():
    """膝关节标杆 SOP 必须是 4+14+4 的三段式结构。"""
    from scripts.seed_adjudication_sops import SOP_KNEE_BEARING

    steps = SOP_KNEE_BEARING["steps"]
    assert len(steps) == 22

    phases = [s["phase"] for s in steps]
    assert phases[:4] == ["prep"] * 4
    assert phases[4:18] == ["execute"] * 14
    assert phases[18:] == ["verify"] * 4


def test_knee_bearing_sop_has_kit_and_order_validations():
    from scripts.seed_adjudication_sops import SOP_KNEE_BEARING

    steps = SOP_KNEE_BEARING["steps"]
    kit_steps = [s for s in steps if s["expected_action"] == "confirm_kit"]
    assert len(kit_steps) == 2
    assert any(s["required_parts"] for s in kit_steps)

    tighten = [s for s in steps if s["expected_action"] == "tighten_screw"]
    assert len(tighten) == 1
    validations = tighten[0]["validation_rules"]["validations"]
    order = next(v for v in validations if v["type"] == "screw_order_matched")
    assert len(order["params"]["expectedOrder"]) == 4
```

- [x] **Step 2: 跑测试确认失败**

```bash
cd r-mos-backend && source venv/bin/activate && pytest tests/test_sop_three_phase.py -v
```

Expected: FAIL —— `cannot import name 'build_knee_bearing_sop'`

- [x] **Step 3: 重编排 seed**

在 `seed_adjudication_sops.py` 中把膝关节 SOP 抽成 `build_knee_bearing_sop() -> dict` 函数，按上表 22 步编排。同时把 `to_sop_steps()` 扩展为透传 `phase` / `group_path` / `step_view` / `required_parts`（`step_drafts` 里给了就带上，没给则 `phase="execute"`、其余 `None`）。

> ⚠️ **不要动 30 个 `focus_step` SOP 的 builder**。`to_sop_steps` 的缺省行为必须让它们产出与改造前**逐字节一致**的 step dict（除新增的 `phase="execute"` 字段）。

- [x] **Step 4: 跑测试确认通过**

```bash
cd r-mos-backend && source venv/bin/activate && pytest tests/test_sop_three_phase.py -v
```

- [x] **Step 5: 实跑 seed 并核对入库**

```bash
cd r-mos-backend && source venv/bin/activate && python -m scripts.seed_adjudication_sops
```

然后用 API 核对（后端需在跑）：

```bash
curl --noproxy 127.0.0.1,localhost -s \
  "http://127.0.0.1:8000/api/v1/sops/adjudication?applicable_model=ATOM-01" \
  | python -c "import sys,json; d=json.load(sys.stdin); \
    s=[x for x in d['items'] if '膝' in x['title']][0]; \
    print(len(s['steps']), [t['phase'] for t in s['steps']])"
```

Expected: `22 ['prep','prep','prep','prep','execute',...,'verify','verify','verify','verify']`

- [x] **Step 6: 存量 SOP 回归（必做）**

```bash
cd r-mos-backend && source venv/bin/activate && pytest tests/ -v -k "sop"
```

再确认裁决列表仍返回 31 个 SOP，30 个存量 SOP 的步骤数与改造前一致。

- [x] **Step 7: 提交 + 追加开发日志**

```bash
git commit -m "feat(sop): 膝关节轴承更换 SOP 重编排为 22 步三段式"
```

---

### Task 4.2: 补 `step_view` 与 `required_parts`

> ⚠️ **规格已更正 + 验收口径已由用户裁决（2026-08-21）**
>
> 1. 原文残留 `build_knee_bearing_sop()` —— 该函数不存在（§2.4 第 12 条），已改为 import `SOP_KNEE_BEARING` 常量。
>
> 2. **相机位有真实基准，不要凭空编数值。** `data/robot-assets/1/manifests/assembly_manifest.json` 的 `camera_presets` 里已有 11 个标定过的预设（3D 查看器正在使用），其中：
>
>    ```json
>    "left_knee_link": { "position": [0.4, -0.3, 0.4], "target": [0.1, -0.45, 0.0], "fov": 40 }
>    ```
>
>    22 步一律**以该预设为基准**，按步骤语义在其上做有据可依的微调：准备段用全景（可参考 `L0_overview`: position [1.5,1.0,1.5] / target [0,0.3,0] / fov 45），执行段随作业深度推近（缩短 position 到 target 的距离、或收窄 fov），验证段拉回中景。**不要发明与该基准无关的坐标系。**
>
> 3. **Step 5「目视逐步验收」的口径**：用户已裁决采用「基于真实预设推导」方案，**不要求执行方启动前后端逐步目视**。改为：在开发日志中逐步列出每步的 `step_view` 取值**及其推导依据**（基于哪个预设、为何这样微调），并如实说明「相机位为基于标定预设的推导值，未经逐步目视确认」。用户会在交付后自行运行查看，不满意的步骤再行调整。**仍然严禁写「应该正常」这类未经证实的断言。**

**Files:**
- Modify: `r-mos-backend/scripts/seed_adjudication_sops.py`（22 步逐一补构图）
- Test: `r-mos-backend/tests/test_sop_three_phase.py`（追加覆盖率断言）

- [x] **Step 1: 写失败测试**

```python
def test_knee_bearing_steps_have_step_view():
    """22 步必须全部带 step_view，否则 3D 展示会退回启发式猜测。"""
    from scripts.seed_adjudication_sops import SOP_KNEE_BEARING

    steps = SOP_KNEE_BEARING["steps"]
    missing = [s["title"] for s in steps if not s.get("step_view")]
    assert missing == [], f"以下步骤缺 step_view：{missing}"


def test_step_view_shape_is_valid():
    from scripts.seed_adjudication_sops import SOP_KNEE_BEARING

    for s in SOP_KNEE_BEARING["steps"]:
        view = s["step_view"]
        if "camera" in view:
            assert len(view["camera"]["position"]) == 3
            assert len(view["camera"]["target"]) == 3
            assert 20 <= view["camera"]["fov"] <= 90
        if "explode" in view:
            assert 0 <= view["explode"] <= 1
```

- [x] **Step 2-4**：跑测试确认失败 → 逐步补 `step_view`（相机位以膝关节为中心，准备段用全景，执行段随作业深度推近，验证段拉回中景）与 `required_parts` → 跑测试确认通过。

- [x] **Step 5: 目视验收（必做，不能只靠单测）**

启动前后端，打开维保工作台加载该 SOP，逐步点过 22 步，确认每步 3D 视角对准了该步的目标零件。**截图或逐步记录实际观察结果**写进开发日志——这一项不允许写「应该正常」。

- [x] **Step 6: 提交 + 追加开发日志**

---

## Phase 5 — 验收

### Task 5.1: E2E 与记录落库

**Files:**
- Modify: `r-mos-frontend/src/components/Maintenance/SOPPlayerAdjudicated.tsx:216`（`syncStepCompletion` 带上证据）
- Create: `r-mos-frontend/e2e/sop-three-phase.spec.ts`
- Modify: `r-mos-backend/app/api/v1/endpoints/pipeline.py`（`StepCompleteRequest` 加 `is_compliant`；`evidence_type` / `evidence_value` / `duration_seconds` **已存在**）
- Modify: `r-mos-backend/app/services/pipeline/task_pipeline_service.py`（`complete_step` 的 `is_compliant=True` 是硬编码，需改为接收参数——见 §2.4 第 13 条）

**Interfaces:**
- `StepCompleteRequest` 增 `evidence_type: Optional[str]`、`evidence_value: Optional[dict]`、`is_compliant: bool = True`，写入 `TaskStepResult` 同名字段（该表字段已存在，无需迁移）

- [ ] **Step 1: 后端接收证据** —— 先写后端测试（构造带 evidence 的 step complete 请求，断言落库），确认失败，再实现，确认通过。
- [ ] **Step 2: 前端上报证据** —— `syncStepCompletion` 在齐套/验收步骤带上 `evidence_type: 'kit_checklist' | 'verify_checklist'` 与勾选结果。
- [ ] **Step 3: 写 E2E** —— Playwright 走通 22 步：验证 prep 段没做完时 execute 段被挡、齐套没勾满时不能推进、全程走完后报告页可见记录。

  > ⚠️ 原文第三个场景「螺丝乱序拧紧被拒」**已剔除**——UI 无单颗螺丝粒度，无法复现该交互（§2.4 第 14 条）。该逻辑由 T2.3 单测覆盖。
- [ ] **Step 4: 跑 E2E**

```bash
cd r-mos-frontend && npm run e2e -- sop-three-phase.spec.ts
```

- [ ] **Step 5: 全量回归**

```bash
cd r-mos-backend && source venv/bin/activate && pytest tests/ -v
cd ../r-mos-frontend && npm test && npm run build
```

Expected: 后端 ≥791 通过，前端 ≥465 通过，build PASS

- [ ] **Step 6: 提交 + 追加开发日志**

---

### Task 5.2: 报告页两节

**Files:**
- Modify: `r-mos-frontend/src/pages/ReportPage.tsx`
- Test: `r-mos-frontend/src/pages/__tests__/ReportPage.test.tsx`（若不存在则新建）

- [ ] **Step 1: 写失败测试** —— 断言报告页在有 `kit_checklist` / `verify_checklist` 证据时渲染「齐套记录」「验收记录」两节，无证据时不渲染（存量报告零变化）。
- [ ] **Step 2-4**：确认失败 → 实现 → 确认通过。
- [ ] **Step 5: 全量回归 + 构建**
- [ ] **Step 6: 提交 + 追加开发日志 + 更新 `docs/testing/TEST_REPORT.md`**（AGENTS.md §2.2：变更影响验收必须同步）

---

## 5. 执行约束（Codex 规则）

Codex 每个 Task **开始时**必须输出 Read-first Checkpoint 并逐条 ✅/❌ 确认：

1. 当前仓库目录 `/Users/xuhehong/Desktop/r-mos`
2. Python 环境仅在 `r-mos-backend/venv` 内执行
3. 本机 HTTP 调用使用 `curl --noproxy 127.0.0.1,localhost`
4. 若需访问前后端：先说明「需要启动服务」并给出启动命令与端口
5. `DATABASE_URL` / CORS 不得擅改
6. 允许 commit；**git push 必须事先获得用户许可**
7. 本计划文档为本任务的最高事实源

Codex 每个 Task **结束时**必须输出：

1. `git diff --name-only`
2. 关键差异片段（只截关键函数/段落）
3. 真实测试命令与真实输出摘要（PASS/FAIL）
4. `docs-archive/DEVELOPMENT_LOG.md` 的新增记录
5. commit hash
6. **停在 push 之前**

---

## 6. AGENTS.md 过期项覆盖（重要）

`AGENTS.md` 是 Codex 的权威规则源，但以下四项已过期，**以本节为准**：

| AGENTS.md 写的 | 实际（以此为准） |
|---|---|
| Python 环境用 `.venv` | **`r-mos-backend/venv`** |
| 更新根目录 `DEVELOPMENT_LOG.md` | **`docs-archive/DEVELOPMENT_LOG.md`** |
| 基线 `collected 239`（2026-03-05 快照） | **已严重过期**；实际后端 791 / 前端 465 全绿 |
| 事实源 `docs/plans/2026-03-05-review-test-cleanup-execution.md` | **该文件已不存在**，忽略 |

AGENTS.md §6 的 ADR 触发条件依然有效：Task 1.1 改表结构且影响多模块，**必须**产出 `docs/adr/ADR-2026-08-17-sop-three-phase-schema.md`。

---

## 7. 风险与回滚

| 风险 | 应对 |
|---|---|
| **内容编排成本被低估**（最大风险）。引擎新逻辑只有 Phase 2 四个 Task，但 22 步的 `step_view` 相机位与 `required_parts` 是纯手工活。30 个 SOP 全量升级约 660 步。 | 本轮只打穿一条。**T4.1 实测（2026-08-21）**：22 步结构编排耗时约 5–10 分钟／1 个执行轮次，执行方反馈「重复内容多、漏项风险明显」，660 步的人工核对成本会迅速放大——**风险判断成立**。T4.2 的相机位标定成本更高（需对真实 3D 模型逐步取值）。**不要在本轮扩大范围。** |
| **存量 31 个 SOP 被打破** | 每个 Task 的验收都含存量回归。三道保险：`phase` 的 `server_default="execute"`、`step_view` 为空回落启发式、`getPhaseProgress().length > 1` 才渲染进度条。 |
| **装配方向裁决与拆卸约束图不自洽**（T2.1 最可能出问题） | T2.1 的测试必须覆盖「依赖未就位被拒 / 依赖就位放行 / 工具不匹配被拒」三种路径。若约束图不足以推导装配依赖，**停下来报告**，不要自造一套并行的依赖表。 |
| Alembic 迁移在已有数据库上失败 | `downgrade()` 已写全，`alembic downgrade -1` 直接删 4 列，存量数据不使用这些列，无数据损失。 |

---

## 8. 验收总表

> ⚠️ **基线口径统一（2026-08-18 更正）**：本表原以 465 为前端基线，**已作废**。一律对齐 §📍「当前基线」表；每次新增测试后同步更新该表。
> 原表中「`decisionEngine.test.ts` / `hardwareSopsFlow.test.ts` / `sopExecutor.test.ts` / `examMode.test.ts` 不红」一类判据**全部失效**——这些文件不是 vitest 测试、从不执行（§2.4 第 7 条），已替换为可真实执行的判据。

| Task | 验收命令 | 通过判据 | 状态 |
|---|---|---|---|
| 1.1 | `pytest tests/test_sop_three_phase.py -v`；`alembic upgrade head && alembic current` | 3 passed；revision 为 `20260817_sop_three_phase`；ADR 文件存在且含六节 | ✅ |
| 1.2 | `npx vitest run src/adjudication/__tests__/threePhase.test.ts`；`npm run build` | 4 passed；build PASS | ✅ |
| 2.1 | `npx vitest run src/adjudication/__tests__/assemblyDirection.test.ts`；`npm test` | 7 passed；全量不低于基线；**依赖方向取 `constrainingPart === X` 的 `constrainedPart`**；`vitest.config.ts` include 行已提交；未为测试新增 store API | ✅ |
| 2.2 | `npx vitest run src/adjudication/__tests__/threePhase.test.ts` | 齐套 2 用例通过；全量不低于基线 | ✅ |
| 2.3 | 同上 `-t 对角紧固顺序` | 3 用例通过（顺序错/前缀匹配/全序通过） | ✅ |
| 2.4 | 同上 `-t 阶段门`；`npm test` | 3 用例通过；全量不低于基线 | ✅ |
| 3.1 | `npx vitest run .../PhaseProgress.test.tsx`；`npm run build` | 2 用例通过；单段 SOP 不渲染进度条 | ✅ |
| 3.2 | `npx vitest run .../KitChecklistPanel.test.tsx` | 3 用例通过 | ✅ |
| 3.3 | `npx vitest run .../VerifyChecklistPanel.test.tsx` | ≥3 用例通过 | ✅ |
| 3.4 | `npx vitest run src/adjudication/`；`npm test` | 3 用例通过，**含回落启发式的存量兼容用例** | ✅ |
| 4.1 | `pytest tests/test_sop_three_phase.py -v`；curl 核对 | 22 步、4+14+4 分段正确；31 个 SOP 仍在，30 个存量步骤数不变 | ✅ |
| 4.2 | `pytest` | 22 步全带 `step_view`；相机位以 `camera_presets.left_knee_link` 为基准推导；开发日志逐步记录取值与推导依据，并声明未经目视确认 | ✅ |
| 5.1 | `npm run e2e -- sop-three-phase.spec.ts`；后端 `pytest tests/ -v` | E2E 通过；后端 ≥791；前端不低于 §📍 基线 | ⬜ |
| 5.2 | `npx vitest run .../ReportPage.test.tsx`；`npm run build` | 两节正确渲染；无证据时不渲染 | ⬜ |

> 前端新建测试文件一律记得同步加入 `vitest.config.ts` 的 `include`（该目录是单文件白名单，非 glob），否则测试不会执行却看似"通过"。

---

## 9. 自查记录

- **设计覆盖**：§3 三项设计决策（4 列数据模型 / 三段式复用状态机 / 记录复用 `TaskStepResult`）分别由 T1.1、T2.4+T2.2、T5.1 实现，无遗漏。
- **占位符扫描**：无 TBD / TODO / 「类似 Task N」。T3.3 与 T5.2 的步骤以「同 T3.2 节奏」表述但已列明各自的接口定义、文件路径与测试覆盖点，非占位。
- **类型一致性**：`StepView` / `SOPPhase` / `RequiredPart` 在 T1.2 定义，T2.4（`SOPPhase`）、T3.2（`RequiredPart`）、T3.4（`StepView`）引用一致；`getCurrentPhase()` / `getPhaseProgress()` 在 T2.4 定义，T3.1 消费，签名一致；`KIT_CONFIRMED` 在 T1.2 定义、T2.2 实现、T3.2 供数，链路闭合。
- **已剔除的空活**：`sopScripts.ts` 是纯类型透传，原定的 API 客户端 Task 无实际改动，已删除（15 → 14 Task）。
