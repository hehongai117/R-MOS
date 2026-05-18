import { useEffect, useState } from 'react'
import { fetchAdjudicationSOPs } from '@/api/sopScripts'
import type { SOPScriptAdjudication } from '@/adjudication/types/adjudication'
import { ALL_SOP_SCRIPTS } from '@/data/sopScripts'

export function useSOPScripts(robotModelId?: number | null) {
  const [scripts, setScripts] = useState<SOPScriptAdjudication[]>(ALL_SOP_SCRIPTS)
  const [loading, setLoading] = useState(false)
  const [fromApi, setFromApi] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)

    fetchAdjudicationSOPs(
      robotModelId ? { robot_model_id: robotModelId } : undefined,
    )
      .then((items) => {
        if (!cancelled && items.length > 0) {
          setScripts(items)
          setFromApi(true)
        }
      })
      .catch(() => { /* API unavailable, keep local fallback */ })
      .finally(() => { if (!cancelled) setLoading(false) })

    return () => { cancelled = true }
  }, [robotModelId])

  return { scripts, loading, fromApi }
}
