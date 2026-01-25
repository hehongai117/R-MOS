/**
 * 实时监控页面（V2.3 增强版 - 三栏指挥台布局）
 * 
 * 布局：左侧传感器 + 中间 3D 视图 + 右侧关节状态
 * 功能：故障在 3D 模型上红色闪烁高亮
 */
import { Card, Row, Col, Statistic, Tag, Typography, Space, Alert } from 'antd'
import {
    RobotOutlined,
    ThunderboltOutlined,
    AimOutlined,
    WarningOutlined,
} from '@ant-design/icons'
import { useWebSocket } from '@/hooks/useWebSocket'
import RobotViewer from '@/components/Viewer3D/RobotViewer'
import { Viewer3DErrorBoundary } from '@/components/common/ErrorBoundary'

const { Title, Text } = Typography

function MonitorPage() {
    // WebSocket连接
    const { isConnected, telemetryData, error, status, isDataStale, retryCount, reconnect } = useWebSocket()

    const getStatusColor = () => {
        if (error) return 'error'
        if (isDataStale) return 'warning'
        if (isConnected) return 'success'
        return 'processing'
    }

    const getStatusText = () => {
        if (error) return 'WebSocket 已断开'
        if (isDataStale) return '数据已过期'
        if (status === 'reconnecting') return `重连中 (${retryCount}/10)`
        if (isConnected) return 'WebSocket 已连接'
        return 'WebSocket 连接中...'
    }

    // 从 telemetryData 中获取数据
    const batteryLevel = telemetryData?.sensors?.battery ?? null
    const joints = telemetryData?.joints ?? []
    const activeFaults = telemetryData?.active_faults ?? []
    const imuData = telemetryData?.sensors?.imu

    // 转换关节数据格式供 3D 组件使用
    const joints3D = joints.map((joint: any) => ({
        joint_id: joint.joint_id,
        position: joint.position,
        velocity: joint.velocity,
        torque: joint.torque,
        error_code: joint.error_code,
    }))

    return (
        <div>
            {/* 页面标题 */}
            <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Title level={3} style={{ margin: 0 }}>
                    <RobotOutlined style={{ marginRight: 8 }} />
                    实时监控
                </Title>
                <Space>
                    <Tag color={getStatusColor()}>
                        {getStatusText()}
                    </Tag>
                    {status === 'failed' && (
                        <Tag color="blue" style={{ cursor: 'pointer' }} onClick={reconnect}>
                            点击重连
                        </Tag>
                    )}
                </Space>
            </div>

            {error && (
                <Alert
                    message="连接已断开"
                    description={error || '无法连接到机器人适配器，请检查后端服务是否正常运行。'}
                    type="warning"
                    showIcon
                    style={{ marginBottom: 16 }}
                />
            )}

            {/* 三栏指挥台布局 */}
            <Row gutter={16}>
                {/* 左侧：传感器数据 */}
                <Col xs={24} lg={6}>
                    <Space direction="vertical" style={{ width: '100%' }} size="middle">
                        <Card size="small">
                            <Statistic
                                title="电池电量"
                                value={batteryLevel ?? '--'}
                                suffix={batteryLevel !== null ? '%' : ''}
                                prefix={<ThunderboltOutlined />}
                                valueStyle={{
                                    color: (batteryLevel ?? 100) > 20 ? 'var(--success-color)' : 'var(--error-color)',
                                }}
                            />
                        </Card>

                        <Card size="small">
                            <Statistic
                                title="错误状态"
                                value={activeFaults.length}
                                suffix="个"
                                prefix={<WarningOutlined />}
                                valueStyle={{
                                    color: activeFaults.length > 0 ? 'var(--error-color)' : 'var(--success-color)',
                                }}
                            />
                        </Card>

                        <Card size="small">
                            <Statistic
                                title="系统温度"
                                value={telemetryData?.sensors?.temperature ?? '--'}
                                suffix={telemetryData?.sensors?.temperature ? '°C' : ''}
                                prefix={<AimOutlined />}
                            />
                        </Card>

                        <Card size="small">
                            <Text strong>IMU 加速度</Text>
                            <div style={{ marginTop: 8 }}>
                                <Space direction="vertical" size="small">
                                    <Text>X: {imuData?.acceleration?.x?.toFixed(3) ?? '--'} m/s²</Text>
                                    <Text>Y: {imuData?.acceleration?.y?.toFixed(3) ?? '--'} m/s²</Text>
                                    <Text>Z: {imuData?.acceleration?.z?.toFixed(3) ?? '--'} m/s²</Text>
                                </Space>
                            </div>
                        </Card>
                    </Space>
                </Col>

                {/* 中间：3D 机器人视图 */}
                <Col xs={24} lg={12}>
                    <Card
                        title="3D 机器人视图"
                        size="small"
                        extra={activeFaults.length > 0 && (
                            <Tag color="error" icon={<WarningOutlined />}>
                                {activeFaults.length} 个故障
                            </Tag>
                        )}
                    >
                        <Viewer3DErrorBoundary>
                            <RobotViewer
                                height={400}
                                externalData={{
                                    joints: joints3D,
                                    connected: isConnected,
                                }}
                            />
                        </Viewer3DErrorBoundary>
                    </Card>

                    {/* 活动故障列表 */}
                    {activeFaults.length > 0 && (
                        <Card title="活动故障" size="small" style={{ marginTop: 16 }}>
                            <Space wrap>
                                {activeFaults.map((fault: string, index: number) => (
                                    <Tag key={index} color="error" icon={<WarningOutlined />}>
                                        {fault}
                                    </Tag>
                                ))}
                            </Space>
                        </Card>
                    )}
                </Col>

                {/* 右侧：关节状态 */}
                <Col xs={24} lg={6}>
                    <Card title="关节状态" size="small">
                        <Space direction="vertical" style={{ width: '100%' }} size="small">
                            {joints.length > 0 ? (
                                joints.map((joint: any, index: number) => (
                                    <Card
                                        key={joint.joint_id || index}
                                        size="small"
                                        style={{
                                            borderColor: joint.error_code ? 'var(--error-color)' : undefined,
                                            backgroundColor: joint.error_code ? 'rgba(248, 81, 73, 0.1)' : undefined,
                                        }}
                                    >
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <Text strong>{joint.joint_id || `J${index + 1}`}</Text>
                                            <Text style={{
                                                color: joint.error_code ? 'var(--error-color)' : 'var(--text-primary)',
                                                fontFamily: 'monospace',
                                            }}>
                                                {joint.position?.toFixed(4) ?? '--'}
                                            </Text>
                                        </div>
                                        {joint.error_code && (
                                            <Tag color="error" style={{ marginTop: 4 }}>
                                                {joint.error_code}
                                            </Tag>
                                        )}
                                    </Card>
                                ))
                            ) : (
                                <Text type="secondary">等待遥测数据...</Text>
                            )}
                        </Space>
                    </Card>
                </Col>
            </Row>
        </div>
    )
}

export default MonitorPage

