/**
 * @description SOP 交互推进门控测试
 * @module adjudication/__tests__/interactionGate.test
 */

import { shouldAutoValidateAfterInteraction } from '../ui/interactionGate';
import {
    ActionType,
    AdjudicationState,
    SOPStepAdjudication,
    ScrewState,
    SystemState,
} from '../types/adjudication';

interface TestResult {
    name: string;
    passed: boolean;
    details: string;
}

type InteractionState = Pick<AdjudicationState, 'partStates' | 'screwStates'>;

function makeState(): InteractionState {
    return {
        partStates: {},
        screwStates: {},
    };
}

function makeStep(action: ActionType, targetParts: string[]): SOPStepAdjudication {
    return {
        stepId: 'step_test',
        stepIndex: 1,
        title: 'test',
        description: 'test',
        action,
        targetParts,
        requiredTool: null,
        preconditions: [],
        validations: [],
        failureReasons: [],
        onSuccess: {
            nextStepId: 'end',
            stateTransition: SystemState.VERIFICATION,
        },
        onFailure: {
            action: 'block',
            message: 'blocked',
        },
    };
}

function runMultiScrewPartialTest(): TestResult {
    const state = makeState();
    const step = makeStep(ActionType.ROTATE_SCREW, ['s1', 's2', 's3']);
    state.screwStates.s1 = {
        screwId: 's1',
        state: ScrewState.EXTRACTED,
        currentRotations: 0,
        zDisplacement: 0,
    };
    state.screwStates.s2 = {
        screwId: 's2',
        state: ScrewState.SEATED,
        currentRotations: 0,
        zDisplacement: 0,
    };
    state.screwStates.s3 = {
        screwId: 's3',
        state: ScrewState.SEATED,
        currentRotations: 0,
        zDisplacement: 0,
    };

    const shouldValidate = shouldAutoValidateAfterInteraction(step, state);

    return {
        name: 'Interaction Gate: 多螺丝步骤未完成时不自动验证',
        passed: shouldValidate === false,
        details: `shouldValidate=${shouldValidate}`,
    };
}

function runMultiScrewCompleteTest(): TestResult {
    const state = makeState();
    const step = makeStep(ActionType.ROTATE_SCREW, ['s1', 's2', 's3']);
    ['s1', 's2', 's3'].forEach((id) => {
        state.screwStates[id] = {
            screwId: id,
            state: ScrewState.EXTRACTED,
            currentRotations: 0,
            zDisplacement: 0,
        };
    });

    const shouldValidate = shouldAutoValidateAfterInteraction(step, state);

    return {
        name: 'Interaction Gate: 多螺丝步骤完成后自动验证',
        passed: shouldValidate === true,
        details: `shouldValidate=${shouldValidate}`,
    };
}

function runMultiPartRemovalTest(): TestResult {
    const state = makeState();
    const step = makeStep(ActionType.REMOVE_PART, ['p1', 'p2']);
    state.partStates.p1 = { isRemoved: true, isDetached: true };
    state.partStates.p2 = { isRemoved: false, isDetached: false };

    const partial = shouldAutoValidateAfterInteraction(step, state);
    state.partStates.p2 = { isRemoved: true, isDetached: true };
    const completed = shouldAutoValidateAfterInteraction(step, state);

    const passed = partial === false && completed === true;

    return {
        name: 'Interaction Gate: 多零件移除步骤按完成度推进',
        passed,
        details: `partial=${partial}, completed=${completed}`,
    };
}

function runFocusStepTest(): TestResult {
    const state = makeState();
    const step = makeStep(ActionType.FOCUS_CAMERA, ['torso_link']);
    const shouldValidate = shouldAutoValidateAfterInteraction(step, state);

    return {
        name: 'Interaction Gate: 非累积步骤命中后可直接验证',
        passed: shouldValidate === true,
        details: `shouldValidate=${shouldValidate}`,
    };
}

export function runAllInteractionGateTests(): {
    total: number;
    passed: number;
    failed: number;
    results: TestResult[];
} {
    const results: TestResult[] = [
        runMultiScrewPartialTest(),
        runMultiScrewCompleteTest(),
        runMultiPartRemovalTest(),
        runFocusStepTest(),
    ];
    const passed = results.filter((result) => result.passed).length;
    const failed = results.length - passed;

    return {
        total: results.length,
        passed,
        failed,
        results,
    };
}
