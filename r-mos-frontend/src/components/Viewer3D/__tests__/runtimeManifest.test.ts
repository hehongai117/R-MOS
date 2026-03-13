import { describe, expect, it } from 'vitest'

import { createRuntimeManifestAdapter, detectRuntimeAssetFormat, resolveRuntimeAssetPaths } from '@/components/Viewer3D/runtimeManifest'
import type { MaintenanceDraftResponse } from '@/types/maintenance'

function buildDraft(): MaintenanceDraftResponse {
  return {
    draft_id: 'draft-runtime',
    project_id: 'project-runtime',
    request_id: 'request-runtime',
    review_status: 'draft_pending_review',
    draft: {
      title: 'Fourier N1 维护',
      maintenance_goal: '执行器弯曲维护',
      steps: [
        {
          step_id: 'step-1',
          title: '检查装配',
          description: '检查 arm_assembly',
          model_targets: ['arm_assembly'],
        },
      ],
    },
    verdict_steps: [],
    viewer_manifest: {
      robotId: 'fourier-n1',
      label: 'Fourier N1',
      parts: ['meshes/base_link.STL', 'meshes/elbow_link.STL'],
      assets: [
        {
          asset_id: 'base_link::meshes/base_link.STL',
          asset_type: 'stl',
          display_name: 'base_link',
          node_id: 'base_link',
          path: 'meshes/base_link.STL',
          source_paths: ['meshes/base_link.STL', 'urdf/N1.urdf'],
        },
        {
          asset_id: 'elbow_link::meshes/elbow_link.STL',
          asset_type: 'stl',
          display_name: 'elbow_link',
          node_id: 'elbow_link',
          path: 'meshes/elbow_link.STL',
          source_paths: ['meshes/elbow_link.STL', 'urdf/N1.urdf'],
        },
      ],
      structures: [
        {
          path: 'urdf/N1.urdf',
          root_nodes: ['base_link'],
          structure_type: 'urdf',
        },
      ],
      needs_review_nodes: ['arm_assembly'],
    },
    manifest_tree: {
      robot_key: 'fourier-n1',
      root_nodes: ['base_link'],
      nodes: [
        {
          id: 'base_link',
          display_name: 'base_link',
          parent_id: null,
          children: ['arm_assembly'],
          source_paths: ['meshes/base_link.STL', 'urdf/N1.urdf'],
          runtime_asset_paths: ['meshes/base_link.STL'],
          file_kinds: ['part_model', 'structure'],
        },
        {
          id: 'arm_assembly',
          display_name: 'arm_assembly',
          parent_id: 'base_link',
          children: ['elbow_link'],
          source_paths: ['cad/arm_assembly.SLDASM'],
          runtime_asset_paths: [],
          file_kinds: ['assembly'],
        },
        {
          id: 'elbow_link',
          display_name: 'elbow_link',
          parent_id: 'arm_assembly',
          children: [],
          source_paths: ['meshes/elbow_link.STL', 'cad/elbow_link.STEP'],
          runtime_asset_paths: ['meshes/elbow_link.STL'],
          file_kinds: ['part_model'],
        },
      ],
    },
    manifest_mapping: {
      base_link: {
        source_paths: ['meshes/base_link.STL', 'urdf/N1.urdf'],
        runtime_asset_paths: ['meshes/base_link.STL'],
        file_kinds: ['part_model', 'structure'],
      },
      arm_assembly: {
        source_paths: ['cad/arm_assembly.SLDASM'],
        runtime_asset_paths: [],
        file_kinds: ['assembly'],
      },
      elbow_link: {
        source_paths: ['meshes/elbow_link.STL', 'cad/elbow_link.STEP'],
        runtime_asset_paths: ['meshes/elbow_link.STL'],
        file_kinds: ['part_model'],
      },
    },
    citations: [],
  }
}

describe('runtimeManifest', () => {
  it('resolves descendant STL assets for assembly targets', () => {
    const adapter = createRuntimeManifestAdapter(buildDraft())

    expect(resolveRuntimeAssetPaths(adapter, ['arm_assembly'])).toEqual(['meshes/elbow_link.STL'])
  })

  it('detects runtime formats beyond glb', () => {
    expect(detectRuntimeAssetFormat('meshes/base_link.STL')).toBe('stl')
    expect(detectRuntimeAssetFormat('cad/elbow_link.STEP')).toBe('unsupported')
    expect(detectRuntimeAssetFormat('viewer/elbow.glb')).toBe('gltf')
  })

  it('normalizes runtime tree nodes into the shared viewer tree adapter', () => {
    const adapter = createRuntimeManifestAdapter(buildDraft())

    expect(adapter.tree.rootNodeIds).toEqual(['base_link'])
    expect(adapter.tree.nodes.arm_assembly).toEqual(
      expect.objectContaining({
        id: 'arm_assembly',
        parentId: 'base_link',
        children: ['elbow_link'],
        displayName: 'arm_assembly',
      }),
    )
  })
})
