/**
 * ToolSelector.tsx - 工具选择器组件
 * 
 * 功能：
 * - 显示可用工具列表
 * - 选择当前手持工具
 * - 校验工具与螺丝匹配
 */

import React from 'react';
import { Alert, Card, Space, Tag, Tooltip, Typography } from 'antd';
import { ToolOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { TOOLS, Tool, getRecommendedTool } from '@/data/toolData';

const { Text } = Typography;

export interface ToolSelectorProps {
    selectedToolId: string | null;
    onToolSelect: (toolId: string | null) => void;
    requiredScrewId?: string;  // 当前需要的螺丝类型
    compact?: boolean;
}

export const ToolSelector: React.FC<ToolSelectorProps> = ({
    selectedToolId,
    onToolSelect,
    requiredScrewId,
    compact = false,
}) => {
    // 获取推荐工具
    const recommendedTool = requiredScrewId ? getRecommendedTool(requiredScrewId) : undefined;
    const isCorrectTool = recommendedTool && selectedToolId === recommendedTool.id;

    // 工具卡片组件
    const ToolCard = ({ tool }: { tool: Tool }) => {
        const isSelected = selectedToolId === tool.id;
        const isRecommended = recommendedTool?.id === tool.id;

        return (
            <Tooltip title={tool.description}>
                <button
                    type="button"
                    aria-label={tool.name}
                    aria-pressed={isSelected}
                    style={{
                        width: '100%',
                        padding: compact ? '8px 12px' : '12px 16px',
                        borderRadius: 8,
                        cursor: 'pointer',
                        border: isSelected
                            ? '2px solid #1890ff'
                            : isRecommended
                                ? '2px solid #52c41a'
                                : '1px solid #303030',
                        background: isSelected
                            ? 'rgba(24, 144, 255, 0.1)'
                            : isRecommended
                                ? 'rgba(82, 196, 26, 0.1)'
                                : 'transparent',
                        transition: 'all 0.2s',
                        textAlign: 'left',
                    }}
                    onClick={() => onToolSelect(isSelected ? null : tool.id)}
                >
                    <Space>
                        <span style={{ fontSize: compact ? 18 : 24 }}>{tool.icon}</span>
                        {!compact && (
                            <div>
                                <Text strong style={{ display: 'block' }}>{tool.name}</Text>
                                <Text type="secondary" style={{ fontSize: 12 }}>{tool.size}</Text>
                            </div>
                        )}
                        {compact && <Text>{tool.size}</Text>}
                        {isRecommended && (
                            <Tag color="success" style={{ marginLeft: 8 }}>推荐</Tag>
                        )}
                        {isSelected && (
                            <CheckCircleOutlined style={{ color: '#1890ff', marginLeft: 8 }} />
                        )}
                    </Space>
                </button>
            </Tooltip>
        );
    };

    return (
        <Card
            size="small"
            title={
                <Space>
                    <ToolOutlined />
                    <span>工具选择</span>
                    {selectedToolId && (
                        <Tag color="blue">
                            {TOOLS.find(t => t.id === selectedToolId)?.name}
                        </Tag>
                    )}
                </Space>
            }
        >
            {/* 工具匹配提示 */}
            {requiredScrewId && (
                <div style={{ marginBottom: 12 }}>
                    {isCorrectTool ? (
                        <Alert
                            type="success"
                            showIcon
                            icon={<CheckCircleOutlined />}
                            message="工具已就绪"
                            description={`${recommendedTool?.name} 可用于此螺丝`}
                            style={{ padding: '8px 12px' }}
                        />
                    ) : recommendedTool ? (
                        <Alert
                            type="warning"
                            showIcon
                            icon={<CloseCircleOutlined />}
                            message="请更换工具"
                            description={`需要 ${recommendedTool.name}`}
                            style={{ padding: '8px 12px' }}
                        />
                    ) : null}
                </div>
            )}

            {/* 工具列表 */}
            <Space direction="vertical" style={{ width: '100%' }} size="small">
                {TOOLS.map(tool => (
                    <ToolCard key={tool.id} tool={tool} />
                ))}
            </Space>

            {/* 取消选择 */}
            {selectedToolId && (
                <button
                    type="button"
                    aria-label="放下工具"
                    style={{
                        width: '100%',
                        marginTop: 12,
                        textAlign: 'center',
                        padding: '8px',
                        borderRadius: 4,
                        cursor: 'pointer',
                        background: 'rgba(255, 77, 79, 0.1)',
                        border: '1px solid rgba(255, 77, 79, 0.3)',
                    }}
                    onClick={() => onToolSelect(null)}
                >
                    <Text type="danger">放下工具</Text>
                </button>
            )}
        </Card>
    );
};

export default ToolSelector;
