/**
 * 故障案例管理页面
 */
import React, { useEffect, useState } from 'react';
import { Table, Button, Tag, Space, message } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { listFaultCases } from '@/api/fault';
import { FaultCase } from '@/types/fault';

const FaultManagePage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [faults, setFaults] = useState<FaultCase[]>([]);

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

  const columns = [
    {
      title: '故障代码',
      dataIndex: 'fault_code',
      key: 'fault_code',
    },
    {
      title: '故障名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      render: (severity: string) => {
        const colorMap = { low: 'green', medium: 'orange', high: 'red' };
        return <Tag color={colorMap[severity]}>{severity}</Tag>;
      },
    },
    {
      title: '推荐SOP',
      dataIndex: 'recommended_sop_id',
      key: 'recommended_sop_id',
      render: (sopId: number) => sopId || '未关联',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: FaultCase) => (
        <Space>
          <Button icon={<EditOutlined />} size="small">
            编辑
          </Button>
          <Button icon={<DeleteOutlined />} size="small" danger>
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2>故障案例库管理</h2>
        <Button type="primary" icon={<PlusOutlined />}>
          添加故障案例
        </Button>
      </div>
      
      <Table
        columns={columns}
        dataSource={faults}
        rowKey="id"
        loading={loading}
      />
    </div>
  );
};

export default FaultManagePage;
