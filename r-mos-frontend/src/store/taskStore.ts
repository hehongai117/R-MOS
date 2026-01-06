/**
 * Task状态管理（使用Zustand）
 */
import { create } from 'zustand';
import { Task } from '@/types/task';

interface TaskStore {
  currentTask: Task | null;
  setCurrentTask: (task: Task | null) => void;
  executing: boolean;
  setExecuting: (executing: boolean) => void;
}

export const useTaskStore = create<TaskStore>((set) => ({
  currentTask: null,
  setCurrentTask: (task) => set({ currentTask: task }),
  executing: false,
  setExecuting: (executing) => set({ executing }),
}));
