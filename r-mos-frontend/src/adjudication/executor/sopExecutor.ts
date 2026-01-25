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
import { adjudicateAction, validateActionCompletion } from '../core/decisionEngine';
import { isScrewExtracted } from '../core/geometryJudge';
import { scoringEngine } from '../core/scoringEngine';

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

        // 致命失败锁定：禁止任何后续操作
        if (useAdjudicationStore.getState().systemState === SystemState.FAILED_FATAL) {
            return {
                result: AdjudicationResult.BLOCKED,
                targetPart: step.targetParts[0] || '',
                reason: '系统已进入致命失败状态，需重置',
                reasonCode: 'FAILED_FATAL',
                blockingConstraints: [],
                requiredActions: ['重置系统状态'],
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
            const currentTool = useAdjudicationStore.getState().currentToolId;
            for (const targetId of step.targetParts) {
                const targetReport = adjudicateAction(
                    step.action,
                    targetId,
                    currentTool
                );

                if (targetReport.result !== AdjudicationResult.ALLOWED) {
                    return targetReport;
                }
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

        const step = this.getCurrentStep();
        if (useAdjudicationStore.getState().systemState === SystemState.FAILED_FATAL) {
            return {
                result: AdjudicationResult.BLOCKED,
                targetPart: '',
                reason: '系统已进入致命失败状态，需重置',
                reasonCode: 'FAILED_FATAL',
                blockingConstraints: [],
                requiredActions: ['重置系统状态'],
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
            if (step?.fatalOnFailure) {
                const failureHandling = this.handleFailure(step, canExecute);
                if (failureHandling.hint) {
                    canExecute.hint = failureHandling.hint;
                }
                canExecute.allowRetry = false;
                canExecute.shouldSummarize = true;
                useAdjudicationStore.getState().setSystemState(SystemState.FAILED_FATAL);
                this.context.executionState = SOPExecutionState.FAILED;
                this.context.lastReport = canExecute;
                this.notifyStateChange();
                this.onFailed?.(canExecute.reason);
                this.onBlocked?.(canExecute);
                return canExecute;
            }
            const failureHandling = step ? this.handleFailure(step, canExecute) : { allowRetry: false };
            if (failureHandling.hint) {
                canExecute.hint = failureHandling.hint;
            }
            canExecute.allowRetry = failureHandling.allowRetry;
            if (failureHandling.shouldSummarize) {
                canExecute.shouldSummarize = true;
            }
            if (failureHandling.allowRetry) {
                this.context.executionState = SOPExecutionState.FAILED;
                this.context.lastReport = canExecute;
                this.notifyStateChange();
                return canExecute;
            }
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

        if (useAdjudicationStore.getState().systemState === SystemState.FAILED_FATAL) {
            return {
                result: AdjudicationResult.BLOCKED,
                targetPart: step.targetParts[0] || '',
                reason: '系统已进入致命失败状态，需重置',
                reasonCode: 'FAILED_FATAL',
                blockingConstraints: [],
                requiredActions: ['重置系统状态'],
                timestamp: Date.now(),
            };
        }

        // 更新状态为验证中
        this.context.executionState = SOPExecutionState.VALIDATION;
        this.notifyStateChange();

        // 三元完成判定（语义 && 约束 && 几何）
        const currentTool = useAdjudicationStore.getState().currentToolId;
        for (const targetId of step.targetParts) {
            const completionReport = validateActionCompletion(step.action, targetId, currentTool);
            if (completionReport.result !== AdjudicationResult.ALLOWED) {
                this.context.lastReport = completionReport;

                if (completionReport.result === AdjudicationResult.BLOCKED) {
                    this.context.executionState = SOPExecutionState.BLOCKED;
                    this.notifyStateChange();
                    this.onBlocked?.(completionReport);
                    return completionReport;
                }

                // INCOMPLETE 走既有失败分支
                if (step.onFailure.action === 'block') {
                    const failureHandling = this.handleFailure(step, completionReport);
                    if (failureHandling.hint) {
                        completionReport.hint = failureHandling.hint;
                    }
                    completionReport.allowRetry = failureHandling.allowRetry;
                    if (failureHandling.shouldSummarize) {
                        completionReport.shouldSummarize = true;
                    }
                    if (failureHandling.allowRetry) {
                        this.context.executionState = SOPExecutionState.FAILED;
                        this.notifyStateChange();
                        return completionReport;
                    }
                    this.context.executionState = SOPExecutionState.BLOCKED;
                    this.notifyStateChange();
                    this.onBlocked?.(completionReport);
                }

                return completionReport;
            }
        }

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
                const failureHandling = this.handleFailure(step, report);
                if (failureHandling.hint) {
                    report.hint = failureHandling.hint;
                }
                report.allowRetry = failureHandling.allowRetry;
                if (failureHandling.shouldSummarize) {
                    report.shouldSummarize = true;
                }
                if (failureHandling.allowRetry) {
                    this.context.executionState = SOPExecutionState.FAILED;
                    this.notifyStateChange();
                    return report;
                }
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

        const currentStep = this.getCurrentStep();
        const currentStepCompleted = currentStep
            ? this.context.completedSteps.includes(currentStep.stepId)
            : false;
        const isRollingBack = stepIndex < this.context.currentStepIndex;
        if (
            isRollingBack &&
            currentStep?.isIrreversible &&
            (this.context.executionState === SOPExecutionState.EXECUTING || currentStepCompleted)
        ) {
            throw new Error('不可逆步骤不允许回滚');
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

    /**
     * 教学模式重试当前步骤
     */
    retryStep(): boolean {
        if (!this.context) return false;
        if (this.context.executionState !== SOPExecutionState.FAILED) return false;
        this.context.executionState = SOPExecutionState.IDLE;
        this.context.lastReport = null;
        this.notifyStateChange();
        return true;
    }

    private handleFailure(
        step: SOPStepAdjudication,
        report: AdjudicationReport
    ): { allowRetry: boolean; hint?: string; shouldSummarize?: boolean } {
        const { operationMode } = useAdjudicationStore.getState();

        if (operationMode === 'teaching') {
            // 教学模式：允许重试（UI 可提示引导）
            const hint = step.failureReasons
                .find(reason => reason.teachingResponse?.showHint && reason.teachingResponse.hintContent)
                ?.teachingResponse.hintContent;
            return { allowRetry: true, hint };
        }

        if (operationMode === 'exam') {
            const failure = step.failureReasons[0];
            const examResponse = failure?.examResponse;
            if (examResponse) {
                if (examResponse.deductPoints > 0) {
                    scoringEngine.deduct(step.stepId, failure.code, examResponse.deductPoints);
                }
                if (!examResponse.allowContinue) {
                    useAdjudicationStore.getState().setSystemState(SystemState.FAILED_FATAL);
                    scoringEngine.finalize(failure.code);
                    report.shouldSummarize = true;
                    return { allowRetry: false, shouldSummarize: true };
                }
            }
            return { allowRetry: false };
        }

        // 维保模式：沿用严格阻断
        return { allowRetry: false };
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
