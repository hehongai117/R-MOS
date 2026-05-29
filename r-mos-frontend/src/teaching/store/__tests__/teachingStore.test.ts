/**
 * teachingStore 配置驱动测试
 * 验证 startAttempt 正确读取 scoringPolicy.pass_score 并传给 createTask
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Assignment, AssignmentAttempt } from '@/types/teaching'

// Mock API modules before importing the store
vi.mock('@/api/task', () => ({
  createTask: vi.fn(),
  startTask: vi.fn(),
}))

vi.mock('@/api/teaching', () => ({
  createAttempt: vi.fn(),
  getAttemptEvidence: vi.fn(),
  listAssignments: vi.fn(),
}))

import { createTask, startTask } from '@/api/task'
import { createAttempt, listAssignments } from '@/api/teaching'
import { useTeachingStore } from '../teachingStore'

const mockCreateTask = vi.mocked(createTask)
const mockStartTask = vi.mocked(startTask)
const mockCreateAttempt = vi.mocked(createAttempt)
const mockListAssignments = vi.mocked(listAssignments)

const makeAssignment = (overrides: Partial<Assignment> = {}): Assignment => ({
  id: 1,
  classId: 10,
  title: '减速器拆装实训',
  sopId: 42,
  scoringPolicy: null,
  ...overrides,
})

const makeAttempt = (overrides: Partial<AssignmentAttempt> = {}): AssignmentAttempt => ({
  id: 100,
  assignmentId: 1,
  studentId: 5,
  taskId: 200,
  status: 'in_progress',
  attemptIndex: 1,
  ...overrides,
})

beforeEach(() => {
  vi.clearAllMocks()
  // Reset store state between tests
  useTeachingStore.setState({
    assignments: [],
    currentAttempt: null,
    evidence: null,
    loading: false,
    error: null,
  })
})

describe('teachingStore.startAttempt', () => {
  it('使用 scoringPolicy.pass_score=85 时，createTask 收到 pass_score=85', async () => {
    const fakeTask = { id: 200 }
    const fakeAttempt = makeAttempt()

    mockCreateTask.mockResolvedValue(fakeTask as never)
    mockStartTask.mockResolvedValue(undefined as never)
    mockCreateAttempt.mockResolvedValue(fakeAttempt as never)

    const assignment = makeAssignment({ scoringPolicy: { pass_score: 85 } })

    const result = await useTeachingStore.getState().startAttempt(assignment, 5)

    expect(mockCreateTask).toHaveBeenCalledOnce()
    const callArg = mockCreateTask.mock.calls[0][0]
    expect(callArg.pass_score).toBe(85)
    expect(result).toEqual(fakeAttempt)
    expect(useTeachingStore.getState().currentAttempt).toEqual(fakeAttempt)
  })

  it('scoringPolicy 为 null 时，createTask 默认收到 pass_score=70', async () => {
    const fakeTask = { id: 201 }
    const fakeAttempt = makeAttempt({ taskId: 201 })

    mockCreateTask.mockResolvedValue(fakeTask as never)
    mockStartTask.mockResolvedValue(undefined as never)
    mockCreateAttempt.mockResolvedValue(fakeAttempt as never)

    const assignment = makeAssignment({ scoringPolicy: null })

    await useTeachingStore.getState().startAttempt(assignment, 5)

    expect(mockCreateTask).toHaveBeenCalledOnce()
    const callArg = mockCreateTask.mock.calls[0][0]
    expect(callArg.pass_score).toBe(70)
  })

  it('无 sopId 时抛出"作业未配置 SOP"错误', async () => {
    const assignment = makeAssignment({ sopId: null })

    await expect(
      useTeachingStore.getState().startAttempt(assignment, 5)
    ).rejects.toThrow('作业未配置 SOP，无法开始')

    expect(mockCreateTask).not.toHaveBeenCalled()
    // formatTeachingError 将原始错误包装为 '创建尝试失败' fallback 消息
    expect(useTeachingStore.getState().error).toBeTruthy()
  })

  it('createTask 正确收到 title、sop_id、user_id 字段', async () => {
    const fakeTask = { id: 202 }
    const fakeAttempt = makeAttempt()

    mockCreateTask.mockResolvedValue(fakeTask as never)
    mockStartTask.mockResolvedValue(undefined as never)
    mockCreateAttempt.mockResolvedValue(fakeAttempt as never)

    const assignment = makeAssignment({ sopId: 42, title: '减速器拆装实训', scoringPolicy: { pass_score: 90 } })

    await useTeachingStore.getState().startAttempt(assignment, 7)

    expect(mockCreateTask).toHaveBeenCalledWith({
      title: '减速器拆装实训-任务',
      sop_id: 42,
      user_id: 7,
      pass_score: 90,
    })
  })

  it('完成后 loading 状态归 false', async () => {
    const fakeTask = { id: 203 }
    const fakeAttempt = makeAttempt()

    mockCreateTask.mockResolvedValue(fakeTask as never)
    mockStartTask.mockResolvedValue(undefined as never)
    mockCreateAttempt.mockResolvedValue(fakeAttempt as never)

    const assignment = makeAssignment()

    await useTeachingStore.getState().startAttempt(assignment, 5)

    expect(useTeachingStore.getState().loading).toBe(false)
  })

  it('API 失败时 loading 归 false 且 error 有值', async () => {
    mockCreateTask.mockRejectedValue(new Error('网络错误') as never)

    const assignment = makeAssignment()

    await expect(
      useTeachingStore.getState().startAttempt(assignment, 5)
    ).rejects.toThrow()

    expect(useTeachingStore.getState().loading).toBe(false)
    expect(useTeachingStore.getState().error).toBeTruthy()
  })
})

describe('teachingStore.loadAssignments', () => {
  it('成功加载时 assignments 有值', async () => {
    const fakeAssignments = [makeAssignment({ id: 1 }), makeAssignment({ id: 2 })]
    mockListAssignments.mockResolvedValue(fakeAssignments as never)

    await useTeachingStore.getState().loadAssignments()

    expect(useTeachingStore.getState().assignments).toEqual(fakeAssignments)
    expect(useTeachingStore.getState().loading).toBe(false)
  })
})

describe('teachingStore.clearError', () => {
  it('清除 error 状态', () => {
    useTeachingStore.setState({ error: '测试错误' })
    useTeachingStore.getState().clearError()
    expect(useTeachingStore.getState().error).toBeNull()
  })
})
