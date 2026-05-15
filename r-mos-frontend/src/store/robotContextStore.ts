// r-mos-frontend/src/store/robotContextStore.ts
import { create } from 'zustand'

import { listRobots, listStudentRobots } from '@/api/robots'
import type { RobotModel } from '@/types/robotModel'

const STORAGE_KEY = 'rmos_current_robot_id'

interface RobotContextState {
  currentRobotId: number | null
  currentRobot: RobotModel | null
  availableRobots: RobotModel[]
  isLoading: boolean

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

  async fetchAvailableRobots(studentId: number) {
    set({ isLoading: true })
    try {
      const res = await listStudentRobots(studentId)
      const robots = res.items

      // 恢复之前选中的机器人，或自动选中唯一一台
      const storedId = getStoredRobotId()
      let current: RobotModel | null = null
      if (storedId) {
        current = robots.find((r) => r.id === storedId) ?? null
      }
      if (!current && robots.length === 1) {
        current = robots[0]
      }

      set({
        availableRobots: robots,
        currentRobot: current,
        currentRobotId: current?.id ?? null,
      })

      if (current) {
        localStorage.setItem(STORAGE_KEY, String(current.id))
      }
    } catch {
      set({ availableRobots: [] })
    } finally {
      set({ isLoading: false })
    }
  },

  async fetchTeacherRobots() {
    set({ isLoading: true })
    try {
      const res = await listRobots()
      const robots = res.items

      const storedId = getStoredRobotId()
      let current: RobotModel | null = null
      if (storedId) {
        current = robots.find((r) => r.id === storedId) ?? null
      }
      if (!current && robots.length > 0) {
        current = robots[0]
      }

      set({
        availableRobots: robots,
        currentRobot: current,
        currentRobotId: current?.id ?? null,
      })

      if (current) {
        localStorage.setItem(STORAGE_KEY, String(current.id))
      }
    } catch {
      set({ availableRobots: [] })
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
