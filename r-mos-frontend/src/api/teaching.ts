/**
 * 教学域接口模块
 */
import { apiClient } from './client'
import type {
  Assignment,
  AssignmentAttempt,
  AttemptEvidenceResponse,
  AttemptStatus,
  DiagnosisReport,
  Enrollment,
  TeachingClass,
} from '@/types/teaching'

export async function listClasses(): Promise<TeachingClass[]> {
  const response = await apiClient.get<TeachingClass[]>('/classes')
  return response.data
}

export async function listEnrollments(classId?: number): Promise<Enrollment[]> {
  const response = await apiClient.get<Enrollment[]>('/enrollments', {
    params: classId ? { class_id: classId } : undefined,
  })
  return response.data
}

export async function listAssignments(classId?: number): Promise<Assignment[]> {
  const response = await apiClient.get<Assignment[]>('/assignments', {
    params: classId ? { class_id: classId } : undefined,
  })
  return response.data
}

export async function getAssignment(assignmentId: number): Promise<Assignment> {
  const response = await apiClient.get<Assignment>(`/assignments/${assignmentId}`)
  return response.data
}

export async function listAssignmentAttempts(assignmentId: number): Promise<AssignmentAttempt[]> {
  const response = await apiClient.get<AssignmentAttempt[]>(`/assignments/${assignmentId}/attempts`)
  return response.data
}

export async function createAttempt(
  assignmentId: number,
  studentId: number,
  taskId?: number | null
): Promise<AssignmentAttempt> {
  const response = await apiClient.post<AssignmentAttempt>(
    `/assignments/${assignmentId}/attempts`,
    {
      studentId,
      taskId: taskId ?? null,
    }
  )
  return response.data
}

export async function getAttempt(attemptId: number): Promise<AssignmentAttempt> {
  const response = await apiClient.get<AssignmentAttempt>(`/attempts/${attemptId}`)
  return response.data
}

export async function updateAttemptStatus(
  attemptId: number,
  status: AttemptStatus
): Promise<AssignmentAttempt> {
  const response = await apiClient.patch<AssignmentAttempt>(`/attempts/${attemptId}`, {
    status,
  })
  return response.data
}

export async function gradeAttempt(
  attemptId: number,
  score: number
): Promise<AssignmentAttempt> {
  const response = await apiClient.post<AssignmentAttempt>(`/attempts/${attemptId}/grade`, {
    score,
  })
  return response.data
}

export async function getAttemptEvidence(attemptId: number): Promise<AttemptEvidenceResponse> {
  const response = await apiClient.get<AttemptEvidenceResponse>(`/attempts/${attemptId}/evidence`)
  return response.data
}

export async function getAttemptDiagnosis(attemptId: number): Promise<DiagnosisReport> {
  const response = await apiClient.get<DiagnosisReport>(`/attempts/${attemptId}/diagnosis`)
  return response.data
}
