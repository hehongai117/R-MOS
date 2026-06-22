import { useEffect, useMemo, useState } from 'react'
import { Badge, Empty, Input, Modal, Select, Table, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'

import {
  getApprovalDetail,
  grantApproval,
  listApprovals,
  rejectApproval,
  type ApprovalRecord,
} from '@/api/approvals'
import { PageHeader, SectionCard, StatusBadge } from '@/components/common'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { formatDateTime } from '@/utils/format'

type ApprovalStatus = 'pending' | 'approved' | 'rejected'

function getStatusTone(status: string) {
  if (status === 'pending') {
    return 'warning'
  }
  if (status === 'approved') {
    return 'success'
  }
  if (status === 'rejected') {
    return 'error'
  }
  return 'idle'
}

function ApprovalQueuePage() {
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<ApprovalStatus>('pending')
  const [keyword, setKeyword] = useState('')
  const [rows, setRows] = useState<ApprovalRecord[]>([])
  const [selectedRow, setSelectedRow] = useState<ApprovalRecord | null>(null)
  const [detailRow, setDetailRow] = useState<ApprovalRecord | null>(null)
  const [rejectOpen, setRejectOpen] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)
  const [reason, setReason] = useState('')

  const loadRows = async () => {
    setLoading(true)
    try {
      const response = await listApprovals({ status: activeTab, limit: 100, offset: 0 })
      setRows(response.items)
    } catch (error) {
      message.error('加载审批列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadRows()
  }, [activeTab])

  const filteredRows = useMemo(() => {
    const q = keyword.trim().toLowerCase()
    if (!q) {
      return rows
    }
    return rows.filter((row) => {
      const haystack = [
        row.id,
        row.trace_id,
        row.reason,
        row.created_by_user_id,
        row.decided_by_user_id,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
      return haystack.includes(q)
    })
  }, [keyword, rows])

  const handleApprove = async (row: ApprovalRecord) => {
    try {
      await grantApproval(row.id, 'frontend-approval-queue')
      message.success(`已批准审批 #${row.id}`)
      void loadRows()
    } catch {
      message.error('批准失败')
    }
  }

  const handleReject = async () => {
    if (!selectedRow) {
      return
    }
    try {
      await rejectApproval(selectedRow.id, reason || 'frontend-approval-queue-reject')
      message.success(`已拒绝审批 #${selectedRow.id}`)
      setRejectOpen(false)
      setReason('')
      setSelectedRow(null)
      void loadRows()
    } catch {
      message.error('拒绝失败')
    }
  }

  const openDetail = async (row: ApprovalRecord) => {
    try {
      const detail = await getApprovalDetail(row.id)
      setDetailRow(detail)
      setDetailOpen(true)
    } catch {
      message.error('加载审批详情失败')
    }
  }

  const columns: ColumnsType<ApprovalRecord> = [
    {
      title: '审批 ID',
      dataIndex: 'id',
      key: 'id',
      width: 120,
      render: (value: number) => <span className="font-mono text-text-primary">#{value}</span>,
    },
    {
      title: 'Trace',
      dataIndex: 'trace_id',
      key: 'trace_id',
      render: (value: string | null | undefined) => (
        <span className="font-mono text-xs text-text-secondary">{value ?? '--'}</span>
      ),
    },
    {
      title: '命令 / Tool',
      key: 'command',
      render: (_: unknown, row) => (
        <div className="space-y-1">
          <div className="text-sm text-text-primary">command #{row.command_id ?? '--'}</div>
          <div className="font-mono text-xs text-text-muted">tool #{row.tool_call_id ?? '--'}</div>
        </div>
      ),
    },
    {
      title: '申请人',
      dataIndex: 'created_by_user_id',
      key: 'created_by_user_id',
      render: (value: string | null | undefined) => value ?? '--',
    },
    {
      title: '原因',
      dataIndex: 'reason',
      key: 'reason',
      render: (value: string | null | undefined) => (
        <div className="max-w-[320px] text-sm text-text-secondary">{value ?? '未填写原因'}</div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (value: string) => <StatusBadge label={value} status={getStatusTone(value)} />,
    },
    {
      title: '时间',
      key: 'created_at',
      width: 160,
      render: (_: unknown, row) => (
        <div className="text-xs text-text-muted">
          <div>创建 {formatDateTime(row.created_at)}</div>
          <div>处理 {formatDateTime(row.decided_at)}</div>
        </div>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 220,
      render: (_: unknown, row) => (
        <div className="flex gap-2">
          <Button size="sm" type="button" variant="secondary" onClick={() => void openDetail(row)}>
            详情
          </Button>
          {row.status === 'pending' ? (
            <>
              <Button size="sm" type="button" onClick={() => void handleApprove(row)}>
                批准
              </Button>
              <Button
                size="sm"
                type="button"
                variant="outline"
                onClick={() => {
                  setSelectedRow(row)
                  setRejectOpen(true)
                }}
              >
                拒绝
              </Button>
            </>
          ) : null}
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="审批队列"
        subtitle="统一切换到 /ai/approvals 真实路由；支持待审批、已批准、已拒绝三类视图"
        breadcrumb={['管理员', '审批队列']}
      />

      <SectionCard title="筛选与状态">
        <div className="flex flex-wrap items-center gap-3">
          <Select
            className="min-w-[180px]"
            options={[
              { value: 'pending', label: '待审批' },
              { value: 'approved', label: '已批准' },
              { value: 'rejected', label: '已拒绝' },
            ]}
            value={activeTab}
            onChange={(value) => setActiveTab(value)}
          />
          <Input
            className="max-w-[320px]"
            placeholder="按 trace / reason / user 搜索"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
          />
          <Button size="sm" type="button" variant="secondary" onClick={() => void loadRows()}>
            刷新
          </Button>
          <Badge count={filteredRows.length} />
        </div>
      </SectionCard>

      <SectionCard title="审批列表">
        {filteredRows.length === 0 && !loading ? (
          <Empty description="当前筛选条件下没有审批记录" />
        ) : (
          <Table
            columns={columns}
            dataSource={filteredRows}
            loading={loading}
            pagination={{ pageSize: 10 }}
            rowKey="id"
          />
        )}
      </SectionCard>

      <Modal
        footer={null}
        open={detailOpen}
        title={detailRow ? `审批详情 #${detailRow.id}` : '审批详情'}
        onCancel={() => setDetailOpen(false)}
      >
        {detailRow ? (
          <div className="space-y-3 text-sm">
            <div className="rounded-lg border border-border-subtle bg-bg-elevated p-3">
              <div className="text-xs uppercase tracking-[0.2em] text-text-muted">trace</div>
              <div className="mt-2 font-mono text-text-primary">{detailRow.trace_id ?? '--'}</div>
            </div>
            <div className="rounded-lg border border-border-subtle bg-bg-elevated p-3">
              <div className="text-xs uppercase tracking-[0.2em] text-text-muted">reason</div>
              <div className="mt-2 text-text-primary">{detailRow.reason ?? '未填写原因'}</div>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-border-subtle bg-bg-elevated p-3">
                <div className="text-xs uppercase tracking-[0.2em] text-text-muted">created by</div>
                <div className="mt-2 text-text-primary">{detailRow.created_by_user_id ?? '--'}</div>
              </div>
              <div className="rounded-lg border border-border-subtle bg-bg-elevated p-3">
                <div className="text-xs uppercase tracking-[0.2em] text-text-muted">decided by</div>
                <div className="mt-2 text-text-primary">{detailRow.decided_by_user_id ?? '--'}</div>
              </div>
            </div>
          </div>
        ) : null}
      </Modal>

      <Modal
        okButtonProps={{ danger: true }}
        okText="确认拒绝"
        open={rejectOpen}
        title={selectedRow ? `拒绝审批 #${selectedRow.id}` : '拒绝审批'}
        onCancel={() => {
          setRejectOpen(false)
          setReason('')
          setSelectedRow(null)
        }}
        onOk={() => void handleReject()}
      >
        <div className="space-y-3">
          <div className="text-sm text-text-secondary">
            拒绝原因会提交到 `/ai/approvals/{`{id}`}/reject` 并写入审批记录。
          </div>
          <Textarea
            placeholder="请输入拒绝原因"
            rows={4}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        </div>
      </Modal>
    </div>
  )
}

export default ApprovalQueuePage
