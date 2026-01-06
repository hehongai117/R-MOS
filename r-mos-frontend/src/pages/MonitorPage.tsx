/**
 * 实时监控页面
 * 展示机器人遥测数据和状态
 */
import { Card, Row, Col, Statistic, Tag, Typography, Space, Alert } from 'antd'
import {
    RobotOutlined,
    ThunderboltOutlined,
    AimOutlined,
    WarningOutlined,
} from '@ant-design/icons'
import { useWebSocket } from '@/hooks/useWebSocket'

const { Title, Text } = Typography

function MonitorPage() {
    // WebSocket连接 - 使用正确的返回值
    const { isConnected, telemetryData, error } = useWebSocket()

    const getStatusColor = () => {
        if (error) return 'error'
        if (isConnected) return 'success'
        return 'processing'
    }

    const getStatusText = () => {
        if (error) return 'WebSocket 已断开'
        if (isConnected) return 'WebSocket 已连接'
        return 'WebSocket 连接中...'
    }

    // 从 telemetryData 中获取数据
    const batteryLevel = telemetryData?.sensors?.battery ?? null
    const joints = telemetryData?.joints ?? []
    const activeFaults = telemetryData?.active_faults ?? []

    // 计算 IMU 位置（如果有）
    const imuData = telemetryData?.sensors?.imu

    return (
        <div>
            <div style={{ marginBottom: 24, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Title level={3} style={{ margin: 0 }}>
                    <RobotOutlined style={{ marginRight: 8 }} />
                    实时监控
                </Title>
                <Tag color={getStatusColor()}>
                    {getStatusText()}
                </Tag>
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

            <Row gutter={[16, 16]}>
                {/* 电池状态 */}
                <Col xs={24} sm={12} lg={6}>
                    <Card>
                        <Statistic
                            title="电池电量"
                            value={batteryLevel ?? '--'}
                            suffix={batteryLevel !== null ? '%' : ''}
                            prefix={<ThunderboltOutlined />}
                            valueStyle={{
                                color: (batteryLevel ?? 100) > 20 ? '#3f8600' : '#cf1322',
                            }}
                        />
                    </Card>
                </Col>

                {/* 活动故障数 */}
                <Col xs={24} sm={12} lg={6}>
                    <Card>
                        <Statistic
                            title="错误状态"
                            value={activeFaults.length}
                            suffix="个"
                            prefix={<WarningOutlined />}
                            valueStyle={{
                                color: activeFaults.length > 0 ? '#cf1322' : '#3f8600',
                            }}
                        />
                    </Card>
                </Col>

                {/* 温度 */}
                <Col xs={24} sm={12} lg={6}>
                    <Card>
                        <Statistic
                            title="系统温度"
                            value={telemetryData?.sensors?.temperature ?? '--'}
                            suffix={telemetryData?.sensors?.temperature ? '°C' : ''}
                            prefix={<AimOutlined />}
                        />
                    </Card>
                </Col>

                {/* IMU 数据 */}
                <Col xs={24} sm={12} lg={6}>
                    <Card>
                        <Text strong>IMU 加速度</Text>
                        <div style={{ marginTop: 8 }}>
                            <Space direction="vertical" size="small">
                                <Text>X: {imuData?.acceleration?.x?.toFixed(3) ?? '--'} m/s²</Text>
                                <Text>Y: {imuData?.acceleration?.y?.toFixed(3) ?? '--'} m/s²</Text>
                                <Text>Z: {imuData?.acceleration?.z?.toFixed(3) ?? '--'} m/s²</Text>
                            </Space>
                        </div>
                    </Card>
                </Col>
            </Row>

            {/* 关节状态 */}
            <Card title="关节状态" style={{ marginTop: 16 }}>
                <Row gutter={[8, 8]}>
                    {joints.length > 0 ? (
                        joints.map((joint, index: number) => (
                            <Col key={joint.joint_id || index} xs={12} sm={8} md={4}>
                                <Card size="small">
                                    <Statistic
                                        title={`关节 ${joint.joint_id || index + 1}`}
                                        value={joint.position?.toFixed(4) ?? '--'}
                                        valueStyle={{
                                            fontSize: 14,
                                            color: joint.error_code ? '#cf1322' : undefined
                                        }}
                                    />
                                    {joint.error_code && (
                                        <Tag color="error" style={{ marginTop: 4 }}>
                                            {joint.error_code}
                                        </Tag>
                                    )}
                                </Card>
                            </Col>
                        ))
                    ) : (
                        <Col span={24}>
                            <Text type="secondary">等待遥测数据...</Text>
                        </Col>
                    )}
                </Row>
            </Card>

            {/* 活动故障列表 */}
            {activeFaults.length > 0 && (
                <Card title="活动故障" style={{ marginTop: 16 }}>
                    <Space wrap>
                        {activeFaults.map((fault: string, index: number) => (
                            <Tag key={index} color="error" icon={<WarningOutlined />}>
                                {fault}
                            </Tag>
                        ))}
                    </Space>
                </Card>
            )}
        </div>
    )
}

export default MonitorPage
