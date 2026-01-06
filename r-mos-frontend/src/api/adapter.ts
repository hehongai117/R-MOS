/**
 * Adapter API 模块
 * 与后端 /adapter/* 端点对接 (V2.2)
 * 
 * 用于与机器人适配器交互，包括获取状态、故障注入等
 */
import { apiClient } from './client'
import {
    RobotInfo,
    RobotStructure,
    FaultInjectionResult,
    FaultClearResult,
} from '@/types/robot'

/**
 * 故障注入请求参数
 */
export interface FaultInjectionRequest {
    fault_code: string      // 故障代码: E001_OVERHEAT, E002_STALL, etc.
    target_part: string     // 目标部件 ID
    severity?: 'low' | 'medium' | 'high'  // 严重程度，默认 medium
}

/**
 * 获取 Adapter 和机器人基础信息
 */
export async function getAdapterInfo(): Promise<RobotInfo> {
    const response = await apiClient.get<RobotInfo>('/adapter/info')
    return response.data
}

/**
 * 获取机器人结构描述
 * 包含所有关节、传感器、电源模块的定义
 */
export async function getRobotStructure(): Promise<RobotStructure> {
    const response = await apiClient.get<RobotStructure>('/adapter/structure')
    return response.data
}

/**
 * 故障注入
 * 
 * 支持的故障代码：
 * - E001_OVERHEAT: 过热（温度+30℃，扭矩-30%）
 * - E002_STALL: 卡死（速度=0，位置冻结）
 * - E003_VOLTAGE_DROP: 电压下降（电池-50%，扭矩-50%）
 * - E004_SENSOR_FAILURE: 传感器故障（数据噪声）
 * - E005_JOINT_LOOSE: 关节松动（位置噪声，扭矩-70%）
 */
export async function injectFault(request: FaultInjectionRequest): Promise<FaultInjectionResult> {
    const response = await apiClient.post<FaultInjectionResult>('/adapter/inject-fault', request)
    return response.data
}

/**
 * 清除指定故障
 */
export async function clearFault(faultCode: string): Promise<FaultClearResult> {
    const response = await apiClient.delete<FaultClearResult>(`/adapter/fault/${faultCode}`)
    return response.data
}

/**
 * 获取当前所有活动故障
 */
export async function getActiveFaults(): Promise<string[]> {
    const response = await apiClient.get<string[]>('/adapter/faults')
    return response.data
}
