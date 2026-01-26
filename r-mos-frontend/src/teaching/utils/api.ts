/**
 * 教学域错误信息格式化
 */
import type { AxiosError } from 'axios'
import type { ErrorResponse } from '@/api/client'

export function formatTeachingError(error: unknown, fallback: string): string {
  const axiosError = error as AxiosError<ErrorResponse>
  const status = axiosError?.response?.status
  const errorCode = axiosError?.response?.data?.details?.code
  const message = axiosError?.response?.data?.message
  const detail = message || fallback

  if (status && errorCode) {
    return `${detail}（状态码：${status}，错误码：${errorCode}）`
  }
  if (status) {
    return `${detail}（状态码：${status}）`
  }
  return detail
}
