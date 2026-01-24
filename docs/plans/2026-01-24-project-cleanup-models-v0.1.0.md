# Project Cleanup + Model Isolation v0.1.0 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Clean up the repo, fold worktree changes back into main, restructure GLB models for per-robot loading (ATOM01 only), and ship a v0.1.0 commit with next-steps plan.

**Architecture:** Keep GLB assets in frontend `public/` but segregate by `robotId` under `/models/robots/<robotId>`, while keeping shared parts under `/models/parts`. Introduce a configurable model base URL (`VITE_MODEL_BASE_URL`) so assets can later be served from an external DB/CDN without frontend code changes. Keep `robot/` as source files (no conversion).

**Tech Stack:** React + Vite, TypeScript, FastAPI, PostgreSQL.

---

### Task 1: Inventory and merge worktree changes back to main

**Files:**
- Modify: `docs/cleanup-candidates.md` (create or update)
- Modify: files identified from `.worktrees/run-and-clean` diff

**Step 1: Write the failing test**

Run:
```bash
git worktree list
```
Expected: shows `.worktrees/run-and-clean` (precondition = exists).

**Step 2: Run test to verify it fails**

Run:
```bash
git -C .worktrees/run-and-clean status --porcelain
```
Expected: any tracked changes that must be reviewed (if empty, nothing to merge).

**Step 3: Write minimal implementation**

Apply only required changes from worktree to main (exclude `.env` files). If needed, copy file-by-file or use `git diff` patches.

**Step 4: Run test to verify it passes**

Run:
```bash
git -C .worktrees/run-and-clean status --porcelain
```
Expected: empty after changes are safely merged or intentionally discarded.

**Step 5: Commit**

_No commit yet (batch with other cleanup changes)._ 

---

### Task 2: Clean up top-level docs (keep 3 specified)

**Files:**
- Delete: `mvp骨架文档-v2.3.md`
- Delete: `rmos拆包A_v2.3.md`
- Delete: `rmos拆包B_v2.3md.md`
- Delete: `rmos拆包C-v2.2.md`
- Delete: `rmos拆包D_v1.2.md`
- Delete: `开发计划.md`
- Delete: `交接文档.md`
- Keep: `裁决级系统重构开发计划.md`
- Keep: `开发记录.md`
- Keep: `Codex交接提示词.md`

**Step 1: Write the failing test**

Run:
```bash
ls mvp骨架文档-v2.3.md rmos拆包A_v2.3.md rmos拆包B_v2.3md.md rmos拆包C-v2.2.md rmos拆包D_v1.2.md 开发计划.md 交接文档.md
```
Expected: files exist before deletion.

**Step 2: Run test to verify it fails**

Run:
```bash
ls 裁决级系统重构开发计划.md 开发记录.md Codex交接提示词.md
```
Expected: these 3 files exist (must remain).

**Step 3: Write minimal implementation**

Delete the listed files only.

**Step 4: Run test to verify it passes**

Run:
```bash
ls 裁决级系统重构开发计划.md 开发记录.md Codex交接提示词.md
```
Expected: the 3 files remain, and deleted files are gone.

**Step 5: Commit**

_No commit yet (batch with other cleanup changes)._ 

---

### Task 3: Remove worktree and return to main-only workflow

**Files:**
- Delete: `.worktrees/run-and-clean` (worktree)
- Delete: `.worktrees/` (if empty)

**Step 1: Write the failing test**

Run:
```bash
git worktree list
```
Expected: shows `.worktrees/run-and-clean` before removal.

**Step 2: Run test to verify it fails**

Run:
```bash
test -d .worktrees/run-and-clean && echo "exists"
```
Expected: prints `exists`.

**Step 3: Write minimal implementation**

Remove the worktree via git, then delete the directory if empty.

**Step 4: Run test to verify it passes**

Run:
```bash
git worktree list
```
Expected: only main worktree remains.

**Step 5: Commit**

_No commit yet (batch with other cleanup changes)._ 

---

### Task 4: Restructure GLB assets for per-robot loading (ATOM01)

**Files:**
- Move: `r-mos-frontend/public/models/atom01/` → `r-mos-frontend/public/models/robots/atom01/`
- Create: `r-mos-frontend/public/models/robots/atom01/manifest.json`
- Modify: `r-mos-frontend/src/components/Viewer3D/constants.ts`
- Modify: `r-mos-frontend/src/components/Viewer3D/Atom01Model.tsx`
- Modify: `r-mos-frontend/src/components/Viewer3D/Atom01Interactive.tsx`
- Modify: `r-mos-frontend/src/adjudication/data/partRegistry.ts`
- Create: `r-mos-frontend/src/config/robots.ts` (or `src/config/models.ts`)
- Modify: `r-mos-frontend/.env.example`

**Step 1: Write the failing test**

Run:
```bash
rg -n "/models/atom01" r-mos-frontend/src
```
Expected: matches existing hardcoded paths (will need to change).

**Step 2: Run test to verify it fails**

Run:
```bash
ls r-mos-frontend/public/models/atom01
```
Expected: directory exists before move.

**Step 3: Write minimal implementation**

- Move `public/models/atom01` into `public/models/robots/atom01`.
- Add `manifest.json` describing the robot’s GLB list.
- Add `VITE_MODEL_BASE_URL` to `.env.example` (default `/models`).
- Introduce `getRobotModelBase(robotId)` that resolves to `${VITE_MODEL_BASE_URL}/robots/${robotId}`.
- Update code references from `/models/atom01/...` to `${getRobotModelBase('atom01')}/...`.
- Keep shared parts in `/models/parts` for now (no conversion, no relocation).

**Step 4: Run test to verify it passes**

Run:
```bash
rg -n "/models/atom01" r-mos-frontend/src
```
Expected: no matches (all paths updated).

**Step 5: Commit**

_No commit yet (batch with other cleanup changes)._ 

---

### Task 5: Add next-steps plan and progress note

**Files:**
- Create: `docs/plans/2026-01-24-next-steps.md`

**Step 1: Write the failing test**

Run:
```bash
test ! -f docs/plans/2026-01-24-next-steps.md && echo "missing"
```
Expected: prints `missing` before creation.

**Step 2: Run test to verify it fails**

Run:
```bash
ls docs/plans/2026-01-24-next-steps.md
```
Expected: file does not exist yet (ls fails).

**Step 3: Write minimal implementation**

Create the plan with:
- Current cleanup summary
- Current model isolation state
- Next steps (DB model storage service + user/robot assignment + asset pipeline)

**Step 4: Run test to verify it passes**

Run:
```bash
ls docs/plans/2026-01-24-next-steps.md
```
Expected: file exists.

**Step 5: Commit**

_No commit yet (batch with other cleanup changes)._ 

---

### Task 6: Version bump and release commit (v0.1.0)

**Files:**
- Modify: `r-mos-frontend/package.json` (version → 0.1.0)
- Modify: `r-mos-backend/main.py` (version string → 0.1.0) **(confirm if desired)**
- Modify: `README.md` (optional version mention)

**Step 1: Write the failing test**

Run:
```bash
rg -n "version" r-mos-frontend/package.json r-mos-backend/main.py
```
Expected: current versions are not 0.1.0.

**Step 2: Run test to verify it fails**

Run:
```bash
rg -n "0.1.0" r-mos-frontend/package.json r-mos-backend/main.py
```
Expected: no matches before update.

**Step 3: Write minimal implementation**

Update versions to `0.1.0` (frontend always; backend optional based on approval).

**Step 4: Run test to verify it passes**

Run:
```bash
rg -n "0.1.0" r-mos-frontend/package.json r-mos-backend/main.py
```
Expected: matches updated version string(s).

**Step 5: Commit**

Run:
```bash
git add -A
git commit -m "chore: v0.1.0 cleanup and model isolation"
git tag v0.1.0
```

---

### Notes / Safeguards
- Do **not** delete or modify `robot/` source files.
- Do **not** commit `.env` files.
- Keep `裁决级系统重构开发计划.md`、`开发记录.md`、`Codex交接提示词.md`.
- Prepare for future DB storage by using `VITE_MODEL_BASE_URL` (later can point to API/CDN/DB service).

