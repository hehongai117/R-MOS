import { EyeOff, Globe, Lock, Rocket } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { StatusBadge } from '@/components/common'
import type { RobotModel, RobotModelStatus } from '@/types/robotModel'

interface PublishControlProps {
  robot: RobotModel
  onPublish: () => void
  onToggleVisibility: () => void
}

const STATUS_BADGE: Record<RobotModelStatus, { label: string; tone: 'idle' | 'active' | 'success' }> = {
  draft: { label: '草稿', tone: 'idle' },
  analyzing: { label: '分析中', tone: 'active' },
  ready: { label: '已发布', tone: 'success' },
}

export function PublishControl({ robot, onPublish, onToggleVisibility }: PublishControlProps) {
  const badgeCfg = STATUS_BADGE[robot.status as RobotModelStatus] ?? STATUS_BADGE.draft
  const isReady = robot.status === 'ready'
  const isAnalyzing = robot.status === 'analyzing'
  const isShared = robot.visibility === 'shared'

  return (
    <div className="flex flex-wrap items-center gap-3">
      <StatusBadge label={badgeCfg.label} status={badgeCfg.tone} />

      <Button
        size="sm"
        type="button"
        variant={isReady ? 'outline' : 'default'}
        disabled={isAnalyzing}
        onClick={onPublish}
      >
        {isAnalyzing ? (
          '分析中...'
        ) : isReady ? (
          <>
            <EyeOff className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
            取消发布
          </>
        ) : (
          <>
            <Rocket className="mr-1 h-3.5 w-3.5" aria-hidden="true" />
            发布
          </>
        )}
      </Button>

      <button
        className="flex items-center gap-1 rounded-md px-2 py-1 text-xs transition-colors hover:bg-bg-elevated"
        onClick={onToggleVisibility}
      >
        {isShared ? (
          <>
            <Globe className="h-3.5 w-3.5 text-blue-500" aria-hidden="true" />
            <span className="text-blue-500">共享</span>
          </>
        ) : (
          <>
            <Lock className="h-3.5 w-3.5 text-text-muted" aria-hidden="true" />
            <span className="text-text-muted">私有</span>
          </>
        )}
      </button>
    </div>
  )
}
