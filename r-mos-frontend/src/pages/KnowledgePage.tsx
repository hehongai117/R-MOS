import { FileUp, Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Empty, Form, Select, Table, Tabs, message } from 'antd'

import {
  KnowledgeEntry,
  type KnowledgeUploadJob,
  approveKnowledge,
  createKnowledge,
  getKnowledgeUploadJob,
  searchKnowledge,
  submitKnowledgeForReview,
  uploadKnowledgeFile,
} from '@/api/agent'
import { PageHeader, SectionCard, StatusBadge } from '@/components/common'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import { Textarea } from '@/components/ui/textarea'

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

const KnowledgePage = () => {
  const [activeTab, setActiveTab] = useState('search')
  const [loading, setLoading] = useState(false)
  const [knowledgeList, setKnowledgeList] = useState<KnowledgeEntry[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedDevice, setSelectedDevice] = useState<string | undefined>()
  const [uploadBrand, setUploadBrand] = useState<string | undefined>()
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploading, setUploading] = useState(false)
  const [uploadJobs, setUploadJobs] = useState<KnowledgeUploadJob[]>([])
  const [form] = Form.useForm()

  const handleSearch = async () => {
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
  }

  useEffect(() => {
    if (activeTab === 'search') {
      void handleSearch()
    }
  }, [activeTab])

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
      void handleSearch()
    } catch {
      message.error('创建失败')
    }
  }

  const handleUpload = async (file: File) => {
    setUploading(true)
    setUploadProgress(15)
    try {
      const job = await uploadKnowledgeFile(file, uploadBrand)
      setUploadProgress(70)
      const finalJob = await getKnowledgeUploadJob(job.job_id)
      setUploadProgress(100)
      setUploadJobs((prev) => [finalJob, ...prev].slice(0, 10))
      message.success(`上传完成：${finalJob.filename ?? file.name}`)
    } catch {
      setUploadProgress(0)
      message.error('上传失败')
    } finally {
      setTimeout(() => setUploadProgress(0), 600)
      setUploading(false)
    }
    return false
  }

  const columns = [
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
            <Button size="sm" type="button" variant="secondary" onClick={() => void submitKnowledgeForReview(record.id).then(handleSearch)}>
              提交
            </Button>
          ) : null}
          {record.status === 'PENDING' ? (
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

  return (
    <div className="space-y-6">
      <PageHeader
        title="知识库"
        subtitle="知识搜索、条目创建和 PDF 上传统一到同一工作台"
        breadcrumb={['通用', '知识库']}
      />

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
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
                      columns={columns}
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
          {
            key: 'upload',
            label: '上传 PDF',
            children: (
              <div className="space-y-4">
                <SectionCard title="上传文档">
                  <div className="space-y-4">
                    <div className="flex flex-wrap gap-3">
                      <Select
                        allowClear
                        className="min-w-[180px]"
                        placeholder="选择品牌"
                        value={uploadBrand}
                        onChange={setUploadBrand}
                      >
                        <Option value="ATOM">ATOM</Option>
                        <Option value="R-MOS">R-MOS</Option>
                      </Select>
                      <label className="flex cursor-pointer items-center gap-2 rounded-md border border-dashed border-border-default bg-bg-elevated px-4 py-2 text-sm text-text-primary">
                        <FileUp className="h-4 w-4" />
                        选择 PDF
                        <input
                          accept="application/pdf"
                          className="hidden"
                          type="file"
                          onChange={(event) => {
                            const file = event.target.files?.[0]
                            if (file) {
                              void handleUpload(file)
                            }
                            event.target.value = ''
                          }}
                        />
                      </label>
                    </div>
                    {uploading || uploadProgress > 0 ? (
                      <div className="space-y-2">
                        <div className="text-xs text-text-muted">上传进度</div>
                        <Progress value={uploadProgress} />
                      </div>
                    ) : null}
                  </div>
                </SectionCard>

                <SectionCard title="文档列表">
                  {uploadJobs.length === 0 ? (
                    <Empty description="暂无上传记录" />
                  ) : (
                    <div className="space-y-3">
                      {uploadJobs.map((job) => (
                        <div
                          key={job.job_id}
                          className="flex items-center justify-between rounded-lg border border-border-subtle bg-bg-elevated px-4 py-3"
                        >
                          <div>
                            <div className="text-sm text-text-primary">{job.filename ?? job.job_id}</div>
                            <div className="mt-1 text-xs text-text-muted">
                              {job.content_type ?? 'unknown'} · {job.size_bytes ?? 0} bytes
                            </div>
                          </div>
                          <StatusBadge label={job.status} status={job.status === 'completed' ? 'success' : 'warning'} />
                        </div>
                      ))}
                    </div>
                  )}
                </SectionCard>
              </div>
            ),
          },
        ]}
      />
    </div>
  )
}

export default KnowledgePage
