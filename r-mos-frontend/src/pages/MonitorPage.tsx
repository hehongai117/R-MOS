import { AlertTriangle, Cpu, RefreshCw, WifiOff } from 'lucide-react'

import { Viewer3DErrorBoundary } from '@/components/common/ErrorBoundary'
import { Button } from '@/components/ui/button'
import RobotViewer from '@/components/Viewer3D/RobotViewer'
import { useWebSocket, type JointState } from '@/hooks/useWebSocket'
import { cn } from '@/lib/utils'

function MetricCard({
  label,
  value,
  suffix,
  tone = 'default',
  children,
}: {
  label: string
  value: string | number
  suffix?: string
  tone?: 'default' | 'danger' | 'success'
  children?: React.ReactNode
}) {
  const toneClassName =
    tone === 'danger'
      ? 'border-danger/30 bg-danger/5'
      : tone === 'success'
        ? 'border-success/30 bg-success/5'
        : 'border-border-subtle bg-bg-surface'

  const valueClassName =
    tone === 'danger'
      ? 'text-danger'
      : tone === 'success'
        ? 'text-success'
        : 'text-text-primary'

  return (
    <div className={cn('rounded-lg border p-4', toneClassName)}>
      <div className="mb-1 text-[10px] uppercase tracking-[0.2em] text-text-muted">{label}</div>
      <div className={cn('text-data text-3xl font-bold', valueClassName)}>
        {value}
        {suffix ? <span className="ml-1 text-base font-normal text-text-muted">{suffix}</span> : null}
      </div>
      {children}
    </div>
  )
}

function formatStatusText({
  error,
  isDataStale,
  isConnected,
  status,
  retryCount,
}: {
  error: string | null
  isDataStale: boolean
  isConnected: boolean
  status: string
  retryCount: number
}) {
  if (error) return 'WebSocket 已断开'
  if (isDataStale) return '数据已过期'
  if (status === 'reconnecting') return `重连中 (${retryCount}/10)`
  if (isConnected) return 'WebSocket 已连接'
  return 'WebSocket 连接中...'
}

function JointStatusCard({ joint, fallbackLabel }: { joint: JointState; fallbackLabel: string }) {
  return (
    <div
      className={cn(
        'rounded-md border p-3 transition-colors',
        joint.error_code
          ? 'border-danger/40 bg-danger/5'
          : 'border-border-subtle bg-bg-elevated',
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="text-data text-xs text-text-secondary">{joint.joint_id || fallbackLabel}</span>
        <span
          className={cn(
            'text-data text-sm font-medium',
            joint.error_code ? 'text-danger' : 'text-text-primary',
          )}
        >
          {joint.position?.toFixed(4) ?? '--'}
        </span>
      </div>
      {joint.error_code ? (
        <div className="mt-2 inline-flex rounded-full border border-danger/30 bg-danger/10 px-2 py-0.5 text-data text-[10px] text-danger">
          {joint.error_code}
        </div>
      ) : null}
    </div>
  )
}

function MonitorPage() {
  const { isConnected, telemetryData, error, status, isDataStale, retryCount, reconnect } = useWebSocket()

  const batteryLevel = telemetryData?.sensors?.battery ?? null
  const joints = telemetryData?.joints ?? []
  const activeFaults = telemetryData?.active_faults ?? []
  const imuData = telemetryData?.sensors?.imu

  const joints3D = joints.map((joint) => ({
    joint_id: joint.joint_id,
    position: joint.position,
    velocity: joint.velocity,
    torque: joint.torque,
    error_code: joint.error_code,
  }))

  const statusText = formatStatusText({
    error,
    isDataStale,
    isConnected,
    status,
    retryCount,
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 rounded-xl border border-border-subtle bg-bg-surface px-5 py-4 shadow-sm lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="mb-1 text-[10px] uppercase tracking-[0.22em] text-text-muted">REALTIME MONITOR</div>
          <h1 className="text-2xl font-semibold text-text-primary">实时监控</h1>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <span
            className={cn(
              'status-dot',
              error ? 'bg-danger' : isDataStale ? 'bg-amber' : isConnected ? 'bg-success animate-pulse' : 'bg-text-muted',
            )}
          />
          <span className="text-data text-xs text-text-secondary">{statusText}</span>
          {status === 'failed' ? (
            <Button type="button" variant="outline" size="sm" onClick={reconnect}>
              <RefreshCw className="h-4 w-4" />
              重连
            </Button>
          ) : null}
        </div>
      </div>

      {error ? (
        <div className="flex items-start gap-3 rounded-lg border border-danger/30 bg-danger/5 px-4 py-3">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-danger" />
          <div>
            <div className="text-sm font-medium text-danger">连接已断开</div>
            <div className="text-xs text-text-muted">{error}</div>
          </div>
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)_280px]">
        <div className="space-y-4">
          <MetricCard
            label="BATTERY"
            value={batteryLevel ?? '--'}
            suffix={batteryLevel === null ? undefined : '%'}
            tone={(batteryLevel ?? 100) <= 20 ? 'danger' : 'default'}
          >
            {batteryLevel !== null ? (
              <div className="mt-3 h-1.5 rounded-full bg-bg-elevated">
                <div
                  className={cn(
                    'h-full rounded-full transition-[width] duration-slow ease-base',
                    batteryLevel > 60 ? 'bg-success' : batteryLevel > 20 ? 'bg-amber' : 'bg-danger',
                  )}
                  style={{ width: `${batteryLevel}%` }}
                />
              </div>
            ) : null}
          </MetricCard>

          <MetricCard
            label="ACTIVE FAULTS"
            value={activeFaults.length}
            suffix="个"
            tone={activeFaults.length > 0 ? 'danger' : 'success'}
          />

          <MetricCard label="SYS TEMP" value={telemetryData?.sensors?.temperature ?? '--'} suffix="°C" />

          <div className="rounded-lg border border-border-subtle bg-bg-surface p-4">
            <div className="mb-2 text-[10px] uppercase tracking-[0.2em] text-text-muted">IMU ACCELERATION</div>
            <div className="space-y-2">
              {(['x', 'y', 'z'] as const).map((axis) => (
                <div key={axis} className="flex items-center justify-between gap-3">
                  <span className="text-data text-xs uppercase text-text-muted">{axis}</span>
                  <span className="text-data text-sm text-text-primary">
                    {imuData?.acceleration?.[axis]?.toFixed(3) ?? '--'}
                    <span className="ml-1 text-text-muted">m/s²</span>
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="overflow-hidden rounded-lg border border-border-subtle bg-bg-surface">
            <div className="flex items-center justify-between border-b border-border-subtle px-4 py-3">
              <span className="text-[11px] uppercase tracking-[0.18em] text-text-muted">3D ROBOT VIEW</span>
              {activeFaults.length > 0 ? (
                <span className="inline-flex items-center gap-1 rounded-full border border-danger/30 bg-danger/10 px-2 py-0.5 text-data text-[10px] text-danger">
                  <AlertTriangle className="h-3 w-3" />
                  {activeFaults.length} FAULT{activeFaults.length > 1 ? 'S' : ''}
                </span>
              ) : null}
            </div>
            <div className="p-0">
              <Viewer3DErrorBoundary>
                <RobotViewer
                  height={400}
                  externalData={{
                    joints: joints3D,
                    connected: isConnected,
                  }}
                />
              </Viewer3DErrorBoundary>
            </div>
          </div>

          {activeFaults.length > 0 ? (
            <div className="rounded-lg border border-danger/30 bg-danger/5 p-4">
              <div className="mb-3 text-[10px] uppercase tracking-[0.2em] text-danger">ACTIVE FAULTS</div>
              <div className="flex flex-wrap gap-2">
                {activeFaults.map((fault) => (
                  <span
                    key={fault}
                    className="inline-flex items-center gap-1 rounded-full border border-danger/30 bg-danger/10 px-3 py-1 text-data text-[11px] text-danger"
                  >
                    <AlertTriangle className="h-3 w-3" />
                    {fault}
                  </span>
                ))}
              </div>
            </div>
          ) : null}
        </div>

        <div className="rounded-lg border border-border-subtle bg-bg-surface">
          <div className="border-b border-border-subtle px-4 py-3">
            <span className="text-[11px] uppercase tracking-[0.18em] text-text-muted">JOINT STATUS</span>
          </div>
          <div className="space-y-2 p-3">
            {joints.length > 0 ? (
              joints.map((joint, index) => (
                <JointStatusCard key={joint.joint_id || `joint-${index}`} joint={joint} fallbackLabel={`J${index + 1}`} />
              ))
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-text-muted">
                <WifiOff className="mb-2 h-6 w-6 opacity-40" />
                <span className="text-xs">等待遥测数据...</span>
              </div>
            )}
          </div>

          <div className="border-t border-border-subtle px-4 py-3">
            <div className="flex items-center gap-2 text-xs text-text-muted">
              <Cpu className="h-4 w-4" />
              遥测通道由 `useWebSocket()` 实时驱动
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default MonitorPage
