import { describe, expect, it } from 'vitest'

import {
  buildAssemblyIndex,
  parseAssemblyManifest,
  parseExplodeManifest,
  parseRobotDataManifest,
} from '@/components/Viewer3D/assemblyManifest'

const MOCK_ASSEMBLY_RAW = {
  version: '2026-03-13',
  robotId: '1',
  rootNodeId: 'base_link',
  mesh_catalog: {
    base_link_mesh: '/api/v1/robots/1/assets/models/base_link.glb',
    torso_link_mesh: '/api/v1/robots/1/assets/models/torso_link.glb',
    torso_shell_front_mesh: '/api/v1/robots/1/assets/models/torso_shell_front.glb',
    torso_shell_rear_mesh: '/api/v1/robots/1/assets/models/torso_shell_rear.glb',
    torso_shell_lower_mesh: '/api/v1/robots/1/assets/models/torso_shell_lower.glb',
    torso_shell_back_lower_mesh: '/api/v1/robots/1/assets/models/torso_shell_back_lower.glb',
    frame_torso_chest_mesh: '/api/v1/robots/1/assets/models/frame_torso_chest.glb',
    torso_motor_mesh: '/api/v1/robots/1/assets/models/torso_motor.glb',
    torso_pcb_main_mesh: '/api/v1/robots/1/assets/models/torso_pcb_main.glb',
    left_arm_pitch_link_mesh: '/api/v1/robots/1/assets/models/left_arm_pitch_link.glb',
    right_arm_pitch_link_mesh: '/api/v1/robots/1/assets/models/right_arm_pitch_link.glb',
    fastener_m3x10_mesh: '/api/v1/robots/1/assets/models/fastener_m3x10.glb',
    fastener_m4x12_mesh: '/api/v1/robots/1/assets/models/fastener_m4x12.glb',
  },
  nodes: [
    {
      id: 'base_link',
      parent_id: null,
      children: ['torso_link'],
      mesh_id: 'base_link_mesh',
      display_name: 'Base Link',
      category: 'link',
      link_name: 'base_link',
      transform: { translation: [0, 0, 0], rotation_quat: [0, 0, 0, 1], scale: [1, 1, 1] },
    },
    {
      id: 'torso_link',
      parent_id: 'base_link',
      children: [
        'torso_shell_front',
        'torso_shell_rear',
        'torso_shell_lower',
        'torso_shell_back_lower',
        'frame_torso_chest',
        'torso_motor',
        'torso_pcb_main',
        'left_arm_pitch_link',
        'right_arm_pitch_link',
      ],
      mesh_id: 'torso_link_mesh',
      display_name: '躯干总成',
      category: 'link',
      link_name: 'torso_link',
      transform: { translation: [0, 0, 0.067], rotation_quat: [0, 0, 0, 1], scale: [1, 1, 1] },
    },
    {
      id: 'torso_shell_front',
      parent_id: 'torso_link',
      children: [],
      mesh_id: 'torso_shell_front_mesh',
      display_name: 'Torso Shell Front',
      category: 'shell',
      link_name: null,
      transform: { translation: [0.008, 0, 0.014], rotation_quat: [0, 0, 0, 1], scale: [1, 1, 1] },
    },
    {
      id: 'torso_shell_rear',
      parent_id: 'torso_link',
      children: [],
      mesh_id: 'torso_shell_rear_mesh',
      display_name: 'Torso Shell Rear',
      category: 'shell',
      link_name: null,
      transform: { translation: [-0.008, 0, 0.014], rotation_quat: [0, 0, 0, 1], scale: [1, 1, 1] },
    },
    {
      id: 'torso_shell_lower',
      parent_id: 'torso_link',
      children: [],
      mesh_id: 'torso_shell_lower_mesh',
      display_name: 'Torso Shell Lower',
      category: 'shell',
      link_name: null,
      transform: { translation: [0, 0, 0], rotation_quat: [0, 0, 0, 1], scale: [1, 1, 1] },
    },
    {
      id: 'torso_shell_back_lower',
      parent_id: 'torso_link',
      children: [],
      mesh_id: 'torso_shell_back_lower_mesh',
      display_name: 'Torso Shell Back Lower',
      category: 'shell',
      link_name: null,
      transform: { translation: [0, 0, 0], rotation_quat: [0, 0, 0, 1], scale: [1, 1, 1] },
    },
    {
      id: 'frame_torso_chest',
      parent_id: 'torso_link',
      children: [],
      mesh_id: 'frame_torso_chest_mesh',
      display_name: 'Frame Torso Chest',
      category: 'frame',
      link_name: null,
      transform: { translation: [0, 0, 0], rotation_quat: [0, 0, 0, 1], scale: [1, 1, 1] },
    },
    {
      id: 'torso_motor',
      parent_id: 'torso_link',
      children: [],
      mesh_id: 'torso_motor_mesh',
      display_name: 'Torso Motor',
      category: 'actuator',
      link_name: null,
      transform: { translation: [0, 0, 0], rotation_quat: [0, 0, 0, 1], scale: [1, 1, 1] },
    },
    {
      id: 'torso_pcb_main',
      parent_id: 'torso_link',
      children: [],
      mesh_id: 'torso_pcb_main_mesh',
      display_name: 'Torso PCB Main',
      category: 'electronics',
      link_name: null,
      transform: { translation: [0, 0, 0], rotation_quat: [0, 0, 0, 1], scale: [1, 1, 1] },
    },
    {
      id: 'left_arm_pitch_link',
      parent_id: 'torso_link',
      children: [],
      mesh_id: 'left_arm_pitch_link_mesh',
      display_name: 'Left Arm Pitch Link',
      category: 'link',
      link_name: null,
      transform: { translation: [0.1, 0, 0], rotation_quat: [0, 0, 0, 1], scale: [1, 1, 1] },
    },
    {
      id: 'right_arm_pitch_link',
      parent_id: 'torso_link',
      children: [],
      mesh_id: 'right_arm_pitch_link_mesh',
      display_name: 'Right Arm Pitch Link',
      category: 'link',
      link_name: null,
      transform: { translation: [-0.1, 0, 0], rotation_quat: [0, 0, 0, 1], scale: [1, 1, 1] },
    },
  ],
  fastener_instances: [
    {
      id: 'screw_torso_m3x10_001',
      type: 'M3x10',
      parent_id: 'torso_shell_front',
      mesh_id: 'fastener_m3x10_mesh',
      transform: { translation: [0.02, 0.01, 0], rotation_quat: [0, 0, 0, 1], scale: [1, 1, 1] },
      tool: 'hex_2.5',
      torque_nm: 0.5,
    },
    {
      id: 'screw_torso_m3x10_008',
      type: 'M3x10',
      parent_id: 'torso_shell_front',
      mesh_id: 'fastener_m3x10_mesh',
      transform: { translation: [-0.02, 0.01, 0], rotation_quat: [0, 0, 0, 1], scale: [1, 1, 1] },
      tool: 'hex_2.5',
      torque_nm: 0.5,
    },
    {
      id: 'screw_torso_m4x12_001',
      type: 'M4x12',
      parent_id: 'torso_shell_rear',
      mesh_id: 'fastener_m4x12_mesh',
      transform: { translation: [0.03, 0.02, 0], rotation_quat: [0, 0, 0, 1], scale: [1, 1, 1] },
      tool: 'hex_3',
      torque_nm: 1.2,
    },
    {
      id: 'screw_torso_m4x12_006',
      type: 'M4x12',
      parent_id: 'torso_shell_rear',
      mesh_id: 'fastener_m4x12_mesh',
      transform: { translation: [-0.03, 0.02, 0], rotation_quat: [0, 0, 0, 1], scale: [1, 1, 1] },
      tool: 'hex_3',
      torque_nm: 1.2,
    },
  ],
}

const MOCK_EXPLODE_RAW = {
  version: '2026-04-30',
  robotId: '1',
  views: [
    {
      id: 'torso_service_view',
      focus_node_id: 'torso_link',
      camera: {
        projection: 'orthographic',
        position: [1.15, 0.58, 0.72],
        target: [0.04, 0, 0.28],
      },
    },
  ],
  sequences: [
    {
      id: 'torso_cover_removal',
      step_index: 1,
      node_ids: ['torso_shell_front', 'torso_shell_rear'],
      direction: [0, 0, 1],
      distance: 0.18,
      anchor_node_id: 'torso_link',
    },
  ],
}

describe('assemblyManifest', () => {
  it('parses an assembly manifest with required fields', () => {
    const manifest = parseAssemblyManifest(MOCK_ASSEMBLY_RAW)

    expect(manifest.robotId).toBe('1')
    expect(manifest.rootNodeId).toBe('base_link')
    expect(manifest.nodes.length).toBeGreaterThanOrEqual(8)
    expect(Object.keys(manifest.mesh_catalog).length).toBeGreaterThanOrEqual(8)
    expect(manifest.fastener_instances.length).toBeGreaterThanOrEqual(4)

    const index = buildAssemblyIndex(manifest)
    expect(index.byId.torso_link.display_name).toBe('躯干总成')
    expect(index.childrenByParent.torso_link).toEqual(
      expect.arrayContaining([
        'torso_shell_front',
        'torso_shell_rear',
        'torso_shell_lower',
        'torso_shell_back_lower',
        'frame_torso_chest',
        'torso_motor',
        'torso_pcb_main',
        'left_arm_pitch_link',
        'right_arm_pitch_link',
      ]),
    )

    const torsoFastenerIds = manifest.fastener_instances
      .filter((instance) => instance.id.startsWith('screw_torso_'))
      .map((instance) => instance.id)

    expect(torsoFastenerIds.length).toBeGreaterThanOrEqual(4)
    expect(torsoFastenerIds).toEqual(
      expect.arrayContaining([
        'screw_torso_m3x10_001',
        'screw_torso_m3x10_008',
        'screw_torso_m4x12_001',
        'screw_torso_m4x12_006',
      ]),
    )
  })

  it('parses an explode manifest with authored sequences', () => {
    const manifest = parseExplodeManifest(MOCK_EXPLODE_RAW)

    expect(manifest.robotId).toBe('1')
    expect(manifest.views).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: 'torso_service_view',
        }),
      ]),
    )
    expect(manifest.sequences).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: 'torso_cover_removal',
          step_index: 1,
          node_ids: expect.arrayContaining(['torso_shell_front', 'torso_shell_rear']),
        }),
      ]),
    )
  })

  it('rejects manifests that omit required node transform fields', () => {
    expect(() =>
      parseAssemblyManifest({
        version: '2026-03-13',
        robotId: '1',
        rootNodeId: 'base_link',
        mesh_catalog: {},
        nodes: [
          {
            id: 'broken-node',
            parent_id: null,
            children: [],
            mesh_id: 'base_link',
            display_name: 'Broken',
            category: 'link',
          },
        ],
        fastener_instances: [],
      }),
    ).toThrow('assembly node broken-node is missing transform')
  })
})

describe('parseRobotDataManifest', () => {
  it('parses extended manifest with parts_registry', () => {
    const raw = {
      ...MOCK_ASSEMBLY_RAW,
      parts_registry: [{ id: 'base', category: 'frame', bom_code: 'TEST-BASE-001', display_name: 'Base', parent_id: null, mesh_id: null, local_position: [0,0,0], local_rotation: [0,0,0], group: 'base' }],
    }
    const result = parseRobotDataManifest(raw)
    expect(result.parts_registry).toHaveLength(1)
    expect(result.parts_registry![0].bom_code).toBe('TEST-BASE-001')
  })

  it('provides empty defaults for missing extended fields', () => {
    const result = parseRobotDataManifest(MOCK_ASSEMBLY_RAW)
    expect(result.parts_registry).toEqual([])
    expect(result.screw_instances).toEqual([])
    expect(result.constraints).toEqual([])
    expect(result.tools).toEqual([])
    expect(result.camera_presets).toEqual({})
    expect(result.display_names).toEqual({})
  })
})
