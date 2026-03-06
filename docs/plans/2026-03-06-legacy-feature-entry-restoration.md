# Legacy Feature Entry Restoration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restore visible navigation entry points for existing SOP maintenance, 3D model, monitor, report, and replay pages so users can discover features that still exist in the codebase.

**Architecture:** Keep the current role-based layout shell and only widen discoverability for already-mounted routes. Do not restore deleted 3D helper components in this task; first expose surviving pages through `AppLayout` and protect the behavior with focused layout tests.

**Tech Stack:** React 18, React Router 6, Zustand, Vitest, Testing Library, TypeScript

### Task 1: Lock expected navigation behavior with tests

**Files:**
- Create: `r-mos-frontend/src/components/Layout/__tests__/AppLayout.test.tsx`
- Modify: `r-mos-frontend/src/components/Layout/AppLayout.tsx`

**Step 1: Write the failing test**

Create role-based navigation tests that assert:
- student can see `SOP 工作台` / `3D 展示` / `执行回放`
- teacher keeps `班级监控台` and gains `SOP 工作台`
- admin keeps `系统概览` and gains `执行回放`

**Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npm test -- src/components/Layout/__tests__/AppLayout.test.tsx
```

Expected: FAIL because current `AppLayout` does not expose those links.

**Step 3: Write minimal implementation**

Add a shared navigation block for authenticated roles that links to existing routes:
- `/maintenance`
- `/atom01`
- `/monitor`
- `/reports`
- `/agent/replay`

Keep existing role-specific workbench/admin items intact.

**Step 4: Run test to verify it passes**

Run:

```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npm test -- src/components/Layout/__tests__/AppLayout.test.tsx
```

Expected: PASS

**Step 5: Commit**

```bash
git add docs/plans/2026-03-06-legacy-feature-entry-restoration.md r-mos-frontend/src/components/Layout/AppLayout.tsx r-mos-frontend/src/components/Layout/__tests__/AppLayout.test.tsx
git commit -m "feat: restore legacy feature navigation entries"
```

### Task 2: Verify no regression in auth/layout gate

**Files:**
- Test: `r-mos-frontend/src/components/auth/__tests__/ProtectedRoute.test.tsx`

**Step 1: Run related tests**

Run:

```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npm test -- src/components/Layout/__tests__/AppLayout.test.tsx src/components/auth/__tests__/ProtectedRoute.test.tsx
```

Expected: PASS

**Step 2: Run type/build verification**

Run:

```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npx tsc --noEmit
cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npm run build
```

Expected: PASS

### Task 3: Record evidence

**Files:**
- Modify: `DEVELOPMENT_LOG.md`

**Step 1: Append reproducible commands and results**

Record:
- exact test commands
- pass/fail summary
- remaining risk: deleted `DisassemblyDemoAdjudicated.tsx` / `PartInspector.tsx` still not restored

**Step 2: Commit**

```bash
git add DEVELOPMENT_LOG.md
git commit -m "docs: record legacy feature entry restoration verification"
```
