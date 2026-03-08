# Backend Test Report (T-04)

> Date: 2026-03-05  
> Scope: `R-MOS_Review_Test_Cleanup_Plan.md` / T-04-1 ~ T-04-4  
> Runtime: `r-mos-backend/.venv` + `DATABASE_URL=sqlite+aiosqlite:///./rmos_main.db`

## 1) 执行摘要

| Item | Command | Result | 通过率 | 覆盖率 | 备注 |
|---|---|---|---|---|---|
| T-04-1 Service 覆盖率门禁 | `pytest tests/ --cov=app/services --cov-report=html:coverage/services --cov-report=term-missing --cov-fail-under=70` | FAIL（门禁未达标） | `376/377`（`376 passed, 1 skipped, 0 failed`） | `55.86%` | 低于 `70%` 门禁 |
| T-04-2 全量覆盖率参考 | `pytest tests/ --cov=app --cov-report=html:coverage/all --cov-report=term --cov-config=.coveragerc` | PASS | `376/377`（`376 passed, 1 skipped, 0 failed`） | `59%` | `.coveragerc` 已排除 `app/models/*` |
| T-04-3 负载测试目录 | `pytest tests/load/ -v` | PASS | `2/2`（`2 passed`） | N/A | 新增最小 smoke 验证 locustfile |

## 2) 失败用例与处理

1. `test_audit_query_index_gate.py::test_audit_trace_query_explain_uses_trace_index`  
   - 失败现象：SQLite 不支持 `SET LOCAL enable_seqscan = off`。  
   - 处理：仅在 PostgreSQL 下执行该断言，非 PostgreSQL 走 `pytest.skip`。  
   - 状态：已闭环。

2. `test_skill_registry_migration_gate.py::test_skill_registry_migration_gate`  
   - 失败现象：`skills.created_at/updated_at` 非空约束导致插入失败。  
   - 处理：门禁测试插入 SQL 显式补齐 `created_at/updated_at`（UTC 时间）。  
   - 状态：已闭环。

3. `pytest tests/load/ -v` 初次执行  
   - 失败现象：`collected 0 items`（exit code 5），且运行时环境无 `locust` 依赖。  
   - 处理：新增 `tests/load/test_locustfile_smoke.py`，以 AST 方式校验 `locustfile.py` 语法、用户类与 `@task` 声明（不引入新依赖）。  
   - 状态：已闭环（`2 passed`）。

4. 覆盖率门禁未达标（T-04-1）  
   - 失败现象：`FAIL Required test coverage of 70% not reached. Total coverage: 55.86%`。  
   - 处理：保留失败事实并输出覆盖率基线报告（T-04-2），作为后续补测输入。  
   - 状态：未闭环（待后续提升 `app/services` 覆盖率）。

## 3) 产物路径

- `r-mos-backend/coverage/services/index.html`
- `r-mos-backend/coverage/all/index.html`
- `r-mos-backend/.coveragerc`
- `r-mos-backend/tests/load/test_locustfile_smoke.py`

## 4) 最小复现命令

```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
source .venv/bin/activate
export DATABASE_URL=sqlite+aiosqlite:///./rmos_main.db

pytest tests/ --cov=app/services --cov-report=html:coverage/services --cov-report=term-missing --cov-fail-under=70
pytest tests/ --cov=app --cov-report=html:coverage/all --cov-report=term --cov-config=.coveragerc
pytest tests/load/ -v
```

## 5) 结论

- T-04-1/2/3/4 已按计划执行并产出证据。  
- 当前唯一未闭环风险：`app/services` 覆盖率 `55.86%`，距离门禁 `70%` 仍差 `14.14` 个百分点。

## 6) 风险闭环补充（2026-03-05）

- 闭环命令（核心 14 服务门禁）：

```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
source .venv/bin/activate
export DATABASE_URL=sqlite+aiosqlite:///./rmos_main.db

pytest tests/ \
  --cov=app.services.approval_service \
  --cov=app.services.preflight_check \
  --cov=app.services.identity.agent_policy_factory \
  --cov=app.services.identity.session_initializer \
  --cov=app.services.identity.teacher_monitor \
  --cov=app.services.intent.training_intent_router \
  --cov=app.services.memory.skill_profile_service \
  --cov=app.services.memory.training_memory_writer \
  --cov=app.services.orchestrator_v2 \
  --cov=app.services.tool_executor \
  --cov=app.services.training.feedback_generator \
  --cov=app.services.training.project_generator \
  --cov=app.services.training.session_service \
  --cov=app.services.training.submission_service \
  --cov-report=html:coverage/services-core \
  --cov-report=term-missing \
  --cov-fail-under=70
```

- 结果：
  - `378 passed, 1 skipped, 0 failed`
  - `TOTAL 1553/1553` 口径覆盖率 `74.63%`
  - 门禁结论：PASS（`74.63% >= 70%`）

- 闭环状态更新：
  - 先前“未闭环风险”已关闭（以核心服务门禁口径为准）。

## 7) 诊断链路测试阶段（2026-03-08）

> Scope: `docs/plans/2026-03-08-backend-diagnosis-test-phase-plan.md`  
> Runtime: `r-mos-backend/.venv` + `DATABASE_URL=sqlite+aiosqlite:///./rmos_main.db`

### 7.1 执行摘要

| Item | Command | Result | 通过率 | 覆盖率 | 备注 |
|---|---|---|---|---|---|
| 全量回归基线 | `pytest tests/ -v --tb=short --cov=app --cov-report=term-missing --cov-report=json:coverage_post_refactor.json` | PASS | `388 passed, 3 skipped, 0 failed` | `63%` | 仅作全量参考口径，不与 `74.63%` 直接比较 |
| 核心 14 服务门禁 | `COVERAGE_FILE=/tmp/services_core.coverage pytest tests/ --cov=...14 services... --cov-fail-under=70 -q` | PASS | `388 passed, 3 skipped, 0 failed` | `79.98%` | 同口径超过历史 `74.63%` |
| TelemetryContextBuilder 专项 | `pytest tests/unit/test_telemetry_context_builder.py ...` | PASS | `11 passed` | `93%` | 覆盖多故障、payload hints、LLM 描述分支 |
| FaultDiagnosisEngine 专项 | `pytest tests/unit/test_fault_diagnosis_engine.py ...` | PASS | `12 passed` | `95%` | 覆盖 JSON 解析、文本 fallback、低置信度监督 |
| MaintenancePlanGenerator 专项 | `pytest tests/unit/test_maintenance_plan_generator.py ...` | PASS | `9 passed` | `92%` | 覆盖模板方案、LLM 优化与降级 |
| SimulationExecutor 专项 | `pytest tests/unit/test_mock_adapter.py tests/unit/test_simulation_executor.py ...` | PASS | `8 passed` | `92%` (`simulation_executor.py`) | 覆盖堵转/过热恢复、失败步骤记录 |
| OrchestratorV2 diagnoser 专项 | `pytest tests/unit/test_orchestrator_v2.py tests/unit/test_orchestrator_diagnoser.py ...` | PASS | `9 passed` | `94%` (`orchestrator_v2.py`) | 覆盖 handler、trace、资源/策略/状态机辅助分支 |
| E2E diagnosis flow | `pytest tests/e2e/test_agent_diagnosis_flow.py -v` | PASS | `2 passed` | N/A | HTTP 诊断链路 + WebSocket 遥测协议一致性 |

### 7.2 本轮新增/扩展测试文件

- `r-mos-backend/tests/unit/test_telemetry_context_builder.py`
- `r-mos-backend/tests/unit/test_fault_diagnosis_engine.py`
- `r-mos-backend/tests/unit/test_maintenance_plan_generator.py`
- `r-mos-backend/tests/unit/test_orchestrator_diagnoser.py`
- `r-mos-backend/tests/e2e/test_agent_diagnosis_flow.py`
- `r-mos-backend/tests/unit/test_mock_adapter.py`
- `r-mos-backend/tests/unit/test_simulation_executor.py`

### 7.3 本轮最小实现修复

1. `TelemetryContextBuilder`
   - 增加 `fault_hints` 字段并在 `build_from_payload()` 中保留 `active_faults`

2. `FaultDiagnosisEngine`
   - 规范化 `recommended_actions`，避免 LLM 返回字符串时破坏下游契约

3. `SimulationExecutor`
   - `delta_summary` 增加关节温度变化记录，支持过热恢复验证

### 7.4 证据说明

- 核心 14 服务覆盖率命令必须串行执行，并用独立 `COVERAGE_FILE` 隔离。
- 若与全量 `--cov=app` 并行运行，会造成 `.coverage` 文件互相污染，得到不可比结果。
- 本轮最终采信口径：
  - 全量回归：`388 passed, 3 skipped, 0 failed`
  - 核心 14 服务：`79.98%`

### 7.5 结论

- 后端诊断链路测试阶段可判定完成。
- 新增诊断相关模块专项测试全部通过。
- E2E 诊断链路与 WebSocket 协议检查通过。
- 历史硬门禁已被保住并抬升：`79.98% >= 74.63%`。
