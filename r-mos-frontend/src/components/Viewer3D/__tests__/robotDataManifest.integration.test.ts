import { describe, it, expect } from 'vitest'
import { parseRobotDataManifest } from '../assemblyManifest'
import { buildAdjudicationDataFromManifest } from '@/adjudication/data/manifestAdapter'
import { PartCategory } from '@/adjudication/types/adjudication'

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
    expect(manifest.overview_config?.overview_nodes).toEqual(['base_link', 'torso_link'])
  })

  it('converts to adjudication data correctly', () => {
    const manifest = parseRobotDataManifest(MOCK_MANIFEST)
    const data = buildAdjudicationDataFromManifest(manifest)

    // Part registry
    expect(Object.keys(data.partRegistry)).toHaveLength(2)
    expect(data.partRegistry['base_link'].bomCode).toBe('T-BASE-001')
    expect(data.partRegistry['base_link'].category).toBe(PartCategory.FRAME)
    expect(data.partRegistry['torso_link'].displayName).toBe('Torso')

    // Screw registry
    expect(Object.keys(data.screwRegistry)).toHaveLength(1)
    expect(data.screwRegistry['s1'].category).toBe(PartCategory.SCREW)
    expect(data.screwRegistry['s1'].screwSpec?.torque).toBe(1.5)
    expect(data.screwRegistry['s1'].screwSpec?.requiredTool).toBe('hex_2.5')

    // Constraints
    expect(data.constraints).toHaveLength(1)
    expect(data.constraints[0].type).toBe('fastened_by')
    expect(data.constraints[0].constrainedPart).toBe('torso_link')
    expect(data.constraints[0].isActive).toBe(true)
  })

  it('handles manifest with no extended fields gracefully', () => {
    const minimal = {
      version: '2026-05-18', robotId: '2', rootNodeId: 'root',
      nodes: [{ id: 'root', parent_id: null, children: [], mesh_id: null, display_name: 'Root', category: 'frame', link_name: null, transform: { translation: [0,0,0], rotation_quat: [0,0,0,1], scale: [1,1,1] } }],
      mesh_catalog: {}, fastener_instances: [],
    }
    const manifest = parseRobotDataManifest(minimal)
    const data = buildAdjudicationDataFromManifest(manifest)

    expect(manifest.parts_registry).toEqual([])
    expect(manifest.tools).toEqual([])
    expect(Object.keys(data.partRegistry)).toHaveLength(0)
    expect(data.constraints).toHaveLength(0)
  })
})
