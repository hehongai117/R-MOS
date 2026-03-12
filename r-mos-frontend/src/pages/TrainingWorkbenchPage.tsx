import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  ChevronDown,
  Circle,
  Dumbbell,
  Expand,
  FileUp,
  ListChecks,
  Maximize2,
  RefreshCw,
  Send,
  Sparkles,
  Wrench,
  XCircle,
} from 'lucide-react'
import { type ChangeEvent, type FormEvent, useEffect, useMemo, useState } from 'react'
import { Spin } from 'antd'
import { AxiosError } from 'axios'
import { useNavigate } from 'react-router-dom'
import { useStore } from 'zustand'

import {
  askTrainingWorkbenchAssistant,
  generateTrainingWorkbenchDraft,
  getActiveTrainingSession,
  getTrainingSessionDetail,
  type SessionDetailResponse,
  type SessionResponse,
  submitTrainingWorkbenchStep,
  type TrainingWorkbenchAssistantMessage,
  type TrainingWorkbenchDraftResponse,
  uploadTrainingWorkbenchEvidence,
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
  type WorkbenchProject,
  type WorkbenchStep,
  type WorkbenchTool,
  type WorkbenchToolConfirmation,
  type WorkbenchToolStatus,
  workbenchStore,
} from '@/store/workbenchStore'

type StepBlueprint = {
  title: string
  instruction: string
  evidenceHint?: string
  modelTargets?: string[]
  tools: WorkbenchTool[]
}

const STEP_COPY: Record<string, StepBlueprint> = {
  prepare_station: {
    title: '准备工位',
    instruction: '确认作业台清洁、安全防护到位，并校验本步骤需要使用的关键工具。',
    evidenceHint: '建议上传工位全景、断电挂牌或 PPE 佩戴照片。',
    modelTargets: ['torso_link', 'left_arm_pitch_link', 'right_arm_pitch_link'],
    tools: [
      { id: 'ppe-gloves', name: '防护手套', spec: 'A级绝缘', isCritical: true },
      { id: 'torque-wrench', name: '扭矩扳手', spec: '5-25Nm', isCritical: true },
      { id: 'inspection-lamp', name: '检修灯', spec: '无频闪', isCritical: false },
    ],
  },
  motor_cover_remove: {
    title: '拆解电机盖',
    instruction: '按对角顺序松开固定螺钉，记录拆下零件的摆放方向，避免混放。',
    evidenceHint: '建议上传螺钉拆卸顺序照片和电机盖拆下后的局部特写。',
    modelTargets: ['torso_link', 'left_arm_yaw_link'],
    tools: [
      { id: 'hex-key', name: '六角扳手', spec: '4mm', isCritical: true },
      { id: 'parts-tray', name: '零件托盘', spec: '分区托盘', isCritical: true },
      { id: 'marker-pen', name: '记号笔', spec: '油性细头', isCritical: false },
    ],
  },
  align_reducer: {
    title: '校准减速器',
    instruction: '复核定位点和齿面状态，必要时拍照留证并记录偏差范围。',
    evidenceHint: '建议上传定位点和齿面状态照片，保留偏差读数。',
    modelTargets: ['torso_link', 'left_knee_link', 'right_knee_link'],
    tools: [
      { id: 'dial-indicator', name: '百分表', spec: '0.01mm', isCritical: true },
      { id: 'inspection-card', name: '检查记录卡', spec: '纸质/电子', isCritical: false },
    ],
  },
  final_check: {
    title: '最终复核',
    instruction: '完成工具回收、螺钉复紧和风险复盘后，再提交本步骤裁决。',
    evidenceHint: '建议上传复装后整体照片和关键紧固点复核照片。',
    modelTargets: ['torso_link', 'left_arm_pitch_link', 'right_arm_pitch_link'],
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
  if (status === 'completed' || status === 'pass') {
    return 'passed'
  }
  if (status === 'failed' || status === 'fail') {
    return 'failed'
  }
  if (index + 1 === currentStep) {
    return 'active'
  }
  return 'pending'
}

function buildFallbackStep(step: SessionDetailResponse['steps'][number], session: SessionResponse): WorkbenchStep {
  const fallbackIndex = ((step.step_index ?? 0) + FALLBACK_STEP_ORDER.length) % FALLBACK_STEP_ORDER.length
  const fallback = STEP_COPY[step.step_id] ?? STEP_COPY[FALLBACK_STEP_ORDER[fallbackIndex]]

  return {
    id: step.step_id,
    stepIndex: step.step_index,
    title: fallback.title,
    attemptCount: step.attempt_count,
    durationSec: step.duration_sec ?? undefined,
    status: mapStepStatus(step.status, session.current_step, step.step_index),
    instruction: fallback.instruction,
    evidenceHint: fallback.evidenceHint ?? '建议上传本步骤关键动作截图、工具状态照片或设备局部特写。',
    modelTargets: fallback.modelTargets ?? ['torso_link'],
    tools: fallback.tools,
    toolsConfirmed: (step.tools_confirmed ?? []).map((tool) => ({
      toolId: tool.tool_id,
      status: tool.status,
    })),
    evidenceBundleId: step.evidence?.bundle_id ?? null,
    evidenceNote: step.evidence?.note ?? null,
    verdict: step.verdict_result
      ? {
          result: step.verdict_result.result,
          summary: step.verdict_result.summary,
          details: step.verdict_result.details,
        }
      : null,
  }
}

function mapSnapshotStep(snapshotStep: NonNullable<NonNullable<SessionResponse['project_snapshot']>['steps']>[number], record: SessionDetailResponse['steps'][number], session: SessionResponse): WorkbenchStep {
  return {
    id: String(snapshotStep.id),
    stepIndex: Number(snapshotStep.step_index ?? record.step_index ?? 0),
    title: String(snapshotStep.title),
    attemptCount: record.attempt_count,
    durationSec: record.duration_sec ?? undefined,
    status: mapStepStatus(record.status, session.current_step, Number(snapshotStep.step_index ?? record.step_index ?? 0)),
    instruction: String(snapshotStep.instruction),
    evidenceHint:
      typeof snapshotStep.evidence_hint === 'string'
        ? snapshotStep.evidence_hint
        : '建议上传本步骤关键动作截图、工具状态照片或设备局部特写。',
    modelTargets: Array.isArray(snapshotStep.model_targets)
      ? snapshotStep.model_targets.filter((value): value is string => typeof value === 'string')
      : ['torso_link'],
    tools: Array.isArray(snapshotStep.tools)
      ? snapshotStep.tools.map((tool) => ({
          id: String(tool.id),
          name: String(tool.name),
          spec: typeof tool.spec === 'string' ? tool.spec : undefined,
          isCritical: Boolean(tool.is_critical),
          recommendation:
            typeof tool.recommendation === 'string' ? tool.recommendation : undefined,
        }))
      : [],
    toolsConfirmed: (record.tools_confirmed ?? []).map((tool) => ({
      toolId: tool.tool_id,
      status: tool.status,
    })),
    evidenceBundleId: record.evidence?.bundle_id ?? null,
    evidenceNote: record.evidence?.note ?? null,
    verdict: record.verdict_result
      ? {
          result: record.verdict_result.result,
          summary: record.verdict_result.summary,
          details: record.verdict_result.details,
        }
      : null,
  }
}

function buildToolStatusMap(steps: WorkbenchStep[]) {
  return steps.reduce<Record<string, WorkbenchToolStatus>>((acc, step) => {
    step.toolsConfirmed?.forEach((tool) => {
      acc[tool.toolId] = tool.status
    })
    return acc
  }, {})
}

function createDefaultMessages(detail?: SessionDetailResponse): WorkbenchChatMessage[] {
  const seedMessages = detail?.session.project_snapshot?.seed_messages
  if (Array.isArray(seedMessages) && seedMessages.length > 0) {
    return seedMessages.map((message, index) => ({
      id: String(message.id ?? `seed-${index}`),
      role:
        message.role === 'teacher' || message.role === 'user'
          ? message.role
          : 'assistant',
      content: String(message.content ?? ''),
      createdAt: typeof message.created_at === 'string' ? message.created_at : new Date().toISOString(),
    }))
  }

  return [
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
}

function buildProjectFromDetail(detail: SessionDetailResponse, mappedSteps: WorkbenchStep[]): WorkbenchProject {
  const title = detail.session.project_snapshot?.title || `${detail.session.project_id} 训练任务`
  const progressPercent =
    mappedSteps.length === 0
      ? 0
      : Math.round((mappedSteps.filter((step) => step.status === 'passed').length / mappedSteps.length) * 100)

  return {
    sessionId: detail.session.session_id,
    projectId: detail.session.project_id,
    title,
    progressPercent,
  }
}

function buildStepsFromDetail(detail: SessionDetailResponse): WorkbenchStep[] {
  const snapshotSteps = detail.session.project_snapshot?.steps ?? []
  const snapshotMap = new Map(snapshotSteps.map((step) => [String(step.id), step]))

  return [...detail.steps]
    .sort((a, b) => a.step_index - b.step_index)
    .map((step) => {
      const snapshotStep = snapshotMap.get(step.step_id)
      return snapshotStep
        ? mapSnapshotStep(snapshotStep, step, detail.session)
        : buildFallbackStep(step, detail.session)
    })
}

function normalizeStepStatus(status: 'pass' | 'fail'): WorkbenchStep['status'] {
  return status === 'pass' ? 'passed' : 'failed'
}

function updateStepsAfterSubmission(
  steps: WorkbenchStep[],
  stepId: string,
  status: 'pass' | 'fail',
  nextStepId: string | null,
  note: string,
  evidenceBundleId: string | null,
  toolsConfirmed: WorkbenchToolConfirmation[],
  verdict: WorkbenchStep['verdict'],
): WorkbenchStep[] {
  return steps.map((step) => {
    if (step.id === stepId) {
      return {
        ...step,
        status: normalizeStepStatus(status),
        attemptCount: (step.attemptCount ?? 0) + 1,
        evidenceBundleId,
        evidenceNote: note,
        toolsConfirmed,
        verdict,
      }
    }
    if (status === 'pass' && nextStepId && step.id === nextStepId && step.status === 'pending') {
      return {
        ...step,
        status: 'active',
      }
    }
    if (status === 'pass' && step.status === 'active' && step.id !== nextStepId) {
      return {
        ...step,
        status: 'pending',
      }
    }
    return step
  })
}

function buildToolActionLabel(toolName: string, targetStatus: WorkbenchToolStatus) {
  if (targetStatus === 'CONFIRMED') {
    return `将${toolName}标记为已确认`
  }
  if (targetStatus === 'ANOMALY') {
    return `将${toolName}标记为异常`
  }
  return `将${toolName}标记为待确认`
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
  label,
  activeStatus,
  targetStatus,
  children,
  onClick,
}: {
  toolId: string
  label: string
  activeStatus?: WorkbenchToolStatus
  targetStatus: WorkbenchToolStatus
  children: React.ReactNode
  onClick: (toolId: string, status: WorkbenchToolStatus) => void
}) {
  const isActive = activeStatus === targetStatus

  return (
    <Button
      aria-label={label}
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
  const setSteps = useStore(workbenchStore, (state) => state.setSteps)
  const setProject = useStore(workbenchStore, (state) => state.setProject)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showVerdictDetail, setShowVerdictDetail] = useState(false)
  const [draftRobotModel, setDraftRobotModel] = useState('ATOM01')
  const [draftTaskSummary, setDraftTaskSummary] = useState('关节电机盖拆装')
  const [draftFocusPrompt, setDraftFocusPrompt] = useState('强调工具确认、证据留存与 AI 提示')
  const [draftLoading, setDraftLoading] = useState(false)
  const [draftError, setDraftError] = useState<string | null>(null)
  const [submitLoading, setSubmitLoading] = useState(false)
  const [askLoading, setAskLoading] = useState(false)
  const [assistantDraft, setAssistantDraft] = useState('')
  const [selectedEvidenceFile, setSelectedEvidenceFile] = useState<File | null>(null)
  const [evidenceInputKey, setEvidenceInputKey] = useState(0)

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

        const mappedSteps = buildStepsFromDetail(detail)

        hydrateTrainingProject({
          project: buildProjectFromDetail(detail, mappedSteps),
          steps: mappedSteps,
          currentStepId: mappedSteps.find((step) => step.status === 'active')?.id ?? mappedSteps[0]?.id ?? null,
          messages: createDefaultMessages(detail),
          toolStatusMap: buildToolStatusMap(mappedSteps),
        })
      } catch (requestError) {
        if (!alive) {
          return
        }

        resetTrainingProject()
        if (requestError instanceof AxiosError && requestError.response?.status === 404) {
          setError(null)
          return
        }
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

  useEffect(() => {
    const activeStep = steps.find((step) => step.id === currentStepId) ?? null
    setVerdict(activeStep?.verdict ?? null)
    setEvidenceName(null)
    setSelectedEvidenceFile(null)
    setEvidenceInputKey((prev) => prev + 1)
    setShowVerdictDetail(false)
  }, [currentStepId, setEvidenceName, setVerdict, steps])

  const currentStep = useMemo(() => getCurrentStep(workbenchStore.getState()), [currentStepId, steps])
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
    setSelectedEvidenceFile(file ?? null)
    setEvidenceName(file?.name ?? null)
  }

  const handleSubmitStep = async () => {
    if (!currentStep || !project) {
      return
    }

    const note = noteDraft.trim()
    const toolsConfirmed: WorkbenchToolConfirmation[] = currentTools
      .map((tool) => ({
        toolId: tool.id,
        status: toolStatusMap[tool.id] ?? 'PENDING',
      }))
      .filter((tool) => tool.status !== 'PENDING')

    setSubmitLoading(true)
    setError(null)

    try {
      let evidenceBundleId = currentStep.evidenceBundleId ?? null
      if (selectedEvidenceFile) {
        const uploadResponse = await uploadTrainingWorkbenchEvidence(
          project.sessionId,
          currentStep.id,
          note || currentStep.evidenceHint || `${currentStep.title} 证据`,
          selectedEvidenceFile,
        )
        evidenceBundleId = uploadResponse.evidenceBundleId
        setEvidenceName(uploadResponse.filename)
      }

      const response = await submitTrainingWorkbenchStep(project.sessionId, currentStep.id, {
        stepIndex: currentStep.stepIndex,
        note,
        evidenceBundleId,
        toolsConfirmed,
      })

      const nextSteps = updateStepsAfterSubmission(
        steps,
        currentStep.id,
        response.status,
        response.nextStepId ?? null,
        note,
        evidenceBundleId,
        toolsConfirmed,
        response.verdict,
      )

      setSteps(nextSteps)
      setProject({
        ...project,
        progressPercent:
          nextSteps.length === 0
            ? 0
            : Math.round((nextSteps.filter((step) => step.status === 'passed').length / nextSteps.length) * 100),
      })
      setCurrentStep(
        response.status === 'pass' && response.nextStepId ? response.nextStepId : currentStep.id,
      )
      setVerdict(response.verdict)
      setShowVerdictDetail(true)
      addMessage({
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.verdict.details || response.verdict.summary,
        createdAt: new Date().toISOString(),
      })
      setSelectedEvidenceFile(null)
      setEvidenceInputKey((prev) => prev + 1)
      if (response.status === 'pass' && response.nextStepId) {
        setNoteDraft('')
        setEvidenceName(null)
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : '步骤提交失败')
    } finally {
      setSubmitLoading(false)
    }
  }

  const handleGenerateDraft = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setDraftLoading(true)
    setDraftError(null)

    try {
      const draft = await generateTrainingWorkbenchDraft({
        robotModel: draftRobotModel.trim() || 'ATOM01',
        taskSummary: draftTaskSummary.trim() || '关节电机盖拆装',
        focusPrompt: draftFocusPrompt.trim() || '强调工具确认、证据留存与 AI 提示',
      })
      hydrateTrainingProject(draft as TrainingWorkbenchDraftResponse)
      setError(null)
      setSelectedEvidenceFile(null)
      setAssistantDraft('')
      setEvidenceInputKey((prev) => prev + 1)
    } catch (requestError) {
      setDraftError(requestError instanceof Error ? requestError.message : '训练草案生成失败')
    } finally {
      setDraftLoading(false)
    }
  }

  const handleAskAssistant = async () => {
    if (!project || !currentStep) {
      return
    }

    const question = assistantDraft.trim()
    if (!question) {
      return
    }

    const userMessage: WorkbenchChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: question,
      createdAt: new Date().toISOString(),
    }

    const messagePayload = [...messages, userMessage]
      .slice(-6)
      .map((message) => ({
        role: message.role,
        content: message.content,
      }))

    addMessage(userMessage)
    setAssistantDraft('')
    setAskLoading(true)
    setError(null)

    try {
      const assistantMessage = await askTrainingWorkbenchAssistant({
        sessionId: project.sessionId,
        stepId: currentStep.id,
        question,
        messages: messagePayload,
      })
      addMessage(assistantMessage as TrainingWorkbenchAssistantMessage)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'AI 助手追问失败')
    } finally {
      setAskLoading(false)
    }
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
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_360px]">
          <SectionCard
            className="overflow-hidden"
            description="使用当前账号在设置页保存的大模型配置，生成可直接展示的训练工作台草案。"
            title="AI 生成训练草案"
          >
            <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_220px]">
              <form className="space-y-4" onSubmit={(event) => void handleGenerateDraft(event)}>
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="space-y-2 text-sm text-text-secondary">
                    <span>机器人型号</span>
                    <Input
                      aria-label="机器人型号"
                      value={draftRobotModel}
                      onChange={(event) => setDraftRobotModel(event.target.value)}
                    />
                  </label>
                  <label className="space-y-2 text-sm text-text-secondary">
                    <span>训练任务</span>
                    <Input
                      aria-label="训练任务"
                      value={draftTaskSummary}
                      onChange={(event) => setDraftTaskSummary(event.target.value)}
                    />
                  </label>
                </div>

                <label className="space-y-2 text-sm text-text-secondary">
                  <span>AI 生成重点</span>
                  <Input
                    aria-label="AI 生成重点"
                    value={draftFocusPrompt}
                    onChange={(event) => setDraftFocusPrompt(event.target.value)}
                  />
                </label>

                {(draftError || error) ? (
                  <div className="rounded-lg border border-danger/30 bg-danger/5 px-4 py-3 text-sm text-danger">
                    {draftError ?? error}
                  </div>
                ) : null}

                <div className="flex flex-wrap gap-3">
                  <Button disabled={draftLoading} type="submit">
                    <Sparkles className="h-4 w-4" />
                    {draftLoading ? '生成中…' : '生成训练草案'}
                  </Button>
                  <Button type="button" variant="outline" onClick={() => navigate('/settings')}>
                    去设置页检查模型配置
                  </Button>
                  <Button type="button" variant="ghost" onClick={() => navigate('/ai-chat')}>
                    去 AI 工作台
                  </Button>
                </div>
              </form>

              <div className="rounded-2xl border border-primary/20 bg-[radial-gradient(circle_at_top,_rgba(0,153,255,0.18),_transparent_58%),linear-gradient(180deg,rgba(12,21,40,0.96),rgba(6,12,24,0.92))] p-5">
                <div className="text-xs uppercase tracking-[0.18em] text-primary/70">Preview</div>
                <div className="mt-3 text-lg font-semibold text-text-primary">
                  生成后会直接铺开完整训练画布
                </div>
                <div className="mt-2 text-sm leading-6 text-text-secondary">
                  包括步骤编排、工具确认、证据上传提示和 AI 助手首轮建议，方便先看页面结构，再决定是否正式建训练项目。
                </div>
                <div className="mt-5 space-y-3">
                  {[
                    { icon: ListChecks, title: '步骤编排', detail: '3 到 5 个训练步骤，首步自动激活' },
                    { icon: Wrench, title: '工具确认', detail: '关键工具带确认状态与异常建议' },
                    { icon: FileUp, title: '证据上传', detail: '每步附带证据留存提示' },
                    { icon: Bot, title: 'AI 提示', detail: '生成教师提示与 AI 助手开场建议' },
                  ].map((item) => (
                    <div key={item.title} className="flex items-start gap-3 rounded-xl bg-white/5 px-3 py-3">
                      <item.icon className="mt-0.5 h-4 w-4 text-primary" />
                      <div>
                        <div className="text-sm font-medium text-text-primary">{item.title}</div>
                        <div className="text-xs leading-5 text-text-muted">{item.detail}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </SectionCard>

          <SectionCard
            description="如果暂时不需要 AI 生成，也可以从现有入口继续使用。"
            title="当前状态"
          >
            <div className="space-y-4">
              <EmptyState
                action={{ label: '去 AI 工作台创建训练', onClick: () => navigate('/ai-chat') }}
                description={error ?? '当前没有可恢复的训练项目，可先生成一份草案，或继续从 AI 工作台创建正式训练任务。'}
                icon={Dumbbell}
                title="还没有训练项目"
              />
            </div>
          </SectionCard>
        </div>
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
                highlightLinks={currentStep?.modelTargets ?? ['torso_link']}
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

                  {error ? (
                    <div className="rounded-lg border border-danger/30 bg-danger/5 px-4 py-3 text-sm text-danger">
                      {error}
                    </div>
                  ) : null}

                  <Input
                    placeholder="记录当前步骤执行说明或异常备注"
                    value={noteDraft}
                    onChange={(event) => setNoteDraft(event.target.value)}
                  />

                  <label className="flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-border-default bg-bg-elevated px-4 py-6 text-center">
                    <input
                      key={evidenceInputKey}
                      className="hidden"
                      type="file"
                      onChange={handleEvidenceChange}
                    />
                    <div className="text-sm text-text-primary">
                      {evidenceName ? `已选择证据：${evidenceName}` : '拖拽或点击上传证据'}
                    </div>
                    <div className="mt-1 text-xs text-text-muted">
                      {currentStep.evidenceHint ?? '建议上传步骤照片或关键操作截图'}
                    </div>
                    {currentStep.evidenceBundleId ? (
                      <div className="mt-2 text-xs text-success">
                        当前步骤已有证据包：{currentStep.evidenceBundleId}
                      </div>
                    ) : null}
                  </label>

                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div>
                        <Button
                          className="w-full"
                          disabled={!canSubmit || submitLoading}
                          type="button"
                          onClick={() => void handleSubmitStep()}
                        >
                          {submitLoading ? '提交中…' : '提交当前步骤'}
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
                              label={buildToolActionLabel(tool.name, 'CONFIRMED')}
                              targetStatus="CONFIRMED"
                              toolId={tool.id}
                              onClick={setToolStatus}
                            >
                              <CheckCircle2 className="h-4 w-4 text-success" />
                            </ToolStatusButton>
                            <ToolStatusButton
                              activeStatus={status}
                              label={buildToolActionLabel(tool.name, 'ANOMALY')}
                              targetStatus="ANOMALY"
                              toolId={tool.id}
                              onClick={setToolStatus}
                            >
                              <AlertTriangle className="h-4 w-4 text-amber-400" />
                            </ToolStatusButton>
                            <ToolStatusButton
                              activeStatus={status}
                              label={buildToolActionLabel(tool.name, 'PENDING')}
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
                    value={assistantDraft}
                    onChange={(event) => setAssistantDraft(event.target.value)}
                  />
                  <Button
                    aria-label="发送给 AI 助手"
                    size="icon"
                    type="button"
                    variant="secondary"
                    disabled={askLoading}
                    onClick={() => void handleAskAssistant()}
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
