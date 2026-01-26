/**
 * 教学域状态管理
 */
import { create } from 'zustand'
import type { Assignment, AssignmentAttempt, AttemptEvidenceResponse } from '@/types/teaching'
import { createTask, startTask } from '@/api/task'
import {
  createAttempt,
  getAttemptEvidence,
  listAssignments,
} from '@/api/teaching'
import type { TaskCreateRequest } from '@/types/task'
import { formatTeachingError } from '@/teaching/utils/api'

interface TeachingStoreState {
  assignments: Assignment[]
  currentAttempt: AssignmentAttempt | null
  evidence: AttemptEvidenceResponse | null
  loading: boolean
  error: string | null
  loadAssignments: () => Promise<void>
  startAttempt: (assignment: Assignment, studentId: number) => Promise<AssignmentAttempt | null>
  fetchEvidence: (attemptId: number) => Promise<AttemptEvidenceResponse | null>
  clearError: () => void
}

export const useTeachingStore = create<TeachingStoreState>((set) => ({
  assignments: [],
  currentAttempt: null,
  evidence: null,
  loading: false,
  error: null,
  loadAssignments: async () => {
    set({ loading: true, error: null })
    try {
      const data = await listAssignments()
      set({ assignments: data })
    } catch (error: any) {
      const message = formatTeachingError(error, '加载作业失败')
      set({ error: message })
      throw error
    } finally {
      set({ loading: false })
    }
  },
  startAttempt: async (assignment, studentId) => {
    set({ loading: true, error: null })
    try {
      if (!assignment.sopId) {
        throw new Error('作业未配置 SOP，无法开始')
      }
      const taskPayload: TaskCreateRequest = {
        title: `${assignment.title}-任务`,
        sop_id: assignment.sopId,
        user_id: studentId,
        pass_score: 70,
      }
      const task = await createTask(taskPayload)
      await startTask(task.id)
      const attempt = await createAttempt(assignment.id, studentId, task.id)
      set({ currentAttempt: attempt })
      return attempt
    } catch (error: any) {
      const message = formatTeachingError(error, '创建尝试失败')
      set({ error: message })
      throw error
    } finally {
      set({ loading: false })
    }
  },
  fetchEvidence: async (attemptId) => {
    set({ loading: true, error: null })
    try {
      const data = await getAttemptEvidence(attemptId)
      set({ evidence: data })
      return data
    } catch (error: any) {
      const message = formatTeachingError(error, '获取证据失败')
      set({ error: message })
      throw error
    } finally {
      set({ loading: false })
    }
  },
  clearError: () => set({ error: null }),
}))
