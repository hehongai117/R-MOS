/**
 * 连接状态条组件（V2.3 新增）
 * 
 * 在页面顶部显示 WebSocket 连接状态：
 * - 已连接（绿色）
 * - 重连中（黄色）
 * - 已断开（红色）
 * - 数据过期（橙色）
 */
import React from 'react';
import { Alert, Space, Tag, Typography, Button } from 'antd';
import {
    CheckCircleOutlined,
    SyncOutlined,
    DisconnectOutlined,
    WarningOutlined,
    ReloadOutlined
} from '@ant-design/icons';
import { ConnectionStatus } from '../../hooks/useWebSocket';

const { Text } = Typography;

interface ConnectionStatusBarProps {
    status: ConnectionStatus;
    isDataStale: boolean;
    retryCount: number;
    lastUpdateTime: Date | null;
    onReconnect: () => void;
}

const statusConfig: Record<ConnectionStatus, {
    type: 'success' | 'warning' | 'error' | 'info';
    icon: React.ReactNode;
    text: string;
}> = {
    connected: {
        type: 'success',
        icon: <CheckCircleOutlined />,
        text: '已连接',
    },
    connecting: {
        type: 'info',
        icon: <SyncOutlined spin />,
        text: '连接中...',
    },
    reconnecting: {
        type: 'warning',
        icon: <SyncOutlined spin />,
        text: '重连中',
    },
    disconnected: {
        type: 'error',
        icon: <DisconnectOutlined />,
        text: '已断开',
    },
    failed: {
        type: 'error',
        icon: <DisconnectOutlined />,
        text: '连接失败',
    },
};

export const ConnectionStatusBar: React.FC<ConnectionStatusBarProps> = ({
    status,
    isDataStale,
    retryCount,
    lastUpdateTime,
    onReconnect,
}) => {
    const config = statusConfig[status];

    // 仅在非连接状态或数据过期时显示
    if (status === 'connected' && !isDataStale) {
        return null;
    }

    return (
        <Alert
            type={isDataStale ? 'warning' : config.type}
            banner
            showIcon
            icon={isDataStale ? <WarningOutlined /> : config.icon}
            message={
                <Space size="middle" style={{ width: '100%', justifyContent: 'space-between' }}>
                    <Space>
                        <Tag color={isDataStale ? 'orange' : config.type === 'success' ? 'green' : config.type === 'error' ? 'red' : 'gold'}>
                            {isDataStale ? '数据已过期' : config.text}
                        </Tag>
                        {status === 'reconnecting' && (
                            <Text type="secondary">
                                第 {retryCount} 次重连...
                            </Text>
                        )}
                        {lastUpdateTime && isDataStale && (
                            <Text type="secondary" style={{ fontSize: 12 }}>
                                最后更新: {lastUpdateTime.toLocaleTimeString()}
                            </Text>
                        )}
                    </Space>
                    {(status === 'failed' || status === 'disconnected') && (
                        <Button
                            size="small"
                            icon={<ReloadOutlined />}
                            onClick={onReconnect}
                        >
                            重新连接
                        </Button>
                    )}
                </Space>
            }
        />
    );
};

export default ConnectionStatusBar;
