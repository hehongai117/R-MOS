import type { ReactNode } from 'react'
import { Lock, ShieldAlert } from 'lucide-react'

import { PageHeader, SectionCard, StatusBadge } from '@/components/common'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { cn } from '@/lib/utils'

interface SOPMaintenanceHeaderProps {
  viewModeControl: ReactNode
  title?: string
  subtitle?: string
  breadcrumb?: string[]
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
  isolationControls?: ReactNode
  sopListContent: ReactNode
  toolSelectorContent: ReactNode
  sopPlayerContent: ReactNode
}

interface SOPMaintenanceExamOverlayProps {
  reasonCode: string
  currentScore: number
  onReset: () => void
}

export function SOPMaintenanceHeader({
  viewModeControl,
  title = 'SOP 维保系统',
  breadcrumb = ['维保端', 'SOP 工作台'],
  subtitle,
}: SOPMaintenanceHeaderProps) {
  return (
    <PageHeader
      title={title}
      subtitle={subtitle}
      breadcrumb={breadcrumb}
      actions={(
        <div className="flex max-w-4xl flex-wrap items-center justify-end gap-2">
          <div className="min-w-[180px]">{viewModeControl}</div>
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
  isolationControls,
  sopListContent,
  toolSelectorContent,
  sopPlayerContent,
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

      {isolationControls}
      {sopListContent}
      {toolSelectorContent}
      {sopPlayerContent}
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
