/**
 * P2-4: User Preference Types
 * 用户偏好设置类型定义
 */

export type GuidanceMode = 'full_time' | 'on_demand' | 'silent'

export interface UserPreference {
  user_id: number
  guidance_mode: GuidanceMode
  guidance_mode_display: string
  preferences: Record<string, any>
}

export interface GuidanceModeRequest {
  mode: GuidanceMode
}
