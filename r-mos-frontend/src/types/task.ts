/**
 * Task 相关类型定义
 * 与后端 schemas/task.py 完全对齐 (V2.3)
 */

// 任务状态枚举 - 对齐后端 TaskStatus
export enum TaskStatus {
    PENDING = 'pending',
    IN_PROGRESS = 'in_progress',
    PAUSED = 'paused',
    COMPLETED = 'completed',
    FAILED = 'failed',
    TIMEOUT = 'timeout',
}

// 任务响应 - 对齐 TaskResponse
export interface Task {
    id: number
    title: string
    sop_id?: number                     // V2.3: 可为NULL（SOP删除后）
    user_id?: number
    status: TaskStatus
    current_step_index: number
    started_at?: string
    completed_at?: string
    paused_at?: string                  // V2.3新增
    time_limit?: number                 // 时间限制（秒）
    pass_score: number                  // 及格分数，默认70
    final_score?: number
    is_passed?: boolean
    created_at: string
    updated_at: string
}

// 任务详情（包含SOP信息）- 用于前端展示
export interface TaskWithSOP extends Task {
    sop?: {
        id: number
        name: string
        steps: Array<{
            step_index: number
            title: string
            description: string
            is_critical: boolean
        }>
    }
}

// 创建任务请求 - 对齐 TaskCreate
export interface TaskCreateRequest {
    title: string                       // 任务标题
    sop_id: number                      // SOP ID
    user_id?: number                    // 执行用户ID
    time_limit?: number                 // 时间限制（秒），最小60
    pass_score?: number                 // 及格分数，默认70
}

// 步骤执行请求 - 对齐 StepExecutionRequest
export interface StepExecutionRequest {
    step_index: number                  // 步骤索引（从1开始）
    action: string                      // 执行的操作
    parameters?: Record<string, any>    // 操作参数
    notes?: string                      // 备注
}

// 步骤执行响应 - 对齐 StepExecutionResponse（V2.3强制约束）
export interface StepExecutionResponse {
    task_id: number                     // 任务ID
    step_index: number                  // 已执行步骤索引
    status: 'success' | 'failed' | 'skipped' // 执行状态
    message: string                     // 执行结果消息
    snapshot_id?: number                // 快照ID（如已创建）
    next_step_index?: number            // 下一步骤索引（如未完成）
    is_task_completed: boolean          // 任务是否已完成
}

// 任务状态更新响应
export interface TaskStatusResponse {
    task_id: number
    status: TaskStatus
    message: string
}
