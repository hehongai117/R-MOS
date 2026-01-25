/**
 * 事件列表页（Incident）
 */
import React, { useEffect, useState } from 'react'
import { Table, Tag, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { listIncidents } from '@/api/incident'
import { IncidentListItem } from '@/types/incident'

const mockIncidents: IncidentListItem[] = [
    {
        incident_id: 'inc-001',
        robot_id: 'robot-01',
        incident_type: 'maintenance',
        incident_level: 'warning',
        status: 'open',
        event_time_start: '2026-01-16T09:30:00Z',
        ingest_time: '2026-01-16T09:31:05Z',
    },
    {
        incident_id: 'inc-002',
        robot_id: 'robot-02',
        incident_type: 'connectivity',
        incident_level: 'critical',
        status: 'open',
        event_time_start: '2026-01-16T10:12:00Z',
        ingest_time: '2026-01-16T10:12:30Z',
    },
    {
        incident_id: 'inc-003',
        robot_id: 'robot-03',
        incident_type: 'operational',
        incident_level: 'info',
        status: 'closed',
        event_time_start: '2026-01-15T16:08:00Z',
        ingest_time: '2026-01-15T16:08:40Z',
    },
]

const statusColor: Record<string, string> = {
    open: 'blue',
    closed: 'green',
    archived: 'default',
}

const levelColor: Record<string, string> = {
    info: 'default',
    warning: 'orange',
    critical: 'red',
}

const formatTime = (value: string) => {
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    return date.toLocaleString()
}

const IncidentListPage: React.FC = () => {
    const [loading, setLoading] = useState(false)
    const [incidents, setIncidents] = useState<IncidentListItem[]>([])
    const [total, setTotal] = useState(0)
    const [page, setPage] = useState(1)
    const [pageSize, setPageSize] = useState(20)
    const [usingMock, setUsingMock] = useState(false)

    const fetchIncidents = async () => {
        setLoading(true)
        try {
            const response = await listIncidents({ page, size: pageSize })
            setIncidents(response.items)
            setTotal(response.total)
            setUsingMock(false)
        } catch (error) {
            message.warning('后端不可用，已使用本地 mock 数据')
            setIncidents(mockIncidents)
            setTotal(mockIncidents.length)
            setUsingMock(true)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchIncidents()
    }, [page, pageSize])

    const columns: ColumnsType<IncidentListItem> = [
        {
            title: '事件ID',
            dataIndex: 'incident_id',
            key: 'incident_id',
            width: 180,
        },
        {
            title: '机器人ID',
            dataIndex: 'robot_id',
            key: 'robot_id',
            width: 140,
        },
        {
            title: '类型',
            dataIndex: 'incident_type',
            key: 'incident_type',
            width: 140,
        },
        {
            title: '等级',
            dataIndex: 'incident_level',
            key: 'incident_level',
            width: 120,
            render: (value: string) => <Tag color={levelColor[value] || 'default'}>{value}</Tag>,
        },
        {
            title: '状态',
            dataIndex: 'status',
            key: 'status',
            width: 120,
            render: (value: string) => <Tag color={statusColor[value] || 'default'}>{value}</Tag>,
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
        <div style={{ padding: '24px' }}>
            <div style={{ marginBottom: 16 }}>
                <h2 style={{ marginBottom: 4 }}>事件列表</h2>
                <div style={{ color: usingMock ? '#fa8c16' : '#8c8c8c' }}>
                    {usingMock ? '当前使用本地 mock 数据' : '来自后端的事实事件记录'}
                </div>
            </div>

            <Table
                columns={columns}
                dataSource={incidents}
                rowKey="incident_id"
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
            />
        </div>
    )
}

export default IncidentListPage
