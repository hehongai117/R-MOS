import { ChevronDown, ChevronUp } from 'lucide-react'
import { type ReactNode, useState } from 'react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface SectionCardProps {
  title: string
  description?: string
  actions?: ReactNode
  children: ReactNode
  collapsible?: boolean
  className?: string
}

export function SectionCard({
  title,
  description,
  actions,
  children,
  collapsible = false,
  className,
}: SectionCardProps) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <section
      className={cn(
        'glass-card overflow-hidden rounded-xl border border-border-subtle',
        className,
      )}
    >
      <header className="flex items-center justify-between gap-3 border-b border-border-subtle px-5 py-4">
        <div className="min-w-0">
          <div className="text-sm font-medium text-primary">{title}</div>
          {description ? <div className="text-xs text-text-muted">{description}</div> : null}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {actions}
          {collapsible ? (
            <Button
              type="button"
              size="icon"
              variant="ghost"
              onClick={() => setCollapsed((value) => !value)}
            >
              {collapsed ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
            </Button>
          ) : null}
        </div>
      </header>
      {!collapsed ? <div className="p-5">{children}</div> : null}
    </section>
  )
}
