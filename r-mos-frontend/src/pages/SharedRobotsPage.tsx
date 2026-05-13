import { Search, Link2, Link2Off, Bot, Loader2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Empty, message } from 'antd'

import { bindSharedRobot, listSharedRobots, unbindSharedRobot } from '@/api/robots'
import { PageHeader, SectionCard, StatusBadge } from '@/components/common'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { SharedRobotModel } from '@/types/robotModel'

const SharedRobotsPage = () => {
  const [robots, setRobots] = useState<SharedRobotModel[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [bindingId, setBindingId] = useState<number | null>(null)

  const fetchSharedRobots = useCallback(async (query?: string) => {
    setLoading(true)
    try {
      const result = await listSharedRobots(query || undefined)
      setRobots(result.items)
    } catch {
      message.error('加载共享库失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetchSharedRobots()
  }, [fetchSharedRobots])

  const handleSearch = () => {
    void fetchSharedRobots(search)
  }

  const handleBind = async (robotId: number) => {
    setBindingId(robotId)
    try {
      await bindSharedRobot(robotId)
      message.success('引用成功，已添加到你的机器人列表')
      setRobots((prev) =>
        prev.map((r) => (r.id === robotId ? { ...r, is_bound: true } : r)),
      )
    } catch {
      message.error('引用失败')
    } finally {
      setBindingId(null)
    }
  }

  const handleUnbind = async (robotId: number) => {
    setBindingId(robotId)
    try {
      await unbindSharedRobot(robotId)
      message.success('已取消引用')
      setRobots((prev) =>
        prev.map((r) => (r.id === robotId ? { ...r, is_bound: false } : r)),
      )
    } catch {
      message.error('取消引用失败')
    } finally {
      setBindingId(null)
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="共享机器人库"
        subtitle="浏览其他教师共享的机器人，一键引用到自己名下"
        breadcrumb={['通用', '共享库']}
      />

      <SectionCard title="搜索">
        <div className="flex gap-3">
          <Input
            className="max-w-[320px]"
            placeholder="搜索品牌或型号..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
          <Button size="sm" type="button" onClick={handleSearch}>
            <Search className="mr-1 h-4 w-4" />
            搜索
          </Button>
        </div>
      </SectionCard>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-text-muted" />
        </div>
      ) : robots.length === 0 ? (
        <Empty description="暂无共享机器人" />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {robots.map((robot) => (
            <div
              key={robot.id}
              className="flex flex-col rounded-lg border border-border-subtle bg-bg-surface p-4 transition-shadow hover:shadow-md"
            >
              <div className="mb-3 flex items-start justify-between">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-muted">
                  <Bot className="h-5 w-5 text-primary" />
                </div>
                <StatusBadge label="已共享" status="active" />
              </div>

              <h3 className="text-sm font-semibold text-text-primary">{robot.model_name}</h3>
              <p className="mt-0.5 text-xs text-text-muted">
                {robot.brand} · v{robot.version}
              </p>

              {robot.description ? (
                <p className="mt-2 line-clamp-2 text-xs text-text-secondary">
                  {robot.description}
                </p>
              ) : null}

              <div className="mt-auto pt-4">
                {robot.is_bound ? (
                  <Button
                    size="sm"
                    variant="outline"
                    className="w-full"
                    disabled={bindingId === robot.id}
                    onClick={() => void handleUnbind(robot.id)}
                  >
                    <Link2Off className="mr-1 h-3.5 w-3.5" />
                    {bindingId === robot.id ? '处理中...' : '取消引用'}
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    className="w-full"
                    disabled={bindingId === robot.id}
                    onClick={() => void handleBind(robot.id)}
                  >
                    <Link2 className="mr-1 h-3.5 w-3.5" />
                    {bindingId === robot.id ? '处理中...' : '引用到我的列表'}
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default SharedRobotsPage
