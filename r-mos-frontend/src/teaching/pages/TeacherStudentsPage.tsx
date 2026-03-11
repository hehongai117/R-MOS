import { useCallback, useEffect, useMemo, useState } from 'react'
import { Spin } from 'antd'
import { BarChart3, Flame, History, Users } from 'lucide-react'

import {
  getStudentProfile,
  getWeakSteps,
  getTrainingSessions,
  type SkillProfileResponse,
  type WeakStepResponse,
  type SessionResponse,
} from '@/api/training'
import { listClasses, listEnrollments, listAssignments, listAssignmentAttempts } from '@/api/teaching'
import type { TeachingClass, Assignment, Enrollment } from '@/types/teaching'
import { DataCard, EmptyState, PageHeader, SectionCard } from '@/components/common'
import { SkillRadarChart } from '@/components/training/SkillRadarChart'
import { WeakStepHeatmap } from '@/components/training/WeakStepHeatmap'
import { TrainingTimeline } from '@/components/training/TrainingTimeline'
import { Progress } from '@/components/ui/progress'

/* ── helpers ── */

const STEP_NAME_MAP: Record<string, string> = {
  prepare_station: '准备工位',
  motor_cover_remove: '拆解电机盖',
  align_reducer: '校准减速器',
  final_check: '最终复核',
}

function formatDateTime(value?: string | null) {
  if (!value) return '暂无'
  return new Date(value).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatHours(seconds?: number | null) {
  if (!seconds) return '0h'
  return `${(seconds / 3600).toFixed(1)}h`
}

/* ── types ── */

interface StudentSummary {
  studentId: number
  attemptCount: number
  bestScore: number | null
  latestStatus: string
}

/* ── main ── */

function TeacherStudentsPage() {
  /* class & student list loading */
  const [classes, setClasses] = useState<TeachingClass[]>([])
  const [selectedClassId, setSelectedClassId] = useState<number | null>(null)
  const [students, setStudents] = useState<StudentSummary[]>([])
  const [listLoading, setListLoading] = useState(false)

  /* selected student detail */
  const [selectedStudentId, setSelectedStudentId] = useState<number | null>(null)
  const [profile, setProfile] = useState<SkillProfileResponse | null>(null)
  const [weakSteps, setWeakSteps] = useState<WeakStepResponse[]>([])
  const [sessions, setSessions] = useState<SessionResponse[]>([])
  const [detailLoading, setDetailLoading] = useState(false)

  /* load classes on mount */
  useEffect(() => {
    let alive = true
    listClasses()
      .then((data) => {
        if (alive) {
          setClasses(data)
          if (data.length > 0) setSelectedClassId(data[0].id)
        }
      })
      .catch(() => { })
    return () => { alive = false }
  }, [])

  /* when class changes, gather unique student IDs from assignments' attempts */
  useEffect(() => {
    if (selectedClassId === null) return
    const activeClassId = selectedClassId
    let alive = true
    setListLoading(true)
    setStudents([])
    setSelectedStudentId(null)

    async function loadStudents() {
      try {
        const [enrollments, assignments]: [Enrollment[], Assignment[]] = await Promise.all([
          listEnrollments(activeClassId),
          listAssignments(activeClassId),
        ])
        const studentMap = new Map<number, StudentSummary>()

        for (const enrollment of enrollments) {
          if (enrollment.role !== 'student') {
            continue
          }

          studentMap.set(enrollment.studentId, {
            studentId: enrollment.studentId,
            attemptCount: 0,
            bestScore: null,
            latestStatus: '未开始',
          })
        }

        await Promise.all(
          assignments.map(async (assignment) => {
            try {
              const attempts = await listAssignmentAttempts(assignment.id)
              for (const attempt of attempts) {
                const existing = studentMap.get(attempt.studentId)
                if (!existing) {
                  studentMap.set(attempt.studentId, {
                    studentId: attempt.studentId,
                    attemptCount: 1,
                    bestScore: attempt.score ?? null,
                    latestStatus: attempt.status,
                  })
                } else {
                  existing.attemptCount += 1
                  if (attempt.score !== null && attempt.score !== undefined) {
                    existing.bestScore =
                      existing.bestScore !== null
                        ? Math.max(existing.bestScore, attempt.score)
                        : attempt.score
                  }
                  existing.latestStatus = attempt.status
                }
              }
            } catch {
              /* skip failed assignment */
            }
          })
        )

        if (alive) {
          setStudents(Array.from(studentMap.values()).sort((a, b) => a.studentId - b.studentId))
        }
      } catch {
        /* class load failed */
      } finally {
        if (alive) setListLoading(false)
      }
    }

    void loadStudents()
    return () => { alive = false }
  }, [selectedClassId])

  /* load student detail */
  const selectStudent = useCallback(async (studentId: number) => {
    setSelectedStudentId(studentId)
    setDetailLoading(true)
    setProfile(null)
    setWeakSteps([])
    setSessions([])

    try {
      const [profileRes, weakRes, sessionsRes] = await Promise.allSettled([
        getStudentProfile(studentId),
        getWeakSteps(studentId),
        getTrainingSessions(studentId),
      ])
      if (profileRes.status === 'fulfilled') setProfile(profileRes.value)
      if (weakRes.status === 'fulfilled') setWeakSteps(weakRes.value)
      if (sessionsRes.status === 'fulfilled') setSessions(sessionsRes.value)
    } finally {
      setDetailLoading(false)
    }
  }, [])

  /* computed data for components */
  const radarProfile = useMemo(
    () => ({
      safety: profile?.score_safety ?? 0,
      quality: profile?.score_procedure ?? 0,
      efficiency: profile?.score_efficiency ?? 0,
      diagnosis: profile?.score_precision ?? 0,
      collaboration: profile?.score_tools ?? 0,
    }),
    [profile]
  )

  const heatmapSteps = useMemo(
    () =>
      weakSteps.map((step) => ({
        stepId: step.step_id,
        stepName: STEP_NAME_MAP[step.step_id] ?? step.step_id,
        failCount: step.fail_count,
      })),
    [weakSteps]
  )

  const timelineRecords = useMemo(
    () =>
      sessions.map((s) => ({
        id: s.session_id,
        model: s.submit_type ? `${s.project_id} · ${s.submit_type}` : s.project_id,
        score: s.score ?? 0,
        trainedAt: formatDateTime(s.submitted_at ?? s.started_at),
      })),
    [sessions]
  )

  const dimensions = useMemo(
    () =>
      profile
        ? [
          { key: 'safety', label: '安全', value: profile.score_safety ?? 0 },
          { key: 'procedure', label: '流程质量', value: profile.score_procedure ?? 0 },
          { key: 'precision', label: '精度诊断', value: profile.score_precision ?? 0 },
          { key: 'efficiency', label: '效率', value: profile.score_efficiency ?? 0 },
          { key: 'tools', label: '工具熟练度', value: profile.score_tools ?? 0 },
        ]
        : [],
    [profile]
  )

  const selectedClass = classes.find((c) => c.id === selectedClassId)

  return (
    <div className="space-y-6">
      <PageHeader
        title="学员档案"
        subtitle={
          selectedClass
            ? `${selectedClass.name} · ${students.length} 名学员`
            : '选择班级查看学员技能画像'
        }
        breadcrumb={['教师端', '学员档案']}
        actions={
          classes.length > 0 ? (
            <select
              value={selectedClassId ?? ''}
              onChange={(e) => setSelectedClassId(Number(e.target.value))}
              className="rounded-md border border-border-default bg-bg-elevated px-3 py-2 text-sm text-text-primary"
            >
              {classes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} {c.term ? `· ${c.term}` : ''}
                </option>
              ))}
            </select>
          ) : null
        }
      />

      <div className="grid gap-4 xl:grid-cols-[320px_1fr]">
        {/* ── Left: Student list ── */}
        <SectionCard title="学员列表" description={`共 ${students.length} 人`}>
          {listLoading ? (
            <div className="flex min-h-[300px] items-center justify-center">
              <Spin />
            </div>
          ) : students.length === 0 ? (
            <EmptyState
              icon={Users}
              title="暂无学员数据"
              description="当前班级暂未录入训练记录。"
            />
          ) : (
            <div className="max-h-[calc(100vh-280px)] space-y-1 overflow-y-auto">
              {students.map((s) => (
                <button
                  key={s.studentId}
                  onClick={() => selectStudent(s.studentId)}
                  className={`flex w-full items-center justify-between rounded-md px-3 py-2.5 text-left transition-colors duration-base ${selectedStudentId === s.studentId
                      ? 'border-l-[3px] border-primary bg-primary-muted text-primary'
                      : 'hover:bg-bg-elevated text-text-secondary hover:text-text-primary'
                    }`}
                >
                  <div>
                    <div className="text-sm font-medium">学员 #{s.studentId}</div>
                    <div className="mt-0.5 text-xs text-text-muted">
                      {s.attemptCount} 次尝试 · {s.latestStatus}
                    </div>
                  </div>
                  {s.bestScore !== null ? (
                    <span className="font-mono text-sm text-primary">{s.bestScore}</span>
                  ) : (
                    <span className="text-xs text-text-muted">未评分</span>
                  )}
                </button>
              ))}
            </div>
          )}
        </SectionCard>

        {/* ── Right: Student detail ── */}
        <div className="space-y-4">
          {selectedStudentId === null ? (
            <EmptyState
              icon={BarChart3}
              title="选择学员"
              description="在左侧列表中点击学员查看技能画像、薄弱步骤和训练历史。"
            />
          ) : detailLoading ? (
            <div className="flex min-h-[400px] items-center justify-center rounded-xl border border-border-subtle bg-bg-surface">
              <Spin size="large" />
            </div>
          ) : (
            <>
              {/* Summary cards */}
              <div className="grid gap-4 xl:grid-cols-4">
                <DataCard
                  title="综合等级"
                  value={profile?.overall_level ?? '--'}
                  trendValue={profile ? `Lv.${profile.overall_level}` : '无数据'}
                  status="success"
                />
                <DataCard
                  title="训练次数"
                  value={profile?.total_sessions ?? '--'}
                  unit="次"
                  trendValue={profile ? '真实记录' : '无数据'}
                />
                <DataCard
                  title="累计时长"
                  value={profile ? formatHours(profile.total_duration) : '--'}
                  trendValue={profile ? `${profile.total_duration ?? 0}秒` : '无数据'}
                />
                <DataCard
                  title="上次训练"
                  value={profile?.last_trained_at ? formatDateTime(profile.last_trained_at).slice(0, 10) : '--'}
                  trendValue={profile ? formatDateTime(profile.last_trained_at) : '无数据'}
                />
              </div>

              {/* Skill radar + dimension detail */}
              <div className="grid gap-4 xl:grid-cols-5">
                <div className="xl:col-span-2">
                  {profile ? (
                    <SkillRadarChart profile={radarProfile} />
                  ) : (
                    <EmptyState
                      icon={BarChart3}
                      title="暂无技能画像"
                      description="该学员暂未产生技能评估数据。"
                    />
                  )}
                </div>
                <div className="xl:col-span-3">
                  <SectionCard title="技能详情" description="五维分布">
                    {profile ? (
                      <div className="grid gap-6 md:grid-cols-[1fr_200px]">
                        <div className="space-y-4">
                          {dimensions.map((item) => (
                            <div key={item.key} className="space-y-2">
                              <div className="flex items-center justify-between text-sm">
                                <span className="text-text-primary">{item.label}</span>
                                <span className="font-mono text-text-secondary">{item.value}</span>
                              </div>
                              <Progress value={item.value} />
                            </div>
                          ))}
                        </div>
                        <div className="rounded-xl border border-border-subtle bg-bg-elevated p-4">
                          <div className="text-xs uppercase tracking-[0.24em] text-text-muted">等级</div>
                          <div className="mt-4 font-mono text-4xl text-primary">Lv.{profile.overall_level}</div>
                          <div className="mt-4 space-y-2 text-xs leading-6 text-text-secondary">
                            <div>L1 {profile.cert_l1_passed ? '✅ 已通过' : '❌ 未通过'}</div>
                            <div>L2 {profile.cert_l2_passed ? '✅ 已通过' : '❌ 未通过'}</div>
                            <div>L3 {profile.cert_l3_eligible ? '🎯 可报名' : '🔒 暂不可'}</div>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <EmptyState
                        icon={Flame}
                        title="暂无技能详情"
                        description="该学员暂未产生技能详情数据。"
                      />
                    )}
                  </SectionCard>
                </div>
              </div>

              {/* Weak steps heatmap */}
              {weakSteps.length > 0 ? (
                <WeakStepHeatmap steps={heatmapSteps} />
              ) : (
                <EmptyState
                  icon={Flame}
                  title="暂无薄弱步骤"
                  description="该学员当前无薄弱步骤记录，表现稳定。"
                />
              )}

              {/* Training timeline */}
              {timelineRecords.length > 0 ? (
                <TrainingTimeline filterLabel="项目筛选" records={timelineRecords} />
              ) : (
                <EmptyState
                  icon={History}
                  title="暂无训练历史"
                  description="该学员尚未产生训练记录。"
                />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default TeacherStudentsPage
