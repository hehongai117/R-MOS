/**
 * Axios客户端配置（V1.1修复版）
 * 
 * ⚠️ 强制约束（遵循骨架文档§2.3和§4.6）：
 * - 所有HTTP API必须包含 /api/v1/ 前缀
 * - WebSocket连接必须使用 /ws/robot/status 路径
 */
import axios, { AxiosError, AxiosResponse } from 'axios';
import { message } from 'antd';

// API基础路径配置（默认相对路径，配合 Vite proxy 消除 CORS）
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

// 创建Axios实例（V1.1修正：添加/api/v1前缀）
export const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,  // ✅ 强制约束：统一添加前缀（默认相对路径）
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可添加认证Token（MVP阶段暂不需要）
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器（V1.1修正：遵循骨架文档§4.7错误格式）
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError<ErrorResponse>) => {
    if (error.response) {
      const errorData = error.response.data;

      // 统一错误提示
      const errorMessage = errorData?.message || '请求失败，请稍后重试';
      message.error(errorMessage);

      // 业务规则违反（409）特殊处理
      if (error.response.status === 409) {
        console.warn('Business rule violation:', errorData);
      }
    } else if (error.request) {
      message.error('网络连接失败，请检查网络');
    } else {
      message.error('请求配置错误');
    }

    return Promise.reject(error);
  }
);

// 错误响应类型（遵循骨架文档§4.7）
export interface ErrorResponse {
  status_code: number;
  error_type: string;
  message: string;
  details?: {
    code: string;
    message: string;
    field?: string;
    details?: Record<string, any>;
  };
  timestamp: string;
  request_id?: string;
}

export default apiClient;
