import { useCallback, useMemo, useState } from 'react';
import { PART_METADATA } from '@/components/Viewer3D/Atom01Interactive';
import {
    getScrewInstance,
    type SOPScriptAdjudication,
    type SOPStepAdjudication,
    type AdjudicationReport,
    type SOPExecutionContext,
    SOPExecutionState,
    ActionType,
} from '@/adjudication';

export interface SOPSceneIntent {
    targetPart: string | null;
    explodeAmount: number;
    requiredTool: string | null;
}

export interface SOPSceneSyncState {
    selectedSopId: string | null;
    selectedSopTitle: string | null;
    currentStepIndex: number;
    totalSteps: number;
    currentStepTitle: string | null;
    executionState: SOPExecutionState | null;
    blockedReason: string | null;
    intent: SOPSceneIntent;
}

const DEFAULT_INTENT: SOPSceneIntent = {
    targetPart: null,
    explodeAmount: 0,
    requiredTool: null,
};

const DEFAULT_STATE: SOPSceneSyncState = {
    selectedSopId: null,
    selectedSopTitle: null,
    currentStepIndex: 0,
    totalSteps: 0,
    currentStepTitle: null,
    executionState: null,
    blockedReason: null,
    intent: DEFAULT_INTENT,
};

const SOP_MODULE_DEFAULT_PART: Record<string, string> = {
    torso: 'torso_link',
    left_arm: 'left_arm_pitch_link',
    right_arm: 'right_arm_pitch_link',
    left_leg: 'left_thigh_pitch_link',
    right_leg: 'right_thigh_pitch_link',
    base: 'base_link',
};

function clamp(value: number, min: number, max: number): number {
    return Math.min(max, Math.max(min, value));
}

function parseExplodePercent(step: SOPStepAdjudication): number | null {
    const sourceText = `${step.title} ${step.description}`;
    const matched = sourceText.match(/(\d{1,3})\s*%/);
    if (!matched) return null;
    const parsed = Number(matched[1]);
    if (!Number.isFinite(parsed)) return null;
    return clamp(parsed / 100, 0, 1);
}

function resolveTargetPart(step: SOPStepAdjudication): string | null {
    for (const rawTarget of step.targetParts) {
        if (PART_METADATA[rawTarget]) {
            return rawTarget;
        }
        const screw = getScrewInstance(rawTarget);
        if (screw?.parentId && PART_METADATA[screw.parentId]) {
            return screw.parentId;
        }
    }
    return null;
}

function deriveExplodeAmount(step: SOPStepAdjudication, targetPart: string | null): number {
    const sourceText = `${step.title} ${step.description}`;
    if (/收起|恢复正常|复位/.test(sourceText)) {
        return 0;
    }
    const fromText = parseExplodePercent(step);
    if (fromText !== null) return fromText;

    switch (step.action) {
        case ActionType.REMOVE_PART:
        case ActionType.DETACH_PART:
            return 0.62;
        case ActionType.EXTRACT_SCREW:
        case ActionType.ROTATE_SCREW:
            return 0.46;
        case ActionType.FOCUS_CAMERA:
            return targetPart ? 0.32 : 0;
        case ActionType.SELECT_TOOL:
            return 0;
        default:
            return targetPart ? 0.42 : 0.2;
    }
}

function buildIntent(step: SOPStepAdjudication | null): SOPSceneIntent {
    if (!step) return DEFAULT_INTENT;
    const targetPart = resolveTargetPart(step);
    return {
        targetPart,
        explodeAmount: deriveExplodeAmount(step, targetPart),
        requiredTool: step.requiredTool ?? null,
    };
}

export function useSOPSceneSync() {
    const [state, setState] = useState<SOPSceneSyncState>(DEFAULT_STATE);

    const bindSOP = useCallback((sop: SOPScriptAdjudication | null) => {
        if (!sop) {
            setState(DEFAULT_STATE);
            return null;
        }

        const firstStep = sop.steps[0] ?? null;
        const firstIntent = buildIntent(firstStep);
        const inferredTargetPart = SOP_MODULE_DEFAULT_PART[sop.targetModule] ?? null;
        const initialIntent: SOPSceneIntent = {
            targetPart: firstIntent.targetPart ?? inferredTargetPart,
            explodeAmount: firstIntent.explodeAmount,
            requiredTool: firstIntent.requiredTool,
        };
        const nextState: SOPSceneSyncState = {
            selectedSopId: sop.sopId,
            selectedSopTitle: sop.title,
            currentStepIndex: 0,
            totalSteps: sop.steps.length,
            currentStepTitle: firstStep?.title ?? null,
            executionState: SOPExecutionState.IDLE,
            blockedReason: null,
            intent: initialIntent,
        };
        setState(nextState);
        return initialIntent;
    }, []);

    const bindStep = useCallback((step: SOPStepAdjudication | null, stepIndex: number) => {
        const baseIntent = buildIntent(step);
        let nextIntent: SOPSceneIntent = baseIntent;
        setState((prev) => {
            nextIntent = {
                targetPart: baseIntent.targetPart ?? prev.intent.targetPart,
                explodeAmount: baseIntent.explodeAmount,
                requiredTool: baseIntent.requiredTool,
            };
            return {
                ...prev,
                currentStepIndex: step ? stepIndex : 0,
                currentStepTitle: step?.title ?? null,
                blockedReason: null,
                intent: nextIntent,
            };
        });
        return nextIntent;
    }, []);

    const bindContext = useCallback((context: SOPExecutionContext | null) => {
        setState((prev) => ({
            ...prev,
            executionState: context?.executionState ?? null,
            currentStepIndex: context?.currentStepIndex ?? prev.currentStepIndex,
        }));
    }, []);

    const bindBlocked = useCallback((report: AdjudicationReport | null) => {
        if (!report) return;
        setState((prev) => ({
            ...prev,
            blockedReason: report.reason,
            executionState: SOPExecutionState.BLOCKED,
        }));
    }, []);

    const progressText = useMemo(() => {
        if (!state.totalSteps) return '未选择 SOP';
        const current = clamp(state.currentStepIndex + 1, 1, state.totalSteps);
        return `${current}/${state.totalSteps}`;
    }, [state.currentStepIndex, state.totalSteps]);

    return {
        state,
        progressText,
        bindSOP,
        bindStep,
        bindContext,
        bindBlocked,
    };
}
