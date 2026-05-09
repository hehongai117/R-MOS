/**
 * SOP列表页
 */
import React, { useEffect, useState } from 'react';
import { Button, Table, Tag, Space, message } from 'antd';
import { PlusOutlined, PlayCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { listSOPs } from '@/api/sop';
import { createTask } from '@/api/task';
import { SOPListItem } from '@/types/sop';
import { useRobotContextStore } from '@/store/robotContextStore';

const SOPListPage: React.FC = () => {
  const navigate = useNavigate();
  const currentRobotId = useRobotContextStore((s) => s.currentRobotId);
  const [loading, setLoading] = useState(false);
  const [sops, setSOPs] = useState<SOPListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [creating, setCreating] = useState(false);

  const fetchSOPs = async () => {
    setLoading(true);
    try {
      const response = await listSOPs({
        skip: (page - 1) * pageSize,
        limit: pageSize,
        robot_model_id: currentRobotId ?? undefined,
      });
      setSOPs(response.items);
      setTotal(response.total);
    } catch (error) {
      message.error('加载SOP列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSOPs();
  }, [page, pageSize, currentRobotId]);

  const handleCreateTask = async (sop: SOPListItem) => {
    setCreating(true);
    try {
      // 调用 API 创建任务
      const task = await createTask({
        title: `${sop.name} - 训练任务`,
        sop_id: sop.id,
      });
      message.success('任务创建成功');
      // 导航到任务执行页
      navigate(`/tasks/${task.id}`);
    } catch (error) {
      message.error('创建任务失败');
    } finally {
      setCreating(false);
    }
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: 'SOP名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      render: (category: string) => <Tag>{category || '未分类'}</Tag>,
    },
    {
      title: '难度',
      dataIndex: 'difficulty_level',
      key: 'difficulty_level',
      render: (level: string) => {
        const colorMap: Record<string, string> = { low: 'green', medium: 'orange', high: 'red' };
        return <Tag color={colorMap[level] || 'default'}>{level}</Tag>;
      },
    },
    {
      title: '步骤数',
      dataIndex: 'step_count',
      key: 'step_count',
    },
    {
      title: '预估时长',
      dataIndex: 'estimated_time',
      key: 'estimated_time',
      render: (seconds: number) => `${Math.round(seconds / 60)}分钟`,
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: SOPListItem) => (
        <Space>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            loading={creating}
            onClick={() => handleCreateTask(record)}
          >
            开始训练
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2>标准操作流程（SOP）</h2>
        <Button type="primary" icon={<PlusOutlined />}>
          创建SOP
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={sops}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          pageSize: pageSize,
          total: total,
          onChange: (page, pageSize) => {
            setPage(page);
            setPageSize(pageSize);
          },
        }}
      />
    </div>
  );
};

export default SOPListPage;
