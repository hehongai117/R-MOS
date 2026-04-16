import { ArrowLeft, FileText } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Empty, Table } from 'antd'

import { getTaskReport } from '@/api/task'
import { DataCard, EmptyState, PageHeader, SectionCard, StatusBadge } from '@/components/common'
import { Button } from '@/components/ui/button'
import { DEMO_MODE } from '@/config/demoMode'
import type { TaskReport } from '@/types/report'

function buildDemoReport(): TaskReport {
  const timestamps = JSON.parse(sessionStorage.getItem('demo_step_timestamps') ?? '{}') as Record<string, { start: number; end?: number }>
  const sopName = sessionStorage.getItem('demo_sop_name') ?? 'ATOM-01 左膝关节轴承更换'

  const stepEntries = Object.entries(timestamps)
  const totalDuration = stepEntries.reduce((sum, [, t]) => sum + ((t.end ?? t.start) - t.start), 0)

  const STEP_NAMES = ['安全确认', '工具准备', '外壳拆卸', '轴承定位', '轴承更换', '回装验证']

  return {
    task_id: 0,
    task_title: sopName,
    sop_name: sopName,
    status: 'COMPLETED',
    final_score: 92,
    pass_score: 60,
    is_passed: true,
    total_duration_seconds: Math.max(1, Math.round(totalDuration / 1000)),
    total_steps: 6,
    completed_steps: Math.max(stepEntries.length, 6),
    skipped_steps: 0,
    error_count: 0,
    started_at: stepEntries[0]?.[1]?.start
      ? new Date(stepEntries[0][1].start).toISOString()
      : new Date().toISOString(),
    completed_at: new Date().toISOString(),
    generated_at: new Date().toISOString(),
    score_breakdown: {
      safety: 24,
      procedure: 23,
      precision: 22,
      efficiency: 23,
    },
    step_scores: STEP_NAMES.map((name, i) => ({
      step_index: i,
      step_title: name,
      score: i === 3 ? 14 : 16,
      max_score: 16,
      deductions: i === 3 ? [{ reason: '定位耗时略长', points: 2 }] : [],
      remarks: i === 3 ? '建议加强故障特征识别训练' : '操作规范',
    })),
    recommendations: [
      '整体操作规范，安全意识良好',
      '轴承定位环节可加强磨损特征识别训练',
      '建议下次维保时同步检查相邻关节状态',
    ],
  } as unknown as TaskReport
}

function formatDateTime(value?: string) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN')
}

const ReportPage = () => {
  const { taskId } = useParams<{ taskId: string }>()
  const navigate = useNavigate()
  const isDemoReport = DEMO_MODE && taskId === 'demo'
  const [loading, setLoading] = useState(!isDemoReport)
  const [report, setReport] = useState<TaskReport | null>(isDemoReport ? buildDemoReport() : null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isDemoReport) return

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
  }, [taskId, isDemoReport])

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

      {isDemoReport && (
        <>
          {/* Fault Summary Card */}
          <div className="mb-6 rounded-xl border border-border-subtle bg-bg-elevated/60 p-6">
            <h2 className="mb-4 text-lg font-semibold text-brand-400">故障诊断摘要</h2>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-text-muted">故障类型</span>
                <p className="font-medium text-text-primary">左膝关节轴承磨损</p>
              </div>
              <div>
                <span className="text-text-muted">AI 置信度</span>
                <p className="font-medium text-green-400">92%</p>
              </div>
              <div>
                <span className="text-text-muted">风险评级</span>
                <p className="font-medium text-amber-400">中高</p>
              </div>
              <div>
                <span className="text-text-muted">处置结果</span>
                <p className="font-medium text-green-400">维保完成</p>
              </div>
            </div>
          </div>

          {/* Before/After Comparison */}
          <div className="mb-6 rounded-xl border border-border-subtle bg-bg-elevated/60 p-6">
            <h2 className="mb-4 text-lg font-semibold text-brand-400">维保前后对比</h2>
            <div className="grid grid-cols-2 gap-8">
              <div className="text-center">
                <div className="text-3xl font-bold text-red-400">65°C</div>
                <div className="text-sm text-text-muted">维保前 · 左膝温度</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-green-400">35°C</div>
                <div className="text-sm text-text-muted">维保后 · 左膝温度</div>
              </div>
            </div>
          </div>

          {/* AI Diagnosis Citations */}
          <div className="mb-6 rounded-xl border border-border-subtle bg-bg-elevated/60 p-6">
            <h2 className="mb-4 text-lg font-semibold text-brand-400">诊断证据链</h2>
            <div className="space-y-2">
              {[
                { icon: '🌡️', text: '左膝温度 35→65°C（30s 内）', source: 'KNEE_LEFT.temperature' },
                { icon: '⚙️', text: '左膝扭矩波动 ±2.1Nm', source: 'KNEE_LEFT.torque' },
                { icon: '⚡', text: '左膝电流 2.0→2.8A', source: 'KNEE_LEFT.current' },
                { icon: '📋', text: '上次维保距今 180 天，超出建议周期', source: 'maintenance_log' },
              ].map((c, i) => (
                <div key={i} className="flex items-center gap-3 rounded-lg bg-bg-base/60 px-4 py-2 text-sm">
                  <span>{c.icon}</span>
                  <span className="text-text-primary">{c.text}</span>
                  <span className="ml-auto text-xs text-text-muted">{c.source}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

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

          {isDemoReport && (
            <div className="mt-6 flex justify-center">
              <button
                className="rounded-lg bg-brand-500 px-6 py-3 text-base font-semibold text-white hover:bg-brand-600 transition-colors"
                onClick={() => navigate('/monitor')}
              >
                返回实时监控
              </button>
            </div>
          )}
        </>
      ) : null}
    </div>
  )
}

export default ReportPage
