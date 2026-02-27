/**
 * @description SOP 交互推进门控：多目标步骤需全部完成后才自动验证推进
 * @module adjudication/ui/interactionGate
 */

import {
    ActionType,
    AdjudicationState,
    SOPStepAdjudication,
    ScrewState,
} from '../types/adjudication';

type InteractionState = Pick<AdjudicationState, 'partStates' | 'screwStates'>;

function isScrewComplete(screwId: string, state: InteractionState): boolean {
    const screwState = state.screwStates[screwId]?.state;
    return screwState === ScrewState.EXTRACTED || screwState === ScrewState.REMOVED;
}

function isPartDetached(partId: string, state: InteractionState): boolean {
    return state.partStates[partId]?.isDetached ?? false;
}

function isPartRemoved(partId: string, state: InteractionState): boolean {
    return state.partStates[partId]?.isRemoved ?? false;
}

/**
 * 当前交互是否已经满足“可自动验证推进”的条件。
 * - 螺丝/拆件多目标步骤：必须全部目标完成
 * - 其他步骤：命中一次交互即可触发验证
 */
export function shouldAutoValidateAfterInteraction(
    step: SOPStepAdjudication,
    state: InteractionState,
): boolean {
    if (step.targetParts.length === 0) {
        return true;
    }

    switch (step.action) {
        case ActionType.ROTATE_SCREW:
        case ActionType.EXTRACT_SCREW:
            return step.targetParts.every((targetId) => isScrewComplete(targetId, state));
        case ActionType.DETACH_PART:
            return step.targetParts.every((targetId) => isPartDetached(targetId, state));
        case ActionType.REMOVE_PART:
            return step.targetParts.every((targetId) => isPartRemoved(targetId, state));
        default:
            return true;
    }
}
