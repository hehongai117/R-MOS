import { Bot, User } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ChatMessage as ChatMessageType } from '@/store/aiAssistantStore'

export function ChatMessage({ message }: { message: ChatMessageType }) {
  const isUser = message.role === 'user'
  return (
    <div className={cn('flex gap-2', isUser && 'flex-row-reverse')}>
      <div
        className={cn(
          'flex h-7 w-7 shrink-0 items-center justify-center rounded-full',
          isUser ? 'bg-primary/10 text-primary' : 'bg-bg-elevated text-text-secondary',
        )}
      >
        {isUser ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
      </div>
      <div
        className={cn(
          'max-w-[80%] rounded-lg px-3 py-2 text-sm',
          isUser
            ? 'bg-primary text-white'
            : 'bg-bg-elevated text-text-primary',
        )}
      >
        {message.content}
      </div>
    </div>
  )
}
