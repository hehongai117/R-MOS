# A2 流程链路证据

- 版本：0.1.0
- 日期：2026-08-27
- 状态：In Review
- 被审基线：`B-ASIS = 29d2a5889e3b320a3e777e3d8c19efbbe31c0294`
- 对应报告：[A2 用户角色与业务闭环审计报告](../2026-08-27-a2-user-roles-and-business-closure-audit-report-v0.1.0.md)

## 1. 链路构建方法

1. **前端可达闭包**：对每个页面组件，用 TypeScript 模块解析（`@/` 别名、相对路径、`index.ts` 兜底、
   `vi.mock`、动态 `import()`）求传递闭包，得到该页面实际能加载到的全部模块。
2. **调用点扫描**：在闭包内的所有模块中扫描 `.get|post|put|patch|delete('<路径>')` 字面量与 `/ws/` 字面量。
   **扫描范围不限 `src/api/`**——认证请求由 `src/store/authStore.ts` 自建的 axios 实例发出，只扫 `src/api/` 会整条漏掉。
3. **动词级对接**：把前端 `${x}` 与后端 `{x}`／`{x:path}` 统一折叠为 `{}`，剥离 `/api/v1` 前缀与开头的 `${API_BASE_URL}`，
   再按 (动词, 归一化路径) 与后端运行时路由表对接。
4. **流程是否跑通**：以数据库真实行数与状态分布判定，不以代码存在判定；行数一律精确 `count(*)`。

## 2. 动词级对接结果

前端调用点字面量 27 个文件、117 条 (动词, 路径) 组合。对 182 条后端路由的对接结果：

| 分类 | 数量 | 含义 |
|---|---:|---|
| 动词级命中 | 94 | 前端确实以该动词调用该路径（A1 路径级口径为 121，差额 27 条全部是 A1 假阳性，反向差额 0） |
| 仅路径命中、该动词无调用 | 5 | 见下表；其中 2 条 WebSocket 无 HTTP 动词，不构成错配 |
| 路径完全无前端调用 | 83 | 含 A1 已登记的 33 条孤立路由 |

### 2.1 被 A1 路径级判定高估的写端点

| 域 | 动词 | 路径 | 后端测试 | A2 动词级事实 |
|---|---|---|---:|---|
| teaching_roster | POST | `/api/v1/classes` | 6 | 前端只有 GET，无该写调用 |
| teaching_roster | POST | `/api/v1/enrollments` | 5 | 前端只有 GET，无该写调用 |
| teaching_roster | POST | `/api/v1/assignments` | 4 | 前端只有 GET，无该写调用 |

这三条正是董事会最低流程里的**教师建班、学生加入、布置作业**。`src/api/teaching.ts` 全部调用如下
（复现：`grep -nE "apiClient\.(get|post|put|patch|delete)" src/api/teaching.ts`）：

```
GET   /classes                              GET   /attempts/{id}
GET   /enrollments                          PATCH /attempts/{id}
GET   /assignments                          POST  /attempts/{id}/grade
GET   /assignments/{id}                     GET   /attempts/{id}/evidence
GET   /assignments/{id}/attempts            GET   /attempts/{id}/diagnosis
POST  /assignments/{id}/attempts
```

全前端源码（排除测试）中检索 `createClass|createEnrollment|createAssignment` 命中 **0**。

## 2A. 写操作前端覆盖率（A2 的核心指标）

「流程能否由用户发起」的直接指标：**94 条写操作路由（POST/PUT/PATCH/DELETE），
51 条有前端入口，43 条没有**。

| 域 | 写操作 | 有前端入口 | 无入口 |
|---|---:|---:|---:|
| `training` | 7 | 0 | **7** |
| `assessments` | 6 | 0 | **6** |
| `teaching_roster` | 9 | 3 | **6** |
| `maintenance` | 5 | 0 | **5** |
| `agent_governance` | 7 | 3 | **4** |
| `fault_cases` | 3 | 0 | **3** |
| `skills` | 3 | 0 | **3** |
| `adapter` | 2 | 0 | **2** |
| `admin` | 1 | 0 | **1** |
| `agent` | 4 | 3 | **1** |
| `evidence` | 1 | 0 | **1** |
| `incidents` | 1 | 0 | **1** |
| `observations` | 1 | 0 | **1** |
| `teaching` | 1 | 0 | **1** |
| `training_workbench` | 5 | 4 | **1** |
| `agent_evidence` | 1 | 1 | 0 |
| `agent_knowledge` | 5 | 5 | 0 |
| `agent_v2` | 4 | 4 | 0 |
| `ai_assistant` | 1 | 1 | 0 |
| `approvals` | 2 | 2 | 0 |
| `auth` | 4 | 4 | 0 |
| `onboarding` | 1 | 1 | 0 |
| `pipeline` | 4 | 4 | 0 |
| `robots` | 9 | 9 | 0 |
| `sops` | 2 | 2 | 0 |
| `tasks` | 5 | 5 | 0 |

**完全没有写入口的 11 个域：** `adapter`、`admin`、`assessments`、`evidence`、`fault_cases`、`incidents`、`maintenance`、`observations`、`skills`、`teaching`、`training`。

### 2A.1 有前端入口的 51 条写操作（全量）

| 域 | 动词 | 路径 |
|---|---|---|
| agent | POST | `/api/v1/agent/coach/recommend` |
| agent | POST | `/api/v1/agent/diagnoser/diagnose` |
| agent | POST | `/api/v1/agent/execute` |
| agent_evidence | POST | `/api/v1/agent/evidence/collect` |
| agent_governance | POST | `/api/v1/agent/approval/{request_id}/approve` |
| agent_governance | POST | `/api/v1/agent/approval/{request_id}/reject` |
| agent_governance | PUT | `/api/v1/agent/preference/llm` |
| agent_knowledge | POST | `/api/v1/agent/knowledge` |
| agent_knowledge | POST | `/api/v1/agent/knowledge/search` |
| agent_knowledge | POST | `/api/v1/agent/knowledge/upload` |
| agent_knowledge | POST | `/api/v1/agent/knowledge/{entry_id}/approve` |
| agent_knowledge | POST | `/api/v1/agent/knowledge/{entry_id}/submit` |
| agent_v2 | POST | `/api/v1/agent/v2/policy/evaluate` |
| agent_v2 | POST | `/api/v1/agent/v2/task/create` |
| agent_v2 | POST | `/api/v1/agent/v2/task/{task_id}/transition` |
| agent_v2 | POST | `/api/v1/agent/v2/trace/{trace_id}/diagnosis-action` |
| ai_assistant | POST | `/api/v1/ai-assistant/chat` |
| approvals | POST | `/api/v1/ai/approvals/{id}/grant` |
| approvals | POST | `/api/v1/ai/approvals/{id}/reject` |
| auth | POST | `/api/v1/auth/login` |
| auth | POST | `/api/v1/auth/logout` |
| auth | POST | `/api/v1/auth/refresh` |
| auth | POST | `/api/v1/auth/register` |
| onboarding | POST | `/api/v1/onboarding/robots` |
| pipeline | POST | `/api/v1/pipeline/diagnose` |
| pipeline | POST | `/api/v1/pipeline/executions/{execution_id}/complete` |
| pipeline | POST | `/api/v1/pipeline/executions/{execution_id}/steps/complete` |
| pipeline | POST | `/api/v1/pipeline/tasks/from-diagnosis` |
| robots | POST | `/api/v1/robots` |
| robots | PUT | `/api/v1/robots/{robot_id}` |
| robots | DELETE | `/api/v1/robots/{robot_id}` |
| robots | POST | `/api/v1/robots/{robot_id}/analyze` |
| robots | POST | `/api/v1/robots/{robot_id}/bind` |
| robots | DELETE | `/api/v1/robots/{robot_id}/bind` |
| robots | PUT | `/api/v1/robots/{robot_id}/publish` |
| robots | POST | `/api/v1/robots/{robot_id}/upload` |
| robots | PUT | `/api/v1/robots/{robot_id}/visibility` |
| sops | POST | `/api/v1/sops` |
| sops | DELETE | `/api/v1/sops/{sop_id}` |
| tasks | POST | `/api/v1/tasks` |
| tasks | POST | `/api/v1/tasks/{task_id}/pause` |
| tasks | POST | `/api/v1/tasks/{task_id}/resume` |
| tasks | POST | `/api/v1/tasks/{task_id}/start` |
| tasks | POST | `/api/v1/tasks/{task_id}/step` |
| teaching_roster | POST | `/api/v1/assignments/{assignment_id}/attempts` |
| teaching_roster | PATCH | `/api/v1/attempts/{attempt_id}` |
| teaching_roster | POST | `/api/v1/attempts/{attempt_id}/grade` |
| training_workbench | POST | `/api/v1/training/workbench/ask` |
| training_workbench | POST | `/api/v1/training/workbench/draft` |
| training_workbench | POST | `/api/v1/training/workbench/evidence` |
| training_workbench | POST | `/api/v1/training/workbench/sessions/{session_id}/steps/{step_id}/submit` |

## 2B. 悬空调用：前端 → 后端反向对照

把前端全部 122 条 HTTP 调用点反向对照后端 185 条运行时路由，得到**前端调用了但后端不存在**的集合。
后端源码检索同样零命中，排除了「路由存在但未注册」的可能。

| 动词 | 路径 | 调用点 |
|---|---|---|
| GET | `/agent/metrics` | `api/agent-v2.ts` |
| POST | `/agent/metrics/record` | `api/agent-v2.ts` |
| POST | `/agent/metrics/report` | `api/agent-v2.ts` |
| POST | `/agent/metrics/reset` | `api/agent-v2.ts` |
| GET | `/agent/metrics/{}` | `api/agent-v2.ts` |
| GET | `/agent/monitor/alerts` | `api/adminConsole.ts` |
| GET | `/agent/monitor/health` | `api/adminConsole.ts` |
| GET | `/agent/monitor/metrics` | `api/adminConsole.ts` |
| GET | `/agent/monitor/metrics/history` | `api/adminConsole.ts` |
| POST | `/agent/replay/decision/record` | `api/agent-v2.ts` |
| GET | `/agent/replay/decision/{}` | `api/agent-v2.ts` |
| POST | `/agent/replay/recalculate` | `api/agent-v2.ts` |
| POST | `/agent/replay/trace` | `api/agent-v2.ts` |
| POST | `/auth/change-password` | `pages/UserSettingsPage.tsx` |
| PATCH | `/auth/profile` | `pages/UserSettingsPage.tsx` |

**合计 15 条。** 复现：

```bash
grep -rn "agent/monitor\|agent/metrics\|agent/replay\|auth/change-password\|auth/profile" \
    r-mos-backend/app/api/v1/endpoints/*.py     # 零命中
```

> **方向性教训：** A1 与 A2 前半程都只做「后端路由 → 找前端消费者」，这个方向永远看不见悬空调用。
> 补上反向对照后立即查出 15 条，其中 `POST /auth/change-password` 与 `PATCH /auth/profile`
> 是用户设置页里任何登录用户都能点到的功能。两个方向都必须做。

## 2C. 审批与回放的函数级事实（异源复核修正）

主审初版按**文件级**可达闭包判定，把 `AdminDashboardPage` 闭包内 `agent-v2.ts` 的全部调用点都算作「该页在用」，
由此把两套审批的消费方向说反。函数级复核结果：

| 事实 | 证据命令 |
|---|---|
| `AdminDashboardPage` 只 `import { listApprovals } from '@/api/approvals'`（只读） | `grep -n "approval" src/pages/admin/AdminDashboardPage.tsx` |
| `/agent/approval/*` 的 4 个前端函数无任何页面调用 | `grep -rn "getPendingApprovals\|getApprovalHistory\|approveRequest\|rejectRequest" src --include='*.tsx'` 零命中 |
| `/ai/approvals/{id}/grant\|reject` 唯一调用点是不可达的 `ApprovalQueuePage` | 见 A1 对象登记附录 FE-MOD |
| 后端只有 `/ai/replay/*` 与 `/teaching/attempts/{id}/replay` 两套回放 | `grep -rn "replay" r-mos-backend/app/api/v1/endpoints/*.py` |
## 3. 页面 → 后端调用规模

每个页面经传递闭包可达的后端调用数（含经 `authStore` 带入的认证调用）：

| 页面 | 可达调用数 |
|---|---:|
| `pages/SOPMaintenancePage.tsx` | 47 |
| `teaching/pages/TeachingAttemptPage.tsx` | 45 |
| `pages/admin/AdminDashboardPage.tsx` | 37 |
| `pages/KnowledgePage.tsx` | 35 |
| `pages/SOPListPage.tsx` | 34 |
| `pages/agent/AgentWorkbenchPage.tsx` | 33 |
| `teaching/pages/TeacherMonitorPage.tsx` | 29 |
| `teaching/pages/TeacherStudentsPage.tsx` | 27 |
| `teaching/pages/TeachingAssignmentsPage.tsx` | 26 |
| `pages/MonitorPage.tsx` | 24 |
| `pages/Atom01DemoPage.tsx` | 22 |
| `pages/ScenarioPickerPage.tsx` | 22 |
| `pages/DashboardPage.tsx` | 22 |
| `pages/SharedRobotsPage.tsx` | 21 |
| `teaching/pages/TeachingDiagnosisPage.tsx` | 18 |
| `teaching/pages/TeachingEvidencePage.tsx` | 18 |
| `pages/StudentSkillsPage.tsx` | 17 |
| `pages/ReportListPage.tsx` | 15 |
| `pages/ReportPage.tsx` | 15 |
| `pages/UserSettingsPage.tsx` | 11 |
| `pages/admin/ApprovalQueuePage.tsx` | 11 |
| `pages/RegisterPage.tsx` | 9 |
| `pages/OnboardingRobotsPage.tsx` | 9 |
| `pages/MyTasksPage.tsx` | 8 |
| `pages/sopMaintenance/SOPViewerScene.tsx` | 7 |
| `pages/sopMaintenance/SOPMaintenancePanels.tsx` | 7 |
| `pages/LoginPage.tsx` | 5 |

## 4. 数据库状态分布（流程是否跑通的直接证据）

| 表 | 行数 | 状态分布 | 对应流程 |
|---|---:|---|---|
| `tasks` | 30 | in_progress=13 / pending=10 / completed=6 / cancelled=1 | FL-08 |
| `task_executions` | 11 | **全部 in_progress=11**，无终态 | FL-08 |
| `training_sessions` | 17 | submitted=16 / active=1 | FL-09 |
| `assignment_attempts` | 9 | completed=6 / in_progress=2 / abandoned=1 | FL-11 |
| `analysis_tasks` | 9 | completed=8 / running=1（类型 full=6 / sop_generate=2 / cad_parse=1） | FL-05 |
| `robot_models` | 13 | ready=9 / draft=4 | FL-05 |
| `knowledge_documents` | 30 | **PENDING=27 / APPROVED=3** | FL-06 |
| `robot_projects` | 3 | **全部 UPLOADED=3** | FL-05 |
| `users` | 13 | student=8 / teacher=4 / admin=1（`users.role` 列） | FL-01 |

### 4.1 与流程直接相关的空表

| 空表 | 含义 |
|---|---|
| `approvals` | `/ai/approvals/*` 链路从未产生数据 |
| `approval_records` | `/agent/approval/*` 链路从未产生数据 |
| `ai_knowledge_chunks` | 知识文档批准后没有切块产物，检索无底料 |
| `evidence_cards` | 证据模型 B 从未产生数据 |
| `evidence_items` | 同上 |
| `incidents` | 异常事件从未产生数据 |
| `observations` | 观测从未产生数据 |
| `commands` | 指令表从未产生数据 |
| `ai_tool_calls` | AI 工具调用从未落库 |
| `conversation_turns` | 会话轮次从未落库 |
| `decision_records` | 决策记录从未落库 |
| `belief_state_records` | 信念状态从未落库 |
| `agent_runtime_snapshots` | Agent 运行时快照从未落库 |
| `replay_checkpoints` | 回放检查点从未产生 |
| `snapshots` | 快照从未产生 |
| `timeline_segments` | 时间线分段从未产生 |
| `sop_audit_logs` | SOP 审计日志从未产生 |
| `robot_sop_drafts` | 维保 SOP 草稿从未产生 |
| `assessment_providers` | 评估提供方未配置 |
| `external_assessments` | 外部评估从未产生 |
| `skills` | 技能注册表为空 |
| `skill_releases` | 技能发布为空 |
| `skill_reviews` | 技能评审为空 |

完整 65 张表的精确行数见 [A1 对象登记附录 §2](./2026-08-26-a1-object-register-v0.1.0.md)。

## 4A. 数据时间轴

对全部含 `created_at` 的非空表取最早与最新时间。复现：

```sql
select min(created_at), max(created_at), count(*) from public."<表>";
```

| 表 | 行数 | 最早 | 最新 |
|---|---:|---|---|
| `access_tokens` | 389 | 2026-05-13 | 2026-08-25 |
| `refresh_tokens` | 389 | 2026-05-13 | 2026-08-25 |
| `sop_steps` | 719 | 2026-05-13 | 2026-08-21 |
| `sops` | 54 | 2026-05-13 | 2026-08-21 |
| `task_executions` | 11 | 2026-05-18 | 2026-08-21 |
| `task_step_results` | 32 | 2026-08-21 | 2026-08-21 |
| `tasks` | 30 | 2026-05-14 | 2026-08-21 |
| `analysis_tasks` | 9 | 2026-05-15 | 2026-08-05 |
| `evidence_links` | 6 | 2026-05-19 | 2026-08-05 |
| `robot_assets` | 33367 | 2026-05-15 | 2026-08-05 |
| `robot_models` | 13 | 2026-05-13 | 2026-08-05 |
| `robot_project_files` | 91 | 2026-08-05 | 2026-08-05 |
| `robot_projects` | 3 | 2026-08-05 | 2026-08-05 |
| `teacher_robot_bindings` | 7 | 2026-05-14 | 2026-08-05 |
| `fault_sop_mappings` | 6 | 2026-05-18 | 2026-07-23 |
| `student_skill_profiles` | 8 | 2026-05-14 | 2026-07-02 |
| `users` | 13 | 2026-05-13 | 2026-07-02 |
| `knowledge_documents` | 30 | 2026-05-14 | 2026-05-16 |
| `assignment_attempts` | 9 | 2026-05-14 | 2026-05-14 |
| `assignments` | 2 | 2026-05-14 | 2026-05-14 |
| `classes` | 3 | 2026-05-13 | 2026-05-14 |
| `courses` | 3 | 2026-05-13 | 2026-05-14 |
| `enrollments` | 7 | 2026-05-13 | 2026-05-14 |
| `fault_cases` | 7 | 2026-05-13 | 2026-05-14 |
| `guidance_policies` | 1 | 2026-05-14 | 2026-05-14 |
| `schools` | 2869 | 2026-05-14 | 2026-05-14 |
| `session_step_records` | 107 | 2026-05-14 | 2026-05-14 |
| `student_weak_steps` | 4 | 2026-05-14 | 2026-05-14 |
| `training_sessions` | 17 | 2026-05-14 | 2026-05-14 |
| `training_submissions` | 16 | 2026-05-14 | 2026-05-14 |
| `user_preferences` | 9 | 2026-05-13 | 2026-05-14 |
| `user_roles` | 11 | 2026-05-13 | 2026-05-14 |
| `audit_events` | 3 | 2026-05-13 | 2026-05-13 |
| `permissions` | 12 | 2026-05-13 | 2026-05-13 |
| `role_permissions` | 23 | 2026-05-13 | 2026-05-13 |
| `roles` | 4 | 2026-05-13 | 2026-05-13 |

**分界非常清晰：** 教学与训练闭环的全部表（`classes`、`courses`、`enrollments`、`assignments`、
`assignment_attempts`、`training_sessions`、`training_submissions`、`session_step_records`、
`student_weak_steps`、`guidance_policies`、`user_roles`）**最新数据全部停在 2026-05-14**；
SOP／任务链路更新至 2026-08-21，机器人资产至 2026-08-05，认证令牌至 2026-08-25。

**批量写入特征：** 17 条 `training_sessions` 创建于同一分钟（2026-05-14 14:45）；
`classes`/`enrollments`/`assignments` 集中在 2026-05-13 18:03 与 2026-05-14 14:45 两个分钟内。
符合脚本一次性写入，不符合用户逐次操作。
## 5. 控制与急停的能力边界

```bash
grep -n 'abstractmethod' -A2 r-mos-backend/app/adapters/base.py    # 10 个抽象方法
grep -rniE 'estop|emergency_stop|急停' r-mos-backend/app
```

`BaseRobotAdapter` 的 10 个抽象方法：`connect`、`disconnect`、`is_connected`、`get_robot_info`、
`get_robot_structure`、`get_joint_states`、`get_sensor_data`、`inject_fault`、`clear_fault`、`get_active_faults`。
**全部是连接、读取与故障注入，没有任何运动控制或停止方法。**

急停的全部实现：`MockRobotAdapter.apply_maintenance_action()` 中 `action_type == "emergency_stop"` 分支
（`app/adapters/mock.py:455`），由 `app/services/simulation/simulation_executor.py:86` 按动作描述里的
中文关键词「停机」或「急停」触发。该方法**不在 `BaseRobotAdapter` 抽象契约内**，也没有任何 HTTP 端点暴露。

## 6. 方法局限

1. 调用点扫描只识别**字符串字面量**路径。若某处用变量拼出完整路径，本批会漏判。
2. 页面可达闭包是**静态**的，包含条件分支下可能永不执行的调用；「可达」不等于「一定会调用」。
3. 数据库是本机开发库快照。表为空证明「在本库从未产生过数据」，不证明功能在其他环境不可用。
4. 本批未执行测试、未启动长驻服务、未连真机，验证等级上限 E1。
