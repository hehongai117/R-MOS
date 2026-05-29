import { describe, it, expect } from 'vitest'
import { manifestPartToPart, manifestScrewToPart, manifestConstraintToConstraint, buildAdjudicationDataFromManifest } from '../manifestAdapter'
import { PartCategory } from '../../types/adjudication'
import type { ManifestPartEntry, ManifestScrewEntry, ManifestConstraintEntry, RobotDataManifest } from '@/components/Viewer3D/assemblyManifest'

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
    expect(result.modelPath).toBe('/api/v1/robots/1/assets/base_link.glb')
  })

  it('handles unknown category with fallback to FRAME', () => {
    const entry: ManifestPartEntry = {
      id: 'x', category: 'unknown_type', bom_code: 'X', display_name: 'X',
      parent_id: null, mesh_id: null, local_position: [0,0,0], local_rotation: [0,0,0], group: null,
    }
    const result = manifestPartToPart(entry, '/base')
    expect(result.category).toBe(PartCategory.FRAME)
    expect(result.modelPath).toBe('')
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
    expect(result.screwSpec?.requiredTool).toBe('hex_3')
    expect(result.parentId).toBe('left_ankle_roll_link')
  })
})

describe('manifestConstraintToConstraint', () => {
  it('converts manifest constraint entry', () => {
    const entry: ManifestConstraintEntry = {
      id: 'c1', type: 'fastened_by', constrained_part: 'cover', constraining_part: 'base',
      params: { screwIds: ['s1'] },
      release_condition: { type: 'all_screws_removed', required_actions: ['s1'] },
    }
    const result = manifestConstraintToConstraint(entry)
    expect(result.type).toBe('fastened_by')
    expect(result.isActive).toBe(true)
    expect(result.constrainedPart).toBe('cover')
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
    expect(result.partRegistry['base'].bomCode).toBe('B-001')
    expect(Object.keys(result.screwRegistry)).toHaveLength(1)
    expect(result.screwRegistry['s1'].screwSpec?.torque).toBe(1.5)
    expect(result.constraints).toHaveLength(1)
    expect(result.constraints[0].type).toBe('fastened_by')
  })

  it('returns empty registries for manifest without extended data', () => {
    const manifest = {
      version: 'test', robotId: '1', rootNodeId: 'root',
      nodes: [], mesh_catalog: {}, fastener_instances: [],
    } as unknown as RobotDataManifest

    const result = buildAdjudicationDataFromManifest(manifest)
    expect(Object.keys(result.partRegistry)).toHaveLength(0)
    expect(Object.keys(result.screwRegistry)).toHaveLength(0)
    expect(result.constraints).toHaveLength(0)
  })
})
