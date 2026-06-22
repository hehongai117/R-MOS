/**
 * SOP 相关类型定义
 * 与后端 schemas/sop.py 完全对齐 (V2.3)
 */

// SOP步骤类型 - 对齐 SOPStepResponse
export interface SOPStep {
    id: number                          // 步骤ID
    sop_id: number                      // 所属SOP ID
    step_index: number                  // 步骤索引（从1开始）
    title: string                       // 步骤标题
    description: string                 // 步骤详细描述
    target_part?: string                // 目标部件ID
    expected_action: string             // 期望操作类型
    action_params?: Record<string, any> // 操作参数
    validation_rules?: Record<string, any> // 验证规则
    is_critical: boolean                // 是否为关键步骤
    timeout_seconds: number             // 超时时长（秒），默认300
    allow_skip: boolean                 // 是否允许跳过
    hints?: string[]                    // 提示信息
    tools_required?: string[]           // 所需工具
    created_at: string                  // 创建时间
    updated_at: string                  // 更新时间
}

// SOP基础类型 - 对齐 SOPBase
export interface SOPBase {
    name: string                        // SOP名称
    description?: string                // SOP描述
    applicable_model: string            // 适用机器人型号
    category?: string                   // 分类
    difficulty_level: 'low' | 'medium' | 'high' // 难度等级
    estimated_time?: number             // 预估时长（秒）
}

// 完整SOP响应 - 对齐 SOPResponse
export interface SOP extends SOPBase {
    id: number
    created_at: string
    updated_at: string
    steps: SOPStep[]
}

// SOP列表项 - 对齐 SOPListItem（简化，不含完整steps）
export interface SOPListItem {
    id: number
    name: string
    category?: string
    difficulty_level: 'low' | 'medium' | 'high'
    step_count: number                  // 步骤数量
    estimated_time?: number
    created_at: string
}

// SOP列表响应 - 对齐 SOPListResponse
export interface SOPListResponse {
    total: number
    items: SOPListItem[]
}

// SOP创建请求 - 对齐 SOPCreate
export interface SOPCreateRequest extends SOPBase {
    robot_model_id?: number
    steps: Omit<SOPStep, 'id' | 'sop_id' | 'created_at' | 'updated_at'>[]
}

// SOP更新请求 - 对齐 SOPUpdate
export interface SOPUpdateRequest {
    name?: string
    description?: string
    category?: string
    difficulty_level?: 'low' | 'medium' | 'high'
    estimated_time?: number
}

// SOP删除警告响应 - 对齐 SOPDeleteWarning
export interface SOPDeleteWarning {
    can_delete: boolean
    warning_type: string
    message: string
    affected_tasks: Array<{
        task_id: number
        title: string
        status: string
    }>
    force_required: boolean
}

// SOP删除成功响应 - 对齐 SOPDeleteResponse
export interface SOPDeleteResponse {
    success: boolean
    message: string
    deleted_sop_id: number
    affected_task_count: number
}
