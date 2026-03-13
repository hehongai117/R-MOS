import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import * as THREE from 'three'

import { resolveExplodeView } from '@/components/Viewer3D/assemblyManifest'
import type { ExplodeManifest } from '@/components/Viewer3D/assemblyManifest'
import type { Atom01AssemblyAdapter } from '@/components/Viewer3D/hooks/useAtom01AssemblyData'
import { Atom01AssemblyRenderer, collectAssemblyRenderItems } from '@/components/Viewer3D/Atom01AssemblyRenderer'

vi.mock('@react-three/drei', () => ({
  useGLTF: vi.fn(() => ({
    scene: new THREE.Group(),
  })),
}))

function buildAdapter(): Atom01AssemblyAdapter {
  return {
    robotId: 'atom01',
    label: 'ATOM01',
    tree: {
      rootNodeIds: ['base_link'],
      nodes: {
        base_link: {
          id: 'base_link',
          displayName: '底座总成',
          parentId: null,
          children: ['torso_link'],
          runtimeAssetPaths: ['/models/robots/atom01/base_link.glb'],
          sourcePaths: [],
          fileKinds: ['link'],
        },
        torso_link: {
          id: 'torso_link',
          displayName: '躯干总成',
          parentId: 'base_link',
          children: ['torso_shell_front'],
          runtimeAssetPaths: ['/models/robots/atom01/torso_link.glb'],
          sourcePaths: [],
          fileKinds: ['link'],
        },
        torso_shell_front: {
          id: 'torso_shell_front',
          displayName: '躯干前盖',
          parentId: 'torso_link',
          children: [],
          runtimeAssetPaths: ['/models/parts/frames/胸腔胸部.glb'],
          sourcePaths: [],
          fileKinds: ['frame'],
        },
      },
    },
    transforms: {
      base_link: {
        translation: [0, 0, 0],
        rotation_quat: [0, 0, 0, 1],
        scale: [1, 1, 1],
      },
      torso_link: {
        translation: [-0.028, 0, 0.067],
        rotation_quat: [0, 0, 0, 1],
        scale: [1, 1, 1],
      },
      torso_shell_front: {
        translation: [0.008, 0, 0.014],
        rotation_quat: [0, 0, 0, 1],
        scale: [1, 1, 1],
      },
      torso_shell_front_m4x12_01: {
        translation: [0.032, 0.046, 0.02],
        rotation_quat: [0, 0, 0, 1],
        scale: [1, 1, 1],
      },
    },
    meshCatalog: {
      torso_shell_front_mesh: '/models/parts/frames/胸腔胸部.glb',
      fastener_m4x12_mesh: '/models/parts/screws/内六角圆柱头螺钉M4x12.glb',
    },
    fastenerInstances: [
      {
        id: 'torso_shell_front_m4x12_01',
        type: 'M4x12',
        parent_id: 'torso_shell_front',
        mesh_id: 'fastener_m4x12_mesh',
        transform: {
          translation: [0.032, 0.046, 0.02],
          rotation_quat: [0, 0, 0, 1],
          scale: [1, 1, 1],
        },
        tool: 'hex_3',
        torque_nm: 1.2,
      },
    ],
    assetUrls: [
      '/models/robots/atom01/torso_link.glb',
      '/models/parts/frames/胸腔胸部.glb',
      '/models/parts/screws/内六角圆柱头螺钉M4x12.glb',
    ],
  }
}

function buildExplodeManifest(): ExplodeManifest {
  return {
    version: '2026-03-13',
    robotId: 'atom01',
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
        node_ids: ['torso_shell_front'],
        direction: [0, 0, 1],
        distance: 0.18,
        anchor_node_id: 'torso_link',
      },
      {
        id: 'torso_secondary_release',
        step_index: 2,
        node_ids: ['torso_shell_front'],
        direction: [0, 1, 0],
        distance: 0.1,
        anchor_node_id: 'torso_link',
      },
    ],
  }
}

describe('Atom01AssemblyRenderer', () => {
  it('collects child nodes and fasteners for a focused link', () => {
    const items = collectAssemblyRenderItems(buildAdapter(), 'torso_link')

    expect(items.map((item) => item.id)).toEqual(['torso_shell_front', 'torso_shell_front_m4x12_01'])
    expect(items[0]).toEqual(expect.objectContaining({
      parentId: 'torso_link',
      kind: 'node',
      translation: [0.008, 0, 0.014],
    }))
    expect(items[1]).toEqual(expect.objectContaining({
      parentId: 'torso_shell_front',
      kind: 'fastener',
      translation: [0.032, 0.046, 0.02],
    }))
  })

  it('renders assembly descendants under their parent nodes', () => {
    render(<Atom01AssemblyRenderer adapter={buildAdapter()} rootLinkName="torso_link" />)

    const node = screen.getByTestId('assembly-node-torso_shell_front')
    const fastener = screen.getByTestId('assembly-fastener-torso_shell_front_m4x12_01')

    expect(node.getAttribute('data-parent-id')).toBe('torso_link')
    expect(node.getAttribute('data-translation')).toBe('0.008,0,0.014')
    expect(fastener.getAttribute('data-parent-id')).toBe('torso_shell_front')
    expect(fastener.closest('[data-testid="assembly-node-torso_shell_front"]')).toBe(node)
  })

  it('applies authored explode offsets to targeted assembly nodes', () => {
    const items = collectAssemblyRenderItems(buildAdapter(), 'torso_link', buildExplodeManifest(), 1)

    expect(items[0]).toEqual(expect.objectContaining({
      id: 'torso_shell_front',
      renderTranslation: [0.008, 0, 0.194],
    }))
    expect(items[1]).toEqual(expect.objectContaining({
      id: 'torso_shell_front_m4x12_01',
      renderTranslation: [0.032, 0.046, 0.02],
    }))
  })

  it('limits authored explode offsets to the active step index', () => {
    const items = collectAssemblyRenderItems(buildAdapter(), 'torso_link', buildExplodeManifest(), 1, 1)

    expect(items[0]).toEqual(expect.objectContaining({
      id: 'torso_shell_front',
      renderTranslation: [0.008, 0, 0.194],
    }))
  })

  it('resolves authored explode views into camera presets', () => {
    expect(resolveExplodeView(buildExplodeManifest(), 'torso_service_view')).toEqual(
      expect.objectContaining({
        id: 'torso_service_view',
        camera: expect.objectContaining({
          projection: 'orthographic',
          position: [1.15, 0.58, 0.72],
          target: [0.04, 0, 0.28],
        }),
      }),
    )
  })
})
