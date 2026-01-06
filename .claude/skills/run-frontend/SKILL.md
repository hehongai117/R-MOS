---
name: run-frontend
type: project-skill
project: R-MOS
phase: MVP
version: 1.0.0

description: >
  Initialize and start the R-MOS frontend development server in a reproducible,
  safe, and auditable manner. This skill verifies project structure, dependency
  integrity, and environment configuration before launching the frontend dev server.
  Use when user requests frontend startup or enters /run-frontend.

allowed-tools:
  - Bash
  - Read
  - Glob
---

# R-MOS Frontend Startup Skill

---

## 1. Skill Purpose（目的与边界）

### Purpose

This skill exists to **initialize and start** the R-MOS frontend development server with full pre-flight verification.

It guarantees:
- Project structure verified before startup
- Dependency integrity checked
- Environment configuration correctness
- Backend connectivity validation (optional)

### Explicit Non-Goals

This skill MUST NOT:
- Modify any source code files
- Change configuration defaults without explicit user consent
- Install global packages or modify system settings
- Perform any "quick fixes" or refactors
- Skip verification steps even if user requests
- Create or modify `package.json` or other config files
- Start backend service (use `/run-backend` for that)

> ⚠️ 如果一个行为不在 Purpose 中明确允许，则默认禁止。

---

## 2. Scope & Validity（适用范围）

This skill is valid ONLY under the following conditions:

- Project: `R-MOS`
- Phase: `MVP`
- Deployment model: `single-node / local`
- Target environment: `dev / test only`
- Frontend: `React + TypeScript`
- Package Manager: `npm` (primary) or `yarn` (if configured)
- Node.js: `18+`

### Supported Modes

- **Development (default)** — Hot reload enabled, development server
- **Production build** — Must be explicitly specified (not covered by this skill)

If no mode is specified, **Development mode is assumed**.

### Mandatory Review / Expiration Conditions

This skill MUST be reviewed, restricted, or deprecated when:

- Moving to containerized deployment (Docker / Kubernetes)
- Changing package manager (npm → pnpm / yarn)
- Changing build tool or bundler configuration
- Changing frontend framework (React → Vue / other)
- Entering production phase

---

## 3. Preconditions（硬前置条件）

ALL of the following MUST be true before execution:

**Hard Requirements (STOP if fail):**
- Frontend directory `r-mos-frontend/` exists
- `r-mos-frontend/package.json` exists
- Node.js installed and version ≥ 18
- Port `3000` is available (not in use) OR port specified in config

**Soft Requirements (WARN if fail, continue):**
- `r-mos-frontend/node_modules/` exists (will install if missing)
- Backend is running on port `8000` (for API connectivity)

❌ If any **Hard Requirement** fails → **STOP IMMEDIATELY**

---

## 4. Explicit Triggers（明确触发条件）

This skill may ONLY be executed when at least one of the following occurs:

- User explicitly requests to start frontend service
- User enters `/run-frontend` command
- User mentions "启动前端" or "start frontend"
- User asks to "run the dev server"
- User asks to "start the React app"

⚠️ Vague or keyword-only mentions are NOT sufficient triggers.

---

## 5. Prohibited Behaviors（绝对禁止）

During execution, the AI MUST NOT:

- Modify source code (`.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.json`)
- Modify configuration files (`package.json`, `vite.config.ts`, `tsconfig.json`)
- Change environment variables in `.env` without consent
- Perform refactors or "quick fixes"
- Execute repeated retries without instruction
- Skip any verification step
- Start frontend if any hard precondition fails
- Install global npm packages without explicit permission
- Upgrade or downgrade dependencies without explicit permission
- Modify `node_modules/` contents directly

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
  - Allowed: directory checks, node/npm version check, npm install, npm run dev
  - Allowed: read-only diagnostic commands (`curl`, `lsof`, `ps`)
  - Allowed: `npm install` (local, not global)
  - Forbidden: file write/delete (except `node_modules/` via npm install)
  - Forbidden: global package installation (`npm install -g`)
  - Forbidden: modifying `package.json` or config files

- **Read / Glob**
  - Inspection only
  - Verify file existence and content
  - No inference beyond visible content

---

## 7. System References（不可变系统事实）

The following system facts are treated as **immutable** within this skill:

| Reference | Value |
|-----------|-------|
| Node.js Version | ≥ 18 |
| Frontend Directory | `r-mos-frontend/` |
| Package Manager | npm |
| Dev Server Port | `3000` (default) |
| Backend API URL | `http://localhost:8000` |
| WebSocket URL | `ws://localhost:8000/ws/robot/status` |
| Start Command | `npm run dev` OR `npm start` (based on package.json scripts) |

❌ These facts MUST NOT be modified or "corrected" by the AI.

---

## 8. Data / Message / Interface Contract（强制契约）

### Backend Health Check Response Contract

When verifying backend connectivity, response MUST conform to:

```json
{
  "status": "healthy",
  "database": "connected",
  "adapter_connected": true
}
```

❌ Backend unreachable → **WARN but continue** (frontend can run without backend)

### Frontend Dev Server Expected Output

Successful startup should display server ready message with local URL.
Exact format depends on build tool (Vite, Create React App, etc.).

Key indicators of success:
- Server process starts without error
- Local URL displayed (typically http://localhost:3000)
- No compilation errors in console

---

## 9. Execution Plan（固定流程，不可跳步）

### Step 1 — Verify Project Structure

* Action: Check frontend directory and package.json existence
* Command:
  ```bash
  echo "=== Frontend Project Structure Check ==="
  [ -d "r-mos-frontend" ] && echo "✓ r-mos-frontend/ directory exists" || echo "✗ r-mos-frontend/ not found"
  [ -f "r-mos-frontend/package.json" ] && echo "✓ package.json exists" || echo "✗ package.json not found"
  ```
* Expected result: Both directory and package.json exist
* Failure condition: Directory or package.json not found

❌ Fail → **STOP IMMEDIATELY**

---

### Step 2 — Verify Node.js Version

* Action: Check Node.js installation and version
* Command:
  ```bash
  echo "=== Node.js Version Check ==="
  node --version
  NODE_MAJOR=$(node -v | cut -d'.' -f1 | sed 's/v//')
  [ "$NODE_MAJOR" -ge 18 ] && echo "✓ Node.js version OK (≥18)" || echo "✗ Node.js version too low (requires ≥18)"
  ```
* Expected result: Node.js 18+ installed
* Failure condition: Node.js not found or version < 18

❌ Fail → **STOP IMMEDIATELY**

---

### Step 3 — Check Port Availability

* Action: Verify port 3000 is not in use
* Command:
  ```bash
  echo "=== Port 3000 Check ==="
  lsof -i :3000 > /dev/null 2>&1 && echo "⚠ Port 3000 is in use" || echo "✓ Port 3000 is available"
  ```
* Expected result: Port 3000 available
* Failure condition: Port already in use

❌ Fail → **WARN and prompt user** (may need to kill existing process or use different port)

---

### Step 4 — Install Dependencies (If Needed)

* Action: Check node_modules and install if missing
* Command:
  ```bash
  cd r-mos-frontend
  if [ ! -d "node_modules" ]; then
    echo "⚠ node_modules not found, installing dependencies..."
    npm install
    echo "✓ Dependencies installed"
  else
    echo "✓ node_modules exists"
  fi
  ```
* Expected result: node_modules exists or successfully installed
* Failure condition: npm install fails

❌ Fail → **STOP IMMEDIATELY**

---

### Step 5 — Backend Connectivity Check (Optional)

* Action: Verify backend is running (optional, warn only)
* Command:
  ```bash
  echo "=== Backend Connectivity Check ==="
  curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1 && echo "✓ Backend is running" || echo "⚠ Backend not reachable (frontend can still start)"
  ```
* Expected result: Backend health check passes
* Failure condition: None (informational only)

---

### Step 6 — Start Frontend Dev Server

* Action: Launch development server
* Command:
  ```bash
  cd r-mos-frontend
  # Check available scripts and use appropriate command
  if grep -q '"dev"' package.json; then
    npm run dev
  elif grep -q '"start"' package.json; then
    npm start
  else
    echo "✗ No dev or start script found in package.json"
    exit 1
  fi
  ```
* Expected result: Dev server starts on port 3000
* Failure condition: npm run dev/start fails or no script found

---

### Step 7 — Post-Startup Verification (Optional)

* Action: Verify frontend is accessible
* Command:
  ```bash
  sleep 3
  curl -s http://localhost:3000 > /dev/null 2>&1 && echo "✓ Frontend is accessible" || echo "⚠ Frontend not responding yet"
  ```
* Expected result: Frontend responds to HTTP request
* Failure condition: None (informational only)

> ⚠️ Steps MUST be executed in order.
> Skipping or reordering is forbidden.

---

## 10. Exit Criteria & Output（裁决出口）

This skill MUST terminate immediately upon:

* Frontend directory not found (Step 1)
* package.json not found (Step 1)
* Node.js not installed or version < 18 (Step 2)
* npm install failure (Step 4)
* npm run dev failure (Step 6)

### Expected Service Endpoints

| Endpoint | URL |
|----------|-----|
| Frontend Dev Server | http://localhost:3000 |
| Backend API (if running) | http://localhost:8000 |
| API Docs (if backend running) | http://localhost:8000/docs |

### Mandatory Output Format

```
[RESULT]
Status: PASS | FAIL
Scope: Frontend Startup
Failed Step: (if applicable)
Root Cause: (if applicable)
Evidence: (error message or log)
Next Recommended Skill: (if applicable)
```

---

## 11. Related Files / Interfaces（只读）

* `r-mos-frontend/package.json`
* `r-mos-frontend/vite.config.ts` OR build config file (if exists)
* `r-mos-frontend/tsconfig.json`
* `r-mos-frontend/src/api/client.ts`
* `r-mos-frontend/src/hooks/useWebSocket.ts`
* `r-mos-frontend/.env` (if exists)
* `r-mos-frontend/.env.example` (if exists)

---

## 12. Skill Invalidation Conditions（失效条件）

This skill becomes INVALID if:

* Package manager changes from npm
* Build tool or bundler configuration changes significantly
* Frontend framework changes from React
* Dev server port configuration becomes dynamic
* Project enters production phase with different deployment model
* Frontend is containerized

Once invalid, this skill MUST NOT be executed without human review.

---
