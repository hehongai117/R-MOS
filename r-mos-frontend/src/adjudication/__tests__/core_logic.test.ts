/**
 * @description P3 核心逻辑测试用例
 * @module adjudication/__tests__/core_logic.test
 */

import {
    AdjudicationResult,
    ActionType,
    PreconditionType,
    SOPScriptAdjudication,
    SystemState,
} from '../types/adjudication';
import { adjudicateAction } from '../core/decisionEngine';
import { createSOPExecutor } from '../executor/sopExecutor';
import { resetStateDirect, useAdjudicationStore } from '../core/stateManager';

function resetTestState(): void {
    resetStateDirect();
}

export function runConstraintBlockingTest(): {
    name: string;
    passed: boolean;
    details: string;
} {
    resetTestState();

    const testName = 'P3-B.2: ACTIVE 约束必须强制阻断';

    const report = adjudicateAction(ActionType.DETACH_PART, 'frame_torso_chest');

    const blocked = report.result === AdjudicationResult.BLOCKED;
    const codeOk = report.reasonCode === 'ERR_CONSTRAINT';
    const hasConstraint = report.blockingConstraints.some(c => c.id === 'constraint_torso_chest_fastened');

    return {
        name: testName,
        passed: blocked && codeOk && hasConstraint,
        details: [
            `结果: ${report.result}`,
            `原因码: ${report.reasonCode}`,
            `阻断约束: ${report.blockingConstraints.map(c => c.id).join(', ') || '无'}`,
            `验证: ${blocked && codeOk ? '✅ 触发阻断' : '❌ 未正确阻断'}`,
        ].join('\n'),
    };
}

export function runIrreversibleRollbackTest(): {
    name: string;
    passed: boolean;
    details: string;
} {
    resetTestState();

    const testName = 'P3-C.2: 不可逆步骤禁止回滚';

    const sop: SOPScriptAdjudication = {
        sopId: 'sop_irreversible_test',
        title: 'Irreversible Rollback Test',
        version: '1.0.0',
        targetModule: 'torso',
        estimatedTime: 20,
        difficulty: 'beginner',
        steps: [
            {
                stepId: 'step_001',
                stepIndex: 0,
                title: '占位步骤',
                description: '用于推进到不可逆步骤',
                action: ActionType.SELECT_TOOL,
                targetParts: [],
                requiredTool: null,
                preconditions: [],
                validations: [],
                failureReasons: [],
                onSuccess: { nextStepId: 'step_002', stateTransition: null },
                onFailure: { action: 'block', message: '阻断' },
            },
            {
                stepId: 'step_002',
                stepIndex: 1,
                title: '不可逆步骤',
                description: '进入执行后禁止回滚',
                action: ActionType.SELECT_TOOL,
                targetParts: [],
                requiredTool: null,
                preconditions: [
                    {
                        type: PreconditionType.PREVIOUS_STEP_COMPLETE,
                        params: {},
                        errorMessage: '',
                    },
                ],
                validations: [],
                failureReasons: [],
                onSuccess: { nextStepId: 'end', stateTransition: null },
                onFailure: { action: 'block', message: '阻断' },
                isIrreversible: true,
            },
        ],
    };

    const executor = createSOPExecutor();
    executor.loadSOP(sop);

    executor.executeStep();
    executor.validateAndAdvance();

    executor.executeStep(); // 进入不可逆步骤执行态

    let threw = false;
    try {
        executor.goToStep(0);
    } catch (error) {
        threw = true;
    }

    return {
        name: testName,
        passed: threw,
        details: [
            `回滚结果: ${threw ? '✅ 抛出异常' : '❌ 未阻止回滚'}`,
        ].join('\n'),
    };
}

export function runFatalFailureLockTest(): {
    name: string;
    passed: boolean;
    details: string;
} {
    resetTestState();

    const testName = 'P3-FAILED_FATAL: 致命失败锁死';

    const sop: SOPScriptAdjudication = {
        sopId: 'sop_fatal_lock_test',
        title: 'Fatal Lock Test',
        version: '1.0.0',
        targetModule: 'torso',
        estimatedTime: 10,
        difficulty: 'beginner',
        steps: [
            {
                stepId: 'step_001',
                stepIndex: 0,
                title: '制造失败触发致命',
                description: '故意违反前置条件触发 fatal',
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
                onSuccess: { nextStepId: 'end', stateTransition: null },
                onFailure: { action: 'block', message: '阻断' },
                fatalOnFailure: true,
            },
        ],
    };

    const executor = createSOPExecutor();
    executor.loadSOP(sop);

    const report = executor.executeStep();
    const systemState = useAdjudicationStore.getState().systemState;
    const fatalTriggered = systemState === SystemState.FAILED_FATAL;
    const blockedAfter = executor.canExecuteStep();

    return {
        name: testName,
        passed: report.result !== AdjudicationResult.ALLOWED &&
            fatalTriggered &&
            blockedAfter.result === AdjudicationResult.BLOCKED,
        details: [
            `执行结果: ${report.result}`,
            `系统状态: ${systemState}`,
            `再次执行检查: ${blockedAfter.result}`,
        ].join('\n'),
    };
}

export interface TestResult {
    name: string;
    passed: boolean;
    details: string;
}

export function runAllCoreLogicTests(): {
    results: TestResult[];
    passed: number;
    failed: number;
    total: number;
} {
    const results: TestResult[] = [
        runConstraintBlockingTest(),
        runIrreversibleRollbackTest(),
        runFatalFailureLockTest(),
    ];

    const passed = results.filter(r => r.passed).length;
    const failed = results.filter(r => !r.passed).length;

    return {
        results,
        passed,
        failed,
        total: results.length,
    };
}
