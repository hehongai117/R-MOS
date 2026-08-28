# A4 安全证据

- 版本：0.1.0
- 日期：2026-08-28
- 状态：In Review
- 被审基线：`B-ASIS = 29d2a5889e3b320a3e777e3d8c19efbbe31c0294`
- 对应报告：[A4 安全、控制与实时通道审计报告](../2026-08-28-a4-security-control-and-realtime-audit-report-v0.1.1.md)

## 1. 提取方法

1. **认证边界**：读 `main.py` 路由注册、`app/core/public_routes.py`、`app/services/authz_guard.py`。
2. **绕过检查**：枚举全部 `include_router` 调用，确认每个嵌套 router 的挂载父级。
3. **授权画像**：AST 遍历每个端点函数的 `Depends(...)`，提取守卫名与 `require_permission("key")` 参数；
   正则识别对象归属校验、角色判定、`school_*` 过滤。
4. **角色权限**：只读查询 `permissions`／`roles`／`role_permissions`。
5. **未做**：没有发起任何越权请求。结论是「代码中不存在检查」，不是「已实证可利用」。

## 2. 画像定义

| 画像 | 判定条件 | 含义 |
|---|---|---|
| PUBLIC | 在 `PUBLIC_ROUTES` 白名单内 | 匿名可访问 |
| WS_NO_AUTH | WebSocket 路由 | 在默认拒绝网关之外，无任何令牌校验 |
| AUTH_ONLY | 端点依赖中无 `get_current_actor`／`require_permission` | 网关保证已认证，但**端点拿不到身份**，无法做对象级授权 |
| ACTOR | 有 `get_current_actor`，无 `require_permission`，无归属校验 | 能拿到身份，代码未用于对象隔离 |
| ACTOR+OWNER | 有身份且有归属校验 | 对象级隔离成立 |
| PERM | 有 `require_permission(key)` | 权限受控（按 RBAC 表判定角色） |

## 3. RBAC 映射（数据库实况）

| 角色 | 权限键 |
|---|---|
| `admin` | `agent:execute`、`agent:read`、`approvals:grant`、`approvals:read`、`approvals:reject`、`assignment_attempts:read`、`audit_events:read`、`skills:publish`、`skills:write`、`teaching:read`、`users:read`、`users:write` |
| `auditor` | `approvals:grant`、`approvals:read`、`approvals:reject`、`audit_events:read` |
| `student` | `agent:read`、`assignment_attempts:read`、`teaching:read` |
| `teacher` | `agent:execute`、`agent:read`、`assignment_attempts:read`、`teaching:read` |

**`auditor` 拥有 `approvals:grant` 与 `approvals:reject`** —— 审计角色具备审批处置权，违反职责分离。

## 4. 逐条身份与对象矩阵（187 行）

> **本表为异源复核修正后的版本。** 初版有两处系统性错误：（a）把根路由 `/` 误并入 AUTH_ONLY，
> 未识别网关只作用于 `/api/v1`；（b）归属校验的正则只匹配字面比较，**漏掉了项目自己封装的
> `app/services/ownership.py` 的 `ensure_user_scope()`／`ensure_task_scope()`**，导致归属校验被低报为 13 条（实为 26 条）。

| # | 方法 | 路径 | 端点文件 | 画像 | 权限键 | 归属校验 | 角色判定 | 学校维度 | 后端测试 |
|---:|---|---|---|---|---|---|---|---|---:|
| 1 | GET | `/docs` | (FastAPI 自带) | ❌ 网关外·匿名可达 | — | — | — | — | — |
| 2 | GET | `/docs/oauth2-redirect` | (FastAPI 自带) | ❌ 网关外·匿名可达 | — | — | — | — | — |
| 3 | GET | `/openapi.json` | (FastAPI 自带) | ❌ 网关外·匿名可达 | — | — | — | — | — |
| 4 | GET | `/redoc` | (FastAPI 自带) | ❌ 网关外·匿名可达 | — | — | — | — | — |
| 5 | DELETE | `/api/v1/adapter/fault/{fault_code}` | adapter | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 6 | GET | `/api/v1/adapter/faults` | adapter | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 7 | GET | `/api/v1/adapter/info` | adapter | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 8 | POST | `/api/v1/adapter/inject-fault` | adapter | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 9 | GET | `/api/v1/adapter/structure` | adapter | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 10 | GET | `/api/v1/admin/users` | admin | 🔒 权限受控 | `users:read` | — | — | — | 2 |
| 11 | POST | `/api/v1/admin/users/{user_id}/role` | admin | 🔒 权限受控 | `users:write` | — | — | — | 2 |
| 12 | POST | `/api/v1/agent/coach/recommend` | agent | 🔒 权限受控 | `agent:execute` | — | — | — | 2 |
| 13 | POST | `/api/v1/agent/coordinate` | agent | 🔒 权限受控 | `agent:execute` | — | — | — | 1 |
| 14 | POST | `/api/v1/agent/diagnoser/diagnose` | agent | 🔒 权限受控 | `agent:execute` | — | — | — | 1 |
| 15 | POST | `/api/v1/agent/execute` | agent | ⚠️ 有身份·无归属 | — | — | — | — | 6 |
| 16 | GET | `/api/v1/agent/task-status/{user_id}` | agent | 🔒 权限受控 | `agent:read` | — | — | — | 2 |
| 17 | GET | `/api/v1/agent/evidence/can-proceed/{step_id}` | agent_evidence | 🔒 权限受控 | `agent:read` | — | — | — | 1 |
| 18 | POST | `/api/v1/agent/evidence/collect` | agent_evidence | 🔒 权限受控 | `agent:execute` | — | — | — | 2 |
| 19 | GET | `/api/v1/agent/evidence/requirements/{action_type}` | agent_evidence | 🔒 权限受控 | `agent:read` | — | — | — | 1 |
| 20 | GET | `/api/v1/agent/evidence/status/{step_id}` | agent_evidence | 🔒 权限受控 | `agent:read` | — | — | — | 1 |
| 21 | GET | `/api/v1/agent/approval/history` | agent_governance | 🔒 权限受控 | `agent:read` | — | — | — | 2 |
| 22 | GET | `/api/v1/agent/approval/pending` | agent_governance | 🔒 权限受控 | `agent:read` | — | — | — | 2 |
| 23 | POST | `/api/v1/agent/approval/request` | agent_governance | 🔒 权限受控 | `agent:execute` | — | — | — | 2 |
| 24 | POST | `/api/v1/agent/approval/{request_id}/approve` | agent_governance | 🔒 权限受控 | `agent:execute` | — | — | — | 3 |
| 25 | POST | `/api/v1/agent/approval/{request_id}/reject` | agent_governance | 🔒 权限受控 | `agent:execute` | — | — | — | 3 |
| 26 | POST | `/api/v1/agent/evaluation/report` | agent_governance | 🔒 权限受控 | `agent:read` | — | — | — | 2 |
| 27 | GET | `/api/v1/agent/preference` | agent_governance | ⚠️ 有身份·无归属 | — | — | — | — | 5 |
| 28 | PUT | `/api/v1/agent/preference/guidance-mode` | agent_governance | ⚠️ 有身份·无归属 | — | — | — | — | 1 |
| 29 | PUT | `/api/v1/agent/preference/llm` | agent_governance | ⚠️ 有身份·无归属 | — | — | — | — | 4 |
| 30 | POST | `/api/v1/agent/sop/quality/check` | agent_governance | 🔒 权限受控 | `agent:execute` | — | — | — | 2 |
| 31 | POST | `/api/v1/agent/knowledge` | agent_knowledge | 🔒 权限受控 | `agent:execute` | — | — | — | 3 |
| 32 | GET | `/api/v1/agent/knowledge/projects` | agent_knowledge | 🔒 权限受控 | `agent:read` | — | — | — | 2 |
| 33 | GET | `/api/v1/agent/knowledge/projects/{project_id}/assets/{asset_path:path}` | agent_knowledge | 🔒 权限受控 | `agent:read` | — | — | — | 2 |
| 34 | GET | `/api/v1/agent/knowledge/projects/{project_id}/manifest` | agent_knowledge | 🔒 权限受控 | `agent:read` | — | — | — | 2 |
| 35 | POST | `/api/v1/agent/knowledge/search` | agent_knowledge | 🔒 权限受控 | `agent:read` | — | — | — | 2 |
| 36 | POST | `/api/v1/agent/knowledge/upload` | agent_knowledge | 🔒 权限受控 | `agent:execute` | — | — | — | 3 |
| 37 | GET | `/api/v1/agent/knowledge/upload/{job_id}` | agent_knowledge | 🔒 权限受控 | `agent:read` | — | — | — | 3 |
| 38 | POST | `/api/v1/agent/knowledge/{entry_id}/approve` | agent_knowledge | 🔒 权限受控 | `agent:execute` | — | — | — | 3 |
| 39 | POST | `/api/v1/agent/knowledge/{entry_id}/submit` | agent_knowledge | 🔒 权限受控 | `agent:execute` | — | — | — | 3 |
| 40 | GET | `/api/v1/agent/v2/idempotency/{idempotency_key}` | agent_v2 | 🔒 权限受控 | `agent:read` | — | — | — | 1 |
| 41 | GET | `/api/v1/agent/v2/modules` | agent_v2 | 🔒 权限受控 | `agent:read` | — | — | — | 1 |
| 42 | POST | `/api/v1/agent/v2/policy/evaluate` | agent_v2 | 🔒 权限受控 | `agent:execute` | — | — | — | 2 |
| 43 | POST | `/api/v1/agent/v2/task/create` | agent_v2 | 🔒 权限受控 | `agent:execute` | — | — | — | 1 |
| 44 | GET | `/api/v1/agent/v2/task/{task_id}` | agent_v2 | 🔒 权限受控 | `agent:read` | — | — | — | 1 |
| 45 | POST | `/api/v1/agent/v2/task/{task_id}/transition` | agent_v2 | 🔒 权限受控 | `agent:execute` | — | — | — | 1 |
| 46 | POST | `/api/v1/agent/v2/trace/{trace_id}/diagnosis-action` | agent_v2 | ⚠️ 有身份·无归属 | — | — | — | — | 2 |
| 47 | GET | `/api/v1/agent/v2/trace/{trace_id}/events` | agent_v2 | 🔒 权限受控 | `agent:read` | — | — | — | 2 |
| 48 | POST | `/api/v1/ai-assistant/chat` | ai_assistant | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 49 | GET | `/api/v1/ai/citations/{ref_id}` | ai_commands | ⚠️ 有身份·无归属 | — | — | — | — | 0 |
| 50 | GET | `/api/v1/ai/replay/metrics/read-tool-success-rate` | ai_commands | 🔒 权限受控 | `audit_events:read` | — | — | — | 0 |
| 51 | GET | `/api/v1/ai/replay/metrics/red-team-pass-rate` | ai_commands | 🔒 权限受控 | `audit_events:read` | — | — | — | 1 |
| 52 | GET | `/api/v1/ai/replay/{trace_id}` | ai_commands | 🔒 权限受控 | `audit_events:read` | — | — | — | 1 |
| 53 | GET | `/api/v1/ai/approvals` | approvals | ✅ 权限+归属 | `approvals:read` | ✅ | — | — | 0 |
| 54 | GET | `/api/v1/ai/approvals/{id}` | approvals | 🔒 权限受控 | `approvals:read` | — | — | — | 0 |
| 55 | POST | `/api/v1/ai/approvals/{id}/grant` | approvals | 🔒 权限受控 | `approvals:grant` | — | — | — | 0 |
| 56 | POST | `/api/v1/ai/approvals/{id}/reject` | approvals | 🔒 权限受控 | `approvals:reject` | — | — | — | 0 |
| 57 | GET | `/api/v1/assessment-providers` | assessments | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 58 | POST | `/api/v1/assessment-providers` | assessments | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 59 | GET | `/api/v1/assessment-providers/{provider_id}` | assessments | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 60 | PATCH | `/api/v1/assessment-providers/{provider_id}` | assessments | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 61 | GET | `/api/v1/assessments` | assessments | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 62 | POST | `/api/v1/assessments` | assessments | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 63 | GET | `/api/v1/assessments/{assessment_id}` | assessments | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 64 | GET | `/api/v1/assessments/{assessment_id}/audit` | assessments | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 65 | POST | `/api/v1/assessments/{assessment_id}/dispute` | assessments | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 66 | POST | `/api/v1/assessments/{assessment_id}/reinstate` | assessments | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 67 | POST | `/api/v1/assessments/{assessment_id}/revoke` | assessments | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 68 | GET | `/api/v1/audit/events` | audit | 🔒 权限受控 | `audit_events:read` | — | — | — | 2 |
| 69 | POST | `/api/v1/auth/login` | auth | ✅ 白名单 | — | — | — | — | 21 |
| 70 | POST | `/api/v1/auth/logout` | auth | ✅ 白名单 | — | — | — | — | 2 |
| 71 | POST | `/api/v1/auth/refresh` | auth | ✅ 白名单 | — | — | — | — | 2 |
| 72 | POST | `/api/v1/auth/register` | auth | ✅ 白名单 | — | — | — | ✅ | 19 |
| 73 | GET | `/api/v1/evidence-bundles` | evidence | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 74 | POST | `/api/v1/evidence-bundles` | evidence | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 75 | GET | `/api/v1/evidence-bundles/{bundle_id}` | evidence | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 76 | GET | `/api/v1/fault-cases` | fault_cases | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 77 | POST | `/api/v1/fault-cases` | fault_cases | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 78 | DELETE | `/api/v1/fault-cases/{fault_case_id}` | fault_cases | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 79 | GET | `/api/v1/fault-cases/{fault_case_id}` | fault_cases | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 80 | PUT | `/api/v1/fault-cases/{fault_case_id}` | fault_cases | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 81 | GET | `/api/v1/health` | health | ✅ 白名单 | — | — | — | — | 3 |
| 82 | GET | `/api/v1/incidents` | incidents | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 83 | POST | `/api/v1/incidents` | incidents | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 84 | GET | `/api/v1/incidents/{incident_id}` | incidents | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 85 | GET | `/api/v1/llm/health` | llm_health | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 86 | GET | `/` | main | ❌ 网关外·匿名可达 | — | — | — | — | 0 |
| 87 | POST | `/api/v1/maintenance/drafts` | maintenance | ⚠️ 仅认证·无隔离 | — | — | — | — | 2 |
| 88 | GET | `/api/v1/maintenance/drafts/{draft_id}` | maintenance | ⚠️ 仅认证·无隔离 | — | — | — | — | 2 |
| 89 | PATCH | `/api/v1/maintenance/drafts/{draft_id}` | maintenance | ⚠️ 仅认证·无隔离 | — | — | — | — | 2 |
| 90 | POST | `/api/v1/maintenance/drafts/{draft_id}/approve` | maintenance | ⚠️ 仅认证·无隔离 | — | — | — | — | 2 |
| 91 | POST | `/api/v1/maintenance/drafts/{draft_id}/reject` | maintenance | ⚠️ 仅认证·无隔离 | — | — | — | — | 2 |
| 92 | POST | `/api/v1/maintenance/drafts/{draft_id}/submit-review` | maintenance | ⚠️ 仅认证·无隔离 | — | — | — | — | 2 |
| 93 | GET | `/api/v1/maintenance/projects/{project_id}/executable-draft` | maintenance | ⚠️ 仅认证·无隔离 | — | — | — | — | 2 |
| 94 | GET | `/api/v1/observations` | observations | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 95 | POST | `/api/v1/observations` | observations | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 96 | GET | `/api/v1/observations/{observation_id}` | observations | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 97 | GET | `/api/v1/onboarding/robots` | onboarding | ⚠️ 有身份·无归属 | — | — | ✅ | — | 0 |
| 98 | POST | `/api/v1/onboarding/robots` | onboarding | ✅ 归属校验 | — | ✅ | ✅ | — | 0 |
| 99 | POST | `/api/v1/pipeline/diagnose` | pipeline | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 100 | POST | `/api/v1/pipeline/executions/{execution_id}/complete` | pipeline | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 101 | POST | `/api/v1/pipeline/executions/{execution_id}/steps/complete` | pipeline | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 102 | POST | `/api/v1/pipeline/tasks/from-diagnosis` | pipeline | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 103 | GET | `/api/v1/robots` | robots | ✅ 归属校验 | — | ✅ | ✅ | — | 1 |
| 104 | POST | `/api/v1/robots` | robots | ⚠️ 有身份·无归属 | — | — | ✅ | — | 1 |
| 105 | GET | `/api/v1/robots/shared` | robots | ✅ 归属校验 | — | ✅ | ✅ | — | 0 |
| 106 | DELETE | `/api/v1/robots/{robot_id}` | robots | ✅ 归属校验 | — | ✅ | ✅ | — | 1 |
| 107 | GET | `/api/v1/robots/{robot_id}` | robots | ✅ 归属校验 | — | ✅ | ✅ | — | 1 |
| 108 | PUT | `/api/v1/robots/{robot_id}` | robots | ✅ 归属校验 | — | ✅ | ✅ | — | 1 |
| 109 | GET | `/api/v1/robots/{robot_id}/analysis-tasks` | robots | ✅ 归属校验 | — | ✅ | ✅ | — | 1 |
| 110 | POST | `/api/v1/robots/{robot_id}/analyze` | robots | ✅ 归属校验 | — | ✅ | ✅ | — | 1 |
| 111 | GET | `/api/v1/robots/{robot_id}/assets` | robots | ⚠️ 有身份·无归属 | — | — | — | — | 1 |
| 112 | GET | `/api/v1/robots/{robot_id}/assets/{file_path:path}` | robots | ⚠️ 有身份·无归属 | — | — | — | — | 1 |
| 113 | DELETE | `/api/v1/robots/{robot_id}/bind` | robots | ✅ 归属校验 | — | ✅ | ✅ | — | 1 |
| 114 | POST | `/api/v1/robots/{robot_id}/bind` | robots | ✅ 归属校验 | — | ✅ | ✅ | — | 1 |
| 115 | PUT | `/api/v1/robots/{robot_id}/publish` | robots | ✅ 归属校验 | — | ✅ | ✅ | — | 1 |
| 116 | GET | `/api/v1/robots/{robot_id}/tools` | robots | ⚠️ 有身份·无归属 | — | — | — | — | 1 |
| 117 | POST | `/api/v1/robots/{robot_id}/upload` | robots | ✅ 归属校验 | — | ✅ | ✅ | — | 1 |
| 118 | PUT | `/api/v1/robots/{robot_id}/visibility` | robots | ✅ 归属校验 | — | ✅ | ✅ | — | 1 |
| 119 | GET | `/api/v1/scenarios` | scenarios | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 120 | GET | `/api/v1/schools` | schools | ✅ 白名单 | — | — | — | — | 3 |
| 121 | GET | `/api/v1/schools/{school_name}/teachers` | schools | ✅ 白名单 | — | — | — | ✅ | 3 |
| 122 | POST | `/api/v1/ai/skills` | skills | 🔒 权限受控 | `skills:write` | — | — | — | 1 |
| 123 | POST | `/api/v1/ai/skills/{id}/publish` | skills | 🔒 权限受控 | `skills:publish` | — | — | — | 1 |
| 124 | POST | `/api/v1/ai/skills/{id}/submit-review` | skills | ✅ 权限+归属 | `skills:write` | ✅ | ✅ | — | 1 |
| 125 | GET | `/api/v1/sops` | sops | ⚠️ 仅认证·无隔离 | — | — | — | — | 1 |
| 126 | POST | `/api/v1/sops` | sops | ⚠️ 仅认证·无隔离 | — | — | — | — | 1 |
| 127 | GET | `/api/v1/sops/adjudication` | sops | ⚠️ 仅认证·无隔离 | — | — | — | — | 1 |
| 128 | DELETE | `/api/v1/sops/{sop_id}` | sops | ⚠️ 仅认证·无隔离 | — | — | — | — | 1 |
| 129 | GET | `/api/v1/sops/{sop_id}` | sops | ⚠️ 仅认证·无隔离 | — | — | — | — | 1 |
| 130 | GET | `/api/v1/sops/{sop_id}/delete-impact` | sops | ⚠️ 仅认证·无隔离 | — | — | — | — | 1 |
| 131 | GET | `/api/v1/student/tasks` | student_tasks | ⚠️ 仅认证·无隔离 | — | — | — | — | 0 |
| 132 | GET | `/api/v1/students/{student_id}/robots` | students | ✅ 归属校验 | — | ✅ | ✅ | — | 6 |
| 133 | GET | `/api/v1/tasks` | tasks | ⚠️ 有身份·无归属 | — | — | — | — | 4 |
| 134 | POST | `/api/v1/tasks` | tasks | ⚠️ 仅认证·无隔离 | — | — | — | — | 4 |
| 135 | GET | `/api/v1/tasks/{task_id}` | tasks | ✅ 归属校验 | — | ✅ | — | — | 4 |
| 136 | GET | `/api/v1/tasks/{task_id}/events` | tasks | ✅ 归属校验 | — | ✅ | — | — | 4 |
| 137 | POST | `/api/v1/tasks/{task_id}/pause` | tasks | ⚠️ 仅认证·无隔离 | — | — | — | — | 4 |
| 138 | GET | `/api/v1/tasks/{task_id}/report` | tasks | ✅ 归属校验 | — | ✅ | — | — | 4 |
| 139 | POST | `/api/v1/tasks/{task_id}/resume` | tasks | ⚠️ 仅认证·无隔离 | — | — | — | — | 4 |
| 140 | POST | `/api/v1/tasks/{task_id}/start` | tasks | ⚠️ 仅认证·无隔离 | — | — | — | — | 4 |
| 141 | POST | `/api/v1/tasks/{task_id}/step` | tasks | ⚠️ 仅认证·无隔离 | — | — | — | — | 4 |
| 142 | GET | `/api/v1/guidance-policies` | teaching | ⚠️ 仅认证·无隔离 | — | — | — | — | 2 |
| 143 | POST | `/api/v1/guidance-policies` | teaching | ⚠️ 仅认证·无隔离 | — | — | — | — | 2 |
| 144 | GET | `/api/v1/guidance-policies/{policy_id}` | teaching | ⚠️ 仅认证·无隔离 | — | — | — | — | 2 |
| 145 | GET | `/api/v1/assignments` | teaching_roster | ⚠️ 仅认证·无隔离 | — | — | — | — | 4 |
| 146 | POST | `/api/v1/assignments` | teaching_roster | ⚠️ 有身份·无归属 | — | — | ✅ | — | 4 |
| 147 | GET | `/api/v1/assignments/{assignment_id}` | teaching_roster | ⚠️ 仅认证·无隔离 | — | — | — | — | 4 |
| 148 | GET | `/api/v1/assignments/{assignment_id}/attempts` | teaching_roster | ⚠️ 仅认证·无隔离 | — | — | — | — | 4 |
| 149 | POST | `/api/v1/assignments/{assignment_id}/attempts` | teaching_roster | ⚠️ 仅认证·无隔离 | — | — | — | — | 4 |
| 150 | GET | `/api/v1/attempts/{attempt_id}` | teaching_roster | ✅ 归属校验 | — | ✅ | ✅ | — | 4 |
| 151 | PATCH | `/api/v1/attempts/{attempt_id}` | teaching_roster | ⚠️ 仅认证·无隔离 | — | — | — | — | 4 |
| 152 | GET | `/api/v1/attempts/{attempt_id}/diagnosis` | teaching_roster | ⚠️ 仅认证·无隔离 | — | — | — | — | 4 |
| 153 | GET | `/api/v1/attempts/{attempt_id}/evidence` | teaching_roster | ⚠️ 仅认证·无隔离 | — | — | — | — | 4 |
| 154 | POST | `/api/v1/attempts/{attempt_id}/grade` | teaching_roster | ⚠️ 仅认证·无隔离 | — | — | — | — | 4 |
| 155 | GET | `/api/v1/classes` | teaching_roster | ⚠️ 仅认证·无隔离 | — | — | — | — | 6 |
| 156 | POST | `/api/v1/classes` | teaching_roster | ⚠️ 仅认证·无隔离 | — | — | — | — | 6 |
| 157 | GET | `/api/v1/classes/{class_id}` | teaching_roster | ✅ 归属校验 | — | ✅ | ✅ | — | 6 |
| 158 | PATCH | `/api/v1/classes/{class_id}` | teaching_roster | ⚠️ 有身份·无归属 | — | — | ✅ | — | 6 |
| 159 | GET | `/api/v1/courses` | teaching_roster | ⚠️ 仅认证·无隔离 | — | — | — | — | 2 |
| 160 | POST | `/api/v1/courses` | teaching_roster | ⚠️ 仅认证·无隔离 | — | — | — | — | 2 |
| 161 | GET | `/api/v1/courses/{course_id}` | teaching_roster | ⚠️ 仅认证·无隔离 | — | — | — | — | 2 |
| 162 | GET | `/api/v1/enrollments` | teaching_roster | ⚠️ 仅认证·无隔离 | — | — | — | — | 5 |
| 163 | POST | `/api/v1/enrollments` | teaching_roster | ⚠️ 仅认证·无隔离 | — | — | — | — | 5 |
| 164 | POST | `/api/v1/evidence_cards` | teaching_roster | ⚠️ 有身份·无归属 | — | — | ✅ | — | 2 |
| 165 | GET | `/api/v1/teaching/attempts/{attempt_id}/replay` | teaching_roster | ⚠️ 有身份·无归属 | — | — | ✅ | — | 5 |
| 166 | GET | `/api/v1/students/{user_id}/profile` | training | ✅ 归属校验 | — | ✅ | — | ✅ | 6 |
| 167 | GET | `/api/v1/students/{user_id}/weak-steps` | training | ✅ 归属校验 | — | ✅ | — | ✅ | 6 |
| 168 | GET | `/api/v1/training/feedback/{session_id}` | training | ✅ 归属校验 | — | ✅ | — | ✅ | 6 |
| 169 | POST | `/api/v1/training/sessions` | training | ⚠️ 仅认证·无隔离 | — | — | — | — | 12 |
| 170 | GET | `/api/v1/training/sessions/{session_id}` | training | ⚠️ 仅认证·无隔离 | — | — | — | — | 12 |
| 171 | PATCH | `/api/v1/training/sessions/{session_id}/abandon` | training | ⚠️ 仅认证·无隔离 | — | — | — | — | 12 |
| 172 | GET | `/api/v1/training/sessions/{session_id}/detail` | training | ✅ 归属校验 | — | ✅ | — | ✅ | 12 |
| 173 | POST | `/api/v1/training/sessions/{session_id}/force-submit` | training | ⚠️ 仅认证·无隔离 | — | — | — | — | 12 |
| 174 | PATCH | `/api/v1/training/sessions/{session_id}/pause` | training | ⚠️ 仅认证·无隔离 | — | — | — | — | 12 |
| 175 | PATCH | `/api/v1/training/sessions/{session_id}/resume` | training | ⚠️ 仅认证·无隔离 | — | — | — | — | 12 |
| 176 | GET | `/api/v1/training/sessions/{session_id}/steps` | training | ⚠️ 仅认证·无隔离 | — | — | — | — | 12 |
| 177 | POST | `/api/v1/training/sessions/{session_id}/steps` | training | ⚠️ 仅认证·无隔离 | — | — | — | — | 12 |
| 178 | POST | `/api/v1/training/sessions/{session_id}/submit` | training | ⚠️ 仅认证·无隔离 | — | — | — | — | 12 |
| 179 | GET | `/api/v1/training/users/{user_id}/active-session` | training | ⚠️ 仅认证·无隔离 | — | — | — | — | 2 |
| 180 | GET | `/api/v1/training/users/{user_id}/sessions` | training | ✅ 归属校验 | — | ✅ | — | ✅ | 2 |
| 181 | POST | `/api/v1/training/projects/generate` | training_workbench | ⚠️ 仅认证·无隔离 | — | — | — | — | 6 |
| 182 | POST | `/api/v1/training/workbench/ask` | training_workbench | ⚠️ 有身份·无归属 | — | — | — | — | 2 |
| 183 | POST | `/api/v1/training/workbench/draft` | training_workbench | ⚠️ 有身份·无归属 | — | — | — | — | 4 |
| 184 | POST | `/api/v1/training/workbench/evidence` | training_workbench | ⚠️ 有身份·无归属 | — | — | — | — | 2 |
| 185 | POST | `/api/v1/training/workbench/sessions/{session_id}/steps/{step_id}/submit` | training_workbench | ⚠️ 有身份·无归属 | — | — | — | — | 2 |
| 186 | WS | `/ws/robot/status` | websocket | ❌ 无认证 | — | — | — | — | — |
| 187 | WS | `/ws/robot/{robot_id}/status` | websocket | ❌ 无认证 | — | — | — | — | — |

### 4.1 画像分布

| 画像 | 条数 |
|---|---:|
| ⚠️ 仅认证·无隔离 | 85 |
| 🔒 权限受控 | 42 |
| ✅ 归属校验 | 24 |
| ⚠️ 有身份·无归属 | 20 |
| ✅ 白名单 | 7 |
| ❌ 网关外·匿名可达 | 5 |
| ✅ 权限+归属 | 2 |
| ❌ 无认证 | 2 |

### 4.2 读写隔离不对称

| | 总数 | 有对象归属校验 | 占比 |
|---|---:|---:|---:|
| 读操作（GET） | 86 | 16 | 18% |
| **写操作** | **94** | **10** | **10%** |

10 条有归属校验的写操作全部在 `robots`／`onboarding`。

### 4.3 无隔离写操作（46 条）

按是否操作既有对象拆分：**带对象 ID 27 条**（明确的跨用户越权面）、**创建型 19 条**（越权面取决于请求体能否指定归属字段，本批记为 UNKNOWN）。

| 方法 | 路径 | 域 | 类型 | 后端测试 |
|---|---|---|---|---:|
| DELETE | `/api/v1/adapter/fault/{fault_code}` | adapter | 带对象ID | 0 |
| POST | `/api/v1/adapter/inject-fault` | adapter | 创建型 | 0 |
| POST | `/api/v1/ai-assistant/chat` | ai_assistant | 创建型 | 0 |
| POST | `/api/v1/assessment-providers` | assessments | 创建型 | 0 |
| PATCH | `/api/v1/assessment-providers/{provider_id}` | assessments | 带对象ID | 0 |
| POST | `/api/v1/assessments` | assessments | 创建型 | 0 |
| POST | `/api/v1/assessments/{assessment_id}/dispute` | assessments | 带对象ID | 0 |
| POST | `/api/v1/assessments/{assessment_id}/reinstate` | assessments | 带对象ID | 0 |
| POST | `/api/v1/assessments/{assessment_id}/revoke` | assessments | 带对象ID | 0 |
| POST | `/api/v1/evidence-bundles` | evidence | 创建型 | 0 |
| POST | `/api/v1/fault-cases` | fault_cases | 创建型 | 0 |
| DELETE | `/api/v1/fault-cases/{fault_case_id}` | fault_cases | 带对象ID | 0 |
| PUT | `/api/v1/fault-cases/{fault_case_id}` | fault_cases | 带对象ID | 0 |
| POST | `/api/v1/incidents` | incidents | 创建型 | 0 |
| POST | `/api/v1/maintenance/drafts` | maintenance | 创建型 | 2 |
| PATCH | `/api/v1/maintenance/drafts/{draft_id}` | maintenance | 带对象ID | 2 |
| POST | `/api/v1/maintenance/drafts/{draft_id}/approve` | maintenance | 带对象ID | 2 |
| POST | `/api/v1/maintenance/drafts/{draft_id}/reject` | maintenance | 带对象ID | 2 |
| POST | `/api/v1/maintenance/drafts/{draft_id}/submit-review` | maintenance | 带对象ID | 2 |
| POST | `/api/v1/observations` | observations | 创建型 | 0 |
| POST | `/api/v1/pipeline/diagnose` | pipeline | 创建型 | 0 |
| POST | `/api/v1/pipeline/executions/{execution_id}/complete` | pipeline | 带对象ID | 0 |
| POST | `/api/v1/pipeline/executions/{execution_id}/steps/complete` | pipeline | 带对象ID | 0 |
| POST | `/api/v1/pipeline/tasks/from-diagnosis` | pipeline | 创建型 | 0 |
| POST | `/api/v1/sops` | sops | 创建型 | 1 |
| DELETE | `/api/v1/sops/{sop_id}` | sops | 带对象ID | 1 |
| POST | `/api/v1/tasks` | tasks | 创建型 | 4 |
| POST | `/api/v1/tasks/{task_id}/pause` | tasks | 带对象ID | 4 |
| POST | `/api/v1/tasks/{task_id}/resume` | tasks | 带对象ID | 4 |
| POST | `/api/v1/tasks/{task_id}/start` | tasks | 带对象ID | 4 |
| POST | `/api/v1/tasks/{task_id}/step` | tasks | 带对象ID | 4 |
| POST | `/api/v1/guidance-policies` | teaching | 创建型 | 2 |
| POST | `/api/v1/assignments/{assignment_id}/attempts` | teaching_roster | 带对象ID | 4 |
| PATCH | `/api/v1/attempts/{attempt_id}` | teaching_roster | 带对象ID | 4 |
| POST | `/api/v1/attempts/{attempt_id}/grade` | teaching_roster | 带对象ID | 4 |
| POST | `/api/v1/classes` | teaching_roster | 创建型 | 6 |
| POST | `/api/v1/courses` | teaching_roster | 创建型 | 2 |
| POST | `/api/v1/enrollments` | teaching_roster | 创建型 | 5 |
| POST | `/api/v1/training/sessions` | training | 创建型 | 12 |
| PATCH | `/api/v1/training/sessions/{session_id}/abandon` | training | 带对象ID | 12 |
| POST | `/api/v1/training/sessions/{session_id}/force-submit` | training | 带对象ID | 12 |
| PATCH | `/api/v1/training/sessions/{session_id}/pause` | training | 带对象ID | 12 |
| PATCH | `/api/v1/training/sessions/{session_id}/resume` | training | 带对象ID | 12 |
| POST | `/api/v1/training/sessions/{session_id}/steps` | training | 带对象ID | 12 |
| POST | `/api/v1/training/sessions/{session_id}/submit` | training | 带对象ID | 12 |
| POST | `/api/v1/training/projects/generate` | training_workbench | 创建型 | 6 |

> **注意最后一列：** 多条端点有通过的后端测试，但**没有一条测试尝试越权访问**——
> 这正是 A4 退出门禁 G3「严重越权不得被测试绿灯掩盖」所指的情形。

### 4.4 归属校验的实现方式

校验通过两条途径实现，初版只识别了第一条：

1. **字面比较**：`actor.user_id != student_id`（`students.py`）、`skill.created_by_user_id == str(actor.user_id)`（`skills.py`）等。
2. **`app/services/ownership.py` 的辅助函数**（初版漏判的部分）：
   - `ensure_user_scope(db, request, actor, target_user_id, ...)`：允许**本人 / 管理员 / 同校教师**，同校判定读 `User.school_name` 比对 `actor.school_name`；
   - `ensure_task_scope(db, request, actor, task, action=...)`：任务对象范围校验。
   调用点：`tasks.py` 3 处、`training.py` 5 处。**学校维度的 7 条中有 5 条来自这条途径。**

## 5. 复现命令

```bash
cd <worktree>/r-mos-backend
# 认证边界
grep -n 'include_router' main.py app/api/v1/__init__.py app/api/v1/endpoints/*.py
cat app/core/public_routes.py
# 授权画像：AST 提取每个端点函数的 Depends 与 require_permission
# RBAC（只读）
psql "$DATABASE_URL" -c "select r.name, p.key from role_permissions rp join roles r on r.id=rp.role_id join permissions p on p.id=rp.permission_id order by 1,2;"
```

## 6. 局限

1. 归属校验用正则识别，可能漏判；「无归属校验」应读作「未在代码中找到归属校验」。
2. **未发起任何越权请求**，结论为静态证据（E1）。代码缺少检查 ≠ 已实证可利用——
   但对无身份参数的写端点而言，实现上已排除做检查的可能。
3. 画像按端点函数聚合，同一函数服务多方法时按最宽口径归类。
