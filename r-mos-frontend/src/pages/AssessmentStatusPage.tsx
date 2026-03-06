import { useEffect, useState } from 'react'
import { Empty, Table, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'

import { listAssessments } from '@/api/assessment'
import { PageHeader, SectionCard, StatusBadge } from '@/components/common'
import type { ExternalAssessmentListItem } from '@/types/assessment'

const mockAssessments: ExternalAssessmentListItem[] = [
  {
    assessment_id: 'assess-001',
    provider_id: 'provider-01',
    assessment_type: 'diagnosis',
    status: 'active',
    report_time: '2026-01-16T10:00:00Z',
    ingest_time: '2026-01-16T10:01:00Z',
  },
  {
    assessment_id: 'assess-002',
    provider_id: 'provider-02',
    assessment_type: 'phm',
    status: 'disputed',
    report_time: '2026-01-16T09:40:00Z',
    ingest_time: '2026-01-16T09:42:00Z',
  },
]

function formatTime(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN')
}

function getStatusTone(status: string) {
  if (status === 'active') return 'success'
  if (status === 'disputed') return 'warning'
  if (status === 'revoked') return 'error'
  return 'idle'
}

const AssessmentStatusPage = () => {
  const [loading, setLoading] = useState(false)
  const [assessments, setAssessments] = useState<ExternalAssessmentListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [usingMock, setUsingMock] = useState(false)

  useEffect(() => {
    const fetchAssessments = async () => {
      setLoading(true)
      try {
        const response = await listAssessments({ page, size: pageSize })
        setAssessments(response.items)
        setTotal(response.total)
        setUsingMock(false)
      } catch {
        message.warning('后端不可用，已降级到本地 mock 数据')
        setAssessments(mockAssessments)
        setTotal(mockAssessments.length)
        setUsingMock(true)
      } finally {
        setLoading(false)
      }
    }

    void fetchAssessments()
  }, [page, pageSize])

  const columns: ColumnsType<ExternalAssessmentListItem> = [
    {
      title: '评估 ID',
      dataIndex: 'assessment_id',
      key: 'assessment_id',
      width: 200,
      render: (value: string) => <span className="font-mono text-xs text-text-secondary">{value}</span>,
    },
    {
      title: '提供方',
      dataIndex: 'provider_id',
      key: 'provider_id',
    },
    {
      title: '类型',
      dataIndex: 'assessment_type',
      key: 'assessment_type',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 140,
      render: (value: string) => <StatusBadge label={value} status={getStatusTone(value)} />,
    },
    {
      title: '报告时间',
      dataIndex: 'report_time',
      key: 'report_time',
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
        title="外部评估状态"
        subtitle={usingMock ? '当前使用本地 mock 数据' : '来自外部评估引用的状态'}
        breadcrumb={['通用', '评估状态']}
      />

      <SectionCard title="评估列表">
        {assessments.length === 0 && !loading ? (
          <Empty description="暂无评估记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <Table
            columns={columns}
            dataSource={assessments}
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
            rowKey="assessment_id"
          />
        )}
      </SectionCard>
    </div>
  )
}

export default AssessmentStatusPage
