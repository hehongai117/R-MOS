import { MessageSquareOff, Monitor, RefreshCw, UserCircle2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { getStudentProfile, type SkillProfileResponse } from '@/api/training'
import {
  getAttempt,
  listAssignmentAttempts,
  listAssignments,
  listClasses,
} from '@/api/teaching'
import { DataCard, EmptyState, PageHeader, SectionCard, StatusBadge } from '@/components/common'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { useWebSocket } from '@/hooks/useWebSocket'
import { cn } from '@/lib/utils'
import type { Assignment, AssignmentAttempt, TeachingClass } from '@/types/teaching'

const POLL_INTERVAL_MS = 10000

function attemptStatusLabel(status: AssignmentAttempt['status']) {
  if (status === 'in_progress') {
    return '训练中'
  }
  if (status === 'completed') {
    return '已完成'
  }
  if (status === 'graded') {
    return '已评分'
  }
  return '已放弃'
}

function attemptStatusTone(status: AssignmentAttempt['status']) {
  if (status === 'in_progress') {
    return 'active'
  }
  if (status === 'completed' || status === 'graded') {
    return 'success'
  }
  return 'warning'
}

function formatDateTime(value?: string) {
  if (!value) {
    return '暂无'
  }
  return new Date(value).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function TeacherMonitorPage() {
  const navigate = useNavigate()
  const ws = useWebSocket()

  const [classes, setClasses] = useState<TeachingClass[]>([])
  const [assignments, setAssignments] = useState<Assignment[]>([])
  const [attempts, setAttempts] = useState<AssignmentAttempt[]>([])
  const [selectedClassId, setSelectedClassId] = useState<number | null>(null)
  const [selectedAssignmentId, setSelectedAssignmentId] = useState<number | null>(null)
  const [selectedAttempt, setSelectedAttempt] = useState<AssignmentAttempt | null>(null)
  const [selectedProfile, setSelectedProfile] = useState<SkillProfileResponse | null>(null)

  const [loading, setLoading] = useState(false)
  const [attemptsLoading, setAttemptsLoading] = useState(false)
  const [profileLoading, setProfileLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true

    async function loadMeta() {
      setLoading(true)
      setError(null)
      try {
        const [classList, assignmentList] = await Promise.all([listClasses(), listAssignments()])
        if (!alive) {
          return
        }

        setClasses(classList)
        setAssignments(assignmentList)

        const initialClassId = classList[0]?.id ?? null
        const initialAssignmentId =
          assignmentList.find((assignment) => assignment.classId === initialClassId)?.id ??
          assignmentList[0]?.id ??
          null

        setSelectedClassId(initialClassId)
        setSelectedAssignmentId(initialAssignmentId)
      } catch (requestError) {
        if (alive) {
          setError(requestError instanceof Error ? requestError.message : '班级与作业加载失败')
        }
      } finally {
        if (alive) {
          setLoading(false)
        }
      }
    }

    void loadMeta()

    return () => {
      alive = false
    }
  }, [])

  useEffect(() => {
    if (!selectedAssignmentId) {
      setAttempts([])
      setSelectedAttempt(null)
      return
    }

    const assignmentId = selectedAssignmentId
    let alive = true

    async function loadAttempts() {
      setAttemptsLoading(true)
      try {
        const result = await listAssignmentAttempts(assignmentId)
        if (!alive) {
          return
        }
        setAttempts(result)
        setSelectedAttempt((current) => {
          if (!current) {
            return result[0] ?? null
          }
          return result.find((item) => item.id === current.id) ?? result[0] ?? null
        })
      } catch (requestError) {
        if (alive) {
          setError(requestError instanceof Error ? requestError.message : '尝试列表加载失败')
          setAttempts([])
        }
      } finally {
        if (alive) {
          setAttemptsLoading(false)
        }
      }
    }

    void loadAttempts()
    const timer = window.setInterval(() => {
      void loadAttempts()
    }, POLL_INTERVAL_MS)

    return () => {
      alive = false
      window.clearInterval(timer)
    }
  }, [selectedAssignmentId])

  useEffect(() => {
    if (!selectedAttempt) {
      setSelectedProfile(null)
      return
    }

    const attemptId = selectedAttempt.id
    const studentId = selectedAttempt.studentId
    let alive = true

    async function loadDetail() {
      setProfileLoading(true)
      try {
        const [profile, latestAttempt] = await Promise.all([
          getStudentProfile(studentId),
          getAttempt(attemptId),
        ])

        if (!alive) {
          return
        }

        setSelectedProfile(profile)
        setSelectedAttempt(latestAttempt)
      } catch {
        if (alive) {
          setSelectedProfile(null)
        }
      } finally {
        if (alive) {
          setProfileLoading(false)
        }
      }
    }

    void loadDetail()

    return () => {
      alive = false
    }
  }, [selectedAttempt])

  const filteredAssignments = useMemo(
    () =>
      selectedClassId
        ? assignments.filter((assignment) => assignment.classId === selectedClassId)
        : assignments,
    [assignments, selectedClassId],
  )

  const todayCompletedCount = useMemo(() => {
    const today = new Date().toDateString()
    return attempts.filter((attempt) => {
      if (attempt.status !== 'completed' && attempt.status !== 'graded') {
        return false
      }
      return attempt.updatedAt ? new Date(attempt.updatedAt).toDateString() === today : false
    }).length
  }, [attempts])

  const warningCount = useMemo(
    () => attempts.filter((attempt) => attempt.attemptIndex >= 3 || attempt.status === 'abandoned').length,
    [attempts],
  )

  const selectedClass = classes.find((item) => item.id === selectedClassId) ?? null
  const selectedAssignment =
    assignments.find((item) => item.id === selectedAssignmentId) ?? null

  const wsStatusLabel =
    ws.status === 'connected'
      ? '全局遥测在线'
      : ws.status === 'reconnecting'
        ? '重连中'
        : ws.status === 'failed'
          ? '连接失败'
          : '离线'

  const wsStatusTone =
    ws.status === 'connected'
      ? 'success'
      : ws.status === 'reconnecting'
        ? 'warning'
        : ws.status === 'failed'
          ? 'error'
          : 'idle'

  return (
    <TooltipProvider>
      <div className="space-y-6">
        <PageHeader
          actions={
            <div className="flex flex-wrap gap-2">
              <select
                className="h-10 rounded-md border border-border-default bg-bg-surface px-3 text-sm text-text-primary"
                value={selectedClassId ?? ''}
                onChange={(event) => {
                  const nextClassId = Number(event.target.value)
                  setSelectedClassId(nextClassId)
                  const nextAssignment = assignments.find((item) => item.classId === nextClassId)
                  setSelectedAssignmentId(nextAssignment?.id ?? null)
                }}
              >
                {classes.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
              <select
                className="h-10 rounded-md border border-border-default bg-bg-surface px-3 text-sm text-text-primary"
                value={selectedAssignmentId ?? ''}
                onChange={(event) => setSelectedAssignmentId(Number(event.target.value))}
              >
                {filteredAssignments.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.title}
                  </option>
                ))}
              </select>
              <Button size="icon" type="button" variant="ghost" onClick={() => window.location.reload()}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          }
          breadcrumb={['教师端', '班级监控台']}
          subtitle={
            selectedClass && selectedAssignment
              ? `${selectedClass.name} · ${selectedAssignment.title}`
              : '选择班级与作业后查看当前尝试状态'
          }
          title="班级监控台"
        />

        <div className="grid gap-4 lg:grid-cols-3">
          <DataCard
            status="normal"
            title="在训人数"
            unit="人"
            value={attempts.filter((attempt) => attempt.status === 'in_progress').length}
          />
          <DataCard
            status="success"
            title="今日已完成"
            unit="项"
            value={todayCompletedCount}
          />
          <DataCard
            status={warningCount > 0 ? 'warning' : 'normal'}
            title="失败预警"
            trendValue={wsStatusLabel}
            unit="项"
            value={warningCount}
          />
        </div>

        <div className="grid gap-4 xl:grid-cols-5">
          <SectionCard
            className="xl:col-span-3"
            description="每 10 秒轮询一次作业 attempts，实时 WS 仅用于全局在线状态"
            title="学员尝试列表"
          >
            {loading || attemptsLoading ? (
              <div className="flex min-h-[420px] items-center justify-center text-sm text-text-muted">
                加载中...
              </div>
            ) : attempts.length > 0 ? (
              <ScrollArea className="h-[520px] pr-3">
                <div className="space-y-2">
                  {attempts.map((attempt) => (
                    <button
                      key={attempt.id}
                      className={cn(
                        'flex w-full items-center gap-4 rounded-lg border border-border-subtle px-4 py-3 text-left transition-colors duration-base ease-base',
                        attempt.attemptIndex >= 3 && 'border-l-[3px] border-l-amber-400 bg-amber-500/5',
                        selectedAttempt?.id === attempt.id ? 'bg-bg-elevated' : 'bg-bg-surface hover:bg-bg-elevated',
                      )}
                      type="button"
                      onClick={() => setSelectedAttempt(attempt)}
                    >
                      <Avatar>
                        <AvatarFallback>{String(attempt.studentId).slice(-2)}</AvatarFallback>
                      </Avatar>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <div className="text-sm font-medium text-text-primary">
                            学员 {attempt.studentId}
                          </div>
                          <StatusBadge
                            label={`第 ${attempt.attemptIndex} 次`}
                            status={attempt.attemptIndex >= 3 ? 'warning' : 'pending'}
                          />
                        </div>
                        <div className="mt-1 text-xs text-text-muted">
                          状态 {attempt.status} · 更新时间 {formatDateTime(attempt.updatedAt)}
                        </div>
                      </div>
                      <StatusBadge
                        label={attemptStatusLabel(attempt.status)}
                        status={attemptStatusTone(attempt.status)}
                      />
                    </button>
                  ))}
                </div>
              </ScrollArea>
            ) : (
              <EmptyState
                description={error ?? '当前作业下还没有任何尝试记录。'}
                icon={Monitor}
                title="暂无尝试数据"
              />
            )}
          </SectionCard>

          <SectionCard className="xl:col-span-2" title="学员详情">
            {selectedAttempt ? (
              <div className="space-y-5">
                <div className="flex items-center gap-4">
                  <Avatar className="h-14 w-14">
                    <AvatarFallback>{String(selectedAttempt.studentId).slice(-2)}</AvatarFallback>
                  </Avatar>
                  <div>
                    <div className="text-lg text-text-primary">学员 {selectedAttempt.studentId}</div>
                    <div className="mt-1 flex items-center gap-2">
                      <StatusBadge
                        label={selectedProfile ? `Lv.${selectedProfile.overall_level}` : '等级待加载'}
                        status="active"
                      />
                      <StatusBadge label={wsStatusLabel} status={wsStatusTone} />
                    </div>
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-lg border border-border-subtle bg-bg-elevated p-3">
                    <div className="text-xs uppercase tracking-[0.2em] text-text-muted">状态</div>
                    <div className="mt-2 text-sm text-text-primary">{selectedAttempt.status}</div>
                  </div>
                  <div className="rounded-lg border border-border-subtle bg-bg-elevated p-3">
                    <div className="text-xs uppercase tracking-[0.2em] text-text-muted">尝试次数</div>
                    <div
                      className={cn(
                        'mt-2 font-mono text-sm',
                        selectedAttempt.attemptIndex >= 3 ? 'text-amber-300' : 'text-text-primary',
                      )}
                    >
                      {selectedAttempt.attemptIndex}
                    </div>
                  </div>
                  <div className="rounded-lg border border-border-subtle bg-bg-elevated p-3">
                    <div className="text-xs uppercase tracking-[0.2em] text-text-muted">分数</div>
                    <div className="mt-2 font-mono text-sm text-text-primary">
                      {selectedAttempt.score ?? '--'}
                    </div>
                  </div>
                  <div className="rounded-lg border border-border-subtle bg-bg-elevated p-3">
                    <div className="text-xs uppercase tracking-[0.2em] text-text-muted">任务 ID</div>
                    <div className="mt-2 font-mono text-sm text-text-primary">
                      {selectedAttempt.taskId ?? '--'}
                    </div>
                  </div>
                </div>

                {profileLoading ? (
                  <div className="text-sm text-text-muted">正在加载技能画像...</div>
                ) : selectedProfile ? (
                  <div className="rounded-lg border border-border-subtle bg-bg-elevated p-4 text-sm text-text-secondary">
                    累计训练 {selectedProfile.total_sessions} 次 · 总时长 {selectedProfile.total_duration} 秒 · 最近训练
                    {` ${formatDateTime(selectedProfile.last_trained_at ?? undefined)}`}
                  </div>
                ) : (
                  <div className="rounded-lg border border-border-subtle bg-bg-elevated p-4 text-sm text-text-muted">
                    当前未加载到该学员的技能画像。
                  </div>
                )}

                <div className="flex flex-wrap gap-2">
                  {/*
                    Legacy attempts can exist without a linked task, so evidence/diagnosis
                    pages are intentionally gated to avoid dead-end 404s.
                  */}
                  <Button
                    type="button"
                    variant="default"
                    onClick={() => navigate(`/teaching/attempts/${selectedAttempt.id}`)}
                  >
                    进入尝试详情
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={!selectedAttempt.taskId}
                    title={!selectedAttempt.taskId ? '该尝试未绑定任务，暂时无法查看证据' : undefined}
                    onClick={() => navigate(`/teaching/attempts/${selectedAttempt.id}/evidence`)}
                  >
                    查看证据
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={!selectedAttempt.taskId}
                    title={!selectedAttempt.taskId ? '该尝试未绑定任务，暂时无法查看诊断' : undefined}
                    onClick={() => navigate(`/teaching/attempts/${selectedAttempt.id}/diagnosis`)}
                  >
                    查看诊断
                  </Button>
                </div>

                <Tooltip>
                  <TooltipTrigger asChild>
                    <div>
                      <Button className="w-full" disabled type="button" variant="outline">
                        <MessageSquareOff className="h-4 w-4" />
                        教师发送提示
                      </Button>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>待后端接口</TooltipContent>
                </Tooltip>

                <div className="rounded-lg border border-border-subtle bg-bg-elevated p-4 text-xs leading-6 text-text-muted">
                  当前页面只展示现有 attempts payload 能提供的字段：`studentId / status / score / attemptIndex / taskId / updatedAt`。
                  `step_warning / current_step / duration` 仍需后端补接口。
                </div>
              </div>
            ) : (
              <EmptyState
                description="从左侧尝试列表中选择一名学员，即可查看详情和相关跳转入口。"
                icon={UserCircle2}
                title="尚未选择学员"
              />
            )}
          </SectionCard>
        </div>

        <SectionCard title="实时能力边界">
          <div className="flex flex-wrap items-center gap-3 text-sm text-text-secondary">
            <StatusBadge label={wsStatusLabel} status={wsStatusTone} />
            <span>
              WebSocket 当前只用于全局遥测在线/离线提示；页面明细仍通过每 {POLL_INTERVAL_MS / 1000} 秒轮询 attempts 刷新。
            </span>
            {ws.telemetryData ? <span>已接收遥测数据。</span> : null}
          </div>
        </SectionCard>
      </div>
    </TooltipProvider>
  )
}

export default TeacherMonitorPage
