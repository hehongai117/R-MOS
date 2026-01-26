/**
 * 教学作业列表页面（学生与教师）
 */
import { useEffect, useMemo, useState } from 'react'
import { Button, Drawer, InputNumber, message, Space, Table, Tabs, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useNavigate } from 'react-router-dom'
import { useTeachingStore } from '@/teaching/store/teachingStore'
import { listAssignmentAttempts } from '@/api/teaching'
import type { Assignment, AssignmentAttempt } from '@/types/teaching'
import { formatTeachingError } from '@/teaching/utils/api'

const { Title, Text } = Typography

const statusColorMap: Record<string, string> = {
  in_progress: 'blue',
  completed: 'green',
  graded: 'purple',
  abandoned: 'default',
}

const statusLabelMap: Record<string, string> = {
  in_progress: '进行中',
  completed: '已完成',
  graded: '已评分',
  abandoned: '已放弃',
}

const TeachingAssignmentsPage = () => {
  const navigate = useNavigate()
  const {
    assignments,
    loadAssignments,
    startAttempt,
    loading,
    error,
    clearError,
  } = useTeachingStore()

  const [studentId, setStudentId] = useState<number>(1)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [teacherLoading, setTeacherLoading] = useState(false)
  const [selectedAssignment, setSelectedAssignment] = useState<Assignment | null>(null)
  const [attempts, setAttempts] = useState<AssignmentAttempt[]>([])

  useEffect(() => {
    loadAssignments().catch(() => {})
  }, [loadAssignments])

  useEffect(() => {
    if (error) {
      message.error(error)
      clearError()
    }
  }, [error, clearError])

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
    } catch (err) {
      // 错误提示由 store 统一处理
    }
  }

  const handleViewAttempts = async (assignment: Assignment) => {
    setTeacherLoading(true)
    setSelectedAssignment(assignment)
    try {
      const data = await listAssignmentAttempts(assignment.id)
      setAttempts(data)
      setDrawerOpen(true)
    } catch (err) {
      message.error(formatTeachingError(err, '加载尝试列表失败'))
    } finally {
      setTeacherLoading(false)
    }
  }

  const assignmentColumns: ColumnsType<Assignment> = useMemo(() => ([
    {
      title: '作业标题',
      dataIndex: 'title',
      key: 'title',
    },
    {
      title: '作业编号',
      dataIndex: 'id',
      key: 'id',
      width: 120,
    },
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
      width: 220,
      render: (_: unknown, record: Assignment) => (
        <Space>
          <Button type="primary" onClick={() => handleStart(record)}>
            开始
          </Button>
        </Space>
      ),
    },
  ]), [studentId])

  const teacherColumns: ColumnsType<Assignment> = useMemo(() => ([
    {
      title: '作业标题',
      dataIndex: 'title',
      key: 'title',
    },
    {
      title: '作业编号',
      dataIndex: 'id',
      key: 'id',
      width: 120,
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: unknown, record: Assignment) => (
        <Button onClick={() => handleViewAttempts(record)} loading={teacherLoading}>
          查看提交
        </Button>
      ),
    },
  ]), [teacherLoading])

  const attemptColumns: ColumnsType<AssignmentAttempt> = [
    {
      title: '尝试编号',
      dataIndex: 'id',
      key: 'id',
      width: 120,
    },
    {
      title: '学生编号',
      dataIndex: 'studentId',
      key: 'studentId',
      width: 120,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (value: string) => (
        <Tag color={statusColorMap[value] || 'default'}>
          {statusLabelMap[value] || value}
        </Tag>
      ),
    },
    {
      title: '得分',
      dataIndex: 'score',
      key: 'score',
      width: 120,
      render: (value: number | null | undefined) => value ?? '-'
    },
    {
      title: '操作',
      key: 'action',
      width: 160,
      render: (_: unknown, record: AssignmentAttempt) => (
        <Space>
          <Button type="link" onClick={() => navigate(`/teaching/attempts/${record.id}`)}>
            进入尝试
          </Button>
          <Button type="link" onClick={() => navigate(`/teaching/attempts/${record.id}/evidence`)}>
            查看证据
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Title level={3} style={{ marginBottom: 8 }}>教学作业中心</Title>
      <Text type="secondary">学生可开始作业，教师可查看提交与证据摘要</Text>

      <Tabs
        style={{ marginTop: 16 }}
        items={[
          {
            key: 'student',
            label: '学生入口',
            children: (
              <div>
                <Space style={{ marginBottom: 16 }}>
                  <span>学生编号：</span>
                  <InputNumber
                    min={1}
                    value={studentId}
                    onChange={(value) => setStudentId(value ?? 1)}
                  />
                  <Button onClick={() => loadAssignments().catch(() => {})}>
                    刷新
                  </Button>
                </Space>
                <Table
                  rowKey="id"
                  loading={loading}
                  columns={assignmentColumns}
                  dataSource={assignments}
                  pagination={{ pageSize: 8 }}
                />
              </div>
            ),
          },
          {
            key: 'teacher',
            label: '教师视图',
            children: (
              <div>
                <Table
                  rowKey="id"
                  loading={loading}
                  columns={teacherColumns}
                  dataSource={assignments}
                  pagination={{ pageSize: 8 }}
                />
              </div>
            ),
          },
        ]}
      />

      <Drawer
        title={selectedAssignment ? `作业「${selectedAssignment.title}」的提交` : '提交列表'}
        width={720}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      >
        <Table
          rowKey="id"
          columns={attemptColumns}
          dataSource={attempts}
          pagination={{ pageSize: 6 }}
        />
      </Drawer>
    </div>
  )
}

export default TeachingAssignmentsPage
