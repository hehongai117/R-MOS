import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

type StatusValue = 'active' | 'idle' | 'error' | 'warning' | 'success' | 'pending'

interface StatusBadgeProps {
  status: StatusValue
  label?: string
}

const variantMap: Record<StatusValue, 'default' | 'secondary' | 'warning' | 'success' | 'destructive'> = {
  active: 'default',
  idle: 'secondary',
  error: 'destructive',
  warning: 'warning',
  success: 'success',
  pending: 'secondary',
}

const dotClassMap: Record<StatusValue, string> = {
  active: 'bg-primary animate-pulse',
  idle: 'bg-text-muted',
  error: 'bg-danger',
  warning: 'bg-amber',
  success: 'bg-success',
  pending: 'bg-text-secondary',
}

const labelMap: Record<StatusValue, string> = {
  active: '在线',
  idle: '空闲',
  error: '异常',
  warning: '警告',
  success: '正常',
  pending: '待处理',
}

export function StatusBadge({ status, label }: StatusBadgeProps) {
  return (
    <Badge variant={variantMap[status]} className="gap-1.5">
      <span className={cn('status-dot', dotClassMap[status])} />
      <span>{label ?? labelMap[status]}</span>
    </Badge>
  )
}
