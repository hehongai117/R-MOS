/**
 * SOPPlayer.tsx - SOP 播放器组件
 * 
 * 功能：
 * - 选择并播放 SOP 脚本
 * - 按步骤高亮零件
 * - 显示操作提示
 * - 工具校验集成
 */

import React, { useState, useEffect } from 'react';
import { Card, Space, Typography, Button, Steps, Tag, Progress, Alert, Select, Tooltip, Empty, Divider } from 'antd';
import {
    PlayCircleOutlined,
    StepForwardOutlined,
    StepBackwardOutlined,
    ReloadOutlined,
    CheckCircleOutlined,
    WarningOutlined,
    ToolOutlined,
    AimOutlined,
    ExpandOutlined,
} from '@ant-design/icons';
import { SOPScript, SOPStep, ALL_SOP_SCRIPTS, formatDuration } from '@/data/sopScripts';
import { getToolById } from '@/data/toolData';

const { Text } = Typography;

export interface SOPPlayerProps {
    onStepChange?: (step: SOPStep | null) => void;
    onExplodeChange?: (amount: number) => void;
    onPartSelect?: (partName: string | null) => void;
    onToolRequired?: (toolId: string | null, screwId: string | null) => void;
    currentToolId?: string | null;
}

// 步骤图标
const StepIcon: Record<string, React.ReactNode> = {
    'highlight': <AimOutlined />,
    'explode': <ExpandOutlined />,
    'tool_check': <ToolOutlined />,
    'action': <StepForwardOutlined />,
    'warning': <WarningOutlined />,
    'complete': <CheckCircleOutlined />,
};

// 步骤颜色
const StepColor: Record<string, string> = {
    'highlight': '#1890ff',
    'explode': '#722ed1',
    'tool_check': '#fa8c16',
    'action': '#52c41a',
    'warning': '#faad14',
    'complete': '#13c2c2',
};

export const SOPPlayer: React.FC<SOPPlayerProps> = ({
    onStepChange,
    onExplodeChange,
    onPartSelect,
    onToolRequired,
    currentToolId,
}) => {
    const [selectedScript, setSelectedScript] = useState<SOPScript | null>(null);
    const [currentStepIndex, setCurrentStepIndex] = useState(0);
    const [isCompleted, setIsCompleted] = useState(false);

    // 当前步骤
    const currentStep = selectedScript?.steps[currentStepIndex] || null;

    // 进度百分比
    const progress = selectedScript
        ? Math.round((currentStepIndex / (selectedScript.steps.length - 1)) * 100)
        : 0;

    // 步骤变化时触发回调
    useEffect(() => {
        if (currentStep) {
            onStepChange?.(currentStep);

            // 高亮零件
            if (currentStep.partName) {
                onPartSelect?.(currentStep.partName);
            }

            // 设置爆炸程度
            if (currentStep.explodeAmount !== undefined) {
                onExplodeChange?.(currentStep.explodeAmount);
            }

            // 工具要求
            if (currentStep.type === 'tool_check' || currentStep.toolId) {
                onToolRequired?.(currentStep.toolId || null, currentStep.screwId || null);
            }
        }
    }, [currentStep, onStepChange, onPartSelect, onExplodeChange, onToolRequired]);

    // 下一步
    const handleNext = () => {
        if (selectedScript && currentStepIndex < selectedScript.steps.length - 1) {
            setCurrentStepIndex(prev => prev + 1);
        } else if (selectedScript && currentStepIndex === selectedScript.steps.length - 1) {
            setIsCompleted(true);
        }
    };

    // 上一步
    const handlePrev = () => {
        if (currentStepIndex > 0) {
            setCurrentStepIndex(prev => prev - 1);
            setIsCompleted(false);
        }
    };

    // 重置
    const handleReset = () => {
        setCurrentStepIndex(0);
        setIsCompleted(false);
        onPartSelect?.(null);
        onExplodeChange?.(0);
        onToolRequired?.(null, null);
    };

    // 选择脚本
    const handleSelectScript = (id: string) => {
        const script = ALL_SOP_SCRIPTS.find(s => s.id === id);
        setSelectedScript(script || null);
        handleReset();
    };

    // 工具匹配检查
    const isToolMatched = currentStep?.toolId && currentToolId === currentStep.toolId;

    // 难度标签颜色
    const difficultyColor = {
        'easy': 'green',
        'medium': 'orange',
        'hard': 'red',
    };

    return (
        <Card
            size="small"
            title={
                <Space>
                    <PlayCircleOutlined />
                    <span>SOP 播放器</span>
                </Space>
            }
        >
            {/* 脚本选择 */}
            <Space direction="vertical" style={{ width: '100%' }} size="small">
                <Select
                    style={{ width: '100%' }}
                    placeholder="选择 SOP 脚本"
                    value={selectedScript?.id}
                    onChange={handleSelectScript}
                    options={ALL_SOP_SCRIPTS.map(s => ({
                        value: s.id,
                        label: (
                            <Space>
                                <span>{s.name}</span>
                                <Tag color={difficultyColor[s.difficulty]} style={{ marginLeft: 'auto' }}>
                                    {s.difficulty === 'easy' ? '简单' : s.difficulty === 'medium' ? '中等' : '困难'}
                                </Tag>
                            </Space>
                        ),
                    }))}
                />

                {selectedScript ? (
                    <>
                        {/* 脚本信息 */}
                        <div style={{
                            padding: '8px 12px',
                            background: 'rgba(24, 144, 255, 0.05)',
                            borderRadius: 6,
                        }}>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                                {selectedScript.description}
                            </Text>
                            <div style={{ marginTop: 4 }}>
                                <Tag color="blue">{selectedScript.steps.length} 步骤</Tag>
                                <Tag color="cyan">约 {selectedScript.estimatedTime} 分钟</Tag>
                            </div>
                        </div>

                        {/* 进度条 */}
                        <Progress
                            percent={progress}
                            size="small"
                            status={isCompleted ? 'success' : 'active'}
                        />

                        {/* 当前步骤 */}
                        {currentStep && !isCompleted && (
                            <Alert
                                type={currentStep.warningLevel === 'danger' ? 'error' :
                                    currentStep.warningLevel === 'warning' ? 'warning' : 'info'}
                                icon={StepIcon[currentStep.type]}
                                message={
                                    <Space>
                                        <Tag color={StepColor[currentStep.type]}>
                                            步骤 {currentStep.id}
                                        </Tag>
                                        <Text strong>{currentStep.title}</Text>
                                    </Space>
                                }
                                description={
                                    <Space direction="vertical" size={4} style={{ width: '100%' }}>
                                        <Text>{currentStep.description}</Text>

                                        {/* 工具提示 */}
                                        {currentStep.toolId && (
                                            <div style={{ marginTop: 4 }}>
                                                {isToolMatched ? (
                                                    <Tag color="success" icon={<CheckCircleOutlined />}>
                                                        工具就绪: {getToolById(currentStep.toolId)?.name}
                                                    </Tag>
                                                ) : (
                                                    <Tag color="warning" icon={<ToolOutlined />}>
                                                        需要: {getToolById(currentStep.toolId)?.name}
                                                    </Tag>
                                                )}
                                            </div>
                                        )}

                                        {/* 时长提示 */}
                                        {currentStep.duration && currentStep.duration > 0 && (
                                            <Text type="secondary" style={{ fontSize: 11 }}>
                                                预计时长: {formatDuration(currentStep.duration)}
                                            </Text>
                                        )}
                                    </Space>
                                }
                                style={{ marginTop: 8 }}
                            />
                        )}

                        {/* 完成提示 */}
                        {isCompleted && (
                            <Alert
                                type="success"
                                icon={<CheckCircleOutlined />}
                                message="SOP 执行完成"
                                description={`已完成「${selectedScript.name}」的所有步骤。`}
                            />
                        )}

                        {/* 控制按钮 */}
                        <Space style={{ width: '100%', justifyContent: 'center', marginTop: 8 }}>
                            <Tooltip title="重置">
                                <Button
                                    icon={<ReloadOutlined />}
                                    onClick={handleReset}
                                    size="small"
                                />
                            </Tooltip>
                            <Button
                                icon={<StepBackwardOutlined />}
                                onClick={handlePrev}
                                disabled={currentStepIndex === 0}
                                size="small"
                            >
                                上一步
                            </Button>
                            <Button
                                type="primary"
                                icon={<StepForwardOutlined />}
                                onClick={handleNext}
                                disabled={isCompleted}
                                size="small"
                            >
                                {currentStepIndex === (selectedScript?.steps.length || 0) - 1 ? '完成' : '下一步'}
                            </Button>
                        </Space>

                        <Divider style={{ margin: '12px 0' }} />

                        {/* 步骤列表 */}
                        <div style={{ maxHeight: 200, overflowY: 'auto' }}>
                            <Steps
                                direction="vertical"
                                size="small"
                                current={currentStepIndex}
                                items={selectedScript.steps.map((step, index) => ({
                                    title: (
                                        <Text
                                            style={{
                                                fontSize: 12,
                                                color: index === currentStepIndex ? '#1890ff' : undefined,
                                            }}
                                        >
                                            {step.title}
                                        </Text>
                                    ),
                                    icon: index < currentStepIndex ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> :
                                        index === currentStepIndex ? StepIcon[step.type] : undefined,
                                    status: index < currentStepIndex ? 'finish' :
                                        index === currentStepIndex ? 'process' : 'wait',
                                }))}
                            />
                        </div>
                    </>
                ) : (
                    <Empty
                        description="选择一个 SOP 脚本开始"
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                    />
                )}
            </Space>
        </Card>
    );
};

export default SOPPlayer;
