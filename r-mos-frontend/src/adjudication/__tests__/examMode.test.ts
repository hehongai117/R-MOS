/**
 * @description P4 考试模式相关测试（红色阶段）
 */

import {
    ActionType,
    PreconditionType,
    SOPScriptAdjudication,
    SystemState,
} from '../types/adjudication';
import { scoringEngine } from '../core/scoringEngine';
import { createSOPExecutor } from '../executor/sopExecutor';
import { resetStateDirect, useAdjudicationStore } from '../core/stateManager';

export interface TestResult {
    name: string;
    passed: boolean;
    details: string;
}

export function runExamScoreDeductTest(): TestResult {
    const testName = 'P4-任务2：考试模式扣分后分数下降';

    scoringEngine.reset(100);
    scoringEngine.deduct('step_001', 'ERR_WRONG_TOOL', 10);

    const state = scoringEngine.getState();
    const first = state.deductions[0];

    const passed = state.currentScore === 90 &&
        state.deductions.length === 1 &&
        first.stepId === 'step_001' &&
        first.reason === 'ERR_WRONG_TOOL' &&
        first.score === 10;

    return {
        name: testName,
        passed,
        details: [
            `当前分数: ${state.currentScore}`,
            `扣分记录数: ${state.deductions.length}`,
            `首条记录: ${first ? `${first.stepId}/${first.reason}/${first.score}` : '空'}`,
            '预期：currentScore=90 且扣分记录完整',
        ].join('\n'),
    };
}

export function runAllExamModeTests(): {
    results: TestResult[];
    passed: number;
    failed: number;
    total: number;
} {
    const results: TestResult[] = [
        runExamScoreDeductTest(),
        runExamForceCorrectionTest(),
        runExamFatalCircuitBreakerTest(),
        runExamFatalWithoutFlagTest(),
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

/**
 * allowContinue=false 即致命（不依赖 fatalOnFailure）
 */
export function runExamFatalWithoutFlagTest(): TestResult {
    resetTestState();

    const testName = 'P4-任务3：考试模式 allowContinue=false 直接熔断';

    const store = useAdjudicationStore.getState();
    store.setOperationMode('exam');

    const sop: SOPScriptAdjudication = {
        sopId: 'sop_exam_fatal_no_flag',
        title: 'Exam Fatal Without Flag',
        version: '1.0.0',
        targetModule: 'foot',
        estimatedTime: 10,
        difficulty: 'beginner',
        steps: [
            {
                stepId: 'step_001',
                stepIndex: 0,
                title: '制造严重错误',
                description: 'allowContinue=false 直接熔断',
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
                failureReasons: [
                    {
                        code: 'ERR_FATAL_NO_FLAG',
                        category: 'unsafe' as any,
                        description: '严重错误',
                        severity: 'critical',
                        teachingResponse: {
                            showHint: true,
                            hintContent: '教学提示不应出现',
                            allowRetry: true,
                        },
                        examResponse: {
                            deductPoints: 100,
                            allowContinue: false,
                            recordToReport: true,
                        },
                    },
                ],
                onSuccess: { nextStepId: 'end', stateTransition: null },
                onFailure: { action: 'block', message: '阻断' },
            },
        ],
    };

    const executor = createSOPExecutor();
    executor.loadSOP(sop);

    const report = executor.executeStep();
    const systemState = useAdjudicationStore.getState().systemState;
    const shouldSummarize = (report as any).shouldSummarize;

    const passed = systemState === SystemState.FAILED_FATAL && shouldSummarize === true;

    return {
        name: testName,
        passed,
        details: [
            `系统状态: ${systemState}`,
            `结算信号: ${String(shouldSummarize)}`,
            '预期：FAILED_FATAL + shouldSummarize=true',
        ].join('\n'),
    };
}

function resetTestState(): void {
    resetStateDirect();
    scoringEngine.reset(100);
}

/**
 * 强制修正：考试模式普通错误 → 扣分 + 不允许重试
 */
export function runExamForceCorrectionTest(): TestResult {
    resetTestState();

    const testName = 'P4-任务3：考试模式普通错误强制修正';

    const store = useAdjudicationStore.getState();
    store.setOperationMode('exam');

    const sop: SOPScriptAdjudication = {
        sopId: 'sop_exam_force_correction',
        title: 'Exam Force Correction',
        version: '1.0.0',
        targetModule: 'foot',
        estimatedTime: 10,
        difficulty: 'beginner',
        steps: [
            {
                stepId: 'step_001',
                stepIndex: 0,
                title: '制造前置条件失败',
                description: '用于触发考试扣分',
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
                failureReasons: [
                    {
                        code: 'ERR_EXAM_FORCE',
                        category: 'wrong_order' as any,
                        description: '测试用错误',
                        severity: 'major',
                        teachingResponse: {
                            showHint: true,
                            hintContent: '教学提示不应出现',
                            allowRetry: true,
                        },
                        examResponse: {
                            deductPoints: 10,
                            allowContinue: true,
                            recordToReport: true,
                        },
                    },
                ],
                onSuccess: { nextStepId: 'end', stateTransition: null },
                onFailure: { action: 'block', message: '阻断' },
            },
        ],
    };

    const executor = createSOPExecutor();
    executor.loadSOP(sop);

    const report = executor.executeStep();
    const scoreState = scoringEngine.getState();
    const allowRetry = (report as any).allowRetry;

    const passed = report.result === 'blocked' &&
        allowRetry !== true &&
        scoreState.currentScore === 90;

    return {
        name: testName,
        passed,
        details: [
            `执行结果: ${report.result}`,
            `allowRetry: ${String(allowRetry)}`,
            `当前分数: ${scoreState.currentScore}`,
            '预期：BLOCKED 且 allowRetry != true，分数从 100 降至 90',
        ].join('\n'),
    };
}

/**
 * 致命熔断：fatalOnFailure 触发 FAILED_FATAL + 结算信号
 */
export function runExamFatalCircuitBreakerTest(): TestResult {
    resetTestState();

    const testName = 'P4-任务3：考试模式致命熔断';

    const store = useAdjudicationStore.getState();
    store.setOperationMode('exam');

    const sop: SOPScriptAdjudication = {
        sopId: 'sop_exam_fatal',
        title: 'Exam Fatal',
        version: '1.0.0',
        targetModule: 'foot',
        estimatedTime: 10,
        difficulty: 'beginner',
        steps: [
            {
                stepId: 'step_001',
                stepIndex: 0,
                title: '制造致命失败',
                description: '触发 fatalOnFailure',
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
                failureReasons: [
                    {
                        code: 'ERR_FATAL_TEST',
                        category: 'unsafe' as any,
                        description: '测试致命错误',
                        severity: 'critical',
                        teachingResponse: {
                            showHint: true,
                            hintContent: '教学提示不应出现',
                            allowRetry: true,
                        },
                        examResponse: {
                            deductPoints: 100,
                            allowContinue: false,
                            recordToReport: true,
                        },
                    },
                ],
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
    const shouldSummarize = (report as any).shouldSummarize;

    const retryReport = executor.executeStep();

    const passed = systemState === SystemState.FAILED_FATAL &&
        shouldSummarize === true &&
        retryReport.result === 'blocked';

    return {
        name: testName,
        passed,
        details: [
            `系统状态: ${systemState}`,
            `结算信号: ${String(shouldSummarize)}`,
            `再次执行: ${retryReport.result}`,
            '预期：FAILED_FATAL + shouldSummarize=true + 再次执行被阻断',
        ].join('\n'),
    };
}
