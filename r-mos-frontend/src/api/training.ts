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

export interface TrainingWorkbenchDraftPayload {
  robotModel: string
  taskSummary: string
  focusPrompt: string
}

export interface TrainingWorkbenchDraftResponse {
  project: {
    sessionId: string
    projectId: string
    title: string
    progressPercent: number
  }
  steps: Array<{
    id: string
    title: string
    status: 'pending' | 'active' | 'passed' | 'failed'
    instruction: string
    evidenceHint?: string
    tools: Array<{
      id: string
      name: string
      spec?: string
      isCritical?: boolean
      recommendation?: string
    }>
  }>
  messages: Array<{
    id: string
    role: 'assistant' | 'teacher' | 'user'
    content: string
    createdAt: string
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

export async function generateTrainingWorkbenchDraft(
  payload: TrainingWorkbenchDraftPayload,
): Promise<TrainingWorkbenchDraftResponse> {
  const response = await apiClient.post('/training/workbench/draft', {
    robot_model: payload.robotModel,
    task_summary: payload.taskSummary,
    focus_prompt: payload.focusPrompt,
  }, {
    timeout: 90000,
  })

  return {
    project: {
      sessionId: response.data.project.session_id,
      projectId: response.data.project.project_id,
      title: response.data.project.title,
      progressPercent: response.data.project.progress_percent,
    },
    steps: response.data.steps.map((step: Record<string, unknown>) => ({
      id: String(step.id),
      title: String(step.title),
      status: step.status as 'pending' | 'active' | 'passed' | 'failed',
      instruction: String(step.instruction),
      evidenceHint: typeof step.evidence_hint === 'string' ? step.evidence_hint : undefined,
      tools: Array.isArray(step.tools)
        ? step.tools.map((tool) => {
            const toolRecord = tool as Record<string, unknown>
            return {
              id: String(toolRecord.id),
              name: String(toolRecord.name),
              spec: typeof toolRecord.spec === 'string' ? toolRecord.spec : undefined,
              isCritical: Boolean(toolRecord.is_critical),
              recommendation:
                typeof toolRecord.recommendation === 'string' ? toolRecord.recommendation : undefined,
            }
          })
        : [],
    })),
    messages: response.data.messages.map((message: Record<string, unknown>) => ({
      id: String(message.id),
      role: message.role as 'assistant' | 'teacher' | 'user',
      content: String(message.content),
      createdAt: String(message.created_at),
    })),
  }
}
