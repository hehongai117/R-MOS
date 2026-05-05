import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ClipboardList, Clock, CheckCircle, XCircle, Play } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { fetchStudentTasks, type StudentTaskItem } from '@/api/studentTasks'

type TaskFilter = 'all' | 'in_progress' | 'completed'

const STATUS_CONFIG = {
  in_progress: { label: '进行中', icon: Clock, variant: 'default' as const, color: 'text-yellow-600' },
  completed: { label: '已完成', icon: CheckCircle, variant: 'success' as const, color: 'text-green-600' },
  abandoned: { label: '已放弃', icon: XCircle, variant: 'destructive' as const, color: 'text-red-600' },
}

export default function MyTasksPage() {
  const [filter, setFilter] = useState<TaskFilter>('all')
  const [tasks, setTasks] = useState<StudentTaskItem[]>([])
  const [loading, setLoading] = useState(true)
  const user = useAuthStore((s) => s.user)
  const navigate = useNavigate()

  useEffect(() => {
    if (!user?.user_id) return
    setLoading(true)
    const status = filter === 'all' ? undefined : filter
    fetchStudentTasks(user.user_id, status)
      .then((res) => setTasks(res.items))
      .catch(() => setTasks([]))
      .finally(() => setLoading(false))
  }, [user?.user_id, filter])

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <ClipboardList className="h-6 w-6 text-primary" />
        <h1 className="text-2xl font-semibold text-text-primary">我的任务</h1>
      </div>

      <Tabs value={filter} onValueChange={(v) => setFilter(v as TaskFilter)}>
        <TabsList>
          <TabsTrigger value="all">全部</TabsTrigger>
          <TabsTrigger value="in_progress">进行中</TabsTrigger>
          <TabsTrigger value="completed">已完成</TabsTrigger>
        </TabsList>
      </Tabs>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="py-4">
                <div className="h-5 w-48 rounded bg-bg-elevated" />
                <div className="mt-2 h-4 w-32 rounded bg-bg-elevated" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : tasks.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-sm text-text-muted">暂无任务记录，开始一次练习吧！</p>
            <Button className="mt-4" onClick={() => navigate('/scenarios')}>
              <Play className="mr-2 h-4 w-4" />
              去练习
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {tasks.map((task) => {
            const config = STATUS_CONFIG[task.status]
            const StatusIcon = config.icon
            return (
              <Card key={task.id} className="transition-colors hover:border-primary/30">
                <CardContent className="flex items-center justify-between py-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-text-primary">{task.task_name}</span>
                      <Badge variant={config.variant}>{config.label}</Badge>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-text-muted">
                      {task.sop_name && <span>SOP: {task.sop_name}</span>}
                      {task.fault_type && <span>故障: {task.fault_type}</span>}
                      <span>{new Date(task.started_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <StatusIcon className={`h-5 w-5 ${config.color}`} />
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
