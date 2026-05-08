import { AlertCircle, CheckCircle2, Clock, Loader2, Zap } from 'lucide-react'
import { Empty } from 'antd'

import { Button } from '@/components/ui/button'
import type { AnalysisTask, AnalysisTaskStatus } from '@/types/robotModel'

interface AnalysisStatusPanelProps {
  tasks: AnalysisTask[]
  loading: boolean
  onTrigger: () => void
  canTrigger?: boolean
}

const STATUS_MAP: Record<AnalysisTaskStatus, { label: string; icon: typeof Clock; className: string }> = {
  pending: { label: '等待中', icon: Clock, className: 'text-text-muted' },
  running: { label: '运行中', icon: Loader2, className: 'text-blue-500' },
  completed: { label: '已完成', icon: CheckCircle2, className: 'text-green-500' },
  failed: { label: '失败', icon: AlertCircle, className: 'text-red-500' },
}

export function AnalysisStatusPanel({ tasks, loading, onTrigger, canTrigger = false }: AnalysisStatusPanelProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-6">
        <Loader2 className="h-5 w-5 animate-spin text-text-muted" />
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-text-primary">AI 分析任务</span>
        {canTrigger && (
          <Button size="sm" variant="outline" type="button" onClick={onTrigger}>
            <Zap className="mr-1 h-3.5 w-3.5" />
            触发分析
          </Button>
        )}
      </div>

      {tasks.length === 0 ? (
        <Empty description="暂无分析任务" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <div className="space-y-2">
          {tasks.map((task) => {
            const cfg = STATUS_MAP[task.status as AnalysisTaskStatus] ?? STATUS_MAP.pending
            const Icon = cfg.icon
            return (
              <div
                key={task.id}
                className="rounded-lg border border-border-subtle bg-bg-elevated px-4 py-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Icon
                      className={`h-4 w-4 ${cfg.className} ${task.status === 'running' ? 'animate-spin' : ''}`}
                    />
                    <span className={`text-sm ${cfg.className}`}>{cfg.label}</span>
                  </div>
                  <span className="text-xs text-text-muted">
                    {new Date(task.created_at).toLocaleString('zh-CN')}
                  </span>
                </div>
                {task.error_message && (
                  <div className="mt-2 text-xs text-red-500">{task.error_message}</div>
                )}
                {task.output_summary && (
                  <div className="mt-2 text-xs text-text-muted">
                    {JSON.stringify(task.output_summary)}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
