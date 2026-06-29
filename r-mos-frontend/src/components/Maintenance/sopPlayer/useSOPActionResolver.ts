/**
 * useSOPActionResolver.ts — SOP アクション解析フック
 *
 * normalizeSpec / resolveScrewTargetId / resolvePartTargetId / handleActionEvent
 * をカプセル化する純粋ロジックフック。
 */

import { useCallback } from 'react';
import {
    ActionType,
    SOPStepAdjudication,
    commitPartDetachment,
    commitPartRemoval,
    commitScrewExtraction,
    getScrewInstance,
    ScrewState,
    useAdjudicationStore,
} from '@/adjudication';
import type { SOPActionEvent } from '../SOPPlayerAdjudicated';
import { PART_TARGET_ALIASES } from './sopPlayerConfig';

export interface UseSOPActionResolverResult {
    normalizeSpec: (value: string) => string;
    resolveScrewTargetId: (step: SOPStepAdjudication, rawScrewId: string) => string | null;
    resolvePartTargetId: (step: SOPStepAdjudication, rawPartId: string) => string | null;
    handleActionEvent: (event: SOPActionEvent) => boolean;
}

export function useSOPActionResolver(currentStep: SOPStepAdjudication | null): UseSOPActionResolverResult {
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

    return {
        normalizeSpec,
        resolveScrewTargetId,
        resolvePartTargetId,
        handleActionEvent,
    };
}
