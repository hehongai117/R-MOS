---
name: test-frontend
type: project-skill
project: R-MOS
phase: MVP
version: 1.0.0

description: >
  Execute the R-MOS frontend test suite in a controlled, read-only, and
  non-destructive manner. This skill runs unit tests, component tests, and
  generates coverage reports. It is designed for verification and quality
  assurance only, not for fixing or modifying code.

allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
---

# R-MOS Frontend Test Skill

---

## 1. Skill Purpose（目的与边界）

### Purpose

This skill exists to **execute and report** the R-MOS frontend test suite.

It provides:
- Unit test execution and result reporting
- Component test execution (if configured)
- Code coverage measurement and reporting
- Test failure diagnosis (read-only)
- TypeScript type checking verification

### Explicit Non-Goals

This skill MUST NOT:
- Modify any source code to fix failing tests
- Modify test files or test fixtures
- Create missing test configuration files
- Change test framework configuration
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
- Frontend: `React + TypeScript`
- Test framework: `Vitest` (primary) or `Jest` (alternative)
- Package Manager: `npm`

### Test Categories

| Category | Path | Status | Description |
|----------|------|--------|-------------|
| Unit Tests | `src/**/*.test.ts` | **Required** | Utility and hook tests |
| Component Tests | `src/**/*.test.tsx` | **Optional** | React component tests |
| Integration Tests | `tests/` or `__tests__/` | **Optional** | Cross-component tests |

### Mandatory Review / Expiration Conditions

This skill MUST be reviewed, restricted, or deprecated when:

- Test framework changes from Vitest/Jest
- Test directory structure changes
- New test categories are introduced (e.g., e2e with Playwright/Cypress)
- CI/CD pipeline is implemented
- Project enters production phase

---

## 3. Preconditions（硬前置条件）

ALL of the following MUST be true before execution:

**Hard Requirements (STOP if fail):**
- Frontend directory `r-mos-frontend/` exists
- `r-mos-frontend/package.json` exists
- `r-mos-frontend/node_modules/` exists (dependencies installed)
- Node.js installed and version ≥ 18

**Soft Requirements (WARN if fail, continue):**
- Test script defined in `package.json` (`test` or `test:unit`)
- Test configuration file exists (`vitest.config.ts` or `jest.config.js`)
- Coverage configuration exists
- TypeScript configuration valid

❌ If any **Hard Requirement** fails → **STOP IMMEDIATELY**

---

## 4. Explicit Triggers（明确触发条件）

This skill may ONLY be executed when at least one of the following occurs:

- User explicitly requests to run frontend tests
- User enters `/test-frontend` command
- User mentions "运行前端测试" or "run frontend tests"
- User asks to "check frontend test coverage"
- User asks "are the frontend tests passing?"
- User asks to verify frontend component behavior

⚠️ Vague or keyword-only mentions are NOT sufficient triggers.

---

## 5. Prohibited Behaviors（绝对禁止）

During execution, the AI MUST NOT:

- Modify source code (`.ts`, `.tsx`, `.js`, `.jsx`, `.json`)
- Modify test files or test utilities
- Create test configuration files (`vitest.config.ts`, `jest.config.js`)
- Change `package.json` scripts or dependencies
- Skip, ignore, or mark tests as expected failures
- Retry failed tests automatically
- Modify mock data or test fixtures
- Install packages without explicit permission
- Perform any "quick fixes" to make tests pass
- Interpret configuration errors as skill failures

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
  - Allowed: test commands listed in Section 7 "Allowed Test Commands"
  - Allowed: directory existence checks (`[ -d ... ]`, `ls`)
  - Allowed: `npx tsc --noEmit` (type checking)
  - Forbidden: file write, deletion
  - Forbidden: package install (unless explicitly allowed by user)
  - Forbidden: modifying test configuration

- **Read / Grep / Glob**
  - Inspection only
  - Locate test files and read test output
  - Check for configuration file existence
  - No inference beyond visible content

---

## 7. System References（不可变系统事实）

The following system facts are treated as **immutable** within this skill:

| Reference | Value | Source |
|-----------|-------|--------|
| Node.js Version | ≥ 18 | run-frontend skill |
| Frontend Directory | `r-mos-frontend/` | Project structure |
| Package Manager | npm | run-frontend skill |
| Test Framework | Vitest (primary) or Jest | package.json |
| Test File Pattern | `*.test.ts`, `*.test.tsx` | Convention |
| Coverage Target | > 70% (recommended) | No formal requirement in MVP |

### Allowed Test Commands

The following test commands may be executed:

- `npm test`
- `npm run test`
- `npm run test:unit`
- `npm run test:coverage`
- `npx vitest run`
- `npx vitest run --coverage`
- `npx jest`
- `npx jest --coverage`

❌ These facts MUST NOT be modified or "corrected" by the AI.

---

## 8. Data / Message / Interface Contract（强制契约）

### Test Result Contract (Vitest)

All Vitest executions MUST produce output conforming to:

```
 ✓ src/hooks/useWebSocket.test.ts (X tests)
 ✓ src/components/Task/StepCard.test.tsx (Y tests)

 Test Files  X passed (X)
 Tests       Y passed (Y)
 Duration    X.XXs
```

### Test Result Contract (Jest)

All Jest executions MUST produce output conforming to:

```
PASS src/hooks/useWebSocket.test.ts
  ✓ test name (Xms)

Test Suites: X passed, X total
Tests:       Y passed, Y total
```

### Coverage Report Contract

```
----------|---------|----------|---------|---------|
File      | % Stmts | % Branch | % Funcs | % Lines |
----------|---------|----------|---------|---------|
All files |   XX.XX |    XX.XX |   XX.XX |   XX.XX |
----------|---------|----------|---------|---------|
```

❌ Any deviation → **Report anomaly but continue**

---

## 9. Execution Plan（固定流程，不可跳步）

### Step 1 — Verify Project Structure

* Action: Check frontend directory and package.json existence
* Command:
  ```bash
  echo "=== Frontend Project Structure Check ==="
  [ -d "r-mos-frontend" ] && echo "✓ r-mos-frontend/ directory exists" || echo "✗ r-mos-frontend/ not found"
  [ -f "r-mos-frontend/package.json" ] && echo "✓ package.json exists" || echo "✗ package.json not found"
  [ -d "r-mos-frontend/node_modules" ] && echo "✓ node_modules exists" || echo "✗ node_modules not found - run npm install first"
  ```
* Expected result: Directory, package.json, and node_modules exist
* Failure condition: Directory or package.json not found

❌ Fail → **STOP IMMEDIATELY**

---

### Step 2 — Check Test Configuration

* Action: Verify test framework and scripts
* Command:
  ```bash
  cd r-mos-frontend
  echo "=== Test Configuration Check ==="

  # Check for test script in package.json
  if grep -q '"test"' package.json; then
    echo "✓ test script found in package.json"
  else
    echo "⚠ No test script in package.json"
  fi

  # Check for test framework config
  [ -f "vitest.config.ts" ] && echo "✓ vitest.config.ts found" || echo "ℹ vitest.config.ts not found"
  [ -f "vitest.config.js" ] && echo "✓ vitest.config.js found" || echo "ℹ vitest.config.js not found"
  [ -f "jest.config.js" ] && echo "✓ jest.config.js found" || echo "ℹ jest.config.js not found"
  [ -f "jest.config.ts" ] && echo "✓ jest.config.ts found" || echo "ℹ jest.config.ts not found"
  ```
* Expected result: Test script exists in package.json
* Failure condition: No test script defined

❌ No test script → **WARN and attempt npx vitest run**

---

### Step 3 — Discover Test Files

* Action: Find all test files in the project
* Command:
  ```bash
  cd r-mos-frontend
  echo "=== Test File Discovery ==="
  echo "Looking for *.test.ts and *.test.tsx files..."

  TEST_COUNT=$(find src -name "*.test.ts" -o -name "*.test.tsx" 2>/dev/null | wc -l)
  echo "Found $TEST_COUNT test file(s)"

  if [ "$TEST_COUNT" -gt 0 ]; then
    echo ""
    echo "Test files:"
    find src -name "*.test.ts" -o -name "*.test.tsx" 2>/dev/null
  else
    echo "⚠ No test files found in src/"
  fi
  ```
* Expected result: At least one test file found
* Failure condition: No test files found

⚠ No test files → **WARN and report** (not a skill failure)

---

### Step 4 — TypeScript Type Check

* Action: Run TypeScript compiler in check mode
* Command:
  ```bash
  cd r-mos-frontend
  echo "=== TypeScript Type Check ==="
  if [ -f "tsconfig.json" ]; then
    npx tsc --noEmit 2>&1 || true
    echo ""
    echo "Type check completed (errors above, if any)"
  else
    echo "⚠ tsconfig.json not found - skipping type check"
  fi
  ```
* Expected result: Type check passes or errors reported
* Failure condition: None (informational step)

---

### Step 5 — Run Unit Tests

* Action: Execute test suite
* Command:
  ```bash
  cd r-mos-frontend
  echo "=== Running Frontend Tests ==="

  # Try different test commands in order of preference
  if grep -q '"test"' package.json 2>/dev/null; then
    npm test -- --run 2>&1 || npm test 2>&1
  elif command -v vitest &> /dev/null || [ -f "node_modules/.bin/vitest" ]; then
    npx vitest run 2>&1
  elif command -v jest &> /dev/null || [ -f "node_modules/.bin/jest" ]; then
    npx jest 2>&1
  else
    echo "✗ No test runner found (vitest or jest)"
    echo "  Install with: npm install -D vitest"
  fi
  ```
* Expected result: Test results displayed
* Failure condition: Test runner not found

---

### Step 6 — Generate Coverage Report (If Available)

* Action: Run tests with coverage measurement
* Command:
  ```bash
  cd r-mos-frontend
  echo "=== Coverage Report ==="

  if grep -q '"test:coverage"' package.json 2>/dev/null; then
    npm run test:coverage 2>&1
  elif [ -f "node_modules/.bin/vitest" ]; then
    npx vitest run --coverage 2>&1 || echo "⚠ Coverage plugin may not be installed"
  elif [ -f "node_modules/.bin/jest" ]; then
    npx jest --coverage 2>&1
  else
    echo "⚠ Coverage report not available"
  fi
  ```
* Expected result: Coverage summary displayed
* Failure condition: None (graceful degradation)

---

### Step 7 — Summarize Results

* Action: Compile test results summary
* Output includes:
  - Total tests run
  - Passed / Failed / Skipped counts
  - Coverage percentage (if available)
  - List of failed tests (if any)
  - TypeScript errors (if any)
* Failure condition: None (always produces summary)

> ⚠️ Steps MUST be executed in order.
> Skipping or reordering is forbidden.

---

## 10. Exit Criteria & Output（裁决出口）

This skill MUST terminate immediately upon:

* Frontend directory not found (Step 1)
* package.json not found (Step 1)
* node_modules not found (Step 1)
* No test runner available and no test files exist

### Test Failure Handling

Test failures are **NOT** exit conditions. The skill MUST:
- Continue execution to completion
- Report all failures in final summary
- Distinguish between test failures and configuration issues
- NOT attempt to fix failures

### Coverage Threshold

| Metric | Target | Action if Below |
|--------|--------|-----------------|
| Line Coverage | > 70% (recommended) | **INFO** in output |
| Target Source | No formal MVP requirement | — |

### Mandatory Output Format

```
[RESULT]
Status: PASS | FAIL | PARTIAL | NO_TESTS
Scope: Frontend Tests
Version: 1.0.0

Environment:
  Node.js: vX.X.X
  Test Framework: vitest | jest | NOT FOUND
  Test Config: found | NOT found

Test Discovery:
  Test Files: X found
  Test Pattern: *.test.ts, *.test.tsx

TypeScript Check:
  Status: PASS | FAIL | SKIPPED
  Errors: X (if any)

Test Summary:
  Tests:    X passed, Y failed, Z skipped
  Duration: X.XXs

Coverage: XX.X% | NOT AVAILABLE
  Target: > 70%
  Status: MEET | BELOW TARGET | NOT MEASURED

Failed Tests: (if any)
  - src/path/file.test.ts > test name - <failure reason>

Next Recommended Action:
  - If no tests: Create test files following *.test.ts pattern
  - If coverage low: Add tests for uncovered components
  - If tests fail: Review test implementation (do NOT auto-fix)
```

---

## 11. Related Files / Interfaces（只读）

* `r-mos-frontend/package.json`
* `r-mos-frontend/vitest.config.ts` (if exists)
* `r-mos-frontend/jest.config.js` (if exists)
* `r-mos-frontend/tsconfig.json`
* `r-mos-frontend/src/**/*.test.ts`
* `r-mos-frontend/src/**/*.test.tsx`
* `r-mos-frontend/src/hooks/useWebSocket.ts` (testable hook)
* `r-mos-frontend/src/api/client.ts` (testable API client)
* `r-mos-frontend/src/store/taskStore.ts` (testable store)

---

## 12. Skill Invalidation Conditions（失效条件）

This skill becomes INVALID if:

* Test framework changes from Vitest/Jest
* Test file pattern changes from `*.test.ts(x)`
* Package manager changes from npm
* Frontend framework changes from React
* CI/CD pipeline requires different test execution flow
* MVP phase ends and production test requirements differ
* E2E testing is introduced (requires separate skill)

Once invalid, this skill MUST NOT be executed without human review.

---
