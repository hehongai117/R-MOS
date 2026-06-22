import { apiClient } from './client'

export interface DiagnoseRequest {
  telemetry: Record<string, unknown>
  fault_type_hint?: string
}

export interface DiagnoseResponse {
  success: boolean
  fault_type: string | null
  confidence: number
  affected_joints: string[]
  reasoning: string
  recommended_sop: string | null
  is_compound: boolean
  llm_enhanced: boolean
}

export interface CreateTaskRequest {
  diagnosis_trace_id: string
  fault_type: string
  student_id: number
}

export interface CreateTaskResponse {
  task_id: number
  execution_id: number
  sop_id: number | null
  sop_name: string
  fault_type: string
}

export interface StepCompleteRequest {
  step_index: number
  evidence_type?: string
  evidence_value?: Record<string, unknown>
  duration_seconds?: number
}

export interface StepCompleteResponse {
  step_index: number
  is_compliant: boolean
  feedback: string | null
}

export interface TaskCompleteResponse {
  execution_id: number
  task_id: number
  status: string
  report_generation: string
}

export async function diagnoseFault(data: DiagnoseRequest): Promise<DiagnoseResponse> {
  const res = await apiClient.post<DiagnoseResponse>('/pipeline/diagnose', data)
  return res.data
}

export async function createTaskFromDiagnosis(data: CreateTaskRequest): Promise<CreateTaskResponse> {
  const res = await apiClient.post<CreateTaskResponse>('/pipeline/tasks/from-diagnosis', data)
  return res.data
}

export async function completeStep(executionId: number, data: StepCompleteRequest): Promise<StepCompleteResponse> {
  const res = await apiClient.post<StepCompleteResponse>(`/pipeline/executions/${executionId}/steps/complete`, data)
  return res.data
}

export async function completeTask(executionId: number): Promise<TaskCompleteResponse> {
  const res = await apiClient.post<TaskCompleteResponse>(`/pipeline/executions/${executionId}/complete`)
  return res.data
}
