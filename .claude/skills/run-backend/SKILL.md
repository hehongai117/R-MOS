---
name: run-backend
type: project-skill
project: R-MOS
phase: MVP
version: 1.0.0

description: >
  Initialize and start the R-MOS backend service in a reproducible, safe, and
  auditable manner. This skill verifies database connectivity, environment
  configuration, dependency integrity, and schema consistency before launching
  the backend. Use when user requests backend startup or enters /run-backend.

allowed-tools:
  - Bash
  - Read
  - Glob
---

# R-MOS Backend Startup Skill

---

## 1. Skill Purpose（目的与边界）

### Purpose

This skill exists to **initialize and start** the R-MOS backend service with full pre-flight verification.

It guarantees:
- Database connectivity verified before startup
- Environment configuration correctness
- Dependency integrity
- Database schema consistency

### Explicit Non-Goals

This skill MUST NOT:
- Modify any source code files
- Change database schema definitions
- Alter configuration defaults without explicit user consent
- Perform any "quick fixes" or refactors
- Skip verification steps even if user requests

> ⚠️ 如果一个行为不在 Purpose 中明确允许，则默认禁止。

---

## 2. Scope & Validity（适用范围）

This skill is valid ONLY under the following conditions:

- Project: `R-MOS`
- Phase: `MVP`
- Deployment model: `single-node / local`
- Target environment: `dev / test only`
- Backend: `Python 3.10+ / FastAPI`
- Database: `PostgreSQL 14+`
- Adapter: `Mock Adapter`

### Supported Modes

- **Development (default)** — Hot reload enabled
- **Production** — Must be explicitly specified

If no mode is specified, **Development mode is assumed**.

### Mandatory Review / Expiration Conditions

This skill MUST be reviewed, restricted, or deprecated when:

- Moving to containerized deployment (Docker / Kubernetes)
- Introducing real robot hardware adapters
- Changing database engine or ORM
- Migrating to multi-node architecture
- Entering production phase

---

## 3. Preconditions（硬前置条件）

ALL of the following MUST be true before execution:

- Backend directory `r-mos-backend/` exists
- Virtual environment `r-mos-backend/venv/` exists
- PostgreSQL service is running and accessible
- Port `8000` is available (not in use)
- `.env.example` file exists (for fallback)

❌ If any precondition fails → **STOP IMMEDIATELY**

---

## 4. Explicit Triggers（明确触发条件）

This skill may ONLY be executed when at least one of the following occurs:

- User explicitly requests to start backend service
- User enters `/run-backend` command
- User mentions "启动后端" or "start backend"
- User asks to "run the API server"

⚠️ Vague or keyword-only mentions are NOT sufficient triggers.

---

## 5. Prohibited Behaviors（绝对禁止）

During execution, the AI MUST NOT:

- Modify source code (`.py`, `.ts`, `.js`, `.json`)
- Modify schemas or data models
- Change configuration defaults in `.env` without consent
- Perform refactors or "quick fixes"
- Execute repeated retries without instruction
- Skip any verification step
- Start backend if any verification fails
- Install system-level packages without explicit permission

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
  - Allowed: health checks, venv activation, pip install, alembic migrate, start server
  - Allowed: read-only diagnostic commands (`curl`, `lsof`, `ps`)
  - Forbidden: file write/delete (except `.env` copy from `.env.example`)
  - Forbidden: system package installation (`apt`, `brew`, etc.)

- **Read / Glob**
  - Inspection only
  - Verify file existence and content
  - No inference beyond visible content

---

## 7. System References（不可变系统事实）

The following system facts are treated as **immutable** within this skill:

| Reference | Value |
|-----------|-------|
| Python Version | ≥ 3.10 |
| PostgreSQL Version | ≥ 14 |
| Backend Directory | `r-mos-backend/` |
| Virtual Environment | `r-mos-backend/venv/` |
| Backend Port | `8000` |
| Health Endpoint | `/api/v1/health` |
| WebSocket Endpoint | `/ws/robot/status` |
| API Docs | `/docs` |

❌ These facts MUST NOT be modified or "corrected" by the AI.

---

## 8. Data / Message / Interface Contract（强制契约）

### Health Check Response Contract

All health check responses MUST conform to:

```json
{
  "status": "healthy",
  "database": "connected",
  "adapter_connected": true
}
```

❌ Any deviation → **WARN but continue** (health check is post-startup verification)

---

## 9. Execution Plan（固定流程，不可跳步）

### Step 1 — PostgreSQL Connection Check

* Action: Verify database connectivity using Python script
* Command:
  ```bash
  cd r-mos-backend && source venv/bin/activate && python3 << 'EOF'
  import os
  from dotenv import load_dotenv
  load_dotenv()

  try:
      import psycopg2
      conn = psycopg2.connect(
          host=os.getenv("POSTGRES_HOST", "localhost"),
          port=os.getenv("POSTGRES_PORT", "5432"),
          user=os.getenv("POSTGRES_USER", "postgres"),
          password=os.getenv("POSTGRES_PASSWORD", ""),
          dbname=os.getenv("POSTGRES_DB", "rmos")
      )
      conn.close()
      print("✓ PostgreSQL connection: OK")
  except Exception as e:
      print(f"✗ PostgreSQL connection FAILED: {e}")
      exit(1)
  EOF
  ```
* Expected result: "PostgreSQL connection: OK"
* Failure condition: Connection exception or exit code 1

❌ Fail → **STOP IMMEDIATELY**

---

### Step 2 — Validate `.env` File

* Action: Check if `.env` exists, create from `.env.example` if missing
* Command:
  ```bash
  cd r-mos-backend
  if [ ! -f .env ]; then
    echo "⚠ .env not found, creating from .env.example"
    cp .env.example .env
  else
    echo "✓ .env file exists"
  fi
  ```
* Expected result: `.env` file exists
* Failure condition: Neither `.env` nor `.env.example` exists

---

### Step 3 — Activate Virtual Environment

* Action: Activate venv and verify Python version
* Command:
  ```bash
  source r-mos-backend/venv/bin/activate
  python --version
  ```
* Expected result: Python 3.10+ version displayed
* Failure condition: venv directory does not exist

❌ Fail → **STOP and prompt user to create venv**

---

### Step 4 — Install Dependencies

* Action: Upgrade pip and install requirements
* Command:
  ```bash
  cd r-mos-backend && source venv/bin/activate
  pip install --upgrade pip -q
  pip install -r requirements.txt -q
  echo "✓ Dependencies installed"
  ```
* Expected result: All packages installed without error
* Failure condition: pip install returns non-zero exit code

---

### Step 5 — Run Database Migrations

* Action: Execute Alembic migrations
* Command:
  ```bash
  cd r-mos-backend && source venv/bin/activate
  alembic upgrade head
  ```
* Expected result: "Done" or already at head
* Failure condition: Migration error or conflict

❌ Fail → **STOP IMMEDIATELY**

---

### Step 6 — Start Backend Service

* Action: Launch FastAPI application
* Command:
  ```bash
  cd r-mos-backend && source venv/bin/activate
  python main.py
  ```
* Expected result: Server starts on port 8000
* Failure condition: Import error or port already in use

---

### Step 7 — Post-Startup Verification (Optional)

* Action: Verify health endpoint responds correctly
* Command:
  ```bash
  curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
  ```
* Expected result: JSON with `status: healthy`
* Failure condition: Connection refused or invalid JSON

> ⚠️ Steps MUST be executed in order.
> Skipping or reordering is forbidden.

---

## 10. Exit Criteria & Output（裁决出口）

This skill MUST terminate immediately upon:

* PostgreSQL connection failure (Step 1)
* Virtual environment not found (Step 3)
* Alembic migration failure (Step 5)
* Port 8000 already in use (Step 6)

### Expected Service Endpoints

| Endpoint | URL |
|----------|-----|
| Backend Service | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Health Check | http://localhost:8000/api/v1/health |
| WebSocket | ws://localhost:8000/ws/robot/status |

### Mandatory Output Format

```
[RESULT]
Status: PASS | FAIL
Scope: Backend Startup
Failed Step: (if applicable)
Root Cause: (if applicable)
Evidence: (error message or log)
Next Recommended Skill: (if applicable)
```

---

## 11. Related Files / Interfaces（只读）

* `r-mos-backend/main.py`
* `r-mos-backend/.env`
* `r-mos-backend/.env.example`
* `r-mos-backend/requirements.txt`
* `r-mos-backend/alembic/`
* `r-mos-backend/alembic.ini`
* `r-mos-backend/app/core/config.py`
* `r-mos-backend/app/core/database.py`

---

## 12. Skill Invalidation Conditions（失效条件）

This skill becomes INVALID if:

* Backend entry point changes from `main.py`
* Database engine changes from PostgreSQL
* Virtual environment path changes
* Port configuration becomes dynamic
* Project enters production phase with different deployment model

Once invalid, this skill MUST NOT be executed without human review.

---
