/**
 * 教学尝试执行页面
 */
import { Suspense, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Button, Card, Descriptions, Divider, message, Result, Spin, Steps, Tag } from 'antd'
import { PlayCircleOutlined, ArrowLeftOutlined } from '@ant-design/icons'
import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import { CameraController } from '@/components/Viewer3D/CameraController'
import { Atom01Interactive } from '@/components/Viewer3D/Atom01Interactive'
import { PART_FOCUS_POSITIONS } from '@/hooks/useCameraFocus'
import { executeStep, getTask, startTask } from '@/api/task'
import {
  getAssignment,
  getAttempt,
  getAttemptEvidence,
  updateAttemptStatus,
} from '@/api/teaching'
import { getSOP } from '@/api/sop'
import type { Assignment, AssignmentAttempt } from '@/types/teaching'
import type { SOP } from '@/types/sop'
import type { Task } from '@/types/task'
import { resolveTargetPart, resolveToolLabel } from '@/teaching/utils/ghostHand'
import { formatTeachingError } from '@/teaching/utils/api'

const GhostToolMarker = ({ targetPart }: { targetPart?: string | null }) => {
  if (!targetPart) return null
  const focus = PART_FOCUS_POSITIONS[targetPart]
  if (!focus) return null
  const [x, y, z] = focus.position
  return (
    <mesh position={[x + 0.06, y + 0.05, z + 0.05]}>
      <boxGeometry args={[0.06, 0.06, 0.16]} />
      <meshStandardMaterial color="#69c0ff" transparent opacity={0.35} />
    </mesh>
  )
}

const 三维加载占位 = () => (
  <mesh>
    <boxGeometry args={[0.2, 0.2, 0.2]} />
    <meshStandardMaterial color="#666" wireframe />
  </mesh>
)

const TeachingAttemptPage = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [attempt, setAttempt] = useState<AssignmentAttempt | null>(null)
  const [assignment, setAssignment] = useState<Assignment | null>(null)
  const [task, setTask] = useState<Task | null>(null)
  const [sop, setSop] = useState<SOP | null>(null)
  const [loading, setLoading] = useState(true)
  const [executing, setExecuting] = useState(false)
  const [notFound, setNotFound] = useState(false)
  const [evidenceReady, setEvidenceReady] = useState(false)
  const statusLabelMap: Record<string, string> = {
    in_progress: '进行中',
    completed: '已完成',
    graded: '已评分',
    abandoned: '已放弃',
  }

  const attemptId = Number(id)

  const loadAttemptData = async () => {
    setLoading(true)
    setNotFound(false)
    try {
      const attemptData = await getAttempt(attemptId)
      setAttempt(attemptData)

      const assignmentData = await getAssignment(attemptData.assignmentId)
      setAssignment(assignmentData)

      if (assignmentData.sopId) {
        const sopData = await getSOP(assignmentData.sopId)
        setSop(sopData)
      }

      if (attemptData.taskId) {
        const taskData = await getTask(attemptData.taskId)
        setTask(taskData)
      }

      if (attemptData.status === 'completed' || attemptData.status === 'graded') {
        setEvidenceReady(true)
      }
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } } | null)?.response?.status
      if (status === 404) {
        setNotFound(true)
      }
      message.error(formatTeachingError(err, '加载尝试失败'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!attemptId) {
      setNotFound(true)
      setLoading(false)
      return
    }
    loadAttemptData()
  }, [attemptId])

  const steps = sop?.steps || []
  const currentStepIndex = task?.current_step_index ?? 0
  const nextStep = steps.find((step) => step.step_index === currentStepIndex + 1) || null
  const targetPart = resolveTargetPart(nextStep)
  const toolLabel = resolveToolLabel(nextStep)

  const handleStartTask = async () => {
    if (!task) return
    try {
      await startTask(task.id)
      message.success('任务已启动')
      await loadAttemptData()
    } catch (err) {
      message.error(formatTeachingError(err, '启动任务失败'))
    }
  }

  const handleExecuteStep = async () => {
    if (!task || !nextStep) return
    setExecuting(true)
    try {
      const response = await executeStep(task.id, {
        step_index: nextStep.step_index,
        action: nextStep.expected_action || 'execute',
        parameters: {},
      })

      message.success(response.message || '步骤执行成功')

      if (response.is_task_completed) {
        await updateAttemptStatus(attemptId, 'completed')
        setEvidenceReady(true)
        message.success('任务完成，尝试已结束')
        try {
          await getAttemptEvidence(attemptId)
        } catch (err) {
          message.error(formatTeachingError(err, '证据生成失败'))
        }
      }

      await loadAttemptData()
    } catch (err) {
      message.error(formatTeachingError(err, '步骤执行失败'))
    } finally {
      setExecuting(false)
    }
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '80px 0' }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>加载教学尝试中...</div>
      </div>
    )
  }

  if (notFound || !attempt) {
    return (
      <Result
        status="404"
        title="尝试不存在"
        subTitle="请返回作业列表重新开始"
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
      <Card title={assignment?.title || '教学尝试'}>
        <Descriptions size="small" column={2} style={{ marginBottom: 16 }}>
          <Descriptions.Item label="尝试编号">{attempt.id}</Descriptions.Item>
          <Descriptions.Item label="学生编号">{attempt.studentId}</Descriptions.Item>
          <Descriptions.Item label="任务编号">{task?.id ?? '未绑定'}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={attempt.status === 'completed' ? 'green' : 'blue'}>
              {statusLabelMap[attempt.status] || attempt.status}
            </Tag>
          </Descriptions.Item>
        </Descriptions>

        <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 0.9fr', gap: 16 }}>
          <Card title="引导视角" bodyStyle={{ padding: 0 }}>
            <div style={{ height: 360 }}>
              <Canvas camera={{ position: [1.5, 1, 1.5], fov: 45 }}>
                <ambientLight intensity={0.6} />
                <directionalLight position={[4, 6, 3]} intensity={0.8} />
                <Suspense fallback={<三维加载占位 />}>
                  <Atom01Interactive
                    selectedPart={targetPart}
                    hoveredPart={null}
                  />
                  <GhostToolMarker targetPart={targetPart} />
                  <CameraController focusTarget={targetPart} />
                  <OrbitControls enablePan enableZoom />
                </Suspense>
              </Canvas>
            </div>
            <div style={{ padding: '12px 16px' }}>
              <div>目标部件：{targetPart || '未解析'}</div>
              <div>工具虚影：{toolLabel}</div>
            </div>
          </Card>

          <Card title="步骤引导">
            <Steps
              current={currentStepIndex}
              items={steps.map((step) => ({
                title: step.title,
                description: step.description,
              }))}
            />
            <Divider />
            <div style={{ minHeight: 120 }}>
              <div style={{ marginBottom: 8, fontWeight: 500 }}>当前步骤</div>
              {nextStep ? (
                <div>
                  <div>步骤 {nextStep.step_index}：{nextStep.title}</div>
                  <div style={{ marginTop: 8, color: '#666' }}>{nextStep.description}</div>
                  {nextStep.hints && nextStep.hints.length > 0 && (
                    <div style={{ marginTop: 8 }}>提示：{nextStep.hints.join(' / ')}</div>
                  )}
                </div>
              ) : (
                <div>暂无待执行步骤</div>
              )}
            </div>
            <Divider />
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {task?.status === 'pending' && (
                <Button type="primary" onClick={handleStartTask}>
                  启动任务
                </Button>
              )}
              {task?.status === 'in_progress' && (
                <Button
                  type="primary"
                  icon={<PlayCircleOutlined />}
                  loading={executing}
                  onClick={handleExecuteStep}
                  disabled={!nextStep}
                >
                  执行下一步
                </Button>
              )}
              {evidenceReady && (
                <Button onClick={() => navigate(`/teaching/attempts/${attempt.id}/evidence`)}>
                  查看证据摘要
                </Button>
              )}
            </div>
          </Card>
        </div>
      </Card>
    </div>
  )
}

export default TeachingAttemptPage
