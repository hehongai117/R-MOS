import { apiClient } from './client'

export interface SkillProfileResponse {
  user_id: number
  overall_level: number
  total_sessions: number
  total_duration: number
  last_trained_at?: string | null
  score_safety?: number | null
  score_procedure?: number | null
  score_precision?: number | null
  score_efficiency?: number | null
  score_tools?: number | null
  cert_l1_passed: boolean
  cert_l2_passed: boolean
  cert_l3_eligible: boolean
}

export interface WeakStepResponse {
  step_id: string
  sop_id?: string | null
  fail_count: number
  last_failed_at?: string | null
  fail_tags?: string[] | null
  is_resolved: boolean
}

export interface SessionResponse {
  session_id: string
  project_id: string
  user_id: number
  status: string
  current_step: number
  score?: number | null
  total_duration: number
  submit_type?: string | null
  started_at: string
  paused_at?: string | null
  submitted_at?: string | null
}

export interface SessionDetailResponse {
  session: SessionResponse
  steps: Array<{
    record_id: string
    session_id: string
    step_id: string
    step_index: number
    status: string
    attempt_count: number
    duration_sec?: number | null
  }>
}

export async function getStudentProfile(userId: number) {
  const response = await apiClient.get<SkillProfileResponse>(`/students/${userId}/profile`)
  return response.data
}

export async function getWeakSteps(userId: number) {
  const response = await apiClient.get<WeakStepResponse[]>(`/students/${userId}/weak-steps`)
  return response.data
}

export async function getTrainingSessions(userId: number) {
  const response = await apiClient.get<SessionResponse[]>(`/training/users/${userId}/sessions`)
  return response.data
}

export async function getActiveTrainingSession(userId: number) {
  const response = await apiClient.get<SessionResponse>(`/training/users/${userId}/active-session`)
  return response.data
}

export async function getTrainingSessionDetail(sessionId: string) {
  const response = await apiClient.get<SessionDetailResponse>(`/training/sessions/${sessionId}/detail`)
  return response.data
}
