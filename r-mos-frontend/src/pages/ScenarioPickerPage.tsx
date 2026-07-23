import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dumbbell, Sparkles, Play } from 'lucide-react'
import { fetchScenarios, type ScenarioItem } from '@/api/scenarios'
import { useRobotContextStore } from '@/store/robotContextStore'

type Difficulty = 'all' | 'beginner' | 'intermediate' | 'advanced'

const DIFFICULTY_LABEL: Record<string, string> = {
  beginner: '入门',
  intermediate: '进阶',
  advanced: '高级',
}

const DIFFICULTY_VARIANT: Record<string, 'default' | 'success' | 'destructive'> = {
  beginner: 'default',
  intermediate: 'success',
  advanced: 'destructive',
}

export default function ScenarioPickerPage() {
  const [difficulty, setDifficulty] = useState<Difficulty>('all')
  const [scenarios, setScenarios] = useState<ScenarioItem[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  const currentRobotId = useRobotContextStore((s) => s.currentRobotId)

  useEffect(() => {
    setLoading(true)
    fetchScenarios(difficulty, currentRobotId ?? undefined)
      .then((res) => setScenarios(res.items))
      .catch(() => setScenarios([]))
      .finally(() => setLoading(false))
  }, [difficulty, currentRobotId])

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Dumbbell className="h-6 w-6 text-primary" />
        <h1 className="text-2xl font-semibold text-text-primary">自主练习</h1>
      </div>

      <Card className="border-primary/20 bg-primary-muted/30">
        <CardContent className="flex items-center gap-3 py-4">
          <Sparkles className="h-5 w-5 text-primary" />
          <p className="text-sm text-text-secondary">
            选择一个故障场景开始练习，AI 助手会在练习过程中为你提供帮助。
          </p>
        </CardContent>
      </Card>

      <Tabs value={difficulty} onValueChange={(v) => setDifficulty(v as Difficulty)}>
        <TabsList>
          <TabsTrigger value="all">全部</TabsTrigger>
          <TabsTrigger value="beginner">入门</TabsTrigger>
          <TabsTrigger value="intermediate">进阶</TabsTrigger>
          <TabsTrigger value="advanced">高级</TabsTrigger>
        </TabsList>
      </Tabs>

      {loading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="py-6">
                <div className="h-5 w-32 rounded bg-bg-elevated" />
                <div className="mt-3 h-4 w-24 rounded bg-bg-elevated" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : scenarios.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-sm text-text-muted">
              暂无可用的练习场景。教师配置故障场景后将显示在此处。
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {scenarios.map((scenario) => (
            <Card key={scenario.id} className="transition-all hover:border-primary/30 hover:shadow-sm">
              <CardContent className="space-y-3 py-5">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-text-primary">
                    {scenario.sop_title || scenario.fault_type}
                  </span>
                  <Badge variant={DIFFICULTY_VARIANT[scenario.difficulty]}>
                    {DIFFICULTY_LABEL[scenario.difficulty]}
                  </Badge>
                </div>
                <p className="text-xs text-text-muted">故障类型: {scenario.fault_type}</p>
                <Button
                  type="button"
                  size="sm"
                  className="w-full"
                  onClick={() => navigate(`/maintenance?sop=sop-db-${scenario.sop_id}`)}
                >
                  <Play className="mr-2 h-3 w-3" />
                  开始练习
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
