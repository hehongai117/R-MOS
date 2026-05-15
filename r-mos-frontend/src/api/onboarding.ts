import { apiClient } from './client'

export interface RobotOption {
  id: number
  brand: string
  model_name: string
  description: string | null
  thumbnail_path: string | null
}

/** 获取可选机器人列表 */
export async function listAvailableRobots(): Promise<RobotOption[]> {
  const res = await apiClient.get('/onboarding/robots')
  return res.data.items
}

/** 教师选择机器人 */
export async function selectRobots(robotIds: number[]): Promise<{ message: string; bound_count: number }> {
  const res = await apiClient.post('/onboarding/robots', { robot_ids: robotIds })
  return res.data
}
