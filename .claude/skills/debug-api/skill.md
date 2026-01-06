---
name: debug-api
type: project-skill
project: R-MOS
phase: MVP
version: 1.0.0

description: >
  Debug and validate the R-MOS REST API endpoints in a controlled,
  read-only, non-destructive manner. This skill is designed for diagnosis,
  verification, and fault localization of API responses only.

allowed-tools:
  - Bash
  - Read
  - Grep
---

# R-MOS REST API Debug Skill

---

## 1. Skill Purpose（目的与边界）

### Purpose
This skill exists to **verify, observe, and diagnose** the R-MOS REST API endpoints.

### Explicit Non-Goals
This skill MUST NOT:
- Modify source code
- Modify schemas or data models
- Change configuration values or environment variables
- Apply fixes, patches, or refactors
- Create, update, or delete database records
- Perform load testing or stress testing

> ⚠️ 如果一个行为不在 Purpose 中明确允许，则默认禁止。

---

## 2. Scope & Validity（适用范围）

This skill is valid ONLY under the following conditions:

- Project: `R-MOS`
- Phase: `MVP`
- Deployment model: `single-node / local`
- Target environment: `dev / test only`
- Backend: `Single FastAPI instance`
- Adapter: `Mock Adapter only`

### Mandatory Review / Expiration Conditions

This skill MUST be reviewed, restricted, or deprecated when:

- Moving to multi-node or distributed deployment
- Introducing Docker / Kubernetes orchestration
- Connecting real robot hardware adapters
- Changing API versioning scheme (currently `/api/v1/`)
- Modifying authentication/authorization model

---

## 3. Preconditions（硬前置条件）

ALL of the following MUST be true before execution:

- Backend directory `r-mos-backend/` exists
- Backend process is running on port `8000`
- Health endpoint `/api/v1/health` returns HTTP 200
- Target is API validation only (not performance testing)

❌ If any precondition fails → **STOP IMMEDIATELY**

---

## 4. Explicit Triggers（明确触发条件）

This skill may ONLY be executed when at least one of the following occurs:

- API endpoint returns unexpected HTTP status code
- API response body does not match expected schema
- API endpoint timeout or connection refused
- Frontend receives malformed or missing data from API
- User explicitly requests API debugging with specific endpoint path
- REST API behaves differently than documented

⚠️ Vague or keyword-only mentions are NOT sufficient triggers.

---

## 5. Prohibited Behaviors（绝对禁止）

During execution, the AI MUST NOT:

- Modify source code (`.py`, `.ts`, `.js`, `.json`)
- Modify Pydantic schemas or SQLAlchemy models
- Change configuration defaults or `.env` files
- Perform refactors or "quick fixes"
- Execute repeated retries without explicit instruction
- Call any of the following write endpoints:
  - `POST /api/v1/tasks` (create task)
  - `POST /api/v1/tasks/{task_id}/start` (start task)
  - `POST /api/v1/tasks/{task_id}/step` (execute step)
  - `POST /api/v1/tasks/{task_id}/pause` (pause task)
  - `POST /api/v1/tasks/{task_id}/resume` (resume task)
  - `POST /api/v1/adapter/inject-fault` (inject fault)
  - `DELETE /api/v1/adapter/fault/{fault_code}` (clear fault)

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
  - Allowed: `curl` with GET requests, `curl` with `-I` (headers only)
  - Allowed: `jq` for JSON parsing
  - Forbidden: file write, deletion, package install
  - Forbidden: calling any endpoint listed in Section 5 "Prohibited Behaviors"

- **Read / Grep**
  - Inspection only
  - No inference beyond visible content

---

## 7. System References（不可变系统事实）

The following system facts are treated as **immutable** within this skill:

Based on **R-MOS MVP Skeleton Document V2.3**:

- API Base URL: `http://localhost:8000/api/v1/`

### Allowed GET Endpoints (read-only whitelist)

The following GET endpoints may be called by this skill:

- Health Endpoint: `GET /api/v1/health`
- Adapter Endpoints:
  - `GET /api/v1/adapter/info`
  - `GET /api/v1/adapter/structure`
  - `GET /api/v1/adapter/faults`
- Task Endpoints:
  - `GET /api/v1/tasks/{task_id}`
  - `GET /api/v1/tasks/{task_id}/report`
- SOP Endpoints:
  - `GET /api/v1/sops`
  - `GET /api/v1/sops/{sop_id}`
- Fault Case Endpoints:
  - `GET /api/v1/fault-cases`

❌ These facts MUST NOT be modified or "corrected" by the AI.

---

## 8. Data / Message / Interface Contract（强制契约）

### Health Response Schema

All `/api/v1/health` responses MUST conform to:

```json
{
  "status": "healthy | degraded | unhealthy",
  "timestamp": "ISO-8601 UTC",
  "version": "string",
  "checks": {
    "adapter": {
      "status": "up | down",
      "message": "string | null",
      "details": "object | null"
    },
    "system": {
      "status": "up | down",
      "message": "string | null"
    }
  }
}
```

### Adapter Info Response Schema

All `/api/v1/adapter/info` responses MUST conform to:

```json
{
  "robot_id": "string",
  "model": "string",
  "firmware_version": "string",
  "serial_number": "string"
}
```

❌ Any deviation → **FAIL and STOP**

---

## 9. Execution Plan（固定流程，不可跳步）

### Step 1 — Health Check

* Action: Execute `curl -s http://localhost:8000/api/v1/health`
* Expected result: HTTP 200, `status == "healthy"`, `checks.adapter.status == "up"`
* Failure condition: Non-200 status, unhealthy status, or adapter down

---

### Step 2 — Target Endpoint Reachability

* Action: Execute `curl -I http://localhost:8000/api/v1/{target_endpoint}`
* Constraint: `{target_endpoint}` MUST be from Section 7 whitelist
* Expected result: HTTP 200 or expected status code for the endpoint
* Failure condition: Connection refused, timeout, or unexpected HTTP status

---

### Step 3 — Response Schema Validation

* Action: Execute `curl -s http://localhost:8000/api/v1/{target_endpoint}` and parse with `jq`
* Constraint: `{target_endpoint}` MUST be from Section 7 whitelist
* Expected result: Response body matches documented schema
* Failure condition: Missing required fields, wrong field types

---

### Step 4 — Response Content Verification

* Action: Inspect response values against expected business rules
* Expected result: Values are within expected ranges and formats
* Failure condition: Invalid timestamps, out-of-range values, malformed IDs

---

### Step 5 — Source Code Correlation (Optional)

Execute ONLY if:
* Previous steps fail and user requests root cause analysis

* Action: Read relevant endpoint source file
* Expected result: Identify code path that produces the error
* Failure condition: Cannot locate relevant code

> ⚠️ Steps MUST be executed in order.
> Skipping or reordering is forbidden.

---

## 10. Exit Criteria & Output（裁决出口）

This skill MUST terminate immediately upon:

* Schema mismatch detected
* Endpoint unreachable
* Unexpected HTTP status code
* Response validation failure

### Mandatory Output Format

```
[RESULT]
Status: PASS | FAIL
Endpoint: <tested endpoint path>
HTTP Status: <status code>
Root Cause: <if FAIL, describe the issue>
Evidence: <relevant response snippet or error>
Next Recommended Skill: <debug-websocket | run-backend | test-backend | none>
```

---

## 11. Related Files / Interfaces（只读）

* `app/api/v1/__init__.py`
* `app/api/v1/endpoints/health.py`
* `app/api/v1/endpoints/adapter.py`
* `app/api/v1/endpoints/tasks.py`
* `app/api/v1/endpoints/sops.py`
* `app/api/v1/endpoints/fault_cases.py`
* `app/core/exceptions.py`
* `app/schemas/`

---

## 12. Skill Invalidation Conditions（失效条件）

This skill becomes INVALID if:

* API versioning changes from `/api/v1/`
* Backend port changes from `8000`
* Health endpoint path changes
* Major schema version upgrade occurs
* System enters non-MVP phase

Once invalid, this skill MUST NOT be executed without human review.

---
