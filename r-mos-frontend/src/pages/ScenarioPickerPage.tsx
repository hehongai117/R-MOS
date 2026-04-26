import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Dumbbell, Sparkles } from 'lucide-react'

type Difficulty = 'all' | 'beginner' | 'intermediate' | 'advanced'

export default function ScenarioPickerPage() {
  const [difficulty, setDifficulty] = useState<Difficulty>('all')

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
            AI 将根据你的技能画像推荐适合当前水平的练习场景。
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

      <Card>
        <CardHeader>
          <CardTitle className="text-base text-text-secondary">
            暂无可用的练习场景
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-text-muted">
            故障场景库将在后续版本中填充。届时你可以选择不同类型和难度的故障进行练习。
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
