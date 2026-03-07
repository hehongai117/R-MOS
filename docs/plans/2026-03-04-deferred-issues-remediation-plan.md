# Deferred Issues Remediation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在不破坏现有功能的前提下，集中关闭 `PHASE0_DEFERRED_ISSUES_AND_REMEDIATION.md` 中 P0~P4 的延期问题，并恢复“可启动、可构建、可测试、可验收”的交付基线。

**Architecture:** 采用“先止血再收敛”策略：先处理启动/构建阻断（compensation_planner 缺失、前端 TS 阻断、依赖缺失），再做 API 契约与前后端真联调，随后补齐持久化与迁移，最后补全自动化测试与验收证据链。每个阶段均通过最小门禁后再进入下一阶段。

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy/Alembic, React + TypeScript + Ant Design, pytest, npm/tsc/vite.

## Scope Mapping
- Source of truth: `/Users/xuhehong/Desktop/r-mos/docs/testing/PHASE0_DEFERRED_ISSUES_AND_REMEDIATION.md`
- Target closure: P0-DI-001~004, P1-DI-001~005, P2-DI-001~006, P3-DI-001~005, P4-DI-001~007

## Execution Order (Hard)
1. Stage A: 启动/构建阻断修复（必须先清零）
2. Stage B: API 契约修复与前后端真实联调
3. Stage C: 持久化与迁移收敛
4. Stage D: 自动化测试补齐与 CI 门禁
5. Stage E: 文档、报告与最终验收

---

### Task 1: Stage A-1 后端启动阻断修复

**Files:**
- Create: `r-mos-backend/app/services/compensation_planner.py`
- Modify: `r-mos-backend/app/api/v1/endpoints/agent.py`
- Test: `r-mos-backend/tests/unit/test_compensation_planner.py`

**Step 1: Write the failing test**
- Add test: `test_compensation_planner_minimal_flow` (analyze -> generate -> approve -> execute)

**Step 2: Run test to verify it fails**
- Run: `cd r-mos-backend && source .venv/bin/activate && pytest tests/unit/test_compensation_planner.py::test_compensation_planner_minimal_flow -q`
- Expected: FAIL (`ModuleNotFoundError` or missing symbol)

**Step 3: Write minimal implementation**
- Implement enums/classes/functions used by agent endpoints:
  - `FailureType`
  - `CompensationStrategy`
  - `analyze_failure()`
  - `generate_compensation_plan()`
  - `update_plan_status()`
  - `get_plan()` / `get_failure_history()` / `get_plans_by_status()`

**Step 4: Run test to verify it passes**
- Same pytest command above
- Expected: PASS

**Step 5: Startup smoke verification**
- Run: `cd r-mos-backend && source .venv/bin/activate && python -c "import main; print('OK_MAIN_IMPORT')"`
- Expected: prints `OK_MAIN_IMPORT`

**Step 6: Commit**
- `git add r-mos-backend/app/services/compensation_planner.py r-mos-backend/app/api/v1/endpoints/agent.py r-mos-backend/tests/unit/test_compensation_planner.py`
- `git commit -m "fix: add compensation planner service and unblock agent startup"`

---

### Task 2: Stage A-2 前端编译阻断清零

**Files:**
- Modify: `r-mos-frontend/src/pages/admin/AcceptanceDashboardPage.tsx`
- Modify: `r-mos-frontend/src/components/Agent/CompensationConfirm.tsx`
- Modify: `r-mos-frontend/src/pages/agent/AgentWorkbenchPage.tsx`
- Modify: `r-mos-frontend/src/pages/ReplayPage.tsx`
- Modify: `r-mos-frontend/src/components/Agent/EvidencePanel.tsx`

**Step 1: Write failing type/build checks**
- Run: `cd r-mos-frontend && npm run build`
- Expected: FAIL with current TS errors (TS1382, missing icon export, unused symbol set)

**Step 2: Minimal fixes**
- Escape JSX text (`>=` -> `&gt;=`)
- Replace invalid icon (`SkipForwardOutlined` -> valid icon)
- Remove or use currently unused imports/states

**Step 3: Re-run build**
- Run: `cd r-mos-frontend && npm run build`
- Expected: PASS

**Step 4: Commit**
- `git add r-mos-frontend/src/pages/admin/AcceptanceDashboardPage.tsx r-mos-frontend/src/components/Agent/CompensationConfirm.tsx r-mos-frontend/src/pages/agent/AgentWorkbenchPage.tsx r-mos-frontend/src/pages/ReplayPage.tsx r-mos-frontend/src/components/Agent/EvidencePanel.tsx`
- `git commit -m "fix: clear frontend phase2-4 TypeScript blockers"`

---

### Task 3: Stage A-3 依赖与环境门禁修复

**Files:**
- Modify: `r-mos-backend/requirements.txt`
- Create: `docs/adr/ADR-AGENT-DEPENDENCY-PSUTIL.md`

**Step 1: Confirm dependency gap**
- Run: `cd r-mos-backend && source .venv/bin/activate && python -c "import psutil"`
- Expected: currently FAIL (until dependency installed in env)

**Step 2: Document dependency decision (ADR)**
- Add rationale, alternatives, impact, migration/rollback

**Step 3: Validate runtime import path**
- Run: `cd r-mos-backend && source .venv/bin/activate && python -c "from app.services.system_monitor import system_monitor; print('OK_MONITOR_IMPORT')"`
- Expected: PASS

**Step 4: Commit**
- `git add r-mos-backend/requirements.txt docs/adr/ADR-AGENT-DEPENDENCY-PSUTIL.md`
- `git commit -m "docs: add ADR for psutil dependency and monitoring runtime"`

---

### Task 4: Stage B-1 后端 API 契约收敛（P0/P1）

**Files:**
- Modify: `r-mos-backend/app/api/v1/endpoints/agent.py`
- Modify: `r-mos-backend/app/services/orchestrator_v2.py`
- Modify: `r-mos-backend/app/services/policy_matrix.py`
- Test: `r-mos-backend/tests/unit/test_agent_v2_contract.py`

**Step 1: Write failing contract tests**
- Cover:
  - `/agent/v2/request`
  - `/agent/v2/policy/evaluate`
  - `/agent/v2/task/*`
  - `/agent/v2/modules`

**Step 2: Run tests to verify failure**
- Run: `cd r-mos-backend && source .venv/bin/activate && pytest tests/unit/test_agent_v2_contract.py -q`

**Step 3: Minimal implementation fixes**
- Replace invalid dataclass `.model_dump()` usage
- Use request/response models for policy endpoint
- Ensure response fields match frontend SDK expectations

**Step 4: Re-run tests**
- same pytest command, expected PASS

**Step 5: Commit**
- `git add ...`
- `git commit -m "fix: align agent v2 API contracts and runtime serialization"`

---

### Task 5: Stage B-2 前端去 mock，接真实 API（P2/P3/P4）

**Files:**
- Modify: `r-mos-frontend/src/components/Agent/EvidencePanel.tsx`
- Modify: `r-mos-frontend/src/pages/admin/ApprovalQueuePage.tsx`
- Modify: `r-mos-frontend/src/pages/ReplayPage.tsx`
- Modify: `r-mos-frontend/src/pages/admin/AcceptanceDashboardPage.tsx`
- Modify: `r-mos-frontend/src/api/agent-v2.ts`

**Step 1: Write failing page-level tests**
- Tests should assert actual API calls are invoked, not local mock assignments

**Step 2: Implement API integration**
- EvidencePanel -> `/agent/evidence/v2/*`
- ApprovalQueue -> `/agent/approval/*`
- ReplayPage -> `/agent/replay/*`
- AcceptanceDashboard -> `/agent/metrics*`

**Step 3: Run frontend tests and build**
- `cd r-mos-frontend && npm run test -- --runInBand`
- `cd r-mos-frontend && npm run build`

**Step 4: Commit**
- `git add ...`
- `git commit -m "feat: replace phase2-4 frontend mock flows with live APIs"`

---

### Task 6: Stage C-1 持久化收敛（Belief/Evidence/Approval/Replay）

**Files:**
- Create: `r-mos-backend/alembic/versions/202603xx_xxxx_add_agent_runtime_state_tables.py`
- Modify: `r-mos-backend/app/services/belief_state.py`
- Modify: `r-mos-backend/app/services/evidence_collector.py`
- Modify: `r-mos-backend/app/services/approval_queue.py`
- Modify: `r-mos-backend/app/services/decision_recalculator.py`
- Test: `r-mos-backend/tests/unit/test_agent_state_persistence.py`

**Step 1: Write failing persistence tests**
- Create -> read -> restart-simulated reload -> still exists

**Step 2: Add minimal schema + repository logic**
- Persist critical entities by `trace_id/decision_id/request_id`

**Step 3: Migration validation**
- `cd r-mos-backend && source .venv/bin/activate && pytest tests/unit/test_migration_contract.py -q`

**Step 4: Re-run persistence tests**
- expected PASS

**Step 5: Commit**
- `git add ...`
- `git commit -m "feat: persist agent runtime state for replay auditability"`

---

### Task 7: Stage C-2 修复历史错误迁移（P0-DI-002）

**Files:**
- Modify or replace: `r-mos-backend/alembic/versions/20260304_0858_869864251bc9_phase0_week2_extend_command_toolcall_.py`
- Test: `r-mos-backend/tests/unit/test_migration_contract.py`

**Step 1: Write migration regression test**
- Ensure no unrelated drop/alter destructive operations

**Step 2: Build minimal additive migration**
- Keep only required new columns/indexes/constraints

**Step 3: Verify upgrade/downgrade**
- `cd r-mos-backend && source .venv/bin/activate && alembic upgrade head`
- `cd r-mos-backend && source .venv/bin/activate && alembic downgrade -1`

**Step 4: Commit**
- `git add ...`
- `git commit -m "fix: replace destructive migration with additive phase0 migration"`

---

### Task 8: Stage D 自动化测试补齐与门禁脚本

**Files:**
- Create: `r-mos-backend/tests/unit/test_phase2_contract.py`
- Create: `r-mos-backend/tests/unit/test_phase3_contract.py`
- Create: `r-mos-backend/tests/unit/test_phase4_contract.py`
- Create: `r-mos-frontend/src/__tests__/phase2-4-pages.spec.tsx`
- Modify: `scripts/run_phase3_regression.sh` (or add `scripts/run_phase4_regression.sh`)

**Step 1: Add failing tests by phase issue IDs**
- Each P*-DI maps to at least one test

**Step 2: Run targeted test sets**
- `cd r-mos-backend && source .venv/bin/activate && pytest tests/unit/test_phase2_contract.py tests/unit/test_phase3_contract.py tests/unit/test_phase4_contract.py -q`
- `cd r-mos-frontend && npm run test -- --runInBand`

**Step 3: Ensure all pass**

**Step 4: Commit**
- `git add ...`
- `git commit -m "test: add phase2-4 contract and regression coverage"`

---

### Task 9: Stage E 文档与验收收口

**Files:**
- Modify: `docs/testing/PHASE0_DEFERRED_ISSUES_AND_REMEDIATION.md`
- Modify: `docs/testing/TEST_PLAN.md`
- Modify: `docs/testing/TEST_REPORT.md`
- Modify: `DEVELOPMENT_LOG.md`

**Step 1: Mark each P*-DI status**
- `DEFERRED` -> `CLOSED` with commit + test evidence

**Step 2: Update acceptance metrics evidence**
- Include M-ENTRY-001/M-OBJ-001/M-REPLAY-002/M-SAFE-001 measured outputs

**Step 3: Final full verification**
- `cd r-mos-backend && source .venv/bin/activate && pytest -q`
- `cd r-mos-frontend && npm run build`
- `cd r-mos-backend && source .venv/bin/activate && python -c "import main; print('OK_MAIN_IMPORT')"`

**Step 4: Commit**
- `git add docs/testing/PHASE0_DEFERRED_ISSUES_AND_REMEDIATION.md docs/testing/TEST_PLAN.md docs/testing/TEST_REPORT.md DEVELOPMENT_LOG.md`
- `git commit -m "docs: close deferred issue ledger with final acceptance evidence"`

---

## Definition of Done (All Must Pass)
- Backend app import/startup passes (`OK_MAIN_IMPORT`)
- Frontend build passes (`npm run build`)
- No mock-only critical admin/agent workflows remain
- V2 + Phase2/3/4 APIs have contract tests and pass
- Deferred issue doc updated: all target IDs closed with evidence
- Acceptance metrics generated from real data path, not hardcoded assumptions

## Risk Controls
- Do not change `DATABASE_URL` and CORS fixed constraints.
- Preserve backward compatibility on legacy endpoints; new behavior behind feature flags where needed.
- Each task isolated, with small commits and rollback-safe changes.

## Suggested Execution Batches
- Batch 1 (Day 1): Task 1-3
- Batch 2 (Day 2-3): Task 4-5
- Batch 3 (Day 4-5): Task 6-7
- Batch 4 (Day 6): Task 8-9
