/**
 * Assessment 状态页
 */
import React, { useEffect, useState } from 'react'
import { Table, Tag, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { listAssessments } from '@/api/assessment'
import { ExternalAssessmentListItem } from '@/types/assessment'

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
    {
        assessment_id: 'assess-003',
        provider_id: 'provider-03',
        assessment_type: 'insurance',
        status: 'revoked',
        report_time: '2026-01-15T13:20:00Z',
        ingest_time: '2026-01-15T13:22:00Z',
    },
]

const statusColor: Record<string, string> = {
    active: 'green',
    revoked: 'red',
    disputed: 'orange',
}

const formatTime = (value: string) => {
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    return date.toLocaleString()
}

const AssessmentStatusPage: React.FC = () => {
    const [loading, setLoading] = useState(false)
    const [assessments, setAssessments] = useState<ExternalAssessmentListItem[]>([])
    const [total, setTotal] = useState(0)
    const [page, setPage] = useState(1)
    const [pageSize, setPageSize] = useState(20)
    const [usingMock, setUsingMock] = useState(false)

    const fetchAssessments = async () => {
        setLoading(true)
        try {
            const response = await listAssessments({ page, size: pageSize })
            setAssessments(response.items)
            setTotal(response.total)
            setUsingMock(false)
        } catch (error) {
            message.warning('后端不可用，已使用本地 mock 数据')
            setAssessments(mockAssessments)
            setTotal(mockAssessments.length)
            setUsingMock(true)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchAssessments()
    }, [page, pageSize])

    const columns: ColumnsType<ExternalAssessmentListItem> = [
        {
            title: '评估ID',
            dataIndex: 'assessment_id',
            key: 'assessment_id',
            width: 200,
        },
        {
            title: '提供方',
            dataIndex: 'provider_id',
            key: 'provider_id',
            width: 160,
        },
        {
            title: '类型',
            dataIndex: 'assessment_type',
            key: 'assessment_type',
            width: 140,
        },
        {
            title: '状态',
            dataIndex: 'status',
            key: 'status',
            width: 140,
            render: (value: string) => <Tag color={statusColor[value] || 'default'}>{value}</Tag>,
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
        <div style={{ padding: '24px' }}>
            <div style={{ marginBottom: 16 }}>
                <h2 style={{ marginBottom: 4 }}>外部评估状态</h2>
                <div style={{ color: usingMock ? '#fa8c16' : '#8c8c8c' }}>
                    {usingMock ? '当前使用本地 mock 数据' : '来自外部评估引用的状态'}
                </div>
            </div>

            <Table
                columns={columns}
                dataSource={assessments}
                rowKey="assessment_id"
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

export default AssessmentStatusPage
