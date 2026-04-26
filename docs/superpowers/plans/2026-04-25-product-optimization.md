# R-MOS 产品化优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strip demo scaffolding and unused pages from R-MOS, restructure navigation for student/teacher/admin roles, and create skeleton pages for the new task-driven practice flow.

**Architecture:** Phase 1 removes DEMO_MODE and 17 unused pages. Phase 2 restructures navigation. Phase 3 adds two new skeleton pages (MyTasksPage, ScenarioPickerPage). Phase 4 cleans up backend Phase 2 dead code. Each phase produces a working, testable app.

**Tech Stack:** React 18, TypeScript, Vite, Zustand, React Router, Ant Design, Lucide icons, FastAPI, SQLAlchemy, Pydantic

---

## File Structure

### Files to Delete (Frontend)

```
src/config/demoMode.ts
src/api/demo.ts
src/pages/AIChatPage.tsx
src/pages/BeliefTrackerPage.tsx
src/pages/DiagnosisPage.tsx
src/pages/EvidencePage.tsx
src/pages/IncidentListPage.tsx
src/pages/AssessmentStatusPage.tsx
src/pages/TaskExecutionPage.tsx
src/pages/ReplayPage.tsx
src/pages/MaintenanceProjectDraftPage.tsx
src/pages/SOPMaintenanceInspectorPage.tsx
src/pages/TrainingWorkbenchPage.tsx
src/pages/admin/AcceptanceDashboardPage.tsx
src/pages/admin/CompensationPage.tsx
src/pages/admin/FeatureFlagPage.tsx
src/pages/admin/LLMMetricsPage.tsx
src/pages/admin/FaultManagePage.tsx
src/pages/admin/SeedDataPage.tsx
```

### Files to Delete (Frontend Tests)

```
src/pages/__tests__/TrainingWorkbenchPage.test.tsx
src/pages/__tests__/MaintenanceProjectDraftPage.test.tsx
src/pages/__tests__/SOPMaintenanceInspectorPage.test.tsx
```

### Files to Delete (Backend)

```
app/api/v1/endpoints/demo.py
app/services/belief_state.py
app/services/compensation_planner.py
app/services/decision_recalculator.py
app/services/acceptance_metrics.py
app/services/feature_flag.py
app/services/system_monitor.py
tests/unit/test_phase2_contract.py
tests/unit/test_phase3_contract.py
tests/unit/test_phase4_contract.py
```

### Files to Create (Frontend)

```
src/pages/MyTasksPage.tsx           — student task list (assigned + self-practice)
src/pages/ScenarioPickerPage.tsx    — fault scenario browser with AI recommendation
```

### Files to Modify

```
src/App.tsx                                          — remove deleted routes, add new routes
src/components/Layout/AppLayout.tsx                  — new nav structure per role
src/pages/MonitorPage.tsx                            — remove DEMO_MODE branches
src/pages/agent/AgentWorkbenchPage.tsx               — remove DEMO_MODE branches
src/pages/ReportPage.tsx                             — remove DEMO_MODE branches
src/pages/SOPMaintenancePage.tsx                     — remove DEMO_MODE branches
src/components/Maintenance/SOPPlayerAdjudicated.tsx  — remove DEMO_MODE branches
r-mos-backend/app/api/v1/__init__.py                 — remove demo router
r-mos-backend/app/api/v1/endpoints/agent.py          — remove Phase 2 imports and route blocks
```

---

### Task 1: Remove DEMO_MODE config and demo API client

**Files:**
- Delete: `src/config/demoMode.ts`
- Delete: `src/api/demo.ts`

- [x] **Step 1: Delete the demo mode config file**

```bash
rm r-mos-frontend/src/config/demoMode.ts
```

- [x] **Step 2: Delete the demo API client**

```bash
rm r-mos-frontend/src/api/demo.ts
```

- [x] **Step 3: Verify no other files in config/ depend on demoMode**

```bash
cd r-mos-frontend && grep -r "demoMode" src/config/ || echo "CLEAN"
```

Expected: `CLEAN` (both files deleted)

- [x] **Step 4: Commit**

```bash
git add -A r-mos-frontend/src/config/demoMode.ts r-mos-frontend/src/api/demo.ts
git commit -m "chore: remove DEMO_MODE config and demo API client"
```

---

### Task 2: Clean MonitorPage of demo code

**Files:**
- Modify: `src/pages/MonitorPage.tsx`

- [x] **Step 1: Remove demo imports**

Remove these lines from the top of MonitorPage.tsx:
```typescript
// REMOVE:
import { DEMO_FAULT_TYPE, DEMO_MODE } from '@/config/demoMode'
import { resetDemoFault, startDemoFault } from '@/api/demo'
```

- [x] **Step 2: Remove demo state and handler**

Remove the `demoFaultActive` state declaration:
```typescript
// REMOVE:
const [demoFaultActive, setDemoFaultActive] = useState(false)
```

Remove the `handleDemoTrigger` callback (the function that calls `startDemoFault` / `resetDemoFault`). Remove the `useEffect` that calls `resetDemoFault` on unmount when `DEMO_MODE && demoFaultActive`.

- [x] **Step 3: Remove demo UI elements from JSX**

Remove the `title` prop with DEMO_MODE ternary on the page header (around line 343).

Remove the "触发故障演示" button block (`{DEMO_MODE && (` ... `)}`) around line 353.

Remove the demo status alert block (`{DEMO_MODE && demoFaultActive && (` ... `)}`) around line 399.

- [x] **Step 4: Clean up joint click navigation**

In the joint card click handler (around line 570), there is:
```typescript
if (DEMO_MODE) {
  navigate(`/agent/workbench?fault=${DEMO_FAULT_TYPE}&joint=${joint.joint_id}`)
}
```

Replace with an unconditional navigation that passes the actual fault type from the joint data:
```typescript
navigate(`/agent/workbench?fault=${joint.fault_code ?? 'unknown'}&joint=${joint.joint_id}`)
```

If the joint does not have a `fault_code` field, use the joint's error state or status to determine the fault type. The key is: clicking an alerting joint always navigates to the diagnosis workbench with fault context.

- [x] **Step 5: Remove unused imports**

Clean up any now-unused imports (`useState` if no longer needed for demo state, etc.).

- [x] **Step 6: Verify the file compiles**

```bash
cd r-mos-frontend && npx tsc --noEmit src/pages/MonitorPage.tsx 2>&1 | head -20
```

- [x] **Step 7: Commit**

```bash
git add r-mos-frontend/src/pages/MonitorPage.tsx
git commit -m "refactor: remove DEMO_MODE from MonitorPage"
```

---

### Task 3: Clean AgentWorkbenchPage of demo code

**Files:**
- Modify: `src/pages/agent/AgentWorkbenchPage.tsx`

- [x] **Step 1: Remove demo imports**

Remove:
```typescript
import { DEMO_MODE } from '@/config/demoMode'
import { streamDemoChat, type DemoChatMeta } from '@/api/demo'
```

- [x] **Step 2: Remove demo-specific state and logic**

Remove or refactor the `demoMeta` state and `demoSubmit` function that calls `streamDemoChat`.

Remove the `useEffect` that auto-populates fault context only when DEMO_MODE (around line 263). Replace with a version that always runs when fault/joint URL params are present:
```typescript
useEffect(() => {
  if (!faultParam || messages.length > 0) return
  // Auto-populate fault context message
  const alertMsg = `检测到设备告警：${jointParam} 温度异常升高，已超过安全阈值。\n请输入"诊断"开始故障分析，或直接描述您的需求。`
  setMessages([{ role: 'assistant', content: alertMsg }])
}, [faultParam, jointParam])
```

- [x] **Step 3: Unify submit handlers**

Replace all `DEMO_MODE ? void demoSubmit(...) : void submit(...)` ternaries with just the real `submit()` call. This affects:
- Enter key handler (around line 624)
- Quick action button onClick (around line 636)
- Submit button disabled state (around line 642)

- [x] **Step 4: Clean DiagnosisPanel props**

Replace the large DEMO_MODE ternary block (lines 690-721) that conditionally maps `demoMeta` vs real data to DiagnosisPanel props. Use only the real data path.

- [x] **Step 5: Remove SOP recommendation button guard**

The "开始维保" button (around line 584) is currently wrapped in `{DEMO_MODE && demoMeta?.sop_recommendation && ...}`. Change it to show whenever there is a valid SOP recommendation from the real diagnosis result, not only in demo mode:
```typescript
{diagnosisResult?.sop_recommendation && !isStreaming && (
  <Button onClick={() => navigate(`/maintenance?sop=${diagnosisResult.sop_recommendation.sop_id}`)}>
    开始维保 → {diagnosisResult.sop_recommendation.sop_name}
  </Button>
)}
```

- [x] **Step 6: Remove unused imports and types**

Remove `DemoChatMeta` type, `demoMeta` state, `demoSubmit` function, and any other now-unused references.

- [x] **Step 7: Verify compilation**

```bash
cd r-mos-frontend && npx tsc --noEmit src/pages/agent/AgentWorkbenchPage.tsx 2>&1 | head -20
```

- [x] **Step 8: Commit**

```bash
git add r-mos-frontend/src/pages/agent/AgentWorkbenchPage.tsx
git commit -m "refactor: remove DEMO_MODE from AgentWorkbenchPage"
```

---

### Task 4: Clean SOPPlayerAdjudicated and SOPMaintenancePage of demo code

**Files:**
- Modify: `src/components/Maintenance/SOPPlayerAdjudicated.tsx`
- Modify: `src/pages/SOPMaintenancePage.tsx`

- [x] **Step 1: Clean SOPPlayerAdjudicated**

Remove the import:
```typescript
import { DEMO_MODE } from '@/config/demoMode'
```

Remove the `useEffect` that tracks demo step timestamps in sessionStorage (around lines 302-308).

Remove the `useEffect` that navigates to `/reports/demo` on completion (around lines 310-323). Replace with navigation to the real report route using the session ID:
```typescript
// When SOP execution completes, navigate to report
useEffect(() => {
  if (executionComplete && sessionId) {
    const timer = setTimeout(() => navigate(`/reports/${sessionId}`), 2000)
    return () => clearTimeout(timer)
  }
}, [executionComplete, sessionId, navigate])
```

The `sessionId` should be passed as a prop or obtained from the practice session context. If it's not available yet, use a placeholder prop `sessionId?: string` and navigate only when it exists.

- [x] **Step 2: Clean SOPMaintenancePage**

Remove the import:
```typescript
import { DEMO_MODE } from '@/config/demoMode'
```

Change line 1231 from:
```typescript
initialSopId={DEMO_MODE ? (sopParam ?? undefined) : undefined}
```
to:
```typescript
initialSopId={sopParam ?? undefined}
```

The `sop` query parameter should always work, not only in demo mode.

- [x] **Step 3: Verify compilation**

```bash
cd r-mos-frontend && npx tsc --noEmit src/components/Maintenance/SOPPlayerAdjudicated.tsx src/pages/SOPMaintenancePage.tsx 2>&1 | head -20
```

- [x] **Step 4: Commit**

```bash
git add r-mos-frontend/src/components/Maintenance/SOPPlayerAdjudicated.tsx r-mos-frontend/src/pages/SOPMaintenancePage.tsx
git commit -m "refactor: remove DEMO_MODE from SOPPlayer and SOPMaintenancePage"
```

---

### Task 5: Clean ReportPage of demo code

**Files:**
- Modify: `src/pages/ReportPage.tsx`

- [x] **Step 1: Remove demo imports and buildDemoReport**

Remove:
```typescript
import { DEMO_MODE } from '@/config/demoMode'
```

Remove the entire `buildDemoReport()` function (lines 12-59).

- [x] **Step 2: Remove demo conditional logic**

Remove the `isDemoReport` variable and all conditionals that use it:
```typescript
// REMOVE:
const isDemoReport = DEMO_MODE && taskId === 'demo'
const [loading, setLoading] = useState(!isDemoReport)
const [report, setReport] = useState<TaskReport | null>(isDemoReport ? buildDemoReport() : null)
// ...
if (isDemoReport) return
```

Replace with standard loading state:
```typescript
const [loading, setLoading] = useState(true)
const [report, setReport] = useState<TaskReport | null>(null)
```

The page should always fetch from the backend API.

- [x] **Step 3: Verify compilation**

```bash
cd r-mos-frontend && npx tsc --noEmit src/pages/ReportPage.tsx 2>&1 | head -20
```

- [x] **Step 4: Commit**

```bash
git add r-mos-frontend/src/pages/ReportPage.tsx
git commit -m "refactor: remove DEMO_MODE from ReportPage"
```

---

### Task 6: Delete unused frontend pages

**Files:**
- Delete: 17 page files + 3 test files (see File Structure above)

- [x] **Step 1: Delete all unused page files**

```bash
cd r-mos-frontend
rm src/pages/AIChatPage.tsx
rm src/pages/BeliefTrackerPage.tsx
rm src/pages/DiagnosisPage.tsx
rm src/pages/EvidencePage.tsx
rm src/pages/IncidentListPage.tsx
rm src/pages/AssessmentStatusPage.tsx
rm src/pages/TaskExecutionPage.tsx
rm src/pages/ReplayPage.tsx
rm src/pages/MaintenanceProjectDraftPage.tsx
rm src/pages/SOPMaintenanceInspectorPage.tsx
rm src/pages/TrainingWorkbenchPage.tsx
rm src/pages/admin/AcceptanceDashboardPage.tsx
rm src/pages/admin/CompensationPage.tsx
rm src/pages/admin/FeatureFlagPage.tsx
rm src/pages/admin/LLMMetricsPage.tsx
rm src/pages/admin/FaultManagePage.tsx
rm src/pages/admin/SeedDataPage.tsx
```

- [x] **Step 2: Delete associated test files**

```bash
cd r-mos-frontend
rm -f src/pages/__tests__/TrainingWorkbenchPage.test.tsx
rm -f src/pages/__tests__/MaintenanceProjectDraftPage.test.tsx
rm -f src/pages/__tests__/SOPMaintenanceInspectorPage.test.tsx
```

- [x] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: delete 17 unused pages and their tests"
```

---

### Task 7: Update App.tsx routes

**Files:**
- Modify: `src/App.tsx`

- [x] **Step 1: Remove lazy imports for deleted pages**

Remove these lines from App.tsx (lines 15-24, 27-29, 31, 33, 36, 39):
```typescript
// REMOVE all of these:
const AcceptanceDashboardPage = lazy(() => import('@/pages/admin/AcceptanceDashboardPage'))
const ApprovalQueuePage = lazy(() => import('@/pages/admin/ApprovalQueuePage'))
const FaultManagePage = lazy(() => import('@/pages/admin/FaultManagePage'))
const LLMMetricsPage = lazy(() => import('@/pages/admin/LLMMetricsPage'))
const SeedDataPage = lazy(() => import('@/pages/admin/SeedDataPage'))
const FeatureFlagPage = lazy(() => import('@/pages/admin/FeatureFlagPage'))
const CompensationPage = lazy(() => import('@/pages/admin/CompensationPage'))
const BeliefTrackerPage = lazy(() => import('@/pages/BeliefTrackerPage'))
const AIChatPage = lazy(() => import('@/pages/AIChatPage'))
const AssessmentStatusPage = lazy(() => import('@/pages/AssessmentStatusPage'))
const DiagnosisPage = lazy(() => import('@/pages/DiagnosisPage'))
const EvidencePage = lazy(() => import('@/pages/EvidencePage'))
const IncidentListPage = lazy(() => import('@/pages/IncidentListPage'))
const MaintenanceProjectDraftPage = lazy(() => import('@/pages/MaintenanceProjectDraftPage'))
const ReplayPage = lazy(() => import('@/pages/ReplayPage'))
const SOPMaintenanceInspectorPage = lazy(() => import('@/pages/SOPMaintenanceInspectorPage'))
const TaskExecutionPage = lazy(() => import('@/pages/TaskExecutionPage'))
const TrainingWorkbenchPage = lazy(() => import('@/pages/TrainingWorkbenchPage'))
```

- [x] **Step 2: Add lazy imports for new pages**

```typescript
const MyTasksPage = lazy(() => import('@/pages/MyTasksPage'))
const ScenarioPickerPage = lazy(() => import('@/pages/ScenarioPickerPage'))
```

- [x] **Step 3: Remove deleted routes from the Route tree**

Remove these `<Route>` elements:
```tsx
// REMOVE:
<Route path="workbench/training" ... />           {/* line 92-95 */}
<Route path="ai-chat" ... />                      {/* line 117 */}
<Route path="maintenance/project-draft" ... />     {/* line 120 */}
<Route path="maintenance/inspector" ... />         {/* line 121 */}
<Route path="workbench/atom01-maintenance" ... />  {/* line 119 */}
<Route path="agent/replay" ... />                  {/* line 141 */}
<Route path="admin/approvals" ... />               {/* line 142-145 */}
<Route path="admin/acceptance" ... />              {/* line 146-149 */}
<Route path="admin/llm-metrics" ... />             {/* line 150-153 */}
<Route path="admin/faults" ... />                  {/* line 154-157 */}
<Route path="admin/seed-data" ... />               {/* line 158-161 */}
<Route path="admin/features" ... />                {/* line 162-165 */}
<Route path="admin/compensation" ... />            {/* line 166-169 */}
<Route path="belief-tracker" ... />                {/* line 170-173 */}
<Route path="incidents" ... />                     {/* line 175 */}
<Route path="evidence" ... />                      {/* line 176 */}
<Route path="assessments" ... />                   {/* line 177 */}
<Route path="diagnosis/:taskId" ... />             {/* line 180 */}
<Route path="tasks/:taskId" ... />                 {/* line 181 */}
```

- [x] **Step 4: Add new routes**

Add inside the protected route block:
```tsx
<Route
  path="my-tasks"
  element={withSuspense(withRoles(<MyTasksPage />, ['student']))}
/>
<Route
  path="scenarios"
  element={withSuspense(withRoles(<ScenarioPickerPage />, ['student']))}
/>
```

- [x] **Step 5: Verify the full route set is correct**

After edits, the protected routes should be:
```
/                          → DefaultRouteRedirect
/my-tasks                  → MyTasksPage (student)
/scenarios                 → ScenarioPickerPage (student)
/student/skills            → StudentSkillsPage (student)
/workbench/teaching        → TeacherMonitorPage (teacher, admin)
/teacher/students          → TeacherStudentsPage (teacher, admin)
/admin/console             → AdminDashboardPage (admin)
/sops                      → SOPListPage (teacher, admin)
/knowledge                 → KnowledgePage (teacher, admin)  ← ADD role restriction
/monitor                   → MonitorPage
/maintenance               → SOPMaintenancePage
/atom01                    → Atom01DemoPage
/teaching/assignments      → TeachingAssignmentsPage (teacher, admin)
/teaching/attempts/:id     → TeachingAttemptPage (teacher, admin)
/teaching/attempts/:id/evidence  → TeachingEvidencePage (teacher, admin)
/teaching/attempts/:id/diagnosis → TeachingDiagnosisPage (teacher, admin)
/agent/workbench           → AgentWorkbenchPage
/settings                  → UserSettingsPage
/reports                   → ReportPage
/reports/:taskId           → ReportPage
```

- [x] **Step 6: Verify compilation**

```bash
cd r-mos-frontend && npx tsc --noEmit src/App.tsx 2>&1 | head -20
```

- [x] **Step 7: Commit**

```bash
git add r-mos-frontend/src/App.tsx
git commit -m "refactor: update routes - remove deleted pages, add MyTasks and Scenarios"
```

---

### Task 8: Restructure navigation in AppLayout

**Files:**
- Modify: `src/components/Layout/AppLayout.tsx`

- [x] **Step 1: Remove DEMO_MODE import and DEMO_NAV**

Remove:
```typescript
import { DEMO_MODE } from '@/config/demoMode'
```

Remove the entire `DEMO_NAV` array (lines 189-205) and `DEMO_LAYOUT_CONFIG` (lines 207-211).

Remove the DEMO_MODE conditional in `RoleLayoutShell`:
```typescript
// CHANGE FROM:
const config = DEMO_MODE ? DEMO_LAYOUT_CONFIG : LAYOUT_CONFIG[role]
// CHANGE TO:
const config = LAYOUT_CONFIG[role]
```

- [x] **Step 2: Replace STUDENT_NAV**

Replace the `STUDENT_NAV` array (lines 65-91) with:
```typescript
const STUDENT_NAV: NavGroup[] = [
  {
    label: '练习中心',
    items: [
      { label: '我的任务', to: '/my-tasks', icon: ClipboardList },
      { label: '自主练习', to: '/scenarios', icon: Dumbbell },
    ],
  },
  {
    label: '维保流程',
    items: [
      { label: '实时监控', to: '/monitor', icon: Activity },
      { label: 'AI 诊断工作台', to: '/agent/workbench', icon: Bot },
      { label: '维保练习工作台', to: '/maintenance', icon: Wrench },
    ],
  },
  {
    label: '学习成长',
    items: [
      { label: '维保报告', to: '/reports', icon: FileText },
      { label: '我的技能', to: '/student/skills', icon: BarChart3 },
    ],
  },
  {
    label: '工具',
    items: [
      { label: '3D 展示', to: '/atom01', icon: Boxes },
    ],
  },
]
```

- [x] **Step 3: Replace TEACHER_NAV**

Replace the `TEACHER_NAV` array (lines 93-133) with:
```typescript
const TEACHER_NAV: NavGroup[] = [
  {
    label: '教学管理',
    items: [
      { label: '班级监控台', to: '/workbench/teaching', icon: Monitor },
      { label: '作业管理', to: '/teaching/assignments', icon: ClipboardList },
      { label: '学员档案', to: '/teacher/students', icon: Users },
    ],
  },
  {
    label: 'SOP & 工具',
    items: [
      { label: 'SOP 管理', to: '/sops', icon: FileText },
      { label: '3D 展示', to: '/atom01', icon: Boxes },
      { label: '实时监控', to: '/monitor', icon: Activity },
    ],
  },
  {
    label: '记录',
    items: [
      { label: '维保报告', to: '/reports', icon: BarChart3 },
      { label: '知识库', to: '/knowledge', icon: BookOpen },
    ],
  },
]
```

- [x] **Step 4: Replace ADMIN_NAV**

Replace the `ADMIN_NAV` array (lines 135-187) with:
```typescript
const ADMIN_NAV: NavGroup[] = [
  {
    label: '概览',
    items: [
      { label: '系统概览', to: '/admin/console', icon: LayoutDashboard },
    ],
  },
  {
    label: '教学管理',
    items: [
      { label: '班级监控台', to: '/workbench/teaching', icon: Monitor },
      { label: '作业管理', to: '/teaching/assignments', icon: ClipboardList },
      { label: '学员档案', to: '/teacher/students', icon: Users },
    ],
  },
  {
    label: 'SOP & 工具',
    items: [
      { label: 'SOP 管理', to: '/sops', icon: FileText },
      { label: '3D 展示', to: '/atom01', icon: Boxes },
      { label: '实时监控', to: '/monitor', icon: Activity },
    ],
  },
  {
    label: '记录',
    items: [
      { label: '维保报告', to: '/reports', icon: BarChart3 },
      { label: '知识库', to: '/knowledge', icon: BookOpen },
    ],
  },
]
```

- [x] **Step 5: Remove unused icon imports**

From the Lucide imports at the top, remove icons no longer referenced: `AlertTriangle`, `Brain`, `CheckSquare`, `Cpu`, `Database`, `FileSearch`, `MessageSquare`, `PlayCircle`, `ShieldCheck`, `ToggleRight`. Keep: `Activity`, `BarChart3`, `BookOpen`, `Boxes`, `Bot`, `ClipboardList`, `Dumbbell`, `FileText`, `LayoutDashboard`, `LogOut`, `Monitor`, `Settings`, `Sparkles`, `Users`, `Wrench`.

Verify by searching each icon name in the file after edits.

- [x] **Step 6: Verify compilation**

```bash
cd r-mos-frontend && npx tsc --noEmit src/components/Layout/AppLayout.tsx 2>&1 | head -20
```

- [x] **Step 7: Commit**

```bash
git add r-mos-frontend/src/components/Layout/AppLayout.tsx
git commit -m "refactor: restructure navigation for student/teacher/admin roles"
```

---

### Task 9: Create MyTasksPage skeleton

**Files:**
- Create: `src/pages/MyTasksPage.tsx`
- Test: `src/pages/__tests__/MyTasksPage.test.tsx`

- [ ] **Step 1: Write the test**

Create `src/pages/__tests__/MyTasksPage.test.tsx`:
```tsx
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import MyTasksPage from '../MyTasksPage'

describe('MyTasksPage', () => {
  it('renders the page title', () => {
    render(
      <MemoryRouter>
        <MyTasksPage />
      </MemoryRouter>,
    )
    expect(screen.getByText('我的任务')).toBeInTheDocument()
  })

  it('renders tab filters for task status', () => {
    render(
      <MemoryRouter>
        <MyTasksPage />
      </MemoryRouter>,
    )
    expect(screen.getByText('待完成')).toBeInTheDocument()
    expect(screen.getByText('进行中')).toBeInTheDocument()
    expect(screen.getByText('已完成')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd r-mos-frontend && npx vitest run src/pages/__tests__/MyTasksPage.test.tsx 2>&1 | tail -10
```

Expected: FAIL — module not found

- [ ] **Step 3: Write the page**

Create `src/pages/MyTasksPage.tsx`:
```tsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ClipboardList } from 'lucide-react'

type TaskFilter = 'pending' | 'in_progress' | 'completed'

export default function MyTasksPage() {
  const [filter, setFilter] = useState<TaskFilter>('pending')
  const navigate = useNavigate()

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <ClipboardList className="h-6 w-6 text-primary" />
        <h1 className="text-2xl font-semibold text-text-primary">我的任务</h1>
      </div>

      <Tabs value={filter} onValueChange={(v) => setFilter(v as TaskFilter)}>
        <TabsList>
          <TabsTrigger value="pending">待完成</TabsTrigger>
          <TabsTrigger value="in_progress">进行中</TabsTrigger>
          <TabsTrigger value="completed">已完成</TabsTrigger>
        </TabsList>
      </Tabs>

      <Card>
        <CardHeader>
          <CardTitle className="text-base text-text-secondary">
            {filter === 'pending' && '暂无待完成的任务'}
            {filter === 'in_progress' && '暂无进行中的任务'}
            {filter === 'completed' && '暂无已完成的任务'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-text-muted">
            教师布置的练习任务和自主练习记录将显示在这里。
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd r-mos-frontend && npx vitest run src/pages/__tests__/MyTasksPage.test.tsx 2>&1 | tail -10
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add r-mos-frontend/src/pages/MyTasksPage.tsx r-mos-frontend/src/pages/__tests__/MyTasksPage.test.tsx
git commit -m "feat: add MyTasksPage skeleton with status tabs"
```

---

### Task 10: Create ScenarioPickerPage skeleton

**Files:**
- Create: `src/pages/ScenarioPickerPage.tsx`
- Test: `src/pages/__tests__/ScenarioPickerPage.test.tsx`

- [ ] **Step 1: Write the test**

Create `src/pages/__tests__/ScenarioPickerPage.test.tsx`:
```tsx
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import ScenarioPickerPage from '../ScenarioPickerPage'

describe('ScenarioPickerPage', () => {
  it('renders the page title', () => {
    render(
      <MemoryRouter>
        <ScenarioPickerPage />
      </MemoryRouter>,
    )
    expect(screen.getByText('自主练习')).toBeInTheDocument()
  })

  it('renders difficulty filter options', () => {
    render(
      <MemoryRouter>
        <ScenarioPickerPage />
      </MemoryRouter>,
    )
    expect(screen.getByText('全部')).toBeInTheDocument()
    expect(screen.getByText('入门')).toBeInTheDocument()
    expect(screen.getByText('进阶')).toBeInTheDocument()
    expect(screen.getByText('高级')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd r-mos-frontend && npx vitest run src/pages/__tests__/ScenarioPickerPage.test.tsx 2>&1 | tail -10
```

Expected: FAIL — module not found

- [ ] **Step 3: Write the page**

Create `src/pages/ScenarioPickerPage.tsx`:
```tsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Dumbbell, Sparkles } from 'lucide-react'

type Difficulty = 'all' | 'beginner' | 'intermediate' | 'advanced'

export default function ScenarioPickerPage() {
  const [difficulty, setDifficulty] = useState<Difficulty>('all')
  const navigate = useNavigate()

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Dumbbell className="h-6 w-6 text-primary" />
        <h1 className="text-2xl font-semibold text-text-primary">自主练习</h1>
      </div>

      <Card className="border-primary/20 bg-primary-muted/30">
        <CardContent className="flex items-center gap-3 py-4">
          <Sparkles className="h-5 w-5 text-primary" />
          <p className="text-sm text-text-secondary">
            AI 将根据你的技能画像推荐适合当前水平的练习场景。
          </p>
        </CardContent>
      </Card>

      <Tabs value={difficulty} onValueChange={(v) => setDifficulty(v as Difficulty)}>
        <TabsList>
          <TabsTrigger value="all">全部</TabsTrigger>
          <TabsTrigger value="beginner">入门</TabsTrigger>
          <TabsTrigger value="intermediate">进阶</TabsTrigger>
          <TabsTrigger value="advanced">高级</TabsTrigger>
        </TabsList>
      </Tabs>

      <Card>
        <CardHeader>
          <CardTitle className="text-base text-text-secondary">
            暂无可用的练习场景
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-text-muted">
            故障场景库将在后续版本中填充。届时你可以选择不同类型和难度的故障进行练习。
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd r-mos-frontend && npx vitest run src/pages/__tests__/ScenarioPickerPage.test.tsx 2>&1 | tail -10
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add r-mos-frontend/src/pages/ScenarioPickerPage.tsx r-mos-frontend/src/pages/__tests__/ScenarioPickerPage.test.tsx
git commit -m "feat: add ScenarioPickerPage skeleton with difficulty filter"
```

---

### Task 11: Remove backend demo endpoints

**Files:**
- Delete: `r-mos-backend/app/api/v1/endpoints/demo.py`
- Modify: `r-mos-backend/app/api/v1/__init__.py`

- [x] **Step 1: Remove demo import and router registration**

In `r-mos-backend/app/api/v1/__init__.py`, remove:
```python
# Line 26: remove from import block
    demo,        # Demo-only: SSE chat + gradual fault trigger
```

```python
# Line 53: remove router registration
api_router.include_router(demo.router, tags=["demo"])  # Demo-only endpoints
```

- [x] **Step 2: Delete the demo endpoint file**

```bash
rm r-mos-backend/app/api/v1/endpoints/demo.py
```

- [x] **Step 3: Verify the backend starts without errors**

```bash
cd r-mos-backend && source venv/bin/activate && python -c "from app.api.v1 import api_router; print(f'Routes: {len(api_router.routes)}')"
```

Expected: prints route count without ImportError

- [x] **Step 4: Commit**

```bash
git add r-mos-backend/app/api/v1/__init__.py
git add -A r-mos-backend/app/api/v1/endpoints/demo.py
git commit -m "chore: remove backend demo endpoints"
```

---

### Task 12: Remove backend Phase 2 dead services

**Files:**
- Delete: 6 service files (see File Structure above)
- Delete: 3 test files
- Modify: `r-mos-backend/app/api/v1/endpoints/agent.py` (remove imports and route blocks)

- [ ] **Step 1: Identify Phase 2 route blocks in agent.py**

The agent.py file has these Phase 2 sections that reference the deleted services. Each section is a group of route handler functions. Find the sections by searching for:

- `belief` routes (belief state endpoints — ~80 lines)
- `compensation` routes (compensation planner endpoints — ~100 lines)
- `replay` / `recalcul` routes (decision replay endpoints — ~80 lines)
- `metrics` / `acceptance` routes (acceptance metrics endpoints — ~80 lines)
- `monitor` routes (system monitor endpoints — ~80 lines)
- `feature` routes (feature flag endpoints — ~60 lines)

Comment out or delete these route blocks entirely. Also remove the `evaluation/report` and `sop/quality` endpoints if they depend on deleted services.

- [ ] **Step 2: Remove Phase 2 imports from agent.py**

Remove these import lines from the top of agent.py:
```python
from app.services.feature_flag import feature_flags                    # line 36
from app.services.belief_state import get_or_create_belief_state, get_belief_state, BeliefConfidence, BeliefSource  # line 37
from app.services.evidence_collector import evidence_collector, EvidenceType, EvidenceStatus  # line 38
from app.services.compensation_planner import compensation_planner, CompensationStrategy  # line 39
```

And the deferred imports further down:
```python
from app.services.decision_recalculator import (...)    # line 1444
from app.services.acceptance_metrics import (...)       # line 1449
from app.services.system_monitor import (...)           # line 1454
```

Keep imports that are still used by remaining routes (e.g., `approval_queue`, `policy_matrix`, `orchestrator_v2`).

- [ ] **Step 3: Delete service files**

```bash
cd r-mos-backend
rm app/services/belief_state.py
rm app/services/compensation_planner.py
rm app/services/decision_recalculator.py
rm app/services/acceptance_metrics.py
rm app/services/feature_flag.py
rm app/services/system_monitor.py
```

- [ ] **Step 4: Delete Phase 2/3/4 contract tests**

```bash
cd r-mos-backend
rm -f tests/unit/test_phase2_contract.py
rm -f tests/unit/test_phase3_contract.py
rm -f tests/unit/test_phase4_contract.py
```

- [ ] **Step 5: Verify the backend still imports cleanly**

```bash
cd r-mos-backend && source venv/bin/activate && python -c "from app.api.v1 import api_router; print('OK')"
```

Expected: `OK`

- [ ] **Step 6: Run remaining backend tests**

```bash
cd r-mos-backend && source venv/bin/activate && python -m pytest tests/ -x --timeout=30 2>&1 | tail -20
```

Expected: all remaining tests pass (some may need adjustment if they imported Phase 2 fixtures)

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "chore: remove Phase 2 dead services (belief, compensation, replay, metrics, feature flags)"
```

---

### Task 13: Frontend build verification

**Files:** None (verification only)

- [ ] **Step 1: Run TypeScript type check on entire frontend**

```bash
cd r-mos-frontend && npx tsc --noEmit 2>&1 | tail -30
```

Expected: no errors. If there are errors from deleted imports in files we didn't touch, fix them by removing the dead references.

- [ ] **Step 2: Run Vite build**

```bash
cd r-mos-frontend && npm run build 2>&1 | tail -20
```

Expected: build succeeds

- [ ] **Step 3: Run frontend tests**

```bash
cd r-mos-frontend && npx vitest run 2>&1 | tail -30
```

Expected: all tests pass. If tests for deleted pages still exist and fail, delete them.

- [ ] **Step 4: Fix any remaining broken references**

Search for any remaining imports of deleted modules:
```bash
cd r-mos-frontend && grep -r "demoMode\|AIChatPage\|BeliefTracker\|DiagnosisPage\|EvidencePage\|IncidentList\|AssessmentStatus\|TaskExecution\|ReplayPage\|MaintenanceProjectDraft\|SOPMaintenanceInspector\|TrainingWorkbench\|AcceptanceDashboard\|CompensationPage\|FeatureFlagPage\|LLMMetrics\|FaultManage\|SeedData\|DEMO_MODE\|demo\.ts" src/ --include="*.ts" --include="*.tsx" -l
```

Fix any hits.

- [ ] **Step 5: Commit fixes if any**

```bash
git add -A && git diff --cached --stat && git commit -m "fix: clean up remaining references to deleted modules" || echo "NOTHING TO COMMIT"
```

---

### Task 14: End-to-end smoke test

**Files:** None (manual verification)

- [ ] **Step 1: Start backend**

```bash
cd r-mos-backend && source venv/bin/activate && python main.py
```

- [ ] **Step 2: Start frontend (without DEMO_MODE)**

```bash
cd r-mos-frontend && npm run dev
```

- [ ] **Step 3: Verify login and navigation**

1. Open `http://localhost:3000`
2. Login with test credentials
3. Verify sidebar navigation matches the new structure for the logged-in role
4. Click through each nav item and verify pages load without blank screens or console errors

- [ ] **Step 4: Verify core flow pages**

1. `/monitor` — loads, shows joint cards, no demo button
2. `/agent/workbench` — loads, chat input works
3. `/maintenance` — loads, SOP player visible
4. `/reports` — loads, shows empty or list view
5. `/my-tasks` — loads, shows tabs and empty state
6. `/scenarios` — loads, shows difficulty filter and empty state

- [ ] **Step 5: Verify deleted pages return 404 / redirect**

Navigate to `/ai-chat`, `/incidents`, `/admin/features` — should redirect to `/` or show fallback.

- [ ] **Step 6: Commit final state tag**

```bash
git tag v0.2.0-product-skeleton
```
