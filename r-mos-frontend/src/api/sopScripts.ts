import apiClient from '@/api/client'
import type { SOPScriptAdjudication } from '@/adjudication/types/adjudication'

interface SOPAdjudicationListResponse {
  total: number
  items: SOPScriptAdjudication[]
}

export async function fetchAdjudicationSOPs(params?: {
  robot_model_id?: number
  applicable_model?: string
  category?: string
}): Promise<SOPScriptAdjudication[]> {
  const response = await apiClient.get<SOPAdjudicationListResponse>(
    '/sops/adjudication',
    { params },
  )
  return response.data.items
}
