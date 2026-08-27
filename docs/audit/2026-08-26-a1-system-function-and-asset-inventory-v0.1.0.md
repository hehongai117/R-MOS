# A1 全系统功能与资产清单报告

- 版本：0.1.0
- 日期：2026-08-26
- 状态：**Ready for Board Review**（异源复核已完成，2 条 MISMATCH 已关闭；等待董事会确认）
- 阶段：A1（董事会方向指令 0.2.0 §A1）
- 被审对象：**整个 R-MOS 项目**，不是 Phase 3
- 现状基线：`B-ASIS = 29d2a5889e3b320a3e777e3d8c19efbbe31c0294`
- Phase 3 前参照：`B-REF = 361eaac85002eec4e9388ae4d7f30c2e3591eee6`
- 被审工作区：`/Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime`（分支 `audit/phase3-auth-control-realtime`，未 push）
- 主审：Claude｜异源复核：Codex（§5.8 自 A1 起生效）
- 采集时间：2026-08-26 21:12–21:30 CST
- 生产代码改动：**0**（本批只写 `docs/audit/**` 下的审计材料）

## 1. 执行摘要

本阶段回答「项目实际有什么」，不评价目标架构，不做改造决策。

**系统规模（全部为双源核对后的数字）**

| 对象 | 数量 |
|---|---:|
| 后端 HTTP 路由 | 181 |
| WebSocket 端点 | 2 |
| 后端功能域（有路由的端点模块） | 36 |
| 业务数据表 | 65 |
| 数据库迁移 | 38（单一 head） |
| 后端 Python 模块 | 231（启动导入 206） |
| 后端服务文件 | 99 |
| 后端脚本 | 18 个 `.py` + 5 个 `.sh` |
| 前端页面组件 | 27 |
| 前端路由 | 26 |
| 前端 API 客户端 | 21 |
| 后端测试 | 123 文件 / 971 用例 |
| 前端测试 | 70 文件 / 518 用例（+ 4 个 e2e 规格） |
| 角色 | 4（`admin`/`teacher`/`student`/`auditor`） |

**必须先说清楚的四件事**

1. **上一轮流传的三个「差值」全部是口径错误，不是系统问题。** `182 vs 181`（路由）来自正则误算多行装饰器与 `.pyc`；`103` 张表来自把 `__pycache__` 里的编译残留计入；`37 页面 vs 23 路由`来自把 16 个 `__tests__/*.test.tsx` 当成页面。本报告的每个数字都带排除项声明。
2. **12 类对象全部完成双源核对，差集全部解释，未分类项 0。** 见 [双源枚举差集证据](./evidence/2026-08-26-a1-dual-source-diff-v0.1.0.md)。
3. **183 条路由中 33 条（18%）在本批口径下没有任何消费者或测试引用**，集中在 7 个域；65 张业务表中 28 张为空、37 张有数据。
4. **本批没有执行任何测试**，只做收集与列举，因此所有验证等级上限为 `E1`，不代表测试通过，更不代表 E2/E3/E4。`REL-BLOCK-01` 未受影响。

## 2. 方法与授权边界

| 项 | 内容 |
|---|---|
| 授权依据 | 董事会 2026-08-26 第 6 项决定：批准 A1 在本机回环启动前后端，按报告限定范围 |
| 实际使用的运行时能力 | 导入后端应用取路由注册表；只读查询本机 PostgreSQL；`vite build` 取构建图；`pytest --collect-only`、`vitest list` |
| **未使用**的能力 | 未启动长驻服务、未连真机、未执行测试、未运行 alembic 升级、未写数据库、未 push |
| 工作区改动 | 采集前 `git status --porcelain` 为空；构建产物写到工作区之外；本批新增文件仅 `docs/audit/**` 下 4 份审计材料（本报告 + 2 份证据 + 1 个脚本），另修改 `docs/audit/README.md` 索引 |
| 基线一致性 | `B-ASIS → HEAD` 仅 6 个文档文件变化，应用代码等同基线 |
| 秘密处理 | `.env` 只用于注入环境变量，报告只记字段名与用途，不记值 |

**状态判定规则（互斥，按顺序取第一个成立者）：** `IMPLEMENTED` → `PARTIAL` → `DEMO_ONLY` → `UNUSED` → `DUPLICATE` → `DEPRECATED` → `UNKNOWN`。
**验证等级：** `E1` = 存在可被收集的自动化测试或 e2e 规格；`NOT_VERIFIED` = 本批未找到任何自动化证据。**本批不产出 E2/E3/E4。**

> **域级与路由级口径不同，已声明：** 路由级状态按该路由自身的调用/测试证据判定；域级状态按**最弱链路**判定（例如 `approvals` 域的读接口可达、写接口无可达入口，域级记 `PARTIAL`）。两者不一致时以域级结论进入 A2。

## 3. 功能清单（表 1）

### 3.1 后端功能域（F-BE）

| Function_ID | 域 | 路由数 | 前端客户端 | 后端测试命中 | e2e 命中 | 实现状态 | 验证等级 |
|---|---|---:|---|---:|---:|---|---|
| F-BE-01 | teaching_roster | 21 | `teaching.ts` | 21 | 0 | IMPLEMENTED | E1 |
| F-BE-02 | robots | 16 | `onboarding.ts`、`robots.ts` | 15 | 15 | IMPLEMENTED | E1 |
| F-BE-03 | training | 15 | `robots.ts`、`training.ts` | 15 | 0 | IMPLEMENTED | E1 |
| F-BE-04 | assessments | 11 | 无 | 0 | 0 | **UNUSED** | NOT_VERIFIED |
| F-BE-05 | agent_governance | 10 | `agent-v2.ts` | 10 | 1 | IMPLEMENTED | E1 |
| F-BE-06 | agent_knowledge | 9 | `agent.ts`、`robotKnowledge.ts` | 9 | 0 | IMPLEMENTED | E1 |
| F-BE-07 | tasks | 9 | `pipeline.ts`、`studentTasks.ts`、`task.ts` | 9 | 9 | IMPLEMENTED | E1 |
| F-BE-08 | agent_v2 | 8 | `agent-v2.ts` | 8 | 0 | IMPLEMENTED | E1 |
| F-BE-09 | maintenance | 7 | **无**（前端不调用 `/api/v1/maintenance/*`；维保页走 `sop.ts`／`sopScripts.ts`） | 7 | 0 | IMPLEMENTED | E1 |
| F-BE-10 | sops | 6 | `sop.ts`、`sopScripts.ts` | 6 | 6 | IMPLEMENTED | E1 |
| F-BE-11 | adapter | 5 | 无 | 0 | 0 | **UNUSED** | NOT_VERIFIED |
| F-BE-12 | agent | 5 | `agent-v2.ts`、`agent.ts` | 5 | 0 | IMPLEMENTED | E1 |
| F-BE-13 | fault_cases | 5 | 无 | 0 | 0 | **UNUSED** | NOT_VERIFIED |
| F-BE-14 | training_workbench | 5 | `training.ts` | 5 | 0 | IMPLEMENTED | E1 |
| F-BE-15 | agent_evidence | 4 | `agent.ts` | 4 | 0 | IMPLEMENTED | E1 |
| F-BE-16 | ai_commands | 4 | 无 | 2 | 0 | **PARTIAL** | E1 |
| F-BE-17 | approvals | 4 | `approvals.ts`（**写操作唯一调用页不可达**） | 0 | 0 | **PARTIAL** | NOT_VERIFIED |
| F-BE-18 | auth | 4 | `client.ts` | 4 | 0 | IMPLEMENTED | E1 |
| F-BE-19 | pipeline | 4 | `pipeline.ts` | 0 | 3 | IMPLEMENTED | E1 |
| F-BE-20 | evidence | 3 | 无 | 0 | 0 | **UNUSED** | NOT_VERIFIED |
| F-BE-21 | incidents | 3 | 无 | 0 | 0 | **UNUSED** | NOT_VERIFIED |
| F-BE-22 | observations | 3 | 无 | 0 | 0 | **UNUSED** | NOT_VERIFIED |
| F-BE-23 | skills | 3 | 无 | 3 | 0 | IMPLEMENTED | E1 |
| F-BE-24 | teaching | 3 | 无 | 3 | 0 | IMPLEMENTED | E1 |
| F-BE-25 | admin | 2 | `adminConsole.ts` | 2 | 0 | IMPLEMENTED | E1 |
| F-BE-26 | onboarding | 2 | `onboarding.ts` | 0 | 2 | IMPLEMENTED | E1 |
| F-BE-27 | schools | 2 | `schools.ts` | 2 | 0 | IMPLEMENTED | E1 |
| F-BE-28 | websocket | 2 | `hooks/useWebSocket.ts` 直连（**字符串匹配未命中，见 §7 注**） | 2 | 0 | IMPLEMENTED | E1 |
| F-BE-29 | ai_assistant | 1 | `aiAssistant.ts` | 0 | 0 | IMPLEMENTED | NOT_VERIFIED |
| F-BE-30 | audit | 1 | 无 | 1 | 0 | IMPLEMENTED | E1 |
| F-BE-31 | health | 1 | `adminConsole.ts` | 1 | 1 | IMPLEMENTED | E1 |
| F-BE-32 | llm_health | 1 | 无 | 0 | 0 | **UNUSED** | NOT_VERIFIED |
| F-BE-33 | main（根路由 `/`） | 1 | 不适用 | — | — | IMPLEMENTED | NOT_VERIFIED |
| F-BE-34 | scenarios | 1 | `scenarios.ts` | 0 | 1 | IMPLEMENTED | E1 |
| F-BE-35 | student_tasks | 1 | `studentTasks.ts` | 0 | 0 | IMPLEMENTED | NOT_VERIFIED |
| F-BE-36 | students | 1 | `robots.ts`、`training.ts` | 1 | 0 | IMPLEMENTED | E1 |

合计 36 个域 / 183 条路由：IMPLEMENTED 28 域、PARTIAL 2 域、UNUSED 6 域。逐条路由证据见[对象登记附录 §1](./evidence/2026-08-26-a1-object-register-v0.1.0.md)。

### 3.2 前端功能入口（F-FE）

| Function_ID | 路由 | 页面组件 | 允许角色 | 实现状态 | 验证等级 |
|---|---|---|---|---|---|
| F-FE-01 | `/login` | LoginPage | 匿名 | IMPLEMENTED | E1 |
| F-FE-02 | `/register` | RegisterPage | 匿名 | IMPLEMENTED | E1 |
| F-FE-03 | `onboarding/robots` | OnboardingRobotsPage | 已登录 | IMPLEMENTED | E1 |
| F-FE-04 | `/` | AppLayout + 默认跳转 | 已登录 | IMPLEMENTED | E1 |
| F-FE-05 | `dashboard` | DashboardPage | student | IMPLEMENTED | E1 |
| F-FE-06 | `my-tasks` | MyTasksPage | student | IMPLEMENTED | E1 |
| F-FE-07 | `scenarios` | ScenarioPickerPage | student | IMPLEMENTED | E1 |
| F-FE-08 | `student/skills` | StudentSkillsPage | student | IMPLEMENTED | E1 |
| F-FE-09 | `workbench/teaching` | TeacherMonitorPage | teacher, admin | IMPLEMENTED | E1 |
| F-FE-10 | `teacher/students` | TeacherStudentsPage | teacher, admin | IMPLEMENTED | E1 |
| F-FE-11 | `admin/console` | AdminDashboardPage | admin | IMPLEMENTED | E1 |
| F-FE-12 | `sops` | SOPListPage | teacher, admin | IMPLEMENTED | E1 |
| F-FE-13 | `knowledge` | KnowledgePage | teacher, admin | IMPLEMENTED | E1 |
| F-FE-14 | `shared-robots` | SharedRobotsPage | teacher, admin | IMPLEMENTED | E1 |
| F-FE-15 | `monitor` | MonitorPage | **任何已登录用户** | IMPLEMENTED | E1 |
| F-FE-16 | `maintenance` | SOPMaintenancePage | **任何已登录用户** | IMPLEMENTED | E1 |
| F-FE-17 | `3d-viewer` | Atom01DemoPage | **任何已登录用户** | IMPLEMENTED | E1 |
| F-FE-18 | `teaching/assignments` | TeachingAssignmentsPage | teacher, admin | IMPLEMENTED | E1 |
| F-FE-19 | `teaching/attempts/:id` | TeachingAttemptPage | teacher, admin | IMPLEMENTED | E1 |
| F-FE-20 | `teaching/attempts/:id/evidence` | TeachingEvidencePage | teacher, admin | IMPLEMENTED | E1 |
| F-FE-21 | `teaching/attempts/:id/diagnosis` | TeachingDiagnosisPage | teacher, admin | IMPLEMENTED | E1 |
| F-FE-22 | `agent/workbench` | AgentWorkbenchPage | **任何已登录用户** | IMPLEMENTED | E1 |
| F-FE-23 | `settings` | UserSettingsPage | **任何已登录用户** | IMPLEMENTED | E1 |
| F-FE-24 | `reports` | ReportListPage | **任何已登录用户** | IMPLEMENTED | E1 |
| F-FE-25 | `reports/:taskId` | ReportPage | **任何已登录用户** | IMPLEMENTED | E1 |
| F-FE-26 | `*` | 兜底跳转 | 已登录 | IMPLEMENTED | NOT_VERIFIED |
| F-FE-27 | **（无路由）** | **ApprovalQueuePage** | — | **UNUSED** | NOT_VERIFIED |

26 条路由 + 1 个无路由页面。7 条路由（`monitor`、`maintenance`、`3d-viewer`、`agent/workbench`、`settings`、`reports`、`reports/:taskId`）在 `ROUTE_PERMISSIONS` 中显式为 `undefined`，即任何已登录用户可访问，其中包含维保作业与 AI 工作台。**本阶段只登记，不下裁决，身份矩阵由 A4 承接。**

### 3.3 角色与账号

| 角色 | 数据库 | 后端使用点 | 前端入口 | 状态 |
|---|---|---|---|---|
| admin | ✅ | 广泛 | `admin/console` 等 | IMPLEMENTED |
| teacher | ✅ | 广泛 | 教学与机器人管理页 | IMPLEMENTED |
| student | ✅ | 广泛 | 学生页 | IMPLEMENTED |
| auditor | ✅ | 仅 `ai_commands.py`、`approvals.py`、`audit.py` 三处字符串判断 | **无任何前端入口** | **PARTIAL** |

账号现状：`users` 表 13 行。**角色没有集中的枚举定义**——后端是散落的字符串字面量，前端是 `src/config/routes.ts` 的权限表（只出现 student/teacher/admin），数据库是 `roles` 表 4 行。三处各说各话，无单一事实源。

## 4. 技术资产清单（表 2）

| Asset_ID | 类型 | 路径/名称 | 数量 | 消费方 | 状态 | 重复/孤立 |
|---|---|---|---:|---|---|---|
| A-01 | 后端路由 | `app/api/v1/endpoints/**` | 181 | 前端 21 个 API 客户端、测试 | IMPLEMENTED | 33 条无消费者 |
| A-02 | WebSocket | `endpoints/websocket.py` | 2 | 前端 `useWebSocket` | IMPLEMENTED | — |
| A-03 | 端点文件 | `app/api/v1/endpoints/*.py` | 37 | — | IMPLEMENTED | 3 个不含路由（`__init__.py`、`teaching_common.py` 为共享辅助、`websocket.py` 为 WS） |
| A-04 | 服务 | `app/services/**` | 99 | 端点、脚本 | IMPLEMENTED | `llm/audit.py`、`policy/` 整包无可达消费者 |
| A-05 | 数据模型 | `app/models/**` | 65 张表 | ORM | IMPLEMENTED | 28 张表无数据（精确计数） |
| A-06 | 迁移 | `alembic/versions/*.py` | 38 | alembic | IMPLEMENTED | 单一 head，无分叉 |
| A-07 | 适配器 | `app/adapters/{base,mock,factory,schemas}.py` | 4 | `adapter` 域（该域 5 条路由无消费者） | IMPLEMENTED | 仅 Mock 实现 |
| A-08 | 后台管线 | `services/analysis/scheduler.py` 的 4 个 process 步骤 | 4 | 分析任务 | IMPLEMENTED | 步骤模块均为延迟导入 |
| A-09 | 后端脚本 | `r-mos-backend/scripts/**` | 18 py + 5 sh | 人工执行 | IMPLEMENTED | 不在应用可达图内，属正常 |
| A-10 | 前端页面 | `src/**/pages/**` | 27 | 路由 | IMPLEMENTED | `ApprovalQueuePage` 孤立 |
| A-11 | 前端路由 | `src/App.tsx` | 26 | — | IMPLEMENTED | — |
| A-12 | 前端 API 客户端 | `src/api/*.ts` | 21 | 页面 | IMPLEMENTED | `tools.ts` 零引用 |
| A-13 | 3D 渲染栈（现行） | `UniversalRobotViewer` 等 | 在构建图内 | `3d-viewer`、维保页 | IMPLEMENTED | — |
| A-14 | 3D 渲染栈（旧） | `Atom01Viewer`、`Viewer3D/index.ts`、`Atom01Model`、`DynamicModelLoader`、`RobotViewer`、`HumanoidRobot`、`constants.ts`、`hooks/useRobotData.ts`、`ModelPreloader` | 9 | 无 | **UNUSED** | 被 A-13 取代但未清理；两个根节点 `Atom01Viewer` 与 `Viewer3D/index.ts` 均零引用 |
| A-15 | 后端测试 | `r-mos-backend/tests/**` | 123 文件 / 971 用例 | pytest | IMPLEMENTED | — |
| A-16 | 未收集的后端测试 | `r-mos-backend/schemas/tests/**` | 7 文件 | 无 | **UNUSED** | 不在 `testpaths` 内，从未执行 |
| A-17 | 前端测试 | `src/**/*.test.ts(x)` | 70 文件 / 518 用例 | vitest | IMPLEMENTED | — |
| A-18 | 伪测试 | `src/adjudication/__tests__/*.test.ts` | 8 文件 | 无 | **UNUSED** | 无 `describe/it`，vitest 不收集（CLAUDE.md 已声明的已知遗留） |
| A-19 | e2e 规格 | `r-mos-frontend/e2e/*.spec.ts` | 4 | Playwright | IMPLEMENTED | 本批未执行 |
| A-20 | 机器人资产 | `data/robot-assets/**` | 1 个文件（A0 采集） | 3D/manifest | UNKNOWN | 与 manifest 的匹配关系由 A3 承接 |
| A-21 | 文档 | 仓库内 Markdown | 136 | 人 | IMPLEMENTED | 数字声明滞后，见表 4 |
| A-22 | 数据库扩展 | `plpgsql 1.0`、`vector 0.8.2` | 2 | 向量检索 | IMPLEMENTED | 部署依赖，A3 承接 |

## 5. 双源枚举差集（表 3）

完整表与复现命令见[双源枚举差集证据](./evidence/2026-08-26-a1-dual-source-diff-v0.1.0.md)。摘要：

| Scope_ID | 对象 | 静态 | 运行时/构建 | 归并 | 剩余 UNKNOWN |
|---|---|---:|---:|---|---:|
| S-01 | 后端 HTTP 路由 | 181 | 181 | 差集 0 | 0 |
| S-02 | WebSocket | 2 | 2 | 差集 0 | 0 |
| S-03 | 框架自带路由 | 0 | 4 | 已解释，不计入功能 | 0 |
| S-04 | 数据表 | 65 | 65 / 66 | 仅差 `alembic_version` | 0 |
| S-05 | 迁移 | 38 | 38 + 数据库 head | 三源一致 | 0 |
| S-06 | 前端页面 | 27 | 构建图 | 1 项孤立已归因 | 0 |
| S-07 | 前端路由 | 26 | 分包产物 | 差集 0 | 0 |
| S-08 | 前端模块 | 195 | 167 | 28 项逐个归因 | 0 |
| S-09 | 后端模块 | 231 | 206 | 25 项逐个归因 | 0 |
| S-10 | 后端测试 | 123 | 123 / 971 | 差集 0（另有 7 个从未收集的文件） | 0 |
| S-11 | 前端测试 | 78 | 70 / 518 | 差 8 = 伪测试 | 0 |
| S-12 | 角色 | 无集中定义 | 数据库 4 行 | 4 种角色 | 0 |

**M-AUD-01 达标：** 12 类对象全部具备两条异源枚举路径，差集全部解释并归并，未分类项 0，剩余 UNKNOWN 0。

## 6. 声明与现实差异（表 4）

| Claim_ID | 文档声明 | 当前事实 | 判定 | 处理阶段 |
|---|---|---|---|---|
| C-01 | CLAUDE.md 将 `useRobotDataManifest.ts` 列为「Key Modularization Files（Phase 1 output）」 | 该文件**零引用、不在构建图内** | FACT | A3 决定保留或删除 |
| C-02 | CLAUDE.md：Universal 3D Viewer「done」 | 属实，但被取代的旧 3D 栈 9 个文件仍在仓库且不可达 | FACT | A3 |
| C-03 | CLAUDE.md 已知遗留：`src/adjudication/__tests__/` 8 个非 vitest 测试 | **复核属实**，vitest 只收集到 70/78 | FACT（声明与现实一致） | A5 决定重写或删除 |
| C-04 | CLAUDE.md：「22 endpoints」 | 端点文件 37 个，其中 34 个含路由，另加根路由与 WS 共 36 个域 | FACT（文档滞后） | A6 修订 |
| C-05 | CLAUDE.md：「50+ services」 | 99 个服务文件 | FACT（文档滞后） | A6 修订 |
| C-06 | CLAUDE.md：「32+ models」 | 65 张业务表 | FACT（文档滞后） | A6 修订 |
| C-07 | CLAUDE.md：「15+ pages」 | 27 个页面组件、26 条路由 | FACT（文档滞后） | A6 修订 |
| C-08 | A0 运行指纹 `FP-CFG-01` 记录 10 个 `.env` 字段名 | **被审工作区没有 `.env`**，该指纹取自主工作区，指纹对象与被审对象不同源 | FACT（A0 口径缺陷） | A0 出 0.1.2 修订，改写口径或降为 UNKNOWN |
| C-09 | 无任何文档提及 `r-mos-backend/schemas/tests/` 下的 7 个测试 | 存在且从未被 pytest 收集 | FACT（未登记资产） | A5 |
| C-10 | 无任何文档提及 `app/main.py` 与根 `main.py` 并存 | 两者同时存在，`app/main.py` 仅被测试引用 | FACT（重复入口） | A3 |

## 7. 本阶段关键发现

> A1 只登记事实，不排优先级、不给修复方案。以下条目均带证据指向，供 A2/A3/A4 承接。

| 发现 | 事实 | 证据 |
|---|---|---|
| **A1-F-01** | `assessments` 域 11 条路由**零前端消费者、零后端测试**，是最大的孤立功能块；`assessment` 一词在整个前端源码中命中 0 个文件 | 附录 BE-RT，`grep -rl assessment r-mos-frontend/src` = 0 |
| **A1-F-02** | 合计 **33 条路由**无任何消费者或测试引用，分布：assessments 11、adapter 5、fault_cases 5、incidents 3、observations 3、evidence 3、ai_commands 2、llm_health 1 | 附录 BE-RT |
| **A1-F-03** | **AI 审批闭环在 UI 上断裂**：`/ai/approvals/{id}`、`/grant`、`/reject` 的唯一页面级调用点是**不可达的** `ApprovalQueuePage`；可达的 `AdminDashboardPage` 只调用 `listApprovals`。该域后端测试为 0 | 构建图 + import 链 |
| **A1-F-04** | 旧 3D 渲染栈 **9 个文件**整簇不可达（两个根节点 `Atom01Viewer.tsx` 与 `Viewer3D/index.ts` 零引用，其余只被这些不可达模块引用），与现行 `UniversalRobotViewer` 并存 | sourcemap 构建图 + TypeScript 模块解析 |
| **A1-F-05** | 65 张业务表中 **28 张为空、37 张有数据**（逐表精确 `count(*)`）。数据量最大的是 `robot_assets` 33,367 行与 `schools` 2,869 行，说明机器人资产与学校名录已有实质数据；教学链路的表则普遍是个位数到两位数 | 逐表 `count(*)` |
| **A1-F-06** | 测试资产存在两处「看着有、其实没跑」：前端 8 个伪测试文件、后端 7 个从未被收集的测试文件 | `vitest list`、`pytest --collect-only` |
| **A1-F-07** | 后端 3 个模块全仓零引用（`app/schemas/user.py`、`app/services/llm/audit.py`、`app/services/policy/__init__.py`），其中 `policy` 包整体不可达，连带 `risk_scorer.py` 无消费者 | 启动闭包 + 引用检索 |
| **A1-F-08** | `auditor` 角色在数据库中存在、后端 3 处有授权判断，但**前端没有任何入口**；`ROUTE_PERMISSIONS` 中完全不出现该角色 | `roles` 表、`src/config/routes.ts` |
| **A1-F-09** | 角色定义**没有单一事实源**：后端散落字符串、前端权限表、数据库表三处并存 | 同上 |
| **A1-F-10** | 7 条前端路由对**任何已登录用户**开放，其中包含 `maintenance`（维保作业）与 `agent/workbench`（AI 工作台） | `ROUTE_PERMISSIONS` 中显式 `undefined` |
| **A1-F-11** | **61 条路由（182 条中的 34%）没有任何前端调用或 e2e 引用**，即后端能力远多于 UI 暴露面。其中 `maintenance` 域 7 条全部无前端调用——维保页面走的是 `sop.ts`／`sopScripts.ts`，不碰 `/api/v1/maintenance/*` | 附录 BE-RT |

> **§7 注（方法局限的实例）：** WebSocket 的两条端点在自动匹配中显示「前端调用 0」，但人工核对发现 `src/hooks/useWebSocket.ts` 确实连接 `${WS_BASE_URL}/ws/robot/${robotId}/status`——路径中间含变量，字符串匹配未命中。这是**假阴性的真实样本**，说明 `UNUSED` 判定必须逐条人工复核后才能作为删除依据。本报告已对该条做人工修正；其余 33 条 `UNUSED` 尚未逐条人工复核，A2/A3 承接时必须重验。

## 8. 退出门禁自评

| 门禁 | 要求 | 本报告 | 结论 |
|---|---|---|---|
| M-AUD-01 | 每类对象两条异源路径，差集为 0 或已解释，分母内覆盖率 100% | 12 类全部双源，差集全部解释，未分类 0 | ✅ 达标 |
| A1-G1 | 所有清单项有唯一编号和证据来源 | F-BE-01~36、F-FE-01~27、A-01~22、BE-RT-001~183、DB-TB-001~065、BE-MOD-001~025、FE-MOD-001~028 | ✅ 达标 |
| A1-G2 | 未分类项为 0 | 0 | ✅ 达标 |
| A1-G3 | 实现状态与验证等级两列分开，状态互斥且唯一 | 已按 §2 规则判定 | ✅ 达标 |
| A1-G4 | 不得把「代码存在」写成「真实可用」 | 全报告验证等级上限 E1，并显式声明本批未执行测试 | ✅ 达标 |
| §5.8 | 自 A1 起主审与复核异源 | Codex 两轮共 20 条断言复核完成，2 条 MISMATCH 全部复验采纳并修正 | ✅ 达标 |

**A1 当前状态：Ready for Board Review。** 全部退出门禁达标，异源复核两轮结束、2 条 MISMATCH 均已关闭。进入 A2 需董事会确认本报告。

## 9. 异源复核记录

| 项 | 内容 |
|---|---|
| 复核方 | Codex（`codex exec`，只读沙箱，`-C` 指向被审工作区） |
| 复核范围 | 第一轮 13 条断言（A-01~A-13）：路由、WebSocket、表、迁移、页面、孤立模块、后端模块可达性、重复入口、测试计数、资产计数、数据库现状 |
| 纪律要求 | 自行重新推导；禁止读取主审脚本与结果文件；禁止任何写操作 |
| 独立性证据 | Codex 主动声明：审计期间观察到「另一个进程在共享工作区生成 A1 文档并修改 README」，但**没有打开或使用这些文件**；结束时确认 `r-mos-backend/` 与 `r-mos-frontend/` 无任何改动或新增 |
| 第一轮结论 | **OVERALL: MISMATCH(1)** — 5 条 AGREE、4 条 AGREE_WITH_CAVEAT、1 条 MISMATCH、3 条 UNKNOWN |
| 第二轮（定向数据库复核） | 7 条断言 D-01~D-07；**OVERALL: MISMATCH(1)** — 6 条 AGREE、1 条 MISMATCH |
| 两轮合计 | 20 条断言，**2 条 MISMATCH，均已由主审复验后采纳并修正** |

### 9.1 MISMATCH 处置

| ID | Codex 主张 | 主审复验 | 处置 |
|---|---|---|---|
| **MISMATCH-01**（对应断言 A-07） | 主审列出的 8 个「零引用」前端模块中只有 6 个成立：`adjudication/data/criticalParts.ts` 被 `adjudication/index.ts` **再导出**；`adjudication/ui/examHeader.ts` 被 `__tests__/p4_mode.test.ts` **直接 import** | 主审用 `grep` 逐条复验，**Codex 完全正确**。根因是主审初版用文件 basename 拼相对路径（`./criticalParts`），匹配不到带子目录的 specifier（`./data/criticalParts`）；同时 barrel 目录名模糊匹配把 `Viewer3D/index.ts` 误判为「仅测试消费」 | **采纳**。判定逻辑改写为真正的 TypeScript 模块解析（`@/` 别名、相对路径、`index.ts` 兜底、`vi.mock`、动态 `import()`），全部 28 个模块重新分类：零引用 8 → **6**，新增「仅测试引用 3」与「构建配置加载 1」。差集证据 §5 与对象登记附录 §5 已同步重写 |

Codex 附带指出 `test-setup.ts` 虽无代码 import，但由 `vitest.config.ts` 的 `setupFiles` 加载，不宜称为无引用——主审核实属实，已单列为「构建配置加载」。

| ID | Codex 主张 | 主审复验 | 处置 |
|---|---|---|---|
| **MISMATCH-02**（对应断言 D-07） | 主审的「7 张表非空、58 张为空」错误：逐表精确 `count(*)` 的结果是 **37 张非空、28 张为空**。主审用的 `pg_stat_user_tables.n_live_tup` 是统计估算值，恰好停在一个陈旧快照上 | 主审对全部 65 张业务表重新执行 `count(*)`，结果与 Codex **完全一致**（37/28），并确认 **35 张表**的估算值与精确值不符：`robot_assets` 估算 0／实际 33,367，`schools` 估算 0／实际 2,869，`users` 估算 0／实际 13——而主审报告里的 `users 13` 用的恰恰是精确查询，等于自己和自己矛盾 | **采纳**。清点脚本 `database_facts()` 改为逐表精确计数，估算值降级为「漂移提示」并单列 `stale_estimates`；主报告、差集证据、对象登记附录三处口径同步修正 |

**这条错误的性质比 MISMATCH-01 严重：** 它不是把一个孤立对象数错，而是把整个系统的数据现状描述反了——原结论暗示「系统几乎没被使用过」，而事实是机器人资产 33,367 行、学校名录 2,869 行、令牌表各 389 行，教学链路各表也普遍有个位数到两位数的真实数据。A2 的流程判断如果建立在错误版本上，会得出完全相反的结论。

### 9.2 口径说明（AGREE_WITH_CAVEAT）

| 断言 | 口径差异 | 处置 |
|---|---|---|
| A-01 | Codex：端点目录 180 条 + 根 `main.py` 1 条 = 181 | 与主审一致，只是拆分口径不同，无需修改 |
| A-08 | 主审给 Codex 的断言按 `app/` 目录计 230/205/25；本报告按「`app/` + 后端根目录 `*.py`」计 **231/206/25**（多出的 1 个是根 `main.py`，它注册了根路由，不计会漏路由） | 两者自洽，已在此显式声明避免读者对不上 |
| A-09 | Codex 独立确认：uvicorn、Docker 与启动脚本均使用根 `main.py`；`app/main.py` 的唯一 import 者是 `tests/e2e/test_agent_execute.py` | 强化 C-10，无冲突 |
| A-11 | Codex 用 `createVitest().listFiles()` + AST 计数（原生 `vitest list` 在只读沙箱下写临时配置失败）：70 文件、518 可列出用例，另有 2 个 skipped 被过滤；该目录共 12 个 `.test.ts`，其中 **8 个无测试声明** | 与主审一致，并补充了「12 个中的 8 个」这一更精确的分母 |
| A-12 | 端点文件 37 含 `__init__.py`，排除后 36 | 本报告 A-03 已按 37 计并注明 3 个不含路由，口径已声明 |

### 9.3 定向数据库复核（补充第二轮）

第一轮 A-04（数据库 66 张表）、A-05（`alembic_version` 内容）、A-13（角色、行数、非空表）三条为 **UNKNOWN**：
Codex 的只读沙箱同时拒绝 TCP 与 Unix 套接字连接（`PermissionError errno=1`），SELECT 无法执行。

主审据此另派**定向数据库复核**：工作目录设在被审仓库之外（Codex 无法写入被审工作区），授予网络访问，
明令只读、禁止任何写库语句与 alembic 升级。复核 D-01~D-07 七条断言，结论：

| 断言 | 结论 |
|---|---|
| D-01 public schema 66 张表 | AGREE |
| D-02 业务表 65 张与 ORM metadata 双向差集 0，唯一额外表是 `alembic_version` | AGREE |
| D-03 `alembic_version` 单行 `20260817_sop_three_phase`，与迁移图唯一 head 一致 | AGREE |
| D-04 扩展为 `plpgsql 1.0`、`vector 0.8.2` | AGREE |
| D-05 `roles` 4 行 admin/teacher/student/auditor | AGREE |
| D-06 `users` 13 行 | AGREE |
| D-07 非空表清单 | **MISMATCH** → 见 MISMATCH-02 |

复核方声明：未修改被审仓库任何文件，未执行任何写数据库语句。主审事后核对 `git status --porcelain`，
被审工作区确实只有主审自己新增的审计材料，Codex 零改动。

**至此 A1 的数据库事实已由两名独立观察者确认**，M-AUD-01 与 §5.8 的异源要求均已满足。

## 10. 移交下阶段的问题

| 移交项 | 承接阶段 | 说明 |
|---|---|---|
| 33 条无消费者路由的去向 | A2/A3 | A2 判断是否属于未接入的流程，A3 判断保留/替换/删除 |
| AI 审批闭环断裂（A1-F-03） | A2 | 审批是完整业务流程的一环，需在流程视角确认断点位置 |
| 7 条对所有已登录用户开放的路由 | A4 | 身份与对象矩阵逐条裁决 |
| `auditor` 角色无入口、角色无单一事实源 | A4 | 同上 |
| 28 张空表 + `robot_assets` 33,367 行的资产集中度 | A3 | 数据所有权与生命周期 |
| 旧 3D 栈、重复入口 `app/main.py` | A3 | 可替换边界与删除边界 |
| 伪测试与未收集测试 | A5 | 测试有效性 |
| CLAUDE.md 数字声明滞后（C-04~C-07） | A6 | 文档修订 |
| A0 `FP-CFG-01` 口径缺陷（C-08） | A0 修订 | 需出 0.1.2 |

## 11. 本批产出物

| 文件 | 说明 |
|---|---|
| 本报告 | A1 主报告 |
| [双源枚举差集证据](./evidence/2026-08-26-a1-dual-source-diff-v0.1.0.md) | 口径、12 类差集、复现命令、方法局限 |
| [对象登记附录](./evidence/2026-08-26-a1-object-register-v0.1.0.md) | 183 路由 / 65 表 / 25 未导入模块 / 28 未进构建图模块逐条登记，机械生成 |
| [双源清点脚本](./evidence/2026-08-26-a1-dual-source-inventory.py) | 可复现脚本，差集未解释时退出码非 0 |
