import { useEffect, useState } from 'react'
import { Empty, Table } from 'antd'
import type { ColumnsType } from 'antd/es/table'

import { listIncidents } from '@/api/incident'
import { PageHeader, SectionCard, StatusBadge } from '@/components/common'
import type { IncidentListItem } from '@/types/incident'

function formatTime(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN')
}

function severityTone(level: string) {
  if (level === 'critical') return 'error'
  if (level === 'warning') return 'warning'
  if (level === 'info') return 'active'
  return 'idle'
}

function statusTone(status: string) {
  if (status === 'open') return 'warning'
  if (status === 'closed') return 'success'
  return 'idle'
}

const IncidentListPage = () => {
  const [loading, setLoading] = useState(false)
  const [incidents, setIncidents] = useState<IncidentListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchIncidents = async () => {
      setLoading(true)
      setError(null)
      try {
        const response = await listIncidents({ page, size: pageSize })
        setIncidents(response.items)
        setTotal(response.total)
      } catch {
        setError('无法加载事件列表，请检查后端服务是否正常运行')
        setIncidents([])
        setTotal(0)
      } finally {
        setLoading(false)
      }
    }

    void fetchIncidents()
  }, [page, pageSize])

  const columns: ColumnsType<IncidentListItem> = [
    {
      title: '事件 ID',
      dataIndex: 'incident_id',
      key: 'incident_id',
      width: 180,
      render: (value: string) => <span className="font-mono text-xs text-text-secondary">{value}</span>,
    },
    {
      title: '机器人 ID',
      dataIndex: 'robot_id',
      key: 'robot_id',
      width: 140,
    },
    {
      title: '类型',
      dataIndex: 'incident_type',
      key: 'incident_type',
    },
    {
      title: '等级',
      dataIndex: 'incident_level',
      key: 'incident_level',
      width: 140,
      render: (value: string) => <StatusBadge label={value} status={severityTone(value)} />,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 140,
      render: (value: string) => <StatusBadge label={value} status={statusTone(value)} />,
    },
    {
      title: '事件开始时间',
      dataIndex: 'event_time_start',
      key: 'event_time_start',
      render: (value: string) => formatTime(value),
    },
    {
      title: '入库时间',
      dataIndex: 'ingest_time',
      key: 'ingest_time',
      render: (value: string) => formatTime(value),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="事件列表"
        subtitle={error ?? '展示系统内事件和严重等级，便于快速回溯'}
        breadcrumb={['通用', '事件列表']}
      />

      <SectionCard title="事件清单">
        {incidents.length === 0 && !loading ? (
          <Empty description={error ?? '暂无事件数据'} image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <Table
            columns={columns}
            dataSource={incidents}
            loading={loading}
            pagination={{
              current: page,
              pageSize,
              total,
              onChange: (nextPage, nextSize) => {
                setPage(nextPage)
                setPageSize(nextSize || 20)
              },
            }}
            rowKey="incident_id"
          />
        )}
      </SectionCard>
    </div>
  )
}

export default IncidentListPage
