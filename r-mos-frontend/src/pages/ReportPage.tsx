import { ArrowLeft, FileText } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Empty, Table } from 'antd'

import { getTaskReport } from '@/api/task'
import { DataCard, EmptyState, PageHeader, SectionCard, StatusBadge } from '@/components/common'
import { Button } from '@/components/ui/button'
import type { TaskReport } from '@/types/report'
import { formatDateTime } from '@/utils/format'

type ChecklistEvidence = {
  step_index: number
  evidence_type: 'kit_checklist' | 'verify_checklist'
  evidence_value?: {
    required_items?: string[]
    confirmed_items?: string[]
  }
  is_compliant: boolean
}

type ReportWithChecklistEvidence = TaskReport & {
  checklist_evidence?: ChecklistEvidence[]
}

const ReportPage = () => {
  const { taskId } = useParams<{ taskId: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [report, setReport] = useState<ReportWithChecklistEvidence | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchReport = async () => {
      if (!taskId) {
        setError('缺少 taskId')
        setLoading(false)
        return
      }

      try {
        setLoading(true)
        const response = await getTaskReport(Number(taskId))
        setReport(response)
      } catch (err: unknown) {
        const detail = (err as { response?: { data?: { detail?: string } } } | null)
          ?.response?.data?.detail
        setError(detail || '获取报告失败')
      } finally {
        setLoading(false)
      }
    }

    void fetchReport()
  }, [taskId])

  const columns = [
    {
      title: '步骤',
      dataIndex: 'step_title',
      key: 'step_title',
    },
    {
      title: '得分',
      key: 'score',
      width: 160,
      render: (_: unknown, record: TaskReport['step_scores'][number]) => (
        <span className="font-mono text-text-primary">
          {record.score} / {record.max_score}
        </span>
      ),
    },
    {
      title: '扣分项',
      dataIndex: 'deductions',
      key: 'deductions',
      render: (deductions: Array<{ reason: string; points: number }>) =>
        deductions.length > 0 ? deductions.map((item) => `${item.reason}(-${item.points})`).join('；') : '-',
    },
    {
      title: '备注',
      dataIndex: 'remarks',
      key: 'remarks',
      render: (value: string | undefined) => value || '-',
    },
  ]

  const checklistEvidence = report?.checklist_evidence ?? []
  const kitEvidence = checklistEvidence.filter((item) => item.evidence_type === 'kit_checklist')
  const verifyEvidence = checklistEvidence.filter((item) => item.evidence_type === 'verify_checklist')

  const renderEvidence = (items: ChecklistEvidence[]) => (
    <div className="space-y-3">
      {items.map((item) => {
        const requiredItems = item.evidence_value?.required_items ?? []
        const confirmedItems = new Set(item.evidence_value?.confirmed_items ?? [])
        return (
          <div key={`${item.evidence_type}-${item.step_index}`} className="rounded-lg border border-border-subtle bg-bg-elevated p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <span className="text-sm text-text-secondary">步骤 {item.step_index}</span>
              <StatusBadge label={item.is_compliant ? '通过' : '未通过'} status={item.is_compliant ? 'success' : 'error'} />
            </div>
            <div className="space-y-2">
              {requiredItems.map((requiredItem) => (
                <div key={requiredItem} className="flex items-center justify-between gap-3 text-sm text-text-primary">
                  <span>{requiredItem}</span>
                  <span className={confirmedItems.has(requiredItem) ? 'text-status-success' : 'text-status-error'}>
                    {confirmedItems.has(requiredItem) ? '已确认' : '未确认'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )

  if (!report && !loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="任务报告" subtitle="报告加载失败" breadcrumb={['任务', '报告']} />
        <EmptyState
          description={error ?? '未知错误'}
          icon={FileText}
          title="无法加载报告"
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        actions={
          <Button size="sm" type="button" variant="secondary" onClick={() => navigate('/sops')}>
            <ArrowLeft className="h-4 w-4" />
            返回 SOP 列表
          </Button>
        }
        breadcrumb={['任务', '报告']}
        subtitle={report ? `${report.task_title} · 报告生成于 ${formatDateTime(report.generated_at)}` : '正在加载报告'}
        title="任务报告"
      />

      {report ? (
        <>
          <div className="grid gap-4 xl:grid-cols-4">
            <DataCard
              status={report.is_passed ? 'success' : 'danger'}
              title="最终得分"
              unit="分"
              value={report.final_score}
            />
            <DataCard title="总时长" unit="秒" value={report.total_duration_seconds} />
            <DataCard title="完成步骤" unit="步" value={`${report.completed_steps}/${report.total_steps}`} />
            <DataCard title="错误次数" unit="次" value={report.error_count} />
          </div>

          <SectionCard title="任务摘要">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-lg border border-border-subtle bg-bg-elevated p-4">
                <div className="text-xs uppercase tracking-[0.2em] text-text-muted">SOP</div>
                <div className="mt-2 text-sm text-text-primary">{report.sop_name ?? '未命名 SOP'}</div>
              </div>
              <div className="rounded-lg border border-border-subtle bg-bg-elevated p-4">
                <div className="text-xs uppercase tracking-[0.2em] text-text-muted">通过状态</div>
                <div className="mt-2">
                  <StatusBadge label={report.is_passed ? '通过' : '未通过'} status={report.is_passed ? 'success' : 'error'} />
                </div>
              </div>
              <div className="rounded-lg border border-border-subtle bg-bg-elevated p-4">
                <div className="text-xs uppercase tracking-[0.2em] text-text-muted">开始时间</div>
                <div className="mt-2 text-sm text-text-primary">{formatDateTime(report.started_at)}</div>
              </div>
              <div className="rounded-lg border border-border-subtle bg-bg-elevated p-4">
                <div className="text-xs uppercase tracking-[0.2em] text-text-muted">完成时间</div>
                <div className="mt-2 text-sm text-text-primary">{formatDateTime(report.completed_at)}</div>
              </div>
            </div>
          </SectionCard>

          <SectionCard title="评分分解">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {Object.entries(report.score_breakdown).map(([key, value]) => (
                <div key={key} className="rounded-lg border border-border-subtle bg-bg-elevated p-4">
                  <div className="text-xs uppercase tracking-[0.2em] text-text-muted">{key}</div>
                  <div className="mt-2 font-mono text-2xl text-primary">{value}</div>
                </div>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="步骤得分详情">
            {report.step_scores.length === 0 ? (
              <Empty description="暂无步骤得分" />
            ) : (
              <Table columns={columns} dataSource={report.step_scores} pagination={false} rowKey="step_index" />
            )}
          </SectionCard>

          {kitEvidence.length > 0 ? (
            <SectionCard title="齐套记录">{renderEvidence(kitEvidence)}</SectionCard>
          ) : null}

          {verifyEvidence.length > 0 ? (
            <SectionCard title="验收记录">{renderEvidence(verifyEvidence)}</SectionCard>
          ) : null}

          <SectionCard title="改进建议">
            {report.recommendations.length === 0 ? (
              <Empty description="暂无建议" />
            ) : (
              <div className="space-y-3">
                {report.recommendations.map((item) => (
                  <div key={item} className="rounded-lg border border-border-subtle bg-bg-elevated px-4 py-3 text-sm text-text-secondary">
                    {item}
                  </div>
                ))}
              </div>
            )}
          </SectionCard>

        </>
      ) : null}
    </div>
  )
}

export default ReportPage
