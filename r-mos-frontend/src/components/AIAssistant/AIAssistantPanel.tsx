import { useRef, useState, useEffect } from 'react'
import { Bot, Send, X, Minimize2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAIAssistantStore } from '@/store/aiAssistantStore'
import { useRobotContextStore } from '@/store/robotContextStore'
import { sendAIChat, type ChatMessagePayload } from '@/api/aiAssistant'
import { ChatMessage } from './ChatMessage'

interface AIAssistantPanelProps {
  sopId?: number
  sopTitle?: string
  currentStepIndex?: number
  currentStepDescription?: string
  faultType?: string
  hintLevel?: number
}

export function AIAssistantPanel({
  sopId,
  sopTitle,
  currentStepIndex,
  currentStepDescription,
  faultType,
  hintLevel = 3,
}: AIAssistantPanelProps) {
  const { isOpen, messages, isLoading, toggle, close, addMessage, setLoading } =
    useAIAssistantStore()
  const currentRobot = useRobotContextStore(s => s.currentRobot)
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  const handleSend = async () => {
    const trimmed = input.trim()
    if (!trimmed || isLoading) return

    addMessage('user', trimmed)
    setInput('')
    setLoading(true)

    try {
      const history: ChatMessagePayload[] = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }))
      const response = await sendAIChat({
        message: trimmed,
        sop_id: sopId,
        sop_title: sopTitle,
        current_step_index: currentStepIndex,
        current_step_description: currentStepDescription,
        fault_type: faultType,
        hint_level: hintLevel,
        history,
        robot_id: currentRobot?.id,
      })
      addMessage('assistant', response.reply)
    } catch {
      addMessage('assistant', '抱歉，请求失败。请稍后重试。')
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) {
    return (
      <button
        onClick={toggle}
        className="fixed bottom-6 right-6 z-50 flex h-12 w-12 items-center justify-center rounded-full bg-primary text-white shadow-lg transition-transform hover:scale-105"
      >
        <Bot className="h-5 w-5" />
      </button>
    )
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 flex h-[480px] w-[360px] flex-col rounded-xl border border-border-subtle bg-bg-surface shadow-xl">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border-subtle px-4 py-3">
        <div className="flex items-center gap-2">
          <Bot className="h-4 w-4 text-primary" />
          <span className="text-sm font-medium text-text-primary">AI 助手</span>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={close}>
            <Minimize2 className="h-3.5 w-3.5" />
          </Button>
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={close}>
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        <div className="space-y-3">
          {messages.length === 0 && (
            <p className="py-8 text-center text-xs text-text-muted">
              有问题随时问我，我会根据当前步骤为你提供帮助。
            </p>
          )}
          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}
          {isLoading && (
            <div className="flex gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-bg-elevated">
                <Bot className="h-3.5 w-3.5 animate-pulse text-text-secondary" />
              </div>
              <div className="rounded-lg bg-bg-elevated px-3 py-2 text-sm text-text-muted">
                思考中...
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-border-subtle p-3">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder="输入问题..."
            className="flex-1 rounded-md border border-border-subtle bg-bg-base px-3 py-2 text-sm outline-none focus:border-primary"
          />
          <Button size="icon" className="h-8 w-8" onClick={handleSend} disabled={isLoading}>
            <Send className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </div>
  )
}
