import { Download, RefreshCw } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Empty, Table } from 'antd'
import type { ColumnsType } from 'antd/es/table'

import { getAcceptanceReports, getCurrentMetrics, type MetricRecord } from '@/api/agent-v2'
import { DataCard, EmptyState, PageHeader, SectionCard, StatusBadge } from '@/components/common'
import { Button } from '@/components/ui/button'

interface HistoryRow {
  report_id: string
  timestamp: number
  passed: number
  failed: number
  warnings: number
  recommendation: string
}

function statusTone(status: string) {
  if (status === 'pass') {
    return 'success'
  }
  if (status === 'warning') {
    return 'warning'
  }
  if (status === 'fail') {
    return 'error'
  }
  return 'idle'
}

function formatDateTime(value?: number | string) {
  if (!value) {
    return '-'
  }
  return new Date(value).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const LLMMetricsPage = () => {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [metrics, setMetrics] = useState<MetricRecord[]>([])
  const [history, setHistory] = useState<HistoryRow[]>([])

  const loadMetrics = async () => {
    setLoading(true)
    setError(null)
    try {
      const [current, reports] = await Promise.all([getCurrentMetrics(), getAcceptanceReports(10)])
      setMetrics(current.metrics)
      setHistory(reports.reports)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : '评测指标加载失败')
      setMetrics([])
      setHistory([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadMetrics()
  }, [])

  const summary = useMemo(() => {
    const passed = metrics.filter((item) => item.status === 'pass').length
    const failed = metrics.filter((item) => item.status === 'fail').length
    const warnings = metrics.filter((item) => item.status === 'warning').length
    return {
      passed,
      failed,
      warnings,
      average:
        metrics.length > 0
          ? Number((metrics.reduce((acc, item) => acc + item.actual_value, 0) / metrics.length).toFixed(1))
          : 0,
    }
  }, [metrics])

  const columns: ColumnsType<MetricRecord> = [
    {
      title: '指标 ID',
      dataIndex: 'metric_id',
      key: 'metric_id',
      width: 180,
      render: (value: string) => <span className="font-mono text-xs text-text-secondary">{value}</span>,
    },
    {
      title: '指标名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 140,
    },
    {
      title: '当前值',
      dataIndex: 'actual_value',
      key: 'actual_value',
      width: 140,
      render: (value: number) => <span className="font-mono text-text-primary">{value.toFixed(1)}%</span>,
    },
    {
      title: '目标值',
      dataIndex: 'target_value',
      key: 'target_value',
      width: 140,
      render: (value: number) => <span className="font-mono text-text-secondary">{value}%</span>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 140,
      render: (value: string) => <StatusBadge label={value} status={statusTone(value)} />,
    },
    {
      title: '详情',
      dataIndex: 'details',
      key: 'details',
      render: (value: Record<string, unknown> | undefined) => (
        <div className="max-w-[360px] text-xs text-text-muted">
          {value ? JSON.stringify(value) : '-'}
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        actions={
          <div className="flex gap-2">
            <Button size="sm" type="button" variant="secondary" onClick={() => void loadMetrics()}>
              <RefreshCw className="h-4 w-4" />
              刷新
            </Button>
            <Button size="sm" type="button" variant="outline" disabled>
              <Download className="h-4 w-4" />
              导出报告
            </Button>
          </div>
        }
        breadcrumb={['管理员', 'LLM 指标']}
        subtitle="已切换到真实 /agent/metrics 与 /agent/metrics/reports 接口，不再使用 mock period 结构"
        title="LLM 评测指标仪表板"
      />

      <div className="grid gap-4 xl:grid-cols-4">
        <DataCard status="success" title="通过指标" unit="项" value={summary.passed} />
        <DataCard status="warning" title="警告指标" unit="项" value={summary.warnings} />
        <DataCard status="danger" title="失败指标" unit="项" value={summary.failed} />
        <DataCard title="平均得分" trendValue={`${metrics.length} 项指标`} unit="%" value={summary.average} />
      </div>

      {error ? (
        <EmptyState
          description={error}
          icon={RefreshCw}
          title="指标加载失败"
        />
      ) : null}

      <SectionCard title="当前指标详情">
        {metrics.length === 0 && !loading ? (
          <Empty description="暂无指标数据" />
        ) : (
          <Table
            columns={columns}
            dataSource={metrics}
            loading={loading}
            pagination={false}
            rowKey="metric_id"
          />
        )}
      </SectionCard>

      <SectionCard title="历史报告">
        {history.length === 0 && !loading ? (
          <Empty description="暂无历史报告" />
        ) : (
          <div className="space-y-3">
            {history.map((report) => (
              <div
                key={report.report_id}
                className="rounded-lg border border-border-subtle bg-bg-elevated px-4 py-3"
              >
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="text-sm text-text-primary">{formatDateTime(report.timestamp)}</div>
                    <div className="mt-1 text-xs text-text-muted">{report.recommendation}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge label={`通过 ${report.passed}`} status="success" />
                    <StatusBadge label={`警告 ${report.warnings}`} status="warning" />
                    <StatusBadge label={`失败 ${report.failed}`} status="error" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </SectionCard>
    </div>
  )
}

export default LLMMetricsPage
