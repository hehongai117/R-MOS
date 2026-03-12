import { AlertTriangle, CheckCircle2, Wrench } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

import type { DiagnosisResult, FaultHypothesis, MaintenancePlan, VerificationResult } from '@/api/agent-v2'
import { StatusBadge } from '@/components/common'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

export interface DiagnosisPanelProps {
  diagnosisResult: DiagnosisResult | null
  maintenancePlan: MaintenancePlan | null
  verificationResult: VerificationResult | null
  isLoading: boolean
  isActionSubmitting?: boolean
  onConfirmExecution: () => void
  onEscalateToTeacher: () => void
}

export interface DiagnosisSnapshot {
  diagnosisResult: DiagnosisResult | null
  maintenancePlan: MaintenancePlan | null
  verificationResult: VerificationResult | null
  traceId?: string
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

function formatEvidenceValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.map(formatEvidenceValue).join(', ')
  }

  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }

  if (value && typeof value === 'object') {
    return JSON.stringify(value)
  }

  return 'unknown'
}

function buildEvidenceChips(hypothesis: FaultHypothesis): string[] {
  const chips = Object.entries(hypothesis.evidence || {}).map(
    ([key, value]) => `${key}: ${formatEvidenceValue(value)}`,
  )

  return [...chips, ...hypothesis.possible_causes]
}

const verificationMetricLabelMap: Record<string, string> = {
  fault_count: '故障数量',
  error_code: '故障码',
  joint_status: '关节状态',
  joint_position: '关节位置',
  temperature: '温度',
  torque: '扭矩',
  current: '电流',
  voltage: '电压',
  pressure: '压力',
}

const verificationBodyTokenMap: Record<string, string> = {
  ankle: '踝',
  arm: '手臂',
  elbow: '肘',
  hip: '髋',
  knee: '膝',
  shoulder: '肩',
  waist: '腰',
  wrist: '腕',
}

const verificationSideTokenMap: Record<string, string> = {
  left: '左',
  right: '右',
  front: '前',
  rear: '后',
}

function normalizeVerificationKey(key: string): string[] {
  return key
    .replace(/[._]/g, ' ')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
}

function formatVerificationNumber(value: number): string {
  if (Number.isInteger(value)) {
    return String(value)
  }

  return value.toFixed(2).replace(/\.?0+$/, '')
}

function formatBusinessTerm(term: string): string {
  const normalized = term.toLowerCase()
  if (verificationMetricLabelMap[normalized]) {
    return verificationMetricLabelMap[normalized]
  }

  const parts = normalizeVerificationKey(term)
  if (parts.length === 0) {
    return term
  }

  const metricToken = parts[parts.length - 1]?.toLowerCase()
  const metricLabel = verificationMetricLabelMap[metricToken]
  if (metricLabel) {
    const prefixTokens = parts.slice(0, -1)
    const side = prefixTokens
      .map((token) => verificationSideTokenMap[token.toLowerCase()] ?? '')
      .join('')
    const body = prefixTokens
      .map((token) => verificationBodyTokenMap[token.toLowerCase()] ?? '')
      .join('')

    if (side || body) {
      return `${side}${body}${metricLabel}`
    }
  }

  return parts
    .map((token) => verificationBodyTokenMap[token.toLowerCase()] ?? verificationSideTokenMap[token.toLowerCase()] ?? token)
    .join('')
}

function formatVerificationLabel(key: string): string {
  return formatBusinessTerm(key)
}

function formatVerificationValue(value: unknown): string {
  if (typeof value === 'number') {
    return formatVerificationNumber(value)
  }

  if (typeof value === 'boolean') {
    return String(value)
  }

  if (typeof value === 'string') {
    const arrowMatch = value.match(/^\s*(-?\d+(?:\.\d+)?)\s*->\s*(-?\d+(?:\.\d+)?)\s*$/)
    if (arrowMatch) {
      const before = formatVerificationNumber(Number(arrowMatch[1]))
      const after = formatVerificationNumber(Number(arrowMatch[2]))
      return `${before} -> ${after}`
    }
    const asNumber = Number(value)
    if (!Number.isNaN(asNumber) && value.trim() !== '') {
      return formatVerificationNumber(asNumber)
    }
    return value
  }

  if (Array.isArray(value)) {
    return value.map(formatVerificationValue).join('、')
  }

  if (value && typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
    if ('before' in (value as Record<string, unknown>) || 'after' in (value as Record<string, unknown>)) {
      const before = formatVerificationValue((value as Record<string, unknown>).before)
      const after = formatVerificationValue((value as Record<string, unknown>).after)
      return `${before} -> ${after}`
    }
    return entries
      .map(([entryKey, entryValue]) => `${formatVerificationLabel(entryKey)}: ${formatVerificationValue(entryValue)}`)
      .join('；')
  }

  return '未返回'
}

function buildVerificationHighlights(
  verificationResult: VerificationResult | null,
): Array<{ label: string; value: string }> {
  if (!verificationResult) {
    return []
  }

  const highlights = Object.entries(verificationResult.delta_summary || {}).map(([key, value]) => ({
    label: formatVerificationLabel(key),
    value: formatVerificationValue(value),
  }))

  if (highlights.length > 0) {
    return highlights
  }

  const beforeState = verificationResult.before_state || {}
  const afterState = verificationResult.after_state || {}
  return Object.keys({ ...beforeState, ...afterState }).map((key) => ({
    label: formatVerificationLabel(key),
    value: `${formatVerificationValue(beforeState[key])} -> ${formatVerificationValue(afterState[key])}`,
  }))
}

export function DiagnosisPanel({
  diagnosisResult,
  maintenancePlan,
  verificationResult,
  isLoading,
  isActionSubmitting = false,
  onConfirmExecution,
  onEscalateToTeacher,
}: DiagnosisPanelProps) {
  const [animateBars, setAnimateBars] = useState(false)

  const hypotheses = useMemo(() => buildSortedHypotheses(diagnosisResult), [diagnosisResult])
  const verificationHighlights = useMemo(
    () => buildVerificationHighlights(verificationResult),
    [verificationResult],
  )
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
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <div className="font-mono text-2xl text-text-muted">◈</div>
        <div className="mt-2 text-sm font-medium text-text-secondary">等待诊断触发</div>
        <div className="mt-1 text-xs text-text-muted">
          发送"诊断问题"意图后显示
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3">
        {hypotheses.map((hypothesis, index) => {
          const isPrimary = diagnosisResult?.primary_hypothesis?.fault_code === hypothesis.fault_code
          const confidence = Math.round(hypothesis.confidence * 100)
          const evidenceChips = buildEvidenceChips(hypothesis)
          return (
            <div
              key={`${hypothesis.fault_code}-${index}`}
              className={cn(
                'rounded-xl border p-4 transition-colors',
                isPrimary
                  ? 'border-success/30 bg-success/5'
                  : 'border-border-subtle bg-bg-elevated',
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className={cn('text-xs font-medium', isPrimary ? 'text-success' : 'text-text-muted')}>
                    {`H${index + 1} · ${hypothesis.fault_code}`}
                  </div>
                  <div className="mt-1 text-sm font-medium text-text-primary">{hypothesis.fault_name}</div>
                  <div className="mt-1 flex flex-wrap gap-2">
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

              {evidenceChips.length ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {evidenceChips.map((chip) => (
                    <span
                      key={`${hypothesis.fault_code}-${chip}`}
                      className="rounded border border-border-default bg-bg-overlay px-1.5 py-0.5 font-mono text-[10px] text-text-muted"
                    >
                      {chip}
                    </span>
                  ))}
                </div>
              ) : null}
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
            {verificationHighlights.length > 0 ? (
              <div className="space-y-2">
                <div className="text-xs uppercase tracking-[0.18em] text-text-muted">关键变化</div>
                {verificationHighlights.map((highlight) => (
                  <div
                    key={`${highlight.label}-${highlight.value}`}
                    className="rounded-lg border border-border-subtle bg-bg-surface p-3"
                  >
                    <div className="text-xs text-text-muted">{highlight.label}</div>
                    <div className="mt-1 text-sm text-text-primary">{highlight.value}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-text-secondary">仿真已执行，但没有返回可展示的变化摘要。</div>
            )}
            {verificationResult.failed_steps.length ? (
              <div className="text-xs text-danger">失败步骤：{verificationResult.failed_steps.join('、')}</div>
            ) : null}
          </div>
        ) : (
          <div className="text-sm text-text-secondary">暂无仿真验证结果。</div>
        )}
      </div>

      <div className="flex flex-wrap gap-3">
        <Button
          disabled={isActionSubmitting || requiresSupervisor || !maintenancePlan}
          onClick={onConfirmExecution}
        >
          确认执行方案
        </Button>
        <Button disabled={isActionSubmitting} variant="outline" onClick={onEscalateToTeacher}>
          上报教师审核
        </Button>
      </div>
    </div>
  )
}
