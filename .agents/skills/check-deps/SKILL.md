---
name: check-deps
type: project-skill
project: R-MOS
phase: MVP
version: 1.0.0

description: >
  Verify and synchronize project dependencies for R-MOS backend and frontend.
  This skill checks dependency integrity, identifies missing packages, detects
  version mismatches, and optionally installs missing dependencies. Use when
  encountering import errors or before running the project after a git pull.

allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
---

# R-MOS Dependency Check Skill

---

## 1. Skill Purpose（目的与边界）

### Purpose

This skill exists to **verify and synchronize** project dependencies.

It provides:
- Backend Python dependency verification (pip/requirements.txt)
- Frontend Node.js dependency verification (npm/package.json)
- Missing package detection
- Version mismatch identification
- Optional dependency installation (with user confirmation)

### Explicit Non-Goals

This skill MUST NOT:
- Modify `requirements.txt` or `package.json`
- Upgrade or downgrade package versions
- Install global packages (system-wide)
- Add new dependencies not in manifest files
- Remove existing packages
- Modify virtual environment configuration
- Change Node.js or Python versions
- Perform any "quick fixes" to dependency issues

> ⚠️ 如果一个行为不在 Purpose 中明确允许，则默认禁止。

---

## 2. Scope & Validity（适用范围）

This skill is valid ONLY under the following conditions:

- Project: `R-MOS`
- Phase: `MVP`
- Deployment model: `single-node / local`
- Target environment: `dev / test only`
- Backend: `Python 3.10+ / pip / venv`
- Frontend: `Node.js 18+ / npm` (if initialized)

### Supported Operations

| Operation | Scope | Command |
|-----------|-------|---------|
| Check Backend | Python dependencies | `pip list` vs `requirements.txt` |
| Check Frontend | Node.js dependencies | `npm ls` vs `package.json` |
| Install Backend | Missing Python packages | `pip install -r requirements.txt` |
| Install Frontend | Missing Node.js packages | `npm install` |

### Mandatory Review / Expiration Conditions

This skill MUST be reviewed, restricted, or deprecated when:

- Package manager changes (pip → poetry, npm → pnpm/yarn)
- Dependency manifest format changes
- Virtual environment approach changes
- Moving to containerized deployment
- Entering production phase

---

## 3. Preconditions（硬前置条件）

ALL of the following MUST be true before execution:

**Hard Requirements (STOP if fail):**
- Project root directory exists
- At least one of the following is true:
  - Backend: `r-mos-backend/` exists with `requirements.txt`
  - Frontend: `r-mos-frontend/` exists with `package.json`

**For Backend Check (STOP if checking backend):**
- `r-mos-backend/venv/` exists and is activatable
- `r-mos-backend/requirements.txt` exists
- Python 3.10+ available

**For Frontend Check (STOP if checking frontend):**
- `r-mos-frontend/package.json` exists
- Node.js 18+ available
- npm available

❌ If any applicable **Hard Requirement** fails → **STOP IMMEDIATELY**

---

## 4. Explicit Triggers（明确触发条件）

This skill may ONLY be executed when at least one of the following occurs:

- User explicitly requests dependency check
- User enters `/check-deps` command
- User mentions "检查依赖" or "check dependencies"
- User encounters `ModuleNotFoundError` or `ImportError`
- User encounters `Cannot find module` error (Node.js)
- User asks "why is this import failing"
- User asks to "sync dependencies" after git pull
- User asks to "fix missing packages"

⚠️ Vague or keyword-only mentions are NOT sufficient triggers.

---

## 5. Prohibited Behaviors（绝对禁止）

During execution, the AI MUST NOT:

- Modify `requirements.txt` or `package.json`
- Upgrade package versions beyond what's specified
- Downgrade package versions
- Install global packages (`pip install --user`, `npm install -g`)
- Add packages not in manifest files
- Remove existing packages
- Modify `venv/` internals directly
- Modify `node_modules/` directly
- Change Python or Node.js versions
- Run `pip install <package>` for individual packages
- Run `npm install <package>` for individual packages
- Perform any "quick fixes"

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
  - Allowed: `pip list`, `pip show`, `pip check`
  - Allowed: `npm ls`, `npm outdated`
  - Allowed: `pip install -r requirements.txt` (ONLY with explicit user confirmation)
  - Allowed: `npm install` (ONLY with explicit user confirmation)
  - Allowed: version checks (`python --version`, `node --version`, `npm --version`)
  - Forbidden: `pip install <package>` (individual packages)
  - Forbidden: `npm install <package>` (individual packages)
  - Forbidden: `pip uninstall`, `npm uninstall`
  - Forbidden: global installs

- **Read / Grep / Glob**
  - Inspection only
  - Read manifest files
  - Compare versions

---

## 7. System References（不可变系统事实）

The following system facts are treated as **immutable** within this skill:

| Reference | Value |
|-----------|-------|
| Backend Directory | `r-mos-backend/` |
| Backend Venv | `r-mos-backend/venv/` |
| Backend Manifest | `r-mos-backend/requirements.txt` |
| Frontend Directory | `r-mos-frontend/` |
| Frontend Manifest | `r-mos-frontend/package.json` |
| Frontend Lock | `r-mos-frontend/package-lock.json` |
| Python Version | ≥ 3.10 |
| Node.js Version | ≥ 18 |

### Key Backend Dependencies (from requirements.txt)

| Package | Minimum Version | Purpose |
|---------|-----------------|---------|
| fastapi | ≥ 0.115.0 | Web framework |
| uvicorn | ≥ 0.30.0 | ASGI server |
| sqlalchemy | ≥ 2.0.30 | ORM |
| asyncpg | ≥ 0.30.0 | PostgreSQL async driver |
| alembic | ≥ 1.13.0 | Database migrations |
| pydantic | ≥ 2.9.0 | Data validation |
| pytest | ≥ 8.0.0 | Testing |

❌ These facts MUST NOT be modified or "corrected" by the AI.

---

## 8. Data / Message / Interface Contract（强制契约）

### Dependency Check Output Contract

All dependency checks MUST produce structured output:

```
=== Backend Dependency Check ===
Python Version: X.X.X (OK | FAIL)
Venv Status: active | not found
Installed Packages: N
Required Packages: M

Missing Packages:
  - package1
  - package2

Version Mismatches:
  - package3: installed=X.X.X, required>=Y.Y.Y

Status: OK | MISSING | MISMATCH
```

### Installation Confirmation Contract

Before any installation, MUST display:

```
The following operation will be performed:
  Command: pip install -r requirements.txt
  Scope: r-mos-backend/

Proceed? [User must confirm]
```

❌ Installation without confirmation → **FORBIDDEN**

---

## 9. Execution Plan（固定流程，不可跳步）

### Step 1 — Detect Project Structure

* Action: Identify which components exist
* Command:
  ```bash
  echo "=== Project Structure Check ==="
  [ -d "r-mos-backend" ] && echo "✓ Backend directory exists" || echo "✗ Backend directory not found"
  [ -f "r-mos-backend/requirements.txt" ] && echo "✓ requirements.txt exists" || echo "✗ requirements.txt not found"
  [ -d "r-mos-frontend" ] && echo "✓ Frontend directory exists" || echo "✗ Frontend directory not found"
  [ -f "r-mos-frontend/package.json" ] && echo "✓ package.json exists" || echo "✗ package.json not found"
  ```
* Expected result: At least one component detected
* Failure condition: Neither backend nor frontend found

❌ Fail → **STOP IMMEDIATELY**

---

### Step 2 — Check Backend Dependencies (If Exists)

* Action: Verify Python environment and dependencies
* Command:
  ```bash
  echo "=== Backend Dependency Check ==="

  # Check Python version
  echo "--- Python Version ---"
  python3 --version

  # Check venv
  echo "--- Virtual Environment ---"
  if [ -d "r-mos-backend/venv" ]; then
    echo "✓ venv directory exists"
    source r-mos-backend/venv/bin/activate
    echo "✓ venv activated"
  else
    echo "✗ venv not found"
    exit 1
  fi

  # Check installed vs required
  echo "--- Dependency Status ---"
  cd r-mos-backend
  pip check 2>&1 || true

  echo "--- Installed Packages ---"
  pip list --format=freeze | wc -l

  echo "--- Missing Packages Check ---"
  # Compare installed vs required
  echo "Checking for missing packages..."
  while IFS= read -r line; do
    pkg=$(echo "$line" | cut -d'>' -f1 | cut -d'=' -f1 | cut -d'[' -f1 | tr -d ' ')
    [ -z "$pkg" ] || [ "${pkg:0:1}" = "#" ] && continue
    pip show "$pkg" > /dev/null 2>&1 || echo "  ✗ Missing: $pkg"
  done < requirements.txt
  echo "Check complete"
  ```
* Expected result: All dependencies satisfied or missing packages listed
* Failure condition: venv not found

---

### Step 3 — Check Frontend Dependencies (If Exists)

* Action: Verify Node.js environment and dependencies
* Command:
  ```bash
  echo "=== Frontend Dependency Check ==="

  # Ensure we're in project root
  cd "$(dirname "$(pwd)")" 2>/dev/null || cd ..

  # Check Node.js version
  echo "--- Node.js Version ---"
  node --version
  npm --version

  # Check if frontend exists and has package.json
  if [ ! -f "r-mos-frontend/package.json" ]; then
    echo "⚠ Frontend not initialized (no package.json)"
    exit 0
  fi

  # Check node_modules
  echo "--- Dependencies Status ---"
  cd r-mos-frontend
  if [ -d "node_modules" ]; then
    echo "✓ node_modules exists"
    npm ls --depth=0 2>&1 | head -20
  else
    echo "⚠ node_modules not found - need to run npm install"
  fi

  # Check for missing dependencies
  echo "--- Missing Dependencies ---"
  npm ls 2>&1 | grep -E "WARN|ERR|missing" || echo "All dependencies satisfied"
  ```
* Expected result: All dependencies satisfied or issues listed
* Failure condition: None (informational)

---

### Step 4 — Generate Summary Report

* Action: Compile check results
* Output includes:
  - Backend status (OK / MISSING / ERROR)
  - Frontend status (OK / MISSING / NOT INITIALIZED)
  - List of missing packages (if any)
  - Recommended actions
* Failure condition: None

---

### Step 5 — Offer Installation (If Needed, With Confirmation)

* Action: If missing dependencies detected, **ASK USER** whether to install
* Note: This step is OPTIONAL - the skill can complete at Step 4 without installation
* User Interaction: Must use AskUserQuestion tool or wait for explicit user confirmation
* Condition: Only proceed if user explicitly confirms
* Backend Command:
  ```bash
  cd r-mos-backend && source venv/bin/activate
  pip install -r requirements.txt
  ```
* Frontend Command:
  ```bash
  cd r-mos-frontend
  npm install
  ```
* Expected result: Dependencies installed
* Failure condition: Installation error

⚠️ User MUST confirm before installation

> ⚠️ Steps MUST be executed in order.
> Skipping or reordering is forbidden.

---

## 10. Exit Criteria & Output（裁决出口）

This skill MUST terminate immediately upon:

* Neither backend nor frontend directory found
* Virtual environment not found (for backend check)
* Python version < 3.10 (for backend check)
* Node.js version < 18 (for frontend check)
* User declines installation

### Mandatory Output Format

```
[RESULT]
Status: PASS | WARN | FAIL
Scope: Dependency Check

Backend:
  Status: OK | MISSING | NOT FOUND
  Python: X.X.X
  Packages: N installed / M required
  Missing: [list or "none"]

Frontend:
  Status: OK | MISSING | NOT INITIALIZED | NOT FOUND
  Node.js: X.X.X
  npm: X.X.X
  Packages: N installed
  Missing: [list or "none"]

Recommended Actions:
  - [action 1]
  - [action 2]

Next Recommended Skill: (if applicable)
```

---

## 11. Related Files / Interfaces（只读）

* `r-mos-backend/requirements.txt`
* `r-mos-backend/venv/`
* `r-mos-backend/.env`
* `r-mos-frontend/package.json`
* `r-mos-frontend/package-lock.json`
* `r-mos-frontend/node_modules/`

---

## 12. Skill Invalidation Conditions（失效条件）

This skill becomes INVALID if:

* Package manager changes (pip → poetry, npm → pnpm/yarn)
* Dependency manifest format changes (requirements.txt → pyproject.toml)
* Virtual environment approach changes (venv → conda/virtualenv)
* Node.js version management changes (nvm integration)
* Moving to containerized deployment with different dependency management
* Project enters production phase with different deployment strategy

Once invalid, this skill MUST NOT be executed without human review.

---
