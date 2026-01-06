/**
 * Fault API 模块
 * 与后端 /fault-cases/* 端点对接
 */
import { apiClient } from './client'
import {
    FaultCase,
    FaultCaseListResponse,
    FaultCaseCreateRequest,
    FaultCaseUpdateRequest,
} from '@/types/fault'

// 获取故障案例列表
// 注意：后端返回分页格式 {total, items}，这里提取 items 数组
export async function listFaultCases(): Promise<FaultCase[]> {
    const response = await apiClient.get<FaultCaseListResponse>('/fault-cases')
    // 后端返回分页格式，提取 items
    return response.data.items as FaultCase[]
}

// 获取单个故障案例
export async function getFaultCase(faultCaseId: number): Promise<FaultCase> {
    const response = await apiClient.get<FaultCase>(`/fault-cases/${faultCaseId}`)
    return response.data
}

// 创建故障案例
export async function createFaultCase(data: FaultCaseCreateRequest): Promise<FaultCase> {
    const response = await apiClient.post<FaultCase>('/fault-cases', data)
    return response.data
}

// 更新故障案例
export async function updateFaultCase(
    faultCaseId: number,
    data: FaultCaseUpdateRequest
): Promise<FaultCase> {
    const response = await apiClient.patch<FaultCase>(`/fault-cases/${faultCaseId}`, data)
    return response.data
}

// 删除故障案例
export async function deleteFaultCase(faultCaseId: number): Promise<void> {
    await apiClient.delete(`/fault-cases/${faultCaseId}`)
}
