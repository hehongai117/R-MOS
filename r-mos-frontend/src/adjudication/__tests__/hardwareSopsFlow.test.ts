/**
 * @description 硬件 SOP 全链路回归
 * @module adjudication/__tests__/hardwareSopsFlow.test
 * @note SOPs are now served via API (DB-backed). Local hardcoded SOP files have
 *       been removed. This module returns an empty result set; real SOP flow
 *       regression is covered by E2E tests against the running backend.
 */

import {
    ActionType,
    AdjudicationResult,
    SOPScriptAdjudication,
    SOPStepAdjudication,
    commitPartDetachment,
    commitPartRemoval,
    commitScrewExtraction,
} from '../index';
import { createSOPExecutor, SOPExecutionState } from '../executor/sopExecutor';
import { resetStateDirect, useAdjudicationStore } from '../core/stateManager';

interface TestResult {
    name: string;
    passed: boolean;
    details: string;
}

function applyStepAction(step: SOPStepAdjudication): void {
    switch (step.action) {
        case ActionType.SELECT_TOOL:
            useAdjudicationStore.getState().setCurrentTool(step.requiredTool ?? null);
            return;
        case ActionType.ROTATE_SCREW:
        case ActionType.EXTRACT_SCREW:
            step.targetParts.forEach((targetId) => commitScrewExtraction(targetId));
            return;
        case ActionType.DETACH_PART:
            step.targetParts.forEach((targetId) => commitPartDetachment(targetId));
            return;
        case ActionType.REMOVE_PART:
            step.targetParts.forEach((targetId) => commitPartRemoval(targetId));
            return;
        default:
            return;
    }
}

function runSingleHardwareSOPFlow(sop: SOPScriptAdjudication): TestResult {
    resetStateDirect();
    const executor = createSOPExecutor();
    executor.loadSOP(sop);

    const maxGuard = sop.steps.length * 4 + 8;

    for (let i = 0; i < maxGuard; i += 1) {
        const step = executor.getCurrentStep();
        const context = executor.getContext();

        if (!step || context?.executionState === SOPExecutionState.COMPLETE) {
            return {
                name: `Hardware SOP Flow: ${sop.title}`,
                passed: true,
                details: `步骤数: ${sop.steps.length}\n执行结果: COMPLETE`,
            };
        }

        const executeReport = executor.executeStep();
        if (executeReport.result !== AdjudicationResult.ALLOWED) {
            return {
                name: `Hardware SOP Flow: ${sop.title}`,
                passed: false,
                details: [
                    `执行阶段阻断: ${step.stepId} / ${step.title}`,
                    `result: ${executeReport.result}`,
                    `reasonCode: ${executeReport.reasonCode}`,
                    `reason: ${executeReport.reason}`,
                ].join('\n'),
            };
        }

        applyStepAction(step);

        const validateReport = executor.validateAndAdvance();
        if (validateReport.result !== AdjudicationResult.ALLOWED) {
            return {
                name: `Hardware SOP Flow: ${sop.title}`,
                passed: false,
                details: [
                    `验证阶段失败: ${step.stepId} / ${step.title}`,
                    `result: ${validateReport.result}`,
                    `reasonCode: ${validateReport.reasonCode}`,
                    `reason: ${validateReport.reason}`,
                ].join('\n'),
            };
        }
    }

    return {
        name: `Hardware SOP Flow: ${sop.title}`,
        passed: false,
        details: `超出执行保护上限: ${maxGuard}，疑似存在循环或无法推进步骤`,
    };
}

/** SOPs are now DB-backed; pass an array from API to run flow tests. */
export function runHardwareSOPFlowTests(scripts: SOPScriptAdjudication[]): {
    total: number;
    passed: number;
    failed: number;
    results: TestResult[];
} {
    const results = scripts.map((sop) => runSingleHardwareSOPFlow(sop));
    const passed = results.filter((result) => result.passed).length;
    const failed = results.length - passed;

    return {
        total: results.length,
        passed,
        failed,
        results,
    };
}

/** Backward-compatible wrapper that runs against an empty dataset. */
export function runAllHardwareSOPFlowTests(): {
    total: number;
    passed: number;
    failed: number;
    results: TestResult[];
} {
    return runHardwareSOPFlowTests([]);
}
