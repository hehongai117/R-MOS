import { BarChart3, Flame, History, Sparkles, Lightbulb } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Spin } from 'antd'

import {
  getActiveTrainingSession,
  getStudentProfile,
  getTrainingSessions,
  getWeakSteps,
  type SessionResponse,
  type SkillProfileResponse,
  type WeakStepResponse,
} from '@/api/training'
import { apiClient } from '@/api/client'
import { DataCard, EmptyState, PageHeader, SectionCard } from '@/components/common'
import { SkillRadarChart } from '@/components/training/SkillRadarChart'
import { TrainingTimeline } from '@/components/training/TrainingTimeline'
import { WeakStepHeatmap } from '@/components/training/WeakStepHeatmap'
import { Progress } from '@/components/ui/progress'
import { useAuthStore } from '@/store/authStore'

const STEP_NAME_MAP: Record<string, string> = {
  prepare_station: '准备工位',
  motor_cover_remove: '拆解电机盖',
  align_reducer: '校准减速器',
  final_check: '最终复核',
}

function formatHours(seconds?: number | null) {
  if (!seconds) {
    return '0h'
  }

  return `${(seconds / 3600).toFixed(1)}h`
}

function formatDateTime(value?: string | null) {
  if (!value) {
    return '暂无'
  }
  return new Date(value).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function dimensionRows(profile: SkillProfileResponse) {
  return [
    { key: 'safety', label: '安全', value: profile.score_safety ?? 0 },
    { key: 'procedure', label: '流程质量', value: profile.score_procedure ?? 0 },
    { key: 'precision', label: '精度诊断', value: profile.score_precision ?? 0 },
    { key: 'efficiency', label: '效率', value: profile.score_efficiency ?? 0 },
    { key: 'tools', label: '工具熟练度', value: profile.score_tools ?? 0 },
  ]
}

function StudentSkillsPage() {
  const userId = useAuthStore((state) => state.user?.user_id)

  const [profile, setProfile] = useState<SkillProfileResponse | null>(null)
  const [weakSteps, setWeakSteps] = useState<WeakStepResponse[]>([])
  const [sessions, setSessions] = useState<SessionResponse[]>([])
  const [activeSession, setActiveSession] = useState<SessionResponse | null>(null)
  const [recommendations, setRecommendations] = useState<{ focus_areas?: string[]; suggested_sops?: string[]; summary?: string } | null>(null)
  const [recsLoading, setRecsLoading] = useState(false)

  const [profileLoading, setProfileLoading] = useState(false)
  const [weakStepsLoading, setWeakStepsLoading] = useState(false)
  const [sessionsLoading, setSessionsLoading] = useState(false)

  const [profileError, setProfileError] = useState<string | null>(null)
  const [weakStepsError, setWeakStepsError] = useState<string | null>(null)
  const [sessionsError, setSessionsError] = useState<string | null>(null)

  useEffect(() => {
    if (!userId) {
      return
    }

    const currentUserId = userId
    let alive = true

    async function loadProfile() {
      setProfileLoading(true)
      setProfileError(null)
      try {
        const response = await getStudentProfile(currentUserId)
        if (alive) {
          setProfile(response)
        }
      } catch (error) {
        if (alive) {
          setProfileError(error instanceof Error ? error.message : '技能画像加载失败')
        }
      } finally {
        if (alive) {
          setProfileLoading(false)
        }
      }
    }

    async function loadWeakSteps() {
      setWeakStepsLoading(true)
      setWeakStepsError(null)
      try {
        const response = await getWeakSteps(currentUserId)
        if (alive) {
          setWeakSteps(response)
        }
      } catch (error) {
        if (alive) {
          setWeakStepsError(error instanceof Error ? error.message : '薄弱步骤加载失败')
        }
      } finally {
        if (alive) {
          setWeakStepsLoading(false)
        }
      }
    }

    async function loadSessions() {
      setSessionsLoading(true)
      setSessionsError(null)
      try {
        const [history, active] = await Promise.allSettled([
          getTrainingSessions(currentUserId),
          getActiveTrainingSession(currentUserId),
        ])

        if (!alive) {
          return
        }

        if (history.status === 'fulfilled') {
          setSessions(history.value)
        } else {
          setSessionsError(history.reason instanceof Error ? history.reason.message : '训练历史加载失败')
        }

        if (active.status === 'fulfilled') {
          setActiveSession(active.value)
        } else {
          setActiveSession(null)
        }
      } finally {
        if (alive) {
          setSessionsLoading(false)
        }
      }
    }

    void loadProfile()
    void loadWeakSteps()
    void loadSessions()

    return () => {
      alive = false
    }
  }, [userId])

  // Load coach recommendations when profile is available
  useEffect(() => {
    if (!profile) return
    let alive = true
    setRecsLoading(true)
    apiClient.post('/api/v1/agent/coach/recommend', {
      student_id: userId,
      overall_level: profile.overall_level,
      weak_areas: weakSteps.map(s => s.step_id),
    }).then(res => {
      if (alive) setRecommendations(res.data)
    }).catch(() => {
      if (alive) setRecommendations(null)
    }).finally(() => {
      if (alive) setRecsLoading(false)
    })
    return () => { alive = false }
  }, [profile, weakSteps, userId])

  const dimensions = useMemo(() => (profile ? dimensionRows(profile) : []), [profile])

  const radarProfile = useMemo(
    () => ({
      safety: profile?.score_safety ?? 0,
      quality: profile?.score_procedure ?? 0,
      efficiency: profile?.score_efficiency ?? 0,
      diagnosis: profile?.score_precision ?? 0,
      collaboration: profile?.score_tools ?? 0,
    }),
    [profile],
  )

  const timelineRecords = useMemo(
    () =>
      sessions.map((session) => ({
        id: session.session_id,
        model: session.submit_type ? `${session.project_id} · ${session.submit_type}` : session.project_id,
        score: session.score ?? 0,
        trainedAt: formatDateTime(session.submitted_at ?? session.started_at),
      })),
    [sessions],
  )

  const heatmapSteps = useMemo(
    () =>
      weakSteps.map((step) => ({
        stepId: step.step_id,
        stepName: STEP_NAME_MAP[step.step_id] ?? step.step_id,
        failCount: step.fail_count,
      })),
    [weakSteps],
  )

  if (!userId) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="我的技能成长"
          subtitle="请先完成登录并加载用户画像。"
          breadcrumb={['学生端', '技能成长']}
        />
        <EmptyState
          description="当前登录态未提供 user_id，暂时无法加载训练画像。"
          icon={BarChart3}
          title="缺少用户上下文"
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="我的技能成长"
        subtitle={
          profile
            ? `技能等级 Lv.${profile.overall_level} · 累计训练 ${profile.total_sessions} 次`
            : '技能等级与训练历史基于真实训练接口加载'
        }
        breadcrumb={['学生端', '技能成长']}
      />

      {activeSession ? (
        <div className="glass-card flex items-center justify-between rounded-xl px-5 py-4">
          <div>
            <div className="text-sm text-text-primary">继续未完成训练</div>
            <div className="mt-1 text-xs text-text-muted">
              当前项目 {activeSession.project_id} · 第 {activeSession.current_step} 步 · 状态 {activeSession.status}
            </div>
          </div>
          <div className="font-mono text-xs text-primary">{activeSession.session_id.slice(0, 8)}</div>
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-4">
        <DataCard
          status="success"
          title="综合等级"
          trendValue={profile ? `Lv.${profile.overall_level}` : '等待画像'}
          value={profile?.overall_level ?? '--'}
        />
        <DataCard
          title="累计训练次数"
          trendValue={profile ? '真实训练记录' : '等待加载'}
          unit="次"
          value={profile?.total_sessions ?? '--'}
        />
        <DataCard
          title="累计训练时长"
          trendValue={profile ? `${profile.total_duration ?? 0} 秒` : '等待加载'}
          value={profile ? formatHours(profile.total_duration) : '--'}
        />
        <DataCard
          title="上次训练时间"
          trendValue={profile ? formatDateTime(profile.last_trained_at) : '等待加载'}
          value={profile?.last_trained_at ? formatDateTime(profile.last_trained_at).slice(0, 10) : '--'}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-5">
        <div className="xl:col-span-2">
          {profileLoading ? (
            <div className="flex min-h-[320px] items-center justify-center rounded-xl border border-border-subtle bg-bg-surface">
              <Spin />
            </div>
          ) : profile ? (
            <SkillRadarChart profile={radarProfile} />
          ) : (
            <EmptyState
              description={profileError ?? '暂无技能画像数据。'}
              icon={Sparkles}
              title="技能雷达暂不可用"
            />
          )}
        </div>
        <div className="xl:col-span-3">
          <SectionCard description="五维分布与升级条件" title="技能详情">
            {profileLoading ? (
              <div className="flex min-h-[320px] items-center justify-center">
                <Spin />
              </div>
            ) : profile ? (
              <div className="grid gap-6 md:grid-cols-[1fr_220px]">
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
                  <div className="text-xs uppercase tracking-[0.24em] text-text-muted">升级进度</div>
                  <div className="mt-4 font-mono text-5xl text-primary">Lv.{profile.overall_level}</div>
                  <div className="mt-4 space-y-2 text-xs leading-6 text-text-secondary">
                    <div>认证状态：L1 {profile.cert_l1_passed ? '已通过' : '未通过'}</div>
                    <div>L2 {profile.cert_l2_passed ? '已通过' : '未通过'}</div>
                    <div>L3 {profile.cert_l3_eligible ? '可报名' : '暂不可报名'}</div>
                    <div>建议优先补强薄弱步骤与工具熟练度，再挑战更高等级。</div>
                  </div>
                </div>
              </div>
            ) : (
              <EmptyState
                description={profileError ?? '技能详情暂不可用。'}
                icon={Flame}
                title="技能详情暂不可用"
              />
            )}
          </SectionCard>
        </div>
      </div>

      <div>
        {weakStepsLoading ? (
          <div className="flex min-h-[280px] items-center justify-center rounded-xl border border-border-subtle bg-bg-surface">
            <Spin />
          </div>
        ) : weakSteps.length > 0 ? (
          <WeakStepHeatmap steps={heatmapSteps} />
        ) : (
          <EmptyState
            description={weakStepsError ?? '暂无薄弱步骤，当前训练表现稳定。'}
            icon={Flame}
            title="暂无薄弱步骤"
          />
        )}
      </div>

      {/* AI Coach Recommendations */}
      <SectionCard title="AI 推荐训练" description="基于你的技能画像和薄弱环节，AI 教练推荐以下训练重点">
        {recsLoading ? (
          <div className="flex min-h-[120px] items-center justify-center"><Spin /></div>
        ) : recommendations ? (
          <div className="grid gap-4 md:grid-cols-3">
            {recommendations.summary && (
              <div className="md:col-span-3 rounded-lg border border-border-subtle bg-bg-elevated p-4">
                <div className="flex items-center gap-2 text-sm font-medium text-primary"><Lightbulb className="h-4 w-4" />综合建议</div>
                <p className="mt-2 text-sm text-text-secondary">{recommendations.summary}</p>
              </div>
            )}
            {recommendations.focus_areas && recommendations.focus_areas.length > 0 && (
              <div className="rounded-lg border border-border-subtle p-4">
                <div className="text-xs font-medium text-text-muted">重点提升领域</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {recommendations.focus_areas.map((area, i) => (
                    <span key={i} className="rounded-full bg-amber-500/10 px-3 py-1 text-xs text-amber-400">{area}</span>
                  ))}
                </div>
              </div>
            )}
            {recommendations.suggested_sops && recommendations.suggested_sops.length > 0 && (
              <div className="rounded-lg border border-border-subtle p-4">
                <div className="text-xs font-medium text-text-muted">推荐 SOP</div>
                <ul className="mt-2 space-y-1">
                  {recommendations.suggested_sops.map((sop, i) => (
                    <li key={i} className="text-sm text-text-secondary">• {sop}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <EmptyState description="暂无 AI 推荐，完成更多训练后将自动生成" icon={Lightbulb} title="等待推荐" />
        )}
      </SectionCard>

      <div>
        {sessionsLoading ? (
          <div className="flex min-h-[240px] items-center justify-center rounded-xl border border-border-subtle bg-bg-surface">
            <Spin />
          </div>
        ) : timelineRecords.length > 0 ? (
          <TrainingTimeline filterLabel="项目筛选" records={timelineRecords} />
        ) : (
          <EmptyState
            description={sessionsError ?? '尚未查询到训练历史。'}
            icon={History}
            title="训练历史暂不可用"
          />
        )}
      </div>
    </div>
  )
}

export default StudentSkillsPage
