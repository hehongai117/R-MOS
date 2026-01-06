/**
 * 首页仪表盘
 * 展示系统概览、快速入口和系统状态
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Card,
    Row,
    Col,
    Statistic,
    Button,
    Typography,
    Space,
    Tag,
    List,
    Progress,
    Skeleton,
} from 'antd';
import {
    FileTextOutlined,
    PlayCircleOutlined,
    CheckCircleOutlined,
    WarningOutlined,
    RobotOutlined,
    ThunderboltOutlined,
    ClockCircleOutlined,
    ArrowRightOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;

// 模拟统计数据类型
interface DashboardStats {
    totalSOPs: number;
    totalTasks: number;
    completedTasks: number;
    passRate: number;
    activeFaults: number;
    systemStatus: 'online' | 'offline' | 'error';
}

// 快捷入口配置
const quickActions = [
    {
        key: 'sops',
        title: 'SOP列表',
        description: '查看和管理标准操作流程',
        icon: <FileTextOutlined style={{ fontSize: 32, color: '#1890ff' }} />,
        path: '/sops',
        color: '#e6f7ff',
    },
    {
        key: 'monitor',
        title: '实时监控',
        description: '查看机器人实时状态和遥测数据',
        icon: <RobotOutlined style={{ fontSize: 32, color: '#52c41a' }} />,
        path: '/monitor',
        color: '#f6ffed',
    },
    {
        key: 'faults',
        title: '故障管理',
        description: '管理故障案例库和诊断流程',
        icon: <WarningOutlined style={{ fontSize: 32, color: '#faad14' }} />,
        path: '/admin/faults',
        color: '#fffbe6',
    },
];

const HomePage: React.FC = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [stats, setStats] = useState<DashboardStats | null>(null);

    useEffect(() => {
        // 模拟加载统计数据
        const loadStats = async () => {
            try {
                // TODO: 替换为实际 API 调用
                await new Promise(resolve => setTimeout(resolve, 500));
                setStats({
                    totalSOPs: 3,
                    totalTasks: 2,
                    completedTasks: 1,
                    passRate: 85,
                    activeFaults: 0,
                    systemStatus: 'online',
                });
            } finally {
                setLoading(false);
            }
        };
        loadStats();
    }, []);

    const getStatusTag = (status: string) => {
        const statusMap: Record<string, { color: string; text: string }> = {
            online: { color: 'success', text: '在线' },
            offline: { color: 'default', text: '离线' },
            error: { color: 'error', text: '错误' },
        };
        const config = statusMap[status] || { color: 'default', text: status };
        return <Tag color={config.color}>{config.text}</Tag>;
    };

    return (
        <div className="fade-in">
            {/* 页面标题 */}
            <div style={{ marginBottom: 24 }}>
                <Title level={2} style={{ margin: 0 }}>
                    欢迎使用 R-MOS
                </Title>
                <Text type="secondary">
                    机器人维护操作训练系统 - 让机器人维护培训更高效
                </Text>
            </div>

            {/* 统计卡片 */}
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
                <Col xs={24} sm={12} lg={6}>
                    <Card>
                        {loading ? (
                            <Skeleton active paragraph={false} />
                        ) : (
                            <Statistic
                                title="SOP 数量"
                                value={stats?.totalSOPs || 0}
                                prefix={<FileTextOutlined />}
                                valueStyle={{ color: '#1890ff' }}
                            />
                        )}
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                    <Card>
                        {loading ? (
                            <Skeleton active paragraph={false} />
                        ) : (
                            <Statistic
                                title="完成任务"
                                value={stats?.completedTasks || 0}
                                suffix={`/ ${stats?.totalTasks || 0}`}
                                prefix={<CheckCircleOutlined />}
                                valueStyle={{ color: '#52c41a' }}
                            />
                        )}
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                    <Card>
                        {loading ? (
                            <Skeleton active paragraph={false} />
                        ) : (
                            <Statistic
                                title="通过率"
                                value={stats?.passRate || 0}
                                suffix="%"
                                prefix={<ThunderboltOutlined />}
                                valueStyle={{ color: '#faad14' }}
                            />
                        )}
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                    <Card>
                        {loading ? (
                            <Skeleton active paragraph={false} />
                        ) : (
                            <div>
                                <Text type="secondary">系统状态</Text>
                                <div style={{ marginTop: 8 }}>
                                    <Space>
                                        <RobotOutlined style={{ fontSize: 24 }} />
                                        {getStatusTag(stats?.systemStatus || 'offline')}
                                    </Space>
                                </div>
                                <Text type="secondary" style={{ fontSize: 12 }}>
                                    活动故障: {stats?.activeFaults || 0}
                                </Text>
                            </div>
                        )}
                    </Card>
                </Col>
            </Row>

            {/* 快捷入口 */}
            <Title level={4} style={{ marginBottom: 16 }}>
                <PlayCircleOutlined style={{ marginRight: 8 }} />
                快速开始
            </Title>
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
                {quickActions.map(action => (
                    <Col xs={24} sm={12} lg={8} key={action.key}>
                        <Card
                            hoverable
                            onClick={() => navigate(action.path)}
                            style={{ height: '100%' }}
                            bodyStyle={{
                                display: 'flex',
                                flexDirection: 'column',
                                height: '100%',
                            }}
                        >
                            <div
                                style={{
                                    width: 64,
                                    height: 64,
                                    borderRadius: 8,
                                    background: action.color,
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    marginBottom: 16,
                                }}
                            >
                                {action.icon}
                            </div>
                            <Title level={5} style={{ margin: 0, marginBottom: 8 }}>
                                {action.title}
                            </Title>
                            <Text type="secondary" style={{ flex: 1 }}>
                                {action.description}
                            </Text>
                            <div style={{ marginTop: 16 }}>
                                <Button type="link" style={{ padding: 0 }}>
                                    进入 <ArrowRightOutlined />
                                </Button>
                            </div>
                        </Card>
                    </Col>
                ))}
            </Row>

            {/* 最近活动 */}
            <Row gutter={[16, 16]}>
                <Col xs={24} lg={12}>
                    <Card
                        title={
                            <Space>
                                <ClockCircleOutlined />
                                最近训练任务
                            </Space>
                        }
                        extra={
                            <Button type="link" onClick={() => navigate('/sops')}>
                                查看全部
                            </Button>
                        }
                    >
                        <List
                            size="small"
                            dataSource={[
                                { title: '日常巡检 - 训练任务', status: 'completed', score: 85 },
                                { title: '关节校准SOP - 训练任务', status: 'in_progress', score: null },
                            ]}
                            renderItem={item => (
                                <List.Item
                                    actions={[
                                        item.status === 'completed' ? (
                                            <Tag color="success">{item.score}分</Tag>
                                        ) : (
                                            <Tag color="processing">进行中</Tag>
                                        ),
                                    ]}
                                >
                                    <List.Item.Meta
                                        title={item.title}
                                        description={
                                            item.status === 'completed'
                                                ? '已完成'
                                                : '正在进行中...'
                                        }
                                    />
                                </List.Item>
                            )}
                            locale={{ emptyText: '暂无训练记录' }}
                        />
                    </Card>
                </Col>
                <Col xs={24} lg={12}>
                    <Card
                        title={
                            <Space>
                                <ThunderboltOutlined />
                                技能提升进度
                            </Space>
                        }
                    >
                        <Space direction="vertical" style={{ width: '100%' }} size="middle">
                            <div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                                    <Text>日常维护</Text>
                                    <Text type="secondary">3/5 完成</Text>
                                </div>
                                <Progress percent={60} status="active" />
                            </div>
                            <div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                                    <Text>故障诊断</Text>
                                    <Text type="secondary">1/3 完成</Text>
                                </div>
                                <Progress percent={33} />
                            </div>
                            <div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                                    <Text>高级校准</Text>
                                    <Text type="secondary">0/2 完成</Text>
                                </div>
                                <Progress percent={0} />
                            </div>
                        </Space>
                    </Card>
                </Col>
            </Row>
        </div>
    );
};

export default HomePage;
