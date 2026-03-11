# Repository Prune Unused Artifacts Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove low-risk unused and outdated repository artifacts while preserving files required by the current runtime, test, and evidence baseline.

**Architecture:** Execute cleanup in evidence-backed batches. Delete only files that are either generated from other tracked sources, ignored local artifacts, or tracked duplicates with no remaining repo references. Re-run the smallest relevant verification commands after each batch and record the outcome in project tracking docs.

**Tech Stack:** Git, FastAPI, pytest, Vite, Vitest, shell tooling (`rg`, `find`)

### Task 1: Inventory Low-Risk Cleanup Targets

**Files:**
- Modify: `docs/plans/2026-03-11-repo-prune-unused-artifacts.md`
- Review: `AGENTS.md`
- Review: `docs/plans/2026-03-05-review-test-cleanup-execution.md`
- Review: `docs/review/review-checklist.md`
- Review: `docs/testing/ACCEPTANCE_CHARTER.md`

**Step 1: Confirm keep/delete rules**

Run: `rg -n "docs-archive|开源机器人|review-checklist|backend-test-report" README.md AGENTS.md docs/plans/2026-03-05-review-test-cleanup-execution.md docs/testing/ACCEPTANCE_CHARTER.md`
Expected: Keep rules for current evidence/docs are explicit.

**Step 2: Identify generated or duplicate artifacts**

Run: `git ls-files 'r-mos-frontend/vite.config.*' 'r-mos-frontend/postcss.config.js' 'r-mos-frontend/tailwind.config.js'`
Expected: Only `vite.config.js` and `vite.config.d.ts` appear as duplicate artifacts; `tailwind.config.js` and `postcss.config.js` stay because they are referenced.

**Step 3: Identify local-only artifacts**

Run: `find . -maxdepth 2 \( -name '__pycache__' -o -name '.pytest_cache' -o -name 'dist' -o -path './logs' -o -path './r-mos-backend/logs' -o -path './r-mos-backend/venv' \) | LC_ALL=C sort`
Expected: Only cache/build/log directories outside `.venv` and `node_modules` are targeted.

### Task 2: Delete Tracked Duplicate Config Files

**Files:**
- Delete: `r-mos-frontend/vite.config.js`
- Delete: `r-mos-frontend/vite.config.d.ts`

**Step 1: Verify no references remain**

Run: `rg -n "vite\\.config\\.js|vite\\.config\\.d\\.ts" . -g '!**/node_modules/**' -g '!**/.git/**'`
Expected: No matches.

**Step 2: Delete the files**

Run: `git rm r-mos-frontend/vite.config.js r-mos-frontend/vite.config.d.ts`
Expected: Files staged as deletions.

**Step 3: Verify frontend still builds and tests**

Run: `cd r-mos-frontend && npm test`
Expected: PASS

Run: `cd r-mos-frontend && npm run build`
Expected: PASS

### Task 3: Delete Ignored Local Artifacts

**Files:**
- Delete local-only: `.DS_Store`
- Delete local-only: `PROJECT_DIRECTORY_FULL.txt`
- Delete local-only: `gate3_delivery_docs_and_evidence.zip`
- Delete local-only: `gate3_delivery_repo_HEAD.tar.gz`
- Delete local-only: `上传.zip`
- Delete local-only directories: `logs/`, `r-mos-backend/logs/`, `r-mos-backend/.pytest_cache/`, `r-mos-backend/venv/`, `r-mos-frontend/dist/`, `scripts/__pycache__/`, `r-mos-backend/app/**/__pycache__/`

**Step 1: Delete only ignored or generated artifacts**

Run: `find r-mos-backend/app -type d -name '__pycache__' -prune -exec rm -rf {} +`
Expected: Python cache directories removed outside `.venv`.

Run: `rm -rf logs r-mos-backend/logs r-mos-backend/.pytest_cache r-mos-backend/venv r-mos-frontend/dist scripts/__pycache__`
Expected: Local generated directories removed.

Run: `rm -f .DS_Store PROJECT_DIRECTORY_FULL.txt gate3_delivery_docs_and_evidence.zip gate3_delivery_repo_HEAD.tar.gz 上传.zip`
Expected: Local generated files removed.

**Step 2: Verify no tracked files were affected by local cleanup**

Run: `git diff --name-only`
Expected: Only tracked deletions from Task 2 appear.

### Task 4: Update Cleanup Tracking Docs

**Files:**
- Modify: `docs/plans/2026-03-05-review-test-cleanup-execution.md`
- Modify: `docs/review/review-checklist.md`
- Modify: `DEVELOPMENT_LOG.md`

**Step 1: Record the cleanup batch**

Update:
- execution plan batch summary
- review checklist evidence
- development log entry with commands and results

**Step 2: Capture final verification**

Run: `git diff --name-only`
Expected: Updated docs plus tracked config deletions.

Run: `cd r-mos-frontend && npm test && npm run build`
Expected: PASS

**Step 3: Prepare commit**

Run: `git add docs/plans/2026-03-11-repo-prune-unused-artifacts.md docs/plans/2026-03-05-review-test-cleanup-execution.md docs/review/review-checklist.md DEVELOPMENT_LOG.md`
Expected: Cleanup documentation staged with code deletions.
