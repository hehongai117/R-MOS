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

/**
 * @deprecated 硬编码的 SOP 模块→默认零件映射。
 * 请改用 buildModuleDefaultParts(manifest) 从机器人数据清单动态推导。
 * 当 manifest 可用时，此表仅作 fallback 兜底。
 */
const SOP_MODULE_DEFAULT_PART: Record<string, string> = {
    torso: 'torso_link',
    left_arm: 'left_arm_pitch_link',
    right_arm: 'right_arm_pitch_link',
    left_leg: 'left_thigh_pitch_link',
    right_leg: 'right_thigh_pitch_link',
    base: 'base_link',
};

/**
 * 从 manifest 的 overview_config.assembly_groups 动态推导 SOP 模块默认零件映射。
 *
 * 每个分组的 child_links[0] 即为该模块的默认高亮零件。
 * 分组 key（link ID）通过正则归一化为简短模块名（如 left_arm_yaw_link → left_arm）。
 *
 * @returns 映射表，若 manifest 无分组信息则返回 null（调用方应 fallback 到硬编码表）
 */
export function buildModuleDefaultParts(
    manifest: { overview_config?: { assembly_groups?: Record<string, { child_links: string[] }> } } | null
): Record<string, string> | null {
    const groups = manifest?.overview_config?.assembly_groups;
    if (!groups) return null;

    const result: Record<string, string> = {};
    for (const [groupKey, group] of Object.entries(groups)) {
        if (group.child_links.length === 0) continue;
        // 从 group key（link ID）推断简短模块名
        const shortName = groupKey
            .replace(/_yaw_link$|_pitch_link$|_roll_link$|_link$/, '')  // 去掉 joint/link 后缀
            .replace(/^(left|right)_thigh.*/, '$1_leg')                  // left_thigh → left_leg
            .replace(/^(left|right)_knee.*/, '$1_leg')                   // left_knee → left_leg
            .replace(/^(left|right)_ankle.*/, '$1_leg')                  // left_ankle → left_leg
            .replace(/^(left|right)_elbow.*/, '$1_arm')                  // left_elbow → left_arm
            .replace(/^(left|right)_arm.*/, '$1_arm');                   // left_arm_yaw → left_arm
        if (shortName) {
            // 先到先得：同一 shortName 只保留第一个分组的默认零件
            if (!(shortName in result)) {
                result[shortName] = group.child_links[0];
            }
        }
    }
    return Object.keys(result).length > 0 ? result : null;
}

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
