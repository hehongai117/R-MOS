import { createStore } from 'zustand/vanilla'

export type WorkbenchToolStatus = 'PENDING' | 'CONFIRMED' | 'ANOMALY'
export type WorkbenchStepStatus = 'pending' | 'active' | 'passed' | 'failed'
export type WorkbenchChatRole = 'assistant' | 'teacher' | 'user'

export interface WorkbenchVerdict {
  result: 'PASS' | 'FAIL'
  summary: string
  details?: string
}

export interface WorkbenchTool {
  id: string
  name: string
  spec?: string
  isCritical?: boolean
  recommendation?: string
}

export interface WorkbenchStep {
  id: string
  title: string
  durationSec?: number
  status: WorkbenchStepStatus
  instruction: string
  evidenceHint?: string
  tools: WorkbenchTool[]
}

export interface WorkbenchChatMessage {
  id: string
  role: WorkbenchChatRole
  content: string
  createdAt: string
}

export interface WorkbenchProject {
  sessionId: string
  projectId: string
  title: string
  progressPercent: number
}

export interface WorkbenchHydrationPayload {
  project: WorkbenchProject
  steps: WorkbenchStep[]
  currentStepId?: string | null
  messages?: WorkbenchChatMessage[]
}

export interface WorkbenchState {
  project: WorkbenchProject | null
  steps: WorkbenchStep[]
  currentStepId: string | null
  toolStatusMap: Record<string, WorkbenchToolStatus>
  verdict: WorkbenchVerdict | null
  noteDraft: string
  evidenceName: string | null
  messages: WorkbenchChatMessage[]
  isViewerFullscreen: boolean
  hydrateTrainingProject: (payload: WorkbenchHydrationPayload) => void
  resetTrainingProject: () => void
  setCurrentStep: (stepId: string | null) => void
  setToolStatus: (toolId: string, status: WorkbenchToolStatus) => void
  setVerdict: (verdict: WorkbenchVerdict) => void
  resetVerdict: () => void
  setNoteDraft: (value: string) => void
  setEvidenceName: (value: string | null) => void
  setMessages: (messages: WorkbenchChatMessage[]) => void
  addMessage: (message: WorkbenchChatMessage) => void
  setViewerFullscreen: (value: boolean) => void
}

function buildToolStatusMap(steps: WorkbenchStep[]) {
  return steps.reduce<Record<string, WorkbenchToolStatus>>((acc, step) => {
    step.tools.forEach((tool) => {
      acc[tool.id] = acc[tool.id] ?? 'PENDING'
    })
    return acc
  }, {})
}

const initialState = {
  project: null,
  steps: [],
  currentStepId: null,
  toolStatusMap: {},
  verdict: null,
  noteDraft: '',
  evidenceName: null,
  messages: [],
  isViewerFullscreen: false,
}

export function createWorkbenchStore() {
  return createStore<WorkbenchState>((set) => ({
    ...initialState,
    hydrateTrainingProject: (payload) =>
      set({
        project: payload.project,
        steps: payload.steps,
        currentStepId: payload.currentStepId ?? payload.steps.find((step) => step.status === 'active')?.id ?? payload.steps[0]?.id ?? null,
        toolStatusMap: buildToolStatusMap(payload.steps),
        verdict: null,
        noteDraft: '',
        evidenceName: null,
        messages: payload.messages ?? [],
        isViewerFullscreen: false,
      }),
    resetTrainingProject: () => set({ ...initialState }),
    setCurrentStep: (stepId) => set({ currentStepId: stepId }),
    setToolStatus: (toolId, status) =>
      set((state) => ({
        toolStatusMap: {
          ...state.toolStatusMap,
          [toolId]: status,
        },
      })),
    setVerdict: (verdict) => set({ verdict }),
    resetVerdict: () => set({ verdict: null }),
    setNoteDraft: (value) => set({ noteDraft: value }),
    setEvidenceName: (value) => set({ evidenceName: value }),
    setMessages: (messages) => set({ messages }),
    addMessage: (message) =>
      set((state) => ({
        messages: [...state.messages.slice(-4), message],
      })),
    setViewerFullscreen: (value) => set({ isViewerFullscreen: value }),
  }))
}

export function getCurrentStep(state: WorkbenchState) {
  return state.steps.find((step) => step.id === state.currentStepId) ?? null
}

export function getCurrentStepTools(state: WorkbenchState) {
  return getCurrentStep(state)?.tools ?? []
}

export function getConfirmedCriticalToolCount(state: WorkbenchState) {
  const tools = getCurrentStepTools(state).filter((tool) => tool.isCritical)
  const confirmed = tools.filter((tool) => state.toolStatusMap[tool.id] === 'CONFIRMED')
  return {
    confirmed: confirmed.length,
    total: tools.length,
  }
}

export function canSubmitCurrentStep(state: WorkbenchState) {
  const { confirmed, total } = getConfirmedCriticalToolCount(state)
  return total === 0 || confirmed === total
}

export const workbenchStore = createWorkbenchStore()
