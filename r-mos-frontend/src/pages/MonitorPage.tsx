import { Activity, AlertTriangle, Battery, Gauge, RefreshCw, Thermometer, WifiOff, Zap } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { FaultAlertCard, type FaultAlert } from '@/components/Monitor/FaultAlertCard'

import { Viewer3DErrorBoundary } from '@/components/common/ErrorBoundary'
import { MonitorRobotViewer } from '@/components/Viewer3D/MonitorRobotViewer'
import { useAssemblyManifest } from '@/components/Viewer3D/useAssemblyManifest'
import { Button } from '@/components/ui/button'
import { useWebSocket, type JointState } from '@/hooks/useWebSocket'
import { cn } from '@/lib/utils'
import { useRobotContextStore } from '@/store/robotContextStore'

type MonitorJointMeta = {
  atomJoint: string
  atomLink: string
  label: string
}

/**
 * @deprecated 硬编码的 ATOM-01 关节映射表。
 * 请通过 `buildJointMetaFromManifest()` 从 assembly manifest 动态构建关节元数据。
 * 组件中 `manifestJointMeta` 已优先使用，此表仅作为 manifest 未就绪时的 fallback。
 * 待 manifest 数据稳定覆盖所有机器人后，此表将被移除。
 */
const MONITOR_JOINT_MAP: Record<string, MonitorJointMeta> = {
  knee_left: { atomJoint: 'left_knee_joint', atomLink: 'left_knee_link', label: '左膝关节' },
  knee_right: { atomJoint: 'right_knee_joint', atomLink: 'right_knee_link', label: '右膝关节' },
  hip_left: { atomJoint: 'left_thigh_pitch_joint', atomLink: 'left_thigh_pitch_link', label: '左髋关节' },
  hip_right: { atomJoint: 'right_thigh_pitch_joint', atomLink: 'right_thigh_pitch_link', label: '右髋关节' },
  ankle_left: { atomJoint: 'left_ankle_pitch_joint', atomLink: 'left_ankle_pitch_link', label: '左踝关节' },
  ankle_right: { atomJoint: 'right_ankle_pitch_joint', atomLink: 'right_ankle_pitch_link', label: '右踝关节' },
  shoulder_left: { atomJoint: 'left_arm_pitch_joint', atomLink: 'left_arm_pitch_link', label: '左肩关节' },
  shoulder_right: { atomJoint: 'right_arm_pitch_joint', atomLink: 'right_arm_pitch_link', label: '右肩关节' },
  elbow_left: { atomJoint: 'left_elbow_pitch_joint', atomLink: 'left_elbow_pitch_link', label: '左肘关节' },
  elbow_right: { atomJoint: 'right_elbow_pitch_joint', atomLink: 'right_elbow_pitch_link', label: '右肘关节' },
  waist: { atomJoint: 'torso_joint', atomLink: 'torso_link', label: '腰部关节' },
  neck: { atomJoint: 'torso_joint', atomLink: 'torso_link', label: '躯干姿态' },
}

function resolveJointMeta(jointId: string): MonitorJointMeta | null {
  return MONITOR_JOINT_MAP[jointId] ?? null
}

/** 从 manifest joints 构建关节元数据 */
function buildJointMetaFromManifest(
  manifest: { joints?: Array<{ name: string; type: string; parent_link: string; child_link: string }> } | null,
  displayNames: Record<string, string>
): Record<string, MonitorJointMeta> | null {
  if (!manifest?.joints) return null

  const result: Record<string, MonitorJointMeta> = {}
  for (const joint of manifest.joints) {
    if (joint.type === 'fixed') continue
    result[joint.name] = {
      atomJoint: joint.name,
      atomLink: joint.child_link,
      label: displayNames[joint.child_link] ?? joint.name.replace(/_/g, ' '),
    }
  }
  return result
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

function formatMetric(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '--'
  }
  const multiplier = 10 ** digits
  const rounded = Math.round(value * multiplier) / multiplier
  return rounded.toFixed(digits)
}

function formatFreshness(lastUpdateTime: Date | null) {
  if (!lastUpdateTime) {
    return '--'
  }
  const seconds = Math.max(0, Math.round((Date.now() - lastUpdateTime.getTime()) / 1000))
  return `${seconds}s`
}

function MetricCard({
  label,
  value,
  suffix,
  tone = 'default',
  icon,
}: {
  label: string
  value: string | number
  suffix?: string
  tone?: 'default' | 'danger' | 'success' | 'warning'
  icon?: React.ReactNode
}) {
  const toneClassName =
    tone === 'danger'
      ? 'border-danger/30 bg-danger/5'
      : tone === 'success'
        ? 'border-success/30 bg-success/5'
        : tone === 'warning'
          ? 'border-amber/30 bg-amber/5'
          : 'border-border-subtle bg-bg-surface'

  const valueClassName =
    tone === 'danger'
      ? 'text-danger'
      : tone === 'success'
        ? 'text-success'
        : tone === 'warning'
          ? 'text-amber'
          : 'text-text-primary'

  return (
    <div className={cn('rounded-xl border p-4', toneClassName)}>
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="text-[10px] uppercase tracking-[0.22em] text-text-muted">{label}</div>
        {icon}
      </div>
      <div className={cn('text-data text-3xl font-semibold', valueClassName)}>
        {value}
        {suffix ? <span className="ml-1 text-sm font-normal text-text-muted">{suffix}</span> : null}
      </div>
    </div>
  )
}

function DataRow({
  label,
  value,
  unit,
  className,
}: {
  label: string
  value: string
  unit?: string
  className?: string
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-border-subtle bg-bg-elevated/40 px-3 py-2">
      <span className="text-xs uppercase tracking-[0.16em] text-text-muted">{label}</span>
      <span className={cn('text-data text-sm text-text-primary', className)}>
        {value}
        {unit ? <span className="ml-1 text-text-muted">{unit}</span> : null}
      </span>
    </div>
  )
}

function SectionCard({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle?: string
  children: React.ReactNode
}) {
  return (
    <div className="rounded-xl border border-border-subtle bg-bg-surface shadow-sm">
      <div className="border-b border-border-subtle px-4 py-3">
        <div className="text-[11px] uppercase tracking-[0.22em] text-text-muted">{title}</div>
        {subtitle ? <div className="mt-1 text-xs text-text-muted">{subtitle}</div> : null}
      </div>
      <div className="p-4">{children}</div>
    </div>
  )
}

const TEMP_WARN = 50
const TEMP_DANGER = 55

function MonitorJointRow({ joint, onClick }: { joint: JointState; onClick?: () => void }) {
  const meta = resolveJointMeta(joint.joint_id)
  const tempValue = joint.temperature ?? 0
  const isError = !!joint.error_code
  const isTempAlert = tempValue >= TEMP_DANGER
  const tempTone = tempValue >= TEMP_DANGER ? 'text-red-400' : tempValue >= TEMP_WARN ? 'text-amber-400' : ''
  const isClickable = isError || isTempAlert

  return (
    <div
      className={cn(
        'rounded-xl border p-3',
        isError
          ? 'border-danger/30 bg-danger/5'
          : isTempAlert
            ? 'border-amber-500/30 bg-amber-500/5 animate-pulse'
            : 'border-border-subtle bg-bg-elevated/40',
        isClickable && 'cursor-pointer hover:brightness-125 transition-all',
      )}
      onClick={isClickable ? onClick : undefined}
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-medium text-text-primary">{meta?.label ?? joint.joint_id}</div>
          <div className="text-data text-[11px] uppercase tracking-[0.16em] text-text-muted">{joint.joint_id}</div>
        </div>
        {joint.error_code ? (
          <span className="inline-flex rounded-full border border-danger/30 bg-danger/10 px-2 py-1 text-data text-[10px] text-danger">
            {joint.error_code}
          </span>
        ) : null}
      </div>

      <div className="grid grid-cols-2 gap-2">
        <DataRow label="位置" value={formatMetric(joint.position, 3)} unit="rad" />
        <DataRow label="速度" value={formatMetric(joint.velocity, 3)} unit="rad/s" />
        <DataRow label="扭矩" value={formatMetric(joint.torque, 2)} unit="Nm" />
        <DataRow label="电流" value={formatMetric(joint.current, 2)} unit="A" />
        <DataRow label="温度" value={formatMetric(joint.temperature, 1)} unit="°C" className={tempTone} />
      </div>
    </div>
  )
}

function MonitorPage() {
  const navigate = useNavigate()
  const currentRobot = useRobotContextStore((s) => s.currentRobot)
  const robotId = currentRobot ? String(currentRobot.id) : null

  const { manifest } = useAssemblyManifest(currentRobot?.id)

  const manifestJointMeta = useMemo(() => {
    if (!manifest) return null
    const displayNames = manifest.display_names ?? {}
    return buildJointMetaFromManifest(manifest, displayNames)
  }, [manifest])

  const {
    isConnected,
    telemetryData,
    error,
    status,
    isDataStale,
    retryCount,
    reconnect,
    lastUpdateTime,
  } = useWebSocket()

  const batteryLevel = telemetryData?.sensors?.battery ?? null
  const joints = telemetryData?.joints ?? []
  const activeFaults = telemetryData?.active_faults ?? []
  const imuData = telemetryData?.sensors?.imu
  const voltageEntries = Object.entries(telemetryData?.sensors?.voltage ?? {})
  const pressureEntries = Object.entries(telemetryData?.sensors?.pressure ?? {})

  const monitorJoints = useMemo(
    () =>
      joints.map((joint) => ({
        ...joint,
        meta: manifestJointMeta?.[joint.joint_id]
          ?? resolveJointMeta(joint.joint_id),
      })),
    [joints, manifestJointMeta],
  )

  const jointAngles = useMemo(
    () =>
      monitorJoints.reduce<Record<string, number>>((angles, joint) => {
        if (joint.meta) {
          angles[joint.meta.atomJoint] = joint.position
        }
        return angles
      }, {}),
    [monitorJoints],
  )

  const faultJoints = useMemo(
    () =>
      monitorJoints
        .filter((joint) => joint.error_code && joint.meta)
        .map((joint) => joint.meta!.atomJoint),
    [monitorJoints],
  )

  const highlightLinks = useMemo(
    () =>
      monitorJoints
        .filter((joint) => joint.error_code && joint.meta)
        .map((joint) => joint.meta!.atomLink),
    [monitorJoints],
  )

  const [dismissedAlerts, setDismissedAlerts] = useState<Set<string>>(new Set())

  const faultAlerts = useMemo(() => {
    if (!telemetryData?.joints) return []
    const alerts: FaultAlert[] = []

    for (const joint of telemetryData.joints) {
      if ((joint.temperature ?? 0) >= 70) {
        alerts.push({
          id: `${joint.joint_id}-overheat`,
          fault_type: 'E001_OVERHEAT',
          fault_name: '关节过热告警',
          affected_joints: [joint.joint_id],
          current_value: `${joint.temperature}°C`,
          threshold: '70°C',
          severity: (joint.temperature ?? 0) >= 80 ? 'danger' : 'warning',
        })
      }
    }

    const voltage = telemetryData.sensors?.voltage?.main as number | undefined
    if (voltage && voltage < 20) {
      alerts.push({
        id: 'voltage-drop',
        fault_type: 'E003_VOLTAGE_DROP',
        fault_name: '电压跌落告警',
        affected_joints: ['system'],
        current_value: `${voltage}V`,
        threshold: '20V',
        severity: 'danger',
      })
    }

    return alerts.filter(a => !dismissedAlerts.has(a.id))
  }, [telemetryData, dismissedAlerts])

  const handleDiagnose = (alert: FaultAlert) => {
    navigate(`/agent/workbench?fault_type=${alert.fault_type}&joints=${alert.affected_joints.join(',')}`)
  }

  const handleDismissAlert = (alertId: string) => {
    setDismissedAlerts(prev => new Set(prev).add(alertId))
  }

  const priorityJoints = useMemo(
    () =>
      [...monitorJoints]
        .sort((left, right) => {
          const leftScore = (left.error_code ? 1000 : 0) + (left.temperature ?? 0) + Math.abs(left.torque ?? 0)
          const rightScore = (right.error_code ? 1000 : 0) + (right.temperature ?? 0) + Math.abs(right.torque ?? 0)
          return rightScore - leftScore
        })
        .slice(0, 6),
    [monitorJoints],
  )

  const faultLinks = useMemo(
    () =>
      monitorJoints
        .filter((joint) => joint.error_code && joint.meta)
        .map((joint) => ({
          code: joint.error_code!,
          label: joint.meta!.label,
          link: joint.meta!.atomLink,
        })),
    [monitorJoints],
  )

  const statusText = formatStatusText({
    error,
    isDataStale,
    isConnected,
    status,
    retryCount,
  })

  if (!currentRobot) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-text-muted">
        <WifiOff className="mb-4 h-12 w-12 opacity-30" />
        <h2 className="text-lg font-medium text-text-primary mb-2">未选择机器人</h2>
        <p className="text-sm">请先在首页选择一台机器人，再进入监控面板。</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-border-subtle bg-[linear-gradient(135deg,rgba(14,20,37,0.98),rgba(18,31,57,0.92))] px-5 py-4 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="mb-1 text-[10px] uppercase tracking-[0.24em] text-text-muted">REALTIME MONITOR</div>
            <h1
              className="text-2xl font-semibold text-text-primary"
            >
              实时监控
            </h1>
            <p className="mt-1 text-sm text-text-muted">
              以 3D 数字孪生为中心，联动展示姿态、动力、故障和重点关节状态。
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <span
              className={cn(
                'status-dot',
                error ? 'bg-danger' : isDataStale ? 'bg-amber' : isConnected ? 'bg-success animate-pulse' : 'bg-text-muted',
              )}
            />
            <span className="text-data text-xs text-text-secondary">{statusText}</span>
            <span className="inline-flex rounded-full border border-border-subtle bg-bg-surface/70 px-3 py-1 text-data text-[11px] text-text-secondary">
              最近更新 {formatFreshness(lastUpdateTime)}
            </span>
            {status === 'failed' ? (
              <Button type="button" variant="outline" size="sm" onClick={reconnect}>
                <RefreshCw className="h-4 w-4" />
                重连
              </Button>
            ) : null}
          </div>
        </div>
      </div>

      {faultAlerts.length > 0 && (
        <div className="space-y-2">
          {faultAlerts.map(alert => (
            <FaultAlertCard
              key={alert.id}
              alert={alert}
              onDiagnose={handleDiagnose}
              onDismiss={handleDismissAlert}
            />
          ))}
        </div>
      )}

      {error ? (
        <div className="flex items-start gap-3 rounded-xl border border-danger/30 bg-danger/5 px-4 py-3">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-danger" />
          <div>
            <div className="text-sm font-medium text-danger">连接已断开</div>
            <div className="text-xs text-text-muted">{error}</div>
          </div>
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)_360px]">
        <div className="space-y-4">
          <SectionCard title="机器人态势" subtitle="连接、能量与总体健康概览">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
              <MetricCard
                label="BATTERY"
                value={batteryLevel !== null && batteryLevel !== undefined ? formatMetric(batteryLevel, 1) : '--'}
                suffix={batteryLevel === null ? undefined : '%'}
                tone={(batteryLevel ?? 100) <= 20 ? 'danger' : batteryLevel && batteryLevel <= 50 ? 'warning' : 'success'}
                icon={<Battery className="h-4 w-4 text-text-muted" />}
              />
              <MetricCard
                label="CORE TEMP"
                value={formatMetric(telemetryData?.sensors?.temperature, 1)}
                suffix={telemetryData?.sensors?.temperature === undefined ? undefined : '°C'}
                tone={(telemetryData?.sensors?.temperature ?? 0) >= 70 ? 'danger' : 'default'}
                icon={<Thermometer className="h-4 w-4 text-text-muted" />}
              />
              <MetricCard
                label="ACTIVE FAULTS"
                value={activeFaults.length}
                suffix="个"
                tone={activeFaults.length > 0 ? 'danger' : 'success'}
                icon={<AlertTriangle className="h-4 w-4 text-text-muted" />}
              />
              <MetricCard
                label="JOINT FEED"
                value={joints.length}
                suffix="路"
                tone={joints.length > 0 ? 'success' : 'default'}
                icon={<Activity className="h-4 w-4 text-text-muted" />}
              />
            </div>
          </SectionCard>

          <SectionCard title="姿态与运动" subtitle="IMU 加速度与角速度">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-1">
              <div className="space-y-2">
                <div className="text-[11px] uppercase tracking-[0.2em] text-text-muted">加速度</div>
                <DataRow label="X" value={formatMetric(imuData?.acceleration?.x, 3)} unit="m/s²" />
                <DataRow label="Y" value={formatMetric(imuData?.acceleration?.y, 3)} unit="m/s²" />
                <DataRow label="Z" value={formatMetric(imuData?.acceleration?.z, 3)} unit="m/s²" />
              </div>
              <div className="space-y-2">
                <div className="text-[11px] uppercase tracking-[0.2em] text-text-muted">角速度</div>
                <DataRow label="X" value={formatMetric(imuData?.angular_velocity?.x, 3)} unit="rad/s" />
                <DataRow label="Y" value={formatMetric(imuData?.angular_velocity?.y, 3)} unit="rad/s" />
                <DataRow label="Z" value={formatMetric(imuData?.angular_velocity?.z, 3)} unit="rad/s" />
              </div>
            </div>
          </SectionCard>

          <SectionCard title="电源与载荷" subtitle="电压总线与压力传感器">
            <div className="space-y-4">
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.2em] text-text-muted">
                  <Zap className="h-3.5 w-3.5" />
                  Voltage
                </div>
                {voltageEntries.length > 0 ? (
                  voltageEntries.map(([key, value]) => (
                    <DataRow key={key} label={key} value={formatMetric(value, 1)} unit="V" />
                  ))
                ) : (
                  <div className="rounded-lg border border-dashed border-border-subtle px-3 py-4 text-xs text-text-muted">
                    暂无电压上报
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.2em] text-text-muted">
                  <Gauge className="h-3.5 w-3.5" />
                  Pressure
                </div>
                {pressureEntries.length > 0 ? (
                  pressureEntries.map(([key, value]) => (
                    <DataRow key={key} label={key} value={formatMetric(value, 1)} unit="kPa" />
                  ))
                ) : (
                  <div className="rounded-lg border border-dashed border-border-subtle px-3 py-4 text-xs text-text-muted">
                    暂无压力上报
                  </div>
                )}
              </div>
            </div>
          </SectionCard>
        </div>

        <div className="space-y-4">
          <SectionCard title="3D 数字孪生" subtitle="故障关节闪烁，重点部位高亮">
            <div className="space-y-4">
              <div className="flex flex-wrap gap-2">
                <span className="inline-flex rounded-full border border-border-subtle bg-bg-elevated/60 px-3 py-1 text-data text-[11px] text-text-secondary">
                  关节映射 {Object.keys(jointAngles).length} / {joints.length}
                </span>
                <span className="inline-flex rounded-full border border-border-subtle bg-bg-elevated/60 px-3 py-1 text-data text-[11px] text-text-secondary">
                  数据鲜度 {formatFreshness(lastUpdateTime)}
                </span>
                {faultLinks.length > 0 ? (
                  <span className="inline-flex rounded-full border border-danger/30 bg-danger/10 px-3 py-1 text-data text-[11px] text-danger">
                    告警部位 {faultLinks.length} 处
                  </span>
                ) : null}
              </div>

              <div className="overflow-hidden rounded-xl border border-border-subtle bg-[#08101f]">
                <Viewer3DErrorBoundary>
                  {currentRobot ? (
                    <MonitorRobotViewer
                      robotId={currentRobot.id}
                      height={460}
                      jointAngles={jointAngles}
                      highlightLinks={highlightLinks}
                    />
                  ) : (
                    <div style={{ height: 460, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#4fc3f7', fontSize: 14 }}>
                      请先选择机器人
                    </div>
                  )}
                </Viewer3DErrorBoundary>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <div className="rounded-lg border border-border-subtle bg-bg-elevated/40 px-3 py-2 text-xs text-text-muted">
                  红色闪烁代表该关节存在告警或错误码。
                </div>
                <div className="rounded-lg border border-border-subtle bg-bg-elevated/40 px-3 py-2 text-xs text-text-muted">
                  绿色高亮代表当前重点观测部位。
                </div>
                <div className="rounded-lg border border-border-subtle bg-bg-elevated/40 px-3 py-2 text-xs text-text-muted">
                  若关节未映射到当前机器人，会仍保留在右侧明细区。
                </div>
              </div>
            </div>
          </SectionCard>

          <SectionCard title="故障定位" subtitle="按故障码与部位联动查看">
            {faultLinks.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {faultLinks.map((fault, index) => (
                  <div
                    key={`${fault.code}-${fault.link}-${index}`}
                    className="rounded-lg border border-danger/30 bg-danger/5 px-3 py-2"
                  >
                    <div className="text-data text-[11px] uppercase tracking-[0.18em] text-danger">{fault.code}</div>
                    <div className="mt-1 text-sm text-text-primary">{fault.label}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-border-subtle px-3 py-5 text-sm text-text-muted">
                当前没有定位到具体告警部位。
              </div>
            )}
          </SectionCard>
        </div>

        <SectionCard title="重点关节" subtitle="优先显示高温、异常和高负载关节">
          {priorityJoints.length > 0 ? (
            <div className="space-y-3">
              {priorityJoints.map((joint, index) => (
                <MonitorJointRow
                  key={`${joint.joint_id}-${index}`}
                  joint={joint}
                  onClick={() => {
                    navigate(`/agent/workbench?fault=${joint.error_code ?? 'unknown'}&joint=${joint.joint_id}`)
                  }}
                />
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-10 text-text-muted">
              <WifiOff className="mb-2 h-6 w-6 opacity-40" />
              <span className="text-sm">等待遥测数据...</span>
            </div>
          )}
        </SectionCard>
      </div>
    </div>
  )
}

export default MonitorPage
