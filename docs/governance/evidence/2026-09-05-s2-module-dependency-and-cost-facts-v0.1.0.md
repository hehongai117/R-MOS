# RMOS-S2-001｜模块级依赖图与改造成本事实报告

- 版本：0.1.0
- 日期：2026-09-05
- 主干阶段：S2｜模块改造顺序
- 主干任务：`RMOS-S2-001（事实收集部分）`
- 证据等级：E1（当前源码、真实运行期路由注册表、ORM 元数据、AST 静态分析、pytest 用例收集）
- 源码事实基线：`cb00b293303ae9df61f9d496b37f1fdbf2a7e9f0`
- 取证工作区 HEAD：`aa6ef40cd8cc4e8caf6912ca8c5a0d89ad472eb0`
- 边界：只记录模块级事实，不给改造顺序、试点、处置或实施建议

> `cb00b293..aa6ef40c` 之间只有治理、证据和交接文档变化，`r-mos-backend/app` 与 `r-mos-backend/tests` 无变化。因此下述源码测量对应指定基线。

## 1. 口径与复现入口

### 1.1 统计口径

1. 文件范围为 `r-mos-backend/app/**/*.py`，共 229 个文件。按 S1-001 §2 的职责与数据归属、§3.1/§3.2 的归位规则映射；没有单一归属依据的文件列为 `UNKNOWN`。
2. 代码行数用 Python `tokenize` 统计含代码 token 的物理行，排除空白行、纯注释行及缩进/换行 token；模块 docstring 计入代码行。
3. 文件依赖边由 Python AST 的 `Import`/`ImportFrom` 节点解析。相同“引用文件→被引用文件”只计 1 条；只聚合两端均有确定模块且模块不同的边。
4. 模块依赖方向为“引用方模块→被引用方模块”。入度/出度均为不同模块数，不是文件边数。
5. 路由在给定环境中载入真实 `main:app`，只枚举 `fastapi.routing.APIRoute`；按运行期 `route.endpoint.__module__` 归到端点文件，再归到模块。WebSocket 路由不计入本指标。
6. 测试文件与用例数来自 `pytest --collect-only -q` 的实际收集结果。每个有用例的测试文件按主要被测对象唯一归类；跨模块或全局测试列为 `UNKNOWN`。参数化后的收集项按实际用例数计。
7. 表数严格使用 S1-001 §2.1 的目标态归属：62 张目标表；3 个支撑模块无自有业务表。
8. 三张待合并源表的“读取”检查只统计 `app/` 函数体 AST `Call` 节点中出现 ORM 类，或调用参数字符串中出现表名；只有 import 不算读取。

### 1.2 环境与临时取证程序

```bash
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime/r-mos-backend
set -a; . /Users/xuhehong/Desktop/r-mos/r-mos-backend/.env; set +a
unset CORS_ORIGINS
export DEBUG=true
PY=/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python
```

- `/tmp/rmos_s2_facts.py`：SHA-256 `8962a72e863eb712566ad8844da49593b8dbc04c9fea5f6ec9cbf4c284fa486d`
- `/tmp/rmos_s2_facts.json`：SHA-256 `68e06a2b4ae321d7797259a99332a945b7ec58b3fa4ef31893fbb3d1c4b11d66`
- `/tmp/rmos_s2_pytest_collect.txt`：pytest 收集原始输出

基线核对 `[R0]`：

```bash
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime
git rev-parse HEAD cb00b293
git diff --name-only cb00b293..HEAD -- r-mos-backend/app r-mos-backend/tests
git status --short
```

统一取证 `[R1]`：

```bash
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime/r-mos-backend
set -a; . /Users/xuhehong/Desktop/r-mos/r-mos-backend/.env; set +a
unset CORS_ORIGINS; export DEBUG=true
PY=/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python
$PY -m pytest --collect-only -q > /tmp/rmos_s2_pytest_collect.txt
$PY /tmp/rmos_s2_facts.py > /tmp/rmos_s2_facts.json
shasum -a 256 /tmp/rmos_s2_facts.py /tmp/rmos_s2_facts.json
```

## 2. 文件→模块映射

### 2.1 汇总

| 模块 | 文件数 | 模块 | 文件数 |
|---|---:|---|---:|
| A 身份与访问控制 | 28 | B 机器人资产 | 27 |
| C 知识 | 14 | D SOP 与维保 | 19 |
| E 任务执行 | 17 | F 教学 | 12 |
| G 训练 | 19 | H 证据与评估 | 19 |
| I Agent 运行时 | 28 | S1 LLM 接入 | 11 |
| S2 实时通道 | 7 | S3 仿真与诊断引擎 | 7 |
| **已归类合计** | **208** | **UNKNOWN** | **21** |
| **总计** | **229** |  |  |

复现 `[R2]`：

```bash
$PY - <<'PY'
import json, collections
d=json.load(open('/tmp/rmos_s2_facts.json'))
print(d['assignment_counts'])
for row in d['assignment_rows']:
    print(row['file'], row['module'] or 'UNKNOWN', row['code_lines'])
PY
```

### 2.2 完整映射

下列路径均相对于 `r-mos-backend/app/`。

#### A｜身份与访问控制（28）

`api/v1/endpoints/admin.py`、`api/v1/endpoints/audit.py`、`api/v1/endpoints/auth.py`、`api/v1/endpoints/schools.py`、`core/public_routes.py`、`core/resource_parser.py`、`core/security.py`、`models/access_token.py`、`models/audit_event.py`、`models/rbac.py`、`models/refresh_token.py`、`models/school.py`、`models/user.py`、`models/user_preference.py`、`schemas/auth.py`、`schemas/user.py`、`services/access_control.py`、`services/audit_event_service.py`、`services/authz_guard.py`、`services/identity/__init__.py`、`services/identity/agent_policy_factory.py`、`services/identity/class_membership.py`、`services/identity/session_initializer.py`、`services/identity/teacher_monitor.py`、`services/login_throttle.py`、`services/ownership.py`、`services/robot_visibility.py`、`services/user_preference_service.py`

#### B｜机器人资产（27）

`api/v1/endpoints/onboarding.py`、`api/v1/endpoints/robots.py`、`api/v1/endpoints/students.py`、`models/analysis_task.py`、`models/robot_asset.py`、`models/robot_model.py`、`models/robot_part_manifest.py`、`models/robot_project.py`、`models/robot_project_file.py`、`schemas/analysis_task.py`、`schemas/robot_model.py`、`schemas/robot_project.py`、`services/analysis/__init__.py`、`services/analysis/assembly_builder.py`、`services/analysis/cad_converter.py`、`services/analysis/fault_extractor.py`、`services/analysis/manifest_generator.py`、`services/analysis/pdf_extractor.py`、`services/analysis/scheduler.py`、`services/analysis/sop_extractor.py`、`services/analysis/urdf_parser.py`、`services/analysis/worker.py`、`services/robot_asset_validator.py`、`services/robot_service.py`、`services/storage/__init__.py`、`services/storage/file_storage.py`、`services/storage/s3_storage.py`

#### C｜知识（14）

`models/knowledge_chunk.py`、`models/knowledge_document.py`、`services/knowledge/__init__.py`、`services/knowledge/document_chunker.py`、`services/knowledge/embedding.py`、`services/knowledge/fallback_embedding.py`、`services/knowledge/file_classifier.py`、`services/knowledge/format_support_matrix.py`、`services/knowledge/hub.py`、`services/knowledge/knowledge_retriever.py`、`services/knowledge/project_ingest_service.py`、`services/knowledge/project_ingest_worker.py`、`services/knowledge/query_embedding_service.py`、`services/knowledge/robot_manifest_builder.py`

#### D｜SOP 与维保（19）

`api/v1/endpoints/fault_cases.py`、`api/v1/endpoints/maintenance.py`、`api/v1/endpoints/sops.py`、`models/audit_log.py`、`models/fault.py`、`models/fault_sop_mapping.py`、`models/robot_sop_draft.py`、`models/sop.py`、`schemas/fault.py`、`schemas/maintenance.py`、`schemas/sop.py`、`services/fault_service.py`、`services/maintenance/__init__.py`、`services/maintenance/sop_draft_generator.py`、`services/maintenance/verdict_step_generator.py`、`services/sop/__init__.py`、`services/sop/quality_monitor.py`、`services/sop/verdict_enhancer.py`、`services/sop_service.py`

#### E｜任务执行（17）

`api/v1/endpoints/pipeline.py`、`api/v1/endpoints/student_tasks.py`、`api/v1/endpoints/tasks.py`、`models/event.py`、`models/snapshot.py`、`models/task.py`、`models/task_execution.py`、`schemas/report.py`、`schemas/task.py`、`services/event_service.py`、`services/pipeline/__init__.py`、`services/pipeline/fault_diagnosis_service.py`、`services/pipeline/task_pipeline_service.py`、`services/preflight_check.py`、`services/scoring_service.py`、`services/snapshot_service.py`、`services/task_service.py`

#### F｜教学（12）

`api/v1/endpoints/teaching.py`、`api/v1/endpoints/teaching_common.py`、`api/v1/endpoints/teaching_roster.py`、`models/teaching.py`、`models/timeline.py`、`schemas/teaching.py`、`services/diagnosis_service.py`、`services/teaching/__init__.py`、`services/teaching/chat_engine.py`、`services/teaching/group_stats.py`、`services/teaching/report_generator.py`、`services/teaching_service.py`

#### G｜训练（19）

`api/v1/endpoints/training.py`、`api/v1/endpoints/training_workbench.py`、`models/skill_profile.py`、`models/training.py`、`models/training_submission.py`、`schemas/training_workbench.py`、`services/memory/__init__.py`、`services/memory/hub.py`、`services/memory/long_term.py`、`services/memory/short_term.py`、`services/memory/skill_profile_service.py`、`services/memory/training_memory_writer.py`、`services/training/__init__.py`、`services/training/feedback_generator.py`、`services/training/project_generator.py`、`services/training/session_service.py`、`services/training/submission_service.py`、`services/training/workbench_draft_generator.py`、`services/training/workbench_execution_service.py`

#### H｜证据与评估（19）

`api/v1/endpoints/agent_evidence.py`、`api/v1/endpoints/assessments.py`、`api/v1/endpoints/evidence.py`、`api/v1/endpoints/incidents.py`、`api/v1/endpoints/observations.py`、`models/assessment.py`、`models/evidence.py`、`models/incident.py`、`models/observation.py`、`schemas/assessment.py`、`schemas/evidence.py`、`schemas/incident.py`、`schemas/observation.py`、`services/assessment_service.py`、`services/evidence_enforcement.py`、`services/evidence_engine.py`、`services/evidence_service.py`、`services/incident_service.py`、`services/observation_service.py`

#### I｜Agent 运行时（28）

`api/v1/endpoints/agent.py`、`api/v1/endpoints/agent_v2.py`、`api/v1/endpoints/ai_commands.py`、`api/v1/endpoints/approvals.py`、`api/v1/endpoints/skills.py`、`models/approval.py`、`models/command_runtime.py`、`models/conversation.py`、`models/skill_registry.py`、`schemas/agent.py`、`services/agent_service.py`、`services/approval_service.py`、`services/coach_agent.py`、`services/diagnoser_agent.py`、`services/intent/__init__.py`、`services/intent/engine.py`、`services/intent/training_intent_router.py`、`services/knowledge_governance.py`、`services/multi_agent_coordinator.py`、`services/orchestration/__init__.py`、`services/orchestration/fsm.py`、`services/orchestration/idempotency.py`、`services/orchestration/module_registry.py`、`services/orchestrator_v2.py`、`services/policy/__init__.py`、`services/policy/risk_scorer.py`、`services/policy_matrix.py`、`services/tool_executor.py`

#### S1｜LLM 接入（11）

`api/v1/endpoints/ai_assistant.py`、`api/v1/endpoints/llm_health.py`、`services/ai_assistant_service.py`、`services/llm/__init__.py`、`services/llm/audit.py`、`services/llm/deepseek_provider.py`、`services/llm/minimax_provider.py`、`services/llm/mock_provider.py`、`services/llm/prompts.py`、`services/llm/router.py`、`services/llm/telemetry_context_builder.py`

#### S2｜实时通道（7）

`adapters/__init__.py`、`adapters/base.py`、`adapters/factory.py`、`adapters/mock.py`、`adapters/schemas.py`、`api/v1/endpoints/websocket.py`、`services/websocket_manager.py`

#### S3｜仿真与诊断引擎（7）

`api/v1/endpoints/scenarios.py`、`services/diagnosis/fault_diagnosis_engine.py`、`services/diagnosis/maintenance_plan_generator.py`、`services/diagnosis/schemas.py`、`services/simulation/__init__.py`、`services/simulation/fault_scenarios.py`、`services/simulation/simulation_executor.py`

### 2.3 不确定文件（21）

| 文件（相对 `app/`） | 代码行 | 不确定原因 |
|---|---:|---|
| `__init__.py` | 3 | 应用包初始化，不承载单一模块职责 |
| `api/__init__.py` | 3 | API 分层包初始化，不承载单一模块职责 |
| `api/v1/__init__.py` | 63 | 聚合全部 API 路由，无法唯一归属 |
| `api/v1/endpoints/__init__.py` | 3 | 端点包初始化，不承载单一模块职责 |
| `api/v1/endpoints/agent_governance.py` | 148 | 同文件同时提供 SOP 质量、教学报告、用户偏好等跨模块入口 |
| `api/v1/endpoints/agent_knowledge.py` | 191 | 同文件同时提供知识治理与机器人项目导入入口，跨 C/B/I |
| `api/v1/endpoints/health.py` | 70 | 全应用健康检查，不属于 S1 定义的任一单一模块 |
| `core/__init__.py` | 3 | 通用核心包初始化，不承载单一模块职责 |
| `core/config.py` | 68 | 全应用配置基础设施，不属于 12 个模块中的单一模块 |
| `core/database.py` | 66 | 全应用数据库基础设施，不属于 12 个模块中的单一模块 |
| `core/enums.py` | 28 | 跨模块共享枚举，无法唯一归属 |
| `core/exceptions.py` | 173 | 跨模块共享异常，无法唯一归属 |
| `core/logging.py` | 60 | 全应用日志基础设施，不属于 12 个模块中的单一模块 |
| `core/migration_contract.py` | 43 | 全应用迁移契约检查，不属于单一业务或支撑模块 |
| `core/timing_middleware.py` | 44 | 全应用计时中间件，不属于单一模块 |
| `main.py` | 3 | app 内的应用转发入口，不属于单一模块 |
| `models/__init__.py` | 138 | 聚合全部模块 ORM 模型，无法唯一归属 |
| `models/agent_runtime.py` | 95 | 同文件含 I 的运行态模型和目标归 A 的 decision_records，无法按目标态唯一归属 |
| `models/base.py` | 42 | 全部 ORM 模型共享基类，不属于单一模块 |
| `schemas/__init__.py` | 45 | 跨模块 schema 聚合入口，无法唯一归属 |
| `services/__init__.py` | 3 | 服务聚合包初始化，不承载单一模块职责 |

## 3. 模块级依赖图

### 3.1 依赖矩阵

单元格为唯一“引用文件→被引用文件”边数；行是引用方，列是被引用方。模块内部边未列入跨模块成本。

| 引用方 \ 被引用方 | A | B | C | D | E | F | G | H | I | S1 | S2 | S3 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A | — | 1 | 0 | 0 | 3 | 2 | 2 | 0 | 0 | 0 | 1 | 0 |
| B | 6 | — | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 |
| C | 0 | 10 | — | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| D | 6 | 3 | 2 | — | 2 | 1 | 0 | 0 | 0 | 1 | 0 | 0 |
| E | 5 | 0 | 0 | 6 | — | 0 | 0 | 2 | 0 | 1 | 1 | 1 |
| F | 7 | 0 | 0 | 1 | 10 | — | 0 | 5 | 0 | 2 | 0 | 0 |
| G | 9 | 1 | 2 | 0 | 0 | 0 | — | 2 | 1 | 4 | 0 | 0 |
| H | 6 | 0 | 0 | 0 | 3 | 1 | 0 | — | 1 | 0 | 0 | 0 |
| I | 14 | 0 | 1 | 0 | 1 | 0 | 0 | 1 | — | 5 | 1 | 3 |
| S1 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | — | 1 | 1 |
| S2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — | 1 |
| S3 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 5 | 1 | — |

原始内部文件依赖边共 636 条。两端均可归类且跨模块的边共 159 条，形成 53 个非零模块方向。另有 121 条边指向不确定文件、95 条边由不确定文件发出；这些边没有强行聚合进模块矩阵。

复现 `[R3]`：

```bash
$PY - <<'PY'
import json
d=json.load(open('/tmp/rmos_s2_facts.json'))
print(d['file_import_edge_count'], d['cross_module_edge_count'], d['excluded_import_edges'])
for source, row in d['dependency_matrix'].items(): print(source, row)
PY
```

### 3.2 每个依赖方向的文件样例

每行最多列前 5 条；不足 5 条时列全部。完整边集保存在统一取证 JSON 的 `dependency_edges[].all_edges`。

| 方向 | 边数 | 文件引用样例（引用方→被引用方） |
|---|---:|---|
| A→B | 1 | `services/robot_visibility.py` → `models/robot_model.py` |
| A→E | 3 | `api/v1/endpoints/admin.py` → `models/event.py`；`services/identity/session_initializer.py` → `models/task.py`；`services/ownership.py` → `models/task.py` |
| A→F | 2 | `services/identity/class_membership.py` → `models/teaching.py`；`services/identity/session_initializer.py` → `models/teaching.py` |
| A→G | 2 | `services/identity/session_initializer.py` → `models/training.py`；`services/identity/session_initializer.py` → `services/memory/hub.py` |
| A→S2 | 1 | `services/identity/teacher_monitor.py` → `services/websocket_manager.py` |
| B→A | 6 | `api/v1/endpoints/onboarding.py` → `models/user.py`；`api/v1/endpoints/onboarding.py` → `services/authz_guard.py`；`api/v1/endpoints/robots.py` → `services/authz_guard.py`；`api/v1/endpoints/robots.py` → `services/robot_visibility.py`；`api/v1/endpoints/students.py` → `models/user.py` |
| B→C | 4 | `api/v1/endpoints/robots.py` → `services/knowledge/project_ingest_service.py`；`services/analysis/fault_extractor.py` → `models/knowledge_document.py`；`services/analysis/pdf_extractor.py` → `models/knowledge_document.py`；`services/analysis/sop_extractor.py` → `models/knowledge_document.py` |
| B→D | 1 | `services/analysis/sop_extractor.py` → `models/sop.py` |
| B→S1 | 2 | `services/analysis/fault_extractor.py` → `services/llm/router.py`；`services/analysis/sop_extractor.py` → `services/llm/router.py` |
| C→B | 10 | `services/knowledge/document_chunker.py` → `models/robot_project.py`；`services/knowledge/project_ingest_service.py` → `models/robot_part_manifest.py`；`services/knowledge/project_ingest_service.py` → `models/robot_project.py`；`services/knowledge/project_ingest_service.py` → `models/robot_project_file.py`；`services/knowledge/project_ingest_service.py` → `schemas/robot_project.py` |
| D→A | 6 | `api/v1/endpoints/fault_cases.py` → `services/authz_guard.py`；`api/v1/endpoints/fault_cases.py` → `services/ownership.py`；`api/v1/endpoints/maintenance.py` → `services/authz_guard.py`；`api/v1/endpoints/maintenance.py` → `services/ownership.py`；`api/v1/endpoints/sops.py` → `services/authz_guard.py` |
| D→B | 3 | `api/v1/endpoints/maintenance.py` → `models/robot_project.py`；`services/maintenance/sop_draft_generator.py` → `models/robot_part_manifest.py`；`services/maintenance/sop_draft_generator.py` → `models/robot_project.py` |
| D→C | 2 | `services/maintenance/sop_draft_generator.py` → `services/knowledge/hub.py`；`services/maintenance/sop_draft_generator.py` → `services/knowledge/query_embedding_service.py` |
| D→E | 2 | `services/sop/quality_monitor.py` → `models/event.py`；`services/sop_service.py` → `models/task.py` |
| D→F | 1 | `services/sop/quality_monitor.py` → `models/teaching.py` |
| D→S1 | 1 | `services/sop/verdict_enhancer.py` → `services/llm/__init__.py` |
| E→A | 5 | `api/v1/endpoints/pipeline.py` → `services/authz_guard.py`；`api/v1/endpoints/pipeline.py` → `services/ownership.py`；`api/v1/endpoints/tasks.py` → `services/authz_guard.py`；`api/v1/endpoints/tasks.py` → `services/ownership.py`；`services/preflight_check.py` → `models/user.py` |
| E→D | 6 | `api/v1/endpoints/student_tasks.py` → `models/sop.py`；`services/pipeline/task_pipeline_service.py` → `models/fault_sop_mapping.py`；`services/pipeline/task_pipeline_service.py` → `models/sop.py`；`services/preflight_check.py` → `models/sop.py`；`services/scoring_service.py` → `models/sop.py` |
| E→H | 2 | `services/preflight_check.py` → `models/incident.py`；`services/task_service.py` → `services/evidence_engine.py` |
| E→S1 | 1 | `services/pipeline/fault_diagnosis_service.py` → `services/llm/router.py` |
| E→S2 | 1 | `services/snapshot_service.py` → `adapters/factory.py` |
| E→S3 | 1 | `services/pipeline/fault_diagnosis_service.py` → `services/simulation/fault_scenarios.py` |
| F→A | 7 | `api/v1/endpoints/teaching.py` → `services/authz_guard.py`；`api/v1/endpoints/teaching.py` → `services/ownership.py`；`api/v1/endpoints/teaching_roster.py` → `services/access_control.py`；`api/v1/endpoints/teaching_roster.py` → `services/authz_guard.py`；`api/v1/endpoints/teaching_roster.py` → `services/ownership.py` |
| F→D | 1 | `services/teaching/report_generator.py` → `models/sop.py` |
| F→E | 10 | `services/diagnosis_service.py` → `models/event.py`；`services/diagnosis_service.py` → `models/task.py`；`services/diagnosis_service.py` → `services/event_service.py`；`services/diagnosis_service.py` → `services/scoring_service.py`；`services/diagnosis_service.py` → `services/task_service.py` |
| F→H | 5 | `api/v1/endpoints/teaching_roster.py` → `models/evidence.py`；`api/v1/endpoints/teaching_roster.py` → `services/evidence_engine.py`；`services/diagnosis_service.py` → `models/evidence.py`；`services/diagnosis_service.py` → `services/evidence_engine.py`；`services/teaching/report_generator.py` → `models/evidence.py` |
| F→S1 | 2 | `services/teaching/chat_engine.py` → `services/llm/__init__.py`；`services/teaching/report_generator.py` → `services/llm/router.py` |
| G→A | 9 | `api/v1/endpoints/training.py` → `models/audit_event.py`；`api/v1/endpoints/training.py` → `services/access_control.py`；`api/v1/endpoints/training.py` → `services/authz_guard.py`；`api/v1/endpoints/training.py` → `services/identity/class_membership.py`；`api/v1/endpoints/training.py` → `services/ownership.py` |
| G→B | 1 | `services/training/workbench_draft_generator.py` → `services/storage/__init__.py` |
| G→C | 2 | `services/training/project_generator.py` → `services/knowledge/hub.py`；`services/training/project_generator.py` → `services/knowledge/query_embedding_service.py` |
| G→H | 2 | `services/training/workbench_execution_service.py` → `schemas/evidence.py`；`services/training/workbench_execution_service.py` → `services/evidence_service.py` |
| G→I | 1 | `services/memory/training_memory_writer.py` → `models/conversation.py` |
| G→S1 | 4 | `services/memory/training_memory_writer.py` → `services/llm/router.py`；`services/training/project_generator.py` → `services/llm/__init__.py`；`services/training/workbench_draft_generator.py` → `services/llm/__init__.py`；`services/training/workbench_execution_service.py` → `services/llm/__init__.py` |
| H→A | 6 | `api/v1/endpoints/agent_evidence.py` → `services/authz_guard.py`；`api/v1/endpoints/assessments.py` → `services/authz_guard.py`；`api/v1/endpoints/assessments.py` → `services/ownership.py`；`api/v1/endpoints/evidence.py` → `services/authz_guard.py`；`api/v1/endpoints/incidents.py` → `services/authz_guard.py` |
| H→E | 3 | `services/evidence_engine.py` → `models/event.py`；`services/evidence_engine.py` → `models/snapshot.py`；`services/evidence_engine.py` → `models/task.py` |
| H→F | 1 | `services/evidence_engine.py` → `models/teaching.py` |
| H→I | 1 | `api/v1/endpoints/agent_evidence.py` → `schemas/agent.py` |
| I→A | 14 | `api/v1/endpoints/agent.py` → `services/access_control.py`；`api/v1/endpoints/agent.py` → `services/authz_guard.py`；`api/v1/endpoints/agent_v2.py` → `services/access_control.py`；`api/v1/endpoints/agent_v2.py` → `services/authz_guard.py`；`api/v1/endpoints/agent_v2.py` → `services/ownership.py` |
| I→C | 1 | `api/v1/endpoints/ai_commands.py` → `models/knowledge_chunk.py` |
| I→E | 1 | `schemas/agent.py` → `schemas/report.py` |
| I→H | 1 | `api/v1/endpoints/agent.py` → `api/v1/endpoints/agent_evidence.py` |
| I→S1 | 5 | `services/intent/engine.py` → `services/llm/__init__.py`；`services/orchestrator_v2.py` → `services/llm/router.py`；`services/orchestrator_v2.py` → `services/llm/telemetry_context_builder.py`；`services/policy/risk_scorer.py` → `services/llm/__init__.py`；`services/policy/risk_scorer.py` → `services/llm/prompts.py` |
| I→S2 | 1 | `services/orchestrator_v2.py` → `adapters/factory.py` |
| I→S3 | 3 | `services/orchestrator_v2.py` → `services/diagnosis/fault_diagnosis_engine.py`；`services/orchestrator_v2.py` → `services/diagnosis/maintenance_plan_generator.py`；`services/orchestrator_v2.py` → `services/simulation/simulation_executor.py` |
| S1→A | 1 | `services/llm/audit.py` → `models/audit_event.py` |
| S1→C | 1 | `services/ai_assistant_service.py` → `models/knowledge_document.py` |
| S1→S2 | 1 | `services/llm/telemetry_context_builder.py` → `adapters/schemas.py` |
| S1→S3 | 1 | `services/llm/mock_provider.py` → `services/simulation/fault_scenarios.py` |
| S2→A | 2 | `api/v1/endpoints/websocket.py` → `services/authz_guard.py`；`api/v1/endpoints/websocket.py` → `services/robot_visibility.py` |
| S2→S3 | 1 | `adapters/mock.py` → `services/simulation/fault_scenarios.py` |
| S3→D | 2 | `api/v1/endpoints/scenarios.py` → `models/fault_sop_mapping.py`；`api/v1/endpoints/scenarios.py` → `models/sop.py` |
| S3→S1 | 5 | `services/diagnosis/fault_diagnosis_engine.py` → `services/llm/prompts.py`；`services/diagnosis/fault_diagnosis_engine.py` → `services/llm/router.py`；`services/diagnosis/fault_diagnosis_engine.py` → `services/llm/telemetry_context_builder.py`；`services/diagnosis/maintenance_plan_generator.py` → `services/llm/prompts.py`；`services/diagnosis/maintenance_plan_generator.py` → `services/llm/router.py` |
| S3→S2 | 1 | `services/simulation/simulation_executor.py` → `adapters/mock.py` |

### 3.3 双向依赖清单

| 模块对 | 正向边 | 反向边 |
|---|---:|---:|
| A ↔ B | A→B 1 | B→A 6 |
| A ↔ E | A→E 3 | E→A 5 |
| A ↔ F | A→F 2 | F→A 7 |
| A ↔ G | A→G 2 | G→A 9 |
| A ↔ S2 | A→S2 1 | S2→A 2 |
| B ↔ C | B→C 4 | C→B 10 |
| B ↔ D | B→D 1 | D→B 3 |
| D ↔ E | D→E 2 | E→D 6 |
| D ↔ F | D→F 1 | F→D 1 |
| E ↔ H | E→H 2 | H→E 3 |
| F ↔ H | F→H 5 | H→F 1 |
| H ↔ I | H→I 1 | I→H 1 |
| S1 ↔ S3 | S1→S3 1 | S3→S1 5 |
| S2 ↔ S3 | S2→S3 1 | S3→S2 1 |

### 3.4 三个及以上模块的循环清单

12 个模块构成 1 个强连通组：`A、B、C、D、E、F、G、H、I、S1、S2、S3`。按“节点不重复、仅旋转去重、方向不同不合并”的简单有向环口径，共 1,934 个三模块以上环：

| 环长度 | 数量 |
|---:|---:|
| 3 | 22 |
| 4 | 45 |
| 5 | 94 |
| 6 | 170 |
| 7 | 278 |
| 8 | 368 |
| 9 | 404 |
| 10 | 319 |
| 11 | 182 |
| 12 | 52 |
| **合计** | **1,934** |

最短的 22 个三模块环如下；更长环由同一强连通组和矩阵确定，完整规范化枚举保存在统一取证 JSON 的 `cycles_3plus`：

1. A→B→D→A
2. A→B→S1→A
3. A→E→D→A
4. A→E→H→A
5. A→E→S1→A
6. A→E→S2→A
7. A→F→D→A
8. A→F→E→A
9. A→F→H→A
10. A→F→S1→A
11. A→G→B→A
12. A→G→H→A
13. A→G→I→A
14. A→G→S1→A
15. B→D→C→B
16. B→S1→C→B
17. D→E→S3→D
18. D→F→E→D
19. D→S1→S3→D
20. E→H→F→E
21. E→H→I→E
22. S1→S2→S3→S1

复现 `[R4]`：

```bash
$PY - <<'PY'
import json, collections
d=json.load(open('/tmp/rmos_s2_facts.json'))
print(d['bidirectional'])
print(collections.Counter(map(len, d['cycles_3plus'])))
for cycle in d['cycles_3plus']: print(' -> '.join(cycle + [cycle[0]]))
PY
```

## 4. 每模块改造成本指标

| 模块 | 文件数 | 代码行 | 目标表数 | APIRoute 数 | 测试文件数 | 测试用例数 | 入度 | 出度 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A 身份与访问控制 | 28 | 2,710 | 10 | 9 | 21 | 260 | 9 | 5 |
| B 机器人资产 | 27 | 2,505 | 7 | 19 | 23 | 182 | 4 | 4 |
| C 知识 | 14 | 1,382 | 2 | 0 | 9 | 21 | 5 | 1 |
| D SOP 与维保 | 19 | 2,062 | 6 | 18 | 6 | 29 | 4 | 6 |
| E 任务执行 | 17 | 2,169 | 5 | 14 | 7 | 42 | 5 | 6 |
| F 教学 | 12 | 2,720 | 11 | 24 | 11 | 96 | 3 | 5 |
| G 训练 | 19 | 4,383 | 5 | 20 | 16 | 87 | 1 | 6 |
| H 证据与评估 | 19 | 1,927 | 7 | 24 | 1 | 3 | 4 | 4 |
| I Agent 运行时 | 28 | 5,122 | 9 | 21 | 12 | 106 | 2 | 7 |
| S1 LLM 接入 | 11 | 1,580 | 0 | 2 | 6 | 47 | 7 | 4 |
| S2 实时通道 | 7 | 1,218 | 0 | 0 | 4 | 41 | 5 | 2 |
| S3 仿真与诊断引擎 | 7 | 1,257 | 0 | 1 | 4 | 28 | 4 | 3 |
| **可归类合计** | **208** | **29,035** | **62** | **152** | **120** | **942** | — | — |
| **UNKNOWN** | **21** | **1,292** | — | **16** | **11** | **53** | — | — |
| **总计** | **229** | **30,327** | **62** | **168** | **131** | **995** | — | — |

目标表清单按 S1-001 §2.1：A 10 张、B 7 张、C 2 张、D 6 张、E 5 张、F 11 张、G 5 张、H 7 张、I 9 张；S1/S2/S3 为 0。

真实路由载入共 168 条 `APIRoute`。UNKNOWN 的 16 条为：`main.root` 1 条、`health.py` 1 条、跨模块 `agent_knowledge.py` 9 条、跨模块 `agent_governance.py` 5 条。真实应用另注册 2 条 WebSocket 路由，按本任务硬口径未计入 `APIRoute` 指标。

测试收集共 131 个文件、995 个用例；可归类 120 个文件、942 个用例。UNKNOWN 的 11 个文件、53 个用例见 §6。

复现 `[R5]`：

```bash
$PY - <<'PY'
import json
d=json.load(open('/tmp/rmos_s2_facts.json'))
for m, x in d['cost'].items():
    print(m, x['file_count'], x['code_lines'], x['target_table_count'],
          x['route_count'], x['test_file_count'], x['test_case_count'],
          x['indegree'], x['outdegree'])
print('unknown routes', d['unknown_routes'])
print('unknown tests', d['unknown_tests'])
PY
```

## 5. S1 三项并表裁决的当前落地面

### 5.1 ORM 定义位置与字段

| 表 | ORM 定义 | 当前字段（类型；可空性） |
|---|---|---|
| `approval_records` | `app/models/agent_runtime.py:91`，`ApprovalRecordDB` | `id VARCHAR(64) PK`；`trace_id VARCHAR(64) NOT NULL`；`decision_id VARCHAR(64) NULL`；`priority VARCHAR(20) NOT NULL`；`status VARCHAR(20) NOT NULL`；`request_data JSON NULL`；`decision_data JSON NULL`；`requested_by VARCHAR(64) NOT NULL`；`requested_at DATETIME NOT NULL`；`resolved_by VARCHAR(64) NULL`；`resolved_at DATETIME NULL`；`resolution_note TEXT NULL` |
| `approvals` | `app/models/approval.py:9`，`Approval` | `id INTEGER PK`；`trace_id VARCHAR(64) NOT NULL`；`command_id INTEGER NOT NULL`；`tool_call_id INTEGER NOT NULL`；`status VARCHAR(32) NOT NULL`；`reason VARCHAR(256) NULL`；`created_by_user_id VARCHAR(64) NULL`；`decided_by_user_id VARCHAR(64) NULL`；`decided_at DATETIME NULL`；`created_at DATETIME NOT NULL`；`updated_at DATETIME NOT NULL` |
| `decision_records` | `app/models/agent_runtime.py:63`，`DecisionRecordDB` | `id VARCHAR(64) PK`；`trace_id VARCHAR(64) NOT NULL`；`decision_type VARCHAR(50) NOT NULL`；`decision_data JSON NOT NULL`；`input_context JSON NULL`；`output_result JSON NULL`；`risk_level VARCHAR(10) NOT NULL`；`risk_score FLOAT NOT NULL`；`requires_approval BOOLEAN NULL`；`approval_level VARCHAR(20) NULL`；`approved_by VARCHAR(64) NULL`；`approved_at DATETIME NULL`；`created_at DATETIME NOT NULL` |
| `audit_events` | `app/models/audit_event.py:15`，`AuditEvent` | `id INTEGER PK`；`actor_user_id VARCHAR(64) NULL`；`action VARCHAR(64) NOT NULL`；`resource_type VARCHAR(64) NULL`；`resource_id VARCHAR(128) NULL`；`decision VARCHAR(16) NOT NULL`；`reason VARCHAR(256) NULL`；`request_meta JSON NULL`；`trace_id VARCHAR(64) NULL`；`skill_id VARCHAR(128) NULL`；`skill_version VARCHAR(32) NULL`；`tool_call_args JSON NULL`；`side_effects_applied JSON NULL`；`approval_id INTEGER NULL FK approvals.id`；`prompt_hash VARCHAR(64) NULL`；`response_hash VARCHAR(64) NULL`；`provider VARCHAR(32) NULL`；`model VARCHAR(64) NULL`；`tokens_in INTEGER NULL`；`tokens_out INTEGER NULL`；`created_at DATETIME NOT NULL` |
| `replay_checkpoints` | `app/models/agent_runtime.py:116`，`ReplayCheckpoint` | `id VARCHAR(64) PK`；`trace_id VARCHAR(64) NOT NULL`；`checkpoint_name VARCHAR(100) NOT NULL`；`sequence_number INTEGER NULL`；`belief_state_snapshot JSON NULL`；`decision_snapshot JSON NULL`；`evidence_snapshot JSON NULL`；`created_at DATETIME NOT NULL` |
| `agent_runtime_snapshots` | `app/models/agent_runtime.py:20`，`AgentRuntimeSnapshot` | `id VARCHAR(64) PK`；`trace_id VARCHAR(64) NOT NULL`；`snapshot_type VARCHAR(50) NOT NULL`；`sequence_number INTEGER NULL`；`state_data JSON NOT NULL`；`created_at DATETIME NOT NULL`；`is_final BOOLEAN NULL` |

上述可空性来自运行期 `Base.metadata.tables`，不是只读源码参数文本。

### 5.2 `approval_records` → `approvals` 字段级差异

| 源字段 | 目标承接字段 | 当前差异/无处安放事实 |
|---|---|---|
| `id VARCHAR(64)` | `id INTEGER` | 同名但类型不同，不能原值直接落入 |
| `trace_id` | `trace_id` | 同名、同长度、均非空 |
| `decision_id` | — | 目标无此字段 |
| `priority` | — | 目标无此字段 |
| `status VARCHAR(20)` | `status VARCHAR(32)` | 同名，目标长度更大 |
| `request_data` | — | 目标无 JSON 请求数据字段 |
| `decision_data` | — | 目标无 JSON 决定数据字段 |
| `requested_by` | `created_by_user_id` | 无同名字段；字段含义存在对应可能，但命名与目标可空性不同 |
| `requested_at` | `created_at` | 无同名字段；时间含义存在对应可能 |
| `resolved_by` | `decided_by_user_id` | 无同名字段；字段含义存在对应可能 |
| `resolved_at` | `decided_at` | 无同名字段；字段含义存在对应可能 |
| `resolution_note TEXT` | `reason VARCHAR(256)` | 无同名字段；文本长度能力不同 |

目标表另有源表不提供的 `command_id INTEGER NOT NULL`、`tool_call_id INTEGER NOT NULL`、`updated_at DATETIME NOT NULL`。明确没有目标字段的源数据为 `decision_id`、`priority`、`request_data`、`decision_data`；`id` 还存在字符串到整数的类型差异。

### 5.3 `decision_records` → `audit_events` 字段级差异

| 源字段 | 目标承接字段 | 当前差异/无处安放事实 |
|---|---|---|
| `id VARCHAR(64)` | `id INTEGER` | 同名但类型不同，不能原值直接落入 |
| `trace_id NOT NULL` | `trace_id NULL` | 同名、同长度，目标允许空 |
| `decision_type` | `action`（含义可能） | 无同名字段，尚无已裁定转换关系 |
| `decision_data` | `request_meta` / `side_effects_applied`（均为 JSON） | 目标有通用 JSON 字段，但没有唯一语义对应 |
| `input_context` | `request_meta`（含义可能） | 无同名字段；与 `decision_data` 竞争同一可能字段 |
| `output_result` | `side_effects_applied`（含义可能） | 无同名字段，尚无已裁定转换关系 |
| `risk_level` | — | 目标无风险等级字段 |
| `risk_score` | — | 目标无风险分数字段 |
| `requires_approval` | — | 目标只有 `approval_id` 外键，没有布尔承接字段 |
| `approval_level` | — | 目标无审批等级字段 |
| `approved_by` | — | 目标无审批人字段；`actor_user_id` 语义不等同 |
| `approved_at` | — | 目标无审批时间字段 |
| `created_at` | `created_at` | 同名、同类型、均非空 |

目标表另有源表不提供的必填 `action`、`decision`，以及 `actor_user_id`、资源、原因、技能、工具、LLM、`approval_id` 等可空字段。明确没有唯一承接位置的源数据为 `decision_data`、`risk_level`、`risk_score`、`requires_approval`、`approval_level`、`approved_by`、`approved_at`；`decision_type`、`input_context`、`output_result` 只有含义可能，没有已裁定的一一映射。

### 5.4 `replay_checkpoints` → `agent_runtime_snapshots` 字段级差异

| 源字段 | 目标承接字段 | 当前差异/无处安放事实 |
|---|---|---|
| `id` | `id` | 同名、同类型 |
| `trace_id` | `trace_id` | 同名、同类型、均非空 |
| `checkpoint_name` | `snapshot_type`（含义可能） | 无同名字段，长度 100→50，且语义未裁定 |
| `sequence_number` | `sequence_number` | 同名、同类型 |
| `belief_state_snapshot` | `state_data`（JSON 打包可能） | 无独立目标字段 |
| `decision_snapshot` | `state_data`（JSON 打包可能） | 无独立目标字段 |
| `evidence_snapshot` | `state_data`（JSON 打包可能） | 无独立目标字段 |
| `created_at` | `created_at` | 同名、同类型、均非空 |

目标表另有源表不提供的必填 `snapshot_type`、`state_data` 以及可空 `is_final`。三份源 JSON 只有一个目标 JSON 容器，需要组合后才能全部承接；`checkpoint_name` 到 `snapshot_type` 还存在长度和含义差异。

### 5.5 当前读取路径

三张源表在 `app/` 函数体 AST `Call` 节点中的 ORM 类命中均为 **0**，调用参数字符串中的表名命中也均为 **0**：

| 源表 | ORM 调用命中 | 表名字符串调用命中 | 当前应用读取路径 |
|---|---:|---:|---|
| `approval_records` | 0 | 0 | 未发现 |
| `decision_records` | 0 | 0 | 未发现 |
| `replay_checkpoints` | 0 | 0 | 未发现 |

`app/models/__init__.py` 只导入并导出三个 ORM 类，没有函数体调用，不计为读取。此处只证明当前仓库 `app/` 的源码可见调用；不证明仓库外程序、反射、动态拼接 SQL 或当前数据库内容。

复现 `[R6]`：

```bash
$PY - <<'PY'
import json
d=json.load(open('/tmp/rmos_s2_facts.json'))
for name in ('approval_records','approvals','decision_records','audit_events',
             'replay_checkpoints','agent_runtime_snapshots'):
    print(name, d['tables'][name])
print(d['merged_table_call_reads'])
PY
```

## 6. UNKNOWN 清单

### 6.1 测试归类 UNKNOWN

| 测试文件 | 用例数 | 原因 |
|---|---:|---|
| `tests/e2e/test_agent_diagnosis_flow.py` | 3 | 同时覆盖 Agent 编排与诊断流程 |
| `tests/e2e/test_e2e_cross_role_access.py` | 1 | 跨多个业务域验证角色访问 |
| `tests/e2e/test_e2e_memory_loop.py` | 1 | 同时覆盖训练记忆与 Agent 运行时循环 |
| `tests/e2e/test_e2e_task_report_evidence.py` | 2 | 同时覆盖任务报告与证据链 |
| `tests/load/test_locustfile_smoke.py` | 2 | 全应用负载入口烟测 |
| `tests/regression/test_p0_bugs_2026_07.py` | 7 | 跨历史 P0 问题的综合回归 |
| `tests/unit/test_cors_settings.py` | 1 | 全应用跨域配置 |
| `tests/unit/test_migration_contract.py` | 1 | 全应用迁移契约 |
| `tests/unit/test_smoke_help_gate.py` | 1 | 全应用帮助/烟测门禁 |
| `tests/unit/test_timing_middleware.py` | 6 | 全应用中间件 |
| `tests/unit/test_yaml_config.py` | 28 | 通用配置装载 |
| **合计** | **53** | **11 个文件** |

### 6.2 路由归类 UNKNOWN

| 端点来源 | APIRoute 数 | 原因 |
|---|---:|---|
| `main.root` | 1 | 全应用根入口，不在 `app/` 文件映射内 |
| `app.api.v1.endpoints.health` | 1 | 全应用健康检查 |
| `app.api.v1.endpoints.agent_knowledge` | 9 | 同文件跨 C/B/I |
| `app.api.v1.endpoints.agent_governance` | 5 | 同文件跨 D/F/A |
| **合计** | **16** |  |

### 6.3 测量边界 UNKNOWN / NOT_RUN

| ID | 项目 | 状态 | 原因与边界 |
|---|---|---|---|
| U-01 | 21 个跨模块或全局 `app/` 文件的唯一模块归属 | UNKNOWN | S1-001 没有给出单一归属，或文件实际聚合多个模块；已在 §2.3 逐项列出 |
| U-02 | 由不确定文件发出/指向不确定文件的 216 条内部 import 边应如何分摊 | UNKNOWN | 95 条源端不确定、121 条目标端不确定；未强行计入矩阵 |
| U-03 | 11 个跨模块或全局测试文件的唯一模块归属 | UNKNOWN | 按主要被测对象仍无法唯一归类；已在 §6.1 列出 |
| U-04 | 16 条跨模块或全局路由的唯一模块归属 | UNKNOWN | 真实路由已枚举，但端点文件没有唯一模块归属 |
| U-05 | 反射、动态 import、monkey patch 形成的额外运行期模块边 | UNKNOWN | AST import 图只覆盖源码可见静态 import |
| U-06 | 仓库外程序是否读取三张待合并源表 | UNKNOWN | 当前扫描范围仅为仓库内 `app/`；外部 ETL、手工 SQL、其他仓库不可见 |
| U-07 | 三张源表当前数据库行数及真实数据形态 | NOT_RUN | 本任务不要求数据库内容取证；沙箱连接 `::1:5432` 受限 |
| U-08 | 995 个测试用例的执行结果 | NOT_RUN | 本任务明确不跑全量测试；本报告只执行 `--collect-only` 统计 |

## 7. 机械一致性自检

| 检查 | 结果 |
|---|---|
| 文件覆盖 | `208 已归类 + 21 UNKNOWN = 229` |
| 代码行覆盖 | `29,035 已归类 + 1,292 UNKNOWN = 30,327` |
| 目标表覆盖 | `10+7+2+6+5+11+5+7+9 = 62` |
| APIRoute 覆盖 | `152 已归类 + 16 UNKNOWN = 168` |
| 测试文件覆盖 | `120 已归类 + 11 UNKNOWN = 131` |
| 测试用例覆盖 | `942 已归类 + 53 UNKNOWN = 995` |
| 矩阵交叉边 | 53 个非零方向，文件边合计 159 |
| 双向依赖 | 14 对 |
| 三模块以上简单环 | 1,934 个；按长度分组之和为 1,934 |
| 待合并源表读取 | 三表 ORM Call 与表名字符串 Call 均为 0 |

复现 `[R7]`：

```bash
$PY - <<'PY'
import json
d=json.load(open('/tmp/rmos_s2_facts.json'))
assert len(d['assignment_rows']) == 229
assert sum(x['file_count'] for x in d['cost'].values()) + len(d['unknown_app']) == 229
assert sum(x['route_count'] for x in d['cost'].values()) + len(d['unknown_routes']) == 168
assert sum(x['test_file_count'] for x in d['cost'].values()) + len(d['unknown_tests']) == 131
assert sum(x['test_case_count'] for x in d['cost'].values()) + sum(x['cases'] for x in d['unknown_tests']) == 995
assert sum(x['target_table_count'] for x in d['cost'].values()) == 62
assert sum(x['edge_count'] for x in d['dependency_edges']) == 159
assert len(d['bidirectional']) == 14
assert len(d['cycles_3plus']) == 1934
print('PASS')
PY
```
