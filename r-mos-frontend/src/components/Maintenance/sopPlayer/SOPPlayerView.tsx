/**
 * SOPPlayerView.tsx — SOPPlayerAdjudicated 的纯展示层
 *
 * 无状态、无副作用；所有数据和回调均由父组件通过 props 注入。
 */

import React from 'react';
import { AIAssistantPanel } from '@/components/AIAssistant/AIAssistantPanel';
import {
    Card, Space, Typography, Button, Steps, Tag, Progress,
    Alert, Select, Tooltip, Empty, Divider, Modal,
} from 'antd';
import {
    PlayCircleOutlined,
    StepForwardOutlined,
    StepBackwardOutlined,
    ReloadOutlined,
    CheckCircleOutlined,
    ToolOutlined,
    AimOutlined,
    StopOutlined,
    ExclamationCircleOutlined,
    BulbOutlined,
} from '@ant-design/icons';
import {
    StepIcon,
    ExecutionStateColor,
    ExecutionStateText,
    difficultyColor,
} from './sopPlayerConfig';
import { getToolById } from '@/data/toolData';
import {
    SOPStepAdjudication,
    SOPScriptAdjudication,
    AdjudicationReport,
    SOPExecutor,
    SOPExecutionContext,
    SOPExecutionState,
} from '@/adjudication';

const { Text } = Typography;

export interface SOPPlayerViewProps {
    selectedSOP: SOPScriptAdjudication | null;
    context: SOPExecutionContext | null;
    executor: SOPExecutor | null;
    lastReport: AdjudicationReport | null;
    currentStep: SOPStepAdjudication | null;
    progress: number;
    isCompleted: boolean;
    isBlocked: boolean;
    executingHint: string | null;
    operationMode: string;
    showBlockedModal: boolean;
    setShowBlockedModal: (v: boolean) => void;
    availableSOPs: SOPScriptAdjudication[];
    isToolMatched: string | boolean | null | undefined;
    handleSelectSOP: (sopId: string) => void;
    handleNext: () => void;
    handleRetry: () => void;
    handlePrev: () => void;
    handleReset: () => void;
    handleSelectTool: (toolId: string) => void;
}

export const SOPPlayerView: React.FC<SOPPlayerViewProps> = ({
    selectedSOP,
    context,
    executor,
    lastReport,
    currentStep,
    progress,
    isCompleted,
    isBlocked,
    executingHint,
    operationMode,
    showBlockedModal,
    setShowBlockedModal,
    availableSOPs,
    isToolMatched,
    handleSelectSOP,
    handleNext,
    handleRetry,
    handlePrev,
    handleReset,
    handleSelectTool,
}) => (
    <Card
        size="small"
        title={
            <Space>
                <PlayCircleOutlined />
                <span>SOP 播放器 (裁决级)</span>
                {context && (
                    <Tag color={ExecutionStateColor[context.executionState]}>
                        {ExecutionStateText[context.executionState]}
                    </Tag>
                )}
            </Space>
        }
    >
        <Space direction="vertical" style={{ width: '100%' }} size="small">
            {/* SOP 选择 */}
            <Select
                style={{ width: '100%' }}
                placeholder="选择 SOP 脚本"
                value={selectedSOP?.sopId}
                onChange={handleSelectSOP}
                options={availableSOPs.map(s => ({
                    value: s.sopId,
                    label: (
                        <Space>
                            <span>{s.title}</span>
                            <Tag color={difficultyColor[s.difficulty]} style={{ marginLeft: 'auto' }}>
                                {s.difficulty === 'beginner' ? '简单' : s.difficulty === 'intermediate' ? '中等' : '高级'}
                            </Tag>
                        </Space>
                    ),
                }))}
            />

            {selectedSOP && context ? (
                <>
                    {/* 进度条 */}
                    <Progress
                        percent={progress}
                        size="small"
                        status={isCompleted ? 'success' : isBlocked ? 'exception' : 'active'}
                    />

                    {/* 阻断提示 */}
                    {isBlocked && lastReport && (
                        <Alert
                            type="error"
                            icon={<StopOutlined />}
                            message="操作被阻断"
                            description={
                                <Space direction="vertical" size={4}>
                                    <Text style={{ color: '#e0b0b0' }}>{lastReport.reason}</Text>
                                    {lastReport.requiredActions.length > 0 && (
                                        <div>
                                            <Text type="secondary">需要先完成：</Text>
                                            <ul style={{ margin: '4px 0', paddingLeft: 20 }}>
                                                {lastReport.requiredActions.map((action, i) => (
                                                    <li key={i}><Text style={{ color: '#d0c0c0' }}>{action}</Text></li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </Space>
                            }
                            style={{ marginBottom: 8, background: '#2b1519', borderColor: '#5a2020' }}
                        />
                    )}

                    {/* 教学提示气泡 */}
                    {isBlocked && lastReport?.hint && operationMode === 'teaching' && (
                        <Alert
                            type="info"
                            icon={<BulbOutlined />}
                            message="教学提示"
                            description={<Text style={{ color: '#b0b8c4' }}>{lastReport.hint}</Text>}
                            action={
                                <Button
                                    size="small"
                                    type="primary"
                                    ghost
                                    onClick={handleRetry}
                                >
                                    重试
                                </Button>
                            }
                            style={{ marginTop: -4, marginBottom: 8, background: '#141c2b', borderColor: '#1e3a5f' }}
                        />
                    )}

                    {/* 当前步骤 */}
                    {currentStep && !isCompleted && !isBlocked && (
                        <Alert
                            type="info"
                            icon={StepIcon[currentStep.action] || <AimOutlined />}
                            message={
                                <Space>
                                    <Tag color="#1890ff">
                                        步骤 {currentStep.stepIndex}
                                    </Tag>
                                    <Text strong style={{ color: '#e0e6ed' }}>{currentStep.title}</Text>
                                </Space>
                            }
                            description={
                                <Space direction="vertical" size={4} style={{ width: '100%' }}>
                                    <Text style={{ color: '#b0b8c4' }}>{currentStep.description}</Text>

                                    {/* 工具提示 */}
                                    {currentStep.requiredTool && (
                                        <div style={{ marginTop: 4 }}>
                                            {isToolMatched ? (
                                                <Tag color="success" icon={<CheckCircleOutlined />}>
                                                    工具就绪: {getToolById(currentStep.requiredTool)?.name}
                                                </Tag>
                                            ) : (
                                                <Space>
                                                    <Tag color="warning" icon={<ToolOutlined />}>
                                                        需要: {getToolById(currentStep.requiredTool)?.name}
                                                    </Tag>
                                                    <Button
                                                        size="small"
                                                        onClick={() => handleSelectTool(currentStep.requiredTool!)}
                                                    >
                                                        选择工具
                                                    </Button>
                                                </Space>
                                            )}
                                        </div>
                                    )}

                                    {/* 前置条件 */}
                                    {currentStep.preconditions.length > 0 && (
                                        <div style={{ marginTop: 4 }}>
                                            <Text type="secondary" style={{ fontSize: 11 }}>
                                                前置条件: {currentStep.preconditions.length} 项
                                            </Text>
                                        </div>
                                    )}
                                    {executingHint && (
                                        <Alert
                                            type="warning"
                                            showIcon
                                            message="等待实际操作完成"
                                            description={executingHint}
                                            style={{ marginTop: 6, background: '#2a2215', borderColor: '#5a4a20' }}
                                        />
                                    )}
                                </Space>
                            }
                            style={{ marginTop: 8, background: '#141c2b', borderColor: '#1e3a5f' }}
                        />
                    )}

                    {/* 完成提示 */}
                    {isCompleted && (
                        <Alert
                            type="success"
                            icon={<CheckCircleOutlined />}
                            message="SOP 执行完成"
                            description={`已完成「${selectedSOP.title}」的所有步骤。`}
                            style={{ background: '#122118', borderColor: '#1e5a35' }}
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
                            disabled={!context || context.currentStepIndex === 0}
                            size="small"
                        >
                            上一步
                        </Button>
                        <Button
                            type="primary"
                            icon={isBlocked ? <ExclamationCircleOutlined /> : <StepForwardOutlined />}
                            onClick={handleNext}
                            disabled={isCompleted}
                            danger={isBlocked}
                            size="small"
                        >
                            {isBlocked
                                ? '重试'
                                : context.executionState === SOPExecutionState.EXECUTING
                                    ? '手动验证'
                                    : context.currentStepIndex === (selectedSOP?.steps.length || 0) - 1
                                        ? '完成'
                                        : '下一步'}
                        </Button>
                    </Space>

                    <Divider style={{ margin: '12px 0' }} />

                    {/* 步骤列表 */}
                    <div style={{ maxHeight: 200, overflowY: 'auto' }}>
                        <Steps
                            direction="vertical"
                            size="small"
                            current={context.currentStepIndex}
                            items={selectedSOP.steps.map((step, index) => ({
                                title: (
                                    <Text
                                        style={{
                                            fontSize: 12,
                                            color: index === context.currentStepIndex ? '#1890ff' :
                                                context.completedSteps.includes(step.stepId) ? '#52c41a' : undefined,
                                        }}
                                    >
                                        {step.title}
                                    </Text>
                                ),
                                icon: context.completedSteps.includes(step.stepId) ?
                                    <CheckCircleOutlined style={{ color: '#52c41a' }} /> :
                                    index === context.currentStepIndex ? StepIcon[step.action] : undefined,
                                status: context.completedSteps.includes(step.stepId) ? 'finish' :
                                    index === context.currentStepIndex ?
                                        (isBlocked ? 'error' : 'process') : 'wait',
                            }))}
                        />
                    </div>

                    {/* 执行报告 */}
                    {executor && (
                        <div style={{
                            marginTop: 8,
                            padding: '4px 8px',
                            background: 'rgba(0,0,0,0.02)',
                            borderRadius: 4,
                            fontSize: 11,
                        }}>
                            <Text type="secondary">
                                已完成: {context.completedSteps.length}/{selectedSOP.steps.length} 步骤
                            </Text>
                        </div>
                    )}
                </>
            ) : (
                <Empty
                    description="选择一个 SOP 脚本开始"
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
            )}
        </Space>

        {/* 阻断详情弹窗 */}
        <Modal
            title={<Space><StopOutlined style={{ color: '#ff4d4f' }} /> 操作被阻断</Space>}
            open={showBlockedModal}
            onOk={() => setShowBlockedModal(false)}
            onCancel={() => setShowBlockedModal(false)}
            okText="我知道了"
            cancelButtonProps={{ style: { display: 'none' } }}
        >
            {lastReport && (
                <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                    <Alert type="error" message={lastReport.reason} />

                    {lastReport.requiredActions.length > 0 && (
                        <div>
                            <Text strong>需要先完成以下操作：</Text>
                            <ul style={{ marginTop: 8 }}>
                                {lastReport.requiredActions.map((action, i) => (
                                    <li key={i}>{action}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    <Text type="secondary">
                        错误码: {lastReport.reasonCode}
                    </Text>
                </Space>
            )}
        </Modal>

        <AIAssistantPanel
            sopId={undefined}
            sopTitle={selectedSOP?.title}
            currentStepIndex={context?.currentStepIndex}
            currentStepDescription={
                selectedSOP && context
                    ? selectedSOP.steps[context.currentStepIndex]?.description
                    : undefined
            }
            faultType={undefined}
            hintLevel={3}
        />
    </Card>
);

export default SOPPlayerView;
