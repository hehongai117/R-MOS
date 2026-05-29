import { useEffect, useState } from 'react'
import { fetchAdjudicationSOPs } from '@/api/sopScripts'
import type { SOPScriptAdjudication } from '@/adjudication/types/adjudication'

export function useSOPScripts(robotModelId?: number | null) {
  const [scripts, setScripts] = useState<SOPScriptAdjudication[]>([])
  const [loading, setLoading] = useState(true)
  const [fromApi, setFromApi] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)

    fetchAdjudicationSOPs(
      robotModelId ? { robot_model_id: robotModelId } : undefined,
    )
      .then((items) => {
        if (!cancelled) {
          setScripts(items)
          setFromApi(true)
        }
      })
      .catch(() => {
        if (!cancelled) setScripts([])
      })
      .finally(() => { if (!cancelled) setLoading(false) })

    return () => { cancelled = true }
  }, [robotModelId])

  return { scripts, loading, fromApi }
}
