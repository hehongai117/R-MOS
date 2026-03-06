import { FileText } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Descriptions, Drawer, Empty, List, Table } from 'antd'
import type { ColumnsType } from 'antd/es/table'

import { getEvidenceBundle, listEvidenceBundles } from '@/api/evidence'
import { EmptyState, PageHeader, SectionCard, StatusBadge } from '@/components/common'
import { Button } from '@/components/ui/button'
import type { EvidenceBundle, EvidenceBundleListItem } from '@/types/evidence'

function formatTime(value?: string | null) {
  if (!value) return '-'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN')
}

const EvidencePage = () => {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [bundles, setBundles] = useState<EvidenceBundleListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [selectedBundle, setSelectedBundle] = useState<EvidenceBundle | null>(null)

  const fetchBundles = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await listEvidenceBundles({ page, size: pageSize })
      setBundles(response.items)
      setTotal(response.total)
    } catch {
      setBundles([])
      setTotal(0)
      setError('无法加载证据包列表，请检查后端服务是否正常运行。')
    } finally {
      setLoading(false)
    }
  }

  const handleViewBundle = async (bundleId: string) => {
    try {
      const detail = await getEvidenceBundle(bundleId)
      setSelectedBundle(detail)
      setDrawerOpen(true)
    } catch {
      setError('无法加载证据详情')
    }
  }

  useEffect(() => {
    void fetchBundles()
  }, [page, pageSize])

  const columns: ColumnsType<EvidenceBundleListItem> = [
    {
      title: 'Bundle ID',
      dataIndex: 'evidence_bundle_id',
      key: 'evidence_bundle_id',
      width: 220,
      render: (value: string) => <span className="font-mono text-xs text-text-secondary">{value}</span>,
    },
    {
      title: '类型',
      dataIndex: 'bundle_type',
      key: 'bundle_type',
      render: (value: string) => <StatusBadge label={value} status="pending" />,
    },
    {
      title: '观测开始',
      dataIndex: 'observed_time_start',
      key: 'observed_time_start',
      render: (value: string) => formatTime(value),
    },
    {
      title: '入库时间',
      dataIndex: 'ingest_time',
      key: 'ingest_time',
      render: (value: string) => formatTime(value),
    },
    {
      title: '封存',
      dataIndex: 'is_sealed',
      key: 'is_sealed',
      width: 120,
      render: (value: boolean) => <StatusBadge label={value ? '已封存' : '未封存'} status={value ? 'success' : 'warning'} />,
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: unknown, record: EvidenceBundleListItem) => (
        <Button size="sm" type="button" variant="secondary" onClick={() => void handleViewBundle(record.evidence_bundle_id)}>
          查看
        </Button>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="证据包"
        subtitle={error ?? '展示后端证据包列表与详情，不再使用 mock 数据兜底'}
        breadcrumb={['通用', '证据包']}
      />

      {error ? <EmptyState description={error} icon={FileText} title="证据包加载失败" /> : null}

      <SectionCard title="证据包列表">
        {bundles.length === 0 && !loading ? (
          <Empty description="暂无证据包数据" />
        ) : (
          <Table
            columns={columns}
            dataSource={bundles}
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
            rowKey="evidence_bundle_id"
          />
        )}
      </SectionCard>

      <Drawer open={drawerOpen} title="证据包详情" width={560} onClose={() => setDrawerOpen(false)}>
        {selectedBundle ? (
          <div className="space-y-4">
            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="Bundle ID">{selectedBundle.evidence_bundle_id}</Descriptions.Item>
              <Descriptions.Item label="类型">{selectedBundle.bundle_type}</Descriptions.Item>
              <Descriptions.Item label="Hash">{selectedBundle.bundle_hash}</Descriptions.Item>
              <Descriptions.Item label="封存状态">{selectedBundle.is_sealed ? '已封存' : '未封存'}</Descriptions.Item>
              <Descriptions.Item label="观测开始">{formatTime(selectedBundle.observed_time_start)}</Descriptions.Item>
              <Descriptions.Item label="观测结束">{formatTime(selectedBundle.observed_time_end)}</Descriptions.Item>
              <Descriptions.Item label="入库时间">{formatTime(selectedBundle.ingest_time)}</Descriptions.Item>
              <Descriptions.Item label="摘要">{selectedBundle.human_summary || '-'}</Descriptions.Item>
            </Descriptions>

            <SectionCard title="证据条目">
              <List
                dataSource={selectedBundle.items}
                renderItem={(item) => (
                  <List.Item>
                    <List.Item.Meta
                      description={
                        <div className="text-xs text-text-muted">
                          <div>URI: {item.content_uri}</div>
                          <div>观测时间: {formatTime(item.observed_time)}</div>
                        </div>
                      }
                      title={`${item.evidence_type} · ${item.evidence_id}`}
                    />
                  </List.Item>
                )}
              />
            </SectionCard>
          </div>
        ) : null}
      </Drawer>
    </div>
  )
}

export default EvidencePage
