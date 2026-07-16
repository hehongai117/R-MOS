import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Bot, CheckCircle2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { RobotModel } from '@/types/robotModel'

interface RobotCardsProps {
  robots: RobotModel[]
  selectedId: number | null
  onSelect: (robot: RobotModel) => void
  loading?: boolean
}

export default function RobotCards({ robots, selectedId, onSelect, loading }: RobotCardsProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <Card key={i} className="animate-pulse">
            <CardContent className="py-6">
              <div className="h-5 w-32 rounded bg-bg-elevated" />
              <div className="mt-3 h-4 w-24 rounded bg-bg-elevated" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  if (robots.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <Bot className="mx-auto h-10 w-10 text-text-muted" />
          <p className="mt-3 text-sm text-text-muted">
            暂无可用机器人。请联系教师配置并发布机器人。
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {robots.map((robot) => {
        const isSelected = robot.id === selectedId
        return (
          <Card
            key={robot.id}
            data-testid="robot-card"
            className={cn(
              'cursor-pointer transition-all hover:shadow-sm',
              isSelected
                ? 'border-primary bg-primary-muted/30 shadow-sm'
                : 'hover:border-primary/30',
            )}
            onClick={() => onSelect(robot)}
          >
            <CardContent className="flex items-start gap-3 py-5">
              <div className={cn(
                'flex h-10 w-10 shrink-0 items-center justify-center rounded-lg',
                isSelected ? 'bg-primary text-white' : 'bg-bg-elevated text-text-muted',
              )}>
                <Bot className="h-5 w-5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="truncate font-medium text-text-primary">
                    {robot.model_name}
                  </span>
                  {isSelected && (
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-primary" />
                  )}
                </div>
                <p className="mt-1 text-xs text-text-secondary">{robot.brand}</p>
                {robot.description && (
                  <p className="mt-1 line-clamp-2 text-xs text-text-muted">{robot.description}</p>
                )}
              </div>
              <Badge variant="default" className="shrink-0 text-[10px]">
                v{robot.version}
              </Badge>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
