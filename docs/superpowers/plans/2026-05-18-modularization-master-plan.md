# R-MOS 全面模块化改造 — 总控计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 R-MOS 中 1800+ 处硬编码全部迁移为数据驱动/配置驱动，使每个功能模块可以独立扩展（新机器人、新 SOP、新工具、新角色）。

**Architecture:** 分 4 个 Phase 渐进实施。Phase 1 扩展 assembly_manifest.json 为"超级清单"，涵盖零件注册表、螺丝、约束、相机预设等所有机器人特定数据；Phase 2 将 SOP 裁决脚本从前端硬编码迁移到后端数据库；Phase 3 将菜单/路由/UI 配置化；Phase 4 后端配置外部化。每个 Phase 独立可交付、可测试。

**Tech Stack:** React 18 + TypeScript + Zustand / FastAPI + SQLAlchemy 2.0 + Pydantic 2.x / PostgreSQL

---

## 总览

| Phase | 名称 | 核心目标 | 预估 Tasks | 依赖 | 状态 |
|-------|------|---------|-----------|------|------|
| 1 | 机器人数据清单化 | ATOM-01 硬编码 → manifest JSON + API | 12 | 无 | ✅ Done |
| 2 | SOP 裁决脚本数据库化 | 前端 SOP 脚本 → 后端 DB + API | 10 | Phase 1 | ✅ Done |
| 3 | 前端配置驱动化 | 菜单/路由/UI → 配置对象 | 6 | 无 | ✅ Done |
| 4 | 后端配置外部化 | 密钥/CORS/Seed → .env + 参数化 | 5 | 无 | ✅ Done |

**关键路径：** Phase 1 → Phase 2（SOP 步骤需引用 manifest 中的零件 ID）
**可并行：** Phase 3、Phase 4 与 Phase 1/2 无依赖

---

## Phase 1: 机器人数据清单化（P0 — 阻塞多机器人扩展）

### 1.1 架构设计

**核心思路：** 扩展现有 `assembly_manifest.json` 为 **Robot Data Manifest**，将所有机器人特定数据统一为一个 JSON 文件，由后端 URDF 解析管线生成，前端通过 API 加载。

**当前状态：**
```
assembly_manifest.json
├── version, robotId, rootNodeId
├── nodes: AssemblyNode[]          ← 已有：装配树节点
├── mesh_catalog: Record<string, string>  ← 已有：GLB 路径
└── joints: AssemblyJoint[]        ← 已有：关节定义
```

**目标状态：**
```
assembly_manifest.json（扩展）
├── version, robotId, rootNodeId
├── nodes: AssemblyNode[]          ← 保持不变
├── mesh_catalog                   ← 保持不变
├── joints                         ← 保持不变
├── parts_registry: PartEntry[]    ← 新增：零件注册表（BOM、分类、显示名）
├── screw_instances: ScrewEntry[]  ← 新增：螺丝实例（位置、规格、扭矩）
├── constraints: ConstraintEntry[] ← 新增：结构约束（紧固、覆盖、阻挡）
├── camera_presets: CameraPresetMap ← 新增：各级相机预设
├── explode_config: ExplodeConfig  ← 新增：爆炸视图偏移
├── tools: ToolEntry[]             ← 新增：工具清单
├── display_names: Record<string, string> ← 新增：节点显示名映射
└── overview_config: OverviewConfig ← 新增：概览节点 + 装配组
```

### 1.2 文件结构

**后端（生成 manifest）：**
```
r-mos-backend/app/services/analysis/
├── assembly_builder.py          ← 修改：扩展 manifest 生成，添加新字段
├── urdf_parser.py               ← 修改：提取更多元数据
└── manifest_schema.py           ← 新建：manifest JSON schema 验证
```

**前端（消费 manifest）：**
```
r-mos-frontend/src/components/Viewer3D/
├── assemblyManifest.ts          ← 修改：扩展类型定义
├── useAssemblyManifest.ts       ← 修改：缓存策略优化
└── useRobotDataManifest.ts      ← 新建：统一加载 hook（包含零件/螺丝/约束）

r-mos-frontend/src/adjudication/
├── data/
│   ├── partRegistry.ts          ← 重构：从 manifest 读取，保留 API 不变
│   ├── screwInstances.ts        ← 重构：从 manifest 读取
│   ├── constraintGraph.ts       ← 重构：从 manifest 读取
│   └── manifestAdapter.ts       ← 新建：manifest → adjudication 类型适配器

r-mos-frontend/src/components/Viewer3D/
├── assemblyTree.ts              ← 重构：从 manifest 派生装配组和相机预设
├── partsManifest.ts             ← 重构：从 manifest 读取零件清单
├── disassemblyConfig.ts         ← 重构：从 manifest 读取拆卸序列
├── Atom01Interactive.tsx        ← 重构：移除硬编码元数据，从 manifest 读取
└── constants.ts                 ← 重构：移除硬编码关节/尺寸/材质

r-mos-frontend/src/hooks/
└── useCameraFocus.ts            ← 重构：从 manifest 相机预设读取焦点位置

r-mos-frontend/src/pages/
├── MonitorPage.tsx              ← 重构：关节映射从 manifest 读取
└── SOPMaintenancePage.tsx       ← 重构：Link 分组从 manifest 读取
```

### 1.3 Tasks

---

### Task 1: 扩展 AssemblyManifest 类型定义

**Files:**
- Modify: `r-mos-frontend/src/components/Viewer3D/assemblyManifest.ts`
- Test: `r-mos-frontend/src/components/Viewer3D/__tests__/assemblyManifest.test.ts`

- [ ] **Step 1: 在 assemblyManifest.ts 中添加新类型定义**

在现有类型之后追加：

```typescript
// ---- Robot Data Manifest 扩展类型 ----

export interface ManifestPartEntry {
  id: string
  category: string              // 'frame' | 'cover' | 'screw' | 'motor' | 'pcb' | ...
  bom_code: string              // 'ATOM-01-BASE-001'
  display_name: string          // '髋部底座'
  parent_id: string | null
  mesh_id: string | null        // 引用 mesh_catalog
  local_position: Vec3
  local_rotation: Vec3           // euler angles
  group: string | null          // 'base' | 'torso' | 'left_arm' | ...
}

export interface ManifestScrewEntry {
  id: string
  bom_code: string
  parent_id: string             // 所属零件 ID
  position: Vec3
  axis: Vec3
  spec: {
    type: string                // 'M4×10'
    pitch: number
    thread_length: number
    required_tool: string       // 'hex_3'
    torque_nm: number
  }
}

export interface ManifestConstraintEntry {
  id: string
  type: 'fastened_by' | 'covered_by' | 'blocked_by'
  constrained_part: string
  constraining_part: string
  params: Record<string, unknown>
  release_condition: {
    type: string
    required_actions: string[]
  }
}

export interface ManifestCameraPreset {
  position: Vec3
  target: Vec3
  fov: number
}

export interface ManifestExplodeOffset {
  node_id: string
  direction: Vec3
  distance: number
}

export interface ManifestToolEntry {
  id: string
  name: string
  type: string                  // 'hex_key' | 'torque_wrench' | 'pliers'
  size: string
  description: string
}

export interface ManifestOverviewConfig {
  overview_nodes: string[]
  reference_set: string[]
  assembly_groups: Record<string, {
    display_name: string
    child_links: string[]
    explode_dir: Vec3
  }>
}

/** 完整的机器人数据清单 — 扩展 AssemblyManifest */
export interface RobotDataManifest extends AssemblyManifest {
  parts_registry?: ManifestPartEntry[]
  screw_instances?: ManifestScrewEntry[]
  constraints?: ManifestConstraintEntry[]
  camera_presets?: Record<string, ManifestCameraPreset>
  explode_offsets?: ManifestExplodeOffset[]
  tools?: ManifestToolEntry[]
  display_names?: Record<string, string>
  overview_config?: ManifestOverviewConfig
}
```

- [ ] **Step 2: 添加解析函数**

在 `assemblyManifest.ts` 中添加：

```typescript
export function parseRobotDataManifest(raw: unknown): RobotDataManifest {
  const base = parseAssemblyManifest(raw)
  const obj = raw as Record<string, unknown>
  return {
    ...base,
    parts_registry: (obj.parts_registry as ManifestPartEntry[]) ?? [],
    screw_instances: (obj.screw_instances as ManifestScrewEntry[]) ?? [],
    constraints: (obj.constraints as ManifestConstraintEntry[]) ?? [],
    camera_presets: (obj.camera_presets as Record<string, ManifestCameraPreset>) ?? {},
    explode_offsets: (obj.explode_offsets as ManifestExplodeOffset[]) ?? [],
    tools: (obj.tools as ManifestToolEntry[]) ?? [],
    display_names: (obj.display_names as Record<string, string>) ?? {},
    overview_config: (obj.overview_config as ManifestOverviewConfig) ?? undefined,
  }
}
```

- [ ] **Step 3: 写测试**

```typescript
// assemblyManifest.test.ts - 追加
describe('parseRobotDataManifest', () => {
  it('parses extended manifest with parts_registry', () => {
    const raw = {
      version: '2026-05-18', robotId: 'test', rootNodeId: 'root',
      nodes: [{ id: 'root', parent_id: null, children: [], mesh_id: null, display_name: 'Root', category: 'frame', link_name: null, transform: { translation: [0,0,0], rotation_quat: [0,0,0,1], scale: [1,1,1] } }],
      mesh_catalog: {}, fastener_instances: [],
      parts_registry: [{ id: 'base', category: 'frame', bom_code: 'TEST-BASE-001', display_name: 'Base', parent_id: null, mesh_id: null, local_position: [0,0,0], local_rotation: [0,0,0], group: 'base' }],
    }
    const result = parseRobotDataManifest(raw)
    expect(result.parts_registry).toHaveLength(1)
    expect(result.parts_registry![0].bom_code).toBe('TEST-BASE-001')
  })

  it('provides empty defaults for missing extended fields', () => {
    const raw = {
      version: '2026-05-18', robotId: 'test', rootNodeId: 'root',
      nodes: [{ id: 'root', parent_id: null, children: [], mesh_id: null, display_name: 'Root', category: 'frame', link_name: null, transform: { translation: [0,0,0], rotation_quat: [0,0,0,1], scale: [1,1,1] } }],
      mesh_catalog: {}, fastener_instances: [],
    }
    const result = parseRobotDataManifest(raw)
    expect(result.parts_registry).toEqual([])
    expect(result.screw_instances).toEqual([])
    expect(result.constraints).toEqual([])
    expect(result.tools).toEqual([])
  })
})
```

- [ ] **Step 4: 运行测试**

Run: `cd r-mos-frontend && npx vitest run src/components/Viewer3D/__tests__/assemblyManifest.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add r-mos-frontend/src/components/Viewer3D/assemblyManifest.ts r-mos-frontend/src/components/Viewer3D/__tests__/assemblyManifest.test.ts
git commit -m "feat(manifest): extend AssemblyManifest with parts_registry, screws, constraints, camera presets"
```

---

### Task 2: 创建 Manifest 适配器（manifest → adjudication 类型转换）

**Files:**
- Create: `r-mos-frontend/src/adjudication/data/manifestAdapter.ts`
- Test: `r-mos-frontend/src/adjudication/data/__tests__/manifestAdapter.test.ts`

- [ ] **Step 1: 创建适配器模块**

```typescript
// manifestAdapter.ts
import type {
  RobotDataManifest,
  ManifestPartEntry,
  ManifestScrewEntry,
  ManifestConstraintEntry,
} from '@/components/Viewer3D/assemblyManifest'
import type {
  Part,
  Constraint,
  ConstraintType,
  ScrewSpec,
} from '../types/adjudication'
import { PartCategory } from '../types/adjudication'

const CATEGORY_MAP: Record<string, PartCategory> = {
  frame: PartCategory.FRAME,
  cover: PartCategory.COVER,
  screw: PartCategory.SCREW,
  nut: PartCategory.NUT,
  motor: PartCategory.MOTOR,
  bearing: PartCategory.BEARING,
  pcb: PartCategory.PCB,
  wire: PartCategory.WIRE,
  tool: PartCategory.TOOL,
}

export function manifestPartToPart(entry: ManifestPartEntry, modelBase: string): Part {
  return {
    id: entry.id,
    category: CATEGORY_MAP[entry.category] ?? PartCategory.FRAME,
    bomCode: entry.bom_code,
    displayName: entry.display_name,
    modelPath: entry.mesh_id ? `${modelBase}/${entry.mesh_id}` : '',
    parentId: entry.parent_id ?? undefined,
    localPosition: entry.local_position,
    localRotation: entry.local_rotation,
  }
}

export function manifestScrewToPart(entry: ManifestScrewEntry, modelBase: string): Part {
  const screwSpec: ScrewSpec = {
    type: entry.spec.type,
    pitch: entry.spec.pitch,
    threadLength: entry.spec.thread_length,
    requiredTool: entry.spec.required_tool,
    torque: entry.spec.torque_nm,
  }
  return {
    id: entry.id,
    category: PartCategory.SCREW,
    bomCode: entry.bom_code,
    displayName: entry.spec.type,
    modelPath: '',
    parentId: entry.parent_id,
    localPosition: entry.position,
    localRotation: [0, 0, 0],
    screwSpec,
  }
}

export function manifestConstraintToConstraint(entry: ManifestConstraintEntry): Constraint {
  return {
    id: entry.id,
    type: entry.type as ConstraintType,
    constrainedPart: entry.constrained_part,
    constrainingPart: entry.constraining_part,
    params: entry.params as any,
    releaseCondition: {
      type: entry.release_condition.type as any,
      requiredActions: entry.release_condition.required_actions,
    },
    isActive: true,
  }
}

/** 从 RobotDataManifest 构建完整的 adjudication 数据集 */
export function buildAdjudicationDataFromManifest(manifest: RobotDataManifest) {
  const modelBase = `/api/v1/robots/${manifest.robotId}/assets`

  const partRegistry: Record<string, Part> = {}
  for (const entry of manifest.parts_registry ?? []) {
    partRegistry[entry.id] = manifestPartToPart(entry, modelBase)
  }

  const screwRegistry: Record<string, Part> = {}
  for (const entry of manifest.screw_instances ?? []) {
    screwRegistry[entry.id] = manifestScrewToPart(entry, modelBase)
  }

  const constraints: Constraint[] = (manifest.constraints ?? []).map(manifestConstraintToConstraint)

  return { partRegistry, screwRegistry, constraints }
}
```

- [ ] **Step 2: 写测试**

```typescript
// manifestAdapter.test.ts
import { describe, it, expect } from 'vitest'
import { manifestPartToPart, manifestScrewToPart, buildAdjudicationDataFromManifest } from '../manifestAdapter'
import { PartCategory } from '../../types/adjudication'
import type { ManifestPartEntry, ManifestScrewEntry, RobotDataManifest } from '@/components/Viewer3D/assemblyManifest'

describe('manifestPartToPart', () => {
  it('converts manifest part entry to adjudication Part', () => {
    const entry: ManifestPartEntry = {
      id: 'base_link', category: 'frame', bom_code: 'ATOM-01-BASE-001',
      display_name: '髋部底座', parent_id: null, mesh_id: 'base_link.glb',
      local_position: [0, 0, 0], local_rotation: [0, 0, 0], group: 'base',
    }
    const result = manifestPartToPart(entry, '/api/v1/robots/1/assets')
    expect(result.id).toBe('base_link')
    expect(result.category).toBe(PartCategory.FRAME)
    expect(result.bomCode).toBe('ATOM-01-BASE-001')
    expect(result.displayName).toBe('髋部底座')
  })
})

describe('manifestScrewToPart', () => {
  it('converts manifest screw to Part with screwSpec', () => {
    const entry: ManifestScrewEntry = {
      id: 'screw_foot_m4x10_001', bom_code: 'ATOM-01-SCREW-M4X10',
      parent_id: 'left_ankle_roll_link', position: [0.02, 0.01, -0.03],
      axis: [0, 0, -1],
      spec: { type: 'M4×10', pitch: 0.7, thread_length: 10, required_tool: 'hex_3', torque_nm: 2.5 },
    }
    const result = manifestScrewToPart(entry, '/models')
    expect(result.category).toBe(PartCategory.SCREW)
    expect(result.screwSpec?.type).toBe('M4×10')
    expect(result.screwSpec?.torque).toBe(2.5)
  })
})

describe('buildAdjudicationDataFromManifest', () => {
  it('builds complete adjudication dataset from manifest', () => {
    const manifest = {
      version: 'test', robotId: '1', rootNodeId: 'root',
      nodes: [], mesh_catalog: {}, fastener_instances: [],
      parts_registry: [
        { id: 'base', category: 'frame', bom_code: 'B-001', display_name: 'Base', parent_id: null, mesh_id: null, local_position: [0,0,0], local_rotation: [0,0,0], group: 'base' },
      ],
      screw_instances: [
        { id: 's1', bom_code: 'S-001', parent_id: 'base', position: [0,0,0], axis: [0,0,1], spec: { type: 'M3×6', pitch: 0.5, thread_length: 6, required_tool: 'hex_2.5', torque_nm: 1.5 } },
      ],
      constraints: [
        { id: 'c1', type: 'fastened_by', constrained_part: 'cover', constraining_part: 'base', params: { screwIds: ['s1'] }, release_condition: { type: 'all_screws_removed', required_actions: ['s1'] } },
      ],
    } as unknown as RobotDataManifest

    const result = buildAdjudicationDataFromManifest(manifest)
    expect(Object.keys(result.partRegistry)).toHaveLength(1)
    expect(Object.keys(result.screwRegistry)).toHaveLength(1)
    expect(result.constraints).toHaveLength(1)
  })
})
```

- [ ] **Step 3: 运行测试**

Run: `cd r-mos-frontend && npx vitest run src/adjudication/data/__tests__/manifestAdapter.test.ts`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add r-mos-frontend/src/adjudication/data/manifestAdapter.ts r-mos-frontend/src/adjudication/data/__tests__/manifestAdapter.test.ts
git commit -m "feat(adjudication): add manifest adapter to convert RobotDataManifest to adjudication types"
```

---

### Task 3: 创建统一 Robot Data Hook

**Files:**
- Create: `r-mos-frontend/src/components/Viewer3D/useRobotDataManifest.ts`
- Test: `r-mos-frontend/src/components/Viewer3D/__tests__/useRobotDataManifest.test.ts`

- [ ] **Step 1: 创建 hook**

```typescript
// useRobotDataManifest.ts
import { useEffect, useState, useMemo } from 'react'
import { apiClient } from '@/api/client'
import type { RobotDataManifest, ManifestCameraPreset } from './assemblyManifest'
import { parseRobotDataManifest } from './assemblyManifest'
import { buildAdjudicationDataFromManifest } from '@/adjudication/data/manifestAdapter'
import type { Part, Constraint } from '@/adjudication/types/adjudication'

export interface RobotDataResult {
  manifest: RobotDataManifest | null
  loading: boolean
  error: string | null
  hasManifest: boolean
  // 便捷访问器
  displayNames: Record<string, string>
  cameraPresets: Record<string, ManifestCameraPreset>
  partRegistry: Record<string, Part>
  screwRegistry: Record<string, Part>
  constraints: Constraint[]
  overviewNodes: string[]
  assemblyGroups: Record<string, { display_name: string; child_links: string[]; explode_dir: [number, number, number] }>
}

const cache = new Map<number, RobotDataManifest | null>()

export function useRobotDataManifest(robotId: number | undefined): RobotDataResult {
  const [manifest, setManifest] = useState<RobotDataManifest | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!robotId) { setLoading(false); return }
    if (cache.has(robotId)) {
      setManifest(cache.get(robotId)!)
      setLoading(false)
      return
    }

    let cancelled = false
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const url = `/robots/${robotId}/assets/manifests/assembly_manifest.json`
        const res = await apiClient.get(url)
        if (!cancelled) {
          const data = parseRobotDataManifest(res.data)
          cache.set(robotId!, data)
          setManifest(data)
        }
      } catch (e: any) {
        if (!cancelled) {
          if (e.response?.status === 404) {
            cache.set(robotId!, null)
            setManifest(null)
          } else {
            setError(e.message || 'Failed to load robot data manifest')
          }
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [robotId])

  const derived = useMemo(() => {
    if (!manifest) {
      return {
        displayNames: {} as Record<string, string>,
        cameraPresets: {} as Record<string, ManifestCameraPreset>,
        partRegistry: {} as Record<string, Part>,
        screwRegistry: {} as Record<string, Part>,
        constraints: [] as Constraint[],
        overviewNodes: [] as string[],
        assemblyGroups: {} as Record<string, { display_name: string; child_links: string[]; explode_dir: [number, number, number] }>,
      }
    }
    const adjData = buildAdjudicationDataFromManifest(manifest)
    return {
      displayNames: manifest.display_names ?? {},
      cameraPresets: manifest.camera_presets ?? {},
      partRegistry: adjData.partRegistry,
      screwRegistry: adjData.screwRegistry,
      constraints: adjData.constraints,
      overviewNodes: manifest.overview_config?.overview_nodes ?? [],
      assemblyGroups: manifest.overview_config?.assembly_groups ?? {},
    }
  }, [manifest])

  return {
    manifest,
    loading,
    error,
    hasManifest: manifest !== null,
    ...derived,
  }
}

/** 清除缓存（供测试用） */
export function clearRobotDataCache() {
  cache.clear()
}
```

- [ ] **Step 2: 运行类型检查**

Run: `cd r-mos-frontend && npx tsc --noEmit 2>&1 | grep -i "useRobotDataManifest"`
Expected: No errors related to this file

- [ ] **Step 3: Commit**

```bash
git add r-mos-frontend/src/components/Viewer3D/useRobotDataManifest.ts
git commit -m "feat(viewer): add useRobotDataManifest hook with derived adjudication data"
```

---

### Task 4: 后端 — 为 ATOM-01 生成扩展 manifest

**Files:**
- Modify: `r-mos-backend/app/services/analysis/assembly_builder.py`
- Create: `r-mos-backend/scripts/generate_atom01_extended_manifest.py`

- [ ] **Step 1: 创建 ATOM-01 扩展 manifest 生成脚本**

从现有前端硬编码数据提取，生成 `assembly_manifest.json` 的扩展字段。这是一个一次性迁移脚本，将 `partRegistry.ts`、`screwInstances.ts`、`constraintGraph.ts`、`assemblyTree.ts`、`useCameraFocus.ts` 中的硬编码数据导出为 JSON。

```python
#!/usr/bin/env python3
"""
从前端硬编码数据生成 ATOM-01 的扩展 manifest 字段。
运行方式：python scripts/generate_atom01_extended_manifest.py
输出：data/robot-assets/{robot_id}/manifests/assembly_manifest.json（追加字段）
"""
import json
import sys
from pathlib import Path

def build_atom01_parts_registry():
    """硬编码数据迁移 — 来自 partRegistry.ts"""
    return [
        {"id": "base_link", "category": "frame", "bom_code": "ATOM-01-BASE-001", "display_name": "髋部底座", "parent_id": None, "mesh_id": "base_link.glb", "local_position": [0,0,0], "local_rotation": [0,0,0], "group": "base"},
        {"id": "torso_link", "category": "frame", "bom_code": "ATOM-01-TORSO-001", "display_name": "躯干", "parent_id": "base_link", "mesh_id": "torso_link.glb", "local_position": [0,0,0.35], "local_rotation": [0,0,0], "group": "torso"},
        {"id": "torso_chest_cover", "category": "cover", "bom_code": "ATOM-01-TORSO-CHEST-001", "display_name": "胸腔前盖", "parent_id": "torso_link", "mesh_id": None, "local_position": [0.05,0,0.15], "local_rotation": [0,0,0], "group": "torso"},
        {"id": "torso_motor", "category": "motor", "bom_code": "ATOM-01-TORSO-MOTOR-001", "display_name": "躯干电机", "parent_id": "torso_link", "mesh_id": None, "local_position": [0,0,0.1], "local_rotation": [0,0,0], "group": "torso"},
        {"id": "left_arm_pitch_link", "category": "frame", "bom_code": "ATOM-01-LARM-001", "display_name": "左肩俯仰", "parent_id": "torso_link", "mesh_id": "left_arm_pitch_link.glb", "local_position": [0.15,0,0.3], "local_rotation": [0,0,0], "group": "left_arm"},
        {"id": "left_arm_roll_link", "category": "frame", "bom_code": "ATOM-01-LARM-002", "display_name": "左肩横滚", "parent_id": "left_arm_pitch_link", "mesh_id": "left_arm_roll_link.glb", "local_position": [0,0,0], "local_rotation": [0,0,0], "group": "left_arm"},
        {"id": "left_arm_yaw_link", "category": "frame", "bom_code": "ATOM-01-LARM-003", "display_name": "左肩偏航", "parent_id": "left_arm_roll_link", "mesh_id": "left_arm_yaw_link.glb", "local_position": [0,0,0], "local_rotation": [0,0,0], "group": "left_arm"},
        {"id": "left_elbow_pitch_link", "category": "frame", "bom_code": "ATOM-01-LARM-004", "display_name": "左肘俯仰", "parent_id": "left_arm_yaw_link", "mesh_id": "left_elbow_pitch_link.glb", "local_position": [0,0,-0.2], "local_rotation": [0,0,0], "group": "left_arm"},
        {"id": "left_elbow_yaw_link", "category": "frame", "bom_code": "ATOM-01-LARM-005", "display_name": "左肘偏航", "parent_id": "left_elbow_pitch_link", "mesh_id": "left_elbow_yaw_link.glb", "local_position": [0,0,0], "local_rotation": [0,0,0], "group": "left_arm"},
        # 右臂（镜像左臂）
        {"id": "right_arm_pitch_link", "category": "frame", "bom_code": "ATOM-01-RARM-001", "display_name": "右肩俯仰", "parent_id": "torso_link", "mesh_id": "right_arm_pitch_link.glb", "local_position": [-0.15,0,0.3], "local_rotation": [0,0,0], "group": "right_arm"},
        {"id": "right_arm_roll_link", "category": "frame", "bom_code": "ATOM-01-RARM-002", "display_name": "右肩横滚", "parent_id": "right_arm_pitch_link", "mesh_id": "right_arm_roll_link.glb", "local_position": [0,0,0], "local_rotation": [0,0,0], "group": "right_arm"},
        {"id": "right_arm_yaw_link", "category": "frame", "bom_code": "ATOM-01-RARM-003", "display_name": "右肩偏航", "parent_id": "right_arm_roll_link", "mesh_id": "right_arm_yaw_link.glb", "local_position": [0,0,0], "local_rotation": [0,0,0], "group": "right_arm"},
        {"id": "right_elbow_pitch_link", "category": "frame", "bom_code": "ATOM-01-RARM-004", "display_name": "右肘俯仰", "parent_id": "right_arm_yaw_link", "mesh_id": "right_elbow_pitch_link.glb", "local_position": [0,0,-0.2], "local_rotation": [0,0,0], "group": "right_arm"},
        {"id": "right_elbow_yaw_link", "category": "frame", "bom_code": "ATOM-01-RARM-005", "display_name": "右肘偏航", "parent_id": "right_elbow_pitch_link", "mesh_id": "right_elbow_yaw_link.glb", "local_position": [0,0,0], "local_rotation": [0,0,0], "group": "right_arm"},
        # 左腿
        {"id": "left_thigh_yaw_link", "category": "frame", "bom_code": "ATOM-01-LTHIGH-001", "display_name": "左大腿偏航", "parent_id": "base_link", "mesh_id": "left_thigh_yaw_link.glb", "local_position": [0.1,0,-0.05], "local_rotation": [0,0,0], "group": "left_leg"},
        {"id": "left_thigh_roll_link", "category": "frame", "bom_code": "ATOM-01-LTHIGH-002", "display_name": "左大腿横滚", "parent_id": "left_thigh_yaw_link", "mesh_id": "left_thigh_roll_link.glb", "local_position": [0,0,0], "local_rotation": [0,0,0], "group": "left_leg"},
        {"id": "left_thigh_pitch_link", "category": "frame", "bom_code": "ATOM-01-LTHIGH-003", "display_name": "左大腿俯仰", "parent_id": "left_thigh_roll_link", "mesh_id": "left_thigh_pitch_link.glb", "local_position": [0,0,0], "local_rotation": [0,0,0], "group": "left_leg"},
        {"id": "left_knee_link", "category": "frame", "bom_code": "ATOM-01-LKNEE-001", "display_name": "左膝关节", "parent_id": "left_thigh_pitch_link", "mesh_id": "left_knee_link.glb", "local_position": [0,0,-0.3], "local_rotation": [0,0,0], "group": "left_leg"},
        {"id": "left_ankle_pitch_link", "category": "frame", "bom_code": "ATOM-01-LANKLE-001", "display_name": "左踝俯仰", "parent_id": "left_knee_link", "mesh_id": "left_ankle_pitch_link.glb", "local_position": [0,0,-0.3], "local_rotation": [0,0,0], "group": "left_leg"},
        {"id": "left_ankle_roll_link", "category": "frame", "bom_code": "ATOM-01-LANKLE-002", "display_name": "左踝横滚", "parent_id": "left_ankle_pitch_link", "mesh_id": "left_ankle_roll_link.glb", "local_position": [0,0,0], "local_rotation": [0,0,0], "group": "left_leg"},
        # 右腿（镜像左腿）
        {"id": "right_thigh_yaw_link", "category": "frame", "bom_code": "ATOM-01-RTHIGH-001", "display_name": "右大腿偏航", "parent_id": "base_link", "mesh_id": "right_thigh_yaw_link.glb", "local_position": [-0.1,0,-0.05], "local_rotation": [0,0,0], "group": "right_leg"},
        {"id": "right_thigh_roll_link", "category": "frame", "bom_code": "ATOM-01-RTHIGH-002", "display_name": "右大腿横滚", "parent_id": "right_thigh_yaw_link", "mesh_id": "right_thigh_roll_link.glb", "local_position": [0,0,0], "local_rotation": [0,0,0], "group": "right_leg"},
        {"id": "right_thigh_pitch_link", "category": "frame", "bom_code": "ATOM-01-RTHIGH-003", "display_name": "右大腿俯仰", "parent_id": "right_thigh_roll_link", "mesh_id": "right_thigh_pitch_link.glb", "local_position": [0,0,0], "local_rotation": [0,0,0], "group": "right_leg"},
        {"id": "right_knee_link", "category": "frame", "bom_code": "ATOM-01-RKNEE-001", "display_name": "右膝关节", "parent_id": "right_thigh_pitch_link", "mesh_id": "right_knee_link.glb", "local_position": [0,0,-0.3], "local_rotation": [0,0,0], "group": "right_leg"},
        {"id": "right_ankle_pitch_link", "category": "frame", "bom_code": "ATOM-01-RANKLE-001", "display_name": "右踝俯仰", "parent_id": "right_knee_link", "mesh_id": "right_ankle_pitch_link.glb", "local_position": [0,0,-0.3], "local_rotation": [0,0,0], "group": "right_leg"},
        {"id": "right_ankle_roll_link", "category": "frame", "bom_code": "ATOM-01-RANKLE-002", "display_name": "右踝横滚", "parent_id": "right_ankle_pitch_link", "mesh_id": "right_ankle_roll_link.glb", "local_position": [0,0,0], "local_rotation": [0,0,0], "group": "right_leg"},
    ]

def build_atom01_display_names():
    """硬编码数据迁移 — 来自 assemblyTree.ts LINK_DISPLAY_NAMES"""
    return {
        "base_link": "髋部底座", "torso_link": "躯干",
        "left_arm_pitch_link": "左肩俯仰", "left_arm_roll_link": "左肩横滚",
        "left_arm_yaw_link": "左肩偏航", "left_elbow_pitch_link": "左肘俯仰",
        "left_elbow_yaw_link": "左肘偏航",
        "right_arm_pitch_link": "右肩俯仰", "right_arm_roll_link": "右肩横滚",
        "right_arm_yaw_link": "右肩偏航", "right_elbow_pitch_link": "右肘俯仰",
        "right_elbow_yaw_link": "右肘偏航",
        "left_thigh_yaw_link": "左大腿偏航", "left_thigh_roll_link": "左大腿横滚",
        "left_thigh_pitch_link": "左大腿俯仰", "left_knee_link": "左膝关节",
        "left_ankle_pitch_link": "左踝俯仰", "left_ankle_roll_link": "左踝横滚",
        "right_thigh_yaw_link": "右大腿偏航", "right_thigh_roll_link": "右大腿横滚",
        "right_thigh_pitch_link": "右大腿俯仰", "right_knee_link": "右膝关节",
        "right_ankle_pitch_link": "右踝俯仰", "right_ankle_roll_link": "右踝横滚",
    }

def build_atom01_camera_presets():
    """硬编码数据迁移 — 来自 useCameraFocus.ts + assemblyTree.ts"""
    return {
        "L0_overview": {"position": [1.5, 1.0, 1.5], "target": [0.0, 0.3, 0.0], "fov": 45},
        "base_link": {"position": [0.6, 0.2, 0.6], "target": [0.0, 0.0, 0.0], "fov": 40},
        "torso_link": {"position": [0.6, 0.5, 0.6], "target": [0.0, 0.35, 0.0], "fov": 40},
        "left_arm_yaw_link": {"position": [0.5, 0.6, 0.3], "target": [0.15, 0.45, 0.0], "fov": 40},
        "right_arm_yaw_link": {"position": [-0.5, 0.6, 0.3], "target": [-0.15, 0.45, 0.0], "fov": 40},
        "left_knee_link": {"position": [0.4, 0.0, 0.4], "target": [0.1, -0.15, 0.0], "fov": 40},
        "right_knee_link": {"position": [-0.4, 0.0, 0.4], "target": [-0.1, -0.15, 0.0], "fov": 40},
    }

def build_atom01_overview_config():
    """硬编码数据迁移 — 来自 overview_nodes.json + assemblyTree.ts"""
    return {
        "overview_nodes": [
            "base_link", "torso_link",
            "left_arm_yaw_link", "left_elbow_yaw_link",
            "right_arm_yaw_link", "right_elbow_yaw_link",
            "left_thigh_pitch_link", "left_knee_link", "left_ankle_roll_link",
            "right_thigh_pitch_link", "right_knee_link", "right_ankle_roll_link",
        ],
        "reference_set": ["base_link", "torso_link"],
        "assembly_groups": {
            "base_link": {"display_name": "髋部底座", "child_links": ["base_link"], "explode_dir": [0, 0, -1]},
            "torso_link": {"display_name": "躯干", "child_links": ["torso_link"], "explode_dir": [0, 0, 1]},
            "left_arm": {"display_name": "左臂", "child_links": ["left_arm_pitch_link", "left_arm_roll_link", "left_arm_yaw_link", "left_elbow_pitch_link", "left_elbow_yaw_link"], "explode_dir": [1, 0, 0]},
            "right_arm": {"display_name": "右臂", "child_links": ["right_arm_pitch_link", "right_arm_roll_link", "right_arm_yaw_link", "right_elbow_pitch_link", "right_elbow_yaw_link"], "explode_dir": [-1, 0, 0]},
            "left_leg": {"display_name": "左腿", "child_links": ["left_thigh_yaw_link", "left_thigh_roll_link", "left_thigh_pitch_link", "left_knee_link", "left_ankle_pitch_link", "left_ankle_roll_link"], "explode_dir": [0.5, 0, -1]},
            "right_leg": {"display_name": "右腿", "child_links": ["right_thigh_yaw_link", "right_thigh_roll_link", "right_thigh_pitch_link", "right_knee_link", "right_ankle_pitch_link", "right_ankle_roll_link"], "explode_dir": [-0.5, 0, -1]},
        },
    }

def build_atom01_tools():
    """硬编码数据迁移 — 来自 toolData.ts"""
    return [
        {"id": "hex_2.5", "name": "2.5mm 内六角扳手", "type": "hex_key", "size": "2.5mm", "description": "用于 M3 螺丝"},
        {"id": "hex_3", "name": "3mm 内六角扳手", "type": "hex_key", "size": "3mm", "description": "用于 M4 螺丝"},
        {"id": "hex_4", "name": "4mm 内六角扳手", "type": "hex_key", "size": "4mm", "description": "用于 M5 螺丝"},
        {"id": "hex_5", "name": "5mm 内六角扳手", "type": "hex_key", "size": "5mm", "description": "用于 M6 螺丝"},
        {"id": "torque_wrench", "name": "扭力扳手", "type": "torque_wrench", "size": "可调", "description": "精确扭矩控制"},
        {"id": "pliers", "name": "尖嘴钳", "type": "pliers", "size": "标准", "description": "用于拔出连接器"},
    ]

def main():
    """读取现有 manifest，追加扩展字段，写回"""
    if len(sys.argv) < 2:
        print("Usage: python generate_atom01_extended_manifest.py <robot_id>")
        sys.exit(1)

    robot_id = sys.argv[1]
    manifest_path = Path(f"data/robot-assets/{robot_id}/manifests/assembly_manifest.json")

    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}")
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    # 追加扩展字段
    manifest["parts_registry"] = build_atom01_parts_registry()
    manifest["display_names"] = build_atom01_display_names()
    manifest["camera_presets"] = build_atom01_camera_presets()
    manifest["overview_config"] = build_atom01_overview_config()
    manifest["tools"] = build_atom01_tools()
    # screw_instances 和 constraints 暂时为空，Phase 1 后续 Task 补充
    manifest.setdefault("screw_instances", [])
    manifest.setdefault("constraints", [])
    manifest.setdefault("explode_offsets", [])

    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"Extended manifest written to {manifest_path}")
    print(f"  parts_registry: {len(manifest['parts_registry'])} entries")
    print(f"  display_names: {len(manifest['display_names'])} entries")
    print(f"  camera_presets: {len(manifest['camera_presets'])} entries")
    print(f"  tools: {len(manifest['tools'])} entries")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行脚本**

Run: `cd r-mos-backend && python scripts/generate_atom01_extended_manifest.py 1`
Expected: 输出 manifest 统计信息

- [ ] **Step 3: 验证 JSON**

Run: `cd r-mos-backend && python -c "import json; d=json.load(open('data/robot-assets/1/manifests/assembly_manifest.json')); print('parts:', len(d.get('parts_registry',[])), 'names:', len(d.get('display_names',{})))"`
Expected: `parts: 26 names: 24`

- [ ] **Step 4: Commit**

```bash
git add r-mos-backend/scripts/generate_atom01_extended_manifest.py
git commit -m "feat(scripts): add ATOM-01 extended manifest generator migrating hardcoded data to JSON"
```

---

### Task 5: 重构 partRegistry.ts — 从 manifest 读取

**Files:**
- Modify: `r-mos-frontend/src/adjudication/data/partRegistry.ts`

- [ ] **Step 1: 添加 manifest 数据源支持**

保持现有 API 不变（`buildPartRegistry()`、`getPartById()` 等），但改为优先从 manifest 读取。当 manifest 不可用时回退到硬编码（向后兼容）。

在文件顶部添加 manifest 注入接口：

```typescript
import type { RobotDataManifest } from '@/components/Viewer3D/assemblyManifest'
import { manifestPartToPart } from './manifestAdapter'

let _manifestRegistry: Record<string, Part> | null = null

/** 从 manifest 注入零件数据（替代硬编码） */
export function injectManifestPartRegistry(manifest: RobotDataManifest): void {
  const modelBase = `/api/v1/robots/${manifest.robotId}/assets`
  _manifestRegistry = {}
  for (const entry of manifest.parts_registry ?? []) {
    _manifestRegistry[entry.id] = manifestPartToPart(entry, modelBase)
  }
}

/** 清除注入的 manifest 数据 */
export function clearManifestPartRegistry(): void {
  _manifestRegistry = null
}
```

修改 `buildPartRegistry()` 和 `getPartById()` 等函数优先使用 `_manifestRegistry`：

```typescript
export function getPartById(id: string): Part | undefined {
  if (_manifestRegistry) return _manifestRegistry[id]
  return PART_REGISTRY[id]  // fallback to hardcoded
}

export function getAllPartIds(): string[] {
  if (_manifestRegistry) return Object.keys(_manifestRegistry)
  return Object.keys(PART_REGISTRY)
}
```

- [ ] **Step 2: 运行现有测试确保不破坏**

Run: `cd r-mos-frontend && npx vitest run src/adjudication/ --reporter=verbose`
Expected: All existing tests PASS（回退到硬编码）

- [ ] **Step 3: Commit**

```bash
git add r-mos-frontend/src/adjudication/data/partRegistry.ts
git commit -m "refactor(adjudication): add manifest injection to partRegistry, keeping hardcoded fallback"
```

---

### Task 6: 重构 assemblyTree.ts — 从 manifest 派生

**Files:**
- Modify: `r-mos-frontend/src/components/Viewer3D/assemblyTree.ts`

- [ ] **Step 1: 添加 manifest 派生函数**

保留现有 `ASSEMBLY_GROUPS` 常量作为 fallback，新增从 manifest 构建的函数：

```typescript
import type { RobotDataManifest, ManifestCameraPreset } from './assemblyManifest'

/** 从 manifest 构建装配组（替代硬编码 ASSEMBLY_GROUPS） */
export function buildAssemblyGroupsFromManifest(
  manifest: RobotDataManifest
): Record<string, { displayName: string; childLinks: string[]; explodeDir: [number, number, number] }> {
  const groups = manifest.overview_config?.assembly_groups
  if (!groups) return ASSEMBLY_GROUPS  // fallback

  const result: Record<string, { displayName: string; childLinks: string[]; explodeDir: [number, number, number] }> = {}
  for (const [key, val] of Object.entries(groups)) {
    result[key] = {
      displayName: val.display_name,
      childLinks: val.child_links,
      explodeDir: val.explode_dir,
    }
  }
  return result
}

/** 从 manifest 获取 L1 相机预设（替代硬编码 L1_CAMERA_PRESETS） */
export function getCameraPresetFromManifest(
  manifest: RobotDataManifest,
  nodeId: string
): ManifestCameraPreset | null {
  return manifest.camera_presets?.[nodeId] ?? null
}

/** 从 manifest 获取显示名（替代硬编码 LINK_DISPLAY_NAMES） */
export function getDisplayNameFromManifest(
  manifest: RobotDataManifest,
  nodeId: string
): string {
  return manifest.display_names?.[nodeId] ?? nodeId.replace(/_/g, ' ')
}
```

- [ ] **Step 2: 运行类型检查**

Run: `cd r-mos-frontend && npx tsc --noEmit 2>&1 | grep assemblyTree`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add r-mos-frontend/src/components/Viewer3D/assemblyTree.ts
git commit -m "refactor(viewer): add manifest-driven assembly groups, camera presets, display names"
```

---

### Task 7: 重构 useCameraFocus.ts — 从 manifest 相机预设读取

**Files:**
- Modify: `r-mos-frontend/src/hooks/useCameraFocus.ts`

- [ ] **Step 1: 添加 manifest 支持**

新增接收 `cameraPresets` 参数的重载，当提供时从 manifest 数据读取，否则回退到硬编码 `PART_FOCUS_POSITIONS`：

```typescript
import type { ManifestCameraPreset } from '@/components/Viewer3D/assemblyManifest'

/** 从 manifest 相机预设构建焦点位置 */
export function buildFocusPositionsFromPresets(
  presets: Record<string, ManifestCameraPreset>
): Record<string, { position: [number, number, number]; target: [number, number, number] }> {
  const result: Record<string, { position: [number, number, number]; target: [number, number, number] }> = {}
  for (const [key, preset] of Object.entries(presets)) {
    if (key === 'L0_overview') continue
    result[key] = {
      position: preset.position as [number, number, number],
      target: preset.target as [number, number, number],
    }
  }
  return result
}
```

在 `useCameraFocus` hook 中添加可选参数：

```typescript
export function useCameraFocus(
  focusTarget: string | null,
  options?: { presets?: Record<string, ManifestCameraPreset> }
) {
  const focusPositions = options?.presets
    ? buildFocusPositionsFromPresets(options.presets)
    : PART_FOCUS_POSITIONS
  // ... 其余逻辑使用 focusPositions
}
```

- [ ] **Step 2: 运行类型检查**

Run: `cd r-mos-frontend && npx tsc --noEmit 2>&1 | grep useCameraFocus`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add r-mos-frontend/src/hooks/useCameraFocus.ts
git commit -m "refactor(hooks): useCameraFocus accepts manifest camera presets, keeps hardcoded fallback"
```

---

### Task 8: 重构 MonitorPage — 关节映射从 manifest 读取

**Files:**
- Modify: `r-mos-frontend/src/pages/MonitorPage.tsx`

- [ ] **Step 1: 从 manifest joints 派生关节映射**

替换硬编码的 `MONITOR_JOINT_MAP` 和 `ATOM01_JOINT_META`，改为从 manifest 的 joints 数组动态构建：

```typescript
import { useRobotDataManifest } from '@/components/Viewer3D/useRobotDataManifest'

/** 从 manifest joints 构建关节映射 */
function buildJointMapFromManifest(
  manifest: RobotDataManifest | null
): { jointMap: Record<string, string>; jointMeta: Record<string, MonitorJointMeta> } {
  if (!manifest?.joints) {
    // fallback to hardcoded
    return { jointMap: MONITOR_JOINT_MAP, jointMeta: ATOM01_JOINT_META }
  }

  const jointMap: Record<string, string> = {}
  const jointMeta: Record<string, MonitorJointMeta> = {}
  const displayNames = manifest.display_names ?? {}

  for (const joint of manifest.joints) {
    if (joint.type === 'fixed') continue
    const key = joint.name.replace('_joint', '')
    jointMap[key] = joint.child_link
    jointMeta[key] = {
      label: displayNames[joint.child_link] ?? joint.name,
      unit: joint.type === 'prismatic' ? 'mm' : '°',
    }
  }

  return { jointMap, jointMeta }
}
```

- [ ] **Step 2: 在组件中使用**

将 `MonitorPage` 组件内的硬编码引用替换：

```typescript
const { manifest } = useRobotDataManifest(currentRobot?.id)
const { jointMap, jointMeta } = useMemo(
  () => buildJointMapFromManifest(manifest),
  [manifest]
)
```

- [ ] **Step 3: 运行类型检查**

Run: `cd r-mos-frontend && npx tsc --noEmit 2>&1 | grep MonitorPage`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add r-mos-frontend/src/pages/MonitorPage.tsx
git commit -m "refactor(monitor): derive joint map from manifest, keep hardcoded fallback"
```

---

### Task 9: 重构 SOPMaintenancePage — Link 分组从 manifest 读取

**Files:**
- Modify: `r-mos-frontend/src/pages/SOPMaintenancePage.tsx`

- [ ] **Step 1: 从 manifest 派生 Link 分组**

替换硬编码的 `UPPER_BODY_CORE_LINKS`、`REMAINING_CORE_LINKS`、`GROUP_NAMES`：

```typescript
import { useRobotDataManifest } from '@/components/Viewer3D/useRobotDataManifest'

/** 从 manifest 装配组派生上身/下身分组 */
function buildLinkGroupsFromManifest(manifest: RobotDataManifest | null) {
  if (!manifest?.overview_config?.assembly_groups) {
    return { upperLinks: UPPER_BODY_CORE_LINKS, lowerLinks: REMAINING_CORE_LINKS, groupNames: GROUP_NAMES }
  }

  const groups = manifest.overview_config.assembly_groups
  const upperGroupKeys = ['torso_link', 'left_arm', 'right_arm']
  const lowerGroupKeys = ['base_link', 'left_leg', 'right_leg']

  const upperLinks: string[] = []
  const lowerLinks: string[] = []
  const groupNames: Record<string, string> = {}

  for (const [key, group] of Object.entries(groups)) {
    groupNames[key] = group.display_name
    if (upperGroupKeys.includes(key)) {
      upperLinks.push(...group.child_links)
    } else if (lowerGroupKeys.includes(key)) {
      lowerLinks.push(...group.child_links)
    }
  }

  return { upperLinks, lowerLinks, groupNames }
}
```

- [ ] **Step 2: 替换工作台标题**

将 `'ATOM01 维保工作台'` 替换为动态标题：

```typescript
const workspaceTitle = currentRobot
  ? `${currentRobot.model_name} 维保工作台`
  : 'SOP 维保工作台'
```

- [ ] **Step 3: 运行类型检查**

Run: `cd r-mos-frontend && npx tsc --noEmit 2>&1 | grep SOPMaintenancePage`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add r-mos-frontend/src/pages/SOPMaintenancePage.tsx
git commit -m "refactor(maintenance): derive link groups from manifest, dynamic workspace title"
```

---

### Task 10: 重构 KnowledgePage — 移除 ATOM01 硬编码下拉

**Files:**
- Modify: `r-mos-frontend/src/pages/KnowledgePage.tsx`

- [ ] **Step 1: 将硬编码的 `<Option value="ATOM01">` 替换为动态机器人列表**

从 robotContextStore 或 API 获取可用机器人列表：

```typescript
import { useRobotContextStore } from '@/store/robotContextStore'

// 在组件内
const robots = useRobotContextStore((s) => s.robots)

// 替换硬编码 Option
{robots.map((r) => (
  <Option key={r.id} value={r.model_name}>{r.model_name}</Option>
))}
```

- [ ] **Step 2: 运行类型检查**

Run: `cd r-mos-frontend && npx tsc --noEmit 2>&1 | grep KnowledgePage`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add r-mos-frontend/src/pages/KnowledgePage.tsx
git commit -m "refactor(knowledge): replace hardcoded ATOM01 dropdown with dynamic robot list"
```

---

### Task 11: 移除 /atom01 固定路由，统一 3D 展示入口

**Files:**
- Modify: `r-mos-frontend/src/App.tsx`
- Modify: `r-mos-frontend/src/components/Layout/AppLayout.tsx`

- [ ] **Step 1: 将 `/atom01` 路由改为 `/3d-viewer`**

```typescript
// App.tsx
// 替换
<Route path="atom01" element={withSuspense(<Atom01DemoPage />)} />
// 为
<Route path="3d-viewer" element={withSuspense(<Atom01DemoPage />)} />
```

- [ ] **Step 2: 更新菜单链接**

```typescript
// AppLayout.tsx
// 在学生和教师菜单中
// 替换 to: '/atom01'
// 为 to: '/3d-viewer'
```

- [ ] **Step 3: 运行类型检查**

Run: `cd r-mos-frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add r-mos-frontend/src/App.tsx r-mos-frontend/src/components/Layout/AppLayout.tsx
git commit -m "refactor(routes): rename /atom01 to /3d-viewer for robot-agnostic 3D showcase"
```

---

### Task 12: 集成测试 — 验证 manifest 数据流端到端

**Files:**
- Create: `r-mos-frontend/src/components/Viewer3D/__tests__/robotDataManifest.integration.test.ts`

- [ ] **Step 1: 写集成测试**

```typescript
import { describe, it, expect } from 'vitest'
import { parseRobotDataManifest } from '../assemblyManifest'
import { buildAdjudicationDataFromManifest } from '@/adjudication/data/manifestAdapter'

// 模拟一个完整的扩展 manifest
const MOCK_MANIFEST = {
  version: '2026-05-18', robotId: '1', rootNodeId: 'base_link',
  nodes: [
    { id: 'base_link', parent_id: null, children: ['torso_link'], mesh_id: 'base_link.glb', display_name: 'Base', category: 'frame', link_name: 'base_link', transform: { translation: [0,0,0], rotation_quat: [0,0,0,1], scale: [1,1,1] } },
    { id: 'torso_link', parent_id: 'base_link', children: [], mesh_id: 'torso_link.glb', display_name: 'Torso', category: 'frame', link_name: 'torso_link', transform: { translation: [0,0,0.35], rotation_quat: [0,0,0,1], scale: [1,1,1] } },
  ],
  mesh_catalog: { 'base_link.glb': 'models/base_link.glb', 'torso_link.glb': 'models/torso_link.glb' },
  fastener_instances: [],
  joints: [{ name: 'torso_joint', type: 'revolute', parent_link: 'base_link', child_link: 'torso_link', axis: [0,0,1], limits: { lower: -1.57, upper: 1.57 } }],
  parts_registry: [
    { id: 'base_link', category: 'frame', bom_code: 'T-BASE-001', display_name: 'Base', parent_id: null, mesh_id: 'base_link.glb', local_position: [0,0,0], local_rotation: [0,0,0], group: 'base' },
    { id: 'torso_link', category: 'frame', bom_code: 'T-TORSO-001', display_name: 'Torso', parent_id: 'base_link', mesh_id: 'torso_link.glb', local_position: [0,0,0.35], local_rotation: [0,0,0], group: 'torso' },
  ],
  screw_instances: [
    { id: 's1', bom_code: 'T-SCREW-001', parent_id: 'torso_link', position: [0.02, 0.01, 0.1], axis: [0, 0, -1], spec: { type: 'M3×10', pitch: 0.5, thread_length: 10, required_tool: 'hex_2.5', torque_nm: 1.5 } },
  ],
  constraints: [
    { id: 'c1', type: 'fastened_by', constrained_part: 'torso_link', constraining_part: 'base_link', params: { screwIds: ['s1'], minScrewsToRelease: 1 }, release_condition: { type: 'all_screws_removed', required_actions: ['s1'] } },
  ],
  camera_presets: {
    'L0_overview': { position: [1.5, 1.0, 1.5], target: [0, 0.3, 0], fov: 45 },
    'torso_link': { position: [0.6, 0.5, 0.6], target: [0, 0.35, 0], fov: 40 },
  },
  tools: [
    { id: 'hex_2.5', name: '2.5mm Hex', type: 'hex_key', size: '2.5mm', description: 'For M3' },
  ],
  display_names: { 'base_link': 'Base Frame', 'torso_link': 'Torso' },
  overview_config: {
    overview_nodes: ['base_link', 'torso_link'],
    reference_set: ['base_link'],
    assembly_groups: {
      'base': { display_name: 'Base', child_links: ['base_link'], explode_dir: [0, 0, -1] },
      'torso': { display_name: 'Torso', child_links: ['torso_link'], explode_dir: [0, 0, 1] },
    },
  },
}

describe('Robot Data Manifest E2E', () => {
  it('parses full extended manifest', () => {
    const manifest = parseRobotDataManifest(MOCK_MANIFEST)
    expect(manifest.nodes).toHaveLength(2)
    expect(manifest.parts_registry).toHaveLength(2)
    expect(manifest.screw_instances).toHaveLength(1)
    expect(manifest.constraints).toHaveLength(1)
    expect(manifest.tools).toHaveLength(1)
    expect(manifest.camera_presets?.['L0_overview'].fov).toBe(45)
    expect(manifest.display_names?.['torso_link']).toBe('Torso')
  })

  it('converts to adjudication data correctly', () => {
    const manifest = parseRobotDataManifest(MOCK_MANIFEST)
    const data = buildAdjudicationDataFromManifest(manifest)

    expect(Object.keys(data.partRegistry)).toHaveLength(2)
    expect(data.partRegistry['base_link'].bomCode).toBe('T-BASE-001')

    expect(Object.keys(data.screwRegistry)).toHaveLength(1)
    expect(data.screwRegistry['s1'].screwSpec?.torque).toBe(1.5)

    expect(data.constraints).toHaveLength(1)
    expect(data.constraints[0].type).toBe('fastened_by')
  })
})
```

- [ ] **Step 2: 运行测试**

Run: `cd r-mos-frontend && npx vitest run src/components/Viewer3D/__tests__/robotDataManifest.integration.test.ts`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add r-mos-frontend/src/components/Viewer3D/__tests__/robotDataManifest.integration.test.ts
git commit -m "test(manifest): add E2E integration test for robot data manifest pipeline"
```

---

## Phase 2: SOP 裁决脚本数据库化（P1）

### 2.1 架构设计

**核心思路：** 扩展后端 `SOPStep` 模型的 JSON 字段，使其能存储裁决级数据（action type、targetParts、validations、failureReasons）。前端从 API 获取 SOP 脚本而非硬编码。

**改造路径：**
```
sopScripts.ts (硬编码)  →  POST /api/v1/sops (写入DB)  →  GET /api/v1/sops/{id} (前端读取)
                              ↑                              ↓
                     seed 脚本迁移数据           SOPPlayerAdjudicated 消费
```

### 2.2 Task 概览（10 Tasks）

| Task | 名称 | 内容 |
|------|------|------|
| 13 | 扩展 SOPStep schema | `action_params` JSON 字段增加 adjudication 子结构 |
| 14 | 扩展 SOP API 响应 | 返回完整的裁决级步骤数据 |
| 15 | 创建 SOP 裁决 seed 脚本 | 将 sopScripts.ts 数据写入数据库 |
| 16 | 前端 SOP API client | `fetchSOPScript(sopId)` 返回 `SOPScriptAdjudication` |
| 17 | 重构 SOPPlayerAdjudicated | 从 API 获取 SOP 脚本而非 `ALL_SOP_SCRIPTS` |
| 18 | 重构 hardwareSOPScripts | 30 条硬件 SOP 迁移到数据库 |
| 19 | 工具数据 API 化 | `GET /api/v1/robots/{id}/tools` |
| 20 | 评分规则配置化 | `pass_score`、`initial_score` 从作业/SOP 配置读取 |
| 21 | 维保知识库 API 化 | `maintenanceKnowledge.ts` 数据迁移到知识库 API |
| 22 | 移除前端硬编码 SOP 文件 | 删除 `data/sopScripts.ts`、`hardwareSOPScripts.ts`、`sopKneeBearing.ts` |

> 详细实施计划：`docs/superpowers/plans/2026-05-19-phase2-sop-modularization.md`

---

## Phase 3: 前端配置驱动化（P2）

### 3.1 架构设计

**核心思路：** 将菜单、路由权限、UI 配置从代码中提取为配置对象，支持角色/权限动态决定菜单项。

### 3.2 Task 概览（6 Tasks）

| Task | 名称 | 内容 |
|------|------|------|
| 23 | 菜单配置对象化 | `AppLayout.tsx` 菜单从 JSON 配置加载 |
| 24 | 路由权限表化 | `App.tsx` 的 `withRoles` 从路由表配置读取 |
| 25 | AI 工作台意图配置化 | `AgentWorkbenchPage` 意图/快速操作从配置读取 |
| 26 | WebSocket URL 环境化 | 确保 WS 地址全部走环境变量 |
| 27 | 版本号/品牌名集中管理 | `R-MOS`、`v0.2.0` 等从 `package.json` / `.env` 读取 |
| 28 | 状态标签/颜色映射集中化 | 各页面的 statusLabelMap 统一管理 |

> 详细实施计划：`docs/superpowers/plans/2026-05-19-phase3-frontend-config.md`

---

## Phase 4: 后端配置外部化（P3）

### 4.1 架构设计

**核心思路：** 敏感配置走 `.env`，seed 脚本参数化，mock 数据可配置。

### 4.2 Task 概览（5 Tasks）

| Task | 名称 | 内容 |
|------|------|------|
| 29 | SECRET_KEY 环境变量化 | `.env` 管理密钥，删除硬编码 |
| 30 | CORS_ORIGINS 环境变量化 | 从 `.env` 读取允许的源 |
| 31 | Seed 脚本参数化 | 用户密码、班级名从配置文件读取 |
| 32 | Mock 适配器参数化 | 故障参数从 config 或 JSON 文件读取 |
| 33 | LLM prompt 模板化 | 系统提示词从文件加载，支持多语言 |

> 详细实施计划：`docs/superpowers/plans/2026-05-19-phase4-backend-config.md`

---

## 验收标准

### Phase 1 验收

- [ ] 添加新机器人时，只需上传 URDF + 运行解析管线，无需修改前端代码
- [ ] ATOM-01 所有现有功能不受影响（向后兼容）
- [ ] `partRegistry`、`constraintGraph`、`screwInstances` 支持从 manifest 读取
- [ ] 监控页面、维保页面、3D 展示页面均从 manifest 获取机器人特定数据
- [ ] 所有现有测试通过

### Phase 2 验收

- [ ] 新 SOP 可通过后端 API 创建，无需修改前端代码
- [ ] `SOPPlayerAdjudicated` 从 API 加载 SOP 脚本
- [ ] 评分规则从 SOP/作业配置读取
- [ ] `data/sopScripts.ts` 等硬编码文件已删除

### Phase 3 验收

- [ ] 添加新角色/菜单项只需修改配置，无需改代码
- [ ] 所有 WS/API 地址走环境变量

### Phase 4 验收

- [ ] `SECRET_KEY` 从 `.env` 读取
- [ ] Seed 脚本可通过配置文件自定义数据
- [ ] LLM prompt 从模板文件加载
