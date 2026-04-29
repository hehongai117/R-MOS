import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Drawer, message } from 'antd'
import {
  ArrowRight,
  CheckCircle2,
  ClipboardList,
  Copy,
  FileSearch,
  History,
  Rocket,
  Send,
  ShieldCheck,
  Sparkles,
} from 'lucide-react'

import {
  type AgentExecutionResult,
  type DiagnosisActionType,
  type AgentRequestV2,
  type PolicyDecision,
  getTraceEvents,
  runDiagnosisAction,
  sendAgentRequestV2,
} from '@/api/agent-v2'
import { createTaskFromDiagnosis } from '@/api/pipeline'
import { setWorkbenchCapsule } from '@/components/Agent/AgentStatusCapsule'
import {
  DiagnosisPanel,
  persistLatestDiagnosisResult,
} from '@/components/DiagnosisPanel/DiagnosisPanel'
import {
  DataCard,
  EmptyState,
  PageHeader,
  SectionCard,
  StatusBadge,
} from '@/components/common'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { useWebSocket } from '@/hooks/useWebSocket'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/store/authStore'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  traceId?: string
  policyDecision?: PolicyDecision
  result?: AgentExecutionResult
}

interface QuickAction {
  id: string
  title: string
  desc: string
  prompt: string
  intent: string
  icon: typeof Rocket
}

const intentOptions = [
  { value: 'general', label: '通用问答' },
  { value: 'execute-task', label: '派单维保' },
  { value: 'delegate-diagnoser', label: '诊断问题' },
  { value: 'read-kb', label: '知识查询' },
  { value: 'write-kb', label: '知识记录' },
  { value: 'delegate-coach', label: '训练指导' },
]

const quickActions: QuickAction[] = [
  {
    id: 'dispatch',
    title: '派单维保',
    desc: '创建维保任务与执行步骤',
    prompt: '请为我创建一个维保派单，并给出执行步骤。',
    intent: 'execute-task',
    icon: Rocket,
  },
  {
    id: 'diagnose',
    title: '诊断问题',
    desc: '分析设备异常与根因',
    prompt: '请帮我诊断当前设备异常并给出排查建议。',
    intent: 'delegate-diagnoser',
    icon: FileSearch,
  },
  {
    id: 'kb',
    title: '知识查询',
    desc: '检索 SOP 与操作知识',
    prompt: '查询减速器相关 SOP 和注意事项。',
    intent: 'read-kb',
    icon: ShieldCheck,
  },
  {
    id: 'tasks',
    title: '查看任务',
    desc: '汇总当前执行上下文',
    prompt: '查看我当前进行中的任务和状态。',
    intent: 'general',
    icon: ClipboardList,
  },
  {
    id: 'approvals',
    title: '审批待办',
    desc: '检查待审批项与风险等级',
    prompt: '查看当前待审批项，并说明每项风险等级。',
    intent: 'general',
    icon: CheckCircle2,
  },
  {
    id: 'reports',
    title: '查看报告',
    desc: '输出执行总结与问题报告',
    prompt: '生成今天的执行总结和问题报告。',
    intent: 'general',
    icon: History,
  },
]

const riskStatusMap: Record<string, 'success' | 'warning' | 'error'> = {
  R0: 'success',
  R1: 'success',
  R2: 'warning',
  R3: 'error',
}

function MessageBody({ content }: { content: string }) {
  const codeMatch = content.match(/```([\s\S]+?)```/)

  if (!codeMatch) {
    return <p className="whitespace-pre-wrap text-sm leading-7 text-text-primary">{content}</p>
  }

  const plain = content.replace(codeMatch[0], '').trim()

  return (
    <div className="space-y-3">
      {plain ? <p className="whitespace-pre-wrap text-sm leading-7 text-text-primary">{plain}</p> : null}
      <pre className="overflow-x-auto rounded-md border border-border-subtle bg-bg-overlay p-3 text-sm text-text-secondary">
        <code>{codeMatch[1].trim()}</code>
      </pre>
    </div>
  )
}

function AgentWorkbenchPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const faultParam = searchParams.get('fault')
  const jointParam = searchParams.get('joint')

  const user = useAuthStore((state) => state.user)
  const { telemetryData } = useWebSocket()
  const [input, setInput] = useState('')
  const [intent, setIntent] = useState('general')
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [traceEvents, setTraceEvents] = useState<Record<string, unknown>[]>([])
  const [traceOpen, setTraceOpen] = useState(false)
  const [diagnosisActionLoading, setDiagnosisActionLoading] = useState(false)
  const [createdTask, setCreatedTask] = useState<{ task_id: number; execution_id: number; sop_name: string } | null>(null)
  const listRef = useRef<HTMLDivElement | null>(null)

  const latestTraceId = useMemo(
    () => [...messages].reverse().find((msg) => msg.traceId)?.traceId,
    [messages],
  )
  const latestDiagnosisBundle = useMemo(
    () =>
      [...messages]
        .reverse()
        .find(
          (msg) =>
            msg.result?.diagnosis || msg.result?.maintenance_plan || msg.result?.verification,
        )?.result ?? null,
    [messages],
  )

  useEffect(() => {
    if (!listRef.current) {
      return
    }
    listRef.current.scrollTop = listRef.current.scrollHeight
  }, [messages])

  useEffect(() => {
    if (loading) {
      setWorkbenchCapsule({
        state: 'EXECUTING',
        title: '智能体处理中',
        detail: '正在生成响应',
      })
      return
    }

    const latestAssistant = [...messages].reverse().find((msg) => msg.role === 'assistant')

    if (!latestAssistant) {
      setWorkbenchCapsule(null)
      return
    }

    const decision = latestAssistant.policyDecision

    if (decision?.requires_approval) {
      setWorkbenchCapsule({
        state: 'WAITING_APPROVAL',
        title: '等待审批',
        detail: decision.approval_level ? `${decision.approval_level} 级` : undefined,
        action: '等待中…',
      })
      return
    }

    if ((decision?.evidence_required?.length || 0) > 0) {
      setWorkbenchCapsule({
        state: 'NEED_EVIDENCE',
        title: '需补充证据',
        detail: decision?.evidence_required?.[0],
        action: '提交证据',
      })
      return
    }

    if (decision?.allowed === false) {
      setWorkbenchCapsule({
        state: 'BLOCKED',
        title: '策略阻断',
        detail: '缺少权限或风险过高',
      })
      return
    }

    setWorkbenchCapsule({
      state: 'DONE',
      title: '任务已响应',
      detail: latestAssistant.content.slice(0, 18),
      action: latestTraceId ? '查看轨迹' : undefined,
    })
  }, [loading, messages, latestTraceId])

  // Auto-populate fault context on mount when arriving from MonitorPage
  useEffect(() => {
    if (!faultParam || messages.length > 0) return
    const alertMsg = `检测到设备告警：${jointParam ?? '未知关节'} 温度异常升高，已超过安全阈值。\n请输入"诊断"开始故障分析，或直接描述您的需求。`
    setMessages([{
      id: `system-${Date.now()}`,
      role: 'assistant',
      content: alertMsg,
      timestamp: Date.now(),
    }])
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [faultParam, jointParam])

  const submit = async (customInput?: string, customIntent?: string) => {
    const content = (customInput ?? input).trim()
    if (!content || loading) {
      return
    }

    const finalIntent = customIntent ?? intent
    if (finalIntent === 'delegate-diagnoser' && !telemetryData) {
      message.error('暂无遥测数据，无法发起诊断')
      return
    }

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      timestamp: Date.now(),
    }

    setMessages((prev) => [...prev, userMessage])
    if (!customInput) {
      setInput('')
    }
    setLoading(true)

    try {
      const request: AgentRequestV2 = {
        user_id: user?.user_id ? String(user.user_id) : 'anonymous',
        message: content,
        intent_classification: finalIntent,
        context: {},
        telemetry_payload: finalIntent === 'delegate-diagnoser' ? telemetryData ?? undefined : undefined,
      }

      const response = await sendAgentRequestV2(request)

      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.message,
        timestamp: Date.now(),
        traceId: response.trace_id,
        policyDecision: response.policy_decision,
        result: response.result,
      }

      if (response.result?.diagnosis || response.result?.maintenance_plan || response.result?.verification) {
        persistLatestDiagnosisResult({
          diagnosisResult: response.result.diagnosis ?? null,
          maintenancePlan: response.result.maintenance_plan ?? null,
          verificationResult: response.result.verification ?? null,
          traceId: response.trace_id,
          timestamp: Date.now(),
        })
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (error: unknown) {
      const err = error as Error
      message.error(err.message || '请求失败')
    } finally {
      setLoading(false)
    }
  }

  const handleDiagnosisAction = async (action: DiagnosisActionType) => {
    if (!latestTraceId || diagnosisActionLoading) {
      if (!latestTraceId) {
        message.error('当前没有可操作的诊断轨迹')
      }
      return
    }

    setDiagnosisActionLoading(true)
    try {
      const response = await runDiagnosisAction(latestTraceId, action)
      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-action-${Date.now()}`,
          role: 'assistant',
          content: response.message,
          timestamp: Date.now(),
          traceId: response.trace_id,
        },
      ])
    } catch (error: unknown) {
      const err = error as Error
      message.error(err.message || '诊断动作执行失败')
    } finally {
      setDiagnosisActionLoading(false)
    }
  }

  const handleConfirmDiagnosisExecution = () => {
    void handleDiagnosisAction('confirm_execution')
  }

  const handleEscalateDiagnosis = () => {
    void handleDiagnosisAction('escalate_to_teacher')
  }

  const handleCreatePipelineTask = async () => {
    const diagnosis = latestDiagnosisBundle?.diagnosis
    if (!diagnosis?.fault_type || !latestTraceId) return
    try {
      const result = await createTaskFromDiagnosis({
        diagnosis_trace_id: latestTraceId,
        fault_type: diagnosis.fault_type,
        student_id: user?.user_id ?? 1,
      })
      setCreatedTask(result)
      message.success(`维保任务已创建: ${result.sop_name}`)
      navigate(`/maintenance?task_id=${result.task_id}&execution_id=${result.execution_id}`)
    } catch {
      message.error('创建维保任务失败')
    }
  }

  const openTrace = async (traceId: string) => {
    try {
      const response = await getTraceEvents(traceId)
      setTraceEvents(response.events || [])
      setTraceOpen(true)
    } catch {
      message.error('轨迹加载失败')
    }
  }

  const handleCopyTrace = async () => {
    if (!latestTraceId) {
      return
    }

    try {
      await navigator.clipboard.writeText(latestTraceId)
      message.success('会话 ID 已复制')
    } catch {
      message.error('复制失败')
    }
  }

  return (
    <div className="flex h-full min-h-[calc(100vh-4rem)] gap-4">
      <div className="flex min-w-0 flex-1 flex-col gap-4">
        <PageHeader
          title="Agent 工作台"
          subtitle="维保编排、知识查询与轨迹追踪统一入口"
          breadcrumb={['工作台', 'Agent']}
        />

        <div className="grid gap-4 md:grid-cols-3">
          <DataCard
            title="Agent 状态"
            value={loading ? '处理中' : messages.length > 0 ? '在线' : '待命'}
            trend={loading ? 'up' : 'flat'}
            trendValue={loading ? '响应生成中' : '消息就绪'}
            status={loading ? 'warning' : 'success'}
          />
          <DataCard
            title="会话 ID"
            value={latestTraceId ? latestTraceId.slice(0, 8) : '未创建'}
            trendValue={latestTraceId ? '点击复制完整 trace' : '等待首次响应'}
            status="normal"
          />
          <DataCard
            title="消息数"
            value={messages.length}
            unit="条"
            trend={messages.length > 0 ? 'up' : 'flat'}
            trendValue={messages.length > 0 ? '对话已建立' : '尚无消息'}
            status="normal"
          />
        </div>

        <div className="glass-card flex items-center justify-between rounded-xl px-5 py-4">
          <div className="flex items-center gap-3">
            <StatusBadge
              status={loading ? 'warning' : messages.length > 0 ? 'active' : 'idle'}
              label={loading ? '处理中' : messages.length > 0 ? '在线' : '空闲'}
            />
            <span className="text-sm text-text-secondary">AgentStatusCapsule 已同步到顶部全局状态</span>
          </div>
          <Button
            disabled={!latestTraceId}
            size="sm"
            variant="ghost"
            onClick={handleCopyTrace}
          >
            <Copy className="h-4 w-4" />
            复制会话 ID
          </Button>
        </div>

        <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-border-subtle bg-bg-surface">
          <div className="border-b border-border-subtle px-5 py-4">
            <div className="text-sm font-medium text-primary">对话流</div>
            <div className="text-xs text-text-muted">消息、风险卡片与证据需求在此聚合显示</div>
          </div>

          {messages.length === 0 ? (
            <EmptyState
              icon={Sparkles}
              title="R-MOS 维保智能体"
              description="告诉我你需要什么，我会基于当前工作台上下文生成响应。也可以先从下方快捷动作直接开始。"
            />
          ) : (
            <ScrollArea className="min-h-0 flex-1">
              <div className="space-y-4 p-5" ref={listRef}>
                {messages.map((item) => (
                  <div
                    key={item.id}
                    className={cn(
                      'flex',
                      item.role === 'user' ? 'justify-end' : 'justify-start',
                    )}
                  >
                    <div
                      className={cn(
                        'max-w-[80%] rounded-xl border p-3',
                        item.role === 'user'
                          ? 'border-primary/20 bg-primary-muted'
                          : 'border-border-subtle bg-bg-elevated',
                      )}
                    >
                      <div className="mb-2 flex items-center justify-between gap-4">
                        <StatusBadge
                          status={item.role === 'user' ? 'active' : 'success'}
                          label={item.role === 'user' ? '你' : '智能体'}
                        />
                        <div className="flex items-center gap-2 text-xs text-text-muted">
                          <span>{new Date(item.timestamp).toLocaleTimeString()}</span>
                          {item.traceId ? (
                            <button
                              className="rounded-full border border-border-default px-2 py-0.5 text-[11px] text-text-secondary transition-colors hover:border-primary hover:text-primary"
                              onClick={() => openTrace(item.traceId!)}
                              type="button"
                            >
                              trace
                            </button>
                          ) : null}
                        </div>
                      </div>

                      <MessageBody content={item.content} />

                      {item.policyDecision ? (
                        <div className="mt-3 space-y-3">
                          <div className="flex flex-wrap gap-2">
                            <StatusBadge
                              status={riskStatusMap[item.policyDecision.risk_level] ?? 'warning'}
                              label={`风险 ${item.policyDecision.risk_level}`}
                            />
                            {item.policyDecision.requires_approval ? (
                              <StatusBadge status="pending" label={`需审批 ${item.policyDecision.approval_level || ''}`} />
                            ) : null}
                          </div>

                          {(item.policyDecision.evidence_required?.length || 0) > 0 ? (
                            <div className="rounded-lg border-l-[3px] border-amber bg-amber/10 p-3">
                              <div className="mb-1 text-sm font-medium text-amber">证据需求</div>
                              <ul className="space-y-1 text-sm text-text-secondary">
                                {item.policyDecision.evidence_required.map((evidence) => (
                                  <li key={evidence}>{evidence}</li>
                                ))}
                              </ul>
                            </div>
                          ) : null}
                        </div>
                      ) : null}
                    </div>
                  </div>
                ))}
                {latestDiagnosisBundle?.diagnosis && (
                  <div className="flex justify-center px-4 py-3">
                    <button
                      className="rounded-lg bg-brand-500 px-6 py-3 text-base font-semibold text-white shadow-lg hover:bg-brand-600 transition-colors"
                      onClick={() => navigate('/maintenance')}
                    >
                      开始维保
                    </button>
                  </div>
                )}
              </div>
            </ScrollArea>
          )}

          <div className="border-t border-border-subtle bg-bg-surface p-4">
            <div className="mb-3">
              <Tabs value={intent} onValueChange={setIntent}>
                <TabsList className="w-full flex-wrap justify-start gap-1 bg-transparent p-0">
                  {intentOptions.map((item) => (
                    <TabsTrigger
                      key={item.value}
                      className="rounded-full border border-border-default bg-bg-elevated px-3 py-2 text-xs data-[state=active]:border-primary/40"
                      value={item.value}
                    >
                      {item.label}
                    </TabsTrigger>
                  ))}
                </TabsList>
              </Tabs>
            </div>

            <div className="space-y-3">
              <Textarea
                className="max-h-[120px] min-h-[96px]"
                placeholder="告诉我你的需求…"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault()
                    void submit()
                  }
                }}
              />
              <div className="flex items-center justify-between gap-3">
                <div className="flex flex-wrap gap-2">
                  {quickActions.map((action) => (
                    <Button
                      key={action.id}
                      size="sm"
                      variant="ghost"
                      onClick={() => void submit(action.prompt, action.intent)}
                    >
                      {action.title}
                    </Button>
                  ))}
                </div>
                <Button disabled={loading} onClick={() => void submit()}>
                  <Send className="h-4 w-4" />
                  发送
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="w-80 shrink-0 space-y-4">
        <SectionCard title="当前任务信息" description="基于最近一条响应推导当前上下文">
          <div className="space-y-4">
            <div className="rounded-lg border border-border-subtle bg-bg-elevated p-3">
              <div className="text-xs uppercase tracking-[0.18em] text-text-muted">最近 trace</div>
              <div className="mt-2 text-data text-sm text-text-primary">
                {latestTraceId ?? '等待任务启动'}
              </div>
            </div>

            <div className="rounded-lg border border-border-subtle bg-bg-elevated p-3">
              <div className="mb-2 text-xs uppercase tracking-[0.18em] text-text-muted">消息摘要</div>
              <div className="text-sm leading-6 text-text-secondary">
                {messages.length > 0
                  ? `${messages.length} 条消息，最近一次来自${messages[messages.length - 1]?.role === 'user' ? '用户' : '智能体'}`
                  : '尚未开始会话'}
              </div>
            </div>

            <div className="rounded-lg border border-border-subtle bg-bg-elevated p-3">
              <div className="mb-2 text-xs uppercase tracking-[0.18em] text-text-muted">下一步建议</div>
              <div className="flex items-start gap-2 text-sm text-text-secondary">
                <ArrowRight className="mt-0.5 h-4 w-4 text-primary" />
                <span>
                  {latestTraceId
                    ? '查看轨迹、补充证据，或继续发送下一条任务指令。'
                    : '先用下方快捷动作发起请求，或在输入区补充更具体的上下文。'}
                </span>
              </div>
            </div>
          </div>
        </SectionCard>

        <SectionCard
          title="诊断结果"
          description="展示故障推理、维保方案和仿真验证结果"
        >
          <DiagnosisPanel
            diagnosisResult={latestDiagnosisBundle?.diagnosis ?? null}
            maintenancePlan={latestDiagnosisBundle?.maintenance_plan ?? null}
            verificationResult={latestDiagnosisBundle?.verification ?? null}
            isLoading={loading && intent === 'delegate-diagnoser'}
            isActionSubmitting={diagnosisActionLoading}
            onConfirmExecution={handleConfirmDiagnosisExecution}
            onEscalateToTeacher={handleEscalateDiagnosis}
          />
          {latestDiagnosisBundle?.diagnosis?.fault_type && !createdTask && (
            <div className="mt-4 flex items-center gap-3 rounded-lg border border-blue-500/30 bg-blue-500/5 p-3">
              <div className="flex-1">
                <div className="text-sm font-medium">推荐: 创建维保任务</div>
                <div className="text-xs text-text-muted">基于诊断结果自动匹配 SOP 并创建任务</div>
              </div>
              <Button onClick={handleCreatePipelineTask}>
                创建维保任务 <ArrowRight className="ml-1 h-3 w-3" />
              </Button>
            </div>
          )}
        </SectionCard>
      </div>

      <Drawer
        open={traceOpen}
        placement="right"
        title="决策轨迹"
        width={560}
        onClose={() => setTraceOpen(false)}
      >
        <div className="space-y-4">
          {traceEvents.length === 0 ? (
            <EmptyState
              icon={History}
              title="暂无轨迹事件"
              description="当前 trace 没有返回事件，或事件列表尚未生成。"
            />
          ) : (
            traceEvents.map((event, index) => (
              <div key={`${String(event.event_type)}-${index}`} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <span className="h-3 w-3 rounded-full bg-primary" />
                  {index < traceEvents.length - 1 ? (
                    <span className="mt-1 h-full w-px bg-border-subtle" />
                  ) : null}
                </div>
                <div className="flex-1 rounded-lg border border-border-subtle bg-bg-surface p-3">
                  <div className="mb-2 flex items-center justify-between gap-4">
                    <div className="text-sm font-medium text-primary">
                      {String(event.event_type || `event-${index + 1}`)}
                    </div>
                    <div className="text-data text-xs text-text-muted">
                      {String(event.timestamp || index + 1)}
                    </div>
                  </div>
                  <pre className="overflow-x-auto whitespace-pre-wrap rounded-md bg-bg-overlay p-3 text-xs text-text-secondary">
                    {JSON.stringify(event, null, 2)}
                  </pre>
                </div>
              </div>
            ))
          )}
        </div>
      </Drawer>
    </div>
  )
}

export default AgentWorkbenchPage
