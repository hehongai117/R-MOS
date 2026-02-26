/**
 * ScrewInfo.tsx - 螺丝信息面板组件
 * 
 * 功能：
 * - 显示零件的螺丝信息
 * - 显示螺丝规格和数量
 * - 提示需要的工具
 */

import React from 'react';
import { Card, Space, Tag, Typography, Tooltip, Empty } from 'antd';
import { InfoCircleOutlined } from '@ant-design/icons';
import {
    getCoreScrewRecords,
    getDetailScrewRecords,
    type DetailPartSelection,
} from '@/data/maintenanceKnowledge';

const { Text } = Typography;

export interface ScrewInfoProps {
    partName: string | null;
    detailSelection?: DetailPartSelection | null;
    onScrewSelect?: (screwId: string) => void;
    selectedScrewId?: string | null;
}

export const ScrewInfo: React.FC<ScrewInfoProps> = ({
    partName,
    detailSelection = null,
    onScrewSelect,
    selectedScrewId,
}) => {
    if (!partName && !detailSelection) {
        return (
            <Card size="small" title={<><InfoCircleOutlined /> 螺丝信息</>}>
                <Empty
                    description="选择一个零件查看螺丝信息"
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
            </Card>
        );
    }

    const screwData = detailSelection
        ? getDetailScrewRecords(detailSelection)
        : (partName ? getCoreScrewRecords(partName) : []);

    if (screwData.length === 0) {
        return (
            <Card size="small" title={<><InfoCircleOutlined /> 螺丝信息</>}>
                <Text type="secondary">此零件无螺丝数据</Text>
            </Card>
        );
    }

    return (
        <Card
            size="small"
            title={
                <Space>
                    <InfoCircleOutlined />
                    <span>螺丝信息</span>
                    <Tag color="blue">{screwData.length} 种</Tag>
                </Space>
            }
        >
            <Space direction="vertical" style={{ width: '100%' }} size="small">
                {screwData.map((item, index) => (
                    <div
                        key={`${item.screwId}-${index}`}
                        style={{
                            padding: '8px 12px',
                            borderRadius: 6,
                            border: selectedScrewId === item.screwId
                                ? '2px solid #1890ff'
                                : '1px solid #303030',
                            background: selectedScrewId === item.screwId
                                ? 'rgba(24, 144, 255, 0.1)'
                                : 'transparent',
                            cursor: 'pointer',
                            transition: 'all 0.2s',
                        }}
                        onClick={() => onScrewSelect?.(item.screwId)}
                    >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <Space>
                                <Text strong style={{ fontSize: 14 }}>{item.spec}</Text>
                                <Tag color="cyan">×{item.quantity}</Tag>
                            </Space>
                            <Tooltip title={`需要 ${item.tool}`}>
                                <Tag color="orange">{item.tool}</Tag>
                            </Tooltip>
                        </div>
                        <div style={{ marginTop: 4 }}>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                                📍 {item.position}
                            </Text>
                        </div>
                        {item.torque !== null && (
                            <div style={{ marginTop: 2 }}>
                                <Text type="secondary" style={{ fontSize: 11 }}>
                                    扭矩: {item.torque} Nm
                                </Text>
                            </div>
                        )}
                    </div>
                ))}
            </Space>

            {/* 统计 */}
            <div style={{
                marginTop: 12,
                padding: '8px 12px',
                background: 'rgba(24, 144, 255, 0.05)',
                borderRadius: 6,
            }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                    总计: {screwData.reduce((sum, s) => sum + s.quantity, 0)} 颗螺丝
                </Text>
            </div>
        </Card>
    );
};

export default ScrewInfo;
