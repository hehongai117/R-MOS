import axios, {
  AxiosError,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios'
import { message } from 'antd'

import {
  AUTH_STORAGE_KEYS,
  type AuthTokenResponse,
  useAuthStore,
} from '@/store/authStore'

export interface ErrorResponse {
  status_code: number
  error_type: string
  message: string
  /** FastAPI HTTPException 的原生错误字段（如资产闸门 409 的缺失清单） */
  detail?: string
  details?: {
    code: string
    message: string
    field?: string
    details?: Record<string, unknown>
  }
  timestamp: string
  request_id?: string
}

interface RequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean
  skipAuthRefresh?: boolean
}

import { API_BASE_URL, API_ROOT } from './config'
import { installRetry } from './retry'
export { API_BASE_URL, API_ROOT }

function getStoredRefreshToken() {
  return (
    localStorage.getItem(AUTH_STORAGE_KEYS.refreshToken) ??
    localStorage.getItem(AUTH_STORAGE_KEYS.legacyRefreshToken)
  )
}

export const apiClient = axios.create({
  baseURL: API_ROOT,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Install retry BEFORE the 401 interceptor.
// Axios response interceptors run FIFO, so the retry handler (registered here)
// runs first: it retries 502/503/504/network errors transparently and lets 401
// pass through to the refresh logic below.
installRetry(apiClient)

apiClient.interceptors.request.use(
  (config) => {
    const token =
      useAuthStore.getState().accessToken ??
      localStorage.getItem(AUTH_STORAGE_KEYS.accessToken) ??
      localStorage.getItem(AUTH_STORAGE_KEYS.legacyAccessToken)

    if (token) {
      config.headers.set('Authorization', `Bearer ${token}`)
    }

    return config
  },
  (error) => Promise.reject(error),
)

apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError<ErrorResponse>) => {
    const originalRequest = error.config as RequestConfig | undefined
    const status = error.response?.status

    if (
      status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !originalRequest.skipAuthRefresh
    ) {
      const refreshToken = getStoredRefreshToken()
      if (!refreshToken) {
        await useAuthStore.getState().logout({ redirect: false, remote: false })
        if (window.location.pathname !== '/login') {
          window.location.assign('/login')
        }
        return Promise.reject(error)
      }

      originalRequest._retry = true

      try {
        const response = await axios.post<AuthTokenResponse>(`${API_ROOT}/auth/refresh`, {
          refresh_token: refreshToken,
        })

        await useAuthStore.getState().applySession(response.data)
        originalRequest.headers.set('Authorization', `Bearer ${response.data.access_token}`)
        return apiClient(originalRequest)
      } catch (refreshError) {
        try {
          await axios.post(`${API_ROOT}/auth/logout`, { refresh_token: refreshToken })
        } catch {
          // Best-effort cleanup.
        }

        await useAuthStore.getState().logout({ redirect: false, remote: false })
        message.error('登录状态已失效，请重新登录')
        if (window.location.pathname !== '/login') {
          window.location.assign('/login')
        }
        return Promise.reject(refreshError)
      }
    }

    if (error.response) {
      message.error(error.response.data?.detail || error.response.data?.message || '请求失败，请稍后重试')
    } else if (error.request) {
      message.error('网络连接失败，请检查网络')
    } else {
      message.error('请求配置错误')
    }

    return Promise.reject(error)
  },
)

export default apiClient
