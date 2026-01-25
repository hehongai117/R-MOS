# Run Project and Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Start backend + frontend successfully, then identify and delete unused files outside `robot/` per user instruction.

**Architecture:** Keep changes isolated to a worktree. Bring up backend (FastAPI + Postgres) and frontend (Vite + React) using the existing README steps. Produce a cleanup candidate list, confirm with the user, then delete only approved items outside `robot/`.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, PostgreSQL, Node.js 18+, React, Vite.

### Task 1: Verify prerequisites and install dependencies

**Files:**
- Create: `r-mos-backend/venv/`
- Create: `r-mos-frontend/node_modules/`

**Step 1: Check versions**

Run:
```bash
python -V
node -v
npm -v
```
Expected: Python >= 3.11, Node >= 18.

**Step 2: Backend venv + deps**

Run:
```bash
cd r-mos-backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
Expected: Dependencies install without errors.

**Step 3: Frontend deps**

Run:
```bash
cd ../r-mos-frontend
npm install
```
Expected: `node_modules/` created, install completes.

### Task 2: Configure and run backend

**Files:**
- Create: `r-mos-backend/.env`
- Modify: `r-mos-backend/.env`

**Step 1: Create backend env**

Run:
```bash
cd ../r-mos-backend
cp .env.example .env
```
Then edit `r-mos-backend/.env` with correct DB connection values.

**Step 2: Create database (if not present)**

Run:
```bash
createdb rmos_dev
```
Expected: Database created or “already exists”.

**Step 3: Migrate + seed**

Run:
```bash
alembic upgrade head
python -m scripts.seed_data
```
Expected: Migrations and seed run successfully.

**Step 4: Start backend**

Run:
```bash
python main.py
```
Expected: Server starts at http://localhost:8000.

### Task 3: Configure and run frontend

**Files:**
- Create: `r-mos-frontend/.env`
- Modify: `r-mos-frontend/.env`

**Step 1: Create frontend env**

Run:
```bash
cd ../r-mos-frontend
cp .env.example .env
```
Then edit `r-mos-frontend/.env` to point API base URL to backend if needed.

**Step 2: Start frontend**

Run:
```bash
npm run dev
```
Expected: Vite dev server starts at http://localhost:3000.

### Task 4: Verify app health

**Files:**
- None (verification only)

**Step 1: Backend health check**

Run:
```bash
curl -s http://localhost:8000/api/v1/health
```
Expected: HTTP 200 with health payload.

**Step 2: Frontend loads**

Open: http://localhost:3000 and confirm UI renders.

### Task 5: Inventory cleanup candidates (exclude `robot/`)

**Files:**
- Create: `docs/cleanup-candidates.md`
- Modify: `docs/cleanup-candidates.md`

**Step 1: Collect candidate list**

Run:
```bash
cd ..
rg --files -g '!*robot/**' > /tmp/all-files-no-robot.txt
```
Then manually review and classify items into keep/remove in `docs/cleanup-candidates.md`.

**Step 2: Validate candidates**

Run:
```bash
rg -n "<candidate-name>" -g '!*robot/**'
```
Expected: No references in active code/docs before deletion.

**Step 3: Confirm with user**

Share `docs/cleanup-candidates.md` summary and ask for explicit approval to delete.

### Task 6: Delete approved files and commit

**Files:**
- Delete: (only approved paths from `docs/cleanup-candidates.md`)

**Step 1: Delete approved items**

Run:
```bash
rm -rf <approved-path-1> <approved-path-2> ...
```
Expected: Files removed.

**Step 2: Commit cleanup**

Run:
```bash
git add -A
git commit -m "chore: remove unused files"
```
Expected: One cleanup commit with only approved deletions.

### Notes / Safeguards
- Never touch `robot/` (explicit user instruction).
- If any command fails or behavior is unexpected, stop and use @superpowers:systematic-debugging before attempting fixes.

