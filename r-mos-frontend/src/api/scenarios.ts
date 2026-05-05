import { apiClient } from './client'

export interface ScenarioItem {
  id: number
  fault_type: string
  sop_id: number
  sop_title: string | null
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  priority: number
}

export interface ScenarioListResponse {
  items: ScenarioItem[]
  total: number
}

export async function fetchScenarios(
  difficulty?: string,
): Promise<ScenarioListResponse> {
  const params: Record<string, string> = {}
  if (difficulty && difficulty !== 'all') params.difficulty = difficulty
  const res = await apiClient.get<ScenarioListResponse>('/scenarios', { params })
  return res.data
}
