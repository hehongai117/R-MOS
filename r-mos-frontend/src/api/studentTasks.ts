import { apiClient } from './client'

export interface StudentTaskItem {
  id: number
  task_id: number
  task_name: string
  sop_name: string | null
  fault_type: string | null
  status: 'in_progress' | 'completed' | 'abandoned'
  started_at: string
  completed_at: string | null
}

export interface StudentTaskListResponse {
  items: StudentTaskItem[]
  total: number
  pending_count: number
  in_progress_count: number
  completed_count: number
}

export async function fetchStudentTasks(
  studentId: number,
  status?: string,
): Promise<StudentTaskListResponse> {
  const params: Record<string, unknown> = { student_id: studentId, limit: 50 }
  if (status) params.status = status
  const res = await apiClient.get<StudentTaskListResponse>('/student/tasks', { params })
  return res.data
}
