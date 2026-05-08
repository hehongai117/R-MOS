import { Search } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Empty, Form, Select, Table, Tabs, message } from 'antd'

import {
  KnowledgeEntry,
  approveKnowledge,
  createKnowledge,
  searchKnowledge,
  submitKnowledgeForReview,
} from '@/api/agent'
import {
  getRobotProjectUploadJob,
  listRobotProjects,
  uploadRobotProjectPackage,
} from '@/api/robotKnowledge'
import { listAnalysisTasks } from '@/api/robots'
import { AddRobotDialog } from '@/components/knowledge/AddRobotDialog'
import { AnalysisStatusPanel } from '@/components/knowledge/AnalysisStatusPanel'
import { FileUploader } from '@/components/knowledge/FileUploader'
import { PublishControl } from '@/components/knowledge/PublishControl'
import { RobotProjectTable } from '@/components/knowledge/RobotProjectTable'
import { RobotProjectUploadPanel } from '@/components/knowledge/RobotProjectUploadPanel'
import { RobotSidebar } from '@/components/knowledge/RobotSidebar'
import { PageHeader, SectionCard, StatusBadge } from '@/components/common'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { useAuthStore } from '@/store/authStore'
import { useRobotStore, useSelectedRobot } from '@/store/robotStore'
import type { AnalysisTask, RobotModelCreateRequest } from '@/types/robotModel'
import type { RobotProjectSummary, RobotProjectUploadJob } from '@/types/robotKnowledge'

const { Option } = Select

function statusTone(status: string) {
  if (status === 'APPROVED') return 'success'
  if (status === 'PENDING') return 'warning'
  if (status === 'REJECTED') return 'error'
  return 'idle'
}

function riskTone(level: string) {
  if (level === 'R3') return 'error'
  if (level === 'R2') return 'warning'
  if (level === 'R1') return 'active'
  return 'success'
}

function uploadStatusTone(status: string) {
  if (status === 'ready') return 'success'
  if (status === 'failed') return 'error'
  if (status === 'ingesting') return 'warning'
  return 'active'
}

const KnowledgePage = () => {
  const role = useAuthStore((state) => state.user?.role ?? 'student')
  const canManageKnowledge = role === 'teacher' || role === 'admin'

  // Robot store
  const { robots, selectedRobotId, isLoading: robotsLoading, fetchRobots, selectRobot, addRobot, togglePublish, toggleVisibility } = useRobotStore((state) => state)
  const selectedRobot = useSelectedRobot()

  // Add robot dialog state
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [addingRobot, setAddingRobot] = useState(false)

  // Analysis tasks state
  const [analysisTasks, setAnalysisTasks] = useState<AnalysisTask[]>([])
  const [analysisLoading, setAnalysisLoading] = useState(false)

  const [activeTab, setActiveTab] = useState('search')
  const [loading, setLoading] = useState(false)
  const [knowledgeList, setKnowledgeList] = useState<KnowledgeEntry[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedDevice, setSelectedDevice] = useState<string | undefined>()
  const [projectsLoading, setProjectsLoading] = useState(false)
  const [projects, setProjects] = useState<RobotProjectSummary[]>([])
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [uploadJobs, setUploadJobs] = useState<RobotProjectUploadJob[]>([])
  const pollingTimersRef = useRef<Record<string, number>>({})
  const [form] = Form.useForm()

  const upsertUploadJob = useCallback((job: RobotProjectUploadJob) => {
    setUploadJobs((prev) => {
      const next = [job, ...prev.filter((item) => item.job_id !== job.job_id)]
      return next.slice(0, 10)
    })
  }, [])

  const loadProjects = useCallback(async () => {
    setProjectsLoading(true)
    try {
      const result = await listRobotProjects()
      const nextProjects = Array.isArray(result)
        ? result
        : Array.isArray(result.projects)
          ? result.projects
          : []
      setProjects(nextProjects)
      setSelectedProjectId((current) => current ?? nextProjects[0]?.project_id ?? null)
    } catch {
      message.error('机器人项目列表加载失败')
    } finally {
      setProjectsLoading(false)
    }
  }, [])

  const handleSearch = useCallback(async () => {
    setLoading(true)
    try {
      const result = await searchKnowledge({
        query: searchQuery,
        device_model: selectedDevice,
      })
      setKnowledgeList(result.results)
    } catch {
      message.error('搜索失败')
    } finally {
      setLoading(false)
    }
  }, [searchQuery, selectedDevice])

  const startPollingUploadJob = useCallback((jobId: string) => {
    const clearCurrent = () => {
      const timerId = pollingTimersRef.current[jobId]
      if (timerId) {
        window.clearTimeout(timerId)
        delete pollingTimersRef.current[jobId]
      }
    }

    const poll = async () => {
      try {
        const job = await getRobotProjectUploadJob(jobId)
        upsertUploadJob(job)

        if (job.status === 'ready' || job.status === 'failed') {
          clearCurrent()
          setUploadProgress(100)
          await loadProjects()
          return
        }

        setUploadProgress((current) => Math.min(current + 15, 90))
        pollingTimersRef.current[jobId] = window.setTimeout(() => {
          void poll()
        }, 2000)
      } catch {
        clearCurrent()
        setUploadProgress(0)
        message.error('ingest 状态轮询失败')
      }
    }

    void poll()
  }, [loadProjects, upsertUploadJob])

  // Load analysis tasks when selectedRobotId changes
  const loadAnalysisTasks = useCallback(async (robotId: number) => {
    setAnalysisLoading(true)
    try {
      const result = await listAnalysisTasks(robotId)
      setAnalysisTasks(result.items)
    } catch {
      message.error('加载分析任务失败')
    } finally {
      setAnalysisLoading(false)
    }
  }, [])

  useEffect(() => {
    void handleSearch()
    void loadProjects()

    return () => {
      Object.values(pollingTimersRef.current).forEach((timerId) => {
        window.clearTimeout(timerId)
      })
      pollingTimersRef.current = {}
    }
  }, [handleSearch, loadProjects])

  // Fetch robots on mount for teacher/admin
  useEffect(() => {
    if (canManageKnowledge) {
      void fetchRobots()
    }
  }, [canManageKnowledge, fetchRobots])

  // Load analysis tasks when selected robot changes
  useEffect(() => {
    if (selectedRobotId !== null) {
      void loadAnalysisTasks(selectedRobotId)
    } else {
      setAnalysisTasks([])
    }
  }, [selectedRobotId, loadAnalysisTasks])

  const handleAddRobot = async (data: RobotModelCreateRequest) => {
    setAddingRobot(true)
    try {
      await addRobot(data)
      message.success('机器人已创建')
      setAddDialogOpen(false)
    } catch {
      message.error('创建机器人失败')
    } finally {
      setAddingRobot(false)
    }
  }

  const handleTriggerAnalysis = async () => {
    if (!selectedRobotId) return
    try {
      const { triggerAnalysis } = await import('@/api/robots')
      await triggerAnalysis(selectedRobotId)
      await loadAnalysisTasks(selectedRobotId)
      await fetchRobots()
      message.success('分析任务已触发')
    } catch {
      message.error('触发分析失败')
    }
  }

  const handleCreate = async (values: {
    title: string
    content: string
    type: string
    device_model?: string
    risk_level?: string
  }) => {
    try {
      await createKnowledge({
        title: values.title,
        content: values.content,
        type: values.type,
        scope: values.device_model ? { device_model: [values.device_model] } : undefined,
        risk_level: values.risk_level || 'R1',
      })
      message.success('知识条目已创建')
      form.resetFields()
      setActiveTab('search')
      await handleSearch()
    } catch {
      message.error('创建失败')
    }
  }

  const handleRobotUpload = async (payload: {
    file: File
    brand: string
    model: string
    version: string
  }) => {
    setUploading(true)
    setUploadProgress(10)
    try {
      const job = await uploadRobotProjectPackage(payload.file, {
        brand: payload.brand,
        model: payload.model,
        version: payload.version,
      })
      upsertUploadJob(job)
      setUploadProgress(35)
      setActiveTab('projects')
      startPollingUploadJob(job.job_id)
      message.success(`项目包已提交：${payload.file.name}`)
    } catch {
      setUploadProgress(0)
      message.error('项目包上传失败')
    } finally {
      setUploading(false)
    }
  }

  const knowledgeColumns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      render: (value: string) => <div className="text-sm text-text-primary">{value}</div>,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 120,
      render: (value: string) => <StatusBadge label={value} status="pending" />,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 140,
      render: (value: string) => <StatusBadge label={value} status={statusTone(value)} />,
    },
    {
      title: '风险等级',
      dataIndex: 'risk_level',
      key: 'risk_level',
      width: 120,
      render: (value: string) => <StatusBadge label={value} status={riskTone(value)} />,
    },
    {
      title: '操作',
      key: 'action',
      width: 240,
      render: (_: unknown, record: KnowledgeEntry) => (
        <div className="flex gap-2">
          {record.status === 'DRAFT' ? (
            <Button
              size="sm"
              type="button"
              variant="secondary"
              onClick={() => void submitKnowledgeForReview(record.id).then(handleSearch)}
            >
              提交
            </Button>
          ) : null}
          {record.status === 'PENDING' && canManageKnowledge ? (
            <>
              <Button
                size="sm"
                type="button"
                onClick={() => void approveKnowledge(record.id, 'approve').then(handleSearch)}
              >
                批准
              </Button>
              <Button
                size="sm"
                type="button"
                variant="outline"
                onClick={() => void approveKnowledge(record.id, 'reject').then(handleSearch)}
              >
                拒绝
              </Button>
            </>
          ) : null}
        </div>
      ),
    },
  ]

  const robotProjectTab = (
    <div className="space-y-4">
      {canManageKnowledge ? (
        <SectionCard title="项目包 ingest">
          <RobotProjectUploadPanel
            uploading={uploading}
            uploadProgress={uploadProgress}
            onUpload={handleRobotUpload}
          />
        </SectionCard>
      ) : null}

      <SectionCard title="最近项目">
        {projects.length === 0 && !projectsLoading ? (
          <Empty description="暂无机器人项目" />
        ) : (
          <RobotProjectTable
            loading={projectsLoading}
            projects={projects}
            selectedProjectId={selectedProjectId}
            onSelectProject={setSelectedProjectId}
          />
        )}
      </SectionCard>

      <SectionCard title="ingest 任务">
        {uploadJobs.length === 0 ? (
          <Empty description="暂无 ingest 记录" />
        ) : (
          <div className="space-y-3">
            {uploadJobs.map((job) => (
              <div
                key={job.job_id}
                className="flex items-center justify-between rounded-lg border border-border-subtle bg-bg-elevated px-4 py-3"
              >
                <div>
                  <div className="text-sm text-text-primary">
                    {(job.brand ?? '未知品牌') + ' ' + (job.model ?? '未知型号')}
                  </div>
                  <div className="mt-1 text-xs text-text-muted">
                    {job.filename ?? job.job_id} · {job.version ?? '-'}
                  </div>
                </div>
                <StatusBadge label={job.status} status={uploadStatusTone(job.status)} />
              </div>
            ))}
          </div>
        )}
      </SectionCard>
    </div>
  )

  const items = useMemo(() => {
    const baseItems = [
      {
        key: 'search',
        label: '知识搜索',
        children: (
          <div className="space-y-4">
            <SectionCard title="搜索条件">
              <div className="flex flex-wrap gap-3">
                <Input
                  className="max-w-[320px]"
                  placeholder="搜索知识..."
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                />
                <Select
                  allowClear
                  className="min-w-[180px]"
                  placeholder="选择设备"
                  value={selectedDevice}
                  onChange={setSelectedDevice}
                >
                  <Option value="ATOM01">ATOM01</Option>
                  <Option value="ATOM02">ATOM02</Option>
                  <Option value="ATOM03">ATOM03</Option>
                </Select>
                <Button size="sm" type="button" onClick={() => void handleSearch()}>
                  <Search className="h-4 w-4" />
                  搜索
                </Button>
              </div>
            </SectionCard>

            <SectionCard title="知识列表">
              {knowledgeList.length === 0 && !loading ? (
                <Empty description="暂无知识条目" />
              ) : (
                <Table
                  columns={knowledgeColumns}
                  dataSource={knowledgeList}
                  loading={loading}
                  pagination={{ pageSize: 10 }}
                  rowKey="id"
                />
              )}
            </SectionCard>
          </div>
        ),
      },
      {
        key: 'projects',
        label: '机器人项目',
        children: robotProjectTab,
      },
    ]

    if (!canManageKnowledge) {
      return baseItems
    }

    return [
      baseItems[0],
      {
        key: 'create',
        label: '创建知识',
        children: (
          <SectionCard title="新建知识条目">
            <Form form={form} layout="vertical" onFinish={handleCreate}>
              <div className="grid gap-4 md:grid-cols-2">
                <Form.Item label="标题" name="title" rules={[{ required: true }]}>
                  <Input placeholder="输入知识标题" />
                </Form.Item>
                <Form.Item label="类型" name="type" rules={[{ required: true }]}>
                  <Select placeholder="选择类型">
                    <Option value="solution">解决方案</Option>
                    <Option value="pattern">模式</Option>
                    <Option value="document">文档</Option>
                    <Option value="tip">技巧</Option>
                    <Option value="warning">警告</Option>
                  </Select>
                </Form.Item>
              </div>

              <Form.Item label="内容" name="content" rules={[{ required: true }]}>
                <Textarea placeholder="输入知识内容..." rows={8} />
              </Form.Item>

              <div className="grid gap-4 md:grid-cols-2">
                <Form.Item label="适用设备" name="device_model">
                  <Select allowClear placeholder="选择适用设备">
                    <Option value="ATOM01">ATOM01</Option>
                    <Option value="ATOM02">ATOM02</Option>
                    <Option value="ATOM03">ATOM03</Option>
                  </Select>
                </Form.Item>
                <Form.Item initialValue="R1" label="风险等级" name="risk_level">
                  <Select>
                    <Option value="R0">R0 - 无风险</Option>
                    <Option value="R1">R1 - 低风险</Option>
                    <Option value="R2">R2 - 中风险</Option>
                    <Option value="R3">R3 - 高风险</Option>
                  </Select>
                </Form.Item>
              </div>

              <Button type="submit">创建条目</Button>
            </Form>
          </SectionCard>
        ),
      },
      // File upload tab (teacher/admin with selected robot)
      ...(selectedRobotId !== null
        ? [
            {
              key: 'upload',
              label: '文件上传',
              children: (
                <SectionCard title="上传机器人文件">
                  <FileUploader
                    robotId={selectedRobotId}
                    onUploadComplete={() => {
                      if (selectedRobotId !== null) {
                        void loadAnalysisTasks(selectedRobotId)
                      }
                    }}
                  />
                </SectionCard>
              ),
            },
            {
              key: 'analysis',
              label: '分析状态',
              children: (
                <SectionCard title="AI 分析任务">
                  <AnalysisStatusPanel
                    tasks={analysisTasks}
                    loading={analysisLoading}
                    onTrigger={() => void handleTriggerAnalysis()}
                    canTrigger={true}
                  />
                </SectionCard>
              ),
            },
          ]
        : []),
      baseItems[1],
    ]
  }, [
    activeTab,
    analysisTasks,
    analysisLoading,
    canManageKnowledge,
    form,
    handleSearch,
    knowledgeColumns,
    knowledgeList,
    loadAnalysisTasks,
    loading,
    projects,
    projectsLoading,
    robotProjectTab,
    searchQuery,
    selectedDevice,
    selectedProjectId,
    selectedRobotId,
    uploadJobs,
  ])

  const mainContent = (
    <div className="space-y-6">
      <PageHeader
        title="知识库"
        subtitle="把文本知识、机器人项目包和运行时资产统一在同一工作台中管理"
        breadcrumb={['通用', '知识库']}
      />

      {/* Publish control bar — shown when a robot is selected */}
      {canManageKnowledge && selectedRobot ? (
        <div className="flex items-center justify-between rounded-lg border border-border-subtle bg-bg-elevated px-4 py-2">
          <div className="text-sm text-text-secondary">
            <span className="font-medium text-text-primary">{selectedRobot.brand}</span>
            {' · '}
            <span>{selectedRobot.model_name}</span>
            {selectedRobot.version ? (
              <span className="ml-1 text-text-muted">v{selectedRobot.version}</span>
            ) : null}
          </div>
          <PublishControl
            robot={selectedRobot}
            onPublish={() => void togglePublish(selectedRobot.id)}
            onToggleVisibility={() => void toggleVisibility(selectedRobot.id)}
          />
        </div>
      ) : null}

      <Tabs activeKey={activeTab} onChange={setActiveTab} items={items} />
    </div>
  )

  if (!canManageKnowledge) {
    return <div className="space-y-6">{mainContent}</div>
  }

  return (
    <div className="flex gap-0">
      <RobotSidebar
        robots={robots}
        selectedRobotId={selectedRobotId}
        loading={robotsLoading}
        onSelect={selectRobot}
        onAdd={() => setAddDialogOpen(true)}
      />
      <div className="min-w-0 flex-1 pl-6">
        {mainContent}
      </div>
      <AddRobotDialog
        open={addDialogOpen}
        onClose={() => setAddDialogOpen(false)}
        onSubmit={handleAddRobot}
        submitting={addingRobot}
      />
    </div>
  )
}

export default KnowledgePage
