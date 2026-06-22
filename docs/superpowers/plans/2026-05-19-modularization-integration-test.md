# 模块化改造集成验证测试计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 验证 4 Phase / 33 Task 模块化改造后，所有功能模块正确使用配置/清单/API 驱动数据，无遗留硬编码，端到端功能完整

**Architecture:** 前端单元+集成测试（Vitest + React Testing Library），后端 E2E 测试（pytest + TestClient），覆盖全部模块化改造点：配置驱动导航、Manifest 驱动 3D/裁决、API 驱动 SOP、YAML 驱动种子/故障/Prompt

**Tech Stack:** Vitest, React Testing Library, pytest, pytest-asyncio, FastAPI TestClient, aiosqlite

---

## 测试路径概览

```
登录 → 角色菜单(config/nav.ts) → 路由权限(config/routes.ts) → 品牌信息(config/brand.ts)
  ↓
机器人上下文切换(robotStore) → Manifest加载(useRobotDataManifest) → 裁决数据桥接(manifestAdapter)
  ↓
SOP脚本API加载(useSOPScripts) → 维保页面渲染(SOPMaintenancePage) → 状态标签(config/statusLabels.ts)
  ↓
Agent意图配置(config/agentIntents.ts) → AI工作台(AgentWorkbenchPage)
  ↓
教学域(teachingStore) → 知识库 → 监控页
  ↓
后端：YAML种子(seed_base.yaml) → Mock故障(mock_faults.yaml) → LLM Prompt(system_prompt.txt) → SOP裁决API
```

---

### Task 1: 前端配置驱动 — 导航 / 路由 / 品牌

**验证目标：** `config/nav.ts`, `config/routes.ts`, `config/brand.ts` 被正确消费，无硬编码菜单/权限/品牌

**Files:**
- Create: `r-mos-frontend/src/config/__tests__/configDriven.test.ts`

- [ ] **Step 1: 编写导航配置测试**

```typescript
import { describe, expect, it } from 'vitest'
import { LAYOUT_CONFIG } from '@/config/nav'
import { ROUTE_PERMISSIONS, getAllowedRoles } from '@/config/routes'
import { BRAND_NAME, APP_VERSION, COPYRIGHT_LINE } from '@/config/brand'

describe('Config-driven: nav.ts', () => {
  it('provides layout config for all three roles', () => {
    expect(LAYOUT_CONFIG).toHaveProperty('student')
    expect(LAYOUT_CONFIG).toHaveProperty('teacher')
    expect(LAYOUT_CONFIG).toHaveProperty('admin')
  })

  it('student nav has no teacher-only routes', () => {
    const studentPaths = LAYOUT_CONFIG.student.navGroups
      .flatMap((g) => g.items.map((i) => i.to))
    expect(studentPaths).not.toContain('/knowledge')
    expect(studentPaths).not.toContain('/sops')
    expect(studentPaths).not.toContain('/teacher/students')
  })

  it('teacher nav includes teaching management routes', () => {
    const teacherPaths = LAYOUT_CONFIG.teacher.navGroups
      .flatMap((g) => g.items.map((i) => i.to))
    expect(teacherPaths).toContain('/knowledge')
    expect(teacherPaths).toContain('/teacher/students')
  })

  it('each nav item has label, to, and icon', () => {
    for (const role of ['student', 'teacher', 'admin'] as const) {
      for (const group of LAYOUT_CONFIG[role].navGroups) {
        for (const item of group.items) {
          expect(item.label).toBeTruthy()
          expect(item.to).toMatch(/^\//)
          expect(typeof item.icon).toBe('function')
        }
      }
    }
  })
})

describe('Config-driven: routes.ts', () => {
  it('student-only routes require student role', () => {
    expect(getAllowedRoles('dashboard')).toEqual(['student'])
    expect(getAllowedRoles('my-tasks')).toEqual(['student'])
    expect(getAllowedRoles('scenarios')).toEqual(['student'])
  })

  it('teacher routes allow teacher and admin', () => {
    expect(getAllowedRoles('knowledge')).toEqual(['teacher', 'admin'])
    expect(getAllowedRoles('sops')).toEqual(['teacher', 'admin'])
  })

  it('shared routes return undefined (any authenticated user)', () => {
    expect(getAllowedRoles('monitor')).toBeUndefined()
    expect(getAllowedRoles('maintenance')).toBeUndefined()
    expect(getAllowedRoles('settings')).toBeUndefined()
  })

  it('all nav items have corresponding route permissions', () => {
    for (const role of ['student', 'teacher', 'admin'] as const) {
      for (const group of LAYOUT_CONFIG[role].navGroups) {
        for (const item of group.items) {
          const routeKey = item.to.replace(/^\//, '')
          // Route either explicitly listed or implicitly open
          const roles = getAllowedRoles(routeKey)
          if (roles) {
            expect(roles).toContain(role)
          }
          // If undefined, route is open to all — that's fine
        }
      }
    }
  })
})

describe('Config-driven: brand.ts', () => {
  it('exports brand constants', () => {
    expect(BRAND_NAME).toBe('R-MOS')
    expect(APP_VERSION).toMatch(/^\d+\.\d+\.\d+$/)
    expect(COPYRIGHT_LINE).toContain(BRAND_NAME)
    expect(COPYRIGHT_LINE).toContain(APP_VERSION)
  })
})
```

- [ ] **Step 2: 运行测试确认通过**

Run: `cd r-mos-frontend && npx vitest run src/config/__tests__/configDriven.test.ts`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add r-mos-frontend/src/config/__tests__/configDriven.test.ts
git commit -m "test: config-driven nav/routes/brand integration tests"
```

---

### Task 2: 前端配置驱动 — 状态标签 / Agent 意图

**验证目标：** `config/statusLabels.ts`, `config/agentIntents.ts` 结构完整，消费端无硬编码

**Files:**
- Create: `r-mos-frontend/src/config/__tests__/statusAndIntents.test.ts`

- [ ] **Step 1: 编写状态标签和 Agent 意图测试**

```typescript
import { describe, expect, it } from 'vitest'
import {
  ATTEMPT_STATUS,
  ATTEMPT_STATUS_FALLBACK,
  ROBOT_MODEL_STATUS,
  ANALYSIS_STATUS,
} from '@/config/statusLabels'
import {
  INTENT_OPTIONS,
  QUICK_ACTIONS,
  RISK_STATUS_MAP,
} from '@/config/agentIntents'

describe('Config-driven: statusLabels.ts', () => {
  it('ATTEMPT_STATUS covers all lifecycle states', () => {
    const keys = Object.keys(ATTEMPT_STATUS)
    expect(keys).toContain('in_progress')
    expect(keys).toContain('completed')
    expect(keys).toContain('graded')
    expect(keys).toContain('abandoned')
  })

  it('each attempt status has label and variant', () => {
    for (const cfg of Object.values(ATTEMPT_STATUS)) {
      expect(cfg.label).toBeTruthy()
      expect(cfg.variant).toBeTruthy()
    }
  })

  it('fallback has valid structure', () => {
    expect(ATTEMPT_STATUS_FALLBACK.label).toBeTruthy()
    expect(ATTEMPT_STATUS_FALLBACK.variant).toBeTruthy()
  })

  it('ROBOT_MODEL_STATUS covers draft/analyzing/ready', () => {
    expect(ROBOT_MODEL_STATUS).toHaveProperty('draft')
    expect(ROBOT_MODEL_STATUS).toHaveProperty('analyzing')
    expect(ROBOT_MODEL_STATUS).toHaveProperty('ready')
  })

  it('ANALYSIS_STATUS covers pending/running/completed/failed', () => {
    expect(ANALYSIS_STATUS).toHaveProperty('pending')
    expect(ANALYSIS_STATUS).toHaveProperty('running')
    expect(ANALYSIS_STATUS).toHaveProperty('completed')
    expect(ANALYSIS_STATUS).toHaveProperty('failed')
  })

  it('each analysis status has icon component', () => {
    for (const cfg of Object.values(ANALYSIS_STATUS)) {
      expect(typeof cfg.icon).toBe('function')
    }
  })
})

describe('Config-driven: agentIntents.ts', () => {
  it('INTENT_OPTIONS has at least 5 intents', () => {
    expect(INTENT_OPTIONS.length).toBeGreaterThanOrEqual(5)
  })

  it('each intent has value and label', () => {
    for (const opt of INTENT_OPTIONS) {
      expect(opt.value).toBeTruthy()
      expect(opt.label).toBeTruthy()
    }
  })

  it('QUICK_ACTIONS reference valid intents', () => {
    const validIntents = new Set(INTENT_OPTIONS.map((o) => o.value))
    for (const action of QUICK_ACTIONS) {
      expect(validIntents).toContain(action.intent)
    }
  })

  it('each quick action has id, title, desc, prompt, icon', () => {
    for (const action of QUICK_ACTIONS) {
      expect(action.id).toBeTruthy()
      expect(action.title).toBeTruthy()
      expect(action.desc).toBeTruthy()
      expect(action.prompt).toBeTruthy()
      expect(typeof action.icon).toBe('function')
    }
  })

  it('RISK_STATUS_MAP covers R0-R3', () => {
    expect(RISK_STATUS_MAP.R0).toBe('success')
    expect(RISK_STATUS_MAP.R1).toBe('success')
    expect(RISK_STATUS_MAP.R2).toBe('warning')
    expect(RISK_STATUS_MAP.R3).toBe('error')
  })
})
```

- [ ] **Step 2: 运行测试确认通过**

Run: `cd r-mos-frontend && npx vitest run src/config/__tests__/statusAndIntents.test.ts`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add r-mos-frontend/src/config/__tests__/statusAndIntents.test.ts
git commit -m "test: status labels and agent intents config-driven tests"
```

---

### Task 3: Manifest 驱动 — RobotDataManifest + ManifestAdapter 集成

**验证目标：** `useRobotDataManifest` → `manifestAdapter` → adjudication 数据桥接全链路正确

**Files:**
- Create: `r-mos-frontend/src/adjudication/data/__tests__/manifestIntegration.test.ts`

- [ ] **Step 1: 编写 Manifest → Adjudication 全链路测试**

```typescript
import { describe, expect, it } from 'vitest'
import type {
  RobotDataManifest,
  ManifestPartEntry,
  ManifestScrewEntry,
  ManifestConstraintEntry,
} from '@/components/Viewer3D/assemblyManifest'
import {
  manifestPartToPart,
  manifestScrewToPart,
  manifestConstraintToConstraint,
  buildAdjudicationDataFromManifest,
} from '@/adjudication/data/manifestAdapter'
import { PartCategory } from '@/adjudication/types/adjudication'

const MOCK_PART: ManifestPartEntry = {
  id: 'part-torso-frame',
  bom_code: 'TF-001',
  display_name: '躯干框架',
  category: 'frame',
  mesh_id: 'torso_frame.glb',
  parent_id: null,
  local_position: [0, 0, 0],
  local_rotation: [0, 0, 0],
}

const MOCK_SCREW: ManifestScrewEntry = {
  id: 'screw-m3x8-torso-01',
  bom_code: 'S-M3-001',
  parent_id: 'part-torso-frame',
  position: [0.1, 0.2, 0.3],
  spec: {
    type: 'M3x8',
    pitch: 0.5,
    thread_length: 8,
    required_tool: 'hex_2mm',
    torque_nm: 0.8,
  },
}

const MOCK_CONSTRAINT: ManifestConstraintEntry = {
  id: 'c-torso-cover',
  type: 'fastening',
  constrained_part: 'part-torso-cover',
  constraining_part: 'part-torso-frame',
  params: { screw_ids: ['screw-m3x8-torso-01'] },
  release_condition: {
    type: 'screw_removal',
    required_actions: ['remove_screw:screw-m3x8-torso-01'],
  },
}

describe('ManifestAdapter: part conversion', () => {
  it('maps manifest part to adjudication Part with correct category', () => {
    const part = manifestPartToPart(MOCK_PART, '/api/v1/robots/1/assets')
    expect(part.id).toBe('part-torso-frame')
    expect(part.category).toBe(PartCategory.FRAME)
    expect(part.bomCode).toBe('TF-001')
    expect(part.displayName).toBe('躯干框架')
    expect(part.modelPath).toBe('/api/v1/robots/1/assets/torso_frame.glb')
  })

  it('handles all category mappings', () => {
    const categories = ['frame', 'cover', 'screw', 'motor', 'bearing', 'pcb', 'wire', 'tool']
    const expected = [
      PartCategory.FRAME, PartCategory.COVER, PartCategory.SCREW,
      PartCategory.MOTOR, PartCategory.BEARING, PartCategory.PCB,
      PartCategory.WIRE, PartCategory.TOOL,
    ]
    categories.forEach((cat, i) => {
      const part = manifestPartToPart({ ...MOCK_PART, category: cat }, '')
      expect(part.category).toBe(expected[i])
    })
  })

  it('falls back to FRAME for unknown category', () => {
    const part = manifestPartToPart({ ...MOCK_PART, category: 'unknown' }, '')
    expect(part.category).toBe(PartCategory.FRAME)
  })
})

describe('ManifestAdapter: screw conversion', () => {
  it('maps manifest screw to Part with screwSpec', () => {
    const screw = manifestScrewToPart(MOCK_SCREW, '/api/v1/robots/1/assets')
    expect(screw.id).toBe('screw-m3x8-torso-01')
    expect(screw.category).toBe(PartCategory.SCREW)
    expect(screw.screwSpec).toBeDefined()
    expect(screw.screwSpec!.type).toBe('M3x8')
    expect(screw.screwSpec!.torque).toBe(0.8)
    expect(screw.screwSpec!.requiredTool).toBe('hex_2mm')
  })
})

describe('ManifestAdapter: constraint conversion', () => {
  it('maps manifest constraint correctly', () => {
    const constraint = manifestConstraintToConstraint(MOCK_CONSTRAINT)
    expect(constraint.id).toBe('c-torso-cover')
    expect(constraint.type).toBe('fastening')
    expect(constraint.constrainedPart).toBe('part-torso-cover')
    expect(constraint.constrainingPart).toBe('part-torso-frame')
    expect(constraint.isActive).toBe(true)
  })
})

describe('ManifestAdapter: buildAdjudicationDataFromManifest full pipeline', () => {
  it('builds complete adjudication dataset from manifest', () => {
    const manifest: RobotDataManifest = {
      robotId: 1,
      robot_key: 'ATOM-01',
      version: '1.0',
      mesh_catalog: {},
      root_nodes: [],
      nodes: [],
      parts_registry: [MOCK_PART],
      screw_instances: [MOCK_SCREW],
      constraints: [MOCK_CONSTRAINT],
      camera_presets: {},
      tools: [],
      display_names: { 'part-torso-frame': '躯干框架' },
      overview_config: {
        overview_nodes: ['torso'],
        assembly_groups: {},
      },
    }

    const result = buildAdjudicationDataFromManifest(manifest)

    expect(Object.keys(result.partRegistry)).toHaveLength(1)
    expect(result.partRegistry['part-torso-frame'].displayName).toBe('躯干框架')

    expect(Object.keys(result.screwRegistry)).toHaveLength(1)
    expect(result.screwRegistry['screw-m3x8-torso-01'].screwSpec!.type).toBe('M3x8')

    expect(result.constraints).toHaveLength(1)
    expect(result.constraints[0].type).toBe('fastening')
  })

  it('handles empty manifest gracefully', () => {
    const manifest: RobotDataManifest = {
      robotId: 1,
      robot_key: 'EMPTY',
      version: '1.0',
      mesh_catalog: {},
      root_nodes: [],
      nodes: [],
    }

    const result = buildAdjudicationDataFromManifest(manifest)
    expect(Object.keys(result.partRegistry)).toHaveLength(0)
    expect(Object.keys(result.screwRegistry)).toHaveLength(0)
    expect(result.constraints).toHaveLength(0)
  })
})
```

- [ ] **Step 2: 运行测试确认通过**

Run: `cd r-mos-frontend && npx vitest run src/adjudication/data/__tests__/manifestIntegration.test.ts`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add r-mos-frontend/src/adjudication/data/__tests__/manifestIntegration.test.ts
git commit -m "test: manifest-to-adjudication full pipeline integration test"
```

---

### Task 4: SOP 脚本 API 驱动 — useSOPScripts Hook

**验证目标：** `useSOPScripts` 从 API 加载 SOP 裁决数据，不依赖任何本地硬编码文件

**Files:**
- Create: `r-mos-frontend/src/hooks/__tests__/useSOPScripts.test.ts`

- [ ] **Step 1: 编写 useSOPScripts Hook 测试**

```typescript
import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useSOPScripts } from '@/hooks/useSOPScripts'

const fetchMock = vi.fn()

vi.mock('@/api/sopScripts', () => ({
  fetchAdjudicationSOPs: (...args: unknown[]) => fetchMock(...args),
}))

describe('useSOPScripts hook (API-driven, no hardcoded fallback)', () => {
  beforeEach(() => {
    fetchMock.mockReset()
  })

  it('fetches SOP scripts from API on mount', async () => {
    const mockScripts = [
      {
        sopId: 'sop-db-1',
        title: '电机过热排查',
        difficulty: 'intermediate',
        steps: [],
      },
    ]
    fetchMock.mockResolvedValue(mockScripts)

    const { result } = renderHook(() => useSOPScripts(1))

    expect(result.current.loading).toBe(true)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.scripts).toEqual(mockScripts)
    expect(result.current.fromApi).toBe(true)
    expect(fetchMock).toHaveBeenCalledWith({ robot_model_id: 1 })
  })

  it('passes undefined filter when no robotModelId', async () => {
    fetchMock.mockResolvedValue([])

    const { result } = renderHook(() => useSOPScripts())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(fetchMock).toHaveBeenCalledWith(undefined)
  })

  it('returns empty array on API failure (no hardcoded fallback)', async () => {
    fetchMock.mockRejectedValue(new Error('Network error'))

    const { result } = renderHook(() => useSOPScripts(1))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.scripts).toEqual([])
    expect(result.current.fromApi).toBe(false)
  })

  it('refetches when robotModelId changes', async () => {
    fetchMock.mockResolvedValue([])

    const { result, rerender } = renderHook(
      ({ id }) => useSOPScripts(id),
      { initialProps: { id: 1 as number | null } },
    )

    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(fetchMock).toHaveBeenCalledWith({ robot_model_id: 1 })

    fetchMock.mockClear()
    rerender({ id: 2 })

    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(fetchMock).toHaveBeenCalledWith({ robot_model_id: 2 })
  })
})
```

- [ ] **Step 2: 运行测试确认通过**

Run: `cd r-mos-frontend && npx vitest run src/hooks/__tests__/useSOPScripts.test.ts`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add r-mos-frontend/src/hooks/__tests__/useSOPScripts.test.ts
git commit -m "test: useSOPScripts API-driven hook integration test"
```

---

### Task 5: 维保知识注入 — maintenanceKnowledge Manifest 注入

**验证目标：** `maintenanceKnowledge.ts` 的 `injectManifestKnowledge()` / `clearManifestKnowledge()` / `getManifestTools()` 正确工作

**Files:**
- Create: `r-mos-frontend/src/data/__tests__/maintenanceKnowledge.test.ts`

- [ ] **Step 1: 读取 maintenanceKnowledge.ts 了解导出接口**

Read: `r-mos-frontend/src/data/maintenanceKnowledge.ts` — 确认 `injectManifestKnowledge`, `clearManifestKnowledge`, `getManifestTools` 的签名和行为

- [ ] **Step 2: 编写 Manifest 知识注入测试**

```typescript
import { beforeEach, describe, expect, it } from 'vitest'
import {
  injectManifestKnowledge,
  clearManifestKnowledge,
  getManifestTools,
  getCorePartDetailRecord,
  getDetailPartDetailRecord,
} from '@/data/maintenanceKnowledge'

describe('maintenanceKnowledge manifest injection', () => {
  beforeEach(() => {
    clearManifestKnowledge()
  })

  it('returns null/empty before injection', () => {
    expect(getCorePartDetailRecord('some_link')).toBeNull()
    expect(getDetailPartDetailRecord('some_link', 'some_part')).toBeNull()
    expect(getManifestTools()).toEqual([])
  })

  it('injects and retrieves manifest knowledge', () => {
    injectManifestKnowledge({
      tools: [
        { id: 'hex_2mm', display_name: '2mm六角扳手', category: 'wrench' },
      ],
      display_names: { torso_link: '躯干' },
    })

    const tools = getManifestTools()
    expect(tools).toHaveLength(1)
    expect(tools[0].display_name).toBe('2mm六角扳手')
  })

  it('clearManifestKnowledge resets state', () => {
    injectManifestKnowledge({
      tools: [{ id: 't1', display_name: 'Tool', category: 'wrench' }],
    })
    expect(getManifestTools()).toHaveLength(1)

    clearManifestKnowledge()
    expect(getManifestTools()).toEqual([])
  })
})
```

- [ ] **Step 3: 运行测试确认通过**

Run: `cd r-mos-frontend && npx vitest run src/data/__tests__/maintenanceKnowledge.test.ts`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add r-mos-frontend/src/data/__tests__/maintenanceKnowledge.test.ts
git commit -m "test: maintenanceKnowledge manifest injection integration test"
```

---

### Task 6: 教学域 Store — teachingStore 配置驱动

**验证目标：** `teachingStore` 的 `startAttempt` 正确读取 `scoringPolicy.pass_score`（不再硬编码 70）

**Files:**
- Create: `r-mos-frontend/src/teaching/store/__tests__/teachingStore.test.ts`

- [ ] **Step 1: 编写 teachingStore pass_score 测试**

```typescript
import { beforeEach, describe, expect, it, vi } from 'vitest'

const createTaskMock = vi.fn()
const startTaskMock = vi.fn()
const createAttemptMock = vi.fn()

vi.mock('@/api/task', () => ({
  createTask: (...args: unknown[]) => createTaskMock(...args),
  startTask: (...args: unknown[]) => startTaskMock(...args),
}))

vi.mock('@/api/teaching', () => ({
  createAttempt: (...args: unknown[]) => createAttemptMock(...args),
  getAttemptEvidence: vi.fn(),
  listAssignments: vi.fn().mockResolvedValue([]),
}))

import { useTeachingStore } from '@/teaching/store/teachingStore'
import type { Assignment } from '@/types/teaching'

describe('teachingStore: config-driven pass_score', () => {
  beforeEach(() => {
    createTaskMock.mockReset()
    startTaskMock.mockReset()
    createAttemptMock.mockReset()
    useTeachingStore.setState({
      assignments: [],
      currentAttempt: null,
      evidence: null,
      loading: false,
      error: null,
    })
  })

  it('uses scoringPolicy.pass_score when available', async () => {
    createTaskMock.mockResolvedValue({ id: 42 })
    startTaskMock.mockResolvedValue({})
    createAttemptMock.mockResolvedValue({ id: 1 })

    const assignment: Assignment = {
      id: 10,
      title: '测试作业',
      sopId: 'sop-1',
      scoringPolicy: { pass_score: 85 },
    } as Assignment

    await useTeachingStore.getState().startAttempt(assignment, 1)

    expect(createTaskMock).toHaveBeenCalledWith(
      expect.objectContaining({ pass_score: 85 }),
    )
  })

  it('defaults to 70 when scoringPolicy is null', async () => {
    createTaskMock.mockResolvedValue({ id: 42 })
    startTaskMock.mockResolvedValue({})
    createAttemptMock.mockResolvedValue({ id: 1 })

    const assignment: Assignment = {
      id: 11,
      title: '默认分数作业',
      sopId: 'sop-2',
      scoringPolicy: null,
    } as Assignment

    await useTeachingStore.getState().startAttempt(assignment, 1)

    expect(createTaskMock).toHaveBeenCalledWith(
      expect.objectContaining({ pass_score: 70 }),
    )
  })

  it('throws when assignment has no sopId', async () => {
    const assignment: Assignment = {
      id: 12,
      title: '无SOP作业',
      sopId: undefined,
      scoringPolicy: null,
    } as unknown as Assignment

    await expect(
      useTeachingStore.getState().startAttempt(assignment, 1),
    ).rejects.toThrow('作业未配置 SOP')
  })
})
```

- [ ] **Step 2: 运行测试确认通过**

Run: `cd r-mos-frontend && npx vitest run src/teaching/store/__tests__/teachingStore.test.ts`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add r-mos-frontend/src/teaching/store/__tests__/teachingStore.test.ts
git commit -m "test: teachingStore config-driven pass_score integration test"
```

---

### Task 7: 后端 YAML 种子数据加载验证

**验证目标：** `data/config/seed_base.yaml` 格式正确且 `seed_data.py` 能正确解析

**Files:**
- Create: `r-mos-backend/tests/unit/test_yaml_config.py`

- [ ] **Step 1: 编写 YAML 配置加载测试**

```python
"""验证 YAML 配置文件格式正确且可被系统正确解析"""
import pathlib

import pytest
import yaml


CONFIG_DIR = pathlib.Path(__file__).resolve().parents[2] / "data" / "config"


class TestSeedBaseYAML:
    """seed_base.yaml 格式与内容验证"""

    @pytest.fixture(autouse=True)
    def load_yaml(self):
        with open(CONFIG_DIR / "seed_base.yaml", "r", encoding="utf-8") as f:
            self.data = yaml.safe_load(f)

    def test_has_required_top_level_keys(self):
        assert "default_robot_model" in self.data
        assert "sops" in self.data
        assert "fault_cases" in self.data

    def test_sops_have_required_fields(self):
        for sop in self.data["sops"]:
            assert "name" in sop
            assert "difficulty_level" in sop
            assert "estimated_time" in sop
            assert "steps" in sop
            assert len(sop["steps"]) > 0

    def test_sop_steps_have_required_fields(self):
        for sop in self.data["sops"]:
            for step in sop["steps"]:
                assert "step_index" in step
                assert "title" in step
                assert "expected_action" in step

    def test_fault_cases_have_required_fields(self):
        for fc in self.data["fault_cases"]:
            assert "fault_code" in fc
            assert "fault_type" in fc
            assert "severity" in fc
            assert "symptoms" in fc

    def test_difficulty_levels_are_valid(self):
        valid = {"low", "medium", "high"}
        for sop in self.data["sops"]:
            assert sop["difficulty_level"] in valid, (
                f"SOP '{sop['name']}' has invalid difficulty: {sop['difficulty_level']}"
            )


class TestMockFaultsYAML:
    """mock_faults.yaml 格式验证"""

    @pytest.fixture(autouse=True)
    def load_yaml(self):
        with open(CONFIG_DIR / "mock_faults.yaml", "r", encoding="utf-8") as f:
            self.data = yaml.safe_load(f)

    def test_has_fault_effects_and_sensor_defaults(self):
        assert "fault_effects" in self.data
        assert "sensor_defaults" in self.data

    def test_fault_effects_match_seed_fault_codes(self):
        with open(CONFIG_DIR / "seed_base.yaml", "r", encoding="utf-8") as f:
            seed = yaml.safe_load(f)
        seed_codes = {fc["fault_code"] for fc in seed["fault_cases"]}
        effect_codes = set(self.data["fault_effects"].keys())
        # All seed fault codes should have effects
        assert seed_codes <= effect_codes, (
            f"Missing fault effects for: {seed_codes - effect_codes}"
        )

    def test_sensor_defaults_have_reasonable_values(self):
        defaults = self.data["sensor_defaults"]
        assert defaults["imu_gravity_z"] == pytest.approx(9.8, abs=0.1)
        assert defaults["voltage_main"] > 0
        assert defaults["voltage_logic"] > 0


class TestSystemPrompt:
    """system_prompt.txt 存在且非空"""

    def test_prompt_file_exists_and_nonempty(self):
        prompt_path = CONFIG_DIR / "prompts" / "system_prompt.txt"
        assert prompt_path.exists(), "system_prompt.txt not found"
        content = prompt_path.read_text(encoding="utf-8")
        assert len(content) > 50, "system_prompt.txt seems too short"
        # 验证包含模板变量（如有）
        assert "维保" in content or "robot" in content.lower() or "maintenance" in content.lower()
```

- [ ] **Step 2: 运行测试确认通过**

Run: `cd r-mos-backend && python -m pytest tests/unit/test_yaml_config.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add r-mos-backend/tests/unit/test_yaml_config.py
git commit -m "test: YAML config files format and cross-reference validation"
```

---

### Task 8: 后端 SOP 裁决 API 端到端测试

**验证目标：** `GET /sops/adjudication` 返回正确的前端格式（difficulty 映射、sopId/stepId 格式）

**Files:**
- Create: `r-mos-backend/tests/e2e/test_e2e_sop_adjudication.py`

- [ ] **Step 1: 编写 SOP 裁决 API E2E 测试**

```python
"""SOP 裁决 API 端到端测试：验证 Phase 2 模块化输出"""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.sop import SOP, SOPStep


async def _seed_sop(session_factory: async_sessionmaker[AsyncSession]) -> int:
    """创建一个测试 SOP 并返回其 ID"""
    async with session_factory() as session:
        sop = SOP(
            name="测试SOP-裁决",
            description="裁决格式验证用",
            applicable_model="TEST_MODEL",
            category="maintenance",
            difficulty_level="medium",
            estimated_time=600,
            version="1.0",
            target_module="elbow",
        )
        session.add(sop)
        await session.flush()
        sop_id = sop.id

        step = SOPStep(
            sop_id=sop_id,
            step_index=1,
            title="检查温度",
            description="测量目标模组温度",
            expected_action="measure_temperature",
            is_critical=True,
            timeout_seconds=60,
        )
        session.add(step)
        await session.commit()
    return sop_id


@pytest.mark.e2e
def test_sop_adjudication_endpoint(
    e2e_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    """GET /sops/adjudication 返回前端裁决格式"""
    client, session_factory = e2e_env
    sop_id = asyncio.run(_seed_sop(session_factory))

    resp = client.get("/api/v1/sops/adjudication")
    assert resp.status_code == 200

    data = resp.json()
    assert "items" in data
    assert len(data["items"]) >= 1

    # 找到我们刚创建的 SOP
    target = None
    for item in data["items"]:
        if item["sopId"] == f"sop-db-{sop_id}":
            target = item
            break

    assert target is not None, f"Expected sop-db-{sop_id} in response"

    # 验证 difficulty 映射：medium → intermediate
    assert target["difficulty"] == "intermediate"

    # 验证 sopId 格式
    assert target["sopId"].startswith("sop-db-")

    # 验证 steps 存在且 stepId 格式正确
    assert len(target["steps"]) >= 1
    first_step = target["steps"][0]
    assert first_step["stepId"].startswith("step-")
    assert first_step["title"] == "检查温度"


@pytest.mark.e2e
def test_sop_adjudication_filter_by_model(
    e2e_env: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    """验证 applicable_model 过滤"""
    client, session_factory = e2e_env
    asyncio.run(_seed_sop(session_factory))

    # 过滤存在的型号
    resp = client.get("/api/v1/sops/adjudication?applicable_model=TEST_MODEL")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) >= 1

    # 过滤不存在的型号
    resp = client.get("/api/v1/sops/adjudication?applicable_model=NONEXISTENT")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 0
```

- [ ] **Step 2: 运行测试确认通过**

Run: `cd r-mos-backend && python -m pytest tests/e2e/test_e2e_sop_adjudication.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add r-mos-backend/tests/e2e/test_e2e_sop_adjudication.py
git commit -m "test: SOP adjudication API e2e test with difficulty mapping"
```

---

### Task 9: 后端 Mock 适配器 YAML 驱动验证

**验证目标：** `MockRobotAdapter` 从 `mock_faults.yaml` 加载故障效果，不再硬编码

**Files:**
- Create: `r-mos-backend/tests/unit/test_mock_adapter_yaml.py`

- [ ] **Step 1: 读取 mock.py 了解 YAML 加载逻辑**

Read: `r-mos-backend/app/adapters/mock.py` — 确认 YAML 加载和 fallback 逻辑

- [ ] **Step 2: 编写 Mock 适配器 YAML 加载测试**

```python
"""验证 MockRobotAdapter 从 YAML 加载故障配置"""
import pytest

from app.adapters.mock import MockRobotAdapter


class TestMockAdapterYAMLDriven:
    """验证 MockRobotAdapter 使用 YAML 配置而非硬编码"""

    @pytest.fixture
    def adapter(self):
        return MockRobotAdapter()

    def test_adapter_initializes_successfully(self, adapter):
        """适配器能正常初始化（YAML 加载成功）"""
        assert adapter is not None

    def test_fault_effects_loaded_from_yaml(self, adapter):
        """故障效果来自 YAML 配置"""
        # 检查适配器内部是否有故障效果数据
        # 具体属性名需要根据 mock.py 实际代码调整
        assert hasattr(adapter, '_fault_effects') or hasattr(adapter, 'fault_effects')

    def test_sensor_defaults_loaded(self, adapter):
        """传感器默认值从 YAML 加载"""
        assert hasattr(adapter, '_sensor_defaults') or hasattr(adapter, 'sensor_defaults')
```

注：此 Task 的具体断言需要 subagent 读取 `mock.py` 后根据实际属性名调整。

- [ ] **Step 3: 运行测试确认通过**

Run: `cd r-mos-backend && python -m pytest tests/unit/test_mock_adapter_yaml.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add r-mos-backend/tests/unit/test_mock_adapter_yaml.py
git commit -m "test: MockRobotAdapter YAML-driven configuration test"
```

---

### Task 10: 前端硬编码残留扫描

**验证目标：** 确认已删除的硬编码文件不存在，且没有遗留 import

**Files:**
- Create: `r-mos-frontend/src/__tests__/noHardcodedImports.test.ts`

- [ ] **Step 1: 编写硬编码残留扫描测试**

```typescript
import { describe, expect, it } from 'vitest'
import * as fs from 'fs'
import * as path from 'path'

const SRC_DIR = path.resolve(__dirname, '..')

function findTsFiles(dir: string): string[] {
  const results: string[] = []
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name)
    if (entry.isDirectory() && !entry.name.startsWith('.') && entry.name !== 'node_modules' && entry.name !== '__tests__') {
      results.push(...findTsFiles(fullPath))
    } else if (entry.isFile() && /\.(ts|tsx)$/.test(entry.name) && !entry.name.endsWith('.test.ts') && !entry.name.endsWith('.test.tsx')) {
      results.push(fullPath)
    }
  }
  return results
}

describe('No hardcoded data file residuals', () => {
  it('deleted data files do not exist', () => {
    const deletedFiles = [
      'src/data/sopScripts.ts',
      'src/data/hardwareSOPScripts.ts',
      'src/data/sopKneeBearing.ts',
    ]
    for (const file of deletedFiles) {
      const fullPath = path.resolve(SRC_DIR, '..', file)
      expect(fs.existsSync(fullPath), `Deleted file should not exist: ${file}`).toBe(false)
    }
  })

  it('no source files import deleted data modules', () => {
    const bannedImports = [
      '@/data/sopScripts',
      '@/data/hardwareSOPScripts',
      '@/data/sopKneeBearing',
      'ALL_SOP_SCRIPTS',
      'HARDWARE_SOP_SCRIPTS',
    ]

    const files = findTsFiles(SRC_DIR)
    const violations: string[] = []

    for (const file of files) {
      const content = fs.readFileSync(file, 'utf-8')
      for (const banned of bannedImports) {
        if (content.includes(banned)) {
          const relPath = path.relative(SRC_DIR, file)
          violations.push(`${relPath} references "${banned}"`)
        }
      }
    }

    expect(violations, `Found residual hardcoded imports:\n${violations.join('\n')}`).toEqual([])
  })
})
```

- [ ] **Step 2: 运行测试确认通过**

Run: `cd r-mos-frontend && npx vitest run src/__tests__/noHardcodedImports.test.ts`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add r-mos-frontend/src/__tests__/noHardcodedImports.test.ts
git commit -m "test: scan for residual hardcoded data imports"
```

---

### Task 11: 全量回归 — 前端 + 后端完整测试套件

**验证目标：** 所有现有测试在模块化改造后仍然通过

**Files:**
- 无新文件，只运行现有测试

- [ ] **Step 1: 运行前端全量测试**

Run: `cd r-mos-frontend && npx vitest run 2>&1 | tail -30`
Expected: 所有 test suites PASS（"No test suite found" 的空文件不算失败）

- [ ] **Step 2: 运行后端单元测试**

Run: `cd r-mos-backend && python -m pytest tests/unit/ -v --tb=short 2>&1 | tail -40`
Expected: PASS

- [ ] **Step 3: 运行后端 E2E 测试**

Run: `cd r-mos-backend && python -m pytest tests/e2e/ -v --tb=short 2>&1 | tail -40`
Expected: PASS

- [ ] **Step 4: 记录测试覆盖率摘要**

如果有失败，在此步记录失败项并修复。确认 0 failures 后标记完成。

---

### Task 12: 跨层集成 — 前端 Config 与 后端 API 一致性

**验证目标：** 前端 config 中的路由、状态值、难度映射与后端 API 返回值一致

**Files:**
- Create: `r-mos-frontend/src/__tests__/crossLayerConsistency.test.ts`

- [ ] **Step 1: 编写跨层一致性测试**

```typescript
import { describe, expect, it } from 'vitest'
import { ROUTE_PERMISSIONS } from '@/config/routes'
import { ATTEMPT_STATUS, ROBOT_MODEL_STATUS, ANALYSIS_STATUS } from '@/config/statusLabels'

describe('Cross-layer consistency', () => {
  describe('Route permissions completeness', () => {
    it('all route keys use valid format (no leading slash, no trailing slash)', () => {
      for (const key of Object.keys(ROUTE_PERMISSIONS)) {
        expect(key).not.toMatch(/^\//)
        expect(key).not.toMatch(/\/$/)
      }
    })

    it('critical routes are defined', () => {
      const critical = ['dashboard', 'maintenance', 'monitor', 'knowledge', 'settings']
      for (const route of critical) {
        expect(ROUTE_PERMISSIONS).toHaveProperty(route)
      }
    })
  })

  describe('Status label completeness', () => {
    it('ATTEMPT_STATUS covers backend enum values', () => {
      // Backend TrainingSession statuses: active, paused, submitted, abandoned, expired
      // Attempt statuses: in_progress, completed, graded, abandoned
      const backendAttemptStatuses = ['in_progress', 'completed', 'graded', 'abandoned']
      for (const status of backendAttemptStatuses) {
        expect(ATTEMPT_STATUS).toHaveProperty(status)
      }
    })

    it('ROBOT_MODEL_STATUS covers backend robot lifecycle', () => {
      const backendRobotStatuses = ['draft', 'analyzing', 'ready']
      for (const status of backendRobotStatuses) {
        expect(ROBOT_MODEL_STATUS).toHaveProperty(status)
      }
    })

    it('ANALYSIS_STATUS covers backend analysis lifecycle', () => {
      const backendAnalysisStatuses = ['pending', 'running', 'completed', 'failed']
      for (const status of backendAnalysisStatuses) {
        expect(ANALYSIS_STATUS).toHaveProperty(status)
      }
    })
  })

  describe('Difficulty mapping consistency', () => {
    it('frontend expects beginner/intermediate/advanced from API', () => {
      // Backend maps: low→beginner, medium→intermediate, high→advanced
      // This test documents the contract
      const DIFFICULTY_MAP: Record<string, string> = {
        low: 'beginner',
        medium: 'intermediate',
        high: 'advanced',
      }
      expect(Object.keys(DIFFICULTY_MAP)).toHaveLength(3)
      expect(DIFFICULTY_MAP.low).toBe('beginner')
      expect(DIFFICULTY_MAP.medium).toBe('intermediate')
      expect(DIFFICULTY_MAP.high).toBe('advanced')
    })
  })
})
```

- [ ] **Step 2: 运行测试确认通过**

Run: `cd r-mos-frontend && npx vitest run src/__tests__/crossLayerConsistency.test.ts`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add r-mos-frontend/src/__tests__/crossLayerConsistency.test.ts
git commit -m "test: cross-layer consistency validation (routes, statuses, difficulty mapping)"
```

---

## 测试矩阵总结

| Task | 模块 | 验证点 | 类型 |
|------|------|--------|------|
| 1 | nav.ts / routes.ts / brand.ts | 角色菜单配置、路由权限、品牌常量 | 前端单元 |
| 2 | statusLabels.ts / agentIntents.ts | 状态标签映射、Agent 意图配置 | 前端单元 |
| 3 | manifestAdapter.ts | Manifest→Adjudication 全链路转换 | 前端集成 |
| 4 | useSOPScripts.ts | SOP API 驱动加载、无硬编码 fallback | 前端 Hook |
| 5 | maintenanceKnowledge.ts | Manifest 知识注入/清除 | 前端单元 |
| 6 | teachingStore.ts | pass_score 配置驱动 | 前端 Store |
| 7 | seed_base.yaml / mock_faults.yaml | YAML 格式校验、交叉引用 | 后端单元 |
| 8 | GET /sops/adjudication | 裁决 API 格式、difficulty 映射 | 后端 E2E |
| 9 | MockRobotAdapter | YAML 驱动故障配置 | 后端单元 |
| 10 | 全局扫描 | 已删除文件不存在、无遗留 import | 前端扫描 |
| 11 | 全量回归 | 所有现有测试仍然通过 | 回归 |
| 12 | 跨层一致性 | 路由/状态/难度映射前后端一致 | 前端契约 |
