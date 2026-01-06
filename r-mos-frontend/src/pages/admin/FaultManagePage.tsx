/**
 * 故障案例管理页面 (V2.3 增强版)
 * 支持完整 CRUD 操作
 */
import React, { useEffect, useState } from 'react';
import {
  Table,
  Button,
  Tag,
  Space,
  message,
  Modal,
  Form,
  Input,
  Select,
  Popconfirm,
  Typography,
  Card,
  Descriptions,
  Drawer,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  WarningOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import {
  listFaultCases,
  getFaultCase,
  createFaultCase,
  updateFaultCase,
  deleteFaultCase,
} from '@/api/fault';
import { FaultCase, FaultCaseCreateRequest, FaultCaseUpdateRequest } from '@/types/fault';

const { Title, Text } = Typography;
const { TextArea } = Input;

const FaultManagePage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [faults, setFaults] = useState<FaultCase[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingFault, setEditingFault] = useState<FaultCase | null>(null);
  const [viewingFault, setViewingFault] = useState<FaultCase | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  // 获取故障案例列表
  const fetchFaults = async () => {
    setLoading(true);
    try {
      const data = await listFaultCases();
      setFaults(data);
    } catch (error) {
      message.error('加载故障案例失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFaults();
  }, []);

  // 打开新建对话框
  const handleCreate = () => {
    setEditingFault(null);
    form.resetFields();
    setModalOpen(true);
  };

  // 打开编辑对话框
  const handleEdit = (fault: FaultCase) => {
    setEditingFault(fault);
    form.setFieldsValue({
      fault_code: fault.fault_code,
      name: fault.name,
      description: fault.description,
      category: fault.category,
      severity: fault.severity,
      affected_parts: fault.affected_parts?.join(', '),
      symptoms: fault.symptoms?.join('\n'),
      diagnosis_steps: fault.diagnosis_steps?.join('\n'),
      solution_steps: fault.solution_steps?.join('\n'),
    });
    setModalOpen(true);
  };

  // 查看详情
  const handleView = async (fault: FaultCase) => {
    try {
      const detail = await getFaultCase(fault.id);
      setViewingFault(detail);
      setDrawerOpen(true);
    } catch (error) {
      message.error('获取详情失败');
    }
  };

  // 删除故障案例
  const handleDelete = async (id: number) => {
    try {
      await deleteFaultCase(id);
      message.success('删除成功');
      fetchFaults();
    } catch (error) {
      message.error('删除失败');
    }
  };

  // 提交表单
  const handleSubmit = async (values: any) => {
    setSubmitting(true);
    try {
      // 处理数组字段
      const data: FaultCaseCreateRequest | FaultCaseUpdateRequest = {
        fault_code: values.fault_code,
        name: values.name,
        description: values.description,
        category: values.category,
        severity: values.severity,
        affected_parts: values.affected_parts
          ? values.affected_parts.split(',').map((s: string) => s.trim()).filter(Boolean)
          : undefined,
        symptoms: values.symptoms
          ? values.symptoms.split('\n').map((s: string) => s.trim()).filter(Boolean)
          : undefined,
        diagnosis_steps: values.diagnosis_steps
          ? values.diagnosis_steps.split('\n').map((s: string) => s.trim()).filter(Boolean)
          : undefined,
        solution_steps: values.solution_steps
          ? values.solution_steps.split('\n').map((s: string) => s.trim()).filter(Boolean)
          : undefined,
      };

      if (editingFault) {
        await updateFaultCase(editingFault.id, data as FaultCaseUpdateRequest);
        message.success('更新成功');
      } else {
        await createFaultCase(data as FaultCaseCreateRequest);
        message.success('创建成功');
      }
      setModalOpen(false);
      fetchFaults();
    } catch (error) {
      message.error(editingFault ? '更新失败' : '创建失败');
    } finally {
      setSubmitting(false);
    }
  };

  // 表格列定义
  const columns = [
    {
      title: '故障代码',
      dataIndex: 'fault_code',
      key: 'fault_code',
      width: 140,
      render: (code: string) => <Text code>{code}</Text>,
    },
    {
      title: '故障名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      render: (category: string) => category || '-',
    },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (severity: string) => {
        const config: Record<string, { color: string; text: string }> = {
          low: { color: 'success', text: '低' },
          medium: { color: 'warning', text: '中' },
          high: { color: 'error', text: '高' },
        };
        const c = config[severity] || { color: 'default', text: severity };
        return <Tag color={c.color}>{c.text}</Tag>;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => new Date(date).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      render: (_: any, record: FaultCase) => (
        <Space size="small">
          <Button
            type="text"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleView(record)}
          />
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          />
          <Popconfirm
            title="确定删除此故障案例？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
            />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div className="fade-in">
      {/* 页面标题 */}
      <div className="flex-between mb-16">
        <Title level={3} style={{ margin: 0 }}>
          <WarningOutlined style={{ marginRight: 8 }} />
          故障案例库管理
        </Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchFaults}>
            刷新
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            添加故障案例
          </Button>
        </Space>
      </div>

      {/* 数据表格 */}
      <Card>
        <Table
          columns={columns}
          dataSource={faults}
          rowKey="id"
          loading={loading}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
        />
      </Card>

      {/* 新建/编辑对话框 */}
      <Modal
        title={editingFault ? '编辑故障案例' : '新建故障案例'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        footer={null}
        width={640}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{ severity: 'medium' }}
        >
          <Form.Item
            name="fault_code"
            label="故障代码"
            rules={[{ required: true, message: '请输入故障代码' }]}
          >
            <Input
              placeholder="例如: E001_OVERHEAT"
              disabled={!!editingFault}
            />
          </Form.Item>

          <Form.Item
            name="name"
            label="故障名称"
            rules={[{ required: true, message: '请输入故障名称' }]}
          >
            <Input placeholder="例如: 电机过热" />
          </Form.Item>

          <Form.Item
            name="description"
            label="故障描述"
            rules={[{ required: true, message: '请输入故障描述' }]}
          >
            <TextArea rows={3} placeholder="详细描述故障现象和原因" />
          </Form.Item>

          <Space size="middle" style={{ display: 'flex' }}>
            <Form.Item name="category" label="分类" style={{ flex: 1 }}>
              <Input placeholder="例如: 温度异常" />
            </Form.Item>
            <Form.Item name="severity" label="严重程度" style={{ flex: 1 }}>
              <Select>
                <Select.Option value="low">低</Select.Option>
                <Select.Option value="medium">中</Select.Option>
                <Select.Option value="high">高</Select.Option>
              </Select>
            </Form.Item>
          </Space>

          <Form.Item name="affected_parts" label="受影响部件">
            <Input placeholder="用逗号分隔，例如: knee_right, hip_left" />
          </Form.Item>

          <Form.Item name="symptoms" label="故障症状">
            <TextArea rows={2} placeholder="每行一个症状" />
          </Form.Item>

          <Form.Item name="diagnosis_steps" label="诊断步骤">
            <TextArea rows={3} placeholder="每行一个步骤" />
          </Form.Item>

          <Form.Item name="solution_steps" label="解决步骤">
            <TextArea rows={3} placeholder="每行一个步骤" />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setModalOpen(false)}>取消</Button>
              <Button type="primary" htmlType="submit" loading={submitting}>
                {editingFault ? '更新' : '创建'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 详情抽屉 */}
      <Drawer
        title="故障案例详情"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={500}
      >
        {viewingFault && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="故障代码">
              <Text code>{viewingFault.fault_code}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="故障名称">
              {viewingFault.name}
            </Descriptions.Item>
            <Descriptions.Item label="严重程度">
              <Tag
                color={
                  viewingFault.severity === 'high'
                    ? 'error'
                    : viewingFault.severity === 'medium'
                      ? 'warning'
                      : 'success'
                }
              >
                {viewingFault.severity}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="分类">
              {viewingFault.category || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="描述">
              {viewingFault.description}
            </Descriptions.Item>
            <Descriptions.Item label="受影响部件">
              {viewingFault.affected_parts?.length ? (
                <Space wrap>
                  {viewingFault.affected_parts.map((part) => (
                    <Tag key={part}>{part}</Tag>
                  ))}
                </Space>
              ) : (
                '-'
              )}
            </Descriptions.Item>
            <Descriptions.Item label="故障症状">
              {viewingFault.symptoms?.length ? (
                <ul style={{ margin: 0, paddingLeft: 16 }}>
                  {viewingFault.symptoms.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              ) : (
                '-'
              )}
            </Descriptions.Item>
            <Descriptions.Item label="诊断步骤">
              {viewingFault.diagnosis_steps?.length ? (
                <ol style={{ margin: 0, paddingLeft: 16 }}>
                  {viewingFault.diagnosis_steps.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ol>
              ) : (
                '-'
              )}
            </Descriptions.Item>
            <Descriptions.Item label="解决步骤">
              {viewingFault.solution_steps?.length ? (
                <ol style={{ margin: 0, paddingLeft: 16 }}>
                  {viewingFault.solution_steps.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ol>
              ) : (
                '-'
              )}
            </Descriptions.Item>
            <Descriptions.Item label="创建时间">
              {new Date(viewingFault.created_at).toLocaleString('zh-CN')}
            </Descriptions.Item>
            <Descriptions.Item label="更新时间">
              {new Date(viewingFault.updated_at).toLocaleString('zh-CN')}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </div>
  );
};

export default FaultManagePage;
