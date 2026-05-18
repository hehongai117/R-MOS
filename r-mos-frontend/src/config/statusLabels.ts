/**
 * Centralized status label / color / variant mappings.
 *
 * Import the relevant constant rather than maintaining local copies in each
 * consumer file.
 */

import { AlertCircle, CheckCircle2, Clock, Loader2 } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

// ---------------------------------------------------------------------------
// Attempt status  (used in TeachingAttemptPage & TeacherMonitorPage)
// ---------------------------------------------------------------------------

/** Variant tokens understood by <StatusBadge status={…} /> */
export type AttemptStatusVariant = 'active' | 'success' | 'warning' | 'pending' | 'idle'

export interface AttemptStatusConfig {
  /** Human-readable Chinese label */
  label: string
  /** StatusBadge `status` prop value */
  variant: AttemptStatusVariant
}

export const ATTEMPT_STATUS: Record<string, AttemptStatusConfig> = {
  in_progress: { label: '进行中', variant: 'active' },
  completed: { label: '已完成', variant: 'success' },
  graded: { label: '已评分', variant: 'success' },
  abandoned: { label: '已放弃', variant: 'warning' },
}

/** Fallback when the status key is unknown */
export const ATTEMPT_STATUS_FALLBACK: AttemptStatusConfig = {
  label: '已放弃',
  variant: 'warning',
}

// ---------------------------------------------------------------------------
// Robot model status  (used in RobotSidebar)
// ---------------------------------------------------------------------------

export interface RobotModelStatusConfig {
  label: string
  className: string
}

export const ROBOT_MODEL_STATUS: Record<string, RobotModelStatusConfig> = {
  draft: { label: '草稿', className: 'text-text-muted' },
  analyzing: { label: '分析中', className: 'text-blue-500' },
  ready: { label: '已发布', className: 'text-green-500' },
}

export const ROBOT_MODEL_STATUS_FALLBACK: RobotModelStatusConfig = ROBOT_MODEL_STATUS.draft

// ---------------------------------------------------------------------------
// Analysis task status  (used in AnalysisStatusPanel)
// ---------------------------------------------------------------------------

export interface AnalysisStatusConfig {
  label: string
  icon: LucideIcon
  className: string
}

export const ANALYSIS_STATUS: Record<string, AnalysisStatusConfig> = {
  pending: { label: '等待中', icon: Clock, className: 'text-text-muted' },
  running: { label: '运行中', icon: Loader2, className: 'text-blue-500' },
  completed: { label: '已完成', icon: CheckCircle2, className: 'text-green-500' },
  failed: { label: '失败', icon: AlertCircle, className: 'text-red-500' },
}

export const ANALYSIS_STATUS_FALLBACK: AnalysisStatusConfig = ANALYSIS_STATUS.pending
