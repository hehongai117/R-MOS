/**
 * @description P4 模式相关测试（红色阶段）
 */

import {
    ActionType,
    AdjudicationResult,
    PreconditionType,
    SOPScriptAdjudication,
} from '../types/adjudication';
import { createSOPExecutor, SOPExecutionState } from '../executor/sopExecutor';
import { resetStateDirect, useAdjudicationStore } from '../core/stateManager';
import { formatCountdown, isCountdownUrgent } from '../ui/examHeader';

export interface TestResult {
    name: string;
    passed: boolean;
    details: string;
}

function resetTestState(): void {
    resetStateDirect();
}

/**
 * 任务1：测试环境存储 Mock 是否就绪
 * 约定：测试入口在注入成功后设置全局标记
 */
export function runStorageMockTest(): TestResult {
    const testName = 'P4-任务1：测试环境存储 Mock 就绪';

    const ready = (globalThis as any).__RMOS_TEST_STORAGE_READY__ === true;

    return {
        name: testName,
        passed: ready,
        details: [
            `标记状态: ${ready ? '✅ 已就绪' : '❌ 未就绪'}`,
            '预期：测试入口应设置 __RMOS_TEST_STORAGE_READY__ = true',
        ].join('\n'),
    };
}

/**
 * 任务2：教学模式提示气泡数据
 * 预期：失败时返回 hint 且允许重试
 */
export function runTeachingModeHintTest(): TestResult {
    resetTestState();

    const testName = 'P4-任务2：教学模式失败返回提示并允许重试';

    const store = useAdjudicationStore.getState();
    store.setOperationMode('teaching');

    const sop: SOPScriptAdjudication = {
        sopId: 'sop_teaching_hint_test',
        title: 'Teaching Hint Test',
        version: '1.0.0',
        targetModule: 'foot',
        estimatedTime: 10,
        difficulty: 'beginner',
        steps: [
            {
                stepId: 'step_001',
                stepIndex: 0,
                title: '制造前置条件失败',
                description: '用于触发教学提示',
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
                        code: 'ERR_HINT_TEST',
                        category: 'wrong_order' as any,
                        description: '测试用错误',
                        severity: 'minor',
                        teachingResponse: {
                            showHint: true,
                            hintContent: '请先移除软胶，再继续拆卸。',
                            allowRetry: true,
                        },
                        examResponse: {
                            deductPoints: 5,
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
    const hint = (report as any).hint;
    const allowRetry = (report as any).allowRetry;

    const passed = report.result !== AdjudicationResult.ALLOWED &&
        hint === '请先移除软胶，再继续拆卸。' &&
        allowRetry === true;

    return {
        name: testName,
        passed,
        details: [
            `执行结果: ${report.result}`,
            `hint: ${hint ?? '空'}`,
            `allowRetry: ${String(allowRetry)}`,
            '预期：hint 不为空且 allowRetry=true',
        ].join('\n'),
    };
}

export function runAllP4Tests(): {
    results: TestResult[];
    passed: number;
    failed: number;
    total: number;
} {
    const results: TestResult[] = [
        runStorageMockTest(),
        runTeachingModeHintTest(),
        runTeachingRetryTest(),
        runExamHeaderFormatTest(),
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
 * 教学模式重试：失败后可调用 retryStep 回到 IDLE
 */
export function runTeachingRetryTest(): TestResult {
    resetTestState();

    const testName = 'P4-任务4：教学模式失败后允许重试';

    const store = useAdjudicationStore.getState();
    store.setOperationMode('teaching');

    const sop: SOPScriptAdjudication = {
        sopId: 'sop_teaching_retry_test',
        title: 'Teaching Retry Test',
        version: '1.0.0',
        targetModule: 'foot',
        estimatedTime: 10,
        difficulty: 'beginner',
        steps: [
            {
                stepId: 'step_001',
                stepIndex: 0,
                title: '制造前置条件失败',
                description: '用于触发重试',
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
                        code: 'ERR_HINT_TEST',
                        category: 'wrong_order' as any,
                        description: '测试用错误',
                        severity: 'minor',
                        teachingResponse: {
                            showHint: true,
                            hintContent: '请先移除软胶，再继续拆卸。',
                            allowRetry: true,
                        },
                        examResponse: {
                            deductPoints: 5,
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

    executor.executeStep();
    const retryResult = (executor as any).retryStep?.();
    const state = executor.getContext()?.executionState;

    const passed = retryResult === true && state === SOPExecutionState.IDLE;

    return {
        name: testName,
        passed,
        details: [
            `retryStep 返回: ${String(retryResult)}`,
            `当前状态: ${String(state)}`,
            '预期：retryStep=true 且状态回到 IDLE',
        ].join('\n'),
    };
}

/**
 * 考试倒计时工具函数
 */
export function runExamHeaderFormatTest(): TestResult {
    const testName = 'P4-任务4：考试倒计时格式与紧急判定';

    const timeText = formatCountdown(4 * 60 * 1000);
    const urgent = isCountdownUrgent(4 * 60 * 1000);

    const passed = timeText === '04:00' && urgent === true;

    return {
        name: testName,
        passed,
        details: [
            `格式: ${timeText}`,
            `紧急: ${String(urgent)}`,
            '预期：04:00 且 urgent=true',
        ].join('\n'),
    };
}
