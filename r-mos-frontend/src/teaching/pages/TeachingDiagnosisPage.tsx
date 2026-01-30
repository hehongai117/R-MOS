/**
 * 教学诊断报告页面
 */
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Button, Card, Descriptions, List, Result, Spin, Tag, Typography } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { getAttemptDiagnosis } from '@/api/teaching'
import type { DiagnosisReport, DiagnosisSeverity } from '@/types/teaching'
import { formatTeachingError } from '@/teaching/utils/api'

const { Title, Text } = Typography

const severityColor: Record<DiagnosisSeverity, string> = {
  LOW: 'green',
  MEDIUM: 'orange',
  HIGH: 'red',
}

const TeachingDiagnosisPage = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const attemptId = Number(id)

  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [data, setData] = useState<DiagnosisReport | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      setNotFound(false)
      setErrorMessage(null)
      try {
        const response = await getAttemptDiagnosis(attemptId)
        setData(response)
      } catch (err: any) {
        if (err?.response?.status === 404) {
          setNotFound(true)
        }
        setErrorMessage(formatTeachingError(err, '加载诊断报告失败'))
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

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '80px 0' }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>加载诊断报告中...</div>
      </div>
    )
  }

  if (notFound || !data) {
    return (
      <Result
        status="404"
        title="诊断报告不存在"
        subTitle={errorMessage || '未找到诊断报告，请确认尝试是否存在'}
        extra={
          <Button type="primary" icon={<ArrowLeftOutlined />} onClick={() => navigate('/teaching/assignments')}>
            返回作业列表
          </Button>
        }
      />
    )
  }

  return (
    <div>
      <Title level={3} style={{ marginBottom: 8 }}>诊断报告</Title>
      <Text type="secondary">面向教师的可解释诊断结果</Text>

      <Card style={{ marginTop: 16 }}>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="尝试编号">{data.attemptId}</Descriptions.Item>
          <Descriptions.Item label="规则编号">{data.ruleId}</Descriptions.Item>
          <Descriptions.Item label="诊断代码">{data.diagnosisCode}</Descriptions.Item>
          <Descriptions.Item label="严重等级">
            <Tag color={severityColor[data.severity]}>{data.severity}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="生成时间">{data.generatedAt}</Descriptions.Item>
          <Descriptions.Item label="证据关联">{data.sourceRefs?.attemptEvidenceId ?? '-'}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="诊断发现" style={{ marginTop: 16 }}>
        {data.findings.length === 0 ? (
          <div>暂无诊断发现</div>
        ) : (
          <List
            size="small"
            dataSource={data.findings}
            renderItem={(item) => <List.Item>{item}</List.Item>}
          />
        )}
      </Card>

      <Card title="建议" style={{ marginTop: 16 }}>
        {data.recommendations.length === 0 ? (
          <div>暂无建议</div>
        ) : (
          <List
            size="small"
            dataSource={data.recommendations}
            renderItem={(item) => <List.Item>{item}</List.Item>}
          />
        )}
      </Card>

      <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/teaching/attempts/${attemptId}/evidence`)}>
          返回证据摘要
        </Button>
        <Button onClick={() => navigate(`/teaching/attempts/${attemptId}`)}>
          返回尝试页面
        </Button>
      </div>
    </div>
  )
}

export default TeachingDiagnosisPage
