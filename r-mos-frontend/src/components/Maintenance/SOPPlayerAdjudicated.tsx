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

import React, { useCallback, useMemo, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { completeStep as pipelineCompleteStep, completeTask as pipelineCompleteTask } from '@/api/pipeline';
import {
    buildPartTargetAliases as _buildPartTargetAliases,
} from './sopPlayer/sopPlayerConfig';
import { useSOPActionResolver } from './sopPlayer/useSOPActionResolver';
import { useSOPExecutorBridge } from './sopPlayer/useSOPExecutorBridge';
import { SOPPlayerView } from './sopPlayer/SOPPlayerView';
import {
    ActionType,
    SOPStepAdjudication,
    SOPScriptAdjudication,
    AdjudicationResult,
    AdjudicationReport,
    SOPExecutor,
    SOPExecutionState,
    SOPExecutionContext,
    useAdjudicationStore,
} from '@/adjudication';
import { shouldAutoValidateAfterInteraction } from '@/adjudication/ui/interactionGate';

// Re-export for backward-compat: external code that imports buildPartTargetAliases
// from this module path continues to work unchanged.
export { _buildPartTargetAliases as buildPartTargetAliases };

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

    // Session ID for navigation to report page on SOP completion
    sessionId?: string;

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
    sessionId,
    currentToolId: propCurrentToolId,
    selectedSOPId,
    actionEvent,
}) => {
    const navigate = useNavigate();

    // 从 store 获取当前工具
    const storeCurrentToolId = useAdjudicationStore((state) => state.currentToolId);
    const operationMode = useAdjudicationStore((state) => state.operationMode);
    const currentToolId = propCurrentToolId ?? storeCurrentToolId;
    const setCurrentTool = useAdjudicationStore((state) => state.setCurrentTool);

    // Executor bridge: 状態管理 + 生命周期
    const {
        selectedSOP,
        executor,
        context,
        lastReport,
        showBlockedModal,
        setShowBlockedModal,
        setLastReport,
        handleSelectSOP,
    } = useSOPExecutorBridge({
        availableSOPs,
        selectedSOPId,
        initialSopId,
        operationMode,
        onStepChange,
        onPartSelect,
        onToolRequired,
        onBlocked,
        onComplete,
        onSummarize,
        onExecutorReady,
        onSOPChange,
        onExecutionContextChange,
    });

    // 当前步骤
    const currentStep = useMemo(() => {
        if (!selectedSOP || context === null) return null;
        return selectedSOP.steps[context.currentStepIndex] || null;
    }, [selectedSOP, context]);

    // Action resolver hook
    const { handleActionEvent } = useSOPActionResolver(currentStep);

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
                return '请先完成当前操作，再点击”手动验证”作为兜底。';
        }
    }, [currentStep, context?.executionState]);

    // Navigate to report on SOP completion
    useEffect(() => {
        if (context?.executionState !== SOPExecutionState.COMPLETE || !sessionId) return;
        const timer = setTimeout(() => navigate(`/reports/${sessionId}`), 2000);
        return () => clearTimeout(timer);
    }, [context?.executionState, sessionId, navigate]);


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
    const stepStartTimeRef = useRef<number>(Date.now());

    // Reset step timer when step changes
    useEffect(() => {
        stepStartTimeRef.current = Date.now();
    }, [context?.currentStepIndex]);

    // Sync step completion to backend pipeline (non-blocking)
    const syncStepCompletion = useCallback((stepIndex: number) => {
        const searchParams = new URLSearchParams(window.location.search);
        const executionId = searchParams.get('execution_id');
        if (!executionId) return;

        const durationSeconds = Math.round((Date.now() - stepStartTimeRef.current) / 1000);
        pipelineCompleteStep(Number(executionId), {
            step_index: stepIndex,
            duration_seconds: durationSeconds,
        }).catch(console.error);
    }, []);

    // Sync task completion to backend pipeline
    const syncTaskCompletion = useCallback(() => {
        const searchParams = new URLSearchParams(window.location.search);
        const executionId = searchParams.get('execution_id');
        if (!executionId) return;

        pipelineCompleteTask(Number(executionId))
            .then((result) => {
                if (result.report_generation === 'triggered') {
                    navigate(`/reports?task_id=${result.task_id}`);
                }
            })
            .catch(console.error);
    }, [navigate]);

    // Auto-trigger task completion when all steps are done
    const hasTriggeredCompletion = useRef(false);
    useEffect(() => {
        if (isCompleted && !hasTriggeredCompletion.current) {
            hasTriggeredCompletion.current = true;
            syncTaskCompletion();
        }
    }, [isCompleted, syncTaskCompletion]);

    const handleNext = useCallback(() => {
        if (!executor || isCompleted) return;
        const prevStepIndex = context?.currentStepIndex ?? 0;

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
                if (validateReport.result === AdjudicationResult.ALLOWED) {
                    syncStepCompletion(prevStepIndex);
                }
            }
        }
        // 如果当前是 EXECUTING 状态，尝试验证并推进
        else if (context?.executionState === SOPExecutionState.EXECUTING) {
            const report = executor.validateAndAdvance();
            setLastReport(report);
            if (report.result === AdjudicationResult.ALLOWED) {
                syncStepCompletion(prevStepIndex);
            }
        }
        // 如果当前是 BLOCKED 状态，重试
        else if (context?.executionState === SOPExecutionState.BLOCKED) {
            const report = executor.executeStep();
            setLastReport(report);
        }
    }, [executor, context, isCompleted, currentStep, syncStepCompletion]);

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

    return (
        <SOPPlayerView
            selectedSOP={selectedSOP}
            context={context}
            executor={executor}
            lastReport={lastReport}
            currentStep={currentStep}
            progress={progress}
            isCompleted={isCompleted}
            isBlocked={isBlocked}
            executingHint={executingHint}
            operationMode={operationMode}
            showBlockedModal={showBlockedModal}
            setShowBlockedModal={setShowBlockedModal}
            availableSOPs={availableSOPs}
            isToolMatched={isToolMatched}
            handleSelectSOP={handleSelectSOP}
            handleNext={handleNext}
            handleRetry={handleRetry}
            handlePrev={handlePrev}
            handleReset={handleReset}
            handleSelectTool={handleSelectTool}
        />
    );
};

export default SOPPlayerAdjudicated;
