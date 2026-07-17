/**
 * useSOPExecutorBridge.ts — SOP 執行器ライフサイクル管理フック
 *
 * selectedSOP / executor / context / lastReport / showBlockedModal 状態と
 * createExecutor / clearSelection / handleSelectSOP + 関連 useEffect を管理する。
 * 親コールバックはパラメータとして注入される。
 */

import { useState, useCallback, useEffect } from 'react';
import {
    SOPStepAdjudication,
    SOPScriptAdjudication,
    AdjudicationReport,
    createSOPExecutor,
    SOPExecutor,
    SOPExecutionContext,
} from '@/adjudication';

export interface UseSOPExecutorBridgeProps {
    availableSOPs: SOPScriptAdjudication[];
    selectedSOPId?: string | null;
    initialSopId?: string;
    operationMode: string;
    onStepChange?: (step: SOPStepAdjudication | null, index: number) => void;
    onPartSelect?: (partName: string | null) => void;
    onToolRequired?: (toolId: string | null) => void;
    onBlocked?: (report: AdjudicationReport) => void;
    onComplete?: () => void;
    onSummarize?: (report: AdjudicationReport) => void;
    onExecutorReady?: (executor: SOPExecutor | null) => void;
    onSOPChange?: (sop: SOPScriptAdjudication | null) => void;
    onExecutionContextChange?: (context: SOPExecutionContext | null, step: SOPStepAdjudication | null) => void;
}

export interface UseSOPExecutorBridgeResult {
    selectedSOP: SOPScriptAdjudication | null;
    executor: SOPExecutor | null;
    context: SOPExecutionContext | null;
    lastReport: AdjudicationReport | null;
    showBlockedModal: boolean;
    setShowBlockedModal: React.Dispatch<React.SetStateAction<boolean>>;
    setLastReport: React.Dispatch<React.SetStateAction<AdjudicationReport | null>>;
    handleSelectSOP: (sopId: string) => void;
}

export function useSOPExecutorBridge({
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
}: UseSOPExecutorBridgeProps): UseSOPExecutorBridgeResult {
    const [selectedSOP, setSelectedSOP] = useState<SOPScriptAdjudication | null>(null);
    const [executor, setExecutor] = useState<SOPExecutor | null>(null);
    const [context, setContext] = useState<SOPExecutionContext | null>(null);
    const [lastReport, setLastReport] = useState<AdjudicationReport | null>(null);
    const [showBlockedModal, setShowBlockedModal] = useState(false);

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

    // selectedSOPId sync effect
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
    }, [initialSopId, availableSOPs]);

    return {
        selectedSOP,
        executor,
        context,
        lastReport,
        showBlockedModal,
        setShowBlockedModal,
        setLastReport,
        handleSelectSOP,
    };
}
