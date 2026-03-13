import { useEffect, useState } from 'react'

import { getRobotModelBase } from '@/config/robots'
import {
  buildAssemblyIndex,
  parseAssemblyManifest,
  parseExplodeManifest,
  type AssemblyFastenerInstance,
  type AssemblyManifest,
  type AssemblyTransform,
  type ExplodeManifest,
} from '@/components/Viewer3D/assemblyManifest'
import type { ViewerTreeAdapter } from '@/components/Viewer3D/runtimeManifest'

const ATOM01_MODEL_BASE = getRobotModelBase('atom01')

export interface Atom01AssemblyAdapter {
  robotId: string
  label: string
  tree: ViewerTreeAdapter
  meshCatalog: Record<string, string>
  transforms: Record<string, AssemblyTransform>
  fastenerInstances: AssemblyFastenerInstance[]
  assetUrls: string[]
}

export interface UseAtom01AssemblyDataResult {
  adapter: Atom01AssemblyAdapter | null
  explodeManifest: ExplodeManifest | null
  isLoading: boolean
  error: Error | null
}

async function fetchJson(url: string): Promise<unknown> {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`failed to load ${url}: ${response.status}`)
  }
  return response.json()
}

export function createStaticAssemblyAdapter(manifest: AssemblyManifest): Atom01AssemblyAdapter {
  const index = buildAssemblyIndex(manifest)
  const transforms = Object.fromEntries([
    ...manifest.nodes.map((node) => [node.id, node.transform] as const),
    ...manifest.fastener_instances.map((instance) => [instance.id, instance.transform] as const),
  ])
  return {
    robotId: manifest.robotId,
    label: manifest.robotId.toUpperCase(),
    tree: {
      rootNodeIds: [manifest.rootNodeId],
      nodes: Object.fromEntries(
        manifest.nodes.map((node) => [
          node.id,
          {
            id: node.id,
            displayName: node.display_name,
            parentId: node.parent_id,
            children: index.childrenByParent[node.id] ?? [],
            runtimeAssetPaths: node.mesh_id ? [manifest.mesh_catalog[node.mesh_id]].filter(Boolean) as string[] : [],
            sourcePaths: [],
            fileKinds: [node.category],
          },
        ]),
      ),
    },
    meshCatalog: manifest.mesh_catalog,
    transforms,
    fastenerInstances: manifest.fastener_instances,
    assetUrls: Object.values(manifest.mesh_catalog),
  }
}

export function useAtom01AssemblyData(enabled = true): UseAtom01AssemblyDataResult {
  const [adapter, setAdapter] = useState<Atom01AssemblyAdapter | null>(null)
  const [explodeManifest, setExplodeManifest] = useState<ExplodeManifest | null>(null)
  const [isLoading, setIsLoading] = useState(enabled)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    let disposed = false

    if (!enabled) {
      setAdapter(null)
      setExplodeManifest(null)
      setError(null)
      setIsLoading(false)
      return () => {
        disposed = true
      }
    }

    async function load() {
      setIsLoading(true)
      setError(null)

      try {
        const [assemblyRaw, explodeRaw] = await Promise.all([
          fetchJson(`${ATOM01_MODEL_BASE}/assembly_manifest.json`),
          fetchJson(`${ATOM01_MODEL_BASE}/explode_manifest.json`),
        ])

        if (disposed) return

        const assemblyManifest = parseAssemblyManifest(assemblyRaw)
        const parsedExplodeManifest = parseExplodeManifest(explodeRaw)

        setAdapter(createStaticAssemblyAdapter(assemblyManifest))
        setExplodeManifest(parsedExplodeManifest)
      } catch (cause) {
        if (!disposed) {
          setError(cause instanceof Error ? cause : new Error('failed to load atom01 assembly data'))
        }
      } finally {
        if (!disposed) {
          setIsLoading(false)
        }
      }
    }

    void load()

    return () => {
      disposed = true
    }
  }, [])

  return {
    adapter,
    explodeManifest,
    isLoading,
    error,
  }
}
