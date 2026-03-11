import { Table } from 'antd'

import { Button } from '@/components/ui/button'
import { StatusBadge } from '@/components/common'
import type { RobotProjectSummary } from '@/types/robotKnowledge'

interface RobotProjectTableProps {
  loading?: boolean
  projects: RobotProjectSummary[]
  selectedProjectId?: string | null
  onSelectProject?: (projectId: string) => void
}

function statusTone(status: string) {
  if (status === 'ready') return 'success'
  if (status === 'failed') return 'error'
  if (status === 'ingesting') return 'warning'
  return 'active'
}

export function RobotProjectTable({
  loading = false,
  projects,
  selectedProjectId,
  onSelectProject,
}: RobotProjectTableProps) {
  return (
    <Table
      columns={[
        {
          title: '品牌',
          dataIndex: 'brand',
          key: 'brand',
        },
        {
          title: '型号',
          dataIndex: 'model',
          key: 'model',
        },
        {
          title: '版本',
          dataIndex: 'version',
          key: 'version',
          render: (value: string | null | undefined) => value || '-',
        },
        {
          title: '状态',
          dataIndex: 'status',
          key: 'status',
          render: (value: string) => <StatusBadge label={value} status={statusTone(value)} />,
        },
        {
          title: '文件 / 分片',
          key: 'counts',
          render: (_: unknown, record: RobotProjectSummary) => (
            <span className="text-xs text-text-muted">
              {(record.ingest_summary?.files_total ?? 0).toString()} / {(record.ingest_summary?.chunks_total ?? 0).toString()}
            </span>
          ),
        },
        {
          title: '操作',
          key: 'actions',
          width: 140,
          render: (_: unknown, record: RobotProjectSummary) =>
            onSelectProject ? (
              <Button
                size="sm"
                type="button"
                variant={selectedProjectId === record.project_id ? 'secondary' : 'outline'}
                onClick={() => onSelectProject(record.project_id)}
              >
                {selectedProjectId === record.project_id ? '已选择' : '选择'}
              </Button>
            ) : null,
        },
      ]}
      dataSource={projects}
      loading={loading}
      pagination={{ pageSize: 6 }}
      rowKey="project_id"
    />
  )
}
