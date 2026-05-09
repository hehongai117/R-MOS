import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { BarChart3, Bot, CheckCircle, Clock, Target } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { useRobotContextStore } from '@/store/robotContextStore'
import RobotCards from '@/components/RobotCards'
import { apiClient } from '@/api/client'

interface TaskStats {
  total: number
  pending_count: number
  in_progress_count: number
  completed_count: number
}

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user)
  const {
    availableRobots,
    currentRobotId,
    currentRobot,
    isLoading: robotsLoading,
    fetchAvailableRobots,
    setCurrentRobot,
  } = useRobotContextStore()

  const [stats, setStats] = useState<TaskStats | null>(null)
  const [statsLoading, setStatsLoading] = useState(true)

  // 加载可用机器人列表（仅学生角色）
  useEffect(() => {
    if (user?.user_id && user.role === 'student') {
      fetchAvailableRobots(user.user_id)
    }
  }, [user?.user_id, user?.role, fetchAvailableRobots])

  // 加载任务统计
  useEffect(() => {
    if (!user?.user_id) return
    apiClient
      .get('/student/tasks', { params: { student_id: user.user_id, limit: 1 } })
      .then((res) => setStats(res.data))
      .catch(() => setStats(null))
      .finally(() => setStatsLoading(false))
  }, [user?.user_id])

  const completionRate = stats && stats.total > 0
    ? Math.round((stats.completed_count / stats.total) * 100)
    : 0

  // 如果有多台机器人且未选中，优先显示机器人选择界面
  const showRobotPicker = user?.role === 'student' && availableRobots.length > 1 && !currentRobot

  return (
    <div className="space-y-6">
      {/* 多机器人时始终显示选择区域 */}
      {user?.role === 'student' && availableRobots.length > 1 && (
        <section className="space-y-3">
          <div className="flex items-center gap-3">
            <Bot className="h-6 w-6 text-primary" />
            <h1 className="text-2xl font-semibold text-text-primary">选择机器人</h1>
          </div>
          <RobotCards
            robots={availableRobots}
            selectedId={currentRobotId}
            onSelect={setCurrentRobot}
            loading={robotsLoading}
          />
        </section>
      )}

      {/* 未选中时不显示学习进度统计（多机器人模式） */}
      {!showRobotPicker && (
        <>
          <div className="flex items-center gap-3">
            <BarChart3 className="h-6 w-6 text-primary" />
            <h1 className="text-2xl font-semibold text-text-primary">学习进度</h1>
            {currentRobot && (
              <span className="text-sm text-text-secondary">
                — {currentRobot.brand} {currentRobot.model_name}
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-text-secondary">总任务数</CardTitle>
                <Target className="h-4 w-4 text-text-muted" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{statsLoading ? '—' : stats?.total ?? 0}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-text-secondary">进行中</CardTitle>
                <Clock className="h-4 w-4 text-yellow-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-yellow-600">
                  {statsLoading ? '—' : stats?.in_progress_count ?? 0}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-text-secondary">已完成</CardTitle>
                <CheckCircle className="h-4 w-4 text-green-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-600">
                  {statsLoading ? '—' : stats?.completed_count ?? 0}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-text-secondary">完成率</CardTitle>
                <BarChart3 className="h-4 w-4 text-primary" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-primary">{statsLoading ? '—' : `${completionRate}%`}</div>
                <Progress value={completionRate} className="mt-2" />
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">技能雷达</CardTitle>
            </CardHeader>
            <CardContent className="flex items-center justify-center py-8">
              <p className="text-sm text-text-muted">
                完成更多练习任务后，技能雷达图将在此显示你的五维能力分布。
              </p>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
