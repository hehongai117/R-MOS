# SOP Depth Recovery Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restore the missing second-layer SOP experience by bringing back the deleted part inspector and adjudicated disassembly demo, then wiring both into the existing SOP maintenance page.

**Architecture:** Keep `SOPMaintenancePage` as the canonical workspace and recover the missing capability by restoring two narrowly scoped helper components. `PartInspector` provides a dedicated sub-part 3D preview, while `DisassemblyDemoAdjudicated` restores the visible “animation -> adjudication -> block/rollback” interaction path that the plain `DisassemblyAnimation` no longer exposes.

**Tech Stack:** React 18, TypeScript, Ant Design, @react-three/fiber, @react-three/drei, Vitest, Testing Library

### Task 1: Lock the deleted component regressions with tests

**Files:**
- Create: `r-mos-frontend/src/components/Viewer3D/__tests__/PartInspector.test.tsx`
- Create: `r-mos-frontend/src/components/Viewer3D/__tests__/DisassemblyDemoAdjudicated.test.tsx`

**Step 1: Write the failing tests**

Add tests that assert:
- `PartInspector` renders empty-state copy when no link is selected
- `PartInspector` lists real torso sub-parts when `selectedLink="torso_link"`
- `DisassemblyDemoAdjudicated` can be imported and rendered with a screw target

**Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npm test -- src/components/Viewer3D/__tests__/PartInspector.test.tsx src/components/Viewer3D/__tests__/DisassemblyDemoAdjudicated.test.tsx
```

Expected: FAIL because both deleted component files are missing.

**Step 3: Restore minimal implementation**

Restore:
- `r-mos-frontend/src/components/Viewer3D/PartInspector.tsx`
- `r-mos-frontend/src/components/Viewer3D/DisassemblyDemoAdjudicated.tsx`

**Step 4: Run test to verify it passes**

Run the same test command and expect PASS.

### Task 2: Reconnect the recovered capabilities to the SOP page

**Files:**
- Modify: `r-mos-frontend/src/pages/SOPMaintenancePage.tsx`

**Step 1: Add the dedicated part-inspector panel**

Render `PartInspector` from the existing right-side detail area so selected links and sub-parts regain an independent 3D preview panel.

**Step 2: Add the adjudicated disassembly panel**

Use `DisassemblyDemoAdjudicated` in the 3D area when a screw and tool are selected. Keep the existing `DisassemblyAnimation` as the generic sequence view, but expose the adjudicated path as the default for screw-level maintenance actions.

**Step 3: Run focused verification**

Run:

```bash
cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npm test -- src/components/Viewer3D/__tests__/PartInspector.test.tsx src/components/Viewer3D/__tests__/DisassemblyDemoAdjudicated.test.tsx src/components/Layout/__tests__/AppLayout.test.tsx
cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npx tsc --noEmit
cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npm run build
```

Expected: PASS

### Task 3: Record evidence

**Files:**
- Modify: `DEVELOPMENT_LOG.md`

**Step 1: Append commands and results**

Record the failing-test evidence, the restoration commands, and the final pass results.

**Step 2: Commit**

```bash
git add docs/plans/2026-03-06-sop-depth-recovery.md r-mos-frontend/src/components/Viewer3D/PartInspector.tsx r-mos-frontend/src/components/Viewer3D/DisassemblyDemoAdjudicated.tsx r-mos-frontend/src/pages/SOPMaintenancePage.tsx r-mos-frontend/src/components/Viewer3D/__tests__/PartInspector.test.tsx r-mos-frontend/src/components/Viewer3D/__tests__/DisassemblyDemoAdjudicated.test.tsx DEVELOPMENT_LOG.md
git commit -m "feat: restore sop depth interactions"
```
