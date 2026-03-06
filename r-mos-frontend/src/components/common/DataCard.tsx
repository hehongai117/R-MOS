import { ArrowDownRight, ArrowRight, ArrowUpRight } from 'lucide-react'

import { cn } from '@/lib/utils'

type TrendDirection = 'up' | 'down' | 'flat'
type CardStatus = 'normal' | 'warning' | 'danger' | 'success'

interface DataCardProps {
  title: string
  value: string | number
  unit?: string
  trend?: TrendDirection
  trendValue?: string
  status?: CardStatus
}

const statusClassMap: Record<CardStatus, string> = {
  normal: 'text-primary',
  warning: 'text-amber',
  danger: 'text-danger',
  success: 'text-success',
}

const trendIconMap = {
  up: ArrowUpRight,
  down: ArrowDownRight,
  flat: ArrowRight,
}

export function DataCard({
  title,
  value,
  unit,
  trend = 'flat',
  trendValue,
  status = 'normal',
}: DataCardProps) {
  const TrendIcon = trendIconMap[trend]

  return (
    <div className="glass-card rounded-lg p-4">
      <div className="mb-2 text-xs uppercase tracking-[0.18em] text-text-muted">{title}</div>
      <div className="flex items-end gap-2">
        <div className="text-data text-2xl font-bold text-primary">{value}</div>
        {unit ? <div className="pb-1 text-sm text-text-secondary">{unit}</div> : null}
      </div>
      {trendValue ? (
        <div className={cn('mt-3 inline-flex items-center gap-1 text-sm', statusClassMap[status])}>
          <TrendIcon className="h-4 w-4" />
          <span>{trendValue}</span>
        </div>
      ) : null}
    </div>
  )
}
