import { ClipboardCheck } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Empty, Table } from 'antd'
import type { ColumnsType } from 'antd/es/table'

import { getCurrentMetrics, type MetricRecord } from '@/api/agent-v2'
import { DataCard, EmptyState, PageHeader, SectionCard, StatusBadge } from '@/components/common'
import { Button } from '@/components/ui/button'

function statusTone(status: string) {
  if (status === 'pass') return 'success'
  if (status === 'warning') return 'warning'
  if (status === 'fail') return 'error'
  return 'idle'
}

const AcceptanceDashboardPage = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [metrics, setMetrics] = useState<MetricRecord[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadMetrics = async () => {
      setLoading(true)
      setError(null)
      try {
        const response = await getCurrentMetrics()
        setMetrics(response.metrics)
      } catch {
        setMetrics([])
        setError('无法从服务器获取验收指标数据，请检查后端服务是否正常运行。')
      } finally {
        setLoading(false)
      }
    }

    void loadMetrics()
  }, [])

  const summary = useMemo(() => {
    const passed = metrics.filter((metric) => metric.status === 'pass').length
    const failed = metrics.filter((metric) => metric.status === 'fail').length
    const warnings = metrics.filter((metric) => metric.status === 'warning').length
    return { passed, failed, warnings }
  }, [metrics])

  const columns: ColumnsType<MetricRecord> = [
    {
      title: '指标 ID',
      dataIndex: 'metric_id',
      key: 'metric_id',
      render: (value: string) => <span className="font-mono text-xs text-text-secondary">{value}</span>,
    },
    {
      title: '指标名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '目标值',
      dataIndex: 'target_value',
      key: 'target_value',
      render: (value: number) => <span className="font-mono text-text-secondary">{value}%</span>,
    },
    {
      title: '实际值',
      dataIndex: 'actual_value',
      key: 'actual_value',
      render: (value: number) => <span className="font-mono text-text-primary">{value.toFixed(1)}%</span>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (value: string) => <StatusBadge label={value} status={statusTone(value)} />,
    },
    {
      title: '详情',
      dataIndex: 'details',
      key: 'details',
      render: (value: Record<string, unknown> | undefined) => (
        <div className="max-w-[320px] text-xs text-text-muted">
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
            <Button size="sm" type="button" variant="secondary" onClick={() => navigate('/agent/replay')}>
              执行回放
            </Button>
            <Button size="sm" type="button" variant="secondary" onClick={() => navigate('/admin/approvals')}>
              审批队列
            </Button>
          </div>
        }
        breadcrumb={['管理员', '验收仪表盘']}
        subtitle="当前验收指标快照与结论统一展示"
        title="验收仪表盘"
      />

      {error ? <EmptyState description={error} icon={ClipboardCheck} title="数据加载失败" /> : null}

      <div className="grid gap-4 xl:grid-cols-4">
        <DataCard title="总指标数" unit="项" value={metrics.length} />
        <DataCard status="success" title="通过" unit="项" value={summary.passed} />
        <DataCard status="danger" title="失败" unit="项" value={summary.failed} />
        <DataCard status="warning" title="警告" unit="项" value={summary.warnings} />
      </div>

      <SectionCard title="验收结论">
        <div className="rounded-lg border border-border-subtle bg-bg-elevated p-4 text-sm text-text-secondary">
          {summary.failed > 0
            ? '验收失败，需要修复关键指标。'
            : summary.warnings > 0
              ? '基本通过，但仍有待改进项。'
              : '全部指标通过验收。'}
        </div>
      </SectionCard>

      <SectionCard title="验收指标详情">
        {metrics.length === 0 && !loading ? (
          <Empty description="暂无指标数据" />
        ) : (
          <Table columns={columns} dataSource={metrics} loading={loading} pagination={false} rowKey="metric_id" />
        )}
      </SectionCard>

      <SectionCard title="指标说明">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-lg border border-border-subtle bg-bg-elevated p-4 text-sm text-text-secondary">
            <div className="font-mono text-text-primary">M-ENTRY-001</div>
            <div className="mt-2">外部写入口唯一性，目标 100%。</div>
          </div>
          <div className="rounded-lg border border-border-subtle bg-bg-elevated p-4 text-sm text-text-secondary">
            <div className="font-mono text-text-primary">M-OBJ-001</div>
            <div className="mt-2">写请求对象绑定率，目标 100%。</div>
          </div>
          <div className="rounded-lg border border-border-subtle bg-bg-elevated p-4 text-sm text-text-secondary">
            <div className="font-mono text-text-primary">M-REPLAY-002</div>
            <div className="mt-2">可复算 trace 覆盖率，目标 &gt;= 98%。</div>
          </div>
          <div className="rounded-lg border border-border-subtle bg-bg-elevated p-4 text-sm text-text-secondary">
            <div className="font-mono text-text-primary">M-SAFE-001</div>
            <div className="mt-2">越权写放行率，目标 0%。</div>
          </div>
        </div>
      </SectionCard>
    </div>
  )
}

export default AcceptanceDashboardPage
