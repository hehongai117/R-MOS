import { LayoutDashboard, ShieldCheck } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  getAdminUsers,
  getMonitorAlerts,
  getMonitorHealth,
  getMonitorMetrics,
  getMonitorMetricsHistory,
  getSystemHealth,
  type MonitorAlert,
  type MonitorMetricsResponse,
} from '@/api/adminConsole'
import { listApprovals, type ApprovalRecord } from '@/api/approvals'
import { getAcceptanceReports, getCurrentMetrics, type MetricRecord } from '@/api/agent-v2'
import { DataCard, EmptyState, PageHeader, SectionCard, StatusBadge } from '@/components/common'
import { Progress } from '@/components/ui/progress'

const REFRESH_INTERVAL_MS = 30000

function formatDateTime(value?: string | number | null) {
  if (!value) {
    return '暂无'
  }

  return new Date(value).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function overallStatusTone(status?: string) {
  const normalized = status?.toLowerCase()
  if (!normalized) {
    return 'idle'
  }
  if (normalized.includes('healthy') || normalized.includes('ok') || normalized.includes('pass')) {
    return 'success'
  }
  if (normalized.includes('warn') || normalized.includes('degraded')) {
    return 'warning'
  }
  return 'error'
}

function AdminDashboardPage() {
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [userTotal, setUserTotal] = useState(0)
  const [approvalsCount, setApprovalsCount] = useState(0)
  const [pendingApprovals, setPendingApprovals] = useState<ApprovalRecord[]>([])
  const [metrics, setMetrics] = useState<MetricRecord[]>([])
  const [metricReports, setMetricReports] = useState<
    Array<{
      report_id: string
      timestamp: number
      total_metrics: number
      passed: number
      failed: number
      warnings: number
      recommendation: string
    }>
  >([])
  const [monitorHealth, setMonitorHealth] = useState<Record<string, unknown> | null>(null)
  const [monitorMetrics, setMonitorMetrics] = useState<MonitorMetricsResponse | null>(null)
  const [monitorHistory, setMonitorHistory] = useState<MonitorMetricsResponse[]>([])
  const [alerts, setAlerts] = useState<MonitorAlert[]>([])
  const [systemHealth, setSystemHealth] = useState<Record<string, unknown> | null>(null)

  useEffect(() => {
    let alive = true

    async function loadDashboard() {
      setError(null)

      try {
        const [
          usersResponse,
          approvalsResponse,
          metricsResponse,
          reportsResponse,
          monitorHealthResponse,
          monitorMetricsResponse,
          monitorHistoryResponse,
          alertsResponse,
          systemHealthResponse,
        ] = await Promise.all([
          getAdminUsers(200),
          listApprovals({ status: 'pending', limit: 5, offset: 0 }),
          getCurrentMetrics(),
          getAcceptanceReports(10),
          getMonitorHealth(),
          getMonitorMetrics(),
          getMonitorMetricsHistory(100),
          getMonitorAlerts(5),
          getSystemHealth(),
        ])

        if (!alive) {
          return
        }

        setUserTotal(usersResponse.total)
        setApprovalsCount(approvalsResponse.count)
        setPendingApprovals(approvalsResponse.items)
        setMetrics(metricsResponse.metrics)
        setMetricReports(reportsResponse.reports)
        setMonitorHealth(monitorHealthResponse as Record<string, unknown>)
        setMonitorMetrics(monitorMetricsResponse)
        setMonitorHistory(monitorHistoryResponse.metrics)
        setAlerts(alertsResponse.alerts)
        setSystemHealth(systemHealthResponse as unknown as Record<string, unknown>)
        setLastUpdatedAt(new Date())
      } catch (requestError) {
        if (alive) {
          setError(requestError instanceof Error ? requestError.message : '管理员首页加载失败')
        }
      }
    }

    void loadDashboard()
    const timer = window.setInterval(() => {
      void loadDashboard()
    }, REFRESH_INTERVAL_MS)

    return () => {
      alive = false
      window.clearInterval(timer)
    }
  }, [])

  const passedMetrics = useMemo(
    () => metrics.filter((item) => item.status === 'pass').length,
    [metrics],
  )
  const metricPassRate = useMemo(
    () => (metrics.length > 0 ? Math.round((passedMetrics / metrics.length) * 100) : 0),
    [metrics, passedMetrics],
  )

  const overallStatus =
    (monitorHealth?.overall_status as string | undefined) ??
    (monitorHealth?.status as string | undefined) ??
    (systemHealth?.status as string | undefined) ??
    'unknown'

  return (
    <div className="space-y-6">
      <PageHeader
        actions={
          <div className="font-mono text-xs text-text-muted">
            最后更新 {lastUpdatedAt ? formatDateTime(lastUpdatedAt.toISOString()) : '等待首次拉取'}
          </div>
        }
        breadcrumb={['管理员', '系统概览']}
        subtitle="用户规模、审批、验收指标与系统监控按 30 秒自动刷新"
        title="系统概览"
      />

      <div className="grid gap-4 xl:grid-cols-4">
        <DataCard title="用户总数" unit="人" value={userTotal} />
        <DataCard
          status={approvalsCount > 0 ? 'warning' : 'success'}
          title="待处理审批"
          unit="条"
          value={approvalsCount}
        />
        <DataCard
          status={metricPassRate >= 80 ? 'success' : 'warning'}
          title="指标通过率"
          trendValue={`${passedMetrics}/${metrics.length || 0} 通过`}
          unit="%"
          value={metricPassRate}
        />
        <DataCard
          status={overallStatusTone(overallStatus) === 'success' ? 'success' : 'warning'}
          title="系统总体状态"
          trendValue={String(overallStatus)}
          value={String(overallStatus).toUpperCase()}
        />
      </div>

      {error ? (
        <EmptyState
          description={error}
          icon={LayoutDashboard}
          title="系统概览加载失败"
        />
      ) : null}

      <div className="grid gap-4 xl:grid-cols-3">
        <SectionCard className="xl:col-span-2" title="评测指标概览 / 历史报告">
          <div className="space-y-4">
            <div className="grid gap-3 md:grid-cols-3">
              {metrics.slice(0, 3).map((metric) => (
                <div
                  key={metric.metric_id}
                  className="rounded-lg border border-border-subtle bg-bg-elevated p-4"
                >
                  <div className="text-xs uppercase tracking-[0.2em] text-text-muted">
                    {metric.metric_id}
                  </div>
                  <div className="mt-2 text-sm text-text-primary">{metric.name}</div>
                  <div className="mt-3 flex items-center justify-between">
                    <span className="font-mono text-lg text-primary">{metric.actual_value.toFixed(1)}%</span>
                    <StatusBadge
                      label={metric.status}
                      status={metric.status === 'pass' ? 'success' : metric.status === 'warning' ? 'warning' : 'error'}
                    />
                  </div>
                </div>
              ))}
            </div>

            <div className="space-y-3">
              {metricReports.slice(0, 5).map((report) => (
                <div
                  key={report.report_id}
                  className="flex items-center justify-between rounded-lg border border-border-subtle bg-bg-elevated px-4 py-3"
                >
                  <div>
                    <div className="text-sm text-text-primary">{formatDateTime(report.timestamp)}</div>
                    <div className="mt-1 text-xs text-text-muted">{report.recommendation}</div>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusBadge label={`通过 ${report.passed}`} status="success" />
                    <StatusBadge label={`警告 ${report.warnings}`} status="warning" />
                    <StatusBadge label={`失败 ${report.failed}`} status="error" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </SectionCard>

        <SectionCard title="待处理审批">
          <div className="space-y-3">
            {approvalsCount === 0 ? (
              <EmptyState
                description="当前没有待处理审批。"
                icon={ShieldCheck}
                title="审批队列清空"
              />
            ) : (
              <>
                <div className="space-y-3">
                  {pendingApprovals.map((approval) => (
                    <div
                      key={approval.id}
                      className="rounded-lg border border-border-subtle bg-bg-elevated px-4 py-3"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <div className="text-sm text-text-primary">
                            审批 #{approval.id} · {approval.reason ?? '待处理审批'}
                          </div>
                          <div className="mt-1 text-xs text-text-muted">
                            trace {approval.trace_id ?? '--'} · {formatDateTime(approval.created_at)}
                          </div>
                        </div>
                        <StatusBadge label={approval.status} status="warning" />
                      </div>
                    </div>
                  ))}
                </div>
                <Link className="text-sm text-primary underline-offset-4 hover:underline" to="/admin/approvals">
                  查看全部待审批
                </Link>
              </>
            )}
          </div>
        </SectionCard>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <SectionCard title="近期告警">
          <div className="space-y-3">
            {alerts.length > 0 ? (
              alerts.map((alert) => (
                <div
                  key={alert.alert_id}
                  className="rounded-lg border border-border-subtle bg-bg-elevated px-4 py-3"
                >
                  <div className="flex items-center justify-between">
                    <div className="text-sm text-text-primary">{alert.message}</div>
                    <StatusBadge
                      label={alert.level}
                      status={alert.level === 'critical' ? 'error' : alert.level === 'warning' ? 'warning' : 'active'}
                    />
                  </div>
                  <div className="mt-1 text-xs text-text-muted">
                    {alert.component} · {formatDateTime(alert.created_at)}
                  </div>
                </div>
              ))
            ) : (
              <EmptyState
                description="当前没有新告警。"
                icon={ShieldCheck}
                title="近期无告警"
              />
            )}
          </div>
        </SectionCard>

        <SectionCard title="系统健康">
          <div className="space-y-4">
            <div className="flex items-center justify-between rounded-lg border border-border-subtle bg-bg-elevated px-4 py-3">
              <div>
                <div className="text-xs uppercase tracking-[0.2em] text-text-muted">Overall</div>
                <div className="mt-2 text-2xl font-mono text-text-primary">{String(overallStatus).toUpperCase()}</div>
              </div>
              <StatusBadge label={String(overallStatus)} status={overallStatusTone(overallStatus)} />
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-border-subtle bg-bg-elevated p-4">
                <div className="mb-2 text-sm text-text-primary">CPU</div>
                <Progress value={monitorMetrics?.cpu_percent ?? 0} />
                <div className="mt-2 font-mono text-xs text-text-muted">
                  {(monitorMetrics?.cpu_percent ?? 0).toFixed(1)}%
                </div>
              </div>
              <div className="rounded-lg border border-border-subtle bg-bg-elevated p-4">
                <div className="mb-2 text-sm text-text-primary">内存</div>
                <Progress value={monitorMetrics?.memory_percent ?? 0} />
                <div className="mt-2 font-mono text-xs text-text-muted">
                  {(monitorMetrics?.memory_percent ?? 0).toFixed(1)}%
                </div>
              </div>
              <div className="rounded-lg border border-border-subtle bg-bg-elevated p-4">
                <div className="mb-2 text-sm text-text-primary">磁盘</div>
                <Progress value={monitorMetrics?.disk_percent ?? 0} />
                <div className="mt-2 font-mono text-xs text-text-muted">
                  {(monitorMetrics?.disk_percent ?? 0).toFixed(1)}%
                </div>
              </div>
              <div className="rounded-lg border border-border-subtle bg-bg-elevated p-4">
                <div className="mb-2 text-sm text-text-primary">历史样本</div>
                <div className="font-mono text-2xl text-primary">{monitorHistory.length}</div>
                <div className="mt-2 text-xs text-text-muted">
                  最新监控点 {monitorHistory[0] ? formatDateTime(monitorHistory[0].timestamp) : '暂无'}
                </div>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <StatusBadge
                label={`Health: ${String(systemHealth?.status ?? 'unknown')}`}
                status={overallStatusTone(systemHealth?.status as string | undefined)}
              />
              <StatusBadge
                label={`WS clients: ${String(monitorHealth?.websocket_clients ?? 0)}`}
                status="pending"
              />
              <StatusBadge
                label={`Agent available: ${monitorHealth?.agent_available ? 'yes' : 'no'}`}
                status={monitorHealth?.agent_available ? 'success' : 'warning'}
              />
            </div>
          </div>
        </SectionCard>
      </div>
    </div>
  )
}

export default AdminDashboardPage
