/**
 * useSOPPlaybackBridge.ts - SOP 播放器回调桥 + 考试总结 hook
 *
 * 从 SOPMaintenancePage.tsx 抽离：SOP 播放器的全部回调（SOP/步骤/上下文/
 * 阻断/选件/工具）、SOP 意图应用、考试计时与总结。
 *
 * 依赖 useSOPViewState 的 enterIsolation/resetToOverview/setSelectedPart 等，
 * 全部通过参数注入，不反向读取页面。
 */
import { useCallback, useEffect, useRef, useState, type Dispatch, type SetStateAction } from 'react';
import type { PartInfo } from '@/components/Viewer3D/manifestPartMetadata';
import { resolveRuntimeAssetPaths, type RuntimeManifestAdapter } from '@/components/Viewer3D/runtimeManifest';
import {
    AdjudicationReport,
    SOPExecutor,
    SOPExecutionContext,
    SOPExecutionState,
    SOPScriptAdjudication,
    SOPStepAdjudication,
} from '@/adjudication';
import type { useSOPSceneSync } from '@/adjudication/ui/useSOPSceneSync';
import { scoringEngine } from '@/adjudication/core/scoringEngine';
import { EXAM_DURATION_MS, type ViewState } from './sopMaintenanceConfig';

interface UseSOPPlaybackBridgeParams {
    operationMode: string;
    setCurrentTool: (toolId: string | null) => void;
    sopSceneSync: ReturnType<typeof useSOPSceneSync>;
    partMetadata: Record<string, PartInfo>;
    viewState: ViewState;
    selectedOverviewNode: string | null;
    enterIsolation: (overviewNodeId: string) => void;
    resetToOverview: () => void;
    setSelectedPart: (part: PartInfo | null) => void;
    setViewMode: (mode: 'normal' | 'explode') => void;
    setExplodeAmount: Dispatch<SetStateAction<number>>;
    runtimeManifest: RuntimeManifestAdapter | null;
    setRuntimeTargetIds: (ids: string[]) => void;
    setRuntimeSelectedAssetPath: (path: string | null) => void;
    setLinkedSOPId: (sopId: string | null) => void;
    setSelectedScrewId: (screwId: string | null) => void;
    setSelectedToolId: (toolId: string | null) => void;
    setRightPanelTab: (tab: string) => void;
}

export function useSOPPlaybackBridge({
    operationMode,
    setCurrentTool,
    sopSceneSync,
    partMetadata,
    viewState,
    selectedOverviewNode,
    enterIsolation,
    resetToOverview,
    setSelectedPart,
    setViewMode,
    setExplodeAmount,
    runtimeManifest,
    setRuntimeTargetIds,
    setRuntimeSelectedAssetPath,
    setLinkedSOPId,
    setSelectedScrewId,
    setSelectedToolId,
    setRightPanelTab,
}: UseSOPPlaybackBridgeParams) {
    const [examRemainingMs, setExamRemainingMs] = useState(EXAM_DURATION_MS);
    const [scoreState, setScoreState] = useState(scoringEngine.getState());
    const [examSummaryReport, setExamSummaryReport] = useState<AdjudicationReport | null>(null);
    const [sopExecutor, setSopExecutor] = useState<SOPExecutor | null>(null);
    const examEndAtRef = useRef<number | null>(null);

    useEffect(() => {
        const unsubscribe = scoringEngine.subscribe((state) => {
            setScoreState(state);
        });
        return unsubscribe;
    }, []);

    useEffect(() => {
        if (operationMode !== 'exam' || examSummaryReport) {
            examEndAtRef.current = null;
            return;
        }
        if (!examEndAtRef.current) {
            examEndAtRef.current = Date.now() + examRemainingMs;
        }
        const timer = setInterval(() => {
            if (!examEndAtRef.current) return;
            const remaining = Math.max(0, examEndAtRef.current - Date.now());
            setExamRemainingMs(remaining);
        }, 1000);
        return () => clearInterval(timer);
    }, [operationMode, examSummaryReport, examRemainingMs]);

    const handleSummarize = useCallback((report: AdjudicationReport) => {
        setExamSummaryReport(report);
        examEndAtRef.current = null;
    }, []);

    const handleResetExam = useCallback(() => {
        scoringEngine.reset(100);
        setExamSummaryReport(null);
        sopExecutor?.reset();
        setExamRemainingMs(EXAM_DURATION_MS);
        examEndAtRef.current = operationMode === 'exam' ? Date.now() + EXAM_DURATION_MS : null;
    }, [sopExecutor, operationMode]);

    const applySOPIntent = useCallback((intent: { targetPart: string | null; explodeAmount: number; requiredTool: string | null }) => {
        if (intent.requiredTool) {
            setSelectedToolId(intent.requiredTool);
            setCurrentTool(intent.requiredTool);
        }

        if (intent.targetPart) {
            const part = partMetadata[intent.targetPart];
            if (part) {
                if (viewState === 'OVERVIEW' || selectedOverviewNode !== intent.targetPart) {
                    enterIsolation(intent.targetPart);
                }
                setSelectedPart(part);
                setRightPanelTab('part');
            }
        }

        if (intent.explodeAmount > 0) {
            setViewMode('explode');
            setExplodeAmount(Math.max(intent.explodeAmount, 0.25));
        }
    }, [setCurrentTool, viewState, selectedOverviewNode, enterIsolation, partMetadata, setSelectedToolId, setSelectedPart, setRightPanelTab, setViewMode, setExplodeAmount]);

    // SOP 播放器回调
    const handleSOPPartSelect = useCallback((partName: string | null) => {
        if (runtimeManifest) {
            const targetIds = partName ? [partName] : [];
            setRuntimeTargetIds(targetIds);
            const assetPaths = resolveRuntimeAssetPaths(runtimeManifest, targetIds);
            setRuntimeSelectedAssetPath(assetPaths[0] ?? runtimeManifest.parts[0] ?? null);
        }
        if (partName) {
            const part = partMetadata[partName];
            if (part) {
                if (viewState === 'OVERVIEW' || selectedOverviewNode !== partName) {
                    enterIsolation(partName);
                }
                setSelectedPart(part);
                setRightPanelTab('part');
            }
        } else {
            setSelectedPart(null);
        }
    }, [runtimeManifest, viewState, selectedOverviewNode, enterIsolation, partMetadata, setRuntimeTargetIds, setRuntimeSelectedAssetPath, setSelectedPart, setRightPanelTab]);

    const handleSOPToolRequired = useCallback((toolId: string | null) => {
        if (toolId) setSelectedToolId(toolId);
        setCurrentTool(toolId ?? null);
    }, [setCurrentTool, setSelectedToolId]);

    const handleSOPChange = useCallback((sop: SOPScriptAdjudication | null) => {
        setLinkedSOPId(sop?.sopId ?? null);
        setSelectedScrewId(null);
        setSelectedToolId(null);
        setCurrentTool(null);
        resetToOverview();
        const intent = sopSceneSync.bindSOP(sop);
        if (intent) {
            applySOPIntent(intent);
        }
    }, [setCurrentTool, resetToOverview, sopSceneSync, applySOPIntent, setLinkedSOPId, setSelectedScrewId, setSelectedToolId]);

    const handleSOPStepChange = useCallback((step: SOPStepAdjudication | null, index: number) => {
        const intent = sopSceneSync.bindStep(step, index);
        applySOPIntent(intent);
        if (runtimeManifest) {
            const targetIds = step?.targetParts ?? [];
            setRuntimeTargetIds(targetIds);
            const assetPaths = resolveRuntimeAssetPaths(runtimeManifest, targetIds);
            setRuntimeSelectedAssetPath(assetPaths[0] ?? runtimeManifest.parts[0] ?? null);
        }
        if (step && /收起|恢复正常|复位/.test(`${step.title} ${step.description}`)) {
            setExplodeAmount(0);
        }
    }, [runtimeManifest, sopSceneSync, applySOPIntent, setRuntimeTargetIds, setRuntimeSelectedAssetPath, setExplodeAmount]);

    const handleSOPContextChange = useCallback((context: SOPExecutionContext | null, _step: SOPStepAdjudication | null) => {
        sopSceneSync.bindContext(context);
        if (context?.executionState === SOPExecutionState.COMPLETE) {
            setExplodeAmount(0);
        }
    }, [sopSceneSync, setExplodeAmount]);

    const handleSOPBlocked = useCallback((report: AdjudicationReport) => {
        sopSceneSync.bindBlocked(report);
        setRightPanelTab('part');
    }, [sopSceneSync, setRightPanelTab]);

    return {
        examSummaryReport,
        scoreState,
        setSopExecutor,
        handleSummarize,
        handleResetExam,
        applySOPIntent,
        handleSOPPartSelect,
        handleSOPToolRequired,
        handleSOPChange,
        handleSOPStepChange,
        handleSOPContextChange,
        handleSOPBlocked,
    };
}
