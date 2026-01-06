/**
 * 任务报告页面
 * 展示任务执行结果和评分
 */
import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
    Card,
    Row,
    Col,
    Typography,
    Tag,
    Table,
    Spin,
    Result,
    Button,
    Descriptions,
    Progress,
    Space,
} from 'antd'
import {
    FileTextOutlined,
    CheckCircleOutlined,
    CloseCircleOutlined,
    ClockCircleOutlined,
    ArrowLeftOutlined,
} from '@ant-design/icons'
import apiClient from '@/api/client'

const { Title, Text } = Typography

// 报告类型定义
interface StepScore {
    step_id: string
    step_name: string
    score: number
    max_score: number
    feedback?: string
}

interface TaskReport {
    task_id: string
    sop_id: string
    sop_title: string
    status: string
    total_score: number
    max_score: number
    percentage: number
    started_at?: string
    completed_at?: string
    step_scores: StepScore[]
}

function ReportPage() {
    const { taskId } = useParams<{ taskId: string }>()
    const navigate = useNavigate()
    const [loading, setLoading] = useState(true)
    const [report, setReport] = useState<TaskReport | null>(null)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        const fetchReport = async () => {
            if (!taskId) return

            try {
                setLoading(true)
                const response = await apiClient.get(`/api/v1/tasks/${taskId}/report`)
                setReport(response.data)
            } catch (err: any) {
                console.error('Failed to fetch report:', err)
                setError(err.response?.data?.detail || '获取报告失败')
            } finally {
                setLoading(false)
            }
        }

        fetchReport()
    }, [taskId])

    if (loading) {
        return (
            <div style={{ textAlign: 'center', padding: '100px' }}>
                <Spin size="large" />
                <p>加载报告中...</p>
            </div>
        )
    }

    if (error || !report) {
        return (
            <Result
                status="error"
                title="加载报告失败"
                subTitle={error || '未知错误'}
                extra={[
                    <Button key="back" type="primary" onClick={() => navigate('/sops')}>
                        返回SOP列表
                    </Button>,
                ]}
            />
        )
    }

    const getScoreColor = (percentage: number) => {
        if (percentage >= 90) return '#52c41a'
        if (percentage >= 70) return '#faad14'
        return '#f5222d'
    }

    const getStatusTag = (status: string) => {
        const statusMap: Record<string, { color: string; text: string }> = {
            completed: { color: 'success', text: '已完成' },
            failed: { color: 'error', text: '失败' },
            timeout: { color: 'warning', text: '超时' },
        }
        const config = statusMap[status] || { color: 'default', text: status }
        return <Tag color={config.color}>{config.text}</Tag>
    }

    const columns = [
        {
            title: '步骤名称',
            dataIndex: 'step_name',
            key: 'step_name',
        },
        {
            title: '得分',
            key: 'score',
            render: (record: StepScore) => (
                <Space>
                    <Text strong>{record.score}</Text>
                    <Text type="secondary">/ {record.max_score}</Text>
                </Space>
            ),
        },
        {
            title: '评价',
            dataIndex: 'feedback',
            key: 'feedback',
            render: (feedback: string) => feedback || '-',
        },
        {
            title: '状态',
            key: 'status',
            render: (record: StepScore) => {
                const passed = record.score >= record.max_score * 0.6
                return passed ? (
                    <Tag icon={<CheckCircleOutlined />} color="success">
                        通过
                    </Tag>
                ) : (
                    <Tag icon={<CloseCircleOutlined />} color="error">
                        未通过
                    </Tag>
                )
            },
        },
    ]

    return (
        <div>
            <div style={{ marginBottom: 24 }}>
                <Button
                    icon={<ArrowLeftOutlined />}
                    onClick={() => navigate('/sops')}
                    style={{ marginBottom: 16 }}
                >
                    返回SOP列表
                </Button>

                <Title level={3}>
                    <FileTextOutlined style={{ marginRight: 8 }} />
                    任务报告
                </Title>
            </div>

            <Row gutter={[16, 16]}>
                {/* 总分卡片 */}
                <Col xs={24} md={8}>
                    <Card>
                        <div style={{ textAlign: 'center' }}>
                            <Progress
                                type="circle"
                                percent={report.percentage}
                                format={(percent) => (
                                    <span style={{ color: getScoreColor(percent || 0) }}>
                                        {percent}%
                                    </span>
                                )}
                                strokeColor={getScoreColor(report.percentage)}
                                size={120}
                            />
                            <div style={{ marginTop: 16 }}>
                                <Text strong style={{ fontSize: 18 }}>
                                    总分: {report.total_score} / {report.max_score}
                                </Text>
                            </div>
                        </div>
                    </Card>
                </Col>

                {/* 任务信息 */}
                <Col xs={24} md={16}>
                    <Card title="任务信息">
                        <Descriptions column={{ xs: 1, sm: 2 }}>
                            <Descriptions.Item label="SOP名称">
                                {report.sop_title}
                            </Descriptions.Item>
                            <Descriptions.Item label="任务状态">
                                {getStatusTag(report.status)}
                            </Descriptions.Item>
                            <Descriptions.Item label="开始时间">
                                {report.started_at ? (
                                    <Space>
                                        <ClockCircleOutlined />
                                        {new Date(report.started_at).toLocaleString('zh-CN')}
                                    </Space>
                                ) : (
                                    '-'
                                )}
                            </Descriptions.Item>
                            <Descriptions.Item label="完成时间">
                                {report.completed_at ? (
                                    <Space>
                                        <ClockCircleOutlined />
                                        {new Date(report.completed_at).toLocaleString('zh-CN')}
                                    </Space>
                                ) : (
                                    '-'
                                )}
                            </Descriptions.Item>
                        </Descriptions>
                    </Card>
                </Col>
            </Row>

            {/* 步骤得分详情 */}
            <Card title="步骤得分详情" style={{ marginTop: 16 }}>
                <Table
                    dataSource={report.step_scores}
                    columns={columns}
                    rowKey="step_id"
                    pagination={false}
                />
            </Card>
        </div>
    )
}

export default ReportPage
