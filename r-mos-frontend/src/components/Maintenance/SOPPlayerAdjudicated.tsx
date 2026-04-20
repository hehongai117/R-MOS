/**
 * SOPPlayerAdjudicated.tsx - 裁决级 SOP 播放器组件
 * 
 * 功能：
 * - 选择并播放 SOP 脚本
 * - 按步骤高亮零件
 * - **前置条件检查，不满足则阻断**
 * - **验证步骤完成后才可推进**
 * - **接入裁决引擎和 SOP 执行器**
 * - 工具校验集成
 * 
 * 符合规范：
 * - B.4：BLOCKED 时 SOP 不前进
 * - A.3：禁止绕过裁决层推进 SOP
 */

import React, { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { DEMO_MODE } from '@/config/demoMode';
import { Card, Space, Typography, Button, Steps, Tag, Progress, Alert, Select, Tooltip, Empty, Divider, Modal } from 'antd';
import {
    PlayCircleOutlined,
    StepForwardOutlined,
    StepBackwardOutlined,
    ReloadOutlined,
    CheckCircleOutlined,
    ToolOutlined,
    AimOutlined,
    ExpandOutlined,
    StopOutlined,
    ExclamationCircleOutlined,
    BulbOutlined,
} from '@ant-design/icons';
import { getToolById } from '@/data/toolData';
import {
    ActionType,
    SOPStepAdjudication,
    SOPScriptAdjudication,
    AdjudicationResult,
    AdjudicationReport,
    createSOPExecutor,
    SOPExecutor,
    SOPExecutionState,
    SOPExecutionContext,
    commitPartDetachment,
    commitPartRemoval,
    commitScrewExtraction,
    getScrewInstance,
    ScrewState,
    useAdjudicationStore,
} from '@/adjudication';
import { shouldAutoValidateAfterInteraction } from '@/adjudication/ui/interactionGate';

const { Text } = Typography;

export interface SOPPlayerAdjudicatedProps {
    // 可用的裁决级 SOP 脚本
    availableSOPs: SOPScriptAdjudication[];

    // Demo: auto-select SOP by ID on mount
    initialSopId?: string;

    // 回调
    onStepChange?: (step: SOPStepAdjudication | null, index: number) => void;
    onExplodeChange?: (amount: number) => void;
    onPartSelect?: (partName: string | null) => void;
    onToolRequired?: (toolId: string | null) => void;
    onBlocked?: (report: AdjudicationReport) => void;
    onComplete?: () => void;
    onSummarize?: (report: AdjudicationReport) => void;
    onExecutorReady?: (executor: SOPExecutor | null) => void;
    onSOPChange?: (sop: SOPScriptAdjudication | null) => void;
    onExecutionContextChange?: (context: SOPExecutionContext | null, step: SOPStepAdjudication | null) => void;

    // 当前状态
    currentToolId?: string | null;
    selectedSOPId?: string | null;
    actionEvent?: SOPActionEvent | null;
}

export type SOPActionEventType = 'tool_selected' | 'part_selected' | 'screw_selected';

export interface SOPActionEvent {
    seq: number;
    type: SOPActionEventType;
    toolId?: string | null;
    partName?: string | null;
    screwId?: string | null;
}

// 步骤图标
const StepIcon: Record<string, React.ReactNode> = {
    'select_tool': <ToolOutlined />,
    'rotate_screw': <AimOutlined />,
    'extract_screw': <AimOutlined />,
    'detach_part': <ExpandOutlined />,
    'remove_part': <ExpandOutlined />,
    'focus_camera': <AimOutlined />,
};

// 执行状态颜色
const ExecutionStateColor: Record<SOPExecutionState, string> = {
    [SOPExecutionState.IDLE]: '#1890ff',
    [SOPExecutionState.PRECONDITION_CHECK]: '#faad14',
    [SOPExecutionState.EXECUTING]: '#52c41a',
    [SOPExecutionState.VALIDATION]: '#722ed1',
    [SOPExecutionState.COMPLETE]: '#13c2c2',
    [SOPExecutionState.FAILED]: '#ff4d4f',
    [SOPExecutionState.BLOCKED]: '#ff4d4f',
};

// 执行状态文本
const ExecutionStateText: Record<SOPExecutionState, string> = {
    [SOPExecutionState.IDLE]: '就绪',
    [SOPExecutionState.PRECONDITION_CHECK]: '检查前置条件',
    [SOPExecutionState.EXECUTING]: '执行中',
    [SOPExecutionState.VALIDATION]: '验证中',
    [SOPExecutionState.COMPLETE]: '已完成',
    [SOPExecutionState.FAILED]: '失败',
    [SOPExecutionState.BLOCKED]: '已阻断',
};

const PART_TARGET_ALIASES: Record<string, string[]> = {
    frame_torso_chest: ['torso_link'],
    torso_motor: ['torso_link'],
    torso_pcb_main: ['torso_link'],
    left_foot_rubber: ['left_ankle_roll_link'],
    right_foot_rubber: ['right_ankle_roll_link'],
};

export const SOPPlayerAdjudicated: React.FC<SOPPlayerAdjudicatedProps> = ({
    availableSOPs,
    initialSopId,
    onStepChange,
    onExplodeChange,
    onPartSelect,
    onToolRequired,
    onBlocked,
    onComplete,
    onSummarize,
    onExecutorReady,
    onSOPChange,
    onExecutionContextChange,
    currentToolId: propCurrentToolId,
    selectedSOPId,
    actionEvent,
}) => {
    const navigate = useNavigate();
    const stepTimestamps = useRef<Record<string, { start: number; end?: number }>>({});
    const [selectedSOP, setSelectedSOP] = useState<SOPScriptAdjudication | null>(null);
    const [executor, setExecutor] = useState<SOPExecutor | null>(null);
    const [context, setContext] = useState<SOPExecutionContext | null>(null);
    const [lastReport, setLastReport] = useState<AdjudicationReport | null>(null);
    const [showBlockedModal, setShowBlockedModal] = useState(false);

    // 从 store 获取当前工具
    const storeCurrentToolId = useAdjudicationStore((state) => state.currentToolId);
    const operationMode = useAdjudicationStore((state) => state.operationMode);
    const currentToolId = propCurrentToolId ?? storeCurrentToolId;
    const setCurrentTool = useAdjudicationStore((state) => state.setCurrentTool);

    // 当前步骤
    const currentStep = useMemo(() => {
        if (!selectedSOP || context === null) return null;
        return selectedSOP.steps[context.currentStepIndex] || null;
    }, [selectedSOP, context]);

    // 进度百分比
    const progress = useMemo(() => {
        if (!selectedSOP || context === null) return 0;
        return Math.round((context.currentStepIndex / (selectedSOP.steps.length - 1)) * 100);
    }, [selectedSOP, context]);

    // 是否完成
    const isCompleted = context?.executionState === SOPExecutionState.COMPLETE;
    const isFailed = context?.executionState === SOPExecutionState.FAILED;
    const isBlocked = context?.executionState === SOPExecutionState.BLOCKED || isFailed;

    const executingHint = useMemo(() => {
        if (!currentStep || context?.executionState !== SOPExecutionState.EXECUTING) return null;
        if (currentStep.targetParts.length === 0) {
            return '请完成当前步骤的检查与记录，点击“手动验证”继续。';
        }
        switch (currentStep.action) {
            case ActionType.SELECT_TOOL:
                return '请在左侧工具区选择本步骤要求的工具，系统将自动验证并推进。';
            case ActionType.ROTATE_SCREW:
            case ActionType.EXTRACT_SCREW:
                return '请在螺丝面板连续点击目标螺丝，全部完成后系统自动验证并推进。';
            case ActionType.DETACH_PART:
            case ActionType.REMOVE_PART:
            case ActionType.FOCUS_CAMERA:
            case ActionType.UNPLUG_CONNECTOR:
                return '请在 3D 视图点击目标零件，系统将自动验证并推进。';
            default:
                return '请先完成当前操作，再点击“手动验证”作为兜底。';
        }
    }, [currentStep, context?.executionState]);

    const emitStepOutputs = useCallback((step: SOPStepAdjudication | null, index: number) => {
        onStepChange?.(step, index);
        onPartSelect?.(step?.targetParts[0] ?? null);
        onToolRequired?.(step?.requiredTool ?? null);
    }, [onStepChange, onPartSelect, onToolRequired]);

    // 创建执行器
    const createExecutor = useCallback((sop: SOPScriptAdjudication) => {
        const newExecutor = createSOPExecutor({
            onStateChange: (ctx) => {
                const snapshot = { ...ctx };
                setContext(snapshot);
                const step = sop.steps[snapshot.currentStepIndex] ?? null;
                onExecutionContextChange?.(snapshot, step);
            },
            onStepChange: (step, index) => {
                emitStepOutputs(step, index);
            },
            onBlocked: (report) => {
                setLastReport(report);
                if (!report.shouldSummarize && operationMode !== 'teaching') {
                    setShowBlockedModal(true);
                }
                onBlocked?.(report);
                if (report.shouldSummarize) {
                    onSummarize?.(report);
                }
            },
            onComplete: () => {
                onComplete?.();
            },
        });

        newExecutor.loadSOP(sop);
        setExecutor(newExecutor);
        onExecutorReady?.(newExecutor);
        onSOPChange?.(sop);

        // 初始化 context
        const initialContext = newExecutor.getContext();
        if (initialContext) {
            const snapshot = { ...initialContext };
            const initialStep = sop.steps[snapshot.currentStepIndex] ?? null;
            setContext(snapshot);
            emitStepOutputs(initialStep, snapshot.currentStepIndex);
            onExecutionContextChange?.(snapshot, initialStep);
        }
    }, [
        emitStepOutputs,
        onBlocked,
        onComplete,
        onSummarize,
        onExecutorReady,
        onSOPChange,
        onExecutionContextChange,
        operationMode,
    ]);

    const clearSelection = useCallback(() => {
        setSelectedSOP(null);
        setExecutor(null);
        setContext(null);
        setLastReport(null);
        onExecutorReady?.(null);
        onSOPChange?.(null);
        emitStepOutputs(null, 0);
        onExecutionContextChange?.(null, null);
    }, [emitStepOutputs, onExecutorReady, onSOPChange, onExecutionContextChange]);

    // 选择 SOP
    const handleSelectSOP = useCallback((sopId: string) => {
        const sop = availableSOPs.find(s => s.sopId === sopId);
        if (sop) {
            setSelectedSOP(sop);
            setLastReport(null);
            createExecutor(sop);
        }
    }, [availableSOPs, createExecutor]);

    useEffect(() => {
        if (selectedSOPId === undefined) return;
        if (selectedSOPId === null) {
            if (selectedSOP) {
                clearSelection();
            }
            return;
        }
        if (selectedSOP?.sopId !== selectedSOPId) {
            handleSelectSOP(selectedSOPId);
        }
    }, [selectedSOPId, selectedSOP, handleSelectSOP, clearSelection]);

    // Demo: auto-select SOP from URL param on mount
    useEffect(() => {
        if (!initialSopId || selectedSOP) return;
        const sop = availableSOPs.find(s => s.sopId === initialSopId);
        if (sop) {
            handleSelectSOP(initialSopId);
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [initialSopId, availableSOPs]);

    // Demo: track step start timestamps
    useEffect(() => {
        if (!DEMO_MODE || !currentStep) return;
        if (!stepTimestamps.current[currentStep.stepId]) {
            stepTimestamps.current[currentStep.stepId] = { start: Date.now() };
        }
    }, [currentStep]);

    // Demo: navigate to report on SOP completion
    useEffect(() => {
        if (!DEMO_MODE || context?.executionState !== SOPExecutionState.COMPLETE) return;
        // Mark last step as complete
        if (currentStep) {
            const ts = stepTimestamps.current[currentStep.stepId];
            if (ts && !ts.end) ts.end = Date.now();
        }
        sessionStorage.setItem('demo_step_timestamps', JSON.stringify(stepTimestamps.current));
        sessionStorage.setItem('demo_sop_name', selectedSOP?.title ?? '');
        const timer = setTimeout(() => navigate('/reports/demo'), 2000);
        return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [context?.executionState]);

    const normalizeSpec = useCallback((value: string): string => {
        return value.toLowerCase().replace(/×/g, 'x').replace(/\s+/g, '');
    }, []);

    const resolveScrewTargetId = useCallback((step: SOPStepAdjudication, rawScrewId: string): string | null => {
        if (step.targetParts.includes(rawScrewId)) {
            return rawScrewId;
        }
        const normalizedInput = normalizeSpec(rawScrewId);
        const store = useAdjudicationStore.getState();
        for (const targetId of step.targetParts) {
            const screw = getScrewInstance(targetId);
            if (!screw?.screwSpec) continue;
            const spec = normalizeSpec(screw.screwSpec.type);
            if (!spec.includes(normalizedInput) && !normalizedInput.includes(spec)) continue;
            const screwState = store.screwStates[targetId];
            if (screwState?.state !== ScrewState.EXTRACTED && screwState?.state !== ScrewState.REMOVED) {
                return targetId;
            }
        }
        for (const targetId of step.targetParts) {
            const screw = getScrewInstance(targetId);
            if (!screw?.screwSpec) continue;
            const spec = normalizeSpec(screw.screwSpec.type);
            if (spec.includes(normalizedInput) || normalizedInput.includes(spec)) {
                return targetId;
            }
        }
        return null;
    }, [normalizeSpec]);

    const resolvePartTargetId = useCallback((step: SOPStepAdjudication, rawPartId: string): string | null => {
        if (step.targetParts.includes(rawPartId)) {
            return rawPartId;
        }
        for (const targetId of step.targetParts) {
            const aliases = PART_TARGET_ALIASES[targetId] ?? [];
            if (aliases.includes(rawPartId)) {
                return targetId;
            }
        }
        return null;
    }, []);

    const handleActionEvent = useCallback((event: SOPActionEvent): boolean => {
        if (!currentStep) return false;
        switch (currentStep.action) {
            case ActionType.SELECT_TOOL:
                return event.type === 'tool_selected'
                    && !!event.toolId
                    && event.toolId === currentStep.requiredTool;
            case ActionType.FOCUS_CAMERA:
            case ActionType.UNPLUG_CONNECTOR:
                if (event.type !== 'part_selected' || !event.partName) return false;
                if (currentStep.targetParts.length === 0) return true;
                return resolvePartTargetId(currentStep, event.partName) !== null;
            case ActionType.ROTATE_SCREW:
            case ActionType.EXTRACT_SCREW: {
                if (event.type !== 'screw_selected' || !event.screwId) return false;
                const targetScrewId = resolveScrewTargetId(currentStep, event.screwId);
                if (!targetScrewId) return false;
                commitScrewExtraction(targetScrewId);
                return true;
            }
            case ActionType.DETACH_PART: {
                if (event.type !== 'part_selected' || !event.partName) return false;
                const targetPartId = resolvePartTargetId(currentStep, event.partName);
                if (!targetPartId) return false;
                commitPartDetachment(targetPartId);
                return true;
            }
            case ActionType.REMOVE_PART: {
                if (event.type !== 'part_selected' || !event.partName) return false;
                const targetPartId = resolvePartTargetId(currentStep, event.partName);
                if (!targetPartId) return false;
                commitPartRemoval(targetPartId);
                return true;
            }
            default:
                return false;
        }
    }, [currentStep, resolvePartTargetId, resolveScrewTargetId]);

    useEffect(() => {
        if (!actionEvent || !executor || !context) return;

        if (context.executionState === SOPExecutionState.IDLE && currentStep?.action === ActionType.SELECT_TOOL) {
            const eventMatched = handleActionEvent(actionEvent);
            if (!eventMatched) return;
            const executeReport = executor.executeStep();
            setLastReport(executeReport);
            if (executeReport.result === AdjudicationResult.ALLOWED) {
                const validateReport = executor.validateAndAdvance();
                setLastReport(validateReport);
            }
            return;
        }

        if (context.executionState !== SOPExecutionState.EXECUTING) return;
        const eventMatched = handleActionEvent(actionEvent);
        if (!eventMatched) return;
        if (currentStep && !shouldAutoValidateAfterInteraction(currentStep, useAdjudicationStore.getState())) {
            return;
        }
        const validateReport = executor.validateAndAdvance();
        setLastReport(validateReport);
    }, [actionEvent, executor, context, currentStep, handleActionEvent]);

    // 执行下一步
    const handleNext = useCallback(() => {
        if (!executor || isCompleted) return;

        // 如果当前是 IDLE 状态，尝试执行步骤
        if (context?.executionState === SOPExecutionState.IDLE) {
            const executeReport = executor.executeStep();
            setLastReport(executeReport);

            // 文档桥接步骤：无目标、无前置验证时直接推进，避免重复点击。
            if (
                executeReport.result === AdjudicationResult.ALLOWED &&
                currentStep &&
                currentStep.targetParts.length === 0 &&
                currentStep.validations.length === 0 &&
                !currentStep.requiredTool
            ) {
                const validateReport = executor.validateAndAdvance();
                setLastReport(validateReport);
            }
        }
        // 如果当前是 EXECUTING 状态，尝试验证并推进
        else if (context?.executionState === SOPExecutionState.EXECUTING) {
            const report = executor.validateAndAdvance();
            setLastReport(report);
        }
        // 如果当前是 BLOCKED 状态，重试
        else if (context?.executionState === SOPExecutionState.BLOCKED) {
            const report = executor.executeStep();
            setLastReport(report);
        }
    }, [executor, context, isCompleted, currentStep]);

    const handleRetry = useCallback(() => {
        if (!executor) return;
        const retried = executor.retryStep();
        if (retried) {
            setLastReport(null);
            setShowBlockedModal(false);
        }
    }, [executor]);

    // 上一步（仅限已完成步骤）
    const handlePrev = useCallback(() => {
        if (!executor || !context || context.currentStepIndex === 0) return;

        // 只能回到已完成的步骤
        executor.goToStep(context.currentStepIndex - 1);
    }, [executor, context]);

    // 重置
    const handleReset = useCallback(() => {
        if (executor) {
            executor.reset();
            setLastReport(null);
        }
        onPartSelect?.(null);
        onExplodeChange?.(0);
        onToolRequired?.(null);
    }, [executor, onPartSelect, onExplodeChange, onToolRequired]);

    // 工具匹配检查
    const isToolMatched = currentStep?.requiredTool && currentToolId === currentStep.requiredTool;

    // 选择工具
    const handleSelectTool = useCallback((toolId: string) => {
        setCurrentTool(toolId);
    }, [setCurrentTool]);

    // 难度标签颜色
    const difficultyColor = {
        'beginner': 'green',
        'intermediate': 'orange',
        'advanced': 'red',
    };

    return (
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
        </Card>
    );
};

export default SOPPlayerAdjudicated;
