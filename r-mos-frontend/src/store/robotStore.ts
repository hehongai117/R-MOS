import { create } from 'zustand'
import { message } from 'antd'

import {
  createRobot,
  deleteRobot,
  listRobots,
  togglePublish,
  toggleVisibility,
  updateRobot,
} from '@/api/robots'
import type { RobotModel, RobotModelCreateRequest, RobotModelUpdateRequest } from '@/types/robotModel'

interface RobotState {
  robots: RobotModel[]
  selectedRobotId: number | null
  isLoading: boolean

  /** 从后端加载机器人列表 */
  fetchRobots: () => Promise<void>
  /** 创建机器人 */
  addRobot: (data: RobotModelCreateRequest) => Promise<RobotModel>
  /** 更新机器人 */
  editRobot: (id: number, data: RobotModelUpdateRequest) => Promise<void>
  /** 删除机器人 */
  removeRobot: (id: number) => Promise<void>
  /** 选中某个机器人 */
  selectRobot: (id: number | null) => void
  /** 发布/取消发布 */
  togglePublish: (id: number) => Promise<void>
  /** 切换共享状态 */
  toggleVisibility: (id: number) => Promise<void>
  /** 取消引用共享机器人 */
  unbindRobot: (id: number) => Promise<void>
  /** 用新数据替换列表中的一条记录 */
  _replaceRobot: (updated: RobotModel) => void
}

export const useRobotStore = create<RobotState>((set, get) => ({
  robots: [],
  selectedRobotId: null,
  isLoading: false,

  async fetchRobots() {
    set({ isLoading: true })
    try {
      const res = await listRobots()
      set({ robots: res.items })
      // 如果当前选中的机器人已不在列表中，清空选中
      const ids = new Set(res.items.map((r) => r.id))
      if (get().selectedRobotId !== null && !ids.has(get().selectedRobotId!)) {
        set({ selectedRobotId: res.items[0]?.id ?? null })
      }
    } catch {
      message.error('加载机器人列表失败')
    } finally {
      set({ isLoading: false })
    }
  },

  async addRobot(data) {
    const robot = await createRobot(data)
    set((state) => ({
      robots: [robot, ...state.robots],
      selectedRobotId: robot.id,
    }))
    return robot
  },

  async editRobot(id, data) {
    const updated = await updateRobot(id, data)
    get()._replaceRobot(updated)
  },

  async removeRobot(id) {
    await deleteRobot(id)
    set((state) => {
      const robots = state.robots.filter((r) => r.id !== id)
      return {
        robots,
        selectedRobotId: state.selectedRobotId === id ? (robots[0]?.id ?? null) : state.selectedRobotId,
      }
    })
  },

  selectRobot(id) {
    set({ selectedRobotId: id })
  },

  async togglePublish(id) {
    const updated = await togglePublish(id)
    get()._replaceRobot(updated)
  },

  async toggleVisibility(id) {
    const updated = await toggleVisibility(id)
    get()._replaceRobot(updated)
  },

  async unbindRobot(id) {
    const { unbindSharedRobot } = await import('@/api/robots')
    await unbindSharedRobot(id)
    set((state) => {
      const robots = state.robots.filter((r) => r.id !== id)
      return {
        robots,
        selectedRobotId: state.selectedRobotId === id ? (robots[0]?.id ?? null) : state.selectedRobotId,
      }
    })
  },

  _replaceRobot(updated) {
    set((state) => ({
      robots: state.robots.map((r) => (r.id === updated.id ? updated : r)),
    }))
  },
}))

/** 获取当前选中的机器人 */
export function useSelectedRobot(): RobotModel | null {
  return useRobotStore((state) => {
    if (state.selectedRobotId === null) return null
    return state.robots.find((r) => r.id === state.selectedRobotId) ?? null
  })
}
