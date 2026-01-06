/**
 * Fault (故障案例) 相关类型定义
 * 与后端 schemas/fault.py 完全对齐 (V2.3)
 */

// 故障案例基础类型 - 对齐 FaultCaseBase
export interface FaultCaseBase {
    fault_code: string                  // 故障代码
    name: string                        // 故障名称
    description: string                 // 故障描述
    category?: string                   // 故障分类
    severity: 'low' | 'medium' | 'high' // 严重程度
    affected_parts?: string[]           // 受影响部件列表
    symptoms?: string[]                 // 故障症状
    diagnosis_steps?: string[]          // 诊断步骤
    solution_steps?: string[]           // 解决步骤
}

// 故障案例响应 - 对齐 FaultCaseResponse
export interface FaultCase extends FaultCaseBase {
    id: number
    created_at: string
    updated_at: string
}

// 故障案例列表项 - 对齐 FaultCaseListItem
export interface FaultCaseListItem {
    id: number
    fault_code: string
    name: string
    category?: string
    severity: 'low' | 'medium' | 'high'
    created_at: string
}

// 故障案例列表响应 - 对齐 FaultCaseListResponse
export interface FaultCaseListResponse {
    total: number
    items: FaultCaseListItem[]
}

// 创建故障案例请求 - 对齐 FaultCaseCreate
export interface FaultCaseCreateRequest extends FaultCaseBase { }

// 更新故障案例请求 - 对齐 FaultCaseUpdate
export interface FaultCaseUpdateRequest {
    name?: string
    description?: string
    category?: string
    severity?: 'low' | 'medium' | 'high'
    affected_parts?: string[]
    symptoms?: string[]
    diagnosis_steps?: string[]
    solution_steps?: string[]
}
