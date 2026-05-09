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
  robotModelId?: number,
): Promise<ScenarioListResponse> {
  const params: Record<string, string | number> = {}
  if (difficulty && difficulty !== 'all') params.difficulty = difficulty
  if (robotModelId) params.robot_model_id = robotModelId
  const res = await apiClient.get<ScenarioListResponse>('/scenarios', { params })
  return res.data
}
