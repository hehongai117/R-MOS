// r-mos-frontend/src/store/robotContextStore.ts
import { create } from 'zustand'

import { listRobots, listStudentRobots } from '@/api/robots'
import { DEFAULT_ROBOT_MODEL_NAME } from '@/config/robots'
import type { RobotModel } from '@/types/robotModel'

const STORAGE_KEY = 'rmos_current_robot_id'

/**
 * 选出初始机器人：优先历史选择 → 精选默认型号（DEFAULT_ROBOT_MODEL_NAME）→ 首个机器人。
 * autoPickFirst=false 时（学生端多台情况）不自动兜底首个，保持"需手动选择"语义。
 */
function pickInitialRobot(
  robots: RobotModel[],
  storedId: number | null,
  autoPickFirst: boolean,
): RobotModel | null {
  if (storedId) {
    const stored = robots.find((r) => r.id === storedId)
    if (stored) return stored
  }
  if (DEFAULT_ROBOT_MODEL_NAME) {
    const featured = robots.find((r) => r.model_name === DEFAULT_ROBOT_MODEL_NAME)
    if (featured) return featured
  }
  if (autoPickFirst && robots.length > 0) return robots[0]
  return null
}

interface RobotContextState {
  currentRobotId: number | null
  currentRobot: RobotModel | null
  availableRobots: RobotModel[]
  isLoading: boolean
  error: string | null

  /** 加载学生可用机器人列表 */
  fetchAvailableRobots: (studentId: number) => Promise<void>
  /** 加载教师名下的机器人列表 */
  fetchTeacherRobots: () => Promise<void>
  /** 设置当前机器人 */
  setCurrentRobot: (robot: RobotModel) => void
  /** 清除上下文（登出时） */
  clearContext: () => void
}

function getStoredRobotId(): number | null {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (!stored) return null
  const parsed = parseInt(stored, 10)
  return isNaN(parsed) ? null : parsed
}

export const useRobotContextStore = create<RobotContextState>((set, _get) => ({
  currentRobotId: getStoredRobotId(),
  currentRobot: null,
  availableRobots: [],
  isLoading: false,
  error: null,

  async fetchAvailableRobots(studentId: number) {
    set({ isLoading: true, error: null })
    try {
      const res = await listStudentRobots(studentId)
      const robots = res.items

      // 恢复历史选择 → 精选默认型号 → 唯一一台时自动选中（多台不自动兜底，需手动选）
      const current = pickInitialRobot(robots, getStoredRobotId(), robots.length === 1)

      set({
        availableRobots: robots,
        currentRobot: current,
        currentRobotId: current?.id ?? null,
      })

      if (current) {
        localStorage.setItem(STORAGE_KEY, String(current.id))
      }
    } catch (err) {
      set({ availableRobots: [], error: err instanceof Error ? err.message : '加载机器人列表失败' })
    } finally {
      set({ isLoading: false })
    }
  },

  async fetchTeacherRobots() {
    set({ isLoading: true, error: null })
    try {
      const res = await listRobots()
      const robots = res.items

      // 恢复历史选择 → 精选默认型号 → 首个机器人
      const current = pickInitialRobot(robots, getStoredRobotId(), true)

      set({
        availableRobots: robots,
        currentRobot: current,
        currentRobotId: current?.id ?? null,
      })

      if (current) {
        localStorage.setItem(STORAGE_KEY, String(current.id))
      }
    } catch (err) {
      set({ availableRobots: [], error: err instanceof Error ? err.message : '加载机器人列表失败' })
    } finally {
      set({ isLoading: false })
    }
  },

  setCurrentRobot(robot: RobotModel) {
    localStorage.setItem(STORAGE_KEY, String(robot.id))
    set({ currentRobotId: robot.id, currentRobot: robot })
  },

  clearContext() {
    localStorage.removeItem(STORAGE_KEY)
    set({ currentRobotId: null, currentRobot: null, availableRobots: [] })
  },
}))

/** Hook: 获取当前选中的机器人 ID（便于组件消费） */
export function useCurrentRobotId(): number | null {
  return useRobotContextStore((s) => s.currentRobotId)
}
