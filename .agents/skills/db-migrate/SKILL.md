---
name: db-migrate
type: project-skill
project: R-MOS
phase: MVP
version: 1.0.0

description: >
  Execute database migration operations for the R-MOS backend using Alembic.
  This skill handles migration generation (autogenerate), upgrade, downgrade,
  and status checking in a controlled, auditable manner. Use after creating
  new models with /new-model skill or when user requests database schema changes.

allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
---

# R-MOS Database Migration Skill

---

## 1. Skill Purpose（目的与边界）

### Purpose

This skill exists to **execute and manage** Alembic database migrations for the R-MOS backend.

It provides:
- Migration script generation (autogenerate from model changes)
- Migration upgrade (apply pending migrations)
- Migration downgrade (rollback migrations)
- Migration status checking (current version, pending migrations)
- Migration history viewing

### Explicit Non-Goals

This skill MUST NOT:
- Modify source code files (models, services, etc.)
- Modify Alembic configuration files (`alembic.ini`, `env.py`)
- Manually edit generated migration scripts
- Drop or truncate database tables directly
- Execute raw SQL statements outside of migrations
- Perform data migrations with business logic
- Change database connection settings
- Create or modify `.env` files

> ⚠️ 如果一个行为不在 Purpose 中明确允许，则默认禁止。

---

## 2. Scope & Validity（适用范围）

This skill is valid ONLY under the following conditions:

- Project: `R-MOS`
- Phase: `MVP`
- Deployment model: `single-node / local`
- Target environment: `dev / test only`
- ORM: `SQLAlchemy 2.0+ (Async)`
- Migration Tool: `Alembic`
- Database: `PostgreSQL 14+`

### Supported Operations

| Operation | Command | Description |
|-----------|---------|-------------|
| Generate | `alembic revision --autogenerate -m "<message>"` | Create migration from model changes |
| Upgrade | `alembic upgrade head` | Apply all pending migrations |
| Upgrade (specific) | `alembic upgrade <revision>` | Apply up to specific revision |
| Downgrade | `alembic downgrade -1` | Rollback one migration |
| Downgrade (specific) | `alembic downgrade <revision>` | Rollback to specific revision |
| Status | `alembic current` | Show current migration version |
| History | `alembic history` | Show migration history |

### Mandatory Review / Expiration Conditions

This skill MUST be reviewed, restricted, or deprecated when:

- ORM changes from SQLAlchemy
- Migration tool changes from Alembic
- Database changes from PostgreSQL
- Moving to containerized deployment
- Introducing multi-database architecture
- Entering production phase with different migration strategy

---

## 3. Preconditions（硬前置条件）

ALL of the following MUST be true before execution:

**Hard Requirements (STOP if fail):**
- Backend directory `r-mos-backend/` exists
- Virtual environment `r-mos-backend/venv/` exists
- `r-mos-backend/alembic.ini` exists
- `r-mos-backend/alembic/` directory exists
- `r-mos-backend/alembic/env.py` exists
- PostgreSQL service is running and accessible
- `.env` file exists with valid PostgreSQL configuration (POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB)

**Soft Requirements (WARN if fail, continue for status/history only):**
- `r-mos-backend/alembic/versions/` contains at least one migration

❌ If any **Hard Requirement** fails → **STOP IMMEDIATELY**

---

## 4. Explicit Triggers（明确触发条件）

This skill may ONLY be executed when at least one of the following occurs:

- User explicitly requests database migration
- User enters `/db-migrate` command
- User mentions "数据库迁移" or "database migration"
- User asks to "apply migrations" or "run migrations"
- User asks to "generate migration" after model changes
- Recommended by `/new-model` skill output
- User asks "what's the current database version"
- User asks to "rollback" or "downgrade" database

⚠️ Vague or keyword-only mentions are NOT sufficient triggers.

---

## 5. Prohibited Behaviors（绝对禁止）

During execution, the AI MUST NOT:

- Modify business source code (`app/`, `tests/`, config files)
- Note: Alembic-generated migration scripts in `alembic/versions/` are the only writable files
- Edit existing migration files (only generate new ones)
- Modify `alembic.ini` or `env.py`
- Execute `DROP TABLE`, `TRUNCATE`, or destructive raw SQL
- Run `alembic downgrade base` (REFUSE - too dangerous, destroys all tables)
- Perform multiple downgrades without explicit confirmation for each
- Change database connection settings
- Modify `.env` file
- Skip precondition verification steps
- Retry failed migrations automatically
- Perform "quick fixes" to migration scripts

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
  - Allowed: alembic commands (revision, upgrade, downgrade, current, history)
  - Allowed: database connectivity check
  - Allowed: read-only diagnostic commands
  - Forbidden: raw SQL execution via psql
  - Forbidden: file write/delete outside of alembic commands
  - Forbidden: editing migration files manually

- **Read / Grep / Glob**
  - Inspection only
  - Read migration files to verify content
  - Check model files for changes
  - No inference beyond visible content

---

## 7. System References（不可变系统事实）

The following system facts are treated as **immutable** within this skill:

| Reference | Value |
|-----------|-------|
| Backend Directory | `r-mos-backend/` |
| Virtual Environment | `r-mos-backend/venv/` |
| Alembic Config | `r-mos-backend/alembic.ini` |
| Alembic Directory | `r-mos-backend/alembic/` |
| Migrations Directory | `r-mos-backend/alembic/versions/` |
| Alembic Env File | `r-mos-backend/alembic/env.py` |
| Database | PostgreSQL 14+ |
| ORM | SQLAlchemy 2.0+ (Async) |
| Migration Naming | `YYYYMMDD_HHMM_<rev>_<slug>.py` |

### Model Files (来源：拆包A, 拆包B)

| Model | File |
|-------|------|
| Base, TimestampMixin | `app/models/base.py` |
| Task | `app/models/task.py` |
| SOP | `app/models/sop.py` |
| Event | `app/models/event.py` |
| Snapshot | `app/models/snapshot.py` |
| Fault | `app/models/fault.py` |

❌ These facts MUST NOT be modified or "corrected" by the AI.

---

## 8. Data / Message / Interface Contract（强制契约）

### Migration Script Contract

All generated migration scripts MUST contain:

```python
"""<description>

Revision ID: <revision>
Revises: <previous_revision or None>
Create Date: <timestamp>
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '<revision>'
down_revision = '<previous_revision>'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # ... upgrade operations

def downgrade() -> None:
    # ... downgrade operations
```

### Alembic Command Output Contract

| Command | Success Indicator |
|---------|-------------------|
| `alembic current` | Displays revision hash |
| `alembic upgrade head` | "Running upgrade" or "Already at head" |
| `alembic downgrade -1` | "Running downgrade" |
| `alembic history` | List of revision entries |
| `alembic revision --autogenerate` | "Generating ... done" |

❌ Any deviation → **Report error and STOP**

---

## 9. Execution Plan（固定流程，不可跳步）

### Operation: Generate Migration

#### Step 1 — Verify Environment

* Action: Check alembic installation and database connectivity
* Command:
  ```bash
  cd r-mos-backend && source venv/bin/activate
  echo "=== Alembic Version ==="
  alembic --version
  echo ""
  echo "=== Database Connectivity ==="
  python3 << 'EOF'
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
    print("✓ Database connection: OK")
except Exception as e:
    print(f"✗ Database connection FAILED: {e}")
    exit(1)
EOF
  ```
* Expected result: Alembic version displayed, database connected
* Failure condition: Alembic not found or database connection failed

❌ Fail → **STOP IMMEDIATELY**

---

#### Step 2 — Check Current Status

* Action: Show current migration version
* Command:
  ```bash
  cd r-mos-backend && source venv/bin/activate
  echo "=== Current Migration Version ==="
  alembic current
  echo ""
  echo "=== Pending Migrations ==="
  alembic history --indicate-current
  ```
* Expected result: Current version displayed
* Failure condition: None (informational)

---

#### Step 3 — Generate Migration (If Requested)

* Action: Generate new migration script
* Command:
  ```bash
  cd r-mos-backend && source venv/bin/activate
  alembic revision --autogenerate -m "<user_provided_message>"
  ```
* Expected result: New migration file created in `alembic/versions/`
* Failure condition:
  - User did not provide migration message → STOP and request message
  - Autogenerate fails (no changes detected or model import error)

❌ User MUST provide migration message → If not provided, STOP and request

---

#### Step 4 — Review Generated Migration

* Action: Display generated migration for user review
* Command:
  ```bash
  cd r-mos-backend
  ls -lt alembic/versions/*.py | head -1
  # Read the newest migration file
  ```
* Expected result: Migration content displayed
* Failure condition: None

---

### Operation: Upgrade

#### Step 1 — Verify Environment

(Same as Generate Step 1)

---

#### Step 2 — Check Pending Migrations

* Action: Show pending migrations before applying
* Command:
  ```bash
  cd r-mos-backend && source venv/bin/activate
  echo "=== Current Version ==="
  alembic current
  echo ""
  echo "=== Migration History ==="
  alembic history --indicate-current
  ```
* Expected result: Migration history displayed
* Failure condition: None

---

#### Step 3 — Apply Migrations

* Action: Upgrade to head (or specific revision)
* Command:
  ```bash
  cd r-mos-backend && source venv/bin/activate
  alembic upgrade head
  ```
* Expected result: "Running upgrade" messages or "Already at head"
* Failure condition: Migration script error

❌ Fail → **STOP and report error**

---

#### Step 4 — Verify Upgrade

* Action: Confirm new version
* Command:
  ```bash
  cd r-mos-backend && source venv/bin/activate
  echo "=== New Current Version ==="
  alembic current
  ```
* Expected result: Version updated
* Failure condition: Version unchanged after upgrade command

---

### Operation: Downgrade

#### Step 1 — Verify Environment

(Same as Generate Step 1)

---

#### Step 2 — Confirm Current Version

* Action: Show what will be downgraded
* Command:
  ```bash
  cd r-mos-backend && source venv/bin/activate
  echo "=== Current Version (will be downgraded) ==="
  alembic current
  echo ""
  echo "=== Migration History ==="
  alembic history --indicate-current
  ```
* Expected result: Current version displayed
* Failure condition: None

---

#### Step 3 — Execute Downgrade

* Action: Downgrade one revision (or to specific revision)
* Command:
  ```bash
  cd r-mos-backend && source venv/bin/activate
  alembic downgrade -1
  ```
* Expected result: "Running downgrade" message
* Failure condition: Downgrade script error

⚠️ User MUST confirm before downgrade

❌ Fail → **STOP and report error**

---

#### Step 4 — Verify Downgrade

* Action: Confirm version after downgrade
* Command:
  ```bash
  cd r-mos-backend && source venv/bin/activate
  echo "=== Version After Downgrade ==="
  alembic current
  ```
* Expected result: Version changed to previous
* Failure condition: None

> ⚠️ Steps MUST be executed in order.
> Skipping or reordering is forbidden.

---

## 10. Exit Criteria & Output（裁决出口）

This skill MUST terminate immediately upon:

* Alembic not installed (Step 1)
* Database connection failure (Step 1)
* Alembic directory structure invalid
* Migration generation failure (autogenerate)
* Migration upgrade/downgrade failure
* User cancellation

### Dangerous Operations Requiring Explicit Confirmation

| Operation | Confirmation Required |
|-----------|----------------------|
| `alembic downgrade -1` | Yes - warn about data loss potential |
| `alembic downgrade <revision>` | Yes - warn about multiple rollbacks |
| `alembic downgrade base` | **REFUSE** - too dangerous for MVP |

### Mandatory Output Format

```
[RESULT]
Status: PASS | FAIL
Scope: Database Migration
Operation: generate | upgrade | downgrade | status

Before:
  Version: <revision_before>

After:
  Version: <revision_after>

Generated File: (if applicable)
  <path_to_new_migration>

Failed Step: (if applicable)
Root Cause: (if applicable)
Evidence: (error message or log)

Next Recommended Action:
  - Review migration script before applying
  - Run /test-backend to verify schema changes
```

---

## 11. Related Files / Interfaces（只读）

* `r-mos-backend/alembic.ini`
* `r-mos-backend/alembic/env.py`
* `r-mos-backend/alembic/versions/*.py`
* `r-mos-backend/app/models/base.py`
* `r-mos-backend/app/models/task.py`
* `r-mos-backend/app/models/sop.py`
* `r-mos-backend/app/models/event.py`
* `r-mos-backend/app/models/snapshot.py`
* `r-mos-backend/app/models/fault.py`
* `r-mos-backend/.env`
* `r-mos-backend/app/core/database.py`

---

## 12. Skill Invalidation Conditions（失效条件）

This skill becomes INVALID if:

* Alembic is replaced with another migration tool
* SQLAlchemy is replaced with another ORM
* Database changes from PostgreSQL
* Migration directory structure changes
* Async database pattern changes
* Multi-database architecture is introduced
* Project enters production phase with CI/CD migration pipeline

Once invalid, this skill MUST NOT be executed without human review.

---
