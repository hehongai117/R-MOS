import { FileText } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Table } from 'antd'

import { listTasks } from '@/api/task'
import { EmptyState, PageHeader, SectionCard, StatusBadge } from '@/components/common'
import { Button } from '@/components/ui/button'
import { TaskStatus, type Task } from '@/types/task'
import { formatDateTime } from '@/utils/format'

const PAGE_SIZE = 10

/** TaskStatus 与 StatusBadge 支持的状态值不是同一套，这里做一次映射。 */
const STATUS_BADGE_MAP: Record<TaskStatus, 'active' | 'idle' | 'error' | 'warning' | 'success' | 'pending'> = {
  [TaskStatus.PENDING]: 'pending',
  [TaskStatus.IN_PROGRESS]: 'active',
  [TaskStatus.PAUSED]: 'idle',
  [TaskStatus.COMPLETED]: 'success',
  [TaskStatus.FAILED]: 'error',
  [TaskStatus.TIMEOUT]: 'warning',
}

/**
 * 维保报告列表页。
 *
 * 此前菜单「维保报告」指向 /reports，但该路由挂的是依赖 taskId 的详情页，
 * 直接访问必然报「缺少 taskId」。这里补上真正的列表入口。
 */
const ReportListPage = () => {
  const navigate = useNavigate()
  const [tasks, setTasks] = useState<Task[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchTasks = useCallback(async (targetPage: number) => {
    try {
      setLoading(true)
      setError(null)
      const result = await listTasks({
        limit: PAGE_SIZE,
        offset: (targetPage - 1) * PAGE_SIZE,
      })
      setTasks(result.items)
      setTotal(result.total)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } } | null)
        ?.response?.data?.detail
      setError(detail || '获取任务列表失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetchTasks(page)
  }, [fetchTasks, page])

  const columns = [
    {
      title: '任务',
      dataIndex: 'title',
      key: 'title',
      render: (value: string) => <span className="text-text-primary">{value}</span>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (value: TaskStatus) => (
        <StatusBadge status={STATUS_BADGE_MAP[value] ?? 'idle'} />
      ),
    },
    {
      title: '得分',
      key: 'score',
      width: 120,
      render: (_: unknown, record: Task) =>
        record.final_score === null || record.final_score === undefined ? (
          <span className="text-text-muted">-</span>
        ) : (
          <span className="font-mono text-text-primary">{record.final_score}</span>
        ),
    },
    {
      title: '完成时间',
      dataIndex: 'completed_at',
      key: 'completed_at',
      width: 200,
      render: (value: string | null) => (value ? formatDateTime(value) : '-'),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: unknown, record: Task) => (
        <Button
          size="sm"
          type="button"
          variant="secondary"
          onClick={() => navigate(`/reports/${record.id}`)}
        >
          查看报告
        </Button>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={['记录', '维保报告']}
        subtitle="查看历史维保任务的执行结果与评分报告"
        title="维保报告"
      />

      <SectionCard title="任务列表">
        {error ? (
          <EmptyState description={error} icon={FileText} title="无法加载列表" />
        ) : (
          <Table
            columns={columns}
            dataSource={tasks}
            loading={loading}
            locale={{ emptyText: '暂无维保任务记录' }}
            pagination={{
              current: page,
              pageSize: PAGE_SIZE,
              total,
              onChange: setPage,
              showSizeChanger: false,
            }}
            rowKey="id"
          />
        )}
      </SectionCard>
    </div>
  )
}

export default ReportListPage
