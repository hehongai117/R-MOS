/**
 * Manifest → Adjudication 全链路集成测试
 *
 * 测试重点：完整 pipeline 的端到端场景
 * - 多零件、多螺丝、多约束的复合 manifest
 * - modelBase URL 构造正确性
 * - 所有 category 枚举映射覆盖
 * - registry 内部引用一致性
 * - 边界值与异常路径
 */

import { describe, it, expect } from 'vitest'
import {
  manifestPartToPart,
  manifestScrewToPart,
  manifestConstraintToConstraint,
  buildAdjudicationDataFromManifest,
} from '../manifestAdapter'
import { PartCategory, ConstraintType } from '../../types/adjudication'
import type {
  ManifestPartEntry,
  ManifestScrewEntry,
  ManifestConstraintEntry,
  RobotDataManifest,
} from '@/components/Viewer3D/assemblyManifest'

// ──────────────────────────────────────────────
// 测试夹具（共享 Fixture）
// ──────────────────────────────────────────────

const MODEL_BASE = '/api/v1/robots/42/assets'

/** 构造一个最小合法的 RobotDataManifest 壳 */
function makeBaseManifest(overrides: Partial<RobotDataManifest> = {}): RobotDataManifest {
  return {
    version: '1.0',
    robotId: '42',
    rootNodeId: 'base_link',
    mesh_catalog: {},
    nodes: [],
    fastener_instances: [],
    ...overrides,
  } as unknown as RobotDataManifest
}

// ──────────────────────────────────────────────
// 1. manifestPartToPart — category 全枚举覆盖
// ──────────────────────────────────────────────

describe('manifestPartToPart — category mapping (all known categories)', () => {
  const categoryMap: Array<[string, PartCategory]> = [
    ['frame',   PartCategory.FRAME],
    ['cover',   PartCategory.COVER],
    ['screw',   PartCategory.SCREW],
    ['nut',     PartCategory.NUT],
    ['motor',   PartCategory.MOTOR],
    ['bearing', PartCategory.BEARING],
    ['pcb',     PartCategory.PCB],
    ['wire',    PartCategory.WIRE],
    ['tool',    PartCategory.TOOL],
  ]

  it.each(categoryMap)('maps category "%s" → PartCategory.%s', (rawCategory, expected) => {
    const entry: ManifestPartEntry = {
      id: `part_${rawCategory}`,
      category: rawCategory,
      bom_code: `BOM-${rawCategory.toUpperCase()}-001`,
      display_name: `测试零件 (${rawCategory})`,
      parent_id: null,
      mesh_id: `${rawCategory}.glb`,
      local_position: [0, 0, 0],
      local_rotation: [0, 0, 0],
      group: null,
    }
    const result = manifestPartToPart(entry, MODEL_BASE)
    expect(result.category).toBe(expected)
  })

  it('falls back to FRAME for unknown category string', () => {
    const entry: ManifestPartEntry = {
      id: 'part_xyz',
      category: 'totally_unknown',
      bom_code: 'BOM-XYZ',
      display_name: '未知类型零件',
      parent_id: null,
      mesh_id: null,
      local_position: [1, 2, 3],
      local_rotation: [0, 0, 0],
      group: null,
    }
    const result = manifestPartToPart(entry, MODEL_BASE)
    expect(result.category).toBe(PartCategory.FRAME)
    expect(result.modelPath).toBe('')
  })
})

// ──────────────────────────────────────────────
// 2. manifestPartToPart — modelPath 构造
// ──────────────────────────────────────────────

describe('manifestPartToPart — modelPath construction', () => {
  it('generates correct modelPath when mesh_id is present', () => {
    const entry: ManifestPartEntry = {
      id: 'torso_link',
      category: 'frame',
      bom_code: 'ATOM-01-TORSO-001',
      display_name: '躯干',
      parent_id: 'base_link',
      mesh_id: 'meshes/torso_link.glb',
      local_position: [0, 0, 0.3],
      local_rotation: [0, 0, 0],
      group: 'torso',
    }
    const result = manifestPartToPart(entry, MODEL_BASE)
    expect(result.modelPath).toBe(`${MODEL_BASE}/meshes/torso_link.glb`)
  })

  it('returns empty string for modelPath when mesh_id is null', () => {
    const entry: ManifestPartEntry = {
      id: 'virtual_part',
      category: 'frame',
      bom_code: 'ATOM-01-VIRTUAL-001',
      display_name: '虚拟零件',
      parent_id: null,
      mesh_id: null,
      local_position: [0, 0, 0],
      local_rotation: [0, 0, 0],
      group: null,
    }
    const result = manifestPartToPart(entry, MODEL_BASE)
    expect(result.modelPath).toBe('')
  })

  it('constructs correct modelPath with robot-specific base URL', () => {
    const customBase = '/api/v1/robots/999/assets'
    const entry: ManifestPartEntry = {
      id: 'arm_link',
      category: 'frame',
      bom_code: 'ROBOT-999-ARM-001',
      display_name: '手臂',
      parent_id: null,
      mesh_id: 'arm.glb',
      local_position: [0, 0, 0],
      local_rotation: [0, 0, 0],
      group: 'arm',
    }
    const result = manifestPartToPart(entry, customBase)
    expect(result.modelPath).toBe('/api/v1/robots/999/assets/arm.glb')
  })
})

// ──────────────────────────────────────────────
// 3. manifestPartToPart — 字段映射完整性
// ──────────────────────────────────────────────

describe('manifestPartToPart — complete field mapping', () => {
  it('maps all fields correctly for a full part entry', () => {
    const entry: ManifestPartEntry = {
      id: 'left_knee_link',
      category: 'motor',
      bom_code: 'ATOM-01-MOTOR-005',
      display_name: '左膝电机',
      parent_id: 'left_thigh_link',
      mesh_id: 'left_knee_motor.glb',
      local_position: [0.05, -0.1, 0.2],
      local_rotation: [0, 1.57, 0],
      group: 'left_leg',
    }
    const result = manifestPartToPart(entry, MODEL_BASE)

    expect(result.id).toBe('left_knee_link')
    expect(result.category).toBe(PartCategory.MOTOR)
    expect(result.bomCode).toBe('ATOM-01-MOTOR-005')
    expect(result.displayName).toBe('左膝电机')
    expect(result.modelPath).toBe(`${MODEL_BASE}/left_knee_motor.glb`)
    expect(result.parentId).toBe('left_thigh_link')
    expect(result.localPosition).toEqual([0.05, -0.1, 0.2])
    expect(result.localRotation).toEqual([0, 1.57, 0])
    expect(result.screwSpec).toBeUndefined()
  })

  it('sets parentId to undefined when parent_id is null', () => {
    const entry: ManifestPartEntry = {
      id: 'root_part',
      category: 'frame',
      bom_code: 'ATOM-01-ROOT-001',
      display_name: '根部件',
      parent_id: null,
      mesh_id: null,
      local_position: [0, 0, 0],
      local_rotation: [0, 0, 0],
      group: null,
    }
    const result = manifestPartToPart(entry, MODEL_BASE)
    expect(result.parentId).toBeUndefined()
  })
})

// ──────────────────────────────────────────────
// 4. manifestScrewToPart — screwSpec 完整映射
// ──────────────────────────────────────────────

describe('manifestScrewToPart — screwSpec mapping', () => {
  const screwEntry: ManifestScrewEntry = {
    id: 'screw_torso_m3x10_001',
    bom_code: 'ATOM-01-SCREW-M3X10-001',
    parent_id: 'torso_cover_link',
    position: [0.02, 0.03, -0.05],
    axis: [0, 0, -1],
    spec: {
      type: 'M3×10',
      pitch: 0.5,
      thread_length: 10,
      required_tool: 'hex_2.5',
      torque_nm: 1.8,
    },
  }

  it('sets category to SCREW', () => {
    const result = manifestScrewToPart(screwEntry, MODEL_BASE)
    expect(result.category).toBe(PartCategory.SCREW)
  })

  it('maps screwSpec type and pitch correctly', () => {
    const result = manifestScrewToPart(screwEntry, MODEL_BASE)
    expect(result.screwSpec?.type).toBe('M3×10')
    expect(result.screwSpec?.pitch).toBe(0.5)
  })

  it('maps screwSpec threadLength from thread_length', () => {
    const result = manifestScrewToPart(screwEntry, MODEL_BASE)
    expect(result.screwSpec?.threadLength).toBe(10)
  })

  it('maps screwSpec requiredTool from required_tool', () => {
    const result = manifestScrewToPart(screwEntry, MODEL_BASE)
    expect(result.screwSpec?.requiredTool).toBe('hex_2.5')
  })

  it('maps screwSpec torque from torque_nm', () => {
    const result = manifestScrewToPart(screwEntry, MODEL_BASE)
    expect(result.screwSpec?.torque).toBe(1.8)
  })

  it('sets displayName to spec.type', () => {
    const result = manifestScrewToPart(screwEntry, MODEL_BASE)
    expect(result.displayName).toBe('M3×10')
  })

  it('maps parentId and localPosition from parent_id and position', () => {
    const result = manifestScrewToPart(screwEntry, MODEL_BASE)
    expect(result.parentId).toBe('torso_cover_link')
    expect(result.localPosition).toEqual([0.02, 0.03, -0.05])
  })

  it('sets localRotation to [0, 0, 0] (default)', () => {
    const result = manifestScrewToPart(screwEntry, MODEL_BASE)
    expect(result.localRotation).toEqual([0, 0, 0])
  })

  it('sets modelPath to empty string (no mesh for screw)', () => {
    const result = manifestScrewToPart(screwEntry, MODEL_BASE)
    expect(result.modelPath).toBe('')
  })
})

// ──────────────────────────────────────────────
// 5. manifestConstraintToConstraint — 字段映射
// ──────────────────────────────────────────────

describe('manifestConstraintToConstraint — field mapping', () => {
  it('maps fastened_by constraint correctly', () => {
    const entry: ManifestConstraintEntry = {
      id: 'con_torso_cover',
      type: 'fastened_by',
      constrained_part: 'torso_cover_link',
      constraining_part: 'screw_torso_m3x10_001',
      params: { screwIds: ['screw_torso_m3x10_001', 'screw_torso_m3x10_002'], minScrewsToRelease: 2 },
      release_condition: {
        type: 'all_screws_removed',
        required_actions: ['screw_torso_m3x10_001', 'screw_torso_m3x10_002'],
      },
    }
    const result = manifestConstraintToConstraint(entry)

    expect(result.id).toBe('con_torso_cover')
    expect(result.type).toBe(ConstraintType.FASTENED_BY)
    expect(result.constrainedPart).toBe('torso_cover_link')
    expect(result.constrainingPart).toBe('screw_torso_m3x10_001')
    expect(result.isActive).toBe(true)
    expect(result.releaseCondition.type).toBe('all_screws_removed')
    expect(result.releaseCondition.requiredActions).toEqual(
      ['screw_torso_m3x10_001', 'screw_torso_m3x10_002'],
    )
  })

  it('maps covered_by constraint correctly', () => {
    const entry: ManifestConstraintEntry = {
      id: 'con_motor_covered',
      type: 'covered_by',
      constrained_part: 'left_knee_motor',
      constraining_part: 'left_knee_cover',
      params: { coverPartId: 'left_knee_cover', coverType: 'full' },
      release_condition: {
        type: 'cover_removed',
        required_actions: ['left_knee_cover'],
      },
    }
    const result = manifestConstraintToConstraint(entry)

    expect(result.type).toBe(ConstraintType.COVERED_BY)
    expect(result.constrainedPart).toBe('left_knee_motor')
    expect(result.constrainingPart).toBe('left_knee_cover')
    expect(result.isActive).toBe(true)
  })

  it('maps blocked_by constraint correctly', () => {
    const entry: ManifestConstraintEntry = {
      id: 'con_pcb_blocked',
      type: 'blocked_by',
      constrained_part: 'main_pcb',
      constraining_part: 'front_panel',
      params: { blockingPartId: 'front_panel', blockingDirection: [1, 0, 0] },
      release_condition: {
        type: 'cover_removed',
        required_actions: ['front_panel'],
      },
    }
    const result = manifestConstraintToConstraint(entry)

    expect(result.type).toBe(ConstraintType.BLOCKED_BY)
    expect(result.params).toMatchObject({ blockingPartId: 'front_panel' })
  })
})

// ──────────────────────────────────────────────
// 6. buildAdjudicationDataFromManifest — 全链路集成
// ──────────────────────────────────────────────

describe('buildAdjudicationDataFromManifest — full pipeline integration', () => {
  /** 构造一个含有完整多零件/螺丝/约束数据的 manifest */
  const fullManifest = makeBaseManifest({
    parts_registry: [
      {
        id: 'base_link',
        category: 'frame',
        bom_code: 'ATOM-42-BASE-001',
        display_name: '底座',
        parent_id: null,
        mesh_id: 'base_link.glb',
        local_position: [0, 0, 0],
        local_rotation: [0, 0, 0],
        group: 'base',
      },
      {
        id: 'torso_cover',
        category: 'cover',
        bom_code: 'ATOM-42-COVER-001',
        display_name: '躯干外壳',
        parent_id: 'base_link',
        mesh_id: 'torso_cover.glb',
        local_position: [0, 0, 0.3],
        local_rotation: [0, 0, 0],
        group: 'torso',
      },
      {
        id: 'main_pcb',
        category: 'pcb',
        bom_code: 'ATOM-42-PCB-001',
        display_name: '主控板',
        parent_id: 'base_link',
        mesh_id: null,
        local_position: [0, 0, 0.1],
        local_rotation: [0, 0, 0],
        group: 'electronics',
      },
    ],
    screw_instances: [
      {
        id: 'screw_cover_001',
        bom_code: 'ATOM-42-SCREW-M3X10-001',
        parent_id: 'torso_cover',
        position: [0.02, 0, -0.05],
        axis: [0, 0, -1],
        spec: { type: 'M3×10', pitch: 0.5, thread_length: 10, required_tool: 'hex_2.5', torque_nm: 1.8 },
      },
      {
        id: 'screw_cover_002',
        bom_code: 'ATOM-42-SCREW-M3X10-002',
        parent_id: 'torso_cover',
        position: [-0.02, 0, -0.05],
        axis: [0, 0, -1],
        spec: { type: 'M3×10', pitch: 0.5, thread_length: 10, required_tool: 'hex_2.5', torque_nm: 1.8 },
      },
    ],
    constraints: [
      {
        id: 'con_cover_fastened',
        type: 'fastened_by',
        constrained_part: 'torso_cover',
        constraining_part: 'screw_cover_001',
        params: { screwIds: ['screw_cover_001', 'screw_cover_002'], minScrewsToRelease: 2 },
        release_condition: {
          type: 'all_screws_removed',
          required_actions: ['screw_cover_001', 'screw_cover_002'],
        },
      },
      {
        id: 'con_pcb_covered',
        type: 'covered_by',
        constrained_part: 'main_pcb',
        constraining_part: 'torso_cover',
        params: { coverPartId: 'torso_cover', coverType: 'full' },
        release_condition: {
          type: 'cover_removed',
          required_actions: ['torso_cover'],
        },
      },
    ],
  })

  it('partRegistry contains all parts_registry entries', () => {
    const { partRegistry } = buildAdjudicationDataFromManifest(fullManifest)
    expect(Object.keys(partRegistry)).toHaveLength(3)
    expect(partRegistry['base_link']).toBeDefined()
    expect(partRegistry['torso_cover']).toBeDefined()
    expect(partRegistry['main_pcb']).toBeDefined()
  })

  it('partRegistry entries have correct categories', () => {
    const { partRegistry } = buildAdjudicationDataFromManifest(fullManifest)
    expect(partRegistry['base_link'].category).toBe(PartCategory.FRAME)
    expect(partRegistry['torso_cover'].category).toBe(PartCategory.COVER)
    expect(partRegistry['main_pcb'].category).toBe(PartCategory.PCB)
  })

  it('partRegistry entries have correct modelPath using robotId in modelBase', () => {
    const { partRegistry } = buildAdjudicationDataFromManifest(fullManifest)
    // robotId = '42', so modelBase = /api/v1/robots/42/assets
    expect(partRegistry['base_link'].modelPath).toBe('/api/v1/robots/42/assets/base_link.glb')
    expect(partRegistry['torso_cover'].modelPath).toBe('/api/v1/robots/42/assets/torso_cover.glb')
    expect(partRegistry['main_pcb'].modelPath).toBe('')  // mesh_id was null
  })

  it('screwRegistry contains all screw_instances entries', () => {
    const { screwRegistry } = buildAdjudicationDataFromManifest(fullManifest)
    expect(Object.keys(screwRegistry)).toHaveLength(2)
    expect(screwRegistry['screw_cover_001']).toBeDefined()
    expect(screwRegistry['screw_cover_002']).toBeDefined()
  })

  it('screwRegistry entries have SCREW category and valid screwSpec', () => {
    const { screwRegistry } = buildAdjudicationDataFromManifest(fullManifest)
    const screw = screwRegistry['screw_cover_001']
    expect(screw.category).toBe(PartCategory.SCREW)
    expect(screw.screwSpec).toBeDefined()
    expect(screw.screwSpec?.type).toBe('M3×10')
    expect(screw.screwSpec?.pitch).toBe(0.5)
    expect(screw.screwSpec?.threadLength).toBe(10)
    expect(screw.screwSpec?.requiredTool).toBe('hex_2.5')
    expect(screw.screwSpec?.torque).toBe(1.8)
  })

  it('constraints array has correct count and types', () => {
    const { constraints } = buildAdjudicationDataFromManifest(fullManifest)
    expect(constraints).toHaveLength(2)
    expect(constraints[0].type).toBe(ConstraintType.FASTENED_BY)
    expect(constraints[1].type).toBe(ConstraintType.COVERED_BY)
  })

  it('all constraints are isActive = true', () => {
    const { constraints } = buildAdjudicationDataFromManifest(fullManifest)
    constraints.forEach((c) => {
      expect(c.isActive).toBe(true)
    })
  })

  it('constraint constrainedPart references valid partRegistry key', () => {
    const { partRegistry, constraints } = buildAdjudicationDataFromManifest(fullManifest)
    // con_cover_fastened → torso_cover
    expect(partRegistry[constraints[0].constrainedPart]).toBeDefined()
    // con_pcb_covered → main_pcb
    expect(partRegistry[constraints[1].constrainedPart]).toBeDefined()
  })

  it('screw parentId references valid partRegistry key', () => {
    const { partRegistry, screwRegistry } = buildAdjudicationDataFromManifest(fullManifest)
    Object.values(screwRegistry).forEach((screw) => {
      if (screw.parentId) {
        expect(partRegistry[screw.parentId]).toBeDefined()
      }
    })
  })
})

// ──────────────────────────────────────────────
// 7. buildAdjudicationDataFromManifest — 空 manifest 边界
// ──────────────────────────────────────────────

describe('buildAdjudicationDataFromManifest — empty manifest', () => {
  it('returns empty registries and constraint list for minimal manifest', () => {
    const manifest = makeBaseManifest()
    const { partRegistry, screwRegistry, constraints } = buildAdjudicationDataFromManifest(manifest)
    expect(Object.keys(partRegistry)).toHaveLength(0)
    expect(Object.keys(screwRegistry)).toHaveLength(0)
    expect(constraints).toHaveLength(0)
  })

  it('returns empty registries when parts_registry is empty array', () => {
    const manifest = makeBaseManifest({ parts_registry: [], screw_instances: [], constraints: [] })
    const { partRegistry, screwRegistry, constraints } = buildAdjudicationDataFromManifest(manifest)
    expect(Object.keys(partRegistry)).toHaveLength(0)
    expect(Object.keys(screwRegistry)).toHaveLength(0)
    expect(constraints).toHaveLength(0)
  })
})

// ──────────────────────────────────────────────
// 8. modelBase URL — robotId 替换验证
// ──────────────────────────────────────────────

describe('buildAdjudicationDataFromManifest — robotId-driven modelBase', () => {
  it('uses robotId from manifest to construct modelBase URL', () => {
    const manifest = makeBaseManifest({
      robotId: '123',
      parts_registry: [
        {
          id: 'leg_link',
          category: 'frame',
          bom_code: 'R123-LEG-001',
          display_name: '腿部',
          parent_id: null,
          mesh_id: 'leg.glb',
          local_position: [0, 0, 0],
          local_rotation: [0, 0, 0],
          group: null,
        },
      ],
    })
    const { partRegistry } = buildAdjudicationDataFromManifest(manifest)
    expect(partRegistry['leg_link'].modelPath).toBe('/api/v1/robots/123/assets/leg.glb')
  })

  it('different robotIds produce different modelBase URLs', () => {
    const makeManifestWithId = (robotId: string) =>
      makeBaseManifest({
        robotId,
        parts_registry: [
          {
            id: 'part_a',
            category: 'frame',
            bom_code: 'BOM-A',
            display_name: '零件A',
            parent_id: null,
            mesh_id: 'part_a.glb',
            local_position: [0, 0, 0],
            local_rotation: [0, 0, 0],
            group: null,
          },
        ],
      })

    const result1 = buildAdjudicationDataFromManifest(makeManifestWithId('1'))
    const result2 = buildAdjudicationDataFromManifest(makeManifestWithId('99'))

    expect(result1.partRegistry['part_a'].modelPath).toBe('/api/v1/robots/1/assets/part_a.glb')
    expect(result2.partRegistry['part_a'].modelPath).toBe('/api/v1/robots/99/assets/part_a.glb')
  })
})
