// src/api/demo.ts
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export interface DemoChatMeta {
  type: 'meta'
  trace_id: string
  diagnosis: Record<string, unknown> | null
  citations: Array<{ type: string; desc: string; source?: string }> | null
  sop_recommendation: {
    sop_id: string
    sop_name: string
    estimated_time: string
    steps_count: number
  } | null
}

export interface DemoChatTextChunk {
  type: 'text'
  content: string
}

export interface DemoChatDone {
  type: 'done'
}

export type DemoChatEvent = DemoChatMeta | DemoChatTextChunk | DemoChatDone

export async function startDemoFault(scenario = 'knee_overheat') {
  const res = await axios.post(`${API_BASE}/api/v1/demo/fault/start`, { scenario })
  return res.data
}

export async function resetDemoFault() {
  const res = await axios.post(`${API_BASE}/api/v1/demo/fault/reset`)
  return res.data
}

export function streamDemoChat(
  message: string,
  faultContext: Record<string, unknown> | null,
  onEvent: (event: DemoChatEvent) => void,
  onDone: () => void,
  onError: (err: Error) => void,
): AbortController {
  const controller = new AbortController()

  fetch(`${API_BASE}/api/v1/demo/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, fault_context: faultContext }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok || !response.body) {
        throw new Error(`Stream failed: ${response.status}`)
      }
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim()
            if (!data) continue
            try {
              const event = JSON.parse(data) as DemoChatEvent
              onEvent(event)
              if (event.type === 'done') {
                onDone()
                return
              }
            } catch {
              // skip malformed events
            }
          }
        }
      }
      onDone()
    })
    .catch((err) => {
      if (err.name !== 'AbortError') onError(err)
    })

  return controller
}
