# Phase 3: 前端配置驱动化 — 详细实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将前端菜单/路由/UI 配置从代码中提取为配置对象，支持角色/权限动态决定菜单项，消除版本号和状态标签的重复硬编码。

**Architecture:** 创建 `src/config/` 目录集中管理所有配置对象（菜单、路由权限、状态标签、品牌信息）。各页面/组件从配置模块导入，不再各自维护本地副本。WebSocket URL 统一走环境变量。

**Tech Stack:** React 18 + TypeScript + Vite

---

## 文件结构

```
r-mos-frontend/src/config/
├── nav.ts              ← 新建：菜单配置（从 AppLayout 提取）
├── routes.ts           ← 新建：路由权限表
├── brand.ts            ← 新建：品牌名/版本号集中管理
├── statusLabels.ts     ← 新建：状态标签/颜色统一映射
└── robots.ts           ← 已有：机器人目录

r-mos-frontend/src/
├── components/Layout/AppLayout.tsx    ← 修改：从 config/nav 导入菜单
├── App.tsx                            ← 修改：从 config/routes 生成路由
├── pages/LoginPage.tsx                ← 修改：从 config/brand 读取版本
├── pages/RegisterPage.tsx             ← 修改：同上
├── pages/agent/AgentWorkbenchPage.tsx ← 修改：意图从配置读取
├── hooks/useWebSocket.ts             ← 确认已用 env var
└── components/Viewer3D/constants.ts  ← 修改：WS_CONFIG 使用 env var
```

---

### Task 23: 菜单配置对象化

**Files:**
- Create: `r-mos-frontend/src/config/nav.ts`
- Modify: `r-mos-frontend/src/components/Layout/AppLayout.tsx`
- Modify: `r-mos-frontend/src/components/Layout/__tests__/AppLayout.test.tsx`

- [ ] **Step 1: 创建菜单配置文件**

创建 `r-mos-frontend/src/config/nav.ts`：

```typescript
import {
  Activity, BookOpen, Brain, BotMessageSquare, ClipboardList,
  Cog, Eye, Gamepad2, GraduationCap, LayoutDashboard, Library,
  ListChecks, MonitorCheck, Share2, Trophy, Users, Wrench,
} from 'lucide-react'
import type { UserRole } from '@/store/authStore'

export interface NavItem {
  label: string
  to: string
  icon: typeof Activity
}

export interface NavGroup {
  title: string
  items: NavItem[]
}

export interface LayoutConfig {
  badgeLabel: string
  badgeVariant: 'default' | 'secondary' | 'outline'
  navGroups: NavGroup[]
}

const STUDENT_NAV: NavGroup[] = [
  {
    title: '练习中心',
    items: [
      { label: '我的任务', to: '/my-tasks', icon: ClipboardList },
      { label: '自主练习', to: '/scenarios', icon: Gamepad2 },
    ],
  },
  {
    title: '维保操作',
    items: [
      { label: '实时监控', to: '/monitor', icon: Activity },
      { label: 'AI 诊断工作台', to: '/agent/workbench', icon: BotMessageSquare },
      { label: '维保练习', to: '/maintenance', icon: Wrench },
    ],
  },
  {
    title: '学习成长',
    items: [
      { label: '我的技能', to: '/student/skills', icon: Trophy },
    ],
  },
  {
    title: '进阶工具',
    items: [
      { label: '3D 展示', to: '/3d-viewer', icon: Eye },
    ],
  },
]

const TEACHER_NAV: NavGroup[] = [
  {
    title: '教学管理',
    items: [
      { label: '班级监控台', to: '/workbench/teaching', icon: MonitorCheck },
      { label: '作业管理', to: '/teaching/assignments', icon: ListChecks },
      { label: '学员档案', to: '/teacher/students', icon: Users },
    ],
  },
  {
    title: 'SOP & 工具',
    items: [
      { label: 'SOP 管理', to: '/sops', icon: BookOpen },
      { label: '实时监控', to: '/monitor', icon: Activity },
      { label: '知识库', to: '/knowledge', icon: Library },
    ],
  },
  {
    title: '记录',
    items: [
      { label: '共享机器人', to: '/shared-robots', icon: Share2 },
    ],
  },
  {
    title: 'AI 工具',
    items: [
      { label: 'AI 诊断工作台', to: '/agent/workbench', icon: BotMessageSquare },
    ],
  },
]

const ADMIN_NAV: NavGroup[] = [
  {
    title: '概览',
    items: [
      { label: '系统概览', to: '/admin/console', icon: LayoutDashboard },
    ],
  },
  ...TEACHER_NAV,
]

export const LAYOUT_CONFIG: Record<UserRole, LayoutConfig> = {
  student: { badgeLabel: 'Student', badgeVariant: 'default', navGroups: STUDENT_NAV },
  teacher: { badgeLabel: 'Teacher', badgeVariant: 'secondary', navGroups: TEACHER_NAV },
  admin: { badgeLabel: 'Admin', badgeVariant: 'outline', navGroups: ADMIN_NAV },
}
```

- [ ] **Step 2: 修改 AppLayout 从配置导入**

在 `AppLayout.tsx` 中：
1. 移除 `STUDENT_NAV`、`TEACHER_NAV`、`ADMIN_NAV`、`LAYOUT_CONFIG` 的本地定义
2. 移除对应的 lucide-react 图标 import（已移到 nav.ts）
3. 添加 `import { LAYOUT_CONFIG } from '@/config/nav'`
4. 保持 `NavItem`/`NavGroup` 类型引用改为从 `@/config/nav` 导入

- [ ] **Step 3: 验证测试通过**

```bash
npx vitest run src/components/Layout/__tests__/AppLayout.test.tsx
```

- [ ] **Step 4: Commit**

```bash
git add src/config/nav.ts src/components/Layout/AppLayout.tsx
git commit -m "refactor(nav): extract menu configuration to config/nav.ts"
```

---

### Task 24: 路由权限表化

**Files:**
- Create: `r-mos-frontend/src/config/routes.ts`
- Modify: `r-mos-frontend/src/App.tsx`

- [ ] **Step 1: 创建路由权限配置**

创建 `r-mos-frontend/src/config/routes.ts`：

```typescript
import type { UserRole } from '@/store/authStore'

export interface RouteConfig {
  path: string
  allowedRoles?: UserRole[]
}

/**
 * 路由权限表。
 * - allowedRoles 为空/undefined 表示任何已登录用户可访问
 * - 只管权限，不管组件映射（组件仍在 App.tsx 的 JSX 中指定）
 */
export const ROUTE_PERMISSIONS: Record<string, UserRole[] | undefined> = {
  // 学生专属
  'dashboard': ['student'],
  'my-tasks': ['student'],
  'scenarios': ['student'],
  'student/skills': ['student'],

  // 教师/管理员
  'workbench/teaching': ['teacher', 'admin'],
  'teaching/assignments': ['teacher', 'admin'],
  'teaching/assignments/:assignmentId': ['teacher', 'admin'],
  'teacher/students': ['teacher', 'admin'],
  'teacher/students/:studentId': ['teacher', 'admin'],
  'sops': ['teacher', 'admin'],
  'knowledge': ['teacher', 'admin'],
  'shared-robots': ['teacher', 'admin'],

  // 管理员专属
  'admin/console': ['admin'],

  // 通用（已登录即可）
  'monitor': undefined,
  'maintenance': undefined,
  '3d-viewer': undefined,
  'agent/workbench': undefined,
  'settings': undefined,
  'reports': undefined,
  'reports/:id': undefined,
}

/**
 * 根据路由路径获取允许的角色列表
 */
export function getAllowedRoles(path: string): UserRole[] | undefined {
  return ROUTE_PERMISSIONS[path]
}
```

- [ ] **Step 2: 修改 App.tsx 使用权限表**

在 `App.tsx` 中：
1. 导入 `import { getAllowedRoles } from '@/config/routes'`
2. 修改 `withRoles` 调用，改为从权限表查询：

```typescript
// 之前：
// <Route path="dashboard" element={withRoles(<DashboardPage />, ['student'])} />
// 之后：
<Route path="dashboard" element={withRoles(<DashboardPage />, getAllowedRoles('dashboard'))} />
```

对每个路由执行此替换。

- [ ] **Step 3: 验证编译和路由正常**

```bash
npx tsc --noEmit
npx vitest run src/components/Layout/__tests__/AppLayout.test.tsx
```

- [ ] **Step 4: Commit**

```bash
git add src/config/routes.ts src/App.tsx
git commit -m "refactor(routes): extract route permissions to config/routes.ts"
```

---

### Task 25: AI 工作台意图配置化

**Files:**
- Create: `r-mos-frontend/src/config/agentIntents.ts`
- Modify: `r-mos-frontend/src/pages/agent/AgentWorkbenchPage.tsx`

- [ ] **Step 1: 提取意图和快速操作配置**

创建 `r-mos-frontend/src/config/agentIntents.ts`：

```typescript
import {
  Brain, ClipboardCheck, ClipboardList, FileSearch, MessageCircle, Stethoscope,
} from 'lucide-react'

export interface IntentOption {
  value: string
  label: string
  icon: typeof Brain
}

export interface QuickAction {
  id: string
  title: string
  desc: string
  prompt: string
  intent: string
  icon: typeof Brain
}

export const INTENT_OPTIONS: IntentOption[] = [
  { value: 'general', label: '通用问答', icon: MessageCircle },
  { value: 'execute-task', label: '派单维保', icon: ClipboardList },
  { value: 'delegate-diagnoser', label: '诊断问题', icon: Stethoscope },
  { value: 'read-kb', label: '知识查询', icon: FileSearch },
  { value: 'write-kb', label: '知识记录', icon: Brain },
  { value: 'delegate-coach', label: '训练指导', icon: ClipboardCheck },
]

export const QUICK_ACTIONS: QuickAction[] = [
  {
    id: 'dispatch',
    title: '派单维保',
    desc: '创建维保任务并分派',
    prompt: '请帮我创建一个维保任务',
    intent: 'execute-task',
    icon: ClipboardList,
  },
  {
    id: 'diagnose',
    title: '诊断问题',
    desc: '分析机器人故障原因',
    prompt: '请帮我诊断当前机器人的问题',
    intent: 'delegate-diagnoser',
    icon: Stethoscope,
  },
  {
    id: 'kb',
    title: '知识查询',
    desc: '搜索维保知识库',
    prompt: '请帮我查询相关知识',
    intent: 'read-kb',
    icon: FileSearch,
  },
  {
    id: 'tasks',
    title: '查看任务',
    desc: '查看当前任务状态',
    prompt: '请帮我查看当前的任务列表',
    intent: 'general',
    icon: ClipboardList,
  },
  {
    id: 'approvals',
    title: '审批待办',
    desc: '查看待审批事项',
    prompt: '请帮我查看待审批的事项',
    intent: 'general',
    icon: ClipboardCheck,
  },
  {
    id: 'reports',
    title: '查看报告',
    desc: '查看维保报告',
    prompt: '请帮我查看最近的维保报告',
    intent: 'general',
    icon: FileSearch,
  },
]

export const RISK_STATUS_MAP: Record<string, 'success' | 'warning' | 'destructive'> = {
  R0: 'success',
  R1: 'success',
  R2: 'warning',
  R3: 'destructive',
}
```

- [ ] **Step 2: 修改 AgentWorkbenchPage 导入配置**

在 `AgentWorkbenchPage.tsx` 中：
1. 移除 `intentOptions`、`quickActions`、`riskStatusMap` 的本地定义
2. 添加 `import { INTENT_OPTIONS, QUICK_ACTIONS, RISK_STATUS_MAP } from '@/config/agentIntents'`
3. 更新组件内引用名称

- [ ] **Step 3: 验证编译**

```bash
npx tsc --noEmit
```

- [ ] **Step 4: Commit**

```bash
git add src/config/agentIntents.ts src/pages/agent/AgentWorkbenchPage.tsx
git commit -m "refactor(agent): extract intent and quick action config to config/agentIntents.ts"
```

---

### Task 26: WebSocket URL 环境化

**Files:**
- Modify: `r-mos-frontend/src/components/Viewer3D/constants.ts`

- [ ] **Step 1: 修复 Viewer3D 的 WS_CONFIG**

在 `constants.ts` 中，修改 `WS_CONFIG.url` 使用环境变量：

```typescript
// 之前：
// url: 'ws://localhost:8000/ws/robot/status',
// 之后：
url: `${import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'}/ws/robot/status`,
```

- [ ] **Step 2: 确认 useWebSocket.ts 已使用环境变量**

验证 `src/hooks/useWebSocket.ts` 第 18 行已有：
```typescript
const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'
```

若已正确则无需修改。

- [ ] **Step 3: Commit**

```bash
git add src/components/Viewer3D/constants.ts
git commit -m "fix(ws): use VITE_WS_BASE_URL env var in Viewer3D WS_CONFIG"
```

---

### Task 27: 版本号/品牌名集中管理

**Files:**
- Create: `r-mos-frontend/src/config/brand.ts`
- Modify: `r-mos-frontend/src/pages/LoginPage.tsx`
- Modify: `r-mos-frontend/src/pages/RegisterPage.tsx`
- Modify: `r-mos-frontend/src/components/Layout/AppLayout.tsx`

- [ ] **Step 1: 创建品牌配置**

创建 `r-mos-frontend/src/config/brand.ts`：

```typescript
/**
 * 品牌和版本信息 — 单一来源。
 * 版本号优先从 package.json 读取（Vite 在构建时注入），
 * 品牌名可在此处集中修改。
 */
export const BRAND_NAME = 'R-MOS'
export const APP_VERSION = __APP_VERSION__ ?? '0.2.0'
export const COPYRIGHT_YEAR = '2026'
export const COPYRIGHT_LINE = `\u00A9 ${COPYRIGHT_YEAR} ${BRAND_NAME} \u00B7 v${APP_VERSION}`
```

- [ ] **Step 2: 在 vite.config.ts 注入版本号**

在 `vite.config.ts` 的 `define` 中添加：

```typescript
define: {
  __APP_VERSION__: JSON.stringify(process.env.npm_package_version),
},
```

并在 `src/vite-env.d.ts` 添加类型声明：

```typescript
declare const __APP_VERSION__: string
```

- [ ] **Step 3: 替换所有硬编码版本号和品牌名**

在 `LoginPage.tsx`、`RegisterPage.tsx`、`AppLayout.tsx` 中：
1. 添加 `import { BRAND_NAME, COPYRIGHT_LINE } from '@/config/brand'`
2. 替换所有 `R-MOS` 字面量为 `{BRAND_NAME}`
3. 替换 `© 2026 R-MOS · v0.2.0` 为 `{COPYRIGHT_LINE}`

- [ ] **Step 4: 验证编译**

```bash
npx tsc --noEmit
```

- [ ] **Step 5: Commit**

```bash
git add src/config/brand.ts src/pages/LoginPage.tsx src/pages/RegisterPage.tsx \
  src/components/Layout/AppLayout.tsx vite.config.ts src/vite-env.d.ts
git commit -m "refactor(brand): centralize brand name and version in config/brand.ts"
```

---

### Task 28: 状态标签/颜色映射集中化

**Files:**
- Create: `r-mos-frontend/src/config/statusLabels.ts`
- Modify: `r-mos-frontend/src/teaching/pages/TeachingAttemptPage.tsx`
- Modify: `r-mos-frontend/src/teaching/pages/TeacherMonitorPage.tsx`
- Modify: `r-mos-frontend/src/components/knowledge/RobotSidebar.tsx`
- Modify: `r-mos-frontend/src/components/knowledge/AnalysisStatusPanel.tsx`

- [ ] **Step 1: 创建状态标签配置**

创建 `r-mos-frontend/src/config/statusLabels.ts`：

```typescript
export interface StatusConfig {
  label: string
  variant: 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning'
  dotClass?: string
}

/** 作业尝试状态 */
export const ATTEMPT_STATUS: Record<string, StatusConfig> = {
  in_progress: { label: '进行中', variant: 'default' },
  completed: { label: '已完成', variant: 'success' },
  graded: { label: '已评分', variant: 'secondary' },
  abandoned: { label: '已放弃', variant: 'destructive' },
}

/** 机器人型号状态 */
export const ROBOT_MODEL_STATUS: Record<string, StatusConfig> = {
  draft: { label: '草稿', variant: 'secondary' },
  analyzing: { label: '分析中', variant: 'warning' },
  ready: { label: '就绪', variant: 'success' },
}

/** 分析任务状态 */
export const ANALYSIS_STATUS: Record<string, StatusConfig> = {
  pending: { label: '排队中', variant: 'secondary' },
  running: { label: '分析中', variant: 'warning' },
  completed: { label: '完成', variant: 'success' },
  failed: { label: '失败', variant: 'destructive' },
}

/** SOP 难度等级 */
export const SOP_DIFFICULTY: Record<string, StatusConfig> = {
  L1: { label: '初级', variant: 'success' },
  L2: { label: '初级', variant: 'success' },
  L3: { label: '中级', variant: 'warning' },
  L4: { label: '高级', variant: 'destructive' },
  L5: { label: '专家', variant: 'destructive' },
  low: { label: '初级', variant: 'success' },
  medium: { label: '中级', variant: 'warning' },
  high: { label: '高级', variant: 'destructive' },
}
```

- [ ] **Step 2: 替换各页面的本地状态映射**

逐一修改以下文件，将本地 `statusLabelMap` / `STATUS_CONFIG` / `STATUS_MAP` 替换为从 `@/config/statusLabels` 导入：

1. `TeachingAttemptPage.tsx`: 删除本地 `statusLabelMap`，改用 `ATTEMPT_STATUS`
2. `TeacherMonitorPage.tsx`: 删除 `attemptStatusLabel()`/`attemptStatusTone()` 函数，改用 `ATTEMPT_STATUS`
3. `RobotSidebar.tsx`: 删除本地 `STATUS_CONFIG`，改用 `ROBOT_MODEL_STATUS`
4. `AnalysisStatusPanel.tsx`: 删除本地 `STATUS_MAP`，改用 `ANALYSIS_STATUS`

- [ ] **Step 3: 验证编译和测试**

```bash
npx tsc --noEmit
npx vitest run
```

- [ ] **Step 4: Commit**

```bash
git add src/config/statusLabels.ts src/teaching/pages/TeachingAttemptPage.tsx \
  src/teaching/pages/TeacherMonitorPage.tsx src/components/knowledge/RobotSidebar.tsx \
  src/components/knowledge/AnalysisStatusPanel.tsx
git commit -m "refactor(status): centralize status label/color maps in config/statusLabels.ts"
```

---

## 验收标准

- [ ] 添加新菜单项只需修改 `config/nav.ts`，无需改 `AppLayout.tsx`
- [ ] 添加新路由权限只需修改 `config/routes.ts`
- [ ] 所有 WS 地址走 `VITE_WS_BASE_URL` 环境变量
- [ ] 版本号从 `package.json` 自动注入，全局唯一来源
- [ ] 状态标签集中管理，无重复定义
- [ ] 所有现有测试通过
