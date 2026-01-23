/**
 * @description SOP 执行器 - 状态机驱动的 SOP 执行
 * @module adjudication/executor/sopExecutor
 * 
 * 基于规范文档 §5 L4: SOP 状态机层
 * 
 * 核心流程：
 * IDLE → PRECONDITION_CHECK → EXECUTING → VALIDATION → [COMPLETE | FAILED]
 *                ↓                          ↓
 *            BLOCKED                    INCOMPLETE
 */

import {
    SOPStepAdjudication,
    SOPScriptAdjudication,
    SOPPrecondition,
    SOPValidation,
    PreconditionType,
    ValidationType,
    ActionType,
    AdjudicationResult,
    AdjudicationReport,
    SystemState,
} from '../types/adjudication';
import { useAdjudicationStore } from '../core/stateManager';
import { adjudicateAction } from '../core/decisionEngine';
import { isScrewExtracted } from '../core/geometryJudge';

// ============================================================
// SOP 执行状态
// ============================================================

export enum SOPExecutionState {
    IDLE = 'idle',
    PRECONDITION_CHECK = 'precondition_check',
    EXECUTING = 'executing',
    VALIDATION = 'validation',
    COMPLETE = 'complete',
    FAILED = 'failed',
    BLOCKED = 'blocked',
}

export interface SOPExecutionContext {
    sopId: string;
    currentStepIndex: number;
    executionState: SOPExecutionState;
    lastReport: AdjudicationReport | null;
    startTime: number;
    stepStartTime: number;
    completedSteps: string[];
    failedSteps: string[];
}

// ============================================================
// 前置条件检查
// ============================================================

/**
 * 检查单个前置条件
 */
function checkPrecondition(precondition: SOPPrecondition): {
    passed: boolean;
    message: string;
} {
    const store = useAdjudicationStore.getState();

    switch (precondition.type) {
        case PreconditionType.PART_REMOVED: {
            const partId = precondition.params.partId as string;
            const isRemoved = store.partStates[partId]?.isRemoved ?? false;
            return {
                passed: isRemoved,
                message: isRemoved ? '' : precondition.errorMessage,
            };
        }

        case PreconditionType.PART_ACCESSIBLE: {
            const partId = precondition.params.partId as string;
            // 检查零件是否可访问（无覆盖约束）
            const report = adjudicateAction(ActionType.DETACH_PART, partId);
            const isAccessible = report.result === AdjudicationResult.ALLOWED ||
                report.result === AdjudicationResult.INCOMPLETE;
            return {
                passed: isAccessible,
                message: isAccessible ? '' : precondition.errorMessage,
            };
        }

        case PreconditionType.TOOL_EQUIPPED: {
            const toolId = precondition.params.toolId as string;
            const currentTool = store.currentToolId;
            const isEquipped = currentTool === toolId;
            return {
                passed: isEquipped,
                message: isEquipped ? '' : precondition.errorMessage,
            };
        }

        case PreconditionType.SCREWS_REMOVED: {
            const screwIds = precondition.params.screwIds as string[];
            const allRemoved = screwIds.every(id => isScrewExtracted(id));
            return {
                passed: allRemoved,
                message: allRemoved ? '' : precondition.errorMessage,
            };
        }

        case PreconditionType.STATE_REACHED: {
            const requiredState = precondition.params.state as SystemState;
            const isReached = store.systemState === requiredState;
            return {
                passed: isReached,
                message: isReached ? '' : precondition.errorMessage,
            };
        }

        case PreconditionType.PREVIOUS_STEP_COMPLETE: {
            // 这个条件由执行器内部管理
            return { passed: true, message: '' };
        }

        default:
            return { passed: false, message: '未知前置条件类型' };
    }
}

/**
 * 检查步骤的所有前置条件
 */
export function checkStepPreconditions(step: SOPStepAdjudication): {
    allPassed: boolean;
    failedConditions: { precondition: SOPPrecondition; message: string }[];
} {
    const failedConditions: { precondition: SOPPrecondition; message: string }[] = [];

    for (const precondition of step.preconditions) {
        const result = checkPrecondition(precondition);
        if (!result.passed) {
            failedConditions.push({
                precondition,
                message: result.message,
            });
        }
    }

    return {
        allPassed: failedConditions.length === 0,
        failedConditions,
    };
}

// ============================================================
// 完成验证
// ============================================================

/**
 * 检查单个验证条件
 */
function checkValidation(validation: SOPValidation): {
    passed: boolean;
    message: string;
} {
    const store = useAdjudicationStore.getState();

    switch (validation.type) {
        case ValidationType.ALL_SCREWS_EXTRACTED: {
            const screwIds = validation.params.screwIds as string[];
            const allExtracted = screwIds.every(id => isScrewExtracted(id));
            return {
                passed: allExtracted,
                message: allExtracted ? '' : '仍有螺丝未完全退出',
            };
        }

        case ValidationType.PART_DETACHED: {
            const partId = validation.params.partId as string;
            const isDetached = store.partStates[partId]?.isDetached ?? false;
            return {
                passed: isDetached,
                message: isDetached ? '' : '零件尚未分离',
            };
        }

        case ValidationType.TOOL_MATCHED: {
            const toolId = validation.params.toolId as string;
            const isMatched = store.currentToolId === toolId;
            return {
                passed: isMatched,
                message: isMatched ? '' : '工具不匹配',
            };
        }

        case ValidationType.STATE_CHECK: {
            const requiredState = validation.params.state as SystemState;
            const isReached = store.systemState === requiredState;
            return {
                passed: isReached,
                message: isReached ? '' : `未达到 ${requiredState} 状态`,
            };
        }

        default:
            return { passed: true, message: '' };
    }
}

/**
 * 验证步骤完成情况
 */
export function validateStepCompletion(step: SOPStepAdjudication): {
    allPassed: boolean;
    failedValidations: { validation: SOPValidation; message: string }[];
} {
    const failedValidations: { validation: SOPValidation; message: string }[] = [];

    for (const validation of step.validations) {
        const result = checkValidation(validation);
        if (!result.passed && validation.isRequired) {
            failedValidations.push({
                validation,
                message: result.message,
            });
        }
    }

    return {
        allPassed: failedValidations.length === 0,
        failedValidations,
    };
}

// ============================================================
// SOP 执行器类
// ============================================================

export class SOPExecutor {
    private currentSOP: SOPScriptAdjudication | null = null;
    private context: SOPExecutionContext | null = null;
    private onStateChange?: (context: SOPExecutionContext) => void;
    private onStepChange?: (step: SOPStepAdjudication | null, index: number) => void;
    private onBlocked?: (report: AdjudicationReport) => void;
    private onComplete?: () => void;
    private onFailed?: (reason: string) => void;

    constructor(options?: {
        onStateChange?: (context: SOPExecutionContext) => void;
        onStepChange?: (step: SOPStepAdjudication | null, index: number) => void;
        onBlocked?: (report: AdjudicationReport) => void;
        onComplete?: () => void;
        onFailed?: (reason: string) => void;
    }) {
        this.onStateChange = options?.onStateChange;
        this.onStepChange = options?.onStepChange;
        this.onBlocked = options?.onBlocked;
        this.onComplete = options?.onComplete;
        this.onFailed = options?.onFailed;
    }

    /**
     * 加载 SOP 脚本
     */
    loadSOP(sop: SOPScriptAdjudication): void {
        this.currentSOP = sop;
        this.context = {
            sopId: sop.sopId,
            currentStepIndex: 0,
            executionState: SOPExecutionState.IDLE,
            lastReport: null,
            startTime: Date.now(),
            stepStartTime: Date.now(),
            completedSteps: [],
            failedSteps: [],
        };
        this.notifyStateChange();
    }

    /**
     * 获取当前步骤
     */
    getCurrentStep(): SOPStepAdjudication | null {
        if (!this.currentSOP || !this.context) return null;
        return this.currentSOP.steps[this.context.currentStepIndex] || null;
    }

    /**
     * 获取执行上下文
     */
    getContext(): SOPExecutionContext | null {
        return this.context;
    }

    /**
     * 检查是否可以执行当前步骤
     */
    canExecuteStep(): AdjudicationReport {
        const step = this.getCurrentStep();
        if (!step || !this.context) {
            return {
                result: AdjudicationResult.BLOCKED,
                targetPart: '',
                reason: '无可执行步骤',
                reasonCode: 'NO_STEP',
                blockingConstraints: [],
                requiredActions: [],
                timestamp: Date.now(),
            };
        }

        // 检查前置条件
        const preconditionCheck = checkStepPreconditions(step);
        if (!preconditionCheck.allPassed) {
            const firstFailed = preconditionCheck.failedConditions[0];
            return {
                result: AdjudicationResult.BLOCKED,
                targetPart: step.targetParts[0] || '',
                reason: firstFailed.message,
                reasonCode: 'PRECONDITION_FAILED',
                blockingConstraints: [],
                requiredActions: preconditionCheck.failedConditions.map(f => f.message),
                timestamp: Date.now(),
            };
        }

        // 检查目标零件/螺丝的约束
        if (step.targetParts.length > 0) {
            const targetReport = adjudicateAction(
                step.action,
                step.targetParts[0],
                step.requiredTool
            );

            if (targetReport.result !== AdjudicationResult.ALLOWED) {
                return targetReport;
            }
        }

        return {
            result: AdjudicationResult.ALLOWED,
            targetPart: step.targetParts[0] || '',
            reason: '可以执行',
            reasonCode: 'OK',
            blockingConstraints: [],
            requiredActions: [],
            timestamp: Date.now(),
        };
    }

    /**
     * 尝试执行当前步骤
     */
    executeStep(): AdjudicationReport {
        if (!this.context) {
            return {
                result: AdjudicationResult.BLOCKED,
                targetPart: '',
                reason: '执行器未初始化',
                reasonCode: 'NOT_INITIALIZED',
                blockingConstraints: [],
                requiredActions: [],
                timestamp: Date.now(),
            };
        }

        // 更新状态为前置条件检查
        this.context.executionState = SOPExecutionState.PRECONDITION_CHECK;
        this.context.stepStartTime = Date.now();
        this.notifyStateChange();

        // 检查是否可执行
        const canExecute = this.canExecuteStep();

        if (canExecute.result !== AdjudicationResult.ALLOWED) {
            this.context.executionState = SOPExecutionState.BLOCKED;
            this.context.lastReport = canExecute;
            this.notifyStateChange();
            this.onBlocked?.(canExecute);
            return canExecute;
        }

        // 更新状态为执行中
        this.context.executionState = SOPExecutionState.EXECUTING;
        this.notifyStateChange();

        return canExecute;
    }

    /**
     * 验证步骤完成并推进
     */
    validateAndAdvance(): AdjudicationReport {
        const step = this.getCurrentStep();
        if (!step || !this.context) {
            return {
                result: AdjudicationResult.BLOCKED,
                targetPart: '',
                reason: '无可验证步骤',
                reasonCode: 'NO_STEP',
                blockingConstraints: [],
                requiredActions: [],
                timestamp: Date.now(),
            };
        }

        // 更新状态为验证中
        this.context.executionState = SOPExecutionState.VALIDATION;
        this.notifyStateChange();

        // 验证完成条件
        const validationCheck = validateStepCompletion(step);

        if (!validationCheck.allPassed) {
            const firstFailed = validationCheck.failedValidations[0];
            const report: AdjudicationReport = {
                result: AdjudicationResult.INCOMPLETE,
                targetPart: step.targetParts[0] || '',
                reason: firstFailed.message,
                reasonCode: 'VALIDATION_FAILED',
                blockingConstraints: [],
                requiredActions: validationCheck.failedValidations.map(f => f.message),
                timestamp: Date.now(),
            };

            this.context.lastReport = report;

            // 根据步骤配置处理失败
            if (step.onFailure.action === 'block') {
                this.context.executionState = SOPExecutionState.BLOCKED;
                this.notifyStateChange();
                this.onBlocked?.(report);
            }

            return report;
        }

        // 标记步骤完成
        this.context.completedSteps.push(step.stepId);

        // 状态转移
        if (step.onSuccess.stateTransition) {
            useAdjudicationStore.getState().setSystemState(step.onSuccess.stateTransition);
        }

        // 检查是否有下一步
        const nextIndex = this.context.currentStepIndex + 1;

        if (nextIndex >= (this.currentSOP?.steps.length || 0)) {
            // SOP 完成
            this.context.executionState = SOPExecutionState.COMPLETE;
            this.notifyStateChange();
            this.onComplete?.();

            return {
                result: AdjudicationResult.ALLOWED,
                targetPart: '',
                reason: 'SOP 执行完成',
                reasonCode: 'SOP_COMPLETE',
                blockingConstraints: [],
                requiredActions: [],
                timestamp: Date.now(),
            };
        }

        // 推进到下一步
        this.context.currentStepIndex = nextIndex;
        this.context.executionState = SOPExecutionState.IDLE;
        this.notifyStateChange();

        const nextStep = this.getCurrentStep();
        this.onStepChange?.(nextStep, nextIndex);

        return {
            result: AdjudicationResult.ALLOWED,
            targetPart: step.targetParts[0] || '',
            reason: '步骤完成',
            reasonCode: 'STEP_COMPLETE',
            blockingConstraints: [],
            requiredActions: [],
            timestamp: Date.now(),
        };
    }

    /**
     * 跳转到指定步骤（仅限已完成的步骤）
     */
    goToStep(stepIndex: number): boolean {
        if (!this.context || !this.currentSOP) return false;

        if (stepIndex < 0 || stepIndex >= this.currentSOP.steps.length) {
            return false;
        }

        // 只能跳转到已完成的步骤或当前步骤
        const stepId = this.currentSOP.steps[stepIndex].stepId;
        if (stepIndex > this.context.currentStepIndex &&
            !this.context.completedSteps.includes(stepId)) {
            return false;
        }

        this.context.currentStepIndex = stepIndex;
        this.context.executionState = SOPExecutionState.IDLE;
        this.notifyStateChange();

        const step = this.getCurrentStep();
        this.onStepChange?.(step, stepIndex);

        return true;
    }

    /**
     * 重置执行器
     */
    reset(): void {
        if (this.context && this.currentSOP) {
            this.context = {
                sopId: this.currentSOP.sopId,
                currentStepIndex: 0,
                executionState: SOPExecutionState.IDLE,
                lastReport: null,
                startTime: Date.now(),
                stepStartTime: Date.now(),
                completedSteps: [],
                failedSteps: [],
            };
            this.notifyStateChange();
            this.onStepChange?.(this.getCurrentStep(), 0);
        }

        // 重置系统状态
        useAdjudicationStore.getState().resetState();
    }

    /**
     * 获取执行报告
     */
    getExecutionReport(): {
        sopId: string;
        totalSteps: number;
        completedSteps: number;
        currentStep: number;
        elapsedTime: number;
        status: SOPExecutionState;
    } | null {
        if (!this.context || !this.currentSOP) return null;

        return {
            sopId: this.context.sopId,
            totalSteps: this.currentSOP.steps.length,
            completedSteps: this.context.completedSteps.length,
            currentStep: this.context.currentStepIndex + 1,
            elapsedTime: Date.now() - this.context.startTime,
            status: this.context.executionState,
        };
    }

    private notifyStateChange(): void {
        if (this.context) {
            this.onStateChange?.({ ...this.context });
        }
    }
}

// ============================================================
// 工厂函数
// ============================================================

/**
 * 创建 SOP 执行器实例
 */
export function createSOPExecutor(options?: {
    onStateChange?: (context: SOPExecutionContext) => void;
    onStepChange?: (step: SOPStepAdjudication | null, index: number) => void;
    onBlocked?: (report: AdjudicationReport) => void;
    onComplete?: () => void;
    onFailed?: (reason: string) => void;
}): SOPExecutor {
    return new SOPExecutor(options);
}
