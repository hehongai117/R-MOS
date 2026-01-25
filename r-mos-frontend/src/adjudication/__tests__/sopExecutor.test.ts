/**
 * @description SOP 执行器致命失败测试
 * @module adjudication/__tests__/sopExecutor.test
 */

import {
    ActionType,
    AdjudicationResult,
    PreconditionType,
    SOPScriptAdjudication,
    SystemState,
} from '../types/adjudication';
import { createSOPExecutor } from '../executor/sopExecutor';
import { useAdjudicationStore, resetStateDirect } from '../core/stateManager';

function resetTestState(): void {
    resetStateDirect();
}

export function runFatalFailureTest(): {
    name: string;
    passed: boolean;
    details: string;
} {
    resetTestState();

    const testName = 'SOP Fatal Failure: fatalOnFailure 触发系统锁死';

    const sop: SOPScriptAdjudication = {
        sopId: 'sop_fatal_test',
        title: 'Fatal Failure Test',
        version: '1.0.0',
        targetModule: 'foot',
        estimatedTime: 10,
        difficulty: 'beginner',
        steps: [
            {
                stepId: 'step_001',
                stepIndex: 0,
                title: '尝试拆卸脚底板（预期失败）',
                description: '故意制造失败以触发致命错误',
                action: ActionType.DETACH_PART,
                targetParts: ['left_ankle_roll_link'],
                requiredTool: null,
                preconditions: [
                    {
                        type: PreconditionType.PART_REMOVED,
                        params: { partId: 'left_foot_rubber' },
                        errorMessage: '必须先拆除软胶',
                    },
                ],
                validations: [],
                failureReasons: [],
                onSuccess: { nextStepId: 'step_002', stateTransition: null },
                onFailure: { action: 'block', message: '阻断' },
                isIrreversible: false,
                fatalOnFailure: true,
            },
            {
                stepId: 'step_002',
                stepIndex: 1,
                title: '占位步骤',
                description: '不应被执行',
                action: ActionType.REMOVE_PART,
                targetParts: ['left_ankle_roll_link'],
                requiredTool: null,
                preconditions: [],
                validations: [],
                failureReasons: [],
                onSuccess: { nextStepId: 'end', stateTransition: null },
                onFailure: { action: 'block', message: '阻断' },
                isIrreversible: false,
            },
        ],
    };

    const executor = createSOPExecutor();
    executor.loadSOP(sop);

    const report = executor.executeStep();
    const systemState = useAdjudicationStore.getState().systemState;
    const fatalTriggered = systemState === SystemState.FAILED_FATAL;

    const secondCheck = executor.canExecuteStep();
    const blockedAfterFatal = secondCheck.result === AdjudicationResult.BLOCKED;

    return {
        name: testName,
        passed: report.result !== AdjudicationResult.ALLOWED && fatalTriggered && blockedAfterFatal,
        details: [
            `初始执行结果: ${report.result}`,
            `系统状态: ${systemState}`,
            `再次执行检查: ${secondCheck.result}`,
            '说明: 未设置教学/考试模式，逻辑层依然判死',
        ].join('\n'),
    };
}
