/**
 * API 通用类型定义
 * 与后端 core/exceptions.py 和通用响应格式对齐
 */

// 标准错误响应 - 对齐后端异常处理格式
export interface ErrorResponse {
    status_code: number                 // HTTP状态码
    error_type: string                  // 错误类型
    message: string                     // 错误消息
    details?: {
        code: string                    // 错误代码
        message: string                 // 详细消息
        field?: string                  // 相关字段
        details?: Record<string, any>   // 额外详情
    }
    timestamp?: string                  // 错误发生时间
    request_id?: string                 // 请求ID
}

// 业务规则违反错误 (409)
export interface BusinessRuleError extends ErrorResponse {
    status_code: 409
    error_type: 'BusinessRuleViolation'
}

// 资源不存在错误 (404)
export interface NotFoundError extends ErrorResponse {
    status_code: 404
    error_type: 'ResourceNotFound'
}

// 验证错误 (422)
export interface ValidationError extends ErrorResponse {
    status_code: 422
    error_type: 'ValidationError'
}

// Adapter连接错误 (503)
export interface AdapterConnectionError extends ErrorResponse {
    status_code: 503
    error_type: 'AdapterConnectionError'
}

// 通用分页响应
export interface PaginatedResponse<T> {
    total: number                       // 总数量
    items: T[]                          // 数据项列表
    skip?: number                       // 跳过数量
    limit?: number                      // 每页数量
}

// 通用成功响应
export interface SuccessResponse {
    success: boolean
    message: string
}

// 健康检查响应
export interface HealthCheckResponse {
    status: 'healthy' | 'unhealthy'
    timestamp: string
    version: string
    checks: {
        adapter: {
            status: 'up' | 'down'
            message: string
            details?: Record<string, any>
        }
        system: {
            status: 'up' | 'down'
            message: string
            details?: Record<string, any>
        }
    }
}
