import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, afterEach } from 'vitest'

import { useAtom01AssemblyData } from '../useAtom01AssemblyData'

function readJsonFromPublic(relativePath: string) {
  const currentDir = dirname(fileURLToPath(import.meta.url))
  const absolutePath = resolve(currentDir, '../../../../../public', relativePath)
  return JSON.parse(readFileSync(absolutePath, 'utf-8')) as unknown
}

function HookProbe() {
  const { adapter, explodeManifest, isLoading, error } = useAtom01AssemblyData()

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

  it('loads the static atom01 assembly and explode manifests into a unified adapter', async () => {
    const assemblyManifest = readJsonFromPublic('models/robots/atom01/assembly_manifest.json')
    const explodeManifest = readJsonFromPublic('models/robots/atom01/explode_manifest.json')

    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input)
        const payload = url.endsWith('explode_manifest.json') ? explodeManifest : assemblyManifest
        return new Response(JSON.stringify(payload), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }),
    )

    render(<HookProbe />)

    await waitFor(() => {
      expect(screen.getByTestId('robot-id').textContent).toBe('atom01')
    })

    expect(screen.getByTestId('root-id').textContent).toBe('base_link')
    expect(screen.getByTestId('node-count').textContent).toBe('17')
    expect(screen.getByTestId('view-count').textContent).toBe('2')
  })
})
