# A2 用户角色与业务闭环审计报告

- 版本：0.1.0
- 日期：2026-08-27
- 状态：**Ready for Board Review**（异源复核已完成，3 条 MISMATCH 已关闭；等待董事会确认）
- 阶段：A2（董事会方向指令 0.2.0 §A2）
- 被审对象：整个 R-MOS 项目
- 现状基线：`B-ASIS = 29d2a5889e3b320a3e777e3d8c19efbbe31c0294`
- 上游输入：[A1 全系统功能与资产清单报告（Approved，提交 `67a4ce30`）](./2026-08-26-a1-system-function-and-asset-inventory-v0.1.0.md)
- 主审：Claude｜异源复核：Codex
- 生产代码改动：**0**

## 1. 执行摘要

A2 回答「功能怎样组合成真实用户流程」。方法是把 A1 清点的 183 条路由、27 个页面、65 张表接成端到端链路，
再用两条硬证据判断每条流程的真实状态：**该流程的写操作在前端有没有入口**，以及**数据库里有没有对应数据**。

**核心事实：系统有 94 条写操作路由，其中只有 51 条（54%）能从前端发起，43 条没有任何 UI 入口。
11 个后端域完全没有写入口。**

由此，董事会最低流程清单分成三类：

18 条流程（17 条用户流程 + 1 条基础设施）的状态分布：**CLOSED 4、PARTIAL 7、SEEDED_ONLY 3、BROKEN 1、MISSING 2**，
另加 1 条基础设施探针 CLOSED。

**（一）写操作齐备、有真实数据、能从头走完的只有 4 条**
注册与入校（FL-01）、登录与会话（FL-02）、机器人接入与建模（FL-05）、评分与技能画像（FL-11）。
支撑数据：`robot_models` 13 行、`robot_assets` 33,367 行、`assignment_attempts` 9 行（6 已完成）、
`student_skill_profiles` 8 行、`access_tokens` 389 行。

**（一·补）链路存在但缺关键环节的 7 条**
知识治理（批准后无切块产物）、SOP 制作（无发布状态列、无更新接口）、任务下发（无完成接口且执行全无终态）、
证据生成（写入口缺失、一套模型全空）、报告（上游无终态）、维保作业（后端域 5 个写操作零调用）、
审计回放（三套并行且回放数据全空）。

**（二）后端齐备、有测试，但前端没有入口，现有数据全靠脚本预置（4 条）**

| 流程 | 缺失的写操作 | 后端测试 | 数据来源 |
|---|---|---:|---|
| 教师建班 / 建课 | `POST /classes`、`POST /courses` | 6 / 2 | **直接证据**：`classes`/`courses` 的 `metadata` 列带 `{"seed":"acceptance_users"}`(2) 与 `{"seed":"demo_full"}`(1) |
| 学生加入班级 | `POST /enrollments` | 5 | 推断：无标记列，但外键挂在上述 seed 班级上且同分钟批量创建 |
| 布置作业 | `POST /assignments` | 4 | 推断：同上 |
| **训练会话生命周期** | `POST /training/sessions` 及 pause/resume/abandon/submit/force-submit，**7 个写操作全部无入口** | 12 | 推断：17 条创建于同一分钟，无标记列 |

训练这条尤其要紧：`training_sessions` 17 行、16 行 `submitted`，看上去是跑通的闭环，
但**前端既不能创建会话也不能提交会话**——学生在工作台只能提交单个步骤
（`POST /training/workbench/sessions/{id}/steps/{id}/submit`），会话级的开始与结束在 UI 上不存在。

**（三）系统层面不存在（2 条）**
机器人控制与异常停止。`BaseRobotAdapter` 的 10 个抽象方法全部是连接、读取与故障注入，
没有任何运动控制或急停方法；急停只作为 `MockRobotAdapter.apply_maintenance_action()` 的一个分支存在，
由模拟执行器按动作描述里的中文关键词「停机／急停」触发，**没有任何 HTTP 端点暴露**。

还有一类问题独立于上述三类：**前端存在 15 条指向后端不存在端点的悬空调用**，
包括管理台的 AI 监控与指标面板（`/agent/monitor/*`、`/agent/metrics*`）、Agent 回放（`/agent/replay/*`），
以及用户设置页的**修改密码**与**修改资料**（`POST /auth/change-password`、`PATCH /auth/profile`）——
后两条是用户可见功能，点击必然失败。详见 §5.1。

此外，AI 审批闭环双线并行且两条都没跑过（`approvals` 与 `approval_records` 两张表都是空的），
另有 7 组重复链路与 14 处流程断点，逐条登记在 §6、§7。

一条贯穿全局的事实：**教学与训练闭环的全部数据停在 2026-05-14，三个半月没有新增**；
仍在演进的是 SOP／任务链路（最新 2026-08-21）与机器人资产（2026-08-05）。详见 §4.1。

**本批未执行任何测试，验证等级上限 E1。**

## 2. 方法与口径

| 项 | 内容 |
|---|---|
| 链路构建 | 前端 TypeScript 模块解析求「页面 → 可达模块」传递闭包；在闭包内扫描 HTTP 调用点字面量；再按 (动词, 归一化路径) 与后端运行时路由表对接 |
| 调用点扫描范围 | **不限 `src/api/`**——认证请求由 `src/store/authStore.ts` 自建的 axios 实例发出，只扫 `src/api/` 会整条漏掉 |
| 路径归一化 | 前端 `${x}` 与后端 `{x}`／`{x:path}` 统一折叠为 `{}`；剥离 `/api/v1` 前缀与开头的 `${API_BASE_URL}` |
| 流程是否跑通 | 需同时看两件事：**写操作有无前端入口**（能否由用户发起）与**数据库有无数据**（是否真的发生过） |
| 数据口径 | 行数一律精确 `count(*)`（沿用 A1 MISMATCH-02 的纠正） |
| 未做的事 | 未执行测试、未启动长驻服务、未连真机、未写数据库、未 push |

**状态定义：**
`CLOSED` 写操作有 UI 入口且有真实数据；
`SEEDED_ONLY` 后端能力齐备但前端无入口，现有数据非 UI 产生（由脚本或直调 API 生成）；
`PARTIAL` 链路存在但缺必要环节或关键产物为空；
`BROKEN` 双实现并行且都无数据；
`MISSING` 系统层面不存在。

### 2.1 对 A1 的一处方法修正（A2 发现）

A1 判断「路由是否有前端调用」采用**路径级子串**匹配：把路由路径去掉 `/api/v1` 后作为子串在前端文件里搜，
**既不区分 HTTP 动词，也会被前缀相同的路由互相带命中**。A2 按 (动词, 归一化完整路径) 重新对接：

| 口径 | 有前端调用的路由数 |
|---|---:|
| A1 路径级子串 | 121 |
| A2 动词级精确 | **94** |
| A1 有而 A2 无 | 27 |
| A2 有而 A1 无 | **0** |

差额 27 条的成因样本：`POST /assignments` 命中的是 `App.tsx` 与 `routes.ts`——那里出现的 `teaching/assignments`
是**前端路由字符串，根本不是 API 调用**；`POST /admin/users/{id}/role` 命中 `adminConsole.ts` 只因该文件含 `/admin/users`；
`PATCH /classes/{id}` 命中 `teaching.ts` 只因该文件含 `/classes`。反向差额为 0，说明 A2 口径严格收紧、无新增命中。

> 这条修正**不改变 A1 的 33 条 UNUSED 结论**（那 33 条本就路径级零命中），只收紧「有消费者」一侧。
> 按 §5 重开点规则记入 A1 待修订项，待 A2 获确认后一并出 A1 0.1.1。

### 2.2 方法局限

1. **可达闭包是文件级，不是函数级。** 页面引用了某个 API 客户端文件，该文件内的**全部**调用点都会被计入可达。
   典型例子：`AdminDashboardPage` 只用 `approvals.ts` 的 `listApprovals`，但该文件里的 `grant`/`reject`
   也因此被算作「可达」——实际调用它们的页面是不可达的 `ApprovalQueuePage`。§4 的 FL-16 已按函数级事实单独说明。
2. 调用点扫描只识别**字符串字面量**路径，变量拼出的完整路径会漏判。
3. 页面可达闭包是**静态**的，含条件分支下可能永不执行的调用；「可达」不等于「一定会调用」。
4. 数据库是本机开发库快照。表为空证明「在本库从未产生过数据」，不证明其他环境不可用。
5. 本批未执行测试，验证等级上限 E1。

## 3. 角色与账号（A2 视角）

| 角色 | 数据库 | 实际账号 | 可达入口 | 能自主完成的动作 | 结论 |
|---|---|---:|---|---|---|
| student | ✅ | 8 | dashboard、my-tasks、scenarios、student/skills、maintenance 等 | 答题、提交步骤、看报告 | 闭环成立 |
| teacher | ✅ | 4 | workbench/teaching、teacher/students、sops、knowledge、shared-robots、monitor | 建机器人、传知识、建 SOP、批改；**不能建班、加学生、布置作业** | **闭环不完整** |
| admin | ✅ | 1 | admin/console + 教师全部入口 | AI 治理监控与审批；**不能改用户角色**（`POST /admin/users/{id}/role` 无前端入口） | **闭环不完整** |
| auditor | ✅ | **0** | **无** | 无 | **无入口、无账号** |

`users` 表 13 行与 `user_roles` 表 11 行不等：**2 个用户没有 `user_roles` 记录**，但 `users.role` 列 13 行全有值——
这是 §6 D-04「角色两套存储」在数据上的直接体现。

## 4. 用户流程（表 1）

| Flow_ID | 角色 | 目标 | 入口 | 状态序列 | 输出 | 当前结果 | 证据 |
|---|---|---|---|---|---|---|---|
| FL-01 | 匿名→学生/教师 | 注册与入校 | `/register` | 选校 → 注册 → 首登 → onboarding | `users` 行 | **CLOSED** | `POST /auth/register` 前端✓、后端测试 19；`users` 13、`schools` 2,869 |
| FL-02 | 全部 | 登录与会话保持 | `/login` | login → refresh → logout | 双令牌 | **CLOSED** | 四个写操作前端全✓；`access_tokens` 389、`refresh_tokens` 389 |
| FL-03 | 教师 | 建班与建课 | **无 UI 入口** | — | `classes`/`courses` | **SEEDED_ONLY** | `POST /classes`、`POST /courses` 前端✗（后端测试 6/2）；`classes` 3、`courses` 3 的 `metadata` 列带 `{"seed":"acceptance_users"}`(2)、`{"seed":"demo_full"}`(1)，**直接证明由种子脚本生成** |
| FL-04 | 教师/学生 | 学生加入班级 | **无 UI 入口** | — | `enrollments` | **SEEDED_ONLY** | `POST /enrollments` 前端✗（后端测试 5）；`enrollments` 7 无标记列，但外键挂在 seed 班级上且同分钟批量创建（推断，非直接证据） |
| FL-05 | 教师 | 机器人接入与建模 | `monitor`、`onboarding/robots`、`shared-robots` | 创建 → 上传 → AI 分析 → 发布 → 绑定/共享 | `robot_models`、`robot_assets` | **CLOSED** | 8 个写操作前端全✓；`robot_models` 13（9 ready/4 draft）、`robot_assets` 33,367、`analysis_tasks` 9（8 completed）、`teacher_robot_bindings` 7 |
| FL-06 | 教师 | 知识治理 | `knowledge` | 上传 → 提交 → 批准 → 切块 → 检索 | 知识块 | **PARTIAL** | upload/submit/approve 前端全✓；但 `knowledge_documents` 30 中 **27 仍 PENDING**，且 `ai_knowledge_chunks` **空**——批准后没有切块产物 |
| FL-07 | 教师 | SOP 制作与发布 | `sops` | 创建（或 AI 生成）→ 保存 → 供任务引用 | `sops`/`sop_steps` | **PARTIAL** | `POST /sops`、`DELETE /sops/{id}` 前端✓（**无更新接口**）；`sops` 54、`sop_steps` 719；但 `sops` 表**没有 status/发布状态列**，无发布门禁；`robot_sop_drafts` 空 |
| FL-08 | 教师→学生 | 任务下发与执行 | `sops`、`teaching/assignments`、`my-tasks`、`scenarios` | 建任务 → start → step → pause/resume | `tasks`/`task_executions` | **PARTIAL** | 创建/start/step/pause/resume 前端✓，**`tasks` 域无完成接口**；`tasks` 30（13 in_progress/10 pending/6 completed/1 cancelled，仅 18 条关联 SOP）；**`task_executions` 11 行全 `in_progress`，无任何终态** |
| FL-09 | 学生 | 训练会话执行与提交 | `dashboard`、`workbench/teaching`（仅读与步骤提交） | active →(pause/resume)→ submitted | `training_sessions` | **SEEDED_ONLY** | **7 个会话级写操作前端全✗**（创建、pause、resume、abandon、submit、force-submit、steps；后端测试 12）；前端只有步骤级 `workbench/.../steps/{id}/submit`✓；`training_sessions` 17（16 submitted）全部创建于同一分钟，无标记列（推断为脚本生成，非直接证据） |
| FL-10 | 系统/教师 | 证据生成与封存 | `teaching/attempts/:id/evidence`（只读） | 采集 → 关联 → 封存 | `evidence_bundles`/`evidence_links` | **PARTIAL** | `POST /evidence_cards`、`POST /evidence-bundles` 前端✗；`evidence_bundles` 6、`evidence_links` 6 有数据，**`evidence_cards`、`evidence_items` 空**（两套模型见 D-03） |
| FL-11 | 教师/系统 | 评分与技能画像 | `teaching/attempts/:id`、`student/skills` | 批改 → 分数 → 画像 → 弱项 | `student_skill_profiles` | **CLOSED** | `POST /attempts/{id}/grade`、`PATCH /attempts/{id}` 前端✓；`assignment_attempts` 9（6 completed）、`student_skill_profiles` 8、`student_weak_steps` 4。外部评估侧 `assessments` 域 **6 个写操作全✗**、三张评估表全空 |
| FL-12 | 学生/教师 | 报告查看 | `reports`、`reports/:taskId` | 任务完成 → 生成报告 | 报告页 | **PARTIAL** | 读链路可达，`task_step_results` 32 支撑内容；但上游 `task_executions` 无终态（FL-08），完成态样本有限 |
| FL-13 | 学生/教师 | 维保作业 | `maintenance` | 准备 → 执行 → 验证（SOP 三段式） | 裁决结果 | **PARTIAL** | 维保页走 `sop.ts`/`sopScripts.ts`/`agent-v2.ts`/`pipeline.ts`；后端 `maintenance` 域 **5 个写操作全✗、7 条路由零前端调用**，`robot_sop_drafts` 空；`fault_cases` 7 行但该域 3 个写操作全✗ |
| FL-14 | 教师/学生 | 机器人控制 | — | — | — | **MISSING** | `BaseRobotAdapter` 10 个抽象方法无任何运动控制；无控制端点；WebSocket 仅单向下发遥测；`adapter` 域 2 个写操作（故障注入）零前端调用 |
| FL-15 | 全部 | 异常停止 | — | — | — | **MISSING** | 急停仅在 `MockRobotAdapter.apply_maintenance_action()` 内，由 `simulation_executor` 按中文关键词「停机／急停」触发；不在适配器抽象契约内；无 HTTP 端点；`incidents` 表空且该域写操作零前端调用 |
| FL-16 | admin | AI 工作台与审批 | `agent/workbench`、`admin/console` | 发起 → 策略评估 → 审批 → 执行 | 审批记录 | **BROKEN** | 两套审批并行（D-01）。函数级事实：可达的 `AdminDashboardPage` **只调用 `/ai/approvals` 的 `listApprovals`（只读）**；`/ai/approvals/{id}/grant|reject` 的唯一调用点是不可达的 `ApprovalQueuePage`；`/agent/approval/*` 的 4 个前端函数**没有任何页面调用**。**`approvals` 与 `approval_records` 两表均空**；`ai_tool_calls`、`conversation_turns`、`decision_records`、`belief_state_records`、`agent_runtime_snapshots` 全空。此外该页的监控与指标卡片调用的 `/agent/monitor/*`、`/agent/metrics*` **后端不存在**（§5.1） |
| FL-17 | 教师/admin/auditor | 审计回放 | 无可用入口 | 记录 → 检索 → 回放 | 回放数据 | **BROKEN** | 后端只有两套回放端点：`/teaching/attempts/{id}/replay`（**前端零调用**，仅后端测试 5）与 `/ai/replay/*`（**无前端**）。前端 `agent-v2.ts` 调用的 `/agent/replay/*` **后端根本不存在**（§5.1 悬空调用）。`replay_checkpoints`/`snapshots`/`timeline_segments` 全空；`audit_events` 仅 3 行，`sop_audit_logs` 空 |
| FL-18 | 运维 | 健康探针 | `admin/console` | — | 健康状态 | **CLOSED**（基础设施，非用户流程） | `/health` 前端✓且有 e2e；`/llm/health` 无消费者 |

## 4.1 数据时间轴（流程是否仍在演进的直接证据）

对全部有 `created_at` 的非空表取最早与最新时间，得到一条清晰的分界：

| 数据簇 | 涉及表 | 最新数据 | 含义 |
|---|---|---|---|
| **教学与训练闭环** | `classes`、`courses`、`enrollments`、`assignments`、`assignment_attempts`、`training_sessions`、`training_submissions`、`session_step_records`、`student_weak_steps`、`guidance_policies`、`user_roles` | **全部停在 2026-05-14** | 三个半月没有任何新增 |
| SOP 与任务链路 | `sops`、`sop_steps`、`tasks`、`task_executions`、`task_step_results` | 2026-08-21 | 仍在演进（与 SOP 三段式改造时间吻合） |
| 机器人与资产 | `robot_models`、`robot_assets`、`robot_projects`、`analysis_tasks`、`evidence_links` | 2026-08-05 | 近期活跃 |
| 认证 | `access_tokens`、`refresh_tokens` | 2026-08-25 | 持续有人登录 |
| 知识 | `knowledge_documents` | 2026-05-16 | 三个月未动，与 27/30 停在 PENDING 一致 |

**批量写入特征：** 17 条 `training_sessions` 全部创建于同一分钟（2026-05-14 14:45）；
`classes`/`enrollments`/`assignments` 也集中在 2026-05-13 18:03 与 2026-05-14 14:45 两个分钟内。
这符合脚本一次性写入，不符合用户逐次操作，与 §5 中这些流程「无前端写入口」的结论互相印证。

**这条时间轴解释了 §4 的分布：** 教学闭环是 5 月的一次性 demo 建设，此后产品重心转向 SOP／任务／维保链路，
教学侧的写入口因此始终没有补齐。这是**产品演进路径的事实记录，不是对优先级的评价**——
是否补齐由 A6 改造计划决定。

## 5. 写操作前端覆盖率（表 1 附表）

判断「流程能否由用户发起」的直接指标。94 条写操作路由中 **51 条有前端入口、43 条没有**。

> **口径声明：** 这里的「有前端入口」= 前端源码中存在该 (动词, 路径) 的调用点，**不保证该调用点位于可达页面**。
> 已知例外两处：`/agent/approval/{id}/approve|reject` 的前端函数没有任何页面调用；
> `/ai/approvals/{id}/grant|reject` 的唯一调用点是不可达的 `ApprovalQueuePage`。
> 即真实可用的写入口**少于 51 条**，函数级逐条核验留给 A3。

| 域 | 写操作 | 有前端入口 | 无入口 | 影响的流程 |
|---|---:|---:|---:|---|
| training | 7 | **0** | 7 | FL-09 训练会话生命周期 |
| assessments | 6 | **0** | 6 | FL-11 外部评估 |
| teaching_roster | 9 | 3 | 6 | FL-03、FL-04、FL-08（建班/选课/作业/证据卡） |
| maintenance | 5 | **0** | 5 | FL-13 维保草稿 |
| agent_governance | 7 | 3 | 4 | FL-16 |
| skills | 3 | **0** | 3 | FL-16 技能注册 |
| fault_cases | 3 | **0** | 3 | FL-13 故障案例 |
| adapter | 2 | **0** | 2 | FL-14、FL-15 |
| admin | 1 | **0** | 1 | 用户角色变更 |
| incidents | 1 | **0** | 1 | FL-15 |
| observations | 1 | **0** | 1 | FL-10 |
| evidence | 1 | **0** | 1 | FL-10 |
| teaching（guidance-policies） | 1 | **0** | 1 | FL-08 |
| agent | 4 | 3 | 1 | FL-16 |
| training_workbench | 5 | 4 | 1 | FL-09 |
| auth、robots、sops、tasks、onboarding、pipeline、agent_knowledge、agent_v2、agent_evidence、ai_assistant、approvals | — | 全部有入口 | 0 | FL-01/02/05/06/07/08/16 |

**11 个域完全没有写入口：** `admin`、`skills`、`adapter`、`fault_cases`、`incidents`、`observations`、
`evidence`、`assessments`、`teaching`、`training`、`maintenance`。

### 5.1 悬空调用：前端调用后端不存在的端点

把前端全部 HTTP 调用点（122 条）反向对照后端 185 条运行时路由，发现 **15 条调用指向后端不存在的路径**
（后端源码检索同样零命中）：

| 分组 | 条数 | 调用点 | 影响的界面 |
|---|---:|---|---|
| `/agent/monitor/alerts|health|metrics|metrics/history` | 4 | `api/adminConsole.ts` | 管理台的 AI 监控卡片 |
| `/agent/metrics`、`/agent/metrics/{}`、`/agent/metrics/record|report|reset` | 5 | `api/agent-v2.ts` | 管理台的指标面板 |
| `/agent/replay/decision/record`、`/agent/replay/decision/{}`、`/agent/replay/recalculate`、`/agent/replay/trace` | 4 | `api/agent-v2.ts` | Agent 决策回放 |
| **`POST /auth/change-password`、`PATCH /auth/profile`** | 2 | `pages/UserSettingsPage.tsx` | **用户设置页的「修改密码」与「修改资料」** |

前 13 条集中在管理台的 AI 治理面板，意味着 `admin/console` 上的监控、指标与回放区域全部是死调用；
后 2 条是**任何登录用户都能点到的功能**，点击必然失败。

复现：

```bash
# 后端零命中
grep -rn "agent/monitor\|agent/metrics\|agent/replay\|auth/change-password\|auth/profile" \
    r-mos-backend/app/api/v1/endpoints/*.py    # 输出 0 行
```

> 这类问题 A1 无法发现——A1 是从后端路由出发找消费者，方向是「后端 → 前端」；
> 悬空调用只有反向对照「前端 → 后端」才会暴露。两个方向都要做，缺一不可。

## 6. 流程断点（表 2）

| Break_ID | Flow_ID | 步骤 | 失败方式 | 影响 | 根因候选 |
|---|---|---|---|---|---|
| **BR-01** | FL-03 | 教师建班/建课 | `POST /classes`、`POST /courses` 无 UI 入口 | 教师无法自助开课，交付现场必须由工程介入建数据 | 前端只封装了读接口 |
| **BR-02** | FL-04 | 学生加入班级 | `POST /enrollments` 无 UI 入口 | 学生名册无法自助维护 | 同上 |
| **BR-03** | FL-08 | 布置作业 | `POST /assignments` 无 UI 入口 | 教学循环无法自主发起 | 同上 |
| **BR-04** | FL-09 | 训练会话生命周期 | 7 个会话级写操作全部无 UI 入口 | 学生无法在 UI 上开始或提交训练会话；现有 16 条已提交会话全部由脚本生成 | 工作台改为步骤级交互后，会话级接口未接入 |
| **BR-05** | FL-08 | 任务执行终态 | `tasks` 域无完成接口；`task_executions` 11 行全 `in_progress` | 任务闭环从未结束，报告与评分的上游数据不完整 | 完成动作可能在 `pipeline` 域，两域职责未收口 |
| **BR-06** | FL-06 | 知识切块 | 3 行 APPROVED，`ai_knowledge_chunks` 仍为空 | 知识检索无底料，AI 引用无法落到真实知识 | 批准后未触发切块，或切块未接入审批回调 |
| **BR-07** | FL-16 | 审批写操作 | `/ai/approvals` 侧唯一操作页不可达；两张审批表全空 | AI 高风险动作缺少可执行的人工闸门 | 页面未挂路由；两套审批实现未收口 |
| **BR-08** | FL-13 | 维保后端域 | 5 个写操作零前端调用，`robot_sop_drafts` 空 | 后端维保草稿能力未被任何界面使用 | 维保页改走 SOP/Agent 链路后原域未清理 |
| **BR-09** | FL-10 | 证据写入 | `POST /evidence_cards`、`POST /evidence-bundles` 无前端；两张卡表空 | 证据模型分裂，其中一套从未产生数据 | 两代证据模型并存未收口 |
| **BR-10** | FL-11 | 外部评估 | `assessments` 域 6 个写操作全无入口，三张表全空 | 多元评估能力完全未接入 | 能力先于场景建设 |
| **BR-11** | FL-05 | 机器人项目 | `robot_projects` 3 行全停在 `UPLOADED` | 项目文件上传后无后续状态流转 | 后续状态机未实现或未触发 |
| **BR-12** | FL-14/15 | 控制与急停 | 系统层面不存在 | 两条最低流程无法演示，也无法对真机做安全承诺 | 适配器契约只覆盖只读与故障注入 |
| **BR-13** | 全局 | 用户角色变更 | `POST /admin/users/{id}/role` 无前端入口 | 管理员无法在 UI 上调整角色；`auditor` 角色因此永远没有账号 | 管理台只实现了用户列表读取 |
| **BR-14** | FL-16、FL-17、全局 | 前端悬空调用 | 15 条前端调用指向后端不存在的端点 | 管理台 AI 监控/指标/回放面板全部失效；**用户设置页的改密码与改资料对所有用户必然失败** | 前后端接口约定漂移，无契约校验 |

## 7. 重复与孤立链路（表 3）

| ID | 链路 A | 链路 B | 重复的数据/状态 | 消费方 | 决策输入 |
|---|---|---|---|---|---|
| **D-01** | `/agent/approval/*`（agent_governance，后端测试 10） | `/ai/approvals/*`（approvals，后端测试 0） | `approval_records` vs `approvals`，两表均空 | **A：前端有函数定义但零页面调用**；**B：可达页面只用其只读 `listApprovals`，写操作唯一调用点是不可达的 `ApprovalQueuePage`** | 二选一收口。A 有测试无消费者，B 有可达只读消费者但写操作不可达——**两套都没有可用的审批闸门** |
| **D-02** | `/teaching/attempts/{id}/replay`（前端零调用，后端测试 5） | `/ai/replay/*`（无前端调用） | 回放语义与检查点 | 两套后端实现均无消费者、无数据；前端另有一套指向**不存在端点**的 `/agent/replay/*` 调用 | 回放实际是「两套后端 + 一套悬空前端」，需整体收口 |
| **D-03** | `evidence_bundles` + `evidence_links`（各 6 行） | `evidence_cards` + `evidence_items`（空） | 证据实体 | A 被教学证据页读取；B 无消费者 | 证据模型收口 |
| **D-04** | `users.role` 列（13 行全有值） | `roles`(4) + `user_roles`(11) 表 | 用户角色 | 后端授权散落使用两者 | 角色单一事实源；2 个用户只在 `users.role` 里有角色 |
| **D-05** | `src/api/client.ts` 的 `apiClient`（统一拦截、重试、令牌刷新） | `src/store/authStore.ts` 自建 axios 实例 | 认证请求通道 | 全站 vs 仅认证 | 认证走独立通道，拦截器策略不共享 |
| **D-06** | `UniversalRobotViewer` 现行 3D 栈 | 旧 `Viewer3D` 栈 9 个文件（不可达） | 3D 渲染 | 仅 A 可达 | A1-F-04 已登记，A3 决定删除边界 |
| **D-07** | `r-mos-backend/main.py`（真实入口） | `r-mos-backend/app/main.py`（仅一个 e2e 测试引用） | 应用装配 | uvicorn/Docker/脚本均用 A | A1 C-10 已登记 |

**孤立功能（A1 已登记，A2 确认不属于任何可发起的用户流程）：** `assessments` 11 条、`adapter` 5 条、
`fault_cases` 5 条、`incidents` 3 条、`observations` 3 条、`evidence` 3 条、`ai_commands` 2 条、`llm_health` 1 条，
共 **33 条路由**；前端 `ApprovalQueuePage` 1 个页面。其中 `adapter`、`incidents` 分别对应 FL-14、FL-15 两条
MISSING 流程——**能力雏形在，但既无接口暴露也无界面消费**。

## 8. A1 功能 → 流程映射覆盖（退出门禁）

| A1 功能域 | 映射流程 |
|---|---|
| auth | FL-02 |
| schools、onboarding | FL-01、FL-05 |
| admin | FL-01（角色变更无入口，见 BR-13） |
| teaching_roster（21 条） | FL-03（classes/courses）、FL-04（enrollments）、FL-08（assignments/attempts）、FL-10（evidence/evidence_cards）、FL-11（grade/diagnosis）、FL-17（replay） |
| teaching（guidance-policies） | FL-08 |
| robots、students | FL-05、FL-11 |
| agent_knowledge | FL-06 |
| sops | FL-07 |
| tasks、student_tasks、scenarios | FL-08 |
| training、training_workbench | FL-09、FL-11 |
| evidence、observations | FL-10（observations 为孤立） |
| assessments | FL-11（孤立） |
| maintenance、fault_cases | FL-13（fault_cases 为孤立） |
| adapter、websocket | FL-14（adapter 为孤立；websocket 仅遥测只读） |
| incidents | FL-15（孤立） |
| agent、agent_v2、agent_governance、agent_evidence、ai_assistant、ai_commands、approvals、skills、pipeline | FL-16 |
| audit | FL-17 |
| health、llm_health、main | FL-18（基础设施） |
| 前端 F-FE-01~26 | 逐条落入 FL-01~FL-17，见 §4 入口列 |
| 前端 F-FE-27 `ApprovalQueuePage` | FL-16，**明确标记为孤立功能（无路由、不可达）** |

**36 个后端域与 27 个前端入口全部映射到至少一条流程或被明确标记为孤立，无遗漏。**

| 门禁 | 要求 | 本报告 | 结论 |
|---|---|---|---|
| A2-G1 | A1 所有面向用户功能映射到至少一条流程或标记孤立 | §8 全覆盖 | ✅ 达标 |
| A2-G2 | 关键流程断点全部登记 | 14 条 BR | ✅ 达标 |
| A2-G3 | 重复链路全部登记 | 7 组 D | ✅ 达标 |
| A2-G4 | 每条流程记录入口、角色、前置数据、关键状态、成功输出、失败路径、跨模块依赖与当前证据 | §4 表 1 + §5 附表 | ✅ 达标 |
| A2-G5 | 不得把「代码存在」写成「真实可用」 | 每条流程同时以「写操作有无 UI 入口」和「数据库有无数据」双重判定；验证等级上限 E1 | ✅ 达标 |
| §5.8 | 主审与复核异源 | Codex 13 条断言复核完成，3 条 MISMATCH 全部复验采纳并修正 | ✅ 达标 |

## 9. 异源复核记录

| 项 | 内容 |
|---|---|
| 复核方 | Codex（工作目录设在被审仓库之外，授网络访问，明令只读；复核后 `git status` 确认被审工作区零改动） |
| 复核范围 | 13 条流程事实断言（B-01~B-13） |
| 结论 | **OVERALL: MISMATCH(3)** — 9 条 AGREE、1 条 AGREE_WITH_CAVEAT、**3 条 MISMATCH** |
| 处置 | 3 条全部由主审复验，**全部成立，全部采纳**；其中 2 条是主审把事实说反 |

### 9.1 MISMATCH 处置

| ID | Codex 主张 | 主审复验 | 处置 |
|---|---|---|---|
| **MISMATCH-A2-01**（B-01） | 现有班级/作业不能归因于 `seed_teaching_demo.py`：库中带该脚本标记 `metadata->>'source'='教学演示脚本'` 的班级为 0，标题为 `示例作业` 的作业也为 0 | 复验属实。进一步查 `classes.metadata` 实际值为 `{"seed":"acceptance_users"}`×2 与 `{"seed":"demo_full"}`×1——**数据确由种子脚本生成，但是另外两个脚本**。Codex 否定我的具体归因是对的；它进一步推出的「没有证据支持是脚本预置」则被 `seed` 标记直接推翻 | **采纳并加强**：SEEDED_ONLY 判定保留，归因改为有直接标记的 `seed_acceptance_users` 与 `seed_demo_full`；`enrollments`/`assignments`/`training_sessions` 无标记列，降级为「推断，非直接证据」 |
| **MISMATCH-A2-02**（B-06） | 可达的 `AdminDashboardPage` 实际调用的是 `/ai/approvals`，**没有**调用 `/agent/approval/*`；后者的 4 个前端函数没有任何页面调用 | 复验属实：该页只 `import { listApprovals } from '@/api/approvals'`；全前端检索 `getPendingApprovals|getApprovalHistory|approveRequest|rejectRequest` 在页面侧零命中。**主审把两套审批的消费方向完全说反了**。根因是文件级可达闭包——`agent-v2.ts` 在该页闭包内，其全部调用点被误算为「该页在用」 | **采纳**。FL-16 与 D-01 已重写：A 侧有测试无消费者，B 侧只有只读消费者、写操作不可达，**两套都没有可用的审批闸门**（比原结论更坏） |
| **MISMATCH-A2-03**（B-10） | `/agent/replay/*` **后端不存在**——源码与 185 条运行时路由中均无此端点，它只是前端的调用定义 | 复验属实：后端仅 `ai_commands.py` 的 `/ai/replay/*` 与 `teaching_roster` 的 `/teaching/attempts/{id}/replay`；`grep -rn "agent/replay" r-mos-backend/app/api/v1/endpoints/` 零命中。**主审把前端的悬空调用当成了一套已存在的回放实现** | **采纳，并由此展开新发现**：反向对照全部 122 条前端调用点后，共查出 **15 条悬空调用**（§5.1），其中包含用户设置页的改密码与改资料。FL-17 由 PARTIAL 下调为 **BROKEN**，新增 BR-14 |

### 9.2 方法教训

三条 MISMATCH 中有两条同源：**可达闭包是文件级而非函数级**，导致「页面引用了某个 API 文件」被误当成「页面在用该文件里的所有接口」。
§2.2 已把该局限列为方法局限第 1 条，§5 的写操作覆盖率也据此加了口径声明。

MISMATCH-A2-03 还暴露了一个**方向性盲区**：A1 与 A2 前半程都只做「后端路由 → 找前端消费者」，
这个方向永远看不见「前端调用了不存在的后端端点」。补上反向对照后立即查出 15 条。
**两个方向都必须做**，已写入 §5.1 与移交项。

## 10. 移交下阶段的问题

| 移交项 | 承接阶段 | 说明 |
|---|---|---|
| 43 条无 UI 入口的写操作：补前端、删后端、还是保留为 API 能力 | A6 | 这是本阶段最大的一笔账，涉及 11 个域 |
| 15 条悬空调用：补后端、删前端、还是标记未完成 | A6 | 其中改密码/改资料是用户可见功能，优先级由董事会定 |
| 前后端接口契约校验（OpenAPI 对拍） | A3、A5 | 悬空调用能长期存在说明缺少契约门禁 |
| 7 组重复链路的收口决策 | A3 | 审批 ×2、回放 ×3、证据 ×2、角色 ×2 |
| 角色两套存储与 2 个无 `user_roles` 的用户 | A3、A4 | 授权判定实际读哪一套 |
| 33 条孤立路由的保留/删除边界 | A3 | 需先逐条人工重验（字符串匹配可能假阴性） |
| FL-14/FL-15 控制与急停缺失 | A4 | 安全与控制的实际能力边界；对真机承诺的影响 |
| 审批闸门形同虚设（BR-07） | A4 | AI 高风险动作的人工审批是安全门禁的一环 |
| `task_executions` 无终态（BR-05） | A5 | 需执行期证据定位是前端未调用还是后端未写 |
| A1 路径级判定的动词级修正 | A1 修订 | 待 A2 获确认后出 A1 0.1.1 |

## 11. 本批产出物

| 文件 | 说明 |
|---|---|
| 本报告 | A2 主报告 |
| [A2 流程链路证据](./evidence/2026-08-27-a2-flow-linkage-v0.1.0.md) | 页面→调用点→路由→表的链路数据、动词级对接结果、写操作覆盖率、数据库状态分布 |
