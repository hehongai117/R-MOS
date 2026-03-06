import { ArrowLeft } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Empty, List } from 'antd'

import { PageHeader, SectionCard, StatusBadge } from '@/components/common'
import { Button } from '@/components/ui/button'

interface Finding {
  code: string
  message: string
  severity: 'info' | 'warning' | 'error' | 'critical'
}

interface Recommendation {
  code: string
  message: string
  priority: 'high' | 'medium' | 'low'
}

const severityColors: Record<Finding['severity'], 'active' | 'warning' | 'error'> = {
  info: 'active',
  warning: 'warning',
  error: 'error',
  critical: 'error',
}

const priorityColors: Record<Recommendation['priority'], 'success' | 'warning' | 'error'> = {
  low: 'success',
  medium: 'warning',
  high: 'error',
}

const DiagnosisPage = () => {
  const { taskId } = useParams<{ taskId: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [diagnosis, setDiagnosis] = useState<{
    root_cause?: string
    root_cause_confidence: number
    findings: Finding[]
    recommendations: Recommendation[]
    evidence_refs: string[]
    baseline_comparison?: {
      baseline_value: number
      actual_value: number
      deviation_percent: number
    }
  } | null>(null)

  useEffect(() => {
    setLoading(true)
    const timer = window.setTimeout(() => {
      setDiagnosis({
        root_cause: 'habit_issue',
        root_cause_confidence: 0.75,
        findings: [
          { code: 'TOO_FAST', message: '操作速度过快，平均耗时 < 5秒', severity: 'warning' },
          { code: 'SKIP_CHECK', message: '检测步骤被跳过', severity: 'error' },
        ],
        recommendations: [
          { code: 'FORCE_PAUSE', message: '强制停顿确认', priority: 'high' },
          { code: 'ADD_CHECKPOINT', message: '添加检查点', priority: 'medium' },
        ],
        evidence_refs: ['ev-001', 'ev-002', 'ev-003'],
        baseline_comparison: {
          baseline_value: 60000,
          actual_value: 45000,
          deviation_percent: -25,
        },
      })
      setLoading(false)
    }, 200)

    return () => window.clearTimeout(timer)
  }, [taskId])

  const rootCauseLabels: Record<string, string> = {
    concept_misunderstanding: '概念理解偏差',
    habit_issue: '操作习惯问题',
    attention_issue: '注意力分散',
    tool_selection_error: '工具选择错误',
    sequence_error: '操作顺序错误',
    unknown: '未知',
  }

  return (
    <div className="space-y-6">
      <PageHeader
        actions={
          <Button size="sm" type="button" variant="secondary" onClick={() => navigate(`/reports/${taskId}`)}>
            <ArrowLeft className="h-4 w-4" />
            返回报告
          </Button>
        }
        breadcrumb={['任务', '诊断报告']}
        subtitle="诊断结果与改进建议统一展示"
        title="诊断报告"
      />

      {!diagnosis && !loading ? (
        <SectionCard title="诊断状态">
          <Empty description="无法加载诊断报告" />
        </SectionCard>
      ) : null}

      {diagnosis ? (
        <>
          <div className="grid gap-4 xl:grid-cols-3">
            <SectionCard title="根因分析">
              <div className="space-y-4">
                <StatusBadge label={rootCauseLabels[diagnosis.root_cause ?? 'unknown']} status="error" />
                <div className="font-mono text-4xl text-primary">
                  {Math.round(diagnosis.root_cause_confidence * 100)}%
                </div>
                <div className="text-sm text-text-muted">根因置信度</div>
              </div>
            </SectionCard>
            <SectionCard title="基线对照">
              {diagnosis.baseline_comparison ? (
                <div className="grid gap-3">
                  <div className="rounded-lg border border-border-subtle bg-bg-elevated p-3">
                    标准时长 {diagnosis.baseline_comparison.baseline_value / 1000} 秒
                  </div>
                  <div className="rounded-lg border border-border-subtle bg-bg-elevated p-3">
                    实际时长 {diagnosis.baseline_comparison.actual_value / 1000} 秒
                  </div>
                  <div className="rounded-lg border border-border-subtle bg-bg-elevated p-3">
                    偏差 {diagnosis.baseline_comparison.deviation_percent.toFixed(0)}%
                  </div>
                </div>
              ) : (
                <Empty description="暂无基线对照" />
              )}
            </SectionCard>
            <SectionCard title="证据引用">
              <div className="flex flex-wrap gap-2">
                {diagnosis.evidence_refs.map((ref) => (
                  <StatusBadge key={ref} label={ref} status="active" />
                ))}
              </div>
            </SectionCard>
          </div>

          <SectionCard title="发现项">
            <List
              dataSource={diagnosis.findings}
              renderItem={(item) => (
                <List.Item>
                  <div className="flex items-center gap-3">
                    <StatusBadge label={item.code} status={severityColors[item.severity]} />
                    <span className="text-sm text-text-secondary">{item.message}</span>
                  </div>
                </List.Item>
              )}
            />
          </SectionCard>

          <SectionCard title="改进建议">
            <List
              dataSource={diagnosis.recommendations}
              renderItem={(item) => (
                <List.Item>
                  <div className="flex items-center gap-3">
                    <StatusBadge label={item.priority} status={priorityColors[item.priority]} />
                    <span className="text-sm text-text-secondary">{item.message}</span>
                  </div>
                </List.Item>
              )}
            />
          </SectionCard>
        </>
      ) : null}
    </div>
  )
}

export default DiagnosisPage
