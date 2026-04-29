import { AlertTriangle, ArrowRight, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export interface FaultAlert {
  id: string
  fault_type: string
  fault_name: string
  affected_joints: string[]
  current_value: string
  threshold: string
  severity: 'warning' | 'danger'
}

interface FaultAlertCardProps {
  alert: FaultAlert
  onDiagnose: (alert: FaultAlert) => void
  onDismiss: (alertId: string) => void
}

export function FaultAlertCard({ alert, onDiagnose, onDismiss }: FaultAlertCardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border p-4 animate-in slide-in-from-top-2',
        alert.severity === 'danger'
          ? 'border-red-500/40 bg-red-500/10'
          : 'border-amber-500/40 bg-amber-500/10',
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <AlertTriangle
            className={cn(
              'h-5 w-5',
              alert.severity === 'danger' ? 'text-red-400' : 'text-amber-400',
            )}
          />
          <div>
            <div className="text-sm font-medium text-text-primary">
              {alert.fault_name}
            </div>
            <div className="text-xs text-text-muted">
              {alert.affected_joints.join(', ')} — {alert.current_value}（阈值 {alert.threshold}）
            </div>
          </div>
        </div>
        <button onClick={() => onDismiss(alert.id)} className="text-text-muted hover:text-text-primary">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="mt-3 flex gap-2">
        <Button size="sm" onClick={() => onDiagnose(alert)}>
          一键诊断 <ArrowRight className="ml-1 h-3 w-3" />
        </Button>
        <Button size="sm" variant="ghost" onClick={() => onDismiss(alert.id)}>
          忽略
        </Button>
      </div>
    </div>
  )
}
