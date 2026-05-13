import { Loader2, Plus } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import type { RobotModel, RobotModelStatus } from '@/types/robotModel'

interface RobotSidebarProps {
  robots: RobotModel[]
  selectedRobotId: number | null
  loading: boolean
  onSelect: (robotId: number) => void
  onAdd: () => void
}

const STATUS_CONFIG: Record<RobotModelStatus, { label: string; className: string }> = {
  draft: { label: '草稿', className: 'text-text-muted' },
  analyzing: { label: '分析中', className: 'text-blue-500' },
  ready: { label: '已发布', className: 'text-green-500' },
}

export function RobotSidebar({ robots, selectedRobotId, loading, onSelect, onAdd }: RobotSidebarProps) {
  return (
    <div className="flex h-full w-[220px] flex-col border-r border-border-subtle bg-bg-surface">
      <div className="flex items-center justify-between border-b border-border-subtle px-3 py-2">
        <span className="text-xs font-medium uppercase tracking-wider text-text-muted">机器人</span>
        <Button size="sm" variant="ghost" onClick={onAdd} aria-label="添加机器人">
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      <ScrollArea className="flex-1">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-text-muted" />
          </div>
        ) : robots.length === 0 ? (
          <div className="px-3 py-6 text-center text-xs text-text-muted">
            暂无机器人，点击上方按钮添加
          </div>
        ) : (
          <div className="space-y-0.5 p-2">
            {robots.map((robot) => {
              const isSelected = robot.id === selectedRobotId
              const statusCfg = STATUS_CONFIG[robot.status as RobotModelStatus] ?? STATUS_CONFIG.draft
              return (
                <button
                  key={robot.id}
                  data-selected={isSelected}
                  className={cn(
                    'flex w-full flex-col items-start rounded-md px-3 py-2 text-left transition-colors',
                    isSelected
                      ? 'bg-primary-muted text-primary'
                      : 'text-text-secondary hover:bg-bg-elevated hover:text-text-primary',
                  )}
                  onClick={() => onSelect(robot.id)}
                >
                  <span className="truncate text-sm font-medium">
                    {robot.model_name}
                    {robot.binding_type === 'shared_ref' ? (
                      <span className="ml-1 text-xs" title="引用自共享库">🔗</span>
                    ) : null}
                  </span>
                  <span className="mt-0.5 flex items-center gap-2 text-xs">
                    <span className="text-text-muted">{robot.brand}</span>
                    <span className={statusCfg.className}>{statusCfg.label}</span>
                  </span>
                </button>
              )
            })}
          </div>
        )}
      </ScrollArea>
    </div>
  )
}
