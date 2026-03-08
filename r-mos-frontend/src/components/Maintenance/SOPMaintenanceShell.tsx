import type { ReactNode } from 'react'
import { Lock, ShieldAlert } from 'lucide-react'

import { PageHeader, SectionCard, StatusBadge } from '@/components/common'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { cn } from '@/lib/utils'

type OperationMode = 'teaching' | 'exam' | 'maintenance'

interface SOPMaintenanceHeaderProps {
  operationMode: OperationMode
  examTimeText?: string
  currentScore?: number
  scoreFlash?: boolean
  totalPartCount: number
  selectedToolIndicator?: ReactNode
  viewModeControl: ReactNode
  detailToggleControl: ReactNode
  modeSelectControl: ReactNode
}

interface SOPMaintenanceRightRailProps {
  rightPanelTab: string
  onRightPanelTabChange: (value: string) => void
  quickSelectControl: ReactNode
  diagnosisContent: ReactNode
  partPanel: ReactNode
  screwPanel: ReactNode
}

interface SOPMaintenanceLeftRailStep {
  stepId: string
  title: string
  description: string
  onFailureAction?: string
  hasCriticalFailureReason?: boolean
}

interface SOPMaintenanceLeftRailProps {
  sopTitle: string
  difficultyLabel: string
  currentStepTitle?: string | null
  steps: SOPMaintenanceLeftRailStep[]
  explodeControls: ReactNode
  isolationControls?: ReactNode
  sopListContent: ReactNode
  toolSelectorContent: ReactNode
  sopPlayerContent: ReactNode
  hoverContent: ReactNode
}

interface SOPMaintenanceExamOverlayProps {
  reasonCode: string
  currentScore: number
  onReset: () => void
}

function MetricChip({
  label,
  value,
  tone = 'neutral',
  flash = false,
}: {
  label: string
  value: string
  tone?: 'neutral' | 'warning' | 'danger'
  flash?: boolean
}) {
  const toneClassName =
    tone === 'danger'
      ? 'border-danger/40 bg-danger/10 text-danger'
      : tone === 'warning'
        ? 'border-amber/40 bg-amber/10 text-amber'
        : 'border-border-default bg-bg-elevated text-text-secondary'

  return (
    <div
      className={cn(
        'rounded-lg border px-3 py-2 text-center transition duration-base ease-base',
        toneClassName,
        flash && 'scale-[1.03] shadow-[0_0_18px_rgba(245,158,11,0.2)]',
      )}
    >
      <div className="text-[11px] uppercase tracking-[0.18em] text-text-muted">{label}</div>
      <div className="mt-1 text-sm font-semibold">{value}</div>
    </div>
  )
}

export function SOPMaintenanceHeader({
  operationMode,
  examTimeText,
  currentScore,
  scoreFlash = false,
  totalPartCount,
  selectedToolIndicator,
  viewModeControl,
  detailToggleControl,
  modeSelectControl,
}: SOPMaintenanceHeaderProps) {
  const modeLabel =
    operationMode === 'exam'
      ? '考试模式'
      : operationMode === 'maintenance'
        ? '维保模式'
        : '教学模式'

  return (
    <PageHeader
      title="SOP 维保系统"
      subtitle="步骤导航、3D 操作区和工具要求统一在同一工作台内处理"
      breadcrumb={['维保端', 'SOP 工作台']}
      actions={(
        <div className="flex max-w-4xl flex-wrap items-center justify-end gap-2">
          <StatusBadge
            label={modeLabel}
            status={operationMode === 'exam' ? 'warning' : 'active'}
          />
          {operationMode === 'exam' && examTimeText ? (
            <MetricChip
              label="倒计时"
              value={`倒计时 ${examTimeText}`}
              tone="danger"
            />
          ) : null}
          {operationMode === 'exam' && typeof currentScore === 'number' ? (
            <MetricChip
              label="得分"
              value={`得分 ${currentScore}`}
              tone="warning"
              flash={scoreFlash}
            />
          ) : null}
          <div className="min-w-[180px]">{viewModeControl}</div>
          {selectedToolIndicator ? (
            <div className="rounded-lg border border-success/40 bg-success/10 px-3 py-2 text-sm font-medium text-success">
              {selectedToolIndicator}
            </div>
          ) : null}
          <MetricChip label="零件总数" value={`${totalPartCount} 个零件`} />
          <div className="min-w-[88px]">{detailToggleControl}</div>
          <div className="min-w-[120px]">{modeSelectControl}</div>
        </div>
      )}
    />
  )
}

export function SOPMaintenanceRightRail({
  rightPanelTab,
  onRightPanelTabChange,
  quickSelectControl,
  diagnosisContent,
  partPanel,
  screwPanel,
}: SOPMaintenanceRightRailProps) {
  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader className="pb-4">
          <CardTitle className="text-base">核心件快速定位</CardTitle>
          <CardDescription>
            已合并上半身/下半身核心件，选择后直接进入隔离爆炸视图。
          </CardDescription>
        </CardHeader>
        <CardContent>{quickSelectControl}</CardContent>
      </Card>

      <SectionCard
        title="最近诊断结果"
        description="从 Agent 工作台同步的最近一次故障推理与维保建议"
      >
        {diagnosisContent}
      </SectionCard>

      <Card className="overflow-hidden">
        <CardHeader className="border-b border-border-subtle pb-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <CardTitle className="text-base">维保详情</CardTitle>
              <CardDescription>零件信息与螺丝操作保持原逻辑，仅统一工作台外壳。</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-6">
          <Tabs value={rightPanelTab} onValueChange={onRightPanelTabChange}>
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="part" onClick={() => onRightPanelTabChange('part')}>
                零件
              </TabsTrigger>
              <TabsTrigger value="tool" onClick={() => onRightPanelTabChange('tool')}>
                螺丝
              </TabsTrigger>
            </TabsList>
            <TabsContent value="part" className="space-y-4">
              {partPanel}
            </TabsContent>
            <TabsContent value="tool" className="space-y-4">
              {screwPanel}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  )
}

export function SOPMaintenanceLeftRail({
  sopTitle,
  difficultyLabel,
  currentStepTitle,
  steps,
  explodeControls,
  isolationControls,
  sopListContent,
  toolSelectorContent,
  sopPlayerContent,
  hoverContent,
}: SOPMaintenanceLeftRailProps) {
  return (
    <div className="flex flex-col gap-4">
      <SectionCard
        title={sopTitle}
        description="保留现有执行逻辑，仅统一为工作台式导航外壳"
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="rounded bg-primary/10 px-2 py-1 font-mono text-xs text-primary">
              ATOM-01
            </span>
            <StatusBadge label={difficultyLabel} status="pending" />
          </div>
          <div className="space-y-2">
            {steps.map((step, index) => {
              const isCurrent = currentStepTitle === step.title
              const isBlock = step.onFailureAction === 'block'
              return (
                <div
                  key={step.stepId}
                  className={cn(
                    'flex items-center gap-3 rounded-md px-3 py-2 text-sm',
                    isCurrent
                      ? 'border-l-[3px] border-primary bg-[#111f33]'
                      : 'bg-[rgba(255,255,255,0.03)]',
                  )}
                >
                  <span
                    className={cn(
                      'font-mono text-xs',
                      isCurrent ? 'text-primary' : 'text-text-muted',
                    )}
                  >
                    {String(index + 1).padStart(2, '0')}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="text-text-primary">{step.title}</div>
                    <div className="truncate text-xs text-text-muted">{step.description}</div>
                  </div>
                  {isBlock ? <Lock aria-label="阻断步骤" className="h-4 w-4 text-amber" /> : null}
                  {step.hasCriticalFailureReason ? (
                    <ShieldAlert aria-label="高危步骤" className="h-4 w-4 text-danger" />
                  ) : null}
                </div>
              )
            })}
          </div>
        </div>
      </SectionCard>

      {explodeControls}
      {isolationControls}
      {sopListContent}
      {toolSelectorContent}
      {sopPlayerContent}
      {hoverContent}
    </div>
  )
}

export function SOPMaintenanceExamOverlay({
  reasonCode,
  currentScore,
  onReset,
}: SOPMaintenanceExamOverlayProps) {
  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-[rgba(10,15,25,0.92)] p-6">
      <div className="w-full max-w-2xl rounded-3xl border border-danger/30 bg-bg-surface/95 p-8 text-center shadow-2xl backdrop-blur">
        <div className="text-xs uppercase tracking-[0.35em] text-danger">Exam Summary</div>
        <h2 className="mt-3 text-3xl font-semibold text-text-primary">考试结束</h2>
        <p className="mt-4 text-lg font-medium text-danger">原因码：{reasonCode}</p>
        <p className="mt-2 text-xl text-text-primary">最终得分：{currentScore}</p>
        <Button className="mt-6" onClick={onReset}>
          重置
        </Button>
      </div>
    </div>
  )
}
