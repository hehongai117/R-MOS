/**
 * P2-4: User Preference API
 * 用户偏好设置 API
 */
import { apiClient } from './client'
import { UserPreference, GuidanceMode, GuidanceModeRequest } from '@/types/user'

/**
 * 获取用户偏好设置
 */
export async function getUserPreference(): Promise<UserPreference> {
  const response = await apiClient.get<UserPreference>('/agent/preference')
  return response.data
}

/**
 * 更新指导模式
 */
export async function updateGuidanceMode(
  mode: GuidanceMode
): Promise<UserPreference> {
  const request: GuidanceModeRequest = { mode }
  const response = await apiClient.put<UserPreference>(
    '/agent/preference/guidance-mode',
    request
  )
  return response.data
}
