# A1 对象登记附录（逐条枚举）

- 版本：0.1.0
- 日期：2026-08-26
- 状态：Ready for Board Review（随 A1 主报告一并提交）
- 被审基线：`29d2a5889e3b320a3e777e3d8c19efbbe31c0294`
- 生成方式：机械生成，禁止手工编辑；口径、复现命令与方法局限见 [双源枚举差集证据](./2026-08-26-a1-dual-source-diff-v0.1.0.md)。

本附录只登记对象与证据指向，不下达可用性结论。`UNUSED` = 本批口径下未找到消费者或测试引用，
依据是路由路径字符串匹配，对动态拼接路径可能漏判，逐条复核前不得作为删除依据。
前端调用者只计入**构建图可达**的文件；不可达文件里的调用单独计列。

## 1. 后端路由（BE-RT）

| ID | 域 | 方法 | 路径 | 后端测试 | 前端调用 | e2e | 实现状态 | 验证等级 |
|---|---|---|---|---:|---:|---:|---|---|
| BE-RT-001 | adapter | DELETE | `/api/v1/adapter/fault/{fault_code}` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-002 | adapter | GET | `/api/v1/adapter/faults` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-003 | adapter | GET | `/api/v1/adapter/info` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-004 | adapter | POST | `/api/v1/adapter/inject-fault` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-005 | adapter | GET | `/api/v1/adapter/structure` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-006 | admin | GET | `/api/v1/admin/users` | 2 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-007 | admin | POST | `/api/v1/admin/users/{user_id}/role` | 2 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-008 | agent | POST | `/api/v1/agent/coach/recommend` | 2 | 2 | 0 | IMPLEMENTED | E1 |
| BE-RT-009 | agent | POST | `/api/v1/agent/coordinate` | 1 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-010 | agent | POST | `/api/v1/agent/diagnoser/diagnose` | 1 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-011 | agent | POST | `/api/v1/agent/execute` | 6 | 2 | 0 | IMPLEMENTED | E1 |
| BE-RT-012 | agent | GET | `/api/v1/agent/task-status/{user_id}` | 2 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-013 | agent_evidence | GET | `/api/v1/agent/evidence/can-proceed/{step_id}` | 1 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-014 | agent_evidence | POST | `/api/v1/agent/evidence/collect` | 2 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-015 | agent_evidence | GET | `/api/v1/agent/evidence/requirements/{action_type}` | 1 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-016 | agent_evidence | GET | `/api/v1/agent/evidence/status/{step_id}` | 1 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-017 | agent_governance | GET | `/api/v1/agent/approval/history` | 2 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-018 | agent_governance | GET | `/api/v1/agent/approval/pending` | 2 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-019 | agent_governance | POST | `/api/v1/agent/approval/request` | 2 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-020 | agent_governance | POST | `/api/v1/agent/approval/{request_id}/approve` | 3 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-021 | agent_governance | POST | `/api/v1/agent/approval/{request_id}/reject` | 3 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-022 | agent_governance | POST | `/api/v1/agent/evaluation/report` | 2 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-023 | agent_governance | GET | `/api/v1/agent/preference` | 5 | 2 | 1 | IMPLEMENTED | E1 |
| BE-RT-024 | agent_governance | PUT | `/api/v1/agent/preference/guidance-mode` | 1 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-025 | agent_governance | PUT | `/api/v1/agent/preference/llm` | 4 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-026 | agent_governance | POST | `/api/v1/agent/sop/quality/check` | 2 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-027 | agent_knowledge | POST | `/api/v1/agent/knowledge` | 3 | 3 | 0 | IMPLEMENTED | E1 |
| BE-RT-028 | agent_knowledge | GET | `/api/v1/agent/knowledge/projects` | 2 | 2 | 0 | IMPLEMENTED | E1 |
| BE-RT-029 | agent_knowledge | GET | `/api/v1/agent/knowledge/projects/{project_id}/assets/{asset_path:path}` | 2 | 2 | 0 | IMPLEMENTED | E1 |
| BE-RT-030 | agent_knowledge | GET | `/api/v1/agent/knowledge/projects/{project_id}/manifest` | 2 | 2 | 0 | IMPLEMENTED | E1 |
| BE-RT-031 | agent_knowledge | POST | `/api/v1/agent/knowledge/search` | 2 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-032 | agent_knowledge | POST | `/api/v1/agent/knowledge/upload` | 3 | 2 | 0 | IMPLEMENTED | E1 |
| BE-RT-033 | agent_knowledge | GET | `/api/v1/agent/knowledge/upload/{job_id}` | 3 | 2 | 0 | IMPLEMENTED | E1 |
| BE-RT-034 | agent_knowledge | POST | `/api/v1/agent/knowledge/{entry_id}/approve` | 3 | 3 | 0 | IMPLEMENTED | E1 |
| BE-RT-035 | agent_knowledge | POST | `/api/v1/agent/knowledge/{entry_id}/submit` | 3 | 3 | 0 | IMPLEMENTED | E1 |
| BE-RT-036 | agent_v2 | GET | `/api/v1/agent/v2/idempotency/{idempotency_key}` | 1 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-037 | agent_v2 | GET | `/api/v1/agent/v2/modules` | 1 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-038 | agent_v2 | POST | `/api/v1/agent/v2/policy/evaluate` | 2 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-039 | agent_v2 | POST | `/api/v1/agent/v2/task/create` | 1 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-040 | agent_v2 | GET | `/api/v1/agent/v2/task/{task_id}` | 1 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-041 | agent_v2 | POST | `/api/v1/agent/v2/task/{task_id}/transition` | 1 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-042 | agent_v2 | POST | `/api/v1/agent/v2/trace/{trace_id}/diagnosis-action` | 2 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-043 | agent_v2 | GET | `/api/v1/agent/v2/trace/{trace_id}/events` | 2 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-044 | ai_assistant | POST | `/api/v1/ai-assistant/chat` | 0 | 2 | 0 | IMPLEMENTED | NOT_VERIFIED |
| BE-RT-045 | ai_commands | GET | `/api/v1/ai/citations/{ref_id}` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-046 | ai_commands | GET | `/api/v1/ai/replay/metrics/read-tool-success-rate` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-047 | ai_commands | GET | `/api/v1/ai/replay/metrics/red-team-pass-rate` | 1 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-048 | ai_commands | GET | `/api/v1/ai/replay/{trace_id}` | 1 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-049 | approvals | GET | `/api/v1/ai/approvals` | 0 | 1 | 0 | IMPLEMENTED | NOT_VERIFIED |
| BE-RT-050 | approvals | GET | `/api/v1/ai/approvals/{id}` | 0 | 1 | 0 | IMPLEMENTED | NOT_VERIFIED |
| BE-RT-051 | approvals | POST | `/api/v1/ai/approvals/{id}/grant` | 0 | 1 | 0 | IMPLEMENTED | NOT_VERIFIED |
| BE-RT-052 | approvals | POST | `/api/v1/ai/approvals/{id}/reject` | 0 | 1 | 0 | IMPLEMENTED | NOT_VERIFIED |
| BE-RT-053 | assessments | GET | `/api/v1/assessment-providers` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-054 | assessments | POST | `/api/v1/assessment-providers` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-055 | assessments | GET | `/api/v1/assessment-providers/{provider_id}` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-056 | assessments | PATCH | `/api/v1/assessment-providers/{provider_id}` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-057 | assessments | GET | `/api/v1/assessments` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-058 | assessments | POST | `/api/v1/assessments` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-059 | assessments | GET | `/api/v1/assessments/{assessment_id}` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-060 | assessments | GET | `/api/v1/assessments/{assessment_id}/audit` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-061 | assessments | POST | `/api/v1/assessments/{assessment_id}/dispute` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-062 | assessments | POST | `/api/v1/assessments/{assessment_id}/reinstate` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-063 | assessments | POST | `/api/v1/assessments/{assessment_id}/revoke` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-064 | audit | GET | `/api/v1/audit/events` | 2 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-065 | auth | POST | `/api/v1/auth/login` | 21 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-066 | auth | POST | `/api/v1/auth/logout` | 2 | 2 | 0 | IMPLEMENTED | E1 |
| BE-RT-067 | auth | POST | `/api/v1/auth/refresh` | 2 | 2 | 0 | IMPLEMENTED | E1 |
| BE-RT-068 | auth | POST | `/api/v1/auth/register` | 19 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-069 | evidence | GET | `/api/v1/evidence-bundles` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-070 | evidence | POST | `/api/v1/evidence-bundles` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-071 | evidence | GET | `/api/v1/evidence-bundles/{bundle_id}` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-072 | fault_cases | GET | `/api/v1/fault-cases` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-073 | fault_cases | POST | `/api/v1/fault-cases` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-074 | fault_cases | DELETE | `/api/v1/fault-cases/{fault_case_id}` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-075 | fault_cases | GET | `/api/v1/fault-cases/{fault_case_id}` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-076 | fault_cases | PUT | `/api/v1/fault-cases/{fault_case_id}` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-077 | health | GET | `/api/v1/health` | 3 | 1 | 1 | IMPLEMENTED | E1 |
| BE-RT-078 | incidents | GET | `/api/v1/incidents` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-079 | incidents | POST | `/api/v1/incidents` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-080 | incidents | GET | `/api/v1/incidents/{incident_id}` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-081 | llm_health | GET | `/api/v1/llm/health` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-082 | main | GET | `/` *(框架根路由，不做路径匹配)* | 0 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-083 | maintenance | POST | `/api/v1/maintenance/drafts` | 2 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-084 | maintenance | GET | `/api/v1/maintenance/drafts/{draft_id}` | 2 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-085 | maintenance | PATCH | `/api/v1/maintenance/drafts/{draft_id}` | 2 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-086 | maintenance | POST | `/api/v1/maintenance/drafts/{draft_id}/approve` | 2 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-087 | maintenance | POST | `/api/v1/maintenance/drafts/{draft_id}/reject` | 2 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-088 | maintenance | POST | `/api/v1/maintenance/drafts/{draft_id}/submit-review` | 2 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-089 | maintenance | GET | `/api/v1/maintenance/projects/{project_id}/executable-draft` | 2 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-090 | observations | GET | `/api/v1/observations` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-091 | observations | POST | `/api/v1/observations` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-092 | observations | GET | `/api/v1/observations/{observation_id}` | 0 | 0 | 0 | UNUSED | NOT_VERIFIED |
| BE-RT-093 | onboarding | GET | `/api/v1/onboarding/robots` | 0 | 2 | 1 | IMPLEMENTED | E1 |
| BE-RT-094 | onboarding | POST | `/api/v1/onboarding/robots` | 0 | 2 | 1 | IMPLEMENTED | E1 |
| BE-RT-095 | pipeline | POST | `/api/v1/pipeline/diagnose` | 0 | 1 | 0 | IMPLEMENTED | NOT_VERIFIED |
| BE-RT-096 | pipeline | POST | `/api/v1/pipeline/executions/{execution_id}/complete` | 0 | 1 | 1 | IMPLEMENTED | E1 |
| BE-RT-097 | pipeline | POST | `/api/v1/pipeline/executions/{execution_id}/steps/complete` | 0 | 1 | 1 | IMPLEMENTED | E1 |
| BE-RT-098 | pipeline | POST | `/api/v1/pipeline/tasks/from-diagnosis` | 0 | 1 | 1 | IMPLEMENTED | E1 |
| BE-RT-099 | robots | GET | `/api/v1/robots` | 1 | 19 | 2 | IMPLEMENTED | E1 |
| BE-RT-100 | robots | POST | `/api/v1/robots` | 1 | 19 | 2 | IMPLEMENTED | E1 |
| BE-RT-101 | robots | GET | `/api/v1/robots/shared` | 0 | 1 | 0 | IMPLEMENTED | NOT_VERIFIED |
| BE-RT-102 | robots | DELETE | `/api/v1/robots/{robot_id}` | 1 | 19 | 2 | IMPLEMENTED | E1 |
| BE-RT-103 | robots | GET | `/api/v1/robots/{robot_id}` | 1 | 19 | 2 | IMPLEMENTED | E1 |
| BE-RT-104 | robots | PUT | `/api/v1/robots/{robot_id}` | 1 | 19 | 2 | IMPLEMENTED | E1 |
| BE-RT-105 | robots | GET | `/api/v1/robots/{robot_id}/analysis-tasks` | 1 | 19 | 2 | IMPLEMENTED | E1 |
| BE-RT-106 | robots | POST | `/api/v1/robots/{robot_id}/analyze` | 1 | 19 | 2 | IMPLEMENTED | E1 |
| BE-RT-107 | robots | GET | `/api/v1/robots/{robot_id}/assets` | 1 | 19 | 2 | IMPLEMENTED | E1 |
| BE-RT-108 | robots | GET | `/api/v1/robots/{robot_id}/assets/{file_path:path}` | 1 | 19 | 2 | IMPLEMENTED | E1 |
| BE-RT-109 | robots | DELETE | `/api/v1/robots/{robot_id}/bind` | 1 | 19 | 2 | IMPLEMENTED | E1 |
| BE-RT-110 | robots | POST | `/api/v1/robots/{robot_id}/bind` | 1 | 19 | 2 | IMPLEMENTED | E1 |
| BE-RT-111 | robots | PUT | `/api/v1/robots/{robot_id}/publish` | 1 | 19 | 2 | IMPLEMENTED | E1 |
| BE-RT-112 | robots | GET | `/api/v1/robots/{robot_id}/tools` | 1 | 19 | 2 | IMPLEMENTED | E1 |
| BE-RT-113 | robots | POST | `/api/v1/robots/{robot_id}/upload` | 1 | 19 | 2 | IMPLEMENTED | E1 |
| BE-RT-114 | robots | PUT | `/api/v1/robots/{robot_id}/visibility` | 1 | 19 | 2 | IMPLEMENTED | E1 |
| BE-RT-115 | scenarios | GET | `/api/v1/scenarios` | 0 | 4 | 1 | IMPLEMENTED | E1 |
| BE-RT-116 | schools | GET | `/api/v1/schools` | 3 | 2 | 0 | IMPLEMENTED | E1 |
| BE-RT-117 | schools | GET | `/api/v1/schools/{school_name}/teachers` | 3 | 2 | 0 | IMPLEMENTED | E1 |
| BE-RT-118 | skills | POST | `/api/v1/ai/skills` | 1 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-119 | skills | POST | `/api/v1/ai/skills/{id}/publish` | 1 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-120 | skills | POST | `/api/v1/ai/skills/{id}/submit-review` | 1 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-121 | sops | GET | `/api/v1/sops` | 1 | 4 | 3 | IMPLEMENTED | E1 |
| BE-RT-122 | sops | POST | `/api/v1/sops` | 1 | 4 | 3 | IMPLEMENTED | E1 |
| BE-RT-123 | sops | GET | `/api/v1/sops/adjudication` | 1 | 1 | 2 | IMPLEMENTED | E1 |
| BE-RT-124 | sops | DELETE | `/api/v1/sops/{sop_id}` | 1 | 4 | 3 | IMPLEMENTED | E1 |
| BE-RT-125 | sops | GET | `/api/v1/sops/{sop_id}` | 1 | 4 | 3 | IMPLEMENTED | E1 |
| BE-RT-126 | sops | GET | `/api/v1/sops/{sop_id}/delete-impact` | 1 | 4 | 3 | IMPLEMENTED | E1 |
| BE-RT-127 | student_tasks | GET | `/api/v1/student/tasks` | 0 | 2 | 0 | IMPLEMENTED | NOT_VERIFIED |
| BE-RT-128 | students | GET | `/api/v1/students/{student_id}/robots` | 6 | 5 | 0 | IMPLEMENTED | E1 |
| BE-RT-129 | tasks | GET | `/api/v1/tasks` | 4 | 4 | 1 | IMPLEMENTED | E1 |
| BE-RT-130 | tasks | POST | `/api/v1/tasks` | 4 | 4 | 1 | IMPLEMENTED | E1 |
| BE-RT-131 | tasks | GET | `/api/v1/tasks/{task_id}` | 4 | 4 | 1 | IMPLEMENTED | E1 |
| BE-RT-132 | tasks | GET | `/api/v1/tasks/{task_id}/events` | 4 | 4 | 1 | IMPLEMENTED | E1 |
| BE-RT-133 | tasks | POST | `/api/v1/tasks/{task_id}/pause` | 4 | 4 | 1 | IMPLEMENTED | E1 |
| BE-RT-134 | tasks | GET | `/api/v1/tasks/{task_id}/report` | 4 | 4 | 1 | IMPLEMENTED | E1 |
| BE-RT-135 | tasks | POST | `/api/v1/tasks/{task_id}/resume` | 4 | 4 | 1 | IMPLEMENTED | E1 |
| BE-RT-136 | tasks | POST | `/api/v1/tasks/{task_id}/start` | 4 | 4 | 1 | IMPLEMENTED | E1 |
| BE-RT-137 | tasks | POST | `/api/v1/tasks/{task_id}/step` | 4 | 4 | 1 | IMPLEMENTED | E1 |
| BE-RT-138 | teaching | GET | `/api/v1/guidance-policies` | 2 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-139 | teaching | POST | `/api/v1/guidance-policies` | 2 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-140 | teaching | GET | `/api/v1/guidance-policies/{policy_id}` | 2 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-141 | teaching_roster | GET | `/api/v1/assignments` | 4 | 6 | 0 | IMPLEMENTED | E1 |
| BE-RT-142 | teaching_roster | POST | `/api/v1/assignments` | 4 | 6 | 0 | IMPLEMENTED | E1 |
| BE-RT-143 | teaching_roster | GET | `/api/v1/assignments/{assignment_id}` | 4 | 6 | 0 | IMPLEMENTED | E1 |
| BE-RT-144 | teaching_roster | GET | `/api/v1/assignments/{assignment_id}/attempts` | 4 | 6 | 0 | IMPLEMENTED | E1 |
| BE-RT-145 | teaching_roster | POST | `/api/v1/assignments/{assignment_id}/attempts` | 4 | 6 | 0 | IMPLEMENTED | E1 |
| BE-RT-146 | teaching_roster | GET | `/api/v1/attempts/{attempt_id}` | 4 | 8 | 0 | IMPLEMENTED | E1 |
| BE-RT-147 | teaching_roster | PATCH | `/api/v1/attempts/{attempt_id}` | 4 | 8 | 0 | IMPLEMENTED | E1 |
| BE-RT-148 | teaching_roster | GET | `/api/v1/attempts/{attempt_id}/diagnosis` | 4 | 8 | 0 | IMPLEMENTED | E1 |
| BE-RT-149 | teaching_roster | GET | `/api/v1/attempts/{attempt_id}/evidence` | 4 | 8 | 0 | IMPLEMENTED | E1 |
| BE-RT-150 | teaching_roster | POST | `/api/v1/attempts/{attempt_id}/grade` | 4 | 8 | 0 | IMPLEMENTED | E1 |
| BE-RT-151 | teaching_roster | GET | `/api/v1/classes` | 6 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-152 | teaching_roster | POST | `/api/v1/classes` | 6 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-153 | teaching_roster | GET | `/api/v1/classes/{class_id}` | 6 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-154 | teaching_roster | PATCH | `/api/v1/classes/{class_id}` | 6 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-155 | teaching_roster | GET | `/api/v1/courses` | 2 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-156 | teaching_roster | POST | `/api/v1/courses` | 2 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-157 | teaching_roster | GET | `/api/v1/courses/{course_id}` | 2 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-158 | teaching_roster | GET | `/api/v1/enrollments` | 5 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-159 | teaching_roster | POST | `/api/v1/enrollments` | 5 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-160 | teaching_roster | POST | `/api/v1/evidence_cards` | 2 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-161 | teaching_roster | GET | `/api/v1/teaching/attempts/{attempt_id}/replay` | 5 | 5 | 0 | IMPLEMENTED | E1 |
| BE-RT-162 | training | GET | `/api/v1/students/{user_id}/profile` | 6 | 5 | 0 | IMPLEMENTED | E1 |
| BE-RT-163 | training | GET | `/api/v1/students/{user_id}/weak-steps` | 6 | 5 | 0 | IMPLEMENTED | E1 |
| BE-RT-164 | training | GET | `/api/v1/training/feedback/{session_id}` | 6 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-165 | training | POST | `/api/v1/training/sessions` | 12 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-166 | training | GET | `/api/v1/training/sessions/{session_id}` | 12 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-167 | training | PATCH | `/api/v1/training/sessions/{session_id}/abandon` | 12 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-168 | training | GET | `/api/v1/training/sessions/{session_id}/detail` | 12 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-169 | training | POST | `/api/v1/training/sessions/{session_id}/force-submit` | 12 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-170 | training | PATCH | `/api/v1/training/sessions/{session_id}/pause` | 12 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-171 | training | PATCH | `/api/v1/training/sessions/{session_id}/resume` | 12 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-172 | training | GET | `/api/v1/training/sessions/{session_id}/steps` | 12 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-173 | training | POST | `/api/v1/training/sessions/{session_id}/steps` | 12 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-174 | training | POST | `/api/v1/training/sessions/{session_id}/submit` | 12 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-175 | training | GET | `/api/v1/training/users/{user_id}/active-session` | 2 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-176 | training | GET | `/api/v1/training/users/{user_id}/sessions` | 2 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-177 | training_workbench | POST | `/api/v1/training/projects/generate` | 6 | 0 | 0 | IMPLEMENTED | E1 |
| BE-RT-178 | training_workbench | POST | `/api/v1/training/workbench/ask` | 2 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-179 | training_workbench | POST | `/api/v1/training/workbench/draft` | 4 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-180 | training_workbench | POST | `/api/v1/training/workbench/evidence` | 2 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-181 | training_workbench | POST | `/api/v1/training/workbench/sessions/{session_id}/steps/{step_id}/submit` | 2 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-182 | websocket | WS | `/ws/robot/status` | 1 | 1 | 0 | IMPLEMENTED | E1 |
| BE-RT-183 | websocket | WS | `/ws/robot/{robot_id}/status` | 1 | 1 | 0 | IMPLEMENTED | E1 |

合计 183 条（181 HTTP + 2 WebSocket）：IMPLEMENTED 150、UNUSED 33；E1 142、NOT_VERIFIED 41。

## 2. 数据表（DB-TB）

**行数一律为精确 `count(*)`。** 初版误用 `pg_stat_user_tables.n_live_tup`（统计估算值），
在未 ANALYZE 的库上停留在陈旧快照，导致「58 张空表」的错误结论；异源复核精确计数后实为 **28 张空表**，
两种口径在 35 张表上不一致。估算值已从本审计的结论口径中移除。

| ID | 表名 | 源码定义文件 | 精确行数 |
|---|---|---|---:|
| DB-TB-001 | `access_tokens` | `app/models/access_token.py` | 389 |
| DB-TB-002 | `agent_runtime_snapshots` | `app/models/agent_runtime.py` | 0 |
| DB-TB-003 | `ai_knowledge_chunks` | `app/models/knowledge_chunk.py` | 0 |
| DB-TB-004 | `ai_tool_calls` | `app/models/command_runtime.py` | 0 |
| DB-TB-005 | `alignment_map` | `app/models/timeline.py` | 0 |
| DB-TB-006 | `analysis_tasks` | `app/models/analysis_task.py` | 9 |
| DB-TB-007 | `approval_records` | `app/models/agent_runtime.py` | 0 |
| DB-TB-008 | `approvals` | `app/models/approval.py` | 0 |
| DB-TB-009 | `assessment_audit_events` | `app/models/assessment.py` | 0 |
| DB-TB-010 | `assessment_providers` | `app/models/assessment.py` | 0 |
| DB-TB-011 | `assignment_attempts` | `app/models/teaching.py` | 9 |
| DB-TB-012 | `assignments` | `app/models/teaching.py` | 2 |
| DB-TB-013 | `audit_events` | `app/models/audit_event.py` | 3 |
| DB-TB-014 | `belief_state_records` | `app/models/agent_runtime.py` | 0 |
| DB-TB-015 | `classes` | `app/models/teaching.py` | 3 |
| DB-TB-016 | `commands` | `app/models/command_runtime.py` | 0 |
| DB-TB-017 | `conversation_turns` | `app/models/conversation.py` | 0 |
| DB-TB-018 | `courses` | `app/models/teaching.py` | 3 |
| DB-TB-019 | `decision_records` | `app/models/agent_runtime.py` | 0 |
| DB-TB-020 | `enrollments` | `app/models/teaching.py` | 7 |
| DB-TB-021 | `events` | `app/models/event.py` | 0 |
| DB-TB-022 | `evidence_bundles` | `app/models/evidence.py` | 6 |
| DB-TB-023 | `evidence_cards` | `app/models/timeline.py` | 0 |
| DB-TB-024 | `evidence_items` | `app/models/evidence.py` | 0 |
| DB-TB-025 | `evidence_links` | `app/models/teaching.py` | 6 |
| DB-TB-026 | `external_assessments` | `app/models/assessment.py` | 0 |
| DB-TB-027 | `fault_cases` | `app/models/fault.py` | 7 |
| DB-TB-028 | `fault_sop_mappings` | `app/models/fault_sop_mapping.py` | 6 |
| DB-TB-029 | `guidance_policies` | `app/models/teaching.py` | 1 |
| DB-TB-030 | `incidents` | `app/models/incident.py` | 0 |
| DB-TB-031 | `knowledge_documents` | `app/models/knowledge_document.py` | 30 |
| DB-TB-032 | `multimodal_timelines` | `app/models/timeline.py` | 0 |
| DB-TB-033 | `observations` | `app/models/observation.py` | 0 |
| DB-TB-034 | `permissions` | `app/models/rbac.py` | 12 |
| DB-TB-035 | `refresh_tokens` | `app/models/refresh_token.py` | 389 |
| DB-TB-036 | `replay_checkpoints` | `app/models/agent_runtime.py` | 0 |
| DB-TB-037 | `robot_assets` | `app/models/robot_asset.py` | 33367 |
| DB-TB-038 | `robot_models` | `app/models/robot_model.py` | 13 |
| DB-TB-039 | `robot_part_manifests` | `app/models/robot_part_manifest.py` | 0 |
| DB-TB-040 | `robot_project_files` | `app/models/robot_project_file.py` | 91 |
| DB-TB-041 | `robot_projects` | `app/models/robot_project.py` | 3 |
| DB-TB-042 | `robot_sop_drafts` | `app/models/robot_sop_draft.py` | 0 |
| DB-TB-043 | `role_permissions` | `app/models/rbac.py` | 23 |
| DB-TB-044 | `roles` | `app/models/rbac.py` | 4 |
| DB-TB-045 | `schools` | `app/models/school.py` | 2869 |
| DB-TB-046 | `session_step_records` | `app/models/training.py` | 107 |
| DB-TB-047 | `skill_releases` | `app/models/skill_registry.py` | 0 |
| DB-TB-048 | `skill_reviews` | `app/models/skill_registry.py` | 0 |
| DB-TB-049 | `skills` | `app/models/skill_registry.py` | 0 |
| DB-TB-050 | `snapshots` | `app/models/snapshot.py` | 0 |
| DB-TB-051 | `sop_audit_logs` | `app/models/audit_log.py` | 0 |
| DB-TB-052 | `sop_steps` | `app/models/sop.py` | 719 |
| DB-TB-053 | `sops` | `app/models/sop.py` | 54 |
| DB-TB-054 | `student_skill_profiles` | `app/models/skill_profile.py` | 8 |
| DB-TB-055 | `student_weak_steps` | `app/models/skill_profile.py` | 4 |
| DB-TB-056 | `task_executions` | `app/models/task_execution.py` | 11 |
| DB-TB-057 | `task_step_results` | `app/models/task_execution.py` | 32 |
| DB-TB-058 | `tasks` | `app/models/task.py` | 30 |
| DB-TB-059 | `teacher_robot_bindings` | `app/models/robot_model.py` | 7 |
| DB-TB-060 | `timeline_segments` | `app/models/timeline.py` | 0 |
| DB-TB-061 | `training_sessions` | `app/models/training.py` | 17 |
| DB-TB-062 | `training_submissions` | `app/models/training_submission.py` | 16 |
| DB-TB-063 | `user_preferences` | `app/models/user_preference.py` | 9 |
| DB-TB-064 | `user_roles` | `app/models/rbac.py` | 11 |
| DB-TB-065 | `users` | `app/models/user.py` | 13 |

合计 65 张业务表（数据库另有 `alembic_version`，Alembic 自带，不计入业务模型）。**非空 37 张，空表 28 张。** 数据量最大的三张：`robot_assets` 33367、`schools` 2869、`access_tokens` 389。

## 3. 迁移（MG）

版本文件 38 = alembic 图节点 38；单一 head `20260817_sop_three_phase`，base `001`；数据库 `alembic_version` = `20260817_sop_three_phase`，三源一致。逐个版本文件见 `r-mos-backend/alembic/versions/`。

## 4. 启动未导入的后端模块（BE-MOD）

以 `import main` 后的 `sys.modules` 为运行时源。未导入≠死代码：延迟导入与脚本消费同样表现为未导入，故每项附第二证据（全仓引用检索）。

| ID | 模块文件 |
|---|---|
| BE-MOD-001 | `app/core/migration_contract.py` |
| BE-MOD-002 | `app/core/timing_middleware.py` |
| BE-MOD-003 | `app/main.py` |
| BE-MOD-004 | `app/schemas/user.py` |
| BE-MOD-005 | `app/services/analysis/assembly_builder.py` |
| BE-MOD-006 | `app/services/analysis/cad_converter.py` |
| BE-MOD-007 | `app/services/analysis/fault_extractor.py` |
| BE-MOD-008 | `app/services/analysis/manifest_generator.py` |
| BE-MOD-009 | `app/services/analysis/pdf_extractor.py` |
| BE-MOD-010 | `app/services/analysis/sop_extractor.py` |
| BE-MOD-011 | `app/services/analysis/urdf_parser.py` |
| BE-MOD-012 | `app/services/identity/teacher_monitor.py` |
| BE-MOD-013 | `app/services/intent/training_intent_router.py` |
| BE-MOD-014 | `app/services/knowledge/embedding.py` |
| BE-MOD-015 | `app/services/knowledge/knowledge_retriever.py` |
| BE-MOD-016 | `app/services/llm/audit.py` |
| BE-MOD-017 | `app/services/llm/deepseek_provider.py` |
| BE-MOD-018 | `app/services/llm/minimax_provider.py` |
| BE-MOD-019 | `app/services/llm/mock_provider.py` |
| BE-MOD-020 | `app/services/policy.py` |
| BE-MOD-021 | `app/services/policy/risk_scorer.py` |
| BE-MOD-022 | `app/services/storage/s3_storage.py` |
| BE-MOD-023 | `app/services/training/workbench_draft_generator.py` |
| BE-MOD-024 | `app/services/training/workbench_execution_service.py` |
| BE-MOD-025 | `app/services/user_preference_service.py` |

合计 25 个（磁盘 231，启动已导入 206）。其中全仓零引用 3 个：`app/schemas/user.py`、`app/services/llm/audit.py`、`app/services/policy/__init__.py`（后者导致 `policy/risk_scorer.py` 亦无可达消费者）。

## 5. 前端未进入构建图的模块（FE-MOD）

运行时/构建源为 `vite build --sourcemap` 产出的模块闭包。引用关系用 **TypeScript 模块解析**判定
（解析 `@/` 别名、相对路径、`index.ts` 兜底、`vi.mock` 与动态 `import()`），不是文件名匹配——
早期用 basename 匹配曾把 `./data/criticalParts` 这类带子目录的再导出漏判为零引用，该缺陷由异源复核发现并已修正。
纯类型文件编译期擦除，天然不在图内，不算孤立。

| ID | 模块 | 生产引用 | 测试引用 | 判定 |
|---|---|---:|---:|---|
| FE-MOD-001 | `src/adjudication/data/criticalParts.ts` | 1 | 0 | 有生产引用但未进构建图 |
| FE-MOD-002 | `src/adjudication/index.ts` | 13 | 7 | 有生产引用但未进构建图 |
| FE-MOD-003 | `src/adjudication/ui/examHeader.ts` | 0 | 4 | 仅测试引用 |
| FE-MOD-004 | `src/api/tools.ts` | 0 | 0 | 零引用 |
| FE-MOD-005 | `src/components/Maintenance/index.ts` | 1 | 3 | 有生产引用但未进构建图 |
| FE-MOD-006 | `src/components/Viewer3D/Atom01Model.tsx` | 1 | 0 | 有生产引用但未进构建图 |
| FE-MOD-007 | `src/components/Viewer3D/Atom01Viewer.tsx` | 0 | 0 | 零引用 |
| FE-MOD-008 | `src/components/Viewer3D/DynamicModelLoader.tsx` | 1 | 1 | 有生产引用但未进构建图 |
| FE-MOD-009 | `src/components/Viewer3D/HumanoidRobot.tsx` | 2 | 0 | 有生产引用但未进构建图 |
| FE-MOD-010 | `src/components/Viewer3D/ModelPreloader.tsx` | 0 | 3 | 仅测试引用 |
| FE-MOD-011 | `src/components/Viewer3D/RobotViewer.tsx` | 1 | 0 | 有生产引用但未进构建图 |
| FE-MOD-012 | `src/components/Viewer3D/constants.ts` | 4 | 0 | 有生产引用但未进构建图 |
| FE-MOD-013 | `src/components/Viewer3D/hooks/useRobotData.ts` | 2 | 1 | 有生产引用但未进构建图 |
| FE-MOD-014 | `src/components/Viewer3D/index.ts` | 0 | 0 | 零引用 |
| FE-MOD-015 | `src/components/Viewer3D/useRobotDataManifest.ts` | 0 | 0 | 零引用 |
| FE-MOD-016 | `src/components/common/index.ts` | 17 | 0 | 有生产引用但未进构建图 |
| FE-MOD-017 | `src/components/knowledge/RobotProjectUploadPanel.tsx` | 0 | 0 | 零引用 |
| FE-MOD-018 | `src/pages/admin/ApprovalQueuePage.tsx` | 0 | 0 | 零引用 |
| FE-MOD-019 | `src/store/workbenchStore.ts` | 0 | 1 | 仅测试引用 |
| FE-MOD-020 | `src/test-setup.ts` | 0 | 0 | 构建配置加载（vitest setupFiles） |
| FE-MOD-021 | `src/types/maintenance.ts` | 3 | 1 | 有生产引用但未进构建图 |
| FE-MOD-022 | `src/types/report.ts` | 2 | 0 | 有生产引用但未进构建图 |
| FE-MOD-023 | `src/types/robot.ts` | 3 | 0 | 有生产引用但未进构建图 |
| FE-MOD-024 | `src/types/robotKnowledge.ts` | 3 | 0 | 有生产引用但未进构建图 |
| FE-MOD-025 | `src/types/robotModel.ts` | 11 | 4 | 有生产引用但未进构建图 |
| FE-MOD-026 | `src/types/sop.ts` | 4 | 0 | 有生产引用但未进构建图 |
| FE-MOD-027 | `src/types/teaching.ts` | 8 | 1 | 有生产引用但未进构建图 |
| FE-MOD-028 | `src/types/user.ts` | 1 | 0 | 有生产引用但未进构建图 |

合计 28 个模块不在构建图内：有生产引用但未进构建图 18、零引用 6、仅测试引用 3、构建配置加载（vitest setupFiles） 1。

**零引用 6 项**（无任何生产或测试引用）：`src/api/tools.ts`、`src/components/Viewer3D/Atom01Viewer.tsx`、`src/components/Viewer3D/index.ts`、`src/components/Viewer3D/useRobotDataManifest.ts`、`src/components/knowledge/RobotProjectUploadPanel.tsx`、`src/pages/admin/ApprovalQueuePage.tsx`。
