import { AlertTriangle, CheckCircle2, FileSearch, Wrench } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

import type { DiagnosisResult, FaultHypothesis, MaintenancePlan, VerificationResult } from '@/api/agent-v2'
import { EmptyState, StatusBadge } from '@/components/common'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

export interface DiagnosisPanelProps {
  diagnosisResult: DiagnosisResult | null
  maintenancePlan: MaintenancePlan | null
  verificationResult: VerificationResult | null
  isLoading: boolean
  onConfirmExecution: () => void
  onEscalateToTeacher: () => void
}

export interface DiagnosisSnapshot {
  diagnosisResult: DiagnosisResult | null
  maintenancePlan: MaintenancePlan | null
  verificationResult: VerificationResult | null
  timestamp: number
}

export const LATEST_DIAGNOSIS_STORAGE_KEY = 'latest-diagnosis-result'

export function persistLatestDiagnosisResult(snapshot: DiagnosisSnapshot) {
  if (typeof window === 'undefined') {
    return
  }

  window.sessionStorage.setItem(LATEST_DIAGNOSIS_STORAGE_KEY, JSON.stringify(snapshot))
}

export function readLatestDiagnosisResult(): DiagnosisSnapshot | null {
  if (typeof window === 'undefined') {
    return null
  }

  const raw = window.sessionStorage.getItem(LATEST_DIAGNOSIS_STORAGE_KEY)
  if (!raw) {
    return null
  }

  try {
    return JSON.parse(raw) as DiagnosisSnapshot
  } catch {
    window.sessionStorage.removeItem(LATEST_DIAGNOSIS_STORAGE_KEY)
    return null
  }
}

function buildSortedHypotheses(diagnosisResult: DiagnosisResult | null): FaultHypothesis[] {
  if (!diagnosisResult) {
    return []
  }

  const hypotheses = [
    ...(diagnosisResult.primary_hypothesis ? [diagnosisResult.primary_hypothesis] : []),
    ...diagnosisResult.alternative_hypotheses,
  ]

  const deduped = new Map<string, FaultHypothesis>()
  hypotheses.forEach((hypothesis) => {
    const existing = deduped.get(hypothesis.fault_code)
    if (!existing || hypothesis.confidence > existing.confidence) {
      deduped.set(hypothesis.fault_code, hypothesis)
    }
  })

  return [...deduped.values()].sort((left, right) => right.confidence - left.confidence)
}

export function DiagnosisPanel({
  diagnosisResult,
  maintenancePlan,
  verificationResult,
  isLoading,
  onConfirmExecution,
  onEscalateToTeacher,
}: DiagnosisPanelProps) {
  const [animateBars, setAnimateBars] = useState(false)

  const hypotheses = useMemo(() => buildSortedHypotheses(diagnosisResult), [diagnosisResult])
  const requiresSupervisor = diagnosisResult?.requires_supervisor || maintenancePlan?.requires_supervisor || false

  useEffect(() => {
    setAnimateBars(false)
    if (!diagnosisResult) {
      return
    }

    const timer = window.setTimeout(() => setAnimateBars(true), 30)
    return () => window.clearTimeout(timer)
  }, [diagnosisResult])

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="grid gap-3">
          <Skeleton className="h-24 rounded-xl" />
          <Skeleton className="h-24 rounded-xl" />
        </div>
        <Skeleton className="h-28 rounded-xl" />
        <Skeleton className="h-28 rounded-xl" />
      </div>
    )
  }

  if (!diagnosisResult && !maintenancePlan && !verificationResult) {
    return (
      <EmptyState
        icon={FileSearch}
        title="暂无诊断结果"
        description="发起一次诊断后，故障推理、维保方案和仿真验证会显示在这里。"
      />
    )
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3">
        {hypotheses.map((hypothesis, index) => {
          const isPrimary = diagnosisResult?.primary_hypothesis?.fault_code === hypothesis.fault_code
          const confidence = Math.round(hypothesis.confidence * 100)
          return (
            <div
              key={`${hypothesis.fault_code}-${index}`}
              className={cn(
                'rounded-xl border p-4 transition-colors',
                isPrimary
                  ? 'border-success/40 bg-success/10'
                  : 'border-border-subtle bg-bg-elevated',
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-medium text-text-primary">{hypothesis.fault_name}</div>
                  <div className="mt-1 flex flex-wrap gap-2">
                    <StatusBadge status={isPrimary ? 'success' : 'pending'} label={hypothesis.fault_code} />
                    {isPrimary ? <StatusBadge status="active" label="主假设" /> : <StatusBadge status="idle" label="备选假设" />}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs uppercase tracking-[0.18em] text-text-muted">置信度</div>
                  <div className="mt-1 text-lg font-semibold text-text-primary">{confidence}%</div>
                </div>
              </div>

              <div className="mt-3 h-2 overflow-hidden rounded-full bg-bg-overlay">
                <div
                  className={cn(
                    'h-full rounded-full transition-[width] duration-500 ease-out',
                    isPrimary ? 'bg-success' : 'bg-text-secondary',
                  )}
                  style={{ width: `${animateBars ? confidence : 0}%` }}
                />
              </div>

              <div className="mt-3 flex flex-wrap gap-2 text-xs text-text-secondary">
                {hypothesis.affected_parts.map((part) => (
                  <span key={part} className="rounded-full border border-border-default px-2 py-1">
                    {part}
                  </span>
                ))}
              </div>
            </div>
          )
        })}
      </div>

      <div className="rounded-xl border border-border-subtle bg-bg-elevated p-4">
        <div className="mb-2 flex items-center gap-2 text-sm font-medium text-text-primary">
          <AlertTriangle className="h-4 w-4 text-amber" />
          因果链
        </div>
        <p className="whitespace-pre-wrap text-sm leading-6 text-text-secondary">
          {diagnosisResult?.reasoning || '诊断链路未返回解释文本。'}
        </p>
        {(diagnosisResult?.recommended_actions?.length || 0) > 0 ? (
          <div className="mt-3 space-y-2">
            <div className="text-xs uppercase tracking-[0.18em] text-text-muted">建议动作</div>
            <div className="space-y-1 text-sm text-text-secondary">
              {diagnosisResult?.recommended_actions.map((action) => (
                <div key={action}>• {action}</div>
              ))}
            </div>
          </div>
        ) : null}
      </div>

      <div className="rounded-xl border border-border-subtle bg-bg-elevated p-4">
        <div className="mb-3 flex items-center gap-2 text-sm font-medium text-text-primary">
          <Wrench className="h-4 w-4 text-primary" />
          维保方案
        </div>
        {maintenancePlan?.actions?.length ? (
          <div className="space-y-3">
            {maintenancePlan.actions.map((action, index) => (
              <div key={action.action_id} className="rounded-lg border border-border-subtle bg-bg-surface p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-sm font-medium text-text-primary">
                      {index + 1}. {action.description}
                    </div>
                    <div className="mt-1 text-xs text-text-muted">
                      {action.action_type} · {action.target_part} · 预计 {action.estimated_duration_minutes} 分钟
                    </div>
                  </div>
                  <StatusBadge status="pending" label={action.action_type} />
                </div>
                {action.required_tools.length ? (
                  <div className="mt-2 text-xs text-text-secondary">
                    工具：{action.required_tools.join('、')}
                  </div>
                ) : null}
                {action.safety_warnings.length ? (
                  <div className="mt-2 text-xs text-amber">
                    安全提示：{action.safety_warnings.join('；')}
                  </div>
                ) : null}
              </div>
            ))}
            <div className="flex flex-wrap gap-2">
              <StatusBadge status="active" label={`总时长 ${maintenancePlan.total_duration_minutes} 分钟`} />
              {maintenancePlan.validation_required ? <StatusBadge status="warning" label="需验证" /> : null}
              {requiresSupervisor ? <StatusBadge status="error" label="需教师审核" /> : null}
            </div>
          </div>
        ) : (
          <div className="text-sm text-text-secondary">暂无维保步骤。</div>
        )}
      </div>

      <div className="rounded-xl border border-border-subtle bg-bg-elevated p-4">
        <div className="mb-3 flex items-center gap-2 text-sm font-medium text-text-primary">
          <CheckCircle2 className={cn('h-4 w-4', verificationResult?.success ? 'text-success' : 'text-danger')} />
          仿真验证
        </div>
        {verificationResult ? (
          <div className="space-y-2">
            <StatusBadge
              status={verificationResult.success ? 'success' : 'error'}
              label={verificationResult.verdict || (verificationResult.success ? '验证通过' : '验证未通过')}
            />
            {Object.keys(verificationResult.delta_summary || {}).length > 0 ? (
              <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg bg-bg-overlay p-3 text-xs text-text-secondary">
                {JSON.stringify(verificationResult.delta_summary, null, 2)}
              </pre>
            ) : null}
            {verificationResult.failed_steps.length ? (
              <div className="text-xs text-danger">失败步骤：{verificationResult.failed_steps.join('、')}</div>
            ) : null}
          </div>
        ) : (
          <div className="text-sm text-text-secondary">暂无仿真验证结果。</div>
        )}
      </div>

      <div className="flex flex-wrap gap-3">
        <Button disabled={requiresSupervisor || !maintenancePlan} onClick={onConfirmExecution}>
          确认执行方案
        </Button>
        <Button variant="outline" onClick={onEscalateToTeacher}>
          上报教师审核
        </Button>
      </div>
    </div>
  )
}
