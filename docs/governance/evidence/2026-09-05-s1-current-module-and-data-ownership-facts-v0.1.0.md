# RMOS-S1-001 当前模块、职责与数据归属事实报告

- 版本：0.1.0
- 日期：2026-09-05
- 主干任务：`RMOS-S1-001（事实收集部分）`
- 证据等级：E1（当前源码、运行期路由注册表、ORM 元数据、AST 静态调用与写入分析）
- 源码事实基线：`cb00b293303ae9df61f9d496b37f1fdbf2a7e9f0`
- 现场 HEAD：`cdd82b29`；`cb00b293..HEAD` 只变化两份治理/交接文档，后端树与前端树对象分别保持 `27a5b0f8859cb07c959d31ee57b507642aaa2d12`、`67521cba2f7da35e2fce4ddc970c5deeaf4b60fe` 不变
- 改动边界：本报告只记录当前事实，不给出目标架构、保留/合并/替换/删除判断或实施建议

## 1. 口径与复现入口

### 1.1 本次口径

1. HTTP 路由从给定环境载入真实 `main:app`，只枚举 `APIRoute`；WebSocket 另枚举 `APIWebSocketRoute`。
2. “依赖/调用”由 AST 中实际 `Call` 节点判定；直接调用、对象方法调用，以及 `Depends(fn)`、`run_sync(fn)` 这类回调参数计入，只有 import、注释或 docstring 不计入。
3. 业务表从 `Base.metadata.tables` 真实枚举。写入者同时识别 ORM 构造、`insert/update/delete(Model)`、`db.delete(row)`，以及从 `select/get` 结果追踪到的 ORM 属性写入。
4. “指定归属字段”严格只统计任务点名的 `created_by_user_id`、`user_id`、`owner_*`、`school_name`。表中的“无”不等于没有任何外键或业务范围，只表示没有这四类直接字段。
5. 前端关系以 TypeScript AST 的真实调用节点为准，并沿页面的本地 import 图传递展开；类型 import、注释、字符串说明不计入。
6. 循环依赖从 `app/**/*.py` 的内部 import 图用 Tarjan 强连通分量复测；与 A3 的“全仓”口径一致。

### 1.2 环境与通用命令

```bash
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime/r-mos-backend
set -a; . /Users/xuhehong/Desktop/r-mos/r-mos-backend/.env; set +a
unset CORS_ORIGINS
export DEBUG=true
PY=/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python
```

本次临时取证程序均位于 `/tmp`，未写入仓库：

- `[R1/R2/R4/R5] /tmp/rmos_s1_facts.py`，SHA-256 `b799fff2153049ee81b24320da27479dc85664bac647c98f1560d5abec81ecda`
- `[R3] /tmp/rmos_s1_frontend_facts.cjs`，SHA-256 `ec62c79ee4d15766aa78b82587972b58d0b3d8b4eb8947dc8da8b4edf8645be3`

```bash
$PY /tmp/rmos_s1_facts.py > /tmp/rmos_s1_facts.json
cd ../r-mos-frontend
node /tmp/rmos_s1_frontend_facts.cjs > /tmp/rmos_s1_frontend_facts.json
```

基线复现 `[R0]`：

```bash
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime
git status --short --branch
git diff --name-status cb00b293..HEAD
git rev-parse cb00b293:r-mos-backend HEAD:r-mos-backend
git rev-parse cb00b293:r-mos-frontend HEAD:r-mos-frontend
```

## 2. 模块与职责现状

### 2.1 后端端点文件与真实路由数

`app/api/v1/endpoints/` 共 36 个 Python 文件（含 `__init__.py`）；其中 35 个非初始化文件。真实 `main:app` 中归属这些端点模块的 HTTP `APIRoute` 为 **167** 条，方法合计为 **DELETE 4**、**GET 80**、**PATCH 7**、**POST 70**、**PUT 6**。另有 `main.root` 的 `GET /` 1 条，因此全应用 `APIRoute` 总数为 **168**。WebSocket 为 **2** 条：`/ws/robot/status`、`/ws/robot/{robot_id}/status`。

| 端点文件 | GET | POST | PUT | PATCH | DELETE | HTTP 合计 | WebSocket | 当前业务域 | 实际调用的 service | 复现 |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| `__init__.py` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 路由聚合包初始化 | — | R1 |
| `admin.py` | 1 | 1 | 0 | 0 | 0 | 2 | 0 | 用户与系统管理 | `authz_guard` | R1 |
| `agent.py` | 1 | 4 | 0 | 0 | 0 | 5 | 0 | Agent 编排与命令执行 | `access_control`、`agent_service`、`authz_guard`、`coach_agent`、`diagnoser_agent`、`multi_agent_coordinator`、`orchestrator_v2`、`tool_executor` | R1 |
| `agent_evidence.py` | 3 | 1 | 0 | 0 | 0 | 4 | 0 | Agent 证据门禁 | `authz_guard`、`evidence_enforcement` | R1 |
| `agent_governance.py` | 1 | 2 | 2 | 0 | 0 | 5 | 0 | Agent 治理、报告与 SOP 质量 | `authz_guard`、`sop.quality_monitor`、`teaching.report_generator`、`user_preference_service` | R1 |
| `agent_knowledge.py` | 4 | 5 | 0 | 0 | 0 | 9 | 0 | 知识治理与机器人项目导入 | `authz_guard`、`knowledge.project_ingest_service`、`knowledge.project_ingest_worker`、`knowledge_governance` | R1 |
| `agent_v2.py` | 3 | 2 | 0 | 0 | 0 | 5 | 0 | Agent V2 编排、任务上下文与事件 | `access_control`、`authz_guard`、`orchestrator_v2`、`ownership`、`policy_matrix` | R1 |
| `ai_assistant.py` | 0 | 1 | 0 | 0 | 0 | 1 | 0 | AI 对话助手 | `ai_assistant_service` | R1 |
| `ai_commands.py` | 4 | 0 | 0 | 0 | 0 | 4 | 0 | AI 引用、审计回放与安全指标 | `access_control`、`authz_guard` | R1 |
| `approvals.py` | 2 | 2 | 0 | 0 | 0 | 4 | 0 | 审批查询、批准、拒绝与执行 | `access_control`、`approval_service`、`authz_guard` | R1 |
| `assessments.py` | 5 | 5 | 0 | 1 | 0 | 11 | 0 | 外部评估提供方、评估记录与审计 | `assessment_service`、`authz_guard`、`ownership` | R1 |
| `audit.py` | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 审计事件查询 | `access_control`、`authz_guard` | R1 |
| `auth.py` | 0 | 4 | 0 | 0 | 0 | 4 | 0 | 注册、登录、刷新与登出 | `access_control`、`identity.session_initializer`、`login_throttle` | R1 |
| `evidence.py` | 2 | 1 | 0 | 0 | 0 | 3 | 0 | 证据包与证据项 | `authz_guard`、`evidence_service` | R1 |
| `fault_cases.py` | 2 | 1 | 1 | 0 | 1 | 5 | 0 | 故障案例 | `authz_guard`、`fault_service`、`ownership` | R1 |
| `health.py` | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 服务健康 | — | R1 |
| `incidents.py` | 2 | 1 | 0 | 0 | 0 | 3 | 0 | 事件/事故记录 | `authz_guard`、`incident_service` | R1 |
| `llm_health.py` | 1 | 0 | 0 | 0 | 0 | 1 | 0 | LLM 提供方健康 | `llm.router` | R1 |
| `maintenance.py` | 2 | 4 | 0 | 1 | 0 | 7 | 0 | 机器人项目 SOP 草稿与审核 | `authz_guard`、`maintenance.sop_draft_generator`、`maintenance.verdict_step_generator`、`ownership` | R1 |
| `observations.py` | 2 | 1 | 0 | 0 | 0 | 3 | 0 | 观测记录 | `authz_guard`、`observation_service` | R1 |
| `onboarding.py` | 1 | 1 | 0 | 0 | 0 | 2 | 0 | 教师机器人选择与绑定 | `authz_guard` | R1 |
| `pipeline.py` | 0 | 4 | 0 | 0 | 0 | 4 | 0 | 任务生成、步骤执行与故障诊断流水线 | `authz_guard`、`ownership`、`pipeline.fault_diagnosis_service`、`pipeline.task_pipeline_service` | R1 |
| `robots.py` | 7 | 4 | 3 | 0 | 2 | 16 | 0 | 机器人、资产、分析任务与绑定 | `authz_guard`、`knowledge.project_ingest_service`、`robot_asset_validator`、`robot_service`、`robot_visibility`、`storage` | R1 |
| `scenarios.py` | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 故障场景读取 | — | R1 |
| `schools.py` | 2 | 0 | 0 | 0 | 0 | 2 | 0 | 学校与教师注册查询 | — | R1 |
| `skills.py` | 0 | 3 | 0 | 0 | 0 | 3 | 0 | 技能注册、评审与发布 | `access_control`、`authz_guard` | R1 |
| `sops.py` | 4 | 1 | 0 | 0 | 1 | 6 | 0 | SOP 与步骤 | `authz_guard`、`ownership`、`sop_service` | R1 |
| `student_tasks.py` | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 学生任务读取 | — | R1 |
| `students.py` | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 学生可见机器人读取 | `authz_guard` | R1 |
| `tasks.py` | 4 | 5 | 0 | 0 | 0 | 9 | 0 | 任务生命周期、事件、评分与报告 | `authz_guard`、`event_service`、`ownership`、`preflight_check`、`scoring_service`、`task_service` | R1 |
| `teaching.py` | 2 | 1 | 0 | 0 | 0 | 3 | 0 | 课程、班级与指导策略 | `authz_guard`、`ownership`、`teaching_service` | R1 |
| `teaching_common.py` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 教学端点共用转换/异常辅助 | — | R1 |
| `teaching_roster.py` | 12 | 7 | 0 | 2 | 0 | 21 | 0 | 班级成员、作业、尝试、回放、诊断与证据 | `access_control`、`authz_guard`、`diagnosis_service`、`evidence_engine`、`ownership`、`teaching_service` | R1 |
| `training.py` | 8 | 4 | 0 | 3 | 0 | 15 | 0 | 训练会话、提交、反馈与技能画像 | `access_control`、`authz_guard`、`identity.class_membership`、`memory.skill_profile_service`、`ownership`、`training.feedback_generator`、`training.session_service`、`training.submission_service` | R1 |
| `training_workbench.py` | 0 | 5 | 0 | 0 | 0 | 5 | 0 | 训练工作台项目、草稿、执行与证据上传 | `authz_guard`、`training.project_generator`、`training.session_service`、`training.workbench_draft_generator`、`training.workbench_execution_service` | R1 |
| `websocket.py` | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 机器人遥测 WebSocket | `authz_guard`、`robot_visibility`、`websocket_manager` | R1 |

复现 `[R1]`：

```bash
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime/r-mos-backend
$PY /tmp/rmos_s1_facts.py > /tmp/rmos_s1_facts.json
$PY - <<'PY'
import json
d=json.load(open('/tmp/rmos_s1_facts.json'))
print(d['route_total'], d['websocket_route_total'])
for m,x in d['route_counts'].items(): print(m, x['routes'], x['methods'])
PY
```

### 2.2 `app/services/` 的组织与调用者

根目录有 **36 个 `.py` 文件**（含 `__init__.py`），一级子包 **16 个**，递归合计 **115 个 Python 模块文件**。下表调用者范围为 `main.py + app/**/*.py`，只计实际 `Call` 节点。

#### 根目录 36 个文件

| service 文件 | 当前直接调用者 | 复现 |
|---|---|---|
| `__init__.py` | `services.storage` | R2 |
| `access_control.py` | `api.v1.endpoints.agent`、`api.v1.endpoints.agent_v2`、`api.v1.endpoints.ai_commands`、`api.v1.endpoints.approvals`、`api.v1.endpoints.audit`、`api.v1.endpoints.auth`、`api.v1.endpoints.skills`、`api.v1.endpoints.teaching_roster`、`api.v1.endpoints.training`、`services.authz_guard`、`services.ownership` | R2 |
| `agent_service.py` | `api.v1.endpoints.agent` | R2 |
| `ai_assistant_service.py` | `api.v1.endpoints.ai_assistant` | R2 |
| `approval_service.py` | `api.v1.endpoints.approvals` | R2 |
| `assessment_service.py` | `api.v1.endpoints.assessments` | R2 |
| `audit_event_service.py` | `services.access_control` | R2 |
| `authz_guard.py` | `api.v1.endpoints.admin`、`api.v1.endpoints.agent`、`api.v1.endpoints.agent_evidence`、`api.v1.endpoints.agent_governance`、`api.v1.endpoints.agent_knowledge`、`api.v1.endpoints.agent_v2`、`api.v1.endpoints.ai_commands`、`api.v1.endpoints.approvals`、`api.v1.endpoints.assessments`、`api.v1.endpoints.audit`、`api.v1.endpoints.evidence`、`api.v1.endpoints.fault_cases`、`api.v1.endpoints.incidents`、`api.v1.endpoints.maintenance`、`api.v1.endpoints.observations`、`api.v1.endpoints.onboarding`、`api.v1.endpoints.pipeline`、`api.v1.endpoints.robots`、`api.v1.endpoints.skills`、`api.v1.endpoints.sops`、`api.v1.endpoints.students`、`api.v1.endpoints.tasks`、`api.v1.endpoints.teaching`、`api.v1.endpoints.teaching_roster`、`api.v1.endpoints.training`、`api.v1.endpoints.training_workbench`、`api.v1.endpoints.websocket`、`services.ownership`、`services.robot_visibility`、`main` | R2 |
| `coach_agent.py` | `api.v1.endpoints.agent` | R2 |
| `diagnoser_agent.py` | `api.v1.endpoints.agent` | R2 |
| `diagnosis_service.py` | `api.v1.endpoints.teaching_roster` | R2 |
| `event_service.py` | `api.v1.endpoints.tasks`、`services.diagnosis_service`、`services.task_service` | R2 |
| `evidence_enforcement.py` | `api.v1.endpoints.agent_evidence` | R2 |
| `evidence_engine.py` | `api.v1.endpoints.teaching_roster`、`services.diagnosis_service`、`services.task_service` | R2 |
| `evidence_service.py` | `api.v1.endpoints.evidence`、`services.training.workbench_execution_service` | R2 |
| `fault_service.py` | `api.v1.endpoints.fault_cases` | R2 |
| `incident_service.py` | `api.v1.endpoints.incidents` | R2 |
| `knowledge_governance.py` | `api.v1.endpoints.agent_knowledge`、`services.orchestrator_v2` | R2 |
| `login_throttle.py` | `api.v1.endpoints.auth` | R2 |
| `multi_agent_coordinator.py` | `api.v1.endpoints.agent` | R2 |
| `observation_service.py` | `api.v1.endpoints.observations` | R2 |
| `orchestrator_v2.py` | `api.v1.endpoints.agent`、`api.v1.endpoints.agent_v2` | R2 |
| `ownership.py` | `api.v1.endpoints.agent_v2`、`api.v1.endpoints.assessments`、`api.v1.endpoints.fault_cases`、`api.v1.endpoints.maintenance`、`api.v1.endpoints.pipeline`、`api.v1.endpoints.sops`、`api.v1.endpoints.tasks`、`api.v1.endpoints.teaching`、`api.v1.endpoints.teaching_roster`、`api.v1.endpoints.training` | R2 |
| `policy_matrix.py` | `api.v1.endpoints.agent_v2`、`services.orchestrator_v2` | R2 |
| `preflight_check.py` | `api.v1.endpoints.tasks` | R2 |
| `robot_asset_validator.py` | `api.v1.endpoints.robots`、`services.analysis.worker` | R2 |
| `robot_service.py` | `api.v1.endpoints.robots` | R2 |
| `robot_visibility.py` | `api.v1.endpoints.robots`、`api.v1.endpoints.websocket` | R2 |
| `scoring_service.py` | `api.v1.endpoints.tasks`、`services.diagnosis_service`、`services.task_service`、`services.teaching.report_generator` | R2 |
| `snapshot_service.py` | `services.task_service` | R2 |
| `sop_service.py` | `api.v1.endpoints.sops` | R2 |
| `task_service.py` | `api.v1.endpoints.tasks`、`services.diagnosis_service` | R2 |
| `teaching_service.py` | `api.v1.endpoints.teaching`、`api.v1.endpoints.teaching_roster`、`services.diagnosis_service` | R2 |
| `tool_executor.py` | `api.v1.endpoints.agent`、`services.approval_service` | R2 |
| `user_preference_service.py` | `api.v1.endpoints.agent_governance`、`services.training.workbench_draft_generator`、`services.training.workbench_execution_service` | R2 |
| `websocket_manager.py` | `api.v1.endpoints.websocket`、`services.identity.teacher_monitor` | R2 |

#### 16 个一级子包

| 子包 | 包内 `.py` 文件 | 包外实际调用者 | 复现 |
|---|---|---|---|
| `analysis/` | `__init__.py`、`assembly_builder.py`、`cad_converter.py`、`fault_extractor.py`、`manifest_generator.py`、`pdf_extractor.py`、`scheduler.py`、`sop_extractor.py`、`urdf_parser.py`、`worker.py` | `main` | R2 |
| `diagnosis/` | `fault_diagnosis_engine.py`、`maintenance_plan_generator.py`、`schemas.py` | — | R2 |
| `identity/` | `__init__.py`、`agent_policy_factory.py`、`class_membership.py`、`session_initializer.py`、`teacher_monitor.py` | `api.v1.endpoints.auth`、`api.v1.endpoints.training`、`services.ownership` | R2 |
| `intent/` | `__init__.py`、`engine.py`、`training_intent_router.py` | `services.orchestrator_v2` | R2 |
| `knowledge/` | `__init__.py`、`document_chunker.py`、`embedding.py`、`fallback_embedding.py`、`file_classifier.py`、`format_support_matrix.py`、`hub.py`、`knowledge_retriever.py`、`project_ingest_service.py`、`project_ingest_worker.py`、`query_embedding_service.py`、`robot_manifest_builder.py` | `api.v1.endpoints.agent_knowledge`、`api.v1.endpoints.robots`、`services.maintenance.sop_draft_generator`、`services.training.project_generator` | R2 |
| `llm/` | `__init__.py`、`audit.py`、`deepseek_provider.py`、`minimax_provider.py`、`mock_provider.py`、`prompts.py`、`router.py`、`telemetry_context_builder.py` | `api.v1.endpoints.llm_health`、`services.ai_assistant_service`、`services.analysis.fault_extractor`、`services.analysis.sop_extractor`、`services.diagnosis.fault_diagnosis_engine`、`services.diagnosis.maintenance_plan_generator`、`services.intent.engine`、`services.memory.training_memory_writer`、`services.orchestrator_v2`、`services.pipeline.fault_diagnosis_service`、`services.policy.risk_scorer`、`services.sop.verdict_enhancer`、`services.teaching.chat_engine`、`services.teaching.report_generator`、`services.training.project_generator`、`services.training.workbench_draft_generator`、`services.training.workbench_execution_service` | R2 |
| `maintenance/` | `__init__.py`、`sop_draft_generator.py`、`verdict_step_generator.py` | `api.v1.endpoints.maintenance` | R2 |
| `memory/` | `__init__.py`、`hub.py`、`long_term.py`、`short_term.py`、`skill_profile_service.py`、`training_memory_writer.py` | `api.v1.endpoints.training`、`services.identity.session_initializer`、`services.training.submission_service` | R2 |
| `orchestration/` | `__init__.py`、`fsm.py`、`idempotency.py`、`module_registry.py` | `services.orchestrator_v2` | R2 |
| `pipeline/` | `__init__.py`、`fault_diagnosis_service.py`、`task_pipeline_service.py` | `api.v1.endpoints.pipeline` | R2 |
| `policy/` | `__init__.py`、`risk_scorer.py` | — | R2 |
| `simulation/` | `__init__.py`、`fault_scenarios.py`、`simulation_executor.py` | `adapters.mock`、`services.llm.mock_provider`、`services.orchestrator_v2` | R2 |
| `sop/` | `__init__.py`、`quality_monitor.py`、`verdict_enhancer.py` | `api.v1.endpoints.agent_governance` | R2 |
| `storage/` | `__init__.py`、`file_storage.py`、`s3_storage.py` | `api.v1.endpoints.robots`、`services.analysis.assembly_builder`、`services.analysis.cad_converter`、`services.analysis.manifest_generator`、`services.analysis.pdf_extractor`、`services.analysis.worker`、`services.training.workbench_draft_generator` | R2 |
| `teaching/` | `__init__.py`、`chat_engine.py`、`group_stats.py`、`report_generator.py` | `api.v1.endpoints.agent_governance` | R2 |
| `training/` | `__init__.py`、`feedback_generator.py`、`project_generator.py`、`session_service.py`、`submission_service.py`、`workbench_draft_generator.py`、`workbench_execution_service.py` | `api.v1.endpoints.training`、`api.v1.endpoints.training_workbench` | R2 |

#### 子包内 79 个文件的直接调用者

| service 文件 | 当前直接调用者 | 复现 |
|---|---|---|
| `analysis/__init__.py` | — | R2 |
| `analysis/assembly_builder.py` | `services.analysis.scheduler` | R2 |
| `analysis/cad_converter.py` | `services.analysis.assembly_builder`、`services.analysis.scheduler` | R2 |
| `analysis/fault_extractor.py` | — | R2 |
| `analysis/manifest_generator.py` | — | R2 |
| `analysis/pdf_extractor.py` | `services.analysis.scheduler` | R2 |
| `analysis/scheduler.py` | `services.analysis.worker` | R2 |
| `analysis/sop_extractor.py` | `services.analysis.scheduler` | R2 |
| `analysis/urdf_parser.py` | `services.analysis.assembly_builder` | R2 |
| `analysis/worker.py` | `main` | R2 |
| `diagnosis/fault_diagnosis_engine.py` | — | R2 |
| `diagnosis/maintenance_plan_generator.py` | — | R2 |
| `diagnosis/schemas.py` | `services.diagnosis.fault_diagnosis_engine`、`services.diagnosis.maintenance_plan_generator` | R2 |
| `identity/__init__.py` | — | R2 |
| `identity/agent_policy_factory.py` | — | R2 |
| `identity/class_membership.py` | `api.v1.endpoints.training`、`services.ownership` | R2 |
| `identity/session_initializer.py` | `api.v1.endpoints.auth` | R2 |
| `identity/teacher_monitor.py` | — | R2 |
| `intent/__init__.py` | `services.orchestrator_v2` | R2 |
| `intent/engine.py` | `services.intent.training_intent_router` | R2 |
| `intent/training_intent_router.py` | — | R2 |
| `knowledge/__init__.py` | `services.knowledge.project_ingest_worker`、`services.knowledge.query_embedding_service` | R2 |
| `knowledge/document_chunker.py` | `services.knowledge.project_ingest_worker` | R2 |
| `knowledge/embedding.py` | — | R2 |
| `knowledge/fallback_embedding.py` | `services.knowledge.project_ingest_worker`、`services.knowledge.query_embedding_service` | R2 |
| `knowledge/file_classifier.py` | `services.knowledge.project_ingest_service`、`services.knowledge.project_ingest_worker` | R2 |
| `knowledge/format_support_matrix.py` | `services.knowledge.file_classifier` | R2 |
| `knowledge/hub.py` | `services.maintenance.sop_draft_generator`、`services.training.project_generator` | R2 |
| `knowledge/knowledge_retriever.py` | — | R2 |
| `knowledge/project_ingest_service.py` | `api.v1.endpoints.agent_knowledge`、`api.v1.endpoints.robots` | R2 |
| `knowledge/project_ingest_worker.py` | `api.v1.endpoints.agent_knowledge` | R2 |
| `knowledge/query_embedding_service.py` | `services.maintenance.sop_draft_generator`、`services.training.project_generator` | R2 |
| `knowledge/robot_manifest_builder.py` | `services.knowledge.project_ingest_worker` | R2 |
| `llm/__init__.py` | `services.intent.engine`、`services.policy.risk_scorer`、`services.sop.verdict_enhancer`、`services.teaching.chat_engine`、`services.training.project_generator`、`services.training.workbench_draft_generator`、`services.training.workbench_execution_service` | R2 |
| `llm/audit.py` | — | R2 |
| `llm/deepseek_provider.py` | `services.llm.router` | R2 |
| `llm/minimax_provider.py` | `services.llm.router` | R2 |
| `llm/mock_provider.py` | `services.llm.router` | R2 |
| `llm/prompts.py` | `services.diagnosis.fault_diagnosis_engine`、`services.diagnosis.maintenance_plan_generator`、`services.policy.risk_scorer` | R2 |
| `llm/router.py` | `api.v1.endpoints.llm_health`、`services.ai_assistant_service`、`services.analysis.fault_extractor`、`services.analysis.sop_extractor`、`services.diagnosis.fault_diagnosis_engine`、`services.diagnosis.maintenance_plan_generator`、`services.llm.telemetry_context_builder`、`services.memory.training_memory_writer`、`services.orchestrator_v2`、`services.pipeline.fault_diagnosis_service`、`services.teaching.report_generator` | R2 |
| `llm/telemetry_context_builder.py` | `services.llm.prompts`、`services.orchestrator_v2` | R2 |
| `maintenance/__init__.py` | — | R2 |
| `maintenance/sop_draft_generator.py` | `api.v1.endpoints.maintenance` | R2 |
| `maintenance/verdict_step_generator.py` | `api.v1.endpoints.maintenance` | R2 |
| `memory/__init__.py` | `services.memory.training_memory_writer` | R2 |
| `memory/hub.py` | `services.identity.session_initializer`、`services.memory.training_memory_writer` | R2 |
| `memory/long_term.py` | `services.memory.hub` | R2 |
| `memory/short_term.py` | `services.memory.hub` | R2 |
| `memory/skill_profile_service.py` | `api.v1.endpoints.training` | R2 |
| `memory/training_memory_writer.py` | `services.training.submission_service` | R2 |
| `orchestration/__init__.py` | — | R2 |
| `orchestration/fsm.py` | `services.orchestrator_v2` | R2 |
| `orchestration/idempotency.py` | `services.orchestrator_v2` | R2 |
| `orchestration/module_registry.py` | `services.orchestrator_v2` | R2 |
| `pipeline/__init__.py` | — | R2 |
| `pipeline/fault_diagnosis_service.py` | `api.v1.endpoints.pipeline` | R2 |
| `pipeline/task_pipeline_service.py` | `api.v1.endpoints.pipeline` | R2 |
| `policy/__init__.py` | — | R2 |
| `policy/risk_scorer.py` | — | R2 |
| `simulation/__init__.py` | — | R2 |
| `simulation/fault_scenarios.py` | `adapters.mock`、`services.llm.mock_provider` | R2 |
| `simulation/simulation_executor.py` | `services.orchestrator_v2` | R2 |
| `sop/__init__.py` | — | R2 |
| `sop/quality_monitor.py` | `api.v1.endpoints.agent_governance` | R2 |
| `sop/verdict_enhancer.py` | — | R2 |
| `storage/__init__.py` | `api.v1.endpoints.robots`、`services.analysis.assembly_builder`、`services.analysis.cad_converter`、`services.analysis.manifest_generator`、`services.analysis.pdf_extractor`、`services.analysis.worker`、`services.training.workbench_draft_generator` | R2 |
| `storage/file_storage.py` | `services.storage.s3_storage` | R2 |
| `storage/s3_storage.py` | — | R2 |
| `teaching/__init__.py` | — | R2 |
| `teaching/chat_engine.py` | — | R2 |
| `teaching/group_stats.py` | `services.teaching.report_generator` | R2 |
| `teaching/report_generator.py` | `api.v1.endpoints.agent_governance` | R2 |
| `training/__init__.py` | — | R2 |
| `training/feedback_generator.py` | `api.v1.endpoints.training` | R2 |
| `training/project_generator.py` | `api.v1.endpoints.training_workbench` | R2 |
| `training/session_service.py` | `api.v1.endpoints.training`、`api.v1.endpoints.training_workbench`、`services.training.workbench_execution_service` | R2 |
| `training/submission_service.py` | `api.v1.endpoints.training`、`services.training.workbench_execution_service` | R2 |
| `training/workbench_draft_generator.py` | `api.v1.endpoints.training_workbench` | R2 |
| `training/workbench_execution_service.py` | `api.v1.endpoints.training_workbench` | R2 |

复现 `[R2]`：

```bash
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime/r-mos-backend
find app/services -maxdepth 1 -type f -name '*.py' | sort
find app/services -mindepth 1 -maxdepth 1 -type d ! -name '__pycache__' | sort
$PY /tmp/rmos_s1_facts.py > /tmp/rmos_s1_facts.json
$PY - <<'PY'
import json
d=json.load(open('/tmp/rmos_s1_facts.json'))['service_organization']
print(d['root_file_count'], d['subpackage_count'], d['service_module_count'])
for service, callers in d['callers'].items(): print(service, callers)
PY
```

### 2.3 前端 `src/pages/` 到 `src/api/` 的实际调用关系

`src/pages/` 中有 **19 个 `*Page.tsx` 页面文件**；`src/api/` 有 **21 个非测试 TypeScript 文件**。表中“经下游模块”表示页面 import 图可达的组件、store 或 hook 内发生真实 API 调用。

| 页面 | 页面内直接调用 | 经下游模块调用 | 复现 |
|---|---|---|---|
| `Atom01DemoPage.tsx` | — | `client.ts`、`robots.ts` | R3 |
| `DashboardPage.tsx` | `client.ts` | `robots.ts` | R3 |
| `KnowledgePage.tsx` | `agent.ts`、`robotKnowledge.ts`、`robots.ts` | `robots.ts` | R3 |
| `LoginPage.tsx` | — | — | R3 |
| `MonitorPage.tsx` | — | `client.ts`、`robots.ts` | R3 |
| `MyTasksPage.tsx` | `studentTasks.ts` | — | R3 |
| `OnboardingRobotsPage.tsx` | `onboarding.ts` | — | R3 |
| `RegisterPage.tsx` | `schools.ts` | — | R3 |
| `ReportListPage.tsx` | `task.ts` | — | R3 |
| `ReportPage.tsx` | `task.ts` | — | R3 |
| `SOPListPage.tsx` | `sop.ts`、`task.ts` | `robots.ts` | R3 |
| `SOPMaintenancePage.tsx` | `agent-v2.ts` | `aiAssistant.ts`、`client.ts`、`pipeline.ts`、`robots.ts`、`sopScripts.ts` | R3 |
| `ScenarioPickerPage.tsx` | `scenarios.ts` | `robots.ts` | R3 |
| `SharedRobotsPage.tsx` | `robots.ts` | — | R3 |
| `StudentSkillsPage.tsx` | `client.ts`、`training.ts` | — | R3 |
| `UserSettingsPage.tsx` | `client.ts` | — | R3 |
| `admin/AdminDashboardPage.tsx` | `adminConsole.ts`、`agent-v2.ts`、`approvals.ts` | — | R3 |
| `admin/ApprovalQueuePage.tsx` | `approvals.ts` | — | R3 |
| `agent/AgentWorkbenchPage.tsx` | `agent-v2.ts`、`pipeline.ts` | — | R3 |

`LoginPage.tsx` 的两列为“—”，表示它不经 `src/api/`：页面调用 `authStore`，实际登录请求由 `src/store/authStore.ts` 内的 `authHttp.post("/auth/login", ...)` 发出。`RegisterPage.tsx` 同时使用 `schools.ts`，注册请求仍由 `authStore.ts` 发出。

另有 6 个页面文件位于 `src/teaching/pages/`，不在题目点名的 `src/pages/` 根下；其事实关系如下：

| 页面 | 实际调用的 `src/api/` 模块 | 复现 |
|---|---|---|
| `src/teaching/pages/TeacherMonitorPage.tsx` | `teaching.ts`、`training.ts` | R3 |
| `src/teaching/pages/TeacherStudentsPage.tsx` | `teaching.ts`、`training.ts` | R3 |
| `src/teaching/pages/TeachingAssignmentsPage.tsx` | `task.ts`、`teaching.ts` | R3 |
| `src/teaching/pages/TeachingAttemptPage.tsx` | `client.ts`、`robots.ts`、`sop.ts`、`task.ts`、`teaching.ts` | R3 |
| `src/teaching/pages/TeachingDiagnosisPage.tsx` | `teaching.ts` | R3 |
| `src/teaching/pages/TeachingEvidencePage.tsx` | `teaching.ts` | R3 |

复现 `[R3]`：

```bash
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime/r-mos-frontend
node /tmp/rmos_s1_frontend_facts.cjs > /tmp/rmos_s1_frontend_facts.json
node - <<'JS'
const d=require('/tmp/rmos_s1_frontend_facts.json')
for (const p of [...d.pages,...d.teaching_pages_outside_requested_root]) console.log(p.page,p.api_modules,p.calls)
JS
```

## 3. 数据归属现状

运行期 ORM 元数据枚举出 **65 张业务表**。按指定直接字段口径，**23 张有字段，42 张没有**。AST 写入路径枚举结果为：**50 张有应用层写入者，15 张没有应用层写入者**。

| 表名 | 当前业务域 | 应用层写入者（endpoint/service） | 指定归属字段 | 应用写入路径 | 脚本写入者 | 复现 |
|---|---|---|---|---|---|---|
| `access_tokens` | 身份与会话 | `api/v1/endpoints/auth.py` | `user_id` | 有 | — | R4 |
| `agent_runtime_snapshots` | Agent 运行时 | — | — | 无 | — | R4 |
| `ai_knowledge_chunks` | 知识 | `services/knowledge/project_ingest_worker.py` | `owner_user_id` | 有 | — | R4 |
| `ai_tool_calls` | Agent 命令与审批 | `api/v1/endpoints/agent.py`、`services/approval_service.py` | — | 有 | — | R4 |
| `alignment_map` | 教学时间线 | — | — | 无 | — | R4 |
| `analysis_tasks` | 机器人资产分析 | `api/v1/endpoints/robots.py`、`services/analysis/scheduler.py` | — | 有 | — | R4 |
| `approval_records` | Agent 审批记录 | — | — | 无 | — | R4 |
| `approvals` | Agent 命令与审批 | `api/v1/endpoints/agent.py`、`services/approval_service.py` | `created_by_user_id` | 有 | — | R4 |
| `assessment_audit_events` | 外部评估 | `services/assessment_service.py` | — | 有 | — | R4 |
| `assessment_providers` | 外部评估 | `services/assessment_service.py` | `created_by_user_id`、`school_name` | 有 | — | R4 |
| `assignment_attempts` | 教学 | `services/evidence_engine.py`、`services/teaching_service.py` | — | 有 | `seed_demo_full.py`、`seed_teaching_diagnosis_cases.py` | R4 |
| `assignments` | 教学 | `services/teaching_service.py` | — | 有 | `seed_demo_full.py`、`seed_teaching_demo.py`、`seed_teaching_diagnosis_cases.py` | R4 |
| `audit_events` | 审计 | `api/v1/endpoints/admin.py`、`api/v1/endpoints/auth.py`、`api/v1/endpoints/training.py`、`services/audit_event_service.py`、`services/llm/audit.py` | — | 有 | — | R4 |
| `belief_state_records` | Agent 记忆 | `services/memory/long_term.py` | — | 有 | — | R4 |
| `classes` | 教学 | `services/teaching_service.py` | — | 有 | `seed_acceptance_users.py`、`seed_demo_full.py`、`seed_teaching_demo.py`、`seed_teaching_diagnosis_cases.py` | R4 |
| `commands` | Agent 命令与审批 | `api/v1/endpoints/agent.py`、`services/approval_service.py` | — | 有 | — | R4 |
| `conversation_turns` | Agent 记忆 | — | — | 无 | — | R4 |
| `courses` | 教学 | `services/teaching_service.py` | — | 有 | `seed_acceptance_users.py`、`seed_demo_full.py`、`seed_teaching_demo.py`、`seed_teaching_diagnosis_cases.py` | R4 |
| `decision_records` | Agent 回放 | — | — | 无 | — | R4 |
| `enrollments` | 教学 | `services/teaching_service.py` | — | 有 | `seed_acceptance_users.py`、`seed_demo_full.py`、`seed_teaching_demo.py` | R4 |
| `events` | 任务执行 | `services/event_service.py` | — | 有 | `seed_teaching_diagnosis_cases.py` | R4 |
| `evidence_bundles` | 证据 | `services/evidence_engine.py`、`services/evidence_service.py`、`services/teaching/report_generator.py` | `created_by_user_id`、`school_name` | 有 | `seed_teaching_diagnosis_cases.py` | R4 |
| `evidence_cards` | 教学证据 | `api/v1/endpoints/teaching_roster.py` | — | 有 | — | R4 |
| `evidence_items` | 证据 | `services/evidence_service.py`、`services/teaching/report_generator.py` | — | 有 | — | R4 |
| `evidence_links` | 教学证据 | `services/evidence_engine.py` | — | 有 | `seed_teaching_diagnosis_cases.py` | R4 |
| `external_assessments` | 外部评估 | `services/assessment_service.py` | `created_by_user_id`、`school_name` | 有 | — | R4 |
| `fault_cases` | 故障与诊断 | `services/fault_service.py` | `created_by_user_id`、`school_name` | 有 | `seed_data.py`、`seed_demo_full.py` | R4 |
| `fault_sop_mappings` | 故障与诊断 | — | — | 无 | `migrate_atom01.py`、`seed_demo_full.py`、`seed_fault_sops.py` | R4 |
| `guidance_policies` | 教学 | `services/teaching_service.py` | — | 有 | `seed_demo_full.py`、`seed_teaching_demo.py`、`seed_teaching_diagnosis_cases.py` | R4 |
| `incidents` | 故障与诊断 | `services/incident_service.py` | `created_by_user_id`、`school_name` | 有 | — | R4 |
| `knowledge_documents` | 知识 | `services/analysis/pdf_extractor.py` | — | 有 | `migrate_atom01.py`、`seed_knowledge.py` | R4 |
| `multimodal_timelines` | 教学时间线 | — | `created_by_user_id` | 无 | — | R4 |
| `observations` | 故障与诊断 | `services/observation_service.py` | `created_by_user_id`、`school_name` | 有 | — | R4 |
| `permissions` | 权限 | — | — | 无 | `seed_acceptance_users.py`、`seed_demo_full.py` | R4 |
| `refresh_tokens` | 身份与会话 | `api/v1/endpoints/auth.py` | `user_id` | 有 | — | R4 |
| `replay_checkpoints` | Agent 回放 | — | — | 无 | — | R4 |
| `robot_assets` | 机器人与资产 | `api/v1/endpoints/robots.py`、`services/analysis/assembly_builder.py`、`services/analysis/cad_converter.py`、`services/analysis/manifest_generator.py` | — | 有 | `migrate_atom01.py`、`seed_demo_full.py`、`seed_opensource_robots.py` | R4 |
| `robot_models` | 机器人与资产 | `api/v1/endpoints/robots.py`、`services/analysis/worker.py` | `owner_teacher_id` | 有 | `migrate_atom01.py`、`seed_demo_full.py`、`seed_opensource_robots.py` | R4 |
| `robot_part_manifests` | 机器人知识项目 | `services/knowledge/project_ingest_worker.py` | — | 有 | — | R4 |
| `robot_project_files` | 机器人知识项目 | `services/knowledge/project_ingest_service.py`、`services/knowledge/project_ingest_worker.py` | — | 有 | — | R4 |
| `robot_projects` | 机器人知识项目 | `services/knowledge/project_ingest_service.py`、`services/knowledge/project_ingest_worker.py` | — | 有 | — | R4 |
| `robot_sop_drafts` | 机器人维保草稿 | `api/v1/endpoints/maintenance.py` | `created_by_user_id`、`school_name` | 有 | — | R4 |
| `role_permissions` | 权限 | — | — | 无 | `seed_acceptance_users.py`、`seed_demo_full.py` | R4 |
| `roles` | 权限 | — | — | 无 | `seed_acceptance_users.py`、`seed_demo_full.py` | R4 |
| `schools` | 身份与学校 | — | — | 无 | `seed_schools.py` | R4 |
| `session_step_records` | 训练 | `services/training/session_service.py` | — | 有 | `seed_demo_full.py` | R4 |
| `skill_releases` | 技能注册 | `api/v1/endpoints/skills.py` | — | 有 | — | R4 |
| `skill_reviews` | 技能注册 | `api/v1/endpoints/skills.py` | — | 有 | — | R4 |
| `skills` | 技能注册 | `api/v1/endpoints/skills.py` | `created_by_user_id` | 有 | — | R4 |
| `snapshots` | 任务执行 | `services/snapshot_service.py` | — | 有 | `seed_teaching_diagnosis_cases.py` | R4 |
| `sop_audit_logs` | SOP 审计 | — | — | 无 | — | R4 |
| `sop_steps` | SOP | `services/analysis/sop_extractor.py`、`services/sop_service.py` | — | 有 | `seed_adjudication_sops.py`、`seed_data.py`、`seed_demo_full.py`、`seed_fault_sops.py`、`seed_teaching_demo.py`、`seed_teaching_diagnosis_cases.py` | R4 |
| `sops` | SOP | `services/analysis/sop_extractor.py`、`services/sop_service.py` | `created_by_user_id`、`school_name` | 有 | `migrate_atom01.py`、`seed_adjudication_sops.py`、`seed_data.py`、`seed_demo_full.py`、`seed_fault_sops.py`、`seed_teaching_demo.py`、`seed_teaching_diagnosis_cases.py` | R4 |
| `student_skill_profiles` | 训练画像 | `services/memory/skill_profile_service.py` | `user_id` | 有 | `seed_demo_full.py` | R4 |
| `student_weak_steps` | 训练画像 | `services/memory/skill_profile_service.py` | `user_id` | 有 | `seed_demo_full.py` | R4 |
| `task_executions` | 任务流水线 | `services/pipeline/task_pipeline_service.py` | — | 有 | — | R4 |
| `task_step_results` | 任务流水线 | `services/pipeline/task_pipeline_service.py` | — | 有 | — | R4 |
| `tasks` | 任务执行 | `services/pipeline/task_pipeline_service.py`、`services/task_service.py` | `user_id` | 有 | `seed_demo_full.py`、`seed_teaching_demo.py`、`seed_teaching_diagnosis_cases.py` | R4 |
| `teacher_robot_bindings` | 机器人与资产 | `api/v1/endpoints/onboarding.py`、`api/v1/endpoints/robots.py` | — | 有 | `seed_demo_full.py` | R4 |
| `timeline_segments` | 教学时间线 | — | — | 无 | — | R4 |
| `training_sessions` | 训练 | `services/memory/training_memory_writer.py`、`services/training/session_service.py`、`services/training/submission_service.py` | `user_id` | 有 | `seed_demo_full.py` | R4 |
| `training_submissions` | 训练 | `services/training/feedback_generator.py`、`services/training/submission_service.py` | `user_id` | 有 | `seed_demo_full.py` | R4 |
| `user_preferences` | 身份与用户 | `services/user_preference_service.py` | `user_id` | 有 | `seed_demo_full.py` | R4 |
| `user_roles` | 权限 | — | `user_id` | 无 | `seed_acceptance_users.py`、`seed_demo_full.py` | R4 |
| `users` | 身份与用户 | `api/v1/endpoints/admin.py`、`api/v1/endpoints/auth.py`、`api/v1/endpoints/onboarding.py` | `school_name` | 有 | `seed_acceptance_users.py`、`seed_demo_full.py` | R4 |

无应用层写入路径的 15 张中，**9 张同时没有脚本写入者**：`agent_runtime_snapshots`、`alignment_map`、`approval_records`、`conversation_turns`、`decision_records`、`multimodal_timelines`、`replay_checkpoints`、`sop_audit_logs`、`timeline_segments`。

其余 **6 张只有脚本写入者**：`fault_sop_mappings`、`permissions`、`role_permissions`、`roles`、`schools`、`user_roles`。

复现 `[R4]`：

```bash
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime/r-mos-backend
$PY /tmp/rmos_s1_facts.py > /tmp/rmos_s1_facts.json
$PY - <<'PY'
import json
d=json.load(open('/tmp/rmos_s1_facts.json'))
print('tables', len(d['tables']))
for t in d['tables']: print(t['table'], t['ownership_fields'], t['application_writers'], t['script_writers'])
print('no_application_writer', d['no_application_writer_count'], d['no_application_writers'])
PY
rg -ni '\binsert\s+into\b|text\([^)]*insert|exec_driver_sql\([^)]*insert' app
```

## 4. 跨模块耦合事实

### 4.1 循环依赖

`app/**/*.py` 共 **229 个模块、636 条内部 import 边**。强连通分量中 size > 1 的循环为 **1 组**：

- `app.services.llm.deepseek_provider` ↔ `app.services.llm.minimax_provider` ↔ `app.services.llm.router`

复现 `[R5]`：

```bash
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime/r-mos-backend
$PY /tmp/rmos_s1_facts.py > /tmp/rmos_s1_facts.json
$PY - <<'PY'
import json
d=json.load(open('/tmp/rmos_s1_facts.json'))
print(d['internal_module_count'], d['internal_edge_count'], d['cycles'])
PY
```

### 4.2 进程内可变状态单例

下表只列源码可证实会跨调用修改、且没有在同一实现中写入数据库/外部持久层的状态。`重启后状态` 是根据模块级实例重新构造和无持久化调用得出的静态事实；本任务没有实际杀进程。

| 单例 | 模块 | 进程内状态 | 当前调用入口/用途 | 重启后状态 | 复现 |
|---|---|---|---|---|---|
| `orchestrator` | `services/agent_service.py` | `task_state`、`event_history`、`last_event_sequence` | `api.agent` 的任务上下文与事件 | 重新初始化为空/0 | R6 |
| `evidence_enforcer` | `services/evidence_enforcement.py` | `_evidence_requirements`、`_collected_evidence` | `api.agent_evidence` 的证据状态、收集与继续判定 | 重新初始化为空字典 | R6 |
| `login_throttle` | `services/login_throttle.py` | `_failures`、`_locked_until` | `api.auth` 登录失败计数与临时锁定 | 重新初始化为空字典 | R6 |
| `memory_hub` | `services/memory/hub.py + memory/short_term.py` | `short_term._fallback_store`（Redis 客户端不可用时） | 会话短期记忆 | fallback 内容重新初始化为空 | R6 |
| `multi_agent_coordinator` | `services/multi_agent_coordinator.py` | `agents`、`conflicts`、`task_state` | `api.agent` 的多 Agent 协调状态 | 重新初始化为空容器 | R6 |
| `orchestrator_v2` | `services/orchestrator_v2.py` | `_task_contexts`、`_event_history`、`_last_event_sequence`、`_trace_owner_user_ids`、`_budget_pools` | `api.agent` / `api.agent_v2` 的任务、trace、事件与预算 | 重新初始化为空/0 | R6 |
| `manager` | `services/websocket_manager.py` | `connections`、`_push_task`、`_heartbeat_task` | WebSocket 连接、心跳与推送任务 | 连接与任务不存在 | R6 |

另有运行期可变配置/缓存单例：`resource_parser`（缓存与存在性回调）、`intent_engine`（置信阈值）、`llm_router`（客户端缓存与 fallback 开关）、`llm_risk_scorer`（风险阈值）、`policy_matrix`（规则）、`analysis_worker`（运行标志）。这些状态也会随进程重建，但表中未把它们归为用户业务记录。`knowledge_governance` 有内存字典，同时会写本地 JSON，因此不列入“纯进程内且重启即丢”。

复现 `[R6]`：

```bash
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime/r-mos-backend
$PY /tmp/rmos_s1_facts.py > /tmp/rmos_s1_facts.json
$PY - <<'PY'
import json
d=json.load(open('/tmp/rmos_s1_facts.json'))
for x in d['mutable_singleton_candidates']: print(x)
PY
```

### 4.3 replay / metrics / evidence 的并存实现文件

| 能力组 | 当前实现/接口族 | 后端挂载状态 | 当前存储或计算来源 | 前端文件与实际调用状态 | 复现 |
|---|---|---|---|---|---|
| replay | `GET /api/v1/ai/replay/{trace_id}`（`api/v1/endpoints/ai_commands.py`） | 已挂载 | `audit_events` | `src/api/` 未找到该路径的调用节点 | R7 |
| replay | `GET /api/v1/teaching/attempts/{attempt_id}/replay`（`teaching_roster.py`） | 已挂载 | `multimodal_timelines`、`timeline_segments`、`alignment_map`、`evidence_cards` 查询 | `src/api/teaching.ts` 未定义 replay 调用 | R7 |
| replay | `GET /api/v1/agent/v2/trace/{trace_id}/events`（`agent_v2.py` → `orchestrator_v2.py`） | 已挂载 | 进程内 `_event_history` | `src/api/agent-v2.ts:219` 定义；`AgentWorkbenchPage.tsx` 实际调用 | R7 |
| replay | `src/api/agent-v2.ts` 的 `/agent/replay/*` 6 条调用 | 未找到对应挂载路由 | 前端只定义请求 | 当前页面未调用这 6 个导出函数 | R7 |
| metrics | `/api/v1/ai/replay/metrics/*` 2 条（`ai_commands.py`） | 已挂载 | `ai_tool_calls` 与 `audit_events` 即时计算 | `src/api/` 未找到这两条路径的调用节点 | R7 |
| metrics | `src/api/agent-v2.ts` 的 `/agent/metrics*` 6 条调用 | 未找到对应挂载路由 | 前端只定义请求 | `AdminDashboardPage.tsx` 实际调用 `getCurrentMetrics`、`getAcceptanceReports` | R7 |
| metrics | `src/api/adminConsole.ts` 的 `/agent/monitor/metrics*` 2 条调用 | 未找到对应挂载路由 | 前端只定义请求 | `AdminDashboardPage.tsx` 实际调用当前值与历史 | R7 |
| evidence | `evidence_bundles` + `evidence_items`（`evidence.py`、`evidence_service.py`、`evidence_engine.py`、`teaching/report_generator.py`） | 3 条证据包路由已挂载 | 数据库 | `src/api/teaching.ts` 通过 attempt evidence 间接读取；无通用 evidence-bundles API 文件 | R7 |
| evidence | `evidence_links` + attempt evidence（`teaching.py`、`teaching_roster.py`、`evidence_engine.py`） | attempt evidence 已挂载 | 数据库 | `src/api/teaching.ts:85` 实际调用 | R7 |
| evidence | `evidence_cards`（`timeline.py`、`teaching_roster.py`） | 创建路由已挂载 | 数据库 | `src/api/` 未找到 evidence_cards 调用 | R7 |
| evidence | `evidence_enforcer`（`evidence_enforcement.py`、`agent_evidence.py`） | 4 条路由已挂载 | 进程内字典 | `src/api/agent.ts` 定义 3 条调用；当前页面调用图未命中这 3 个函数 | R7 |
| evidence | 训练工作台证据（`training_workbench.py`、`workbench_execution_service.py`、`evidence_service.py`） | 上传路由已挂载 | 文件内容 + 数据库证据包 | `src/api/training.ts:271` 定义；当前 `src/pages/` 调用图未命中该函数 | R7 |

复现 `[R7]`：

```bash
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime/r-mos-backend
$PY - <<'PY'
import main
from fastapi.routing import APIRoute
for r in main.app.routes:
    if isinstance(r, APIRoute) and any(x in r.path for x in ('replay','metrics','evidence')):
        print(sorted(r.methods), r.path, r.endpoint.__module__, r.endpoint.__name__)
PY
cd ../r-mos-frontend
node /tmp/rmos_s1_frontend_facts.cjs > /tmp/rmos_s1_frontend_facts.json
node - <<'JS'
const d=require('/tmp/rmos_s1_frontend_facts.json')
for(const x of d.api_http_calls.filter(x=>/replay|metric|evidence|trace.*events/.test(x.url))) console.log(x)
JS
```

## 5. UNKNOWN／无法测量清单

| ID | 项目 | 状态 | 原因与边界 |
|---|---|---|---|
| U-01 | 各 service 在真实业务流量中的调用频次 | UNKNOWN | 本任务没有启动长驻服务、发送业务请求或接入流量追踪；本报告只证明静态可调用关系。 |
| U-02 | 15 张无应用写入表是否被仓库外程序写入 | UNKNOWN | 扫描范围是当前仓库 `app/` 与仓内脚本；外部 ETL、手工 SQL、其他仓库程序不在可见范围。 |
| U-03 | 没有指定直接归属字段的 42 张表是否可经外键完整推导归属 | UNKNOWN | 本报告按题目给定字段名做结构枚举；外键链的业务语义与所有访问路径的强制执行未在本任务中逐条运行。 |
| U-04 | 进程重启后的实际恢复结果 | NOT_RUN | 本任务不启动长驻服务，也没有执行杀进程/恢复实验；“重新初始化”来自构造函数和无持久化写入的 E1 证据。 |
| U-05 | 当前数据库中的表行数与空表数 | NOT_RUN | 任务要求表定义、写入者和归属字段，不要求数据库内容；给定说明也明确本任务不需要数据库测试，沙箱不能连接 `::1:5432`。 |
| U-06 | 反射、运行时动态 import 或 monkey patch 产生的额外 Python 调用边 | UNKNOWN | AST 只计源码可见 `Call` 与 import 图；运行时替换不在静态图中。 |

## 6. 本次取证执行结果

| 项目 | 实测结果 |
|---|---|
| 真实 HTTP 路由 | 端点目录 167 条；全应用 168 条 |
| WebSocket 路由 | 2 条 |
| service 组织 | 根目录 36 文件；16 子包；递归 115 模块文件 |
| 前端页面/API | `src/pages/` 19 页面；`src/api/` 21 文件；另有 `src/teaching/pages/` 6 页面 |
| ORM 业务表 | 65 张 |
| 指定直接归属字段 | 23 张有；42 张无 |
| 应用写入路径 | 50 张有；15 张无（9 张无应用/脚本写入，6 张仅脚本写入） |
| 循环依赖 | 1 组 |
| 仓库变更 | 只新增本报告；没有生产代码、测试、配置变更；没有 commit |

本节只汇总测量值，不构成 S1 目标架构或阶段通过判断。
