/**
 * SOP API 模块
 * 与后端 /sops/* 端点对接 (V2.3)
 */
import { apiClient } from './client'
import {
    SOP,
    SOPListResponse,
    SOPCreateRequest,
    SOPDeleteWarning,
    SOPDeleteResponse
} from '@/types/sop'

// 查询参数
export interface ListSOPsParams {
    skip?: number
    limit?: number
    category?: string
    applicable_model?: string
    robot_model_id?: number
}

/**
 * 获取 SOP 列表
 * 后端返回 { items: SOP[], total: number } 分页格式
 */
export async function listSOPs(params: ListSOPsParams = {}): Promise<SOPListResponse> {
    const { skip = 0, limit = 20, category, applicable_model, robot_model_id } = params
    const response = await apiClient.get<{ items: SOP[]; total: number }>('/sops', {
        params: { skip, limit, category, applicable_model, robot_model_id },
    })
    const { items, total } = response.data
    return {
        items: items.map(sop => ({
            id: sop.id,
            name: sop.name,
            category: sop.category,
            difficulty_level: sop.difficulty_level,
            step_count: sop.steps?.length ?? 0,
            estimated_time: sop.estimated_time,
            created_at: sop.created_at,
        })),
        total,
    }
}

/**
 * 获取单个 SOP 详情（含完整步骤）
 */
export async function getSOP(sopId: number): Promise<SOP> {
    const response = await apiClient.get<SOP>(`/sops/${sopId}`)
    return response.data
}

/**
 * 创建 SOP
 */
export async function createSOP(data: SOPCreateRequest): Promise<SOP> {
    const response = await apiClient.post<SOP>('/sops', data)
    return response.data
}

/**
 * 检查删除 SOP 的影响（二次确认用）
 * 
 * 调用流程：
 * 1. 用户点击删除 -> 调用此接口
 * 2. 如果 force_required=true，显示警告对话框
 * 3. 用户确认后调用 deleteSOP(id, true)
 */
export async function checkDeleteImpact(sopId: number): Promise<SOPDeleteWarning> {
    const response = await apiClient.get<SOPDeleteWarning>(`/sops/${sopId}/delete-impact`)
    return response.data
}

/**
 * 删除 SOP
 * @param sopId SOP ID
 * @param force 是否强制删除（忽略关联 Task）
 */
export async function deleteSOP(sopId: number, force: boolean = false): Promise<SOPDeleteResponse> {
    const response = await apiClient.delete<SOPDeleteResponse>(`/sops/${sopId}`, {
        params: { force }
    })
    return response.data
}
