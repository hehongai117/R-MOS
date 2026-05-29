import { apiClient } from './client'

export interface ChatMessagePayload {
  role: 'user' | 'assistant'
  content: string
}

export interface AIChatRequest {
  message: string
  sop_id?: number
  sop_title?: string
  current_step_index?: number
  current_step_description?: string
  fault_type?: string
  hint_level?: number
  history?: ChatMessagePayload[]
  robot_id?: number
}

export interface AIChatResponse {
  reply: string
  hint_level_used: number
}

export async function sendAIChat(request: AIChatRequest): Promise<AIChatResponse> {
  const res = await apiClient.post<AIChatResponse>('/ai-assistant/chat', request)
  return res.data
}
