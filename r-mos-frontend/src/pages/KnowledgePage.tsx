// Knowledge Base Page
// P1: Knowledge Management and Search

import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Input, Tag, Modal, Form, Select, message, Row, Col, Space, Tabs } from 'antd';
import { SearchOutlined, PlusOutlined, CheckCircleOutlined, CloseCircleOutlined, SyncOutlined } from '@ant-design/icons';
import { searchKnowledge, createKnowledge, submitKnowledgeForReview, approveKnowledge, KnowledgeEntry } from '@/api/agent';

const { Option } = Select;

const KnowledgePage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('search');
  const [loading, setLoading] = useState(false);
  const [knowledgeList, setKnowledgeList] = useState<KnowledgeEntry[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDevice, setSelectedDevice] = useState<string | undefined>();
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    if (activeTab === 'search') {
      handleSearch();
    }
  }, [activeTab]);

  const handleSearch = async () => {
    setLoading(true);
    try {
      const result = await searchKnowledge({
        query: searchQuery,
        device_model: selectedDevice,
      });
      setKnowledgeList(result.results);
    } catch (error) {
      message.error('搜索失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (values: any) => {
    try {
      await createKnowledge({
        title: values.title,
        content: values.content,
        type: values.type,
        scope: values.device_model ? { device_model: [values.device_model] } : undefined,
        risk_level: values.risk_level || 'R1',
      });
      message.success('知识条目已创建');
      setCreateModalVisible(false);
      form.resetFields();
    } catch (error) {
      message.error('创建失败');
    }
  };

  const handleSubmit = async (entryId: string) => {
    try {
      await submitKnowledgeForReview(entryId);
      message.success('已提交审核');
      handleSearch();
    } catch (error) {
      message.error('提交失败');
    }
  };

  const handleApprove = async (entryId: string, decision: 'approve' | 'reject') => {
    try {
      await approveKnowledge(entryId, decision);
      message.success(`已${decision === 'approve' ? '批准' : '拒绝'}`);
      handleSearch();
    } catch (error) {
      message.error('操作失败');
    }
  };

  const columns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      width: 200,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (type: string) => <Tag>{type}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const colors: Record<string, string> = {
          DRAFT: 'default',
          PENDING: 'orange',
          APPROVED: 'green',
          REJECTED: 'red',
          EXPIRED: 'gray',
        };
        return <Tag color={colors[status]}>{status}</Tag>;
      },
    },
    {
      title: '风险等级',
      dataIndex: 'risk_level',
      key: 'risk_level',
      width: 100,
      render: (level: string) => {
        const colors: Record<string, string> = {
          R0: 'green',
          R1: 'blue',
          R2: 'orange',
          R3: 'red',
        };
        return <Tag color={colors[level]}>{level}</Tag>;
      },
    },
    {
      title: '置信度',
      key: 'confidence',
      width: 120,
      render: (_: any, record: any) => {
        const conf = record.confidence || {};
        return conf.success_rate ? `${(conf.success_rate * 100).toFixed(0)}%` : '-';
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_: any, record: KnowledgeEntry) => (
        <Space>
          {record.status === 'DRAFT' && (
            <Button size="small" icon={<SyncOutlined />} onClick={() => handleSubmit(record.id)}>
              提交
            </Button>
          )}
          {record.status === 'PENDING' && (
            <>
              <Button size="small" type="primary" icon={<CheckCircleOutlined />} onClick={() => handleApprove(record.id, 'approve')}>
                批准
              </Button>
              <Button size="small" danger icon={<CloseCircleOutlined />} onClick={() => handleApprove(record.id, 'reject')}>
                拒绝
              </Button>
            </>
          )}
        </Space>
      ),
    },
  ];

  const tabItems = [
    {
      key: 'search',
      label: '知识搜索',
      children: (
        <>
          {/* Search Bar */}
          <Card style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col flex="auto">
                <Input.Search
                  placeholder="搜索知识..."
                  enterButton={<SearchOutlined />}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onSearch={handleSearch}
                />
              </Col>
              <Col>
                <Select
                  placeholder="选择设备"
                  style={{ width: 150 }}
                  allowClear
                  value={selectedDevice}
                  onChange={setSelectedDevice}
                >
                  <Option value="ATOM01">ATOM01</Option>
                  <Option value="ATOM02">ATOM02</Option>
                  <Option value="ATOM03">ATOM03</Option>
                </Select>
              </Col>
            </Row>
          </Card>

          {/* Results Table */}
          <Table
            columns={columns}
            dataSource={knowledgeList}
            loading={loading}
            rowKey="id"
            pagination={{ pageSize: 10 }}
          />
        </>
      ),
    },
    {
      key: 'create',
      label: '创建知识',
      children: (
        <Card>
          <Form form={form} layout="vertical" onFinish={handleCreate}>
            <Form.Item name="title" label="标题" rules={[{ required: true }]}>
              <Input placeholder="输入知识标题" />
            </Form.Item>

            <Form.Item name="type" label="类型" rules={[{ required: true }]}>
              <Select placeholder="选择类型">
                <Option value="solution">解决方案</Option>
                <Option value="pattern">模式</Option>
                <Option value="document">文档</Option>
                <Option value="tip">技巧</Option>
                <Option value="warning">警告</Option>
              </Select>
            </Form.Item>

            <Form.Item name="content" label="内容" rules={[{ required: true }]}>
              <Input.TextArea rows={6} placeholder="输入知识内容..." />
            </Form.Item>

            <Form.Item name="device_model" label="适用设备">
              <Select placeholder="选择适用设备" allowClear>
                <Option value="ATOM01">ATOM01</Option>
                <Option value="ATOM02">ATOM02</Option>
                <Option value="ATOM03">ATOM03</Option>
              </Select>
            </Form.Item>

            <Form.Item name="risk_level" label="风险等级" initialValue="R1">
              <Select>
                <Option value="R0">R0 - 无风险</Option>
                <Option value="R1">R1 - 低风险</Option>
                <Option value="R2">R2 - 中风险</Option>
                <Option value="R3">R3 - 高风险</Option>
              </Select>
            </Form.Item>

            <Form.Item>
              <Button type="primary" htmlType="submit" icon={<PlusOutlined />}>
                创建
              </Button>
            </Form.Item>
          </Form>
        </Card>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px', maxWidth: 1400, margin: '0 auto' }}>
      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
      </Card>
    </div>
  );
};

export default KnowledgePage;
