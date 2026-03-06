import { ArrowLeft } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Collapse, Empty, List, Spin } from 'antd'

import { getAttemptDiagnosis } from '@/api/teaching'
import { EmptyState, PageHeader, SectionCard, StatusBadge } from '@/components/common'
import { Button } from '@/components/ui/button'
import { formatTeachingError } from '@/teaching/utils/api'
import type { DiagnosisReport, DiagnosisSeverity, StepDiagnosisSourceRefs } from '@/types/teaching'

const severityLabels: Record<DiagnosisSeverity, string> = {
  LOW: '低',
  MEDIUM: '中',
  HIGH: '高',
}

function severityTone(severity: DiagnosisSeverity) {
  if (severity === 'LOW') return 'success'
  if (severity === 'MEDIUM') return 'warning'
  return 'error'
}

function formatStepSourceRefs(refs?: StepDiagnosisSourceRefs) {
  if (!refs) return '-'
  const parts: string[] = []
  if (refs.stepId !== undefined && refs.stepId !== null && refs.stepId !== '') parts.push(`step_id=${refs.stepId}`)
  if (refs.snapshotId !== undefined && refs.snapshotId !== null && refs.snapshotId !== '') parts.push(`snapshot_id=${refs.snapshotId}`)
  return parts.length > 0 ? parts.join(', ') : '-'
}

const TeachingDiagnosisPage = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const attemptId = Number(id)

  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<DiagnosisReport | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      if (!attemptId) {
        setErrorMessage('无效的尝试 ID')
        setLoading(false)
        return
      }
      setLoading(true)
      setErrorMessage(null)
      try {
        const response = await getAttemptDiagnosis(attemptId)
        setData(response)
      } catch (err: unknown) {
        setErrorMessage(formatTeachingError(err, '加载诊断报告失败'))
      } finally {
        setLoading(false)
      }
    }

    void fetchData()
  }, [attemptId])

  if (loading) {
    return (
      <div className="flex min-h-[420px] items-center justify-center">
        <Spin size="large" />
      </div>
    )
  }

  if (!data) {
    return (
      <div className="space-y-6">
        <PageHeader title="诊断报告" subtitle="未找到诊断报告" breadcrumb={['教学域', '诊断报告']} />
        <EmptyState description={errorMessage ?? '未找到诊断报告'} icon={ArrowLeft} title="诊断报告不存在" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        actions={
          <Button size="sm" type="button" variant="secondary" onClick={() => navigate(`/teaching/attempts/${attemptId}`)}>
            <ArrowLeft className="h-4 w-4" />
            返回尝试页面
          </Button>
        }
        breadcrumb={['教学域', '诊断报告']}
        subtitle="面向教师的可解释诊断结果"
        title="诊断报告"
      />

      <SectionCard title="诊断摘要">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <div className="rounded-lg border border-border-subtle bg-bg-elevated p-4">
            <div className="text-xs uppercase tracking-[0.2em] text-text-muted">尝试编号</div>
            <div className="mt-2 font-mono text-text-primary">{data.attemptId}</div>
          </div>
          <div className="rounded-lg border border-border-subtle bg-bg-elevated p-4">
            <div className="text-xs uppercase tracking-[0.2em] text-text-muted">诊断代码</div>
            <div className="mt-2 text-text-primary">{data.diagnosisCode}</div>
          </div>
          <div className="rounded-lg border border-border-subtle bg-bg-elevated p-4">
            <div className="text-xs uppercase tracking-[0.2em] text-text-muted">严重等级</div>
            <div className="mt-2">
              <StatusBadge label={severityLabels[data.severity]} status={severityTone(data.severity)} />
            </div>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="诊断发现">
        {data.findings.length === 0 ? (
          <Empty description="无诊断发现" />
        ) : (
          <List dataSource={data.findings} renderItem={(item) => <List.Item>{item}</List.Item>} />
        )}
      </SectionCard>

      <SectionCard title="建议">
        {data.recommendations.length === 0 ? (
          <Empty description="无建议" />
        ) : (
          <List dataSource={data.recommendations} renderItem={(item) => <List.Item>{item}</List.Item>} />
        )}
      </SectionCard>

      <SectionCard title="步骤诊断">
        {data.stepDiagnoses.length === 0 ? (
          <Empty description="无步骤诊断" />
        ) : (
          <Collapse
            accordion
            items={data.stepDiagnoses.map((step) => ({
              key: String(step.stepIndex),
              label: (
                <div className="flex items-center gap-2">
                  <span>步骤 {step.stepIndex}</span>
                  <StatusBadge label={severityLabels[step.severity]} status={severityTone(step.severity)} />
                  <span className="text-xs text-text-muted">{step.stepDiagnosisCode}</span>
                </div>
              ),
              children: (
                <div className="space-y-4">
                  <div className="text-sm text-text-secondary">证据关联：{formatStepSourceRefs(step.sourceRefs)}</div>
                  <div>
                    <div className="mb-2 text-sm font-medium text-text-primary">诊断发现</div>
                    {step.findings.length === 0 ? <Empty description="无" /> : <List dataSource={step.findings} renderItem={(item) => <List.Item>{item}</List.Item>} />}
                  </div>
                  <div>
                    <div className="mb-2 text-sm font-medium text-text-primary">建议</div>
                    {step.recommendations.length === 0 ? <Empty description="无" /> : <List dataSource={step.recommendations} renderItem={(item) => <List.Item>{item}</List.Item>} />}
                  </div>
                </div>
              ),
            }))}
          />
        )}
      </SectionCard>
    </div>
  )
}

export default TeachingDiagnosisPage
