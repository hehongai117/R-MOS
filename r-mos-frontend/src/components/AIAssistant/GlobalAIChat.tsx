import { useState, useRef, useEffect } from 'react'
import { Button, Input } from 'antd'
import { MessageOutlined, CloseOutlined, SendOutlined, RobotOutlined } from '@ant-design/icons'
import apiClient from '@/api/client'
import { useRobotContextStore } from '@/store/robotContextStore'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export function GlobalAIChat() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const currentRobot = useRobotContextStore((s) => s.currentRobot)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  const send = async () => {
    const text = input.trim()
    if (!text || loading) return
    setInput('')
    const userMsg: ChatMessage = { role: 'user', content: text }
    setMessages((prev) => [...prev, userMsg])
    setLoading(true)

    try {
      const res = await apiClient.post<{ reply: string }>('/ai-assistant/chat', {
        message: text,
        robot_model_id: currentRobot?.id ?? null,
        context: currentRobot ? `当前机器人: ${currentRobot.brand} ${currentRobot.model_name}` : undefined,
      })
      setMessages((prev) => [...prev, { role: 'assistant', content: res.data.reply }])
    } catch {
      setMessages((prev) => [...prev, { role: 'assistant', content: '抱歉，AI 助手暂时无法响应，请稍后再试。' }])
    } finally {
      setLoading(false)
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-blue-600 shadow-lg transition-transform hover:scale-110"
        title="AI 助手"
      >
        <MessageOutlined style={{ fontSize: 24, color: '#fff' }} />
      </button>
    )
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 flex h-[500px] w-[380px] flex-col overflow-hidden rounded-xl border border-gray-700 bg-gray-900 shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-700 px-4 py-3">
        <div className="flex items-center gap-2">
          <RobotOutlined style={{ fontSize: 18, color: '#3b82f6' }} />
          <span className="font-semibold text-white">AI 助手</span>
          {currentRobot && (
            <span className="text-xs text-gray-400">· {currentRobot.model_name}</span>
          )}
        </div>
        <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-white">
          <CloseOutlined />
        </button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {messages.length === 0 && (
          <div className="flex h-full items-center justify-center text-gray-400 text-sm">
            你好！我是 R-MOS AI 助手，可以回答机器人维保相关问题。
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[80%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-100'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="rounded-lg bg-gray-800 px-3 py-2 text-sm text-gray-400">
              思考中...
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-gray-700 p-3">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onPressEnter={send}
            placeholder="输入问题..."
            disabled={loading}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={send}
            loading={loading}
          />
        </div>
      </div>
    </div>
  )
}
