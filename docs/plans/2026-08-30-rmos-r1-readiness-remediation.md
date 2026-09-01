# R-MOS R1 Readiness Remediation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the reproducible WebSocket defects, complete every non-human A0–A6/R0 readiness action that can be completed honestly, and reduce the R1 gate to explicit human approvals and independent evidence where those are mandatory.

**Architecture:** Keep the current fail-closed identity boundary until M-03 authentication exists. Bound every WebSocket send so a stalled peer cannot stop subsequent telemetry or heartbeats, return delivery counts to callers, and make caller logs reflect actual delivery. Audit and research gates remain separate from product fixes: no code change automatically upgrades A0–A6, R0, or R1.

**Tech Stack:** Python 3.13.13, FastAPI/Starlette WebSocket, asyncio, pytest/pytest-asyncio, Markdown/YAML/JSON audit evidence.

**Execution status (2026-09-01):** Tasks 1–5 completed; Task 6 partially completed (five-domain first-pass discovery and current drift evidence completed, fixed-version G2/G5 and route saturation still open); Task 7 verification completed up to the database/user-controlled gates. A0 is `REOPENED / IN REVIEW`. The board has confirmed that the 10 questions supplied on 2026-09-01 remain a cross-stage audit question bank and that A0 M-AUD-06 will use separately issued questions. The bank is not automatically assigned to any stage and does not count toward any M-AUD-06 result. The current implementation recommendation is to close A0 evidence and stabilize the revised report before freezing the new A0 question set; this sequencing is not an additional requirement created by the board's latest decision. AG-02 through AG-05, A0 reapproval, A1–A6 reapproval, R0 and R1 remain blocked. Decision evidence: `docs/audit/evidence/2026-09-01-cross-stage-audit-question-bank-board-disposition-v0.1.0.md`.

### Task 1: Freeze the Current Snapshot and Gate Boundaries

**Files:**
- Create: `docs/plans/2026-08-30-rmos-r1-readiness-remediation.md`
- Read: `AGENTS.md`
- Read: `docs/testing/ACCEPTANCE_CHARTER.md`
- Read: `docs/plans/2026-08-26-rmos-complete-audit-and-modernization-board-directive-v0.2.0.md`

**Step 1:** Record branch, HEAD, status, Python interpreter and dependency versions.

**Step 2:** Confirm R1 requires both A6 and R0 approval and list the human-only AG-01 through AG-05 actions separately from code/research work.

**Step 3:** Run `git diff --check` and preserve a clean pre-change status.

### Task 2: Reproduce Stalled WebSocket Delivery

**Files:**
- Modify: `r-mos-backend/tests/unit/test_websocket_targeting.py`
- Read: `r-mos-backend/app/services/websocket_manager.py`

**Step 1: Write failing tests**

- Add a WebSocket double whose send never completes.
- Assert a directed send returns within the configured bound and removes the stalled connection.
- Assert telemetry continues for multiple batches for a healthy connection when another connection stalls.
- Assert heartbeat sends to healthy connections even when one connection stalls.

**Step 2: Run tests to verify RED**

Run:

```bash
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python -m pytest tests/unit/test_websocket_targeting.py -q
```

Expected: the new timeout/continuity tests fail because sends are currently unbounded and heartbeat delivery is serial.

### Task 3: Bound and Isolate WebSocket Sends

**Files:**
- Modify: `r-mos-backend/app/services/websocket_manager.py`
- Test: `r-mos-backend/tests/unit/test_websocket_targeting.py`

**Step 1:** Add a single small send timeout constant appropriate for the 5 Hz loop.

**Step 2:** Wrap telemetry, directed JSON, and heartbeat sends in bounded awaits.

**Step 3:** Run heartbeat sends concurrently, record failures, and disconnect stalled/broken peers without delaying healthy peers beyond the bound.

**Step 4: Run tests to verify GREEN**

Run the targeted WebSocket test file and require all tests to pass.

### Task 4: Make Delivery Results and Logs Truthful

**Files:**
- Modify: `r-mos-backend/app/services/websocket_manager.py`
- Modify: `r-mos-backend/app/services/identity/teacher_monitor.py`
- Modify: `r-mos-backend/tests/unit/test_websocket_targeting.py`
- Modify: `r-mos-backend/tests/unit/test_teacher_monitor.py`

**Step 1: Write failing tests**

- Assert `send_to_user` and `broadcast_to_channel` return the number delivered.
- Assert teacher-monitor logs `not delivered` when the returned count is zero and never logs `sent/published` for zero delivery.

**Step 2:** Run the focused tests and verify the new assertions fail.

**Step 3:** Return delivery counts and branch caller logs on the result.

**Step 4:** Re-run the focused tests and require GREEN.

### Task 5: Protect the Endpoint Pong Wiring

**Files:**
- Modify: `r-mos-backend/tests/unit/test_websocket_targeting.py`
- Read: `r-mos-backend/app/api/v1/endpoints/websocket.py`

**Step 1:** Add an endpoint-level test that sends the real pong frame through `_handle_websocket`, verifies the registered connection state is refreshed, and then disconnects.

**Step 2:** Temporarily verify the test fails if the endpoint handler call is absent; restore the source without committing the temporary mutation.

**Step 3:** Run the endpoint test and the complete WebSocket-focused test set.

### Task 6: Complete Non-Human A0–A6 and R0 Evidence Work

**Files:**
- Create: `docs/research/rmos-open-source-reference-v0.2.0/evidence/*.md`
- Modify only after primary-source verification: current R0 register/result/matrix/report files
- Modify: applicable A0–A6 evidence and current reports only when the underlying evidence actually changes

**Step 1:** Research six current software candidates against fixed-version OSS-G2/G5 evidence.

**Step 2:** Restore candidate discovery for D-01, D-02, D-05, D-06 and D-07 with query and elimination records.

**Step 3:** Keep every unsupported field UNKNOWN and every ineligible candidate unscored.

**Step 4:** Run the R0 mechanical validator and A0–A6 remediation gate.

**Step 5:** Do not mark A6 or R0 approved without the required user approval, independent scoring, delivery receipts and snapshot comparison.

### Task 7: Verification, Records and Commit

**Files:**
- Modify: `docs/testing/TEST_REPORT.md`
- Modify: `docs-archive/DEVELOPMENT_LOG.md`
- Modify: relevant current audit/research status files

**Step 1:** Run focused tests, then the full backend suite once; save exact command, commit, environment, counts and failures.

**Step 2:** Compare `git status` before and after tests; restore only test-generated changes already identified and leave all user changes untouched.

**Step 3:** Run document validators, `git diff --check`, link/path checks and inspect the final diff.

**Step 4:** Request an independent read-only review of the completed change.

**Step 5:** Update the development and test records with only observed results.

**Step 6:** Commit only task files locally. Do not push.

**Step 7:** Issue one of two final R1 readiness decisions:

- `READY FOR HUMAN GATE COMPLETION` when only mandated user/independent actions remain; or
- `BLOCKED` with exact technical/research evidence still missing.
