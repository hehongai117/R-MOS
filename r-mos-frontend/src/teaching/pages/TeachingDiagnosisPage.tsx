/**
 * 教学诊断报告页面
 */
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Button, Card, Collapse, Descriptions, List, Result, Spin, Tag, Typography } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { getAttemptDiagnosis } from '@/api/teaching'
import type { DiagnosisReport, DiagnosisSeverity, StepDiagnosisSourceRefs } from '@/types/teaching'
import { formatTeachingError } from '@/teaching/utils/api'

const { Title, Text } = Typography

const severityColor: Record<DiagnosisSeverity, string> = {
  LOW: 'green',
  MEDIUM: 'orange',
  HIGH: 'red',
}

const severityLabels: Record<DiagnosisSeverity, string> = {
  LOW: '低',
  MEDIUM: '中',
  HIGH: '高',
}

const diagnosisCodeLabels: Record<string, string> = {
  OK: '无异常',
  E_ERROR_OCCURRED: '存在错误步骤',
  E_STEP_SKIPPED: '存在跳过步骤',
  E_TOO_SLOW: '步骤耗时偏长',
}

const getDiagnosisLabel = (code: string) => diagnosisCodeLabels[code] ?? code

const formatStepSourceRefs = (refs?: StepDiagnosisSourceRefs) => {
  if (!refs) {
    return '-'
  }
  const parts: string[] = []
  if (refs.stepId !== undefined && refs.stepId !== null && refs.stepId !== '') {
    parts.push(`step_id=${refs.stepId}`)
  }
  if (refs.snapshotId !== undefined && refs.snapshotId !== null && refs.snapshotId !== '') {
    parts.push(`snapshot_id=${refs.snapshotId}`)
  }
  return parts.length > 0 ? parts.join(', ') : '-'
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

  const diagnosisLabel = getDiagnosisLabel(data.diagnosisCode)
  const stepDiagnoses = data.stepDiagnoses ?? []

  return (
    <div>
      <Title level={3} style={{ marginBottom: 8 }}>诊断报告</Title>
      <Text type="secondary">面向教师的可解释诊断结果</Text>

      <Card style={{ marginTop: 16 }}>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="尝试编号">{data.attemptId}</Descriptions.Item>
          <Descriptions.Item label="规则编号">{data.ruleId}</Descriptions.Item>
          <Descriptions.Item label="诊断代码">
            <span>
              <Text strong>{diagnosisLabel}</Text>
              {diagnosisLabel !== data.diagnosisCode && (
                <Text type="secondary" style={{ marginLeft: 8 }}>
                  ({data.diagnosisCode})
                </Text>
              )}
            </span>
          </Descriptions.Item>
          <Descriptions.Item label="严重等级">
            <Tag color={severityColor[data.severity]}>{severityLabels[data.severity]}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="生成时间">{data.generatedAt}</Descriptions.Item>
          <Descriptions.Item label="证据关联">{data.sourceRefs?.attemptEvidenceId ?? '-'}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="诊断发现" style={{ marginTop: 16 }}>
        {data.findings.length === 0 ? (
          <div>无</div>
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
          <div>无</div>
        ) : (
          <List
            size="small"
            dataSource={data.recommendations}
            renderItem={(item) => <List.Item>{item}</List.Item>}
          />
        )}
      </Card>

      <Card title="步骤诊断" style={{ marginTop: 16 }}>
        {stepDiagnoses.length === 0 ? (
          <div>无</div>
        ) : (
          <Collapse
            accordion
            items={stepDiagnoses.map((step) => ({
              key: String(step.stepIndex),
              label: (
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <span>步骤 {step.stepIndex}</span>
                  <Tag color={severityColor[step.severity]}>{severityLabels[step.severity]}</Tag>
                  <Text type="secondary">{getDiagnosisLabel(step.stepDiagnosisCode)}</Text>
                </div>
              ),
              children: (
                <div>
                  <Descriptions column={2} size="small">
                    <Descriptions.Item label="诊断代码">{getDiagnosisLabel(step.stepDiagnosisCode)}</Descriptions.Item>
                    <Descriptions.Item label="规则编号">{step.ruleId}</Descriptions.Item>
                    <Descriptions.Item label="严重等级">
                      <Tag color={severityColor[step.severity]}>{severityLabels[step.severity]}</Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="证据关联">{formatStepSourceRefs(step.sourceRefs)}</Descriptions.Item>
                  </Descriptions>
                  <div style={{ marginTop: 12 }}>
                    <div style={{ marginBottom: 6 }}>
                      <Text strong>诊断发现</Text>
                    </div>
                    {step.findings.length === 0 ? (
                      <div>无</div>
                    ) : (
                      <List
                        size="small"
                        dataSource={step.findings}
                        renderItem={(item) => <List.Item>{item}</List.Item>}
                      />
                    )}
                  </div>
                  <div style={{ marginTop: 12 }}>
                    <div style={{ marginBottom: 6 }}>
                      <Text strong>建议</Text>
                    </div>
                    {step.recommendations.length === 0 ? (
                      <div>无</div>
                    ) : (
                      <List
                        size="small"
                        dataSource={step.recommendations}
                        renderItem={(item) => <List.Item>{item}</List.Item>}
                      />
                    )}
                  </div>
                </div>
              ),
            }))}
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
