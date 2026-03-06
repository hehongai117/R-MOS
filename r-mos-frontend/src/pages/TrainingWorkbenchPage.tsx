import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  Circle,
  Dumbbell,
  Expand,
  Maximize2,
  RefreshCw,
  Send,
  XCircle,
} from 'lucide-react'
import { type ChangeEvent, useEffect, useMemo, useState } from 'react'
import { Spin } from 'antd'
import { useNavigate } from 'react-router-dom'
import { useStore } from 'zustand'

import {
  getActiveTrainingSession,
  getTrainingSessionDetail,
  type SessionDetailResponse,
  type SessionResponse,
} from '@/api/training'
import { EmptyState, PageHeader, SectionCard, StatusBadge } from '@/components/common'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { Atom01Viewer } from '@/components/Viewer3D'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/store/authStore'
import {
  canSubmitCurrentStep,
  getConfirmedCriticalToolCount,
  getCurrentStep,
  type WorkbenchChatMessage,
  type WorkbenchStep,
  type WorkbenchTool,
  type WorkbenchToolStatus,
  workbenchStore,
} from '@/store/workbenchStore'

const STEP_COPY: Record<string, { title: string; instruction: string; tools: WorkbenchTool[] }> = {
  prepare_station: {
    title: '准备工位',
    instruction: '确认作业台清洁、安全防护到位，并校验本步骤需要使用的关键工具。',
    tools: [
      { id: 'ppe-gloves', name: '防护手套', spec: 'A级绝缘', isCritical: true },
      { id: 'torque-wrench', name: '扭矩扳手', spec: '5-25Nm', isCritical: true },
      { id: 'inspection-lamp', name: '检修灯', spec: '无频闪', isCritical: false },
    ],
  },
  motor_cover_remove: {
    title: '拆解电机盖',
    instruction: '按对角顺序松开固定螺钉，记录拆下零件的摆放方向，避免混放。',
    tools: [
      { id: 'hex-key', name: '六角扳手', spec: '4mm', isCritical: true },
      { id: 'parts-tray', name: '零件托盘', spec: '分区托盘', isCritical: true },
      { id: 'marker-pen', name: '记号笔', spec: '油性细头', isCritical: false },
    ],
  },
  align_reducer: {
    title: '校准减速器',
    instruction: '复核定位点和齿面状态，必要时拍照留证并记录偏差范围。',
    tools: [
      { id: 'dial-indicator', name: '百分表', spec: '0.01mm', isCritical: true },
      { id: 'inspection-card', name: '检查记录卡', spec: '纸质/电子', isCritical: false },
    ],
  },
  final_check: {
    title: '最终复核',
    instruction: '完成工具回收、螺钉复紧和风险复盘后，再提交本步骤裁决。',
    tools: [
      { id: 'torque-wrench-final', name: '扭矩扳手', spec: '15Nm', isCritical: true },
      { id: 'clean-cloth', name: '清洁布', spec: '无纤维脱落', isCritical: false },
    ],
  },
}

const FALLBACK_STEP_ORDER = ['prepare_station', 'motor_cover_remove', 'align_reducer', 'final_check']

function formatDuration(seconds?: number | null) {
  if (!seconds || Number.isNaN(seconds)) {
    return '00:00'
  }

  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
}

function mapStepStatus(status: string, currentStep: number, index: number): WorkbenchStep['status'] {
  if (status === 'completed') {
    return 'passed'
  }
  if (status === 'failed') {
    return 'failed'
  }
  if (index === currentStep) {
    return 'active'
  }
  return 'pending'
}

function buildStep(step: SessionDetailResponse['steps'][number], session: SessionResponse): WorkbenchStep {
  const fallback = STEP_COPY[step.step_id] ?? STEP_COPY[FALLBACK_STEP_ORDER[(step.step_index - 1) % FALLBACK_STEP_ORDER.length]]

  return {
    id: step.step_id,
    title: fallback.title,
    durationSec: step.duration_sec ?? undefined,
    status: mapStepStatus(step.status, session.current_step, step.step_index),
    instruction: fallback.instruction,
    tools: fallback.tools,
  }
}

function getStepStatusIcon(status: WorkbenchStep['status']) {
  if (status === 'passed') {
    return <CheckCircle2 className="h-4 w-4 text-success" />
  }
  if (status === 'failed') {
    return <XCircle className="h-4 w-4 text-danger" />
  }
  return <Circle className="h-4 w-4 text-text-muted" />
}

function ToolStatusButton({
  toolId,
  activeStatus,
  targetStatus,
  children,
  onClick,
}: {
  toolId: string
  activeStatus?: WorkbenchToolStatus
  targetStatus: WorkbenchToolStatus
  children: React.ReactNode
  onClick: (toolId: string, status: WorkbenchToolStatus) => void
}) {
  const isActive = activeStatus === targetStatus

  return (
    <Button
      className={cn(isActive && 'border-primary/40')}
      size="icon"
      type="button"
      variant={isActive ? 'secondary' : 'ghost'}
      onClick={() => onClick(toolId, targetStatus)}
    >
      {children}
    </Button>
  )
}

function TrainingWorkbenchPage() {
  const navigate = useNavigate()
  const userId = useAuthStore((state) => state.user?.user_id)

  const project = useStore(workbenchStore, (state) => state.project)
  const steps = useStore(workbenchStore, (state) => state.steps)
  const currentStepId = useStore(workbenchStore, (state) => state.currentStepId)
  const toolStatusMap = useStore(workbenchStore, (state) => state.toolStatusMap)
  const verdict = useStore(workbenchStore, (state) => state.verdict)
  const noteDraft = useStore(workbenchStore, (state) => state.noteDraft)
  const evidenceName = useStore(workbenchStore, (state) => state.evidenceName)
  const messages = useStore(workbenchStore, (state) => state.messages)
  const isViewerFullscreen = useStore(workbenchStore, (state) => state.isViewerFullscreen)

  const hydrateTrainingProject = useStore(workbenchStore, (state) => state.hydrateTrainingProject)
  const resetTrainingProject = useStore(workbenchStore, (state) => state.resetTrainingProject)
  const setCurrentStep = useStore(workbenchStore, (state) => state.setCurrentStep)
  const setToolStatus = useStore(workbenchStore, (state) => state.setToolStatus)
  const setVerdict = useStore(workbenchStore, (state) => state.setVerdict)
  const setNoteDraft = useStore(workbenchStore, (state) => state.setNoteDraft)
  const setEvidenceName = useStore(workbenchStore, (state) => state.setEvidenceName)
  const addMessage = useStore(workbenchStore, (state) => state.addMessage)
  const setViewerFullscreen = useStore(workbenchStore, (state) => state.setViewerFullscreen)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showVerdictDetail, setShowVerdictDetail] = useState(false)

  useEffect(() => {
    let alive = true

    async function loadProject() {
      if (!userId) {
        resetTrainingProject()
        return
      }

      setLoading(true)
      setError(null)

      try {
        const activeSession = await getActiveTrainingSession(userId)
        const detail = await getTrainingSessionDetail(activeSession.session_id)

        if (!alive) {
          return
        }

        const mappedSteps = detail.steps
          .sort((a, b) => a.step_index - b.step_index)
          .map((step) => buildStep(step, detail.session))

        const progressPercent =
          mappedSteps.length === 0
            ? 0
            : Math.round(
                (mappedSteps.filter((step) => step.status === 'passed').length / mappedSteps.length) * 100,
              )

        const seedMessages: WorkbenchChatMessage[] = [
          {
            id: 'teacher-tip',
            role: 'teacher',
            content: '教师提示：先确认所有关键工具，再上传本步骤证据，避免在裁决环节被退回。',
            createdAt: new Date().toISOString(),
          },
          {
            id: 'assistant-tip',
            role: 'assistant',
            content: 'AI 助手：若发现工具异常，请标记为 ANOMALY，我会在右栏给出补充建议。',
            createdAt: new Date().toISOString(),
          },
        ]

        hydrateTrainingProject({
          project: {
            sessionId: detail.session.session_id,
            projectId: detail.session.project_id,
            title: `${detail.session.project_id} 训练任务`,
            progressPercent,
          },
          steps: mappedSteps,
          currentStepId: mappedSteps.find((step) => step.status === 'active')?.id ?? mappedSteps[0]?.id ?? null,
          messages: seedMessages,
        })
      } catch (requestError) {
        if (!alive) {
          return
        }

        resetTrainingProject()
        setError(requestError instanceof Error ? requestError.message : '训练项目加载失败')
      } finally {
        if (alive) {
          setLoading(false)
        }
      }
    }

    void loadProject()

    return () => {
      alive = false
    }
  }, [hydrateTrainingProject, resetTrainingProject, userId])

  const currentStep = useMemo(() => getCurrentStep(workbenchStore.getState()), [
    currentStepId,
    steps,
  ])
  const criticalCounter = useMemo(
    () => getConfirmedCriticalToolCount(workbenchStore.getState()),
    [currentStepId, steps, toolStatusMap],
  )
  const canSubmit = useMemo(() => canSubmitCurrentStep(workbenchStore.getState()), [
    currentStepId,
    steps,
    toolStatusMap,
  ])

  const currentTools = currentStep?.tools ?? []

  const handleEvidenceChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    setEvidenceName(file?.name ?? null)
  }

  const handleSubmitStep = () => {
    if (!currentStep) {
      return
    }

    const summary = noteDraft.trim() || '操作记录完整，满足提交条件。'

    setVerdict({
      result: canSubmit ? 'PASS' : 'FAIL',
      summary,
      details: canSubmit ? '关键工具已全部确认，可进入下一步。' : '仍有关键工具未确认，建议先补齐确认记录。',
    })

    addMessage({
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: canSubmit
        ? `步骤「${currentStep.title}」已提交。建议继续执行下一步骤，并同步上传现场证据。`
        : `步骤「${currentStep.title}」暂未满足提交条件，请先确认关键工具或标记异常。`,
      createdAt: new Date().toISOString(),
    })
  }

  if (loading) {
    return (
      <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center">
        <Spin size="large" />
      </div>
    )
  }

  if (!project || steps.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="训练工作台"
          subtitle="步骤编排、工具确认、证据上传与 AI 提示统一在此处理"
          breadcrumb={['学生端', '训练工作台']}
        />
        <EmptyState
          action={{ label: '去 AI 工作台创建训练', onClick: () => navigate('/ai-chat') }}
          description={error ?? '当前没有可恢复的训练项目，可先到 AI 工作台创建训练任务。'}
          icon={Dumbbell}
          title="还没有训练项目"
        />
      </div>
    )
  }

  return (
    <TooltipProvider>
      <div className="space-y-4">
        <PageHeader
          title="训练工作台"
          subtitle={`${project.title} · 会话 ${project.sessionId.slice(0, 8)} · 项目 ${project.projectId}`}
          breadcrumb={['学生端', '训练工作台']}
        />

        <div className="grid h-[calc(100vh-11rem)] min-h-[720px] grid-cols-[280px_1fr_300px] gap-4">
          <SectionCard
            actions={<span className="font-mono text-xs text-text-muted">{steps.filter((step) => step.status === 'passed').length}/{steps.length}</span>}
            className="flex h-full flex-col"
            title="训练步骤"
          >
            <div className="space-y-4">
              <Progress value={project.progressPercent} />
              <ScrollArea className="h-[calc(100vh-18rem)] pr-3">
                <div className="space-y-2">
                  {steps.map((step) => (
                    <button
                      key={step.id}
                      className={cn(
                        'flex h-14 w-full items-center gap-3 rounded-md px-3 text-left transition-colors duration-base ease-base',
                        currentStepId === step.id
                          ? 'border-l-[3px] border-primary bg-bg-elevated'
                          : 'bg-bg-surface hover:bg-bg-elevated',
                      )}
                      type="button"
                      onClick={() => setCurrentStep(step.id)}
                    >
                      {getStepStatusIcon(step.status)}
                      <div className="min-w-0 flex-1">
                        <div
                          className={cn(
                            'truncate text-sm',
                            step.status === 'failed'
                              ? 'text-danger'
                              : step.status === 'passed'
                                ? 'text-text-secondary'
                                : 'text-text-primary',
                          )}
                        >
                          {step.title}
                        </div>
                        <div className="truncate text-xs text-text-muted">{step.instruction}</div>
                      </div>
                      <div className="font-mono text-xs text-text-muted">{formatDuration(step.durationSec)}</div>
                    </button>
                  ))}
                </div>
              </ScrollArea>
            </div>
          </SectionCard>

          <div className="grid h-full grid-rows-[minmax(0,60%)_minmax(0,40%)] gap-4">
            <div
              className={cn(
                'relative overflow-hidden rounded-xl border border-border-subtle bg-bg-surface',
                isViewerFullscreen && 'ring-1 ring-primary/40',
              )}
            >
              <div className="absolute right-4 top-4 z-10 flex gap-2">
                <Button size="icon" type="button" variant="ghost" onClick={() => window.location.reload()}>
                  <RefreshCw className="h-4 w-4" />
                </Button>
                <Button
                  size="icon"
                  type="button"
                  variant="ghost"
                  onClick={() => setViewerFullscreen(!isViewerFullscreen)}
                >
                  {isViewerFullscreen ? <Expand className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                </Button>
              </div>
              <Atom01Viewer
                backgroundColor="#07111f"
                height="100%"
                showGrid={false}
                width="100%"
              />
            </div>

            <SectionCard className="flex h-full flex-col" title="当前步骤操作">
              {currentStep ? (
                <div className="flex h-full flex-col gap-4">
                  <div>
                    <div className="mb-2 text-sm font-medium text-text-primary">{currentStep.title}</div>
                    <p className="text-sm leading-7 text-text-primary">{currentStep.instruction}</p>
                  </div>

                  <Input
                    placeholder="记录当前步骤执行说明或异常备注"
                    value={noteDraft}
                    onChange={(event) => setNoteDraft(event.target.value)}
                  />

                  <label className="flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-border-default bg-bg-elevated px-4 py-6 text-center">
                    <input className="hidden" type="file" onChange={handleEvidenceChange} />
                    <div className="text-sm text-text-primary">
                      {evidenceName ? `已选择证据：${evidenceName}` : '拖拽或点击上传证据'}
                    </div>
                    <div className="mt-1 text-xs text-text-muted">建议上传步骤照片或关键操作截图</div>
                  </label>

                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div>
                        <Button
                          className="w-full"
                          disabled={!canSubmit}
                          type="button"
                          onClick={handleSubmitStep}
                        >
                          提交当前步骤
                        </Button>
                      </div>
                    </TooltipTrigger>
                    {!canSubmit ? (
                      <TooltipContent>请先确认所有关键工具</TooltipContent>
                    ) : null}
                  </Tooltip>

                  {verdict ? (
                    <div
                      className={cn(
                        'rounded-lg border-l-4 px-4 py-3',
                        verdict.result === 'PASS'
                          ? 'border-success bg-success/5'
                          : 'border-danger bg-danger/5',
                      )}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <div className="text-sm font-medium text-text-primary">
                            {verdict.result === 'PASS' ? '步骤裁决通过' : '步骤裁决未通过'}
                          </div>
                          <div className="mt-1 text-sm text-text-secondary">{verdict.summary}</div>
                        </div>
                        <Button
                          size="sm"
                          type="button"
                          variant="ghost"
                          onClick={() => setShowVerdictDetail((prev) => !prev)}
                        >
                          LLM 解释
                          <ChevronDown className={cn('h-4 w-4 transition-transform', showVerdictDetail && 'rotate-180')} />
                        </Button>
                      </div>
                      {showVerdictDetail ? (
                        <div className="mt-3 text-xs leading-6 text-text-muted">
                          {verdict.details ?? '本次裁决未返回更多说明。'}
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              ) : (
                <EmptyState
                  description="请先从左侧步骤列表中选择一个步骤。"
                  icon={Dumbbell}
                  title="还未选择步骤"
                />
              )}
            </SectionCard>
          </div>

          <div className="flex h-full flex-col gap-4">
            <SectionCard
              actions={
                <span className="font-mono text-xs text-text-muted">
                  确认 {criticalCounter.confirmed}/{criticalCounter.total}
                </span>
              }
              className="flex min-h-0 flex-1 flex-col"
              title="工具清单"
            >
              <ScrollArea className="h-[calc(100vh-28rem)] pr-3">
                <div className="space-y-3">
                  {currentTools.map((tool) => {
                    const status = toolStatusMap[tool.id] ?? 'PENDING'
                    return (
                      <div
                        key={tool.id}
                        className={cn(
                          'rounded-lg border border-border-subtle px-3 py-3',
                          status === 'CONFIRMED' && 'bg-success/5',
                          status === 'ANOMALY' && 'bg-amber-500/10',
                        )}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <span
                                className={cn(
                                  'inline-block h-2.5 w-2.5 rounded-full',
                                  tool.isCritical ? 'bg-danger' : 'bg-text-muted',
                                )}
                              />
                              <div className="truncate text-sm text-text-primary">{tool.name}</div>
                            </div>
                            <div className="mt-1 text-xs text-text-muted">{tool.spec ?? '未配置规格'}</div>
                          </div>
                          <div className="flex gap-1">
                            <ToolStatusButton
                              activeStatus={status}
                              targetStatus="CONFIRMED"
                              toolId={tool.id}
                              onClick={setToolStatus}
                            >
                              <CheckCircle2 className="h-4 w-4 text-success" />
                            </ToolStatusButton>
                            <ToolStatusButton
                              activeStatus={status}
                              targetStatus="ANOMALY"
                              toolId={tool.id}
                              onClick={setToolStatus}
                            >
                              <AlertTriangle className="h-4 w-4 text-amber-400" />
                            </ToolStatusButton>
                            <ToolStatusButton
                              activeStatus={status}
                              targetStatus="PENDING"
                              toolId={tool.id}
                              onClick={setToolStatus}
                            >
                              <Circle className="h-4 w-4 text-text-muted" />
                            </ToolStatusButton>
                          </div>
                        </div>
                        {status === 'ANOMALY' ? (
                          <div className="mt-3 text-xs leading-6 text-amber-300">
                            {tool.recommendation ?? 'Agent 建议：请补拍当前工具状态，并联系教师确认是否可继续执行。'}
                          </div>
                        ) : null}
                      </div>
                    )
                  })}
                </div>
              </ScrollArea>
            </SectionCard>

            <SectionCard className="h-[300px]" title="AI 助手">
              <div className="flex h-full flex-col gap-3">
                <ScrollArea className="flex-1 pr-3">
                  <div className="space-y-3">
                    {messages.slice(-5).map((message) => (
                      <div
                        key={message.id}
                        className={cn(
                          'rounded-lg px-3 py-2 text-sm',
                          message.role === 'teacher'
                            ? 'border-l-2 border-success bg-success/5'
                            : message.role === 'assistant'
                              ? 'bg-bg-elevated text-text-primary'
                              : 'bg-primary-muted text-text-primary',
                        )}
                      >
                        <div className="mb-1 flex items-center gap-2">
                          <StatusBadge
                            label={
                              message.role === 'teacher'
                                ? '教师提示'
                                : message.role === 'assistant'
                                  ? 'AI 助手'
                                  : '学员记录'
                            }
                            status={message.role === 'teacher' ? 'success' : 'active'}
                          />
                          <span className="font-mono text-[11px] text-text-muted">
                            {new Date(message.createdAt).toLocaleTimeString('zh-CN', {
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </span>
                        </div>
                        <div className="leading-6 text-text-secondary">{message.content}</div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>

                <div className="flex gap-2">
                  <Input
                    placeholder="向 AI 助手补充现场说明"
                    value={noteDraft}
                    onChange={(event) => setNoteDraft(event.target.value)}
                  />
                  <Button
                    size="icon"
                    type="button"
                    variant="secondary"
                    onClick={() => {
                      if (!noteDraft.trim()) {
                        return
                      }
                      addMessage({
                        id: `user-${Date.now()}`,
                        role: 'user',
                        content: noteDraft.trim(),
                        createdAt: new Date().toISOString(),
                      })
                      setNoteDraft('')
                    }}
                  >
                    <Send className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </SectionCard>
          </div>
        </div>
      </div>
    </TooltipProvider>
  )
}

export default TrainingWorkbenchPage
