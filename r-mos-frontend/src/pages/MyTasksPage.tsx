import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ClipboardList } from 'lucide-react'

type TaskFilter = 'pending' | 'in_progress' | 'completed'

export default function MyTasksPage() {
  const [filter, setFilter] = useState<TaskFilter>('pending')

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <ClipboardList className="h-6 w-6 text-primary" />
        <h1 className="text-2xl font-semibold text-text-primary">我的任务</h1>
      </div>

      <Tabs value={filter} onValueChange={(v) => setFilter(v as TaskFilter)}>
        <TabsList>
          <TabsTrigger value="pending">待完成</TabsTrigger>
          <TabsTrigger value="in_progress">进行中</TabsTrigger>
          <TabsTrigger value="completed">已完成</TabsTrigger>
        </TabsList>
      </Tabs>

      <Card>
        <CardHeader>
          <CardTitle className="text-base text-text-secondary">
            {filter === 'pending' && '暂无待完成的任务'}
            {filter === 'in_progress' && '暂无进行中的任务'}
            {filter === 'completed' && '暂无已完成的任务'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-text-muted">
            教师布置的练习任务和自主练习记录将显示在这里。
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
