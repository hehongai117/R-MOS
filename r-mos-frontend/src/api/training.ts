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
  project_snapshot?: {
    title?: string
    summary?: string
    robot_model?: string
    task_summary?: string
    focus_prompt?: string
    seed_messages?: Array<{
      id?: string
      role?: 'assistant' | 'teacher' | 'user'
      content?: string
      created_at?: string
    }>
    steps?: Array<{
      id: string
      step_index: number
      title: string
      instruction: string
      evidence_hint?: string
      model_targets?: string[]
      tools?: Array<{
        id: string
        name: string
        spec?: string
        is_critical?: boolean
        recommendation?: string
      }>
    }>
  } | null
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
    tools_confirmed?: Array<{
      tool_id: string
      status: 'PENDING' | 'CONFIRMED' | 'ANOMALY'
    }> | null
    evidence?: {
      bundle_id?: string | null
      note?: string | null
    } | null
    verdict_result?: {
      result: 'PASS' | 'FAIL'
      summary: string
      details?: string
      missing_critical_tools?: string[]
      anomaly_tools?: string[]
      evidence_bundle_id?: string | null
    } | null
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
    stepIndex: number
    title: string
    status: 'pending' | 'active' | 'passed' | 'failed'
    instruction: string
    evidenceHint?: string
    modelTargets?: string[]
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

export interface TrainingWorkbenchEvidenceUploadResponse {
  evidenceBundleId: string
  filename: string
  contentUri: string
  humanSummary?: string
}

export interface TrainingWorkbenchToolConfirmPayload {
  toolId: string
  status: 'PENDING' | 'CONFIRMED' | 'ANOMALY'
}

export interface TrainingWorkbenchStepSubmitPayload {
  stepIndex: number
  note: string
  evidenceBundleId?: string | null
  toolsConfirmed: TrainingWorkbenchToolConfirmPayload[]
}

export interface TrainingWorkbenchStepSubmitResponse {
  recordId: string
  status: 'pass' | 'fail'
  evidenceBundleId?: string | null
  nextStepId?: string | null
  sessionSubmitted: boolean
  feedback?: {
    submissionId?: string
    score?: number | null
  } | null
  verdict: {
    result: 'PASS' | 'FAIL'
    summary: string
    details?: string
    missingCriticalTools?: string[]
    anomalyTools?: string[]
    evidenceBundleId?: string | null
  }
}

export interface TrainingWorkbenchAssistantMessage {
  id: string
  role: 'assistant' | 'teacher' | 'user'
  content: string
  createdAt: string
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
      stepIndex: Number(step.step_index ?? 0),
      title: String(step.title),
      status: step.status as 'pending' | 'active' | 'passed' | 'failed',
      instruction: String(step.instruction),
      evidenceHint: typeof step.evidence_hint === 'string' ? step.evidence_hint : undefined,
      modelTargets: Array.isArray(step.model_targets)
        ? step.model_targets
            .filter((value): value is string => typeof value === 'string')
        : [],
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

export async function uploadTrainingWorkbenchEvidence(
  sessionId: string,
  stepId: string,
  note: string,
  file: File,
): Promise<TrainingWorkbenchEvidenceUploadResponse> {
  const formData = new FormData()
  formData.append('session_id', sessionId)
  formData.append('step_id', stepId)
  formData.append('note', note)
  formData.append('file', file)

  const response = await apiClient.post('/training/workbench/evidence', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 90000,
  })

  return {
    evidenceBundleId: String(response.data.evidence_bundle_id),
    filename: String(response.data.filename),
    contentUri: String(response.data.content_uri),
    humanSummary:
      typeof response.data.human_summary === 'string' ? response.data.human_summary : undefined,
  }
}

export async function submitTrainingWorkbenchStep(
  sessionId: string,
  stepId: string,
  payload: TrainingWorkbenchStepSubmitPayload,
): Promise<TrainingWorkbenchStepSubmitResponse> {
  const response = await apiClient.post(
    `/training/workbench/sessions/${sessionId}/steps/${stepId}/submit`,
    {
      step_index: payload.stepIndex,
      note: payload.note,
      evidence_bundle_id: payload.evidenceBundleId ?? null,
      tools_confirmed: payload.toolsConfirmed.map((tool) => ({
        tool_id: tool.toolId,
        status: tool.status,
      })),
    },
    {
      timeout: 90000,
    },
  )

  return {
    recordId: String(response.data.record_id),
    status: response.data.status as 'pass' | 'fail',
    evidenceBundleId:
      typeof response.data.evidence_bundle_id === 'string' ? response.data.evidence_bundle_id : null,
    nextStepId: typeof response.data.next_step_id === 'string' ? response.data.next_step_id : null,
    sessionSubmitted: Boolean(response.data.session_submitted),
    feedback: response.data.feedback
      ? {
          submissionId:
            typeof response.data.feedback.submission_id === 'string'
              ? response.data.feedback.submission_id
              : undefined,
          score:
            typeof response.data.feedback.score === 'number' ? response.data.feedback.score : null,
        }
      : null,
    verdict: {
      result: response.data.verdict.result as 'PASS' | 'FAIL',
      summary: String(response.data.verdict.summary),
      details:
        typeof response.data.verdict.details === 'string' ? response.data.verdict.details : undefined,
      missingCriticalTools: Array.isArray(response.data.verdict.missing_critical_tools)
        ? response.data.verdict.missing_critical_tools
            .filter((value: unknown): value is string => typeof value === 'string')
        : [],
      anomalyTools: Array.isArray(response.data.verdict.anomaly_tools)
        ? response.data.verdict.anomaly_tools
            .filter((value: unknown): value is string => typeof value === 'string')
        : [],
      evidenceBundleId:
        typeof response.data.verdict.evidence_bundle_id === 'string'
          ? response.data.verdict.evidence_bundle_id
          : undefined,
    },
  }
}

export async function askTrainingWorkbenchAssistant(payload: {
  sessionId: string
  stepId: string
  question: string
  messages: Array<{
    role: 'assistant' | 'teacher' | 'user'
    content: string
  }>
}): Promise<TrainingWorkbenchAssistantMessage> {
  const response = await apiClient.post(
    '/training/workbench/ask',
    {
      session_id: payload.sessionId,
      step_id: payload.stepId,
      question: payload.question,
      messages: payload.messages,
    },
    {
      timeout: 90000,
    },
  )

  return {
    id: String(response.data.id),
    role: response.data.role as 'assistant' | 'teacher' | 'user',
    content: String(response.data.content),
    createdAt: String(response.data.created_at),
  }
}
