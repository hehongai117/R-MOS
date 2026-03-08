# Backend Diagnosis Test Phase Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在不破坏现有后端基线的前提下，完成诊断链路全量回归、专项测试补强、E2E 验证与覆盖率闭环。

**Architecture:** 先用“全量回归 + 同口径覆盖率”确认当前主干稳定，再按模块拆出专项测试，最后进入缺陷分批修复与 E2E 验收。所有新增测试必须对齐当前实现契约，不允许把尚未存在的字段或接口当成断言目标。

**Tech Stack:** `pytest`、`pytest-cov`、FastAPI、SQLAlchemy、Vitest 已有基线、`DEVELOPMENT_LOG.md` 证据记录、`docs/testing/ACCEPTANCE_CHARTER.md` 门禁。

## Feasibility Adjustments

执行前先固定 4 个口径：

1. 覆盖率比较必须同口径。
   - 现有 `74.63%` 来自“核心 14 服务覆盖率门禁”，不是 `--cov=app` 全量口径。
   - 因此 Phase 1 需要产出两组数据：
     - 全量覆盖率：`--cov=app`
     - 核心 14 服务覆盖率：沿用历史门禁命令
   - 是否进入下一阶段，以“核心 14 服务覆盖率不低于 74.63%”为硬门禁；全量覆盖率作为参考和拉升目标。

2. 专项测试断言必须对齐当前实现。
   - 当前实现存在：`requires_supervisor`、`recommended_actions`、`validation_required`、`to_context_block()`
   - 当前实现不存在：`urgency_level`、`fallback_instruction`、`recommended_action` 单数字段、`to_prompt_dict()`
   - 若要测这些字段，必须先改实现和 schema；本计划默认不扩大需求，测试按现有契约写。

3. 测试文件名避免冲突。
   - 已存在：`tests/unit/test_simulation_executor.py`
   - 因此专项测试文件应采用：
     - `tests/unit/test_telemetry_context_builder.py`
     - `tests/unit/test_fault_diagnosis_engine.py`
     - `tests/unit/test_maintenance_plan_generator.py`
     - `tests/unit/test_simulation_executor.py`（扩展现有文件）
     - `tests/unit/test_orchestrator_diagnoser.py`
     - `tests/e2e/test_agent_diagnosis_flow.py`

4. WebSocket 协议一致性不应完全算作“后端专项”。
   - 后端可验证 `/ws/robot/status` 输出结构。
   - 前端 Viewer3D 解析已在 `T-08` 单测中覆盖。
   - 因此 E2E 中只验证后端 WebSocket 消息结构一致，不重复承担前端解析职责。

---

### Task 1: Establish Baseline Gate

**Files:**
- Modify: `DEVELOPMENT_LOG.md`
- Reference: `docs/testing/ACCEPTANCE_CHARTER.md`
- Reference: `docs/testing/backend-test-report.md`

**Step 1: Run full regression with detailed output**

Run:

```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
source .venv/bin/activate
pytest tests/ -v --tb=short --cov=app --cov-report=term-missing \
  --cov-report=json:coverage_post_refactor.json \
  2>&1 | tee test_baseline_post_refactor.log
```

Expected:
- 完整通过或拿到可分类的失败清单
- 生成 `coverage_post_refactor.json`
- 生成 `test_baseline_post_refactor.log`

**Step 2: Run same-scope historical coverage gate**

Run:

```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
source .venv/bin/activate
pytest tests/unit/test_project_generator.py \
       tests/unit/test_session_service.py \
       tests/unit/test_submission_service.py \
       tests/unit/test_feedback_generator.py \
       tests/unit/test_session_initializer.py \
       tests/unit/test_agent_policy_factory.py \
       tests/unit/test_class_membership.py \
       tests/unit/test_training_memory_writer.py \
       tests/unit/test_skill_profile_service.py \
       tests/unit/test_knowledge_hub.py \
       tests/unit/test_preflight_check.py \
       tests/unit/test_teacher_monitor.py \
       tests/unit/test_training_intent_router.py \
       tests/unit/test_orchestrator_v2.py \
       --cov=app/services \
       --cov-report=term-missing \
       -q
```

Expected:
- 输出核心 14 服务覆盖率
- 与历史 `74.63%` 做同口径对比

**Step 3: Record gate outcome**

在 `DEVELOPMENT_LOG.md` 追加：
- 全量通过/失败数
- 全量覆盖率
- 核心 14 服务覆盖率
- 是否满足进入专项测试门禁

**Step 4: Branch by outcome**

Decision:
- `0 failure` 且核心 14 服务覆盖率 `>= 74.63%` -> 进入 Task 2
- `1~10 failure` -> 进入 Task 5，逐条修复
- `>10 failure` -> 进入 Task 4，先分类归因
- 覆盖率下降 -> 进入 Task 6，先补测试

**Step 5: Commit baseline evidence**

```bash
git add DEVELOPMENT_LOG.md r-mos-backend/coverage_post_refactor.json r-mos-backend/test_baseline_post_refactor.log
git commit -m "test: capture post-refactor backend baseline"
```

---

### Task 2: Add TelemetryContextBuilder Dedicated Tests

**Files:**
- Test: `r-mos-backend/tests/unit/test_telemetry_context_builder.py`
- Reference: `r-mos-backend/app/services/llm/telemetry_context_builder.py`

**Step 1: Write the failing tests**

```python
def test_builder_detects_overheat():
    ...

def test_builder_detects_stall_with_low_velocity_and_low_torque():
    ...

def test_builder_detects_voltage_drop():
    ...

def test_builder_returns_normal_when_no_anomalies():
    ...

def test_builder_reports_multiple_fault_hints():
    ...

def test_to_context_block_shape_is_complete():
    ...
```

重点断言：
- `robot_status`
- `anomalies[*].type`
- 多故障并发时至少包含多个 anomaly type
- `to_context_block()` 返回 `robot_status/joint_summary/battery/temperature/voltage/anomalies`

**Step 2: Run test to verify RED**

```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
source .venv/bin/activate
pytest tests/unit/test_telemetry_context_builder.py -v
```

**Step 3: Implement minimal fixes only if needed**

只允许修改：
- `r-mos-backend/app/services/llm/telemetry_context_builder.py`

不允许顺手扩 schema。

**Step 4: Run test to verify GREEN**

```bash
pytest tests/unit/test_telemetry_context_builder.py -v
```

**Step 5: Check focused coverage**

```bash
pytest tests/unit/test_telemetry_context_builder.py \
  --cov=app/services/llm/telemetry_context_builder.py \
  --cov-report=term-missing -q
```

Target: `>= 90%`

**Step 6: Commit**

```bash
git add tests/unit/test_telemetry_context_builder.py app/services/llm/telemetry_context_builder.py DEVELOPMENT_LOG.md
git commit -m "test: strengthen telemetry context builder coverage"
```

---

### Task 3: Add Diagnosis Engine Dedicated Tests

**Files:**
- Test: `r-mos-backend/tests/unit/test_fault_diagnosis_engine.py`
- Reference: `r-mos-backend/app/services/diagnosis/fault_diagnosis_engine.py`
- Reference: `r-mos-backend/app/services/diagnosis/schemas.py`

**Step 1: Write the failing tests**

```python
@pytest.mark.asyncio
async def test_llm_diagnosis_parses_three_ranked_hypotheses():
    ...

@pytest.mark.asyncio
async def test_llm_invalid_json_falls_back_to_rule_based_result():
    ...

@pytest.mark.asyncio
async def test_llm_timeout_falls_back_without_raising():
    ...

@pytest.mark.asyncio
async def test_invalid_recommended_actions_do_not_crash_parser():
    ...

@pytest.mark.asyncio
async def test_requires_supervisor_is_derived_from_confidence_threshold():
    ...
```

说明：
- 不测 `urgency_level`，因为当前实现没有这个字段。
- “非法 recommended_action 枚举”改为“`recommended_actions` 内容异常时不崩溃”。

**Step 2: Run RED**

```bash
source .venv/bin/activate
pytest tests/unit/test_fault_diagnosis_engine.py -v
```

**Step 3: Minimal implementation fixes if tests expose bugs**

只允许修改：
- `app/services/diagnosis/fault_diagnosis_engine.py`
- `app/services/diagnosis/schemas.py`

**Step 4: Run GREEN**

```bash
pytest tests/unit/test_fault_diagnosis_engine.py -v
```

**Step 5: Check focused coverage**

```bash
pytest tests/unit/test_fault_diagnosis_engine.py \
  --cov=app/services/diagnosis/fault_diagnosis_engine.py \
  --cov-report=term-missing -q
```

Target: `>= 85%`

**Step 6: Commit**

```bash
git add tests/unit/test_fault_diagnosis_engine.py app/services/diagnosis/fault_diagnosis_engine.py app/services/diagnosis/schemas.py DEVELOPMENT_LOG.md
git commit -m "test: harden fault diagnosis engine fallbacks"
```

---

### Task 4: Add Maintenance Plan Generator Dedicated Tests

**Files:**
- Test: `r-mos-backend/tests/unit/test_maintenance_plan_generator.py`
- Reference: `r-mos-backend/app/services/diagnosis/maintenance_plan_generator.py`

**Step 1: Write the failing tests**

```python
@pytest.mark.asyncio
async def test_stall_plan_contains_four_to_six_steps():
    ...

@pytest.mark.asyncio
async def test_first_step_is_safety_or_power_off_related():
    ...

@pytest.mark.asyncio
async def test_low_confidence_or_replace_calibrate_requires_supervisor():
    ...

@pytest.mark.asyncio
async def test_high_confidence_check_only_plan_does_not_require_supervisor():
    ...

@pytest.mark.asyncio
async def test_llm_parse_failure_degrades_to_template_plan():
    ...
```

说明：
- 不测 `urgency_level`、`fallback_instruction`，因为当前实现没有。
- “第一步必须是安全操作”应按现有模板检验“断电/安全提示/急停语义”而不是强行要求新增动作类型。

**Step 2: Run RED**

```bash
source .venv/bin/activate
pytest tests/unit/test_maintenance_plan_generator.py -v
```

**Step 3: Minimal implementation fixes**

只允许修改：
- `app/services/diagnosis/maintenance_plan_generator.py`

**Step 4: Run GREEN**

```bash
pytest tests/unit/test_maintenance_plan_generator.py -v
```

**Step 5: Check focused coverage**

```bash
pytest tests/unit/test_maintenance_plan_generator.py \
  --cov=app/services/diagnosis/maintenance_plan_generator.py \
  --cov-report=term-missing -q
```

Target: `>= 85%`

**Step 6: Commit**

```bash
git add tests/unit/test_maintenance_plan_generator.py app/services/diagnosis/maintenance_plan_generator.py DEVELOPMENT_LOG.md
git commit -m "test: strengthen maintenance plan generator coverage"
```

---

### Task 5: Expand Simulation Executor Coverage

**Files:**
- Modify: `r-mos-backend/tests/unit/test_simulation_executor.py`
- Modify: `r-mos-backend/tests/unit/test_mock_adapter.py`
- Reference: `r-mos-backend/app/services/simulation/simulation_executor.py`
- Reference: `r-mos-backend/app/adapters/mock.py`

**Step 1: Write the failing tests**

```python
@pytest.mark.asyncio
async def test_stall_plan_clears_fault_and_updates_delta_summary():
    ...

@pytest.mark.asyncio
async def test_overheat_plan_reduces_temperature_signal():
    ...

@pytest.mark.asyncio
async def test_apply_maintenance_action_commands_are_all_supported():
    ...

@pytest.mark.asyncio
async def test_failed_steps_are_recorded_when_action_returns_false():
    ...
```

**Step 2: Run RED**

```bash
source .venv/bin/activate
pytest tests/unit/test_mock_adapter.py tests/unit/test_simulation_executor.py -v
```

**Step 3: Minimal fixes**

只允许修改：
- `app/services/simulation/simulation_executor.py`
- `app/adapters/mock.py`

**Step 4: Run GREEN**

```bash
pytest tests/unit/test_mock_adapter.py tests/unit/test_simulation_executor.py -v
```

**Step 5: Check focused coverage**

```bash
pytest tests/unit/test_mock_adapter.py tests/unit/test_simulation_executor.py \
  --cov=app/services/simulation/simulation_executor.py \
  --cov=app/adapters/mock.py \
  --cov-report=term-missing -q
```

Target:
- `simulation_executor.py >= 90%`
- 新增分支逻辑被真实命中

**Step 6: Commit**

```bash
git add tests/unit/test_mock_adapter.py tests/unit/test_simulation_executor.py app/services/simulation/simulation_executor.py app/adapters/mock.py DEVELOPMENT_LOG.md
git commit -m "test: expand simulation executor regression coverage"
```

---

### Task 6: Add Orchestrator Diagnoser Handler Tests

**Files:**
- Test: `r-mos-backend/tests/unit/test_orchestrator_diagnoser.py`
- Reference: `r-mos-backend/app/services/orchestrator_v2.py`
- Reference: `r-mos-backend/app/api/v1/endpoints/agent.py`

**Step 1: Write the failing tests**

```python
@pytest.mark.asyncio
async def test_diagnoser_returns_structured_result_with_telemetry_payload():
    ...

@pytest.mark.asyncio
async def test_diagnoser_returns_error_without_telemetry_payload():
    ...

@pytest.mark.asyncio
async def test_trace_id_is_present_and_unique():
    ...

@pytest.mark.asyncio
async def test_builder_diagnosis_plan_verification_chain_is_called_in_order():
    ...
```

**Step 2: Run RED**

```bash
source .venv/bin/activate
pytest tests/unit/test_orchestrator_diagnoser.py -v
```

**Step 3: Minimal fixes**

只允许修改：
- `app/services/orchestrator_v2.py`
- `app/api/v1/endpoints/agent.py`

**Step 4: Run GREEN**

```bash
pytest tests/unit/test_orchestrator_diagnoser.py -v
```

**Step 5: Check focused coverage**

```bash
pytest tests/unit/test_orchestrator_diagnoser.py \
  --cov=app/services/orchestrator_v2.py \
  --cov-report=term-missing -q
```

Target: `>= 80%`

**Step 6: Commit**

```bash
git add tests/unit/test_orchestrator_diagnoser.py app/services/orchestrator_v2.py app/api/v1/endpoints/agent.py DEVELOPMENT_LOG.md
git commit -m "test: cover orchestrator diagnoser path"
```

---

### Task 7: Add End-to-End Diagnosis Flow Test

**Files:**
- Create: `r-mos-backend/tests/e2e/test_agent_diagnosis_flow.py`
- Reference: `r-mos-backend/tests/e2e/test_agent_execute.py`
- Reference: `r-mos-backend/app/api/v1/endpoints/agent.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_agent_execute_diagnosis_flow_returns_diagnosis_plan_and_verification(...):
    ...
```

断言：
- `POST /api/v1/agent/execute`
- 传 `intent_classification=delegate-diagnoser`
- 传 E002_STALL 遥测 payload
- 返回体包含 `result.diagnosis`
- 返回体包含 `result.maintenance_plan`
- 返回体包含 `result.verification`
- 纯逻辑耗时 `< 2s`

**Step 2: Run RED**

```bash
source .venv/bin/activate
pytest tests/e2e/test_agent_diagnosis_flow.py -v --tb=short
```

**Step 3: Minimal fixes**

仅当 E2E 暴露接口契约问题时，允许修改：
- `app/api/v1/endpoints/agent.py`
- `app/services/orchestrator_v2.py`
- 直接阻塞 E2E 的相关模块

**Step 4: Add WebSocket contract check**

同文件新增一个轻量协议测试：

```python
@pytest.mark.asyncio
async def test_robot_status_websocket_message_shape_is_telemetry_contract():
    ...
```

只断言后端消息形状：
- `type == "telemetry"`
- `timestamp` 存在
- `payload.joints`
- `payload.sensors`
- `payload.active_faults`

**Step 5: Run GREEN**

```bash
pytest tests/e2e/test_agent_diagnosis_flow.py -v --tb=short
```

**Step 6: Commit**

```bash
git add tests/e2e/test_agent_diagnosis_flow.py DEVELOPMENT_LOG.md
git commit -m "test: add diagnosis flow e2e coverage"
```

---

### Task 8: Failure Triage Batch

**Files:**
- Modify: only files directly implicated by failing tests
- Modify: `DEVELOPMENT_LOG.md`

**Step 1: Categorize failures**

分类规则：
- `R-1` 接口契约问题
- `R-2` LLM 解析容错
- `R-3` 覆盖率缺口
- `R-4` 性能问题

**Step 2: Fix one batch at a time**

每个批次循环：

```bash
pytest <affected tests> -v --tb=short
```

然后：
- 写 failing test
- 跑红灯
- 最小修复
- 跑绿灯
- 记录证据

**Step 3: After each batch, rerun full regression**

```bash
pytest tests/ -v --tb=short --cov=app --cov-report=term-missing \
  --cov-report=json:coverage_post_refactor.json
```

以及：

```bash
pytest <core-14-service-list> --cov=app/services --cov-report=term-missing -q
```

**Step 4: Commit per batch**

```bash
git add <only related files>
git commit -m "fix: resolve diagnosis test batch R-<n>"
```

---

### Task 9: Final Acceptance Gate

**Files:**
- Modify: `DEVELOPMENT_LOG.md`
- Modify if needed: `docs/testing/backend-test-report.md`
- Modify if needed: `docs/testing/TEST_REPORT.md`

**Step 1: Run final full backend suite**

```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
source .venv/bin/activate
pytest tests/ -v --tb=short --cov=app --cov-report=term-missing \
  --cov-report=json:coverage_post_refactor.json \
  2>&1 | tee test_baseline_post_refactor.log
```

**Step 2: Run final same-scope historical gate**

```bash
pytest <core-14-service-list> --cov=app/services --cov-report=term-missing -q
```

**Step 3: Validate exit criteria**

必须同时满足：
- `pytest tests/` 全量 `0 failure`
- 核心 14 服务覆盖率 `>= 74.63%`
- 推荐目标：全量覆盖率 `>= 78%`
- `tests/e2e/test_agent_diagnosis_flow.py` PASS
- `DEVELOPMENT_LOG.md` 已记录命令、输出摘要、风险

**Step 4: Update reports**

必要时同步更新：
- `docs/testing/backend-test-report.md`
- `docs/testing/TEST_REPORT.md`

**Step 5: Final commit**

```bash
git add DEVELOPMENT_LOG.md docs/testing/backend-test-report.md docs/testing/TEST_REPORT.md \
        r-mos-backend/coverage_post_refactor.json r-mos-backend/test_baseline_post_refactor.log
git commit -m "test: close backend diagnosis verification gate"
```

---

## Recommended Execution Order

1. Task 1 基线门禁
2. Task 2 TelemetryContextBuilder
3. Task 3 FaultDiagnosisEngine
4. Task 4 MaintenancePlanGenerator
5. Task 5 SimulationExecutor
6. Task 6 Orchestrator diagnoser
7. Task 7 E2E diagnosis flow
8. Task 8 分批修复
9. Task 9 最终验收

## Risks To Watch

1. `--cov=app` 与历史 `74.63%` 不是同一口径，不能直接比较。
2. 若坚持引入 `urgency_level`、`fallback_instruction` 等新字段，计划会从“测试闭环”升级成“测试+需求扩展”，范围会明显变大。
3. E2E 诊断链路依赖真实 `telemetry_payload`，测试夹具必须稳定提供标准 payload。
4. WebSocket 测试可能受异步时序影响，优先做消息结构断言，不先追求复杂订阅行为。

## Minimal Acceptance Summary

- 先保住主干：全量回归 `0 failure`
- 再保住旧门禁：核心 14 服务覆盖率 `>= 74.63%`
- 再补新链路：5 个模块专项 + 1 个 E2E
- 最后才看拉升目标：全量覆盖率尽量到 `78%`
