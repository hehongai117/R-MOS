import { useCallback, useEffect, useMemo, useState } from 'react'
import { Alert, Button, Card, Descriptions, Input, Select, Space, Tag, Typography, message } from 'antd'
import { ArrowRightOutlined, FileSearchOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'

import { createMaintenanceDraft, getExecutableMaintenanceDraft } from '@/api/maintenance'
import { listRobotProjects } from '@/api/robotKnowledge'
import {
  readMaintenanceWorkspaceSession,
  writeMaintenanceWorkspaceSession,
} from '@/features/maintenance/runtimeWorkspaceSession'
import type { MaintenanceDraftResponse } from '@/types/maintenance'
import type { RobotProjectSummary } from '@/types/robotKnowledge'

const { Title, Paragraph, Text } = Typography

function formatProjectLabel(project: RobotProjectSummary) {
  return `${project.brand} ${project.model} ${project.version ?? ''}`.trim()
}

export default function MaintenanceProjectDraftPage() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState<RobotProjectSummary[]>([])
  const [projectsLoading, setProjectsLoading] = useState(false)
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null)
  const [maintenanceGoal, setMaintenanceGoal] = useState('执行器弯曲维护')
  const [focusArea, setFocusArea] = useState('肘关节')
  const [draftLoading, setDraftLoading] = useState(false)
  const [runtimeDraft, setRuntimeDraft] = useState<MaintenanceDraftResponse | null>(null)

  useEffect(() => {
    const session = readMaintenanceWorkspaceSession()
    if (!session) {
      return
    }

    setSelectedProjectId(session.projectId)
    setMaintenanceGoal(session.maintenanceGoal || '执行器弯曲维护')
    setFocusArea(session.focusArea || '肘关节')
    setRuntimeDraft(session.draft)
  }, [])

  useEffect(() => {
    let ignore = false

    const loadProjects = async () => {
      setProjectsLoading(true)
      try {
        const response = await listRobotProjects()
        if (ignore) {
          return
        }
        const readyProjects = response.projects.filter((project) => project.status === 'ready')
        setProjects(readyProjects)
        setSelectedProjectId((current) => current ?? readyProjects[0]?.project_id ?? null)
      } catch {
        if (!ignore) {
          message.error('机器人项目加载失败')
        }
      } finally {
        if (!ignore) {
          setProjectsLoading(false)
        }
      }
    }

    void loadProjects()

    return () => {
      ignore = true
    }
  }, [])

  const selectedProject = useMemo(
    () => projects.find((project) => project.project_id === selectedProjectId) ?? null,
    [projects, selectedProjectId],
  )

  const persistSession = useCallback(
    (draft: MaintenanceDraftResponse | null) => {
      writeMaintenanceWorkspaceSession({
        projectId: selectedProjectId,
        projectLabel: selectedProject ? formatProjectLabel(selectedProject) : undefined,
        maintenanceGoal: maintenanceGoal.trim() || '执行器弯曲维护',
        focusArea: focusArea.trim() || '肘关节',
        draft,
      })
    },
    [focusArea, maintenanceGoal, selectedProject, selectedProjectId],
  )

  const handleGenerateDraft = useCallback(async () => {
    if (!selectedProjectId) {
      message.warning('请先选择机器人项目')
      return
    }

    setDraftLoading(true)
    try {
      const draft = await createMaintenanceDraft({
        project_id: selectedProjectId,
        maintenance_goal: maintenanceGoal.trim() || '执行器弯曲维护',
        focus_area: focusArea.trim() || undefined,
      })
      setRuntimeDraft(draft)
      persistSession(draft)
      message.success('AI 草案已生成')
    } catch {
      message.error('AI 草案生成失败')
    } finally {
      setDraftLoading(false)
    }
  }, [focusArea, maintenanceGoal, persistSession, selectedProjectId])

  const handleLoadExecutableDraft = useCallback(async () => {
    if (!selectedProjectId) {
      message.warning('请先选择机器人项目')
      return
    }

    setDraftLoading(true)
    try {
      const draft = await getExecutableMaintenanceDraft(selectedProjectId)
      setRuntimeDraft(draft)
      persistSession(draft)
      message.success('已加载批准执行版')
    } catch {
      message.error('暂无批准执行版草案')
    } finally {
      setDraftLoading(false)
    }
  }, [persistSession, selectedProjectId])

  const handleOpenWorkbench = useCallback(() => {
    persistSession(runtimeDraft)
    navigate('/maintenance')
  }, [navigate, persistSession, runtimeDraft])

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <div>
        <Title level={2} style={{ marginBottom: 8 }}>
          项目草案页
        </Title>
        <Paragraph type="secondary" style={{ marginBottom: 0 }}>
          在这里选择 ready 机器人项目、生成 AI 维保草案，确认后再进入 SOP 工作台执行与交互。
        </Paragraph>
      </div>

      <Card>
        <div style={{ display: 'grid', gap: 16 }}>
          <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
            <div>
              <Text type="secondary" style={{ display: 'block', marginBottom: 6 }}>
                机器人项目
              </Text>
              <Select
                aria-label="机器人项目"
                loading={projectsLoading}
                value={selectedProjectId ?? undefined}
                placeholder="选择 ready 项目"
                style={{ width: '100%' }}
                onChange={(value) => setSelectedProjectId(value)}
                options={projects.map((project) => ({
                  value: project.project_id,
                  label: formatProjectLabel(project),
                }))}
              />
            </div>

            <div>
              <Text type="secondary" style={{ display: 'block', marginBottom: 6 }}>
                维保目标
              </Text>
              <Input
                aria-label="维保目标"
                value={maintenanceGoal}
                onChange={(event) => setMaintenanceGoal(event.target.value)}
                placeholder="例如 执行器弯曲维护"
              />
            </div>

            <div>
              <Text type="secondary" style={{ display: 'block', marginBottom: 6 }}>
                关注部位
              </Text>
              <Input
                aria-label="关注部位"
                value={focusArea}
                onChange={(event) => setFocusArea(event.target.value)}
                placeholder="例如 肘关节"
              />
            </div>
          </div>

          <Space wrap>
            <Button
              type="primary"
              loading={draftLoading}
              disabled={!selectedProjectId || projectsLoading}
              onClick={() => void handleGenerateDraft()}
            >
              生成 AI 草案
            </Button>
            <Button
              loading={draftLoading}
              disabled={!selectedProjectId || projectsLoading}
              onClick={() => void handleLoadExecutableDraft()}
            >
              加载批准执行版
            </Button>
          </Space>
        </div>
      </Card>

      {runtimeDraft ? (
        <Card
          title={runtimeDraft.draft.title}
          extra={
            <Button
              type="primary"
              aria-label="在 SOP 工作台打开"
              icon={<ArrowRightOutlined />}
              onClick={handleOpenWorkbench}
            >
              在 SOP 工作台打开
            </Button>
          }
        >
          <div style={{ display: 'grid', gap: 16 }}>
            <Descriptions size="small" column={3} bordered>
              <Descriptions.Item label="项目">{selectedProject ? formatProjectLabel(selectedProject) : runtimeDraft.project_id}</Descriptions.Item>
              <Descriptions.Item label="审核状态">{runtimeDraft.review_status}</Descriptions.Item>
              <Descriptions.Item label="引用数量">{runtimeDraft.citations.length}</Descriptions.Item>
            </Descriptions>

            {runtimeDraft.viewer_manifest.needs_review_nodes?.length ? (
              <Alert
                type="warning"
                showIcon
                message={`以下部位仍需人工复核：${runtimeDraft.viewer_manifest.needs_review_nodes.join('、')}`}
              />
            ) : null}

            <div style={{ display: 'grid', gap: 8 }}>
              <Text strong>草案步骤</Text>
              {runtimeDraft.draft.steps.map((step, index) => (
                <Card key={step.step_id} size="small">
                  <Space direction="vertical" size={2}>
                    <Text strong>
                      {index + 1}. {step.title}
                    </Text>
                    <Text type="secondary">{step.description}</Text>
                  </Space>
                </Card>
              ))}
            </div>

            <div style={{ display: 'grid', gap: 8 }}>
              <Text strong>知识引用</Text>
              <Space wrap>
                {runtimeDraft.citations.map((citation, index) => (
                  <Tag key={`${citation.title}-${index}`} icon={<FileSearchOutlined />} color="blue">
                    {citation.title}
                    {citation.source ? ` · ${citation.source}` : ''}
                  </Tag>
                ))}
              </Space>
            </div>
          </div>
        </Card>
      ) : null}
    </div>
  )
}
