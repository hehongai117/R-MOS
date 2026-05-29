/**
 * SOP列表页
 */
import React, { useEffect, useState } from 'react';
import { Button, Table, Tag, Space, message, Modal, Form, Input, Select, InputNumber } from 'antd';
import { PlusOutlined, PlayCircleOutlined, MinusCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { listSOPs, createSOP } from '@/api/sop';
import { createTask } from '@/api/task';
import { SOPListItem, SOPCreateRequest } from '@/types/sop';
import { useRobotContextStore } from '@/store/robotContextStore';

const SOPListPage: React.FC = () => {
  const navigate = useNavigate();
  const currentRobotId = useRobotContextStore((s) => s.currentRobotId);
  const currentRobot = useRobotContextStore((s) => s.currentRobot);
  const [loading, setLoading] = useState(false);
  const [sops, setSOPs] = useState<SOPListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [creating, setCreating] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

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
      navigate(`/maintenance?sop=${sop.id}`);
    } catch (error) {
      message.error('创建任务失败');
    } finally {
      setCreating(false);
    }
  };

  const handleCreateSOP = async (values: any) => {
    setSubmitting(true);
    try {
      const payload: SOPCreateRequest = {
        name: values.name,
        description: values.description,
        applicable_model: currentRobot?.model_name ?? '',
        robot_model_id: currentRobotId ?? undefined,
        category: values.category,
        difficulty_level: values.difficulty_level,
        estimated_time: values.estimated_time ? values.estimated_time * 60 : undefined,
        steps: (values.steps || []).map((step: any, index: number) => ({
          step_index: index + 1,
          title: step.title,
          description: step.description || '',
          expected_action: step.expected_action || 'manual',
          is_critical: step.is_critical ?? false,
          timeout_seconds: step.timeout_seconds ?? 300,
          allow_skip: step.allow_skip ?? false,
        })),
      };
      await createSOP(payload);
      message.success('SOP 创建成功');
      setCreateModalOpen(false);
      form.resetFields();
      fetchSOPs();
    } catch {
      message.error('创建 SOP 失败');
    } finally {
      setSubmitting(false);
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
        const colorMap: Record<string, string> = {
          L1: 'green', L2: 'cyan', L3: 'blue', L4: 'orange', L5: 'red',
          low: 'green', medium: 'orange', high: 'red',
        };
        const labelMap: Record<string, string> = {
          L1: 'L1 入门', L2: 'L2 基础', L3: 'L3 中级', L4: 'L4 高级', L5: 'L5 专家',
          low: '简单', medium: '中等', high: '困难',
        };
        return <Tag color={colorMap[level] || 'default'}>{labelMap[level] || level}</Tag>;
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
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
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

      <Modal
        title="创建 SOP"
        open={createModalOpen}
        onCancel={() => { setCreateModalOpen(false); form.resetFields(); }}
        onOk={() => form.submit()}
        confirmLoading={submitting}
        okText="创建"
        cancelText="取消"
        width={720}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleCreateSOP}>
          <Form.Item name="name" label="SOP 名称" rules={[{ required: true, message: '请输入 SOP 名称' }]}>
            <Input placeholder="例如：左膝关节润滑保养" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="SOP 简要描述" />
          </Form.Item>
          <Space style={{ width: '100%' }} size="large">
            <Form.Item name="category" label="分类">
              <Input placeholder="例如：保养" style={{ width: 200 }} />
            </Form.Item>
            <Form.Item name="difficulty_level" label="难度" rules={[{ required: true, message: '请选择难度' }]}>
              <Select placeholder="选择难度" style={{ width: 160 }}>
                <Select.Option value="low">简单</Select.Option>
                <Select.Option value="medium">中等</Select.Option>
                <Select.Option value="high">困难</Select.Option>
              </Select>
            </Form.Item>
            <Form.Item name="estimated_time" label="预估时长（分钟）">
              <InputNumber min={1} max={600} placeholder="30" style={{ width: 140 }} />
            </Form.Item>
          </Space>

          <Form.List name="steps">
            {(fields, { add, remove }) => (
              <>
                <div style={{ marginBottom: 8, fontWeight: 500 }}>步骤列表</div>
                {fields.map(({ key, name, ...restField }) => (
                  <Space key={key} style={{ display: 'flex', marginBottom: 8 }} align="start">
                    <Form.Item {...restField} name={[name, 'title']} rules={[{ required: true, message: '步骤标题' }]}>
                      <Input placeholder={`步骤 ${name + 1} 标题`} style={{ width: 200 }} />
                    </Form.Item>
                    <Form.Item {...restField} name={[name, 'description']}>
                      <Input placeholder="步骤描述" style={{ width: 300 }} />
                    </Form.Item>
                    <MinusCircleOutlined onClick={() => remove(name)} style={{ marginTop: 8 }} />
                  </Space>
                ))}
                <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />}>
                  添加步骤
                </Button>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>
    </div>
  );
};

export default SOPListPage;
