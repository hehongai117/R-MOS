import { StrictMode } from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, afterEach } from 'vitest'

import { useAtom01AssemblyData } from '../useAtom01AssemblyData'

const MOCK_ASSEMBLY_MANIFEST = {
  version: '2026-03-13',
  robotId: '1',
  rootNodeId: 'base_link',
  mesh_catalog: {
    base_link_mesh: '/api/v1/robots/1/assets/models/base_link.glb',
  },
  nodes: [
    {
      id: 'base_link',
      parent_id: null,
      children: ['torso_link'],
      mesh_id: 'base_link_mesh',
      display_name: 'Base Link',
      category: 'link',
      link_name: null,
      transform: {
        translation: [0, 0, 0],
        rotation_quat: [0, 0, 0, 1],
        scale: [1, 1, 1],
      },
    },
    {
      id: 'torso_link',
      parent_id: 'base_link',
      children: [],
      mesh_id: null,
      display_name: 'Torso',
      category: 'link',
      link_name: null,
      transform: {
        translation: [0, 0, 0.067],
        rotation_quat: [0, 0, 0, 1],
        scale: [1, 1, 1],
      },
    },
  ],
  fastener_instances: [],
}

const MOCK_EXPLODE_MANIFEST = {
  version: '2026-04-30',
  robotId: '1',
  views: [
    {
      id: 'torso_open',
      focus_node_id: 'torso_link',
      camera: {
        projection: 'orthographic',
        position: [1.15, 0.58, 0.72],
        target: [0.04, 0, 0.28],
      },
    },
    {
      id: 'full_explode',
      focus_node_id: 'base_link',
      camera: {
        projection: 'perspective',
        position: [1.5, 1, 1.5],
        target: [0, 0.3, 0],
      },
    },
  ],
  sequences: [
    {
      id: 'torso_cover_removal',
      step_index: 1,
      node_ids: ['torso_link'],
      direction: [0, 0, 1],
      distance: 0.18,
      anchor_node_id: 'base_link',
    },
  ],
}

function HookProbe() {
  const { adapter, explodeManifest, isLoading, error } = useAtom01AssemblyData(true, '1')

  if (isLoading) {
    return <div>loading</div>
  }

  if (error) {
    return <div>{error.message}</div>
  }

  return (
    <div>
      <span data-testid="robot-id">{adapter?.robotId}</span>
      <span data-testid="root-id">{adapter?.tree.rootNodeIds.join(',')}</span>
      <span data-testid="node-count">{Object.keys(adapter?.tree.nodes ?? {}).length}</span>
      <span data-testid="view-count">{explodeManifest?.views.length ?? 0}</span>
    </div>
  )
}

function ToggleProbe({ enabled }: { enabled: boolean }) {
  const { adapter, explodeManifest, isLoading, error } = useAtom01AssemblyData(enabled, '1')

  if (isLoading) {
    return <div>loading</div>
  }

  if (error) {
    return <div>{error.message}</div>
  }

  return (
    <div>
      <span data-testid="robot-id">{adapter?.robotId}</span>
      <span data-testid="root-id">{adapter?.tree.rootNodeIds.join(',')}</span>
      <span data-testid="node-count">{Object.keys(adapter?.tree.nodes ?? {}).length}</span>
      <span data-testid="view-count">{explodeManifest?.views.length ?? 0}</span>
    </div>
  )
}

describe('useAtom01AssemblyData', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('loads the robot assembly and explode manifests into a unified adapter', async () => {
    const requestCounts = new Map<string, number>()

    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        const nextCount = (requestCounts.get(url) ?? 0) + 1
        requestCounts.set(url, nextCount)
        const payload = url.endsWith('explode_manifest.json') ? MOCK_EXPLODE_MANIFEST : MOCK_ASSEMBLY_MANIFEST

        if (nextCount > 1 && init?.cache !== 'no-store') {
          return new Response(null, { status: 304 })
        }

        return new Response(JSON.stringify(payload), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }),
    )

    render(
      <StrictMode>
        <HookProbe />
      </StrictMode>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('robot-id').textContent).toBe('1')
    })

    expect(screen.getByTestId('root-id').textContent).toBe('base_link')
    expect(screen.getByTestId('node-count').textContent).toBe('2')
    expect(screen.getByTestId('view-count').textContent).toBe('2')
    expect(fetch).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/v1\/robots\/1\/assets\/.*assembly_manifest\.json/),
      expect.objectContaining({ cache: 'no-store' }),
    )
  })

  it('loads manifests when enabled flips from false to true', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input)
        const payload = url.endsWith('explode_manifest.json') ? MOCK_EXPLODE_MANIFEST : MOCK_ASSEMBLY_MANIFEST
        return new Response(JSON.stringify(payload), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }),
    )

    const { rerender } = render(<ToggleProbe enabled={false} />)

    expect(screen.getByTestId('robot-id').textContent).toBe('')

    rerender(<ToggleProbe enabled />)

    await waitFor(() => {
      expect(screen.getByTestId('robot-id').textContent).toBe('1')
    })
  })
})
