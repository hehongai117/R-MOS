# A3 架构证据

- 版本：0.1.0
- 日期：2026-08-27
- 状态：In Review
- 被审基线：`B-ASIS = 29d2a5889e3b320a3e777e3d8c19efbbe31c0294`
- 对应报告：[A3 当前架构与数据边界审计报告](../2026-08-27-a3-current-architecture-and-data-boundaries-v0.1.0.md)

## 1. 方法

1. **依赖图**：AST 解析 `app/**/*.py` 的 `Import`/`ImportFrom`（相对导入按 `level` 还原为绝对模块名），
   只保留指向 `app.` 内部的边；目标模块名逐级回退到已知模块（处理 `from app.x.y import Symbol` 的情形）。
2. **循环检测**：Tarjan 强连通分量，只报 size > 1 的分量。
3. **写入者**：ORM 类的构造调用 `Model(...)`，以及 `update(Model)`／`delete(Model)`。
4. **读取者**：`select(Model)` 与 `select(Model.col)`。
5. **共享状态**：只取模块**顶层**的实例化赋值（`x = SomeClass(...)`），不含函数内局部对象。

## 2. 分层与跨层边

| 层 | 模块数 |
|---|---:|
| `services` | 115 |
| `models` | 40 |
| `api` | 39 |
| `schemas` | 18 |
| `core` | 11 |
| `adapters` | 5 |
| `other` | 2 |

| 源层 → 目标层 | 边数 |
|---|---:|
| `services` → `models` | 109 |
| `api` → `services` | 82 |
| `api` → `core` | 42 |
| `api` → `models` | 39 |
| `services` → `core` | 34 |
| `api` → `schemas` | 23 |
| `services` → `schemas` | 12 |
| `services` → `adapters` | 6 |
| `api` → `adapters` | 3 |
| `core` → `models` | 2 |
| `schemas` → `models` | 1 |
| `adapters` → `core` | 1 |
| `adapters` → `services` | 1 |

**反向边核对：** `models→services`、`services→api`、`models→api` 三个方向边数均为 0、0、0。

## 3. 循环依赖

共 1 组：

- app.services.llm.deepseek_provider ↔ app.services.llm.minimax_provider ↔ app.services.llm.router

## 4. 逐表数据所有权

**检测口径（已按异源复核修正）：** 先在每个文件里把 `from app.models.x import Y as Z` 解析成
「本地名 Z → ORM 真名 Y」，再匹配构造调用与 `update/delete`。这样同时消除两类误差：
同名误判（`EvidenceItem`／`AssessmentAuditEvent` 在部分模块指 Pydantic schema）与
别名漏判（ORM 常以 `as XModel` 引入）。`scripts/` 前缀者为种子或运维脚本。

| 表 | 应用侧写入者 | 脚本写入者 | 判定 |
|---|---|---|---|
| `access_tokens` | `api/v1/endpoints/auth.py` | 0 | — |
| `agent_runtime_snapshots` | — | 0 | **完全无写入路径** |
| `ai_knowledge_chunks` | `services/knowledge/project_ingest_worker.py` | 0 | — |
| `ai_tool_calls` | `api/v1/endpoints/agent.py` | 0 | — |
| `alignment_map` | — | 0 | **完全无写入路径** |
| `analysis_tasks` | `api/v1/endpoints/robots.py` | 0 | — |
| `approval_records` | — | 0 | **完全无写入路径** |
| `approvals` | `api/v1/endpoints/agent.py` | 0 | — |
| `assessment_audit_events` | `services/assessment_service.py` | 0 | — |
| `assessment_providers` | `services/assessment_service.py` | 0 | — |
| `assignment_attempts` | `services/teaching_service.py` | 2 | — |
| `assignments` | `services/teaching_service.py` | 3 | — |
| `audit_events` | `api/v1/endpoints/admin.py`、`api/v1/endpoints/training.py`、`services/audit_event_service.py`、`services/llm/audit.py` | 0 | 多写入者 |
| `belief_state_records` | `services/memory/long_term.py` | 0 | — |
| `classes` | `services/teaching_service.py` | 4 | — |
| `commands` | `api/v1/endpoints/agent.py` | 0 | — |
| `conversation_turns` | — | 0 | **完全无写入路径** |
| `courses` | `services/teaching_service.py` | 4 | — |
| `decision_records` | — | 0 | **完全无写入路径** |
| `enrollments` | `services/teaching_service.py` | 3 | — |
| `events` | `services/event_service.py` | 1 | — |
| `evidence_bundles` | `services/evidence_engine.py`、`services/evidence_service.py`、`services/teaching/report_generator.py` | 1 | 多写入者 |
| `evidence_cards` | `api/v1/endpoints/teaching_roster.py` | 0 | — |
| `evidence_items` | `services/evidence_service.py`、`services/teaching/report_generator.py` | 0 | — |
| `evidence_links` | `services/evidence_engine.py` | 1 | — |
| `external_assessments` | `services/assessment_service.py` | 0 | — |
| `fault_cases` | `services/fault_service.py` | 2 | — |
| `fault_sop_mappings` | — | 3 | **仅脚本写入** |
| `guidance_policies` | `services/teaching_service.py` | 3 | — |
| `incidents` | `services/incident_service.py` | 0 | — |
| `knowledge_documents` | `services/analysis/pdf_extractor.py` | 2 | — |
| `multimodal_timelines` | — | 0 | **完全无写入路径** |
| `observations` | `services/observation_service.py` | 0 | — |
| `permissions` | — | 2 | **仅脚本写入** |
| `refresh_tokens` | `api/v1/endpoints/auth.py` | 0 | — |
| `replay_checkpoints` | — | 0 | **完全无写入路径** |
| `robot_assets` | `api/v1/endpoints/robots.py`、`services/analysis/assembly_builder.py`、`services/analysis/cad_converter.py`、`services/analysis/manifest_generator.py` | 3 | 多写入者 |
| `robot_models` | `api/v1/endpoints/robots.py` | 3 | — |
| `robot_part_manifests` | `services/knowledge/project_ingest_worker.py` | 0 | — |
| `robot_project_files` | `services/knowledge/project_ingest_service.py`、`services/knowledge/project_ingest_worker.py` | 0 | — |
| `robot_projects` | `services/knowledge/project_ingest_service.py` | 0 | — |
| `robot_sop_drafts` | `api/v1/endpoints/maintenance.py` | 0 | — |
| `role_permissions` | — | 2 | **仅脚本写入** |
| `roles` | — | 2 | **仅脚本写入** |
| `schools` | — | 1 | **仅脚本写入** |
| `session_step_records` | `services/training/session_service.py` | 1 | — |
| `skill_releases` | `api/v1/endpoints/skills.py` | 0 | — |
| `skill_reviews` | `api/v1/endpoints/skills.py` | 0 | — |
| `skills` | `api/v1/endpoints/skills.py` | 0 | — |
| `snapshots` | `services/snapshot_service.py` | 1 | — |
| `sop_audit_logs` | — | 0 | **完全无写入路径** |
| `sop_steps` | `services/analysis/sop_extractor.py`、`services/sop_service.py` | 6 | — |
| `sops` | `services/analysis/sop_extractor.py`、`services/sop_service.py` | 7 | — |
| `student_skill_profiles` | `services/memory/skill_profile_service.py` | 1 | — |
| `student_weak_steps` | `services/memory/skill_profile_service.py` | 1 | — |
| `task_executions` | `services/pipeline/task_pipeline_service.py` | 0 | — |
| `task_step_results` | `services/pipeline/task_pipeline_service.py` | 0 | — |
| `tasks` | `services/pipeline/task_pipeline_service.py`、`services/task_service.py` | 2 | — |
| `teacher_robot_bindings` | `api/v1/endpoints/onboarding.py`、`api/v1/endpoints/robots.py` | 1 | — |
| `timeline_segments` | — | 0 | **完全无写入路径** |
| `training_sessions` | `services/training/session_service.py` | 1 | — |
| `training_submissions` | `services/training/submission_service.py` | 1 | — |
| `user_preferences` | `services/user_preference_service.py` | 1 | — |
| `user_roles` | — | 2 | **仅脚本写入** |
| `users` | `api/v1/endpoints/auth.py` | 2 | — |

**完全无写入路径 9 张：** `agent_runtime_snapshots`、`alignment_map`、`approval_records`、`conversation_turns`、`decision_records`、`multimodal_timelines`、`replay_checkpoints`、`sop_audit_logs`、`timeline_segments`

**仅由脚本写入、应用代码零写入 6 张：** `fault_sop_mappings`、`permissions`、`role_permissions`、`roles`、`schools`、`user_roles`

**合计 15 张表在应用代码里没有写入路径。** 该数字与异源复核方独立得出的结果一致。

## 5. 端点模块 → 服务 → 模型 全量映射

| 端点模块 | 服务依赖 | 模型依赖 |
|---|---|---|
| `adapter` | — | — |
| `admin` | authz_guard | audit_event、event、user |
| `agent` | access_control、agent_service、authz_guard、coach_agent、diagnoser_agent、knowledge_governance、multi_agent_coordinator、orchestrator_v2、tool_executor | approval、command_runtime |
| `agent_evidence` | authz_guard、evidence_enforcement | — |
| `agent_governance` | approval_queue、authz_guard、sop.quality_monitor、teaching.report_generator、user_preference_service | — |
| `agent_knowledge` | authz_guard、knowledge.project_ingest_service、knowledge.project_ingest_worker、knowledge_governance | — |
| `agent_v2` | access_control、authz_guard、orchestrator_v2、policy_matrix | — |
| `ai_assistant` | ai_assistant_service | — |
| `ai_commands` | access_control、authz_guard | audit_event、command_runtime、knowledge_chunk |
| `approvals` | access_control、approval_service、authz_guard | approval |
| `assessments` | assessment_service | — |
| `audit` | access_control、authz_guard | audit_event |
| `auth` | access_control、identity.session_initializer、login_throttle | access_token、refresh_token、school、user |
| `evidence` | evidence_service | — |
| `fault_cases` | fault_service | — |
| `health` | — | — |
| `incidents` | incident_service | — |
| `llm_health` | llm.router | — |
| `maintenance` | maintenance.sop_draft_generator、maintenance.verdict_step_generator | robot_project、robot_sop_draft |
| `observations` | observation_service | — |
| `onboarding` | authz_guard | robot_model、user |
| `pipeline` | pipeline.fault_diagnosis_service、pipeline.task_pipeline_service | — |
| `robots` | authz_guard、knowledge.project_ingest_service、robot_asset_validator、robot_service、storage | analysis_task、robot_asset、robot_model |
| `scenarios` | — | fault_sop_mapping、sop |
| `schools` | — | school、user |
| `skills` | access_control、authz_guard | skill_registry |
| `sops` | sop_service | — |
| `student_tasks` | — | sop、task、task_execution |
| `students` | authz_guard | robot_model、user |
| `tasks` | authz_guard、event_service、ownership、preflight_check、scoring_service、task_service | task、task_execution |
| `teaching` | teaching_service | — |
| `teaching_common` | — | — |
| `teaching_roster` | access_control、authz_guard、diagnosis_service、evidence_engine、teaching_service | evidence、teaching、timeline |
| `training` | access_control、authz_guard、identity.class_membership、memory.skill_profile_service、ownership、training.feedback_generator、training.session_service、training.submission_service | audit_event、training、training_submission |
| `training_workbench` | authz_guard、training.project_generator、training.session_service、training.workbench_draft_generator、training.workbench_execution_service | — |
| `websocket` | websocket_manager | — |

## 6. 复现命令

```bash
cd <worktree>/r-mos-backend
set -a; . /Users/xuhehong/Desktop/r-mos/r-mos-backend/.env; set +a; unset CORS_ORIGINS
# 依赖图与循环：AST 解析 app/**/*.py 的 Import/ImportFrom + Tarjan SCC
# 写入者：AST 找 Model(...) 构造与 update/delete(Model)
# 单例：AST 取模块顶层 x = SomeClass(...) 赋值
grep -c '' docker-compose.yml && grep -nE 'replicas|volumes:|workers' docker-compose.yml main.py
```

## 7. 局限

1. 写入者基于静态构造调用，裸 SQL（`session.execute(text(...))`）与 ORM 关系级联写入会漏判；
   「无写入路径」应读作「未找到静态写入代码」。
2. 依赖图是模块级，不区分顶层导入与函数内延迟导入，也不反映运行时调用频次。
3. 单例清单只覆盖 `app/`，不含 `scripts/`。
4. 本批未执行测试、未启动长驻服务，验证等级上限 E1。
