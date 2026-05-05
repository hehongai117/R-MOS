import { create } from 'zustand'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

interface AIAssistantState {
  isOpen: boolean
  messages: ChatMessage[]
  isLoading: boolean
  toggle: () => void
  open: () => void
  close: () => void
  addMessage: (role: 'user' | 'assistant', content: string) => void
  setLoading: (loading: boolean) => void
  clearMessages: () => void
}

export const useAIAssistantStore = create<AIAssistantState>((set) => ({
  isOpen: false,
  messages: [],
  isLoading: false,
  toggle: () => set((s) => ({ isOpen: !s.isOpen })),
  open: () => set({ isOpen: true }),
  close: () => set({ isOpen: false }),
  addMessage: (role, content) =>
    set((s) => ({
      messages: [
        ...s.messages,
        { id: `${Date.now()}-${Math.random()}`, role, content, timestamp: Date.now() },
      ],
    })),
  setLoading: (isLoading) => set({ isLoading }),
  clearMessages: () => set({ messages: [] }),
}))
