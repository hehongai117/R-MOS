/**
 * 教学证据摘要页面
 */
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Button, Card, Descriptions, Result, Spin, Tag, Typography } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { getAttemptEvidence } from '@/api/teaching'
import type { AttemptEvidenceResponse } from '@/types/teaching'
import { formatTeachingError } from '@/teaching/utils/api'

const { Title, Text } = Typography

const TeachingEvidencePage = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const attemptId = Number(id)

  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [data, setData] = useState<AttemptEvidenceResponse | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      setNotFound(false)
      setErrorMessage(null)
      try {
        const response = await getAttemptEvidence(attemptId)
        setData(response)
      } catch (err: any) {
        if (err?.response?.status === 404) {
          setNotFound(true)
        }
        setErrorMessage(formatTeachingError(err, '加载证据失败'))
      } finally {
        setLoading(false)
      }
    }

    if (!attemptId) {
      setNotFound(true)
      setLoading(false)
      return
    }

    fetchData()
  }, [attemptId])

  const summary = useMemo(() => data?.summary || null, [data])

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '80px 0' }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>加载证据摘要中...</div>
      </div>
    )
  }

  if (notFound || !data) {
    return (
      <Result
        status="404"
        title="证据不存在"
        subTitle={errorMessage || '未找到证据关联，请确认任务是否完成'}
        extra={
          <Button type="primary" icon={<ArrowLeftOutlined />} onClick={() => navigate('/teaching/assignments')}>
            返回作业列表
          </Button>
        }
      />
    )
  }

  const summaryEntries = Object.entries(summary || {})

  return (
    <div>
      <Title level={3} style={{ marginBottom: 8 }}>证据摘要</Title>
      <Text type="secondary">用于教学回放与评分的摘要数据</Text>

      <Card style={{ marginTop: 16 }}>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="尝试编号">{data.attemptId}</Descriptions.Item>
          <Descriptions.Item label="任务编号">{data.taskId ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="证据包">{data.bundleId}</Descriptions.Item>
          <Descriptions.Item label="摘要状态">
            <Tag color={summary ? 'green' : 'default'}>{summary ? '已生成' : '无摘要'}</Tag>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="摘要详情" style={{ marginTop: 16 }}>
        {summaryEntries.length === 0 ? (
          <div>暂无摘要数据</div>
        ) : (
          <Descriptions column={1} size="small">
            {summaryEntries.map(([key, value]) => (
              <Descriptions.Item key={key} label={key}>
                {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
              </Descriptions.Item>
            ))}
          </Descriptions>
        )}
      </Card>

      <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
        <Button type="primary" onClick={() => navigate(`/teaching/attempts/${attemptId}/diagnosis`)}>
          查看诊断报告
        </Button>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/teaching/attempts/${attemptId}`)}>
          返回尝试页面
        </Button>
      </div>
    </div>
  )
}

export default TeachingEvidencePage
