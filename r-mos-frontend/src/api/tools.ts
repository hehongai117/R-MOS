import apiClient from '@/api/client'

export interface RobotTool {
  tool_id: string
  display_name: string
  category: string
  specs?: Record<string, string>
}

export async function fetchRobotTools(robotId: number): Promise<RobotTool[]> {
  const response = await apiClient.get<{ robot_id: number; tools: RobotTool[] }>(
    `/robots/${robotId}/tools`,
  )
  return response.data.tools
}
