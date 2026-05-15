import { Bot, CheckCircle, LoaderCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { listAvailableRobots, selectRobots, type RobotOption } from '@/api/onboarding'
import { useAuthStore } from '@/store/authStore'

function OnboardingRobotsPage() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)

  const [robots, setRobots] = useState<RobotOption[]>([])
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  useEffect(() => {
    listAvailableRobots()
      .then(setRobots)
      .catch(() => toast.error('加载机器人列表失败'))
      .finally(() => setLoading(false))
  }, [])

  const toggleRobot = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else if (next.size < 5) {
        next.add(id)
      } else {
        toast.warning('最多选择 5 台机器人')
      }
      return next
    })
  }

  const handleSubmit = async () => {
    if (selectedIds.size === 0) {
      toast.error('请至少选择 1 台机器人')
      return
    }
    setSubmitting(true)
    try {
      await selectRobots([...selectedIds])
      // 更新本地状态
      const store = useAuthStore.getState()
      if (store.user) {
        store.setUser({ ...store.user, onboarding_completed: true })
      }
      localStorage.setItem('rmos_onboarding_completed', 'true')
      setDone(true)
      toast.success('机器人选择完成！')
      setTimeout(() => navigate('/workbench/teaching'), 1500)
    } catch {
      toast.error('提交失败，请重试')
    } finally {
      setSubmitting(false)
    }
  }

  // 已完成 onboarding 的教师不应看到此页
  if (user?.onboarding_completed) {
    navigate('/workbench/teaching', { replace: true })
    return null
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-bg-base px-4">
      <div
        className="pointer-events-none absolute left-1/2 top-1/2 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-15"
        style={{
          background: 'radial-gradient(circle, var(--color-primary) 0%, transparent 70%)',
        }}
      />

      <div className="relative z-10 w-full max-w-[640px] overflow-hidden rounded-2xl border border-border-subtle bg-bg-surface/80 shadow-lg backdrop-blur-sm">
        <div className="p-10">
          <div className="mb-6 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary">
              <Bot className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="font-mono text-xl font-bold text-primary">R-MOS</p>
              <p className="text-xs text-text-muted">选择您要教学的机器人</p>
            </div>
          </div>

          {done ? (
            <div className="space-y-4 py-8 text-center">
              <CheckCircle className="mx-auto h-12 w-12 text-green-400" />
              <p className="text-lg font-semibold text-text-primary">设置完成</p>
              <p className="text-sm text-text-secondary">正在进入教学工作台...</p>
            </div>
          ) : loading ? (
            <div className="flex items-center justify-center py-12">
              <LoaderCircle className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : robots.length === 0 ? (
            <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/5 px-4 py-6 text-center text-sm text-yellow-400">
              暂无可用机器人，请联系管理员
            </div>
          ) : (
            <>
              <p className="mb-4 text-sm text-text-secondary">
                请选择您教学中使用的机器人型号（最多 5 台）：
              </p>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {robots.map((r) => (
                  <button
                    key={r.id}
                    type="button"
                    onClick={() => toggleRobot(r.id)}
                    className={`rounded-lg border p-4 text-left transition-colors ${
                      selectedIds.has(r.id)
                        ? 'border-primary bg-primary/10'
                        : 'border-border-subtle hover:border-text-muted'
                    }`}
                  >
                    <p className="font-medium text-text-primary">
                      {r.brand} {r.model_name}
                    </p>
                    {r.description && (
                      <p className="mt-1 text-xs text-text-muted line-clamp-2">{r.description}</p>
                    )}
                  </button>
                ))}
              </div>

              <div className="mt-6 flex items-center justify-between">
                <span className="text-sm text-text-muted">
                  已选 {selectedIds.size}/5
                </span>
                <Button onClick={handleSubmit} disabled={selectedIds.size === 0 || submitting}>
                  {submitting ? (
                    <>
                      <LoaderCircle className="h-4 w-4 animate-spin" />
                      提交中...
                    </>
                  ) : (
                    '确认选择，开始使用'
                  )}
                </Button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default OnboardingRobotsPage
