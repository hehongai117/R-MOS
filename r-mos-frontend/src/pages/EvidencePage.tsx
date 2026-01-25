/**
 * Evidence 视图页
 */
import React, { useEffect, useState } from 'react'
import { Button, Drawer, Descriptions, List, Table, Tag, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { listEvidenceBundles, getEvidenceBundle } from '@/api/evidence'
import { EvidenceBundle, EvidenceBundleListItem } from '@/types/evidence'

const mockBundles: EvidenceBundle[] = [
    {
        evidence_bundle_id: 'bundle-001',
        bundle_type: 'telemetry_snapshot',
        bundle_hash: '0f2c9b8c4e1a5f63c9c7d1e0f9a3c2b1a8d7e6f5c4b3a2918273645544332211',
        bundle_hash_algo: 'sha256',
        observed_time_start: '2026-01-16T08:30:00Z',
        observed_time_end: '2026-01-16T08:35:00Z',
        ingest_time: '2026-01-16T08:35:10Z',
        is_sealed: true,
        sealed_at: '2026-01-16T08:35:10Z',
        items: [
            {
                evidence_id: 'evi-001',
                evidence_type: 'telemetry',
                content_uri: 's3://rmos/evidence/telemetry-001.json',
                content_hash: 'ab12cd34ef56',
                content_hash_algo: 'sha256',
                content_mime_type: 'application/json',
                size_bytes: 20480,
                observed_time: '2026-01-16T08:32:00Z',
                ingest_time: '2026-01-16T08:35:10Z',
                human_summary: '关节数据采样快照',
                machine_code: 'telemetry.snapshot',
                machine_tags: ['joint', 'telemetry'],
            },
        ],
        human_summary: '维保前遥测快照',
        machine_tags: ['snapshot'],
    },
    {
        evidence_bundle_id: 'bundle-002',
        bundle_type: 'event_log',
        bundle_hash: '7f2c9b8c4e1a5f63c9c7d1e0f9a3c2b1a8d7e6f5c4b3a2918273645544332299',
        bundle_hash_algo: 'sha256',
        observed_time_start: '2026-01-16T09:10:00Z',
        observed_time_end: null,
        ingest_time: '2026-01-16T09:15:10Z',
        is_sealed: true,
        sealed_at: '2026-01-16T09:15:10Z',
        items: [
            {
                evidence_id: 'evi-002',
                evidence_type: 'log',
                content_uri: 's3://rmos/evidence/log-002.txt',
                content_hash: 'ff12cd34ef56',
                content_hash_algo: 'sha256',
                content_mime_type: 'text/plain',
                size_bytes: 1024,
                observed_time: '2026-01-16T09:12:00Z',
                ingest_time: '2026-01-16T09:15:10Z',
                human_summary: '控制器日志片段',
                machine_code: 'log.controller',
                machine_tags: ['log'],
            },
        ],
        human_summary: '维保期间事件日志',
        machine_tags: ['event'],
    },
]

const mockBundleMap = new Map<string, EvidenceBundle>(mockBundles.map((bundle) => [bundle.evidence_bundle_id, bundle]))

const formatTime = (value?: string | null) => {
    if (!value) return '-'
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    return date.toLocaleString()
}

const EvidencePage: React.FC = () => {
    const [loading, setLoading] = useState(false)
    const [bundles, setBundles] = useState<EvidenceBundleListItem[]>([])
    const [total, setTotal] = useState(0)
    const [page, setPage] = useState(1)
    const [pageSize, setPageSize] = useState(20)
    const [usingMock, setUsingMock] = useState(false)
    const [drawerOpen, setDrawerOpen] = useState(false)
    const [selectedBundle, setSelectedBundle] = useState<EvidenceBundle | null>(null)

    const fetchBundles = async () => {
        setLoading(true)
        try {
            const response = await listEvidenceBundles({ page, size: pageSize })
            setBundles(response.items)
            setTotal(response.total)
            setUsingMock(false)
        } catch (error) {
            message.warning('后端不可用，已使用本地 mock 数据')
            const listItems = mockBundles.map((bundle) => ({
                evidence_bundle_id: bundle.evidence_bundle_id,
                bundle_type: bundle.bundle_type,
                observed_time_start: bundle.observed_time_start,
                ingest_time: bundle.ingest_time,
                is_sealed: bundle.is_sealed,
            }))
            setBundles(listItems)
            setTotal(listItems.length)
            setUsingMock(true)
        } finally {
            setLoading(false)
        }
    }

    const handleViewBundle = async (bundleId: string) => {
        try {
            const detail = await getEvidenceBundle(bundleId)
            setSelectedBundle(detail)
            setDrawerOpen(true)
        } catch (error) {
            const fallback = mockBundleMap.get(bundleId)
            if (fallback) {
                setSelectedBundle(fallback)
                setDrawerOpen(true)
                return
            }
            message.error('无法加载证据详情')
        }
    }

    useEffect(() => {
        fetchBundles()
    }, [page, pageSize])

    const columns: ColumnsType<EvidenceBundleListItem> = [
        {
            title: 'Bundle ID',
            dataIndex: 'evidence_bundle_id',
            key: 'evidence_bundle_id',
            width: 200,
        },
        {
            title: '类型',
            dataIndex: 'bundle_type',
            key: 'bundle_type',
            width: 160,
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
            render: (value: boolean) => (
                <Tag color={value ? 'green' : 'default'}>{value ? '已封存' : '未封存'}</Tag>
            ),
        },
        {
            title: '操作',
            key: 'actions',
            width: 120,
            render: (_: unknown, record: EvidenceBundleListItem) => (
                <Button type="link" onClick={() => handleViewBundle(record.evidence_bundle_id)}>
                    查看
                </Button>
            ),
        },
    ]

    return (
        <div style={{ padding: '24px' }}>
            <div style={{ marginBottom: 16 }}>
                <h2 style={{ marginBottom: 4 }}>证据包</h2>
                <div style={{ color: usingMock ? '#fa8c16' : '#8c8c8c' }}>
                    {usingMock ? '当前使用本地 mock 数据' : '来自后端的证据记录'}
                </div>
            </div>

            <Table
                columns={columns}
                dataSource={bundles}
                rowKey="evidence_bundle_id"
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

            <Drawer
                title="证据包详情"
                open={drawerOpen}
                width={520}
                onClose={() => setDrawerOpen(false)}
            >
                {selectedBundle ? (
                    <>
                        <Descriptions bordered size="small" column={1} style={{ marginBottom: 16 }}>
                            <Descriptions.Item label="Bundle ID">
                                {selectedBundle.evidence_bundle_id}
                            </Descriptions.Item>
                            <Descriptions.Item label="类型">{selectedBundle.bundle_type}</Descriptions.Item>
                            <Descriptions.Item label="Hash">{selectedBundle.bundle_hash}</Descriptions.Item>
                            <Descriptions.Item label="封存状态">
                                {selectedBundle.is_sealed ? '已封存' : '未封存'}
                            </Descriptions.Item>
                            <Descriptions.Item label="观测开始">
                                {formatTime(selectedBundle.observed_time_start)}
                            </Descriptions.Item>
                            <Descriptions.Item label="观测结束">
                                {formatTime(selectedBundle.observed_time_end)}
                            </Descriptions.Item>
                            <Descriptions.Item label="入库时间">
                                {formatTime(selectedBundle.ingest_time)}
                            </Descriptions.Item>
                            <Descriptions.Item label="摘要">
                                {selectedBundle.human_summary || '-'}
                            </Descriptions.Item>
                        </Descriptions>

                        <List
                            header={<div>证据条目</div>}
                            dataSource={selectedBundle.items}
                            renderItem={(item) => (
                                <List.Item>
                                    <List.Item.Meta
                                        title={`${item.evidence_type} · ${item.evidence_id}`}
                                        description={
                                            <div>
                                                <div>URI: {item.content_uri}</div>
                                                <div>观测时间: {formatTime(item.observed_time)}</div>
                                            </div>
                                        }
                                    />
                                </List.Item>
                            )}
                        />
                    </>
                ) : (
                    <div>暂无数据</div>
                )}
            </Drawer>
        </div>
    )
}

export default EvidencePage
