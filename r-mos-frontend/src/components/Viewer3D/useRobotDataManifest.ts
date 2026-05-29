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
