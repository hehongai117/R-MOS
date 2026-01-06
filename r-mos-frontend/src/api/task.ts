/**
 * Task API 模块
 * 与后端 /tasks/* 端点对接 (V2.3)
 */
import { apiClient } from './client'
import {
    Task,
    TaskCreateRequest,
    StepExecutionRequest,
    StepExecutionResponse,
} from '@/types/task'
import { TaskReport } from '@/types/report'

/**
 * 创建任务
 */
export async function createTask(data: TaskCreateRequest): Promise<Task> {
    const response = await apiClient.post<Task>('/tasks', data)
    return response.data
}

/**
 * 获取任务详情
 */
export async function getTask(taskId: number): Promise<Task> {
    const response = await apiClient.get<Task>(`/tasks/${taskId}`)
    return response.data
}

/**
 * 开始任务
 * 将任务状态从 PENDING 变为 IN_PROGRESS
 */
export async function startTask(taskId: number): Promise<Task> {
    const response = await apiClient.post<Task>(`/tasks/${taskId}/start`)
    return response.data
}

/**
 * 执行步骤（核心 API）
 * 
 * @param taskId 任务 ID
 * @param data 步骤执行请求，包含 step_index, action, parameters
 * @returns 执行结果，包含 is_task_completed 和 next_step_index
 */
export async function executeStep(
    taskId: number,
    data: StepExecutionRequest
): Promise<StepExecutionResponse> {
    const response = await apiClient.post<StepExecutionResponse>(
        `/tasks/${taskId}/step`,  // 修正端点路径
        data
    )
    return response.data
}

/**
 * 暂停任务
 */
export async function pauseTask(taskId: number): Promise<Task> {
    const response = await apiClient.post<Task>(`/tasks/${taskId}/pause`)
    return response.data
}

/**
 * 恢复任务
 */
export async function resumeTask(taskId: number): Promise<Task> {
    const response = await apiClient.post<Task>(`/tasks/${taskId}/resume`)
    return response.data
}

/**
 * 获取任务报告
 * 
 * 注意：只有已完成的任务(status=COMPLETED)才能获取报告
 */
export async function getTaskReport(taskId: number): Promise<TaskReport> {
    const response = await apiClient.get<TaskReport>(`/tasks/${taskId}/report`)
    return response.data
}

/**
 * 获取任务列表（可选，如后端支持）
 */
export async function listTasks(params: {
    status?: string
    skip?: number
    limit?: number
} = {}): Promise<Task[]> {
    const response = await apiClient.get<Task[]>('/tasks', { params })
    return response.data
}
