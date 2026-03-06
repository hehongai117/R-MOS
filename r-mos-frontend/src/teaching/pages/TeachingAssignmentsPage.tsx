import { useEffect, useMemo, useState } from 'react'
import { Empty, InputNumber, Table, Tabs, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useNavigate } from 'react-router-dom'

import { listAssignmentAttempts } from '@/api/teaching'
import { PageHeader, SectionCard, StatusBadge } from '@/components/common'
import { Button } from '@/components/ui/button'
import { useTeachingStore } from '@/teaching/store/teachingStore'
import { formatTeachingError } from '@/teaching/utils/api'
import type { Assignment, AssignmentAttempt } from '@/types/teaching'

function statusTone(status: string) {
  if (status === 'in_progress') return 'active'
  if (status === 'completed' || status === 'graded') return 'success'
  return 'idle'
}

const TeachingAssignmentsPage = () => {
  const navigate = useNavigate()
  const { assignments, loadAssignments, startAttempt, loading, error, clearError } = useTeachingStore()

  const [studentId, setStudentId] = useState<number>(1)
  const [teacherLoading, setTeacherLoading] = useState(false)
  const [selectedAssignment, setSelectedAssignment] = useState<Assignment | null>(null)
  const [attempts, setAttempts] = useState<AssignmentAttempt[]>([])

  useEffect(() => {
    void loadAssignments().catch(() => {})
  }, [loadAssignments])

  useEffect(() => {
    if (error) {
      message.error(error)
      clearError()
    }
  }, [clearError, error])

  const handleStart = async (assignment: Assignment) => {
    if (!studentId || studentId <= 0) {
      message.error('请输入有效的学生编号')
      return
    }
    try {
      const attempt = await startAttempt(assignment, studentId)
      if (attempt) {
        navigate(`/teaching/attempts/${attempt.id}`)
      }
    } catch {
      // 错误交给 store 统一提示
    }
  }

  const handleViewAttempts = async (assignment: Assignment) => {
    setTeacherLoading(true)
    setSelectedAssignment(assignment)
    try {
      const data = await listAssignmentAttempts(assignment.id)
      setAttempts(data)
    } catch (err) {
      message.error(formatTeachingError(err, '加载尝试列表失败'))
    } finally {
      setTeacherLoading(false)
    }
  }

  const assignmentColumns: ColumnsType<Assignment> = useMemo(
    () => [
      { title: '作业标题', dataIndex: 'title', key: 'title' },
      { title: '作业编号', dataIndex: 'id', key: 'id', width: 120 },
      {
        title: 'SOP',
        dataIndex: 'sopId',
        key: 'sopId',
        width: 120,
        render: (value: number | null | undefined) => value ?? '未配置',
      },
      {
        title: '操作',
        key: 'actions',
        width: 180,
        render: (_: unknown, record: Assignment) => (
          <Button size="sm" type="button" onClick={() => void handleStart(record)}>
            开始
          </Button>
        ),
      },
    ],
    [studentId],
  )

  const teacherColumns: ColumnsType<Assignment> = useMemo(
    () => [
      { title: '作业标题', dataIndex: 'title', key: 'title' },
      { title: '作业编号', dataIndex: 'id', key: 'id', width: 120 },
      {
        title: '操作',
        key: 'actions',
        width: 200,
        render: (_: unknown, record: Assignment) => (
          <Button
            size="sm"
            type="button"
            variant="secondary"
            onClick={() => void handleViewAttempts(record)}
          >
            查看提交
          </Button>
        ),
      },
    ],
    [teacherLoading],
  )

  const attemptColumns: ColumnsType<AssignmentAttempt> = [
    { title: '尝试编号', dataIndex: 'id', key: 'id', width: 120 },
    { title: '学生编号', dataIndex: 'studentId', key: 'studentId', width: 120 },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 140,
      render: (value: string) => <StatusBadge label={value} status={statusTone(value)} />,
    },
    {
      title: '得分',
      dataIndex: 'score',
      key: 'score',
      width: 120,
      render: (value: number | null | undefined) => value ?? '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 220,
      render: (_: unknown, record: AssignmentAttempt) => (
        <div className="flex gap-2">
          <Button size="sm" type="button" variant="secondary" onClick={() => navigate(`/teaching/attempts/${record.id}`)}>
            进入尝试
          </Button>
          <Button size="sm" type="button" variant="outline" onClick={() => navigate(`/teaching/attempts/${record.id}/evidence`)}>
            查看证据
          </Button>
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="教学作业中心"
        subtitle="学生可开始作业，教师可查看提交与证据摘要"
        breadcrumb={['教学域', '作业中心']}
      />

      <Tabs
        items={[
          {
            key: 'student',
            label: '学生入口',
            children: (
              <SectionCard title="学生作业列表">
                <div className="mb-4 flex flex-wrap items-center gap-3">
                  <span className="text-sm text-text-secondary">学生编号</span>
                  <InputNumber min={1} value={studentId} onChange={(value) => setStudentId(value ?? 1)} />
                  <Button size="sm" type="button" variant="secondary" onClick={() => void loadAssignments().catch(() => {})}>
                    刷新
                  </Button>
                </div>
                <Table rowKey="id" loading={loading} columns={assignmentColumns} dataSource={assignments} pagination={{ pageSize: 8 }} />
              </SectionCard>
            ),
          },
          {
            key: 'teacher',
            label: '教师视图',
            children: (
              <div className="grid gap-4 xl:grid-cols-[1fr_420px]">
                <SectionCard title="作业列表">
                  <Table rowKey="id" loading={loading} columns={teacherColumns} dataSource={assignments} pagination={{ pageSize: 8 }} />
                </SectionCard>
                <SectionCard title={selectedAssignment ? `「${selectedAssignment.title}」提交列表` : '提交列表'}>
                  {attempts.length === 0 ? (
                    <Empty description="请选择左侧作业查看提交" />
                  ) : (
                    <Table rowKey="id" columns={attemptColumns} dataSource={attempts} pagination={{ pageSize: 6 }} />
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

export default TeachingAssignmentsPage
