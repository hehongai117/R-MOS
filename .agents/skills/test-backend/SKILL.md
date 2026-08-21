---
name: test-backend
type: project-skill
project: R-MOS
phase: MVP
version: 1.1.0

description: >
  Execute the R-MOS backend test suite in a controlled, read-only, and
  non-destructive manner. This skill runs unit tests, generates coverage
  reports, and verifies MVP acceptance criteria. It is designed for
  verification and quality assurance only, not for fixing or modifying code.

allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
---

# R-MOS Backend Test Skill

---

## 1. Skill Purpose（目的与边界）

### Purpose

This skill exists to **execute and report** the R-MOS backend test suite.

It provides:
- Unit test execution and result reporting
- Acceptance test execution (if directory exists)
- Code coverage measurement and reporting
- Test failure diagnosis (read-only)
- MVP criteria verification

### Explicit Non-Goals

This skill MUST NOT:
- Modify any source code to fix failing tests
- Modify test files or test fixtures
- Create missing `conftest.py` or fixtures
- Change pytest configuration
- Skip or ignore failing tests
- Automatically retry failed tests
- Generate or modify mock data
- Install missing dependencies without explicit permission

> ⚠️ 如果一个行为不在 Purpose 中明确允许，则默认禁止。

---

## 2. Scope & Validity（适用范围）

This skill is valid ONLY under the following conditions:

- Project: `R-MOS`
- Phase: `MVP`
- Deployment model: `single-node / local`
- Target environment: `dev / test only`
- Test framework: `pytest + pytest-asyncio`
- Database: `PostgreSQL 14+ (test database, if integration tests exist)`

### Test Categories

| Category | Path | Status | Description |
|----------|------|--------|-------------|
| Unit Tests | `tests/unit/` | **Required** | Service and adapter tests |
| Acceptance Tests | `tests/acceptance/` | **Optional** | MVP criteria verification |

### Current Test Files (as of MVP)

Based on project inspection:
- `tests/unit/test_mock_adapter.py` — Mock Adapter 单元测试
- `tests/unit/test_task_service.py` — TaskService 单元测试

### Mandatory Review / Expiration Conditions

This skill MUST be reviewed, restricted, or deprecated when:

- Test framework changes from pytest
- Test directory structure changes
- New test categories are introduced (e.g., integration, e2e)
- CI/CD pipeline is implemented
- `conftest.py` is added with new fixtures
- Project enters production phase

---

## 3. Preconditions（硬前置条件）

ALL of the following MUST be true before execution:

**Hard Requirements (STOP if fail):**
- Backend directory `r-mos-backend/` exists
- Virtual environment `r-mos-backend/venv/` exists and is activatable
- Test directory `r-mos-backend/tests/unit/` exists
- `pytest` is installed (`pytest --version` succeeds)
- `pytest-asyncio` is installed

**Soft Requirements (WARN if fail, continue):**
- `pytest-cov` installed (required for coverage report)
- `tests/conftest.py` exists (required for fixture-dependent tests)
- `tests/acceptance/` directory exists (required for acceptance tests)
- PostgreSQL test database accessible (required for DB-dependent tests)

### Fixture Dependencies

Some tests require fixtures that may not be defined:
- `test_task_service.py` requires: `db_session`, `sample_sop`, `sample_task`
- These fixtures require `conftest.py` with database session setup

> ⚠️ 如果 `conftest.py` 不存在，依赖 fixtures 的测试将 FAIL 或 SKIP。
> 这不是 skill 的问题，而是测试环境未完整配置。

❌ If any **Hard Requirement** fails → **STOP IMMEDIATELY**

---

## 4. Explicit Triggers（明确触发条件）

This skill may ONLY be executed when at least one of the following occurs:

- User explicitly requests to run tests
- User enters `/test-backend` command
- User mentions "运行测试" or "run tests"
- User asks to "check test coverage"
- User asks "are the tests passing?"
- User asks to verify MVP acceptance criteria

⚠️ Vague or keyword-only mentions are NOT sufficient triggers.

---

## 5. Prohibited Behaviors（绝对禁止）

During execution, the AI MUST NOT:

- Modify source code (`.py`, `.ts`, `.js`, `.json`)
- Modify test files or fixtures
- Create `conftest.py` or define fixtures
- Change pytest.ini or pyproject.toml test configuration
- Skip, ignore, or mark tests as expected failures
- Retry failed tests automatically
- Modify mock data or test databases
- Install packages without explicit permission (including `pytest-cov`)
- Perform any "quick fixes" to make tests pass
- Interpret fixture errors as skill failures

> 本 skill 禁止任何"顺手帮你修一下"的行为。

---

## 6. Allowed Operations & Tool Constraints

### Tool Usage Rules

- Tools may ONLY be used for purposes explicitly described below.
- All operations must be:
  - Deterministic
  - Single-pass
  - Non-looping

### Tool-Specific Constraints

- **Bash**
  - Allowed: pytest execution, coverage report generation
  - Allowed: directory existence checks (`[ -d ... ]`, `ls`)
  - Allowed: read-only commands (`cat`, `grep`)
  - Forbidden: file write, deletion
  - Forbidden: package install (unless explicitly allowed by user)
  - Forbidden: modifying test configuration

- **Read / Grep / Glob**
  - Inspection only
  - Locate test files and read test output
  - Check for `conftest.py` existence
  - No inference beyond visible content

---

## 7. System References（不可变系统事实）

The following system facts are treated as **immutable** within this skill:

| Reference | Value | Source |
|-----------|-------|--------|
| Test Framework | pytest ≥ 8.0.0 | requirements.txt |
| Async Support | pytest-asyncio ≥ 0.24.0 | requirements.txt |
| Coverage Tool | pytest-cov (optional) | Not in requirements.txt |
| Backend Directory | `r-mos-backend/` | Project structure |
| Test Directory | `r-mos-backend/tests/` | Project structure |
| Unit Tests Path | `r-mos-backend/tests/unit/` | Project structure |
| Acceptance Tests Path | `r-mos-backend/tests/acceptance/` | May not exist |
| **Coverage Target** | **> 80%** | **拆包A §7 验收标准** |
| Virtual Environment | `r-mos-backend/venv/` | Project structure |

### MVP 验收标准（来源：拆包A §7, 拆包B §8）

- Mock Adapter 所有方法测试通过
- TaskService 核心流程测试通过
- ScoringService 评分逻辑测试通过
- 单元测试覆盖率 > 80%

❌ These facts MUST NOT be modified or "corrected" by the AI.

---

## 8. Data / Message / Interface Contract（强制契约）

### Test Result Contract

All test executions MUST produce output conforming to pytest standard format:

```
==================== test session starts ====================
collected X items

test_file.py::test_name PASSED/FAILED/SKIPPED/ERROR

==================== X passed, Y failed, Z skipped, W errors ====================
```

### Fixture Error Indicator

If fixtures are missing, pytest will show:

```
ERROR test_file.py::test_name
E       fixture 'fixture_name' not found
```

> ⚠️ Fixture errors indicate test environment issue, not code bug.

### Coverage Report Contract (if pytest-cov installed)

```
Name                      Stmts   Miss  Cover
---------------------------------------------
app/services/xxx.py         100     20    80%
---------------------------------------------
TOTAL                       XXX    XXX    XX%
```

❌ Any deviation → **Report anomaly but continue**

---

## 9. Execution Plan（固定流程，不可跳步）

### Step 1 — Verify Test Environment

* Action: Check pytest installation and test directory structure
* Command:
  ```bash
  cd r-mos-backend && source venv/bin/activate
  echo "=== Pytest Version ==="
  pytest --version
  echo ""
  echo "=== Test Directory Structure ==="
  ls -la tests/
  ls -la tests/unit/ 2>/dev/null || echo "⚠ tests/unit/ not found"
  ls -la tests/acceptance/ 2>/dev/null || echo "ℹ tests/acceptance/ not found (optional)"
  echo ""
  echo "=== Conftest Check ==="
  [ -f tests/conftest.py ] && echo "✓ conftest.py exists" || echo "⚠ conftest.py not found - fixture-dependent tests may fail"
  ```
* Expected result: pytest version displayed, tests/unit/ exists
* Failure condition: pytest not found OR tests/unit/ not found

❌ Fail → **STOP IMMEDIATELY**

---

### Step 2 — Check Test Dependencies

* Action: Verify test-related packages
* Command:
  ```bash
  cd r-mos-backend && source venv/bin/activate
  echo "=== Test Dependencies ==="
  pip show pytest-asyncio > /dev/null 2>&1 && echo "✓ pytest-asyncio installed" || echo "✗ pytest-asyncio NOT installed"
  pip show pytest-cov > /dev/null 2>&1 && echo "✓ pytest-cov installed" || echo "⚠ pytest-cov NOT installed - coverage report will be skipped"
  ```
* Expected result: pytest-asyncio installed
* Failure condition: pytest-asyncio not installed

❌ pytest-asyncio missing → **STOP IMMEDIATELY**

---

### Step 3 — Run Unit Tests

* Action: Execute unit test suite with verbose output
* Command:
  ```bash
  cd r-mos-backend && source venv/bin/activate
  echo "=== Running Unit Tests ==="
  pytest tests/unit -v --tb=short 2>&1
  ```
* Expected result: Test results displayed (pass or fail)
* Failure condition: pytest crashes (not test failures)

> ⚠️ Test failures are reported, not treated as skill failure.

---

### Step 4 — Run Key MVP Tests

* Action: Verify critical MVP test coverage
* Command:
  ```bash
  cd r-mos-backend && source venv/bin/activate
  echo "=== MVP Critical Tests ==="
  echo "Testing: Mock Adapter, TaskService, ScoringService"
  pytest tests/unit -v -k "adapter or task or scoring" --tb=short 2>&1 || true
  ```
* Expected result: Key tests executed
* Failure condition: None (informational step)

---

### Step 5 — Run Acceptance Tests (Optional)

* Action: Execute acceptance tests **IF directory exists**
* Command:
  ```bash
  cd r-mos-backend && source venv/bin/activate
  if [ -d "tests/acceptance" ]; then
    echo "=== Running Acceptance Tests ==="
    pytest tests/acceptance -v --tb=short 2>&1
  else
    echo "ℹ tests/acceptance/ not found - skipping acceptance tests"
    echo "  This is expected in early MVP phase"
  fi
  ```
* Expected result: Acceptance tests run OR skip message
* Failure condition: None (optional step)

---

### Step 6 — Generate Coverage Report (If Available)

* Action: Run tests with coverage measurement
* Command:
  ```bash
  cd r-mos-backend && source venv/bin/activate
  if pip show pytest-cov > /dev/null 2>&1; then
    echo "=== Coverage Report ==="
    pytest --cov=app --cov-report=term-missing tests/unit 2>&1
    echo ""
    echo "HTML report: htmlcov/index.html"
  else
    echo "⚠ pytest-cov not installed - skipping coverage report"
    echo "  Install with: pip install pytest-cov"
  fi
  ```
* Expected result: Coverage summary OR skip message
* Failure condition: None (graceful degradation)

---

### Step 7 — Summarize Results

* Action: Compile test results summary
* Output includes:
  - Total tests run
  - Passed / Failed / Skipped / Error counts
  - Coverage percentage (if available)
  - List of failed tests (if any)
  - Fixture issues (if any)
  - MVP criteria status
* Failure condition: None (always produces summary)

> ⚠️ Steps MUST be executed in order.
> Skipping or reordering is forbidden.

---

## 10. Exit Criteria & Output（裁决出口）

This skill MUST terminate immediately upon:

* pytest not installed (Step 1)
* tests/unit/ directory not found (Step 1)
* pytest-asyncio not installed (Step 2)
* Virtual environment activation failure

### Test Failure Handling

Test failures are **NOT** exit conditions. The skill MUST:
- Continue execution to completion
- Report all failures in final summary
- Distinguish between test failures and fixture/environment issues
- NOT attempt to fix failures

### Coverage Threshold (来源：拆包A §7)

| Metric | Target | Action if Below |
|--------|--------|-----------------|
| Line Coverage | > 80% | **WARN** in output |
| Target Source | 拆包A §7 验收标准 | — |

### Mandatory Output Format

```
[RESULT]
Status: PASS | FAIL | PARTIAL
Scope: Backend Tests
Version: 1.1.0

Environment:
  pytest: X.X.X
  pytest-asyncio: X.X.X
  pytest-cov: installed | NOT installed
  conftest.py: found | NOT found

Test Summary:
  Unit Tests:       X passed, Y failed, Z skipped, W errors
  Acceptance Tests: X passed, Y failed, Z skipped | SKIPPED (directory not found)
  Total:            X passed, Y failed, Z skipped, W errors

MVP Criteria Tests:
  Mock Adapter:     PASS | FAIL | NOT RUN
  TaskService:      PASS | FAIL | NOT RUN
  ScoringService:   PASS | FAIL | NOT RUN

Coverage: XX.X% | NOT AVAILABLE
  Target: > 80% (拆包A §7)
  Status: MEET | BELOW TARGET | NOT MEASURED

Failed Tests: (if any)
  - test_file.py::test_name - <failure reason>

Fixture Issues: (if any)
  - fixture 'xxx' not found - conftest.py may be missing

Coverage Report: htmlcov/index.html | NOT GENERATED

Next Recommended Action:
  - If fixture errors: Create tests/conftest.py with required fixtures
  - If coverage low: Add tests for uncovered code paths
  - If tests fail: Review test implementation (do NOT auto-fix)
```

---

## 11. Related Files / Interfaces（只读）

* `r-mos-backend/tests/unit/test_mock_adapter.py`
* `r-mos-backend/tests/unit/test_task_service.py`
* `r-mos-backend/tests/acceptance/` (may not exist)
* `r-mos-backend/tests/conftest.py` (may not exist)
* `r-mos-backend/pytest.ini` (may not exist)
* `r-mos-backend/pyproject.toml` (test configuration section, if exists)
* `r-mos-backend/requirements.txt` (test dependencies)

### Key Test Dependencies (from requirements.txt)

```
pytest>=8.0.0
pytest-asyncio>=0.24.0
httpx>=0.27.0  # For async HTTP testing
```

### Missing but Recommended

```
pytest-cov  # For coverage reports (not in requirements.txt)
```

---

## 12. Skill Invalidation Conditions（失效条件）

This skill becomes INVALID if:

* Test framework changes from pytest
* Test directory structure changes from `tests/unit/`
* Async test support changes from pytest-asyncio
* Coverage measurement tool changes
* CI/CD pipeline requires different test execution flow
* MVP phase ends and production test requirements differ
* New test categories added without skill update

Once invalid, this skill MUST NOT be executed without human review.

---
