/**
 * @description 裁决引擎 - 核心判定逻辑
 * @module adjudication/core/decisionEngine
 * 
 * 基于规范文档 §2.3 拆卸合法性裁决规则
 * 
 * 核心原则：
 * - 裁决结果优先于动画/UI/用户意图
 * - 完成判定 = 行为语义完成 + 约束解除 + 几何判定
 * - 禁止绕过裁决层
 */

import {
    AdjudicationResult,
    AdjudicationReport,
    ActionType,
    Constraint,
    ConstraintType,
    FastenedByParams,
    CoveredByParams,
    ScrewState,
} from '../types/adjudication';
import {
    getConstraintsByPart,
    getActiveConstraints,
    canReleaseConstraint,
} from '../data/constraintGraph';
import { getPartById, getPartScrews } from '../data/partRegistry';
import { getScrewInstance } from '../data/screwInstances';
import { useAdjudicationStore } from './stateManager';
import {
    isScrewExtracted,
    checkToolMatch,
    getScrewProgress,
    checkPartScrewsExtracted,
} from './geometryJudge';

// ============================================================
// 裁决报告生成辅助函数
// ============================================================

function createReport(
    result: AdjudicationResult,
    targetPart: string,
    reason: string,
    reasonCode: string,
    blockingConstraints: Constraint[] = [],
    requiredActions: string[] = []
): AdjudicationReport {
    return {
        result,
        targetPart,
        reason,
        reasonCode,
        blockingConstraints,
        requiredActions,
        timestamp: Date.now(),
    };
}

// ============================================================
// 约束检查
// ============================================================

/**
 * 获取阻止操作零件的约束
 */
export function getBlockingConstraints(partId: string): Constraint[] {
    const store = useAdjudicationStore.getState();
    const constraints = getConstraintsByPart(partId);

    // 获取已移除的零件和已退出的螺丝
    const removedParts = new Set(
        Object.entries(store.partStates)
            .filter(([_, state]) => state.isRemoved)
            .map(([id]) => id)
    );

    const extractedScrews = new Set(
        Object.entries(store.screwStates)
            .filter(([_, state]) => state.state === ScrewState.EXTRACTED || state.state === ScrewState.REMOVED)
            .map(([id]) => id)
    );

    // 过滤出仍然活跃的阻塞约束
    return constraints.filter(c => {
        if (!store.constraintStates[c.id]) return false;
        return !canReleaseConstraint(c, removedParts, extractedScrews);
    });
}

/**
 * 生成阻塞原因文本
 */
function generateBlockingReason(constraints: Constraint[]): string {
    if (constraints.length === 0) return '';

    const reasons: string[] = [];

    for (const c of constraints) {
        switch (c.type) {
            case ConstraintType.COVERED_BY: {
                const params = c.params as CoveredByParams;
                const coverPart = getPartById(params.coverPartId);
                reasons.push(`请先拆卸 ${coverPart?.displayName || params.coverPartId}`);
                break;
            }
            case ConstraintType.FASTENED_BY: {
                const params = c.params as FastenedByParams;
                const store = useAdjudicationStore.getState();
                const remaining = params.screwIds.filter(id => {
                    const state = store.screwStates[id];
                    return state?.state !== ScrewState.EXTRACTED && state?.state !== ScrewState.REMOVED;
                });
                if (remaining.length > 0) {
                    reasons.push(`还有 ${remaining.length} 颗螺丝未拆除`);
                }
                break;
            }
            case ConstraintType.BLOCKED_BY: {
                const part = getPartById(c.constrainingPart);
                reasons.push(`被 ${part?.displayName || c.constrainingPart} 阻挡`);
                break;
            }
            default:
                reasons.push(`约束 ${c.id} 未解除`);
        }
    }

    return reasons.join('；');
}

/**
 * 生成需要先执行的操作列表
 */
function generateRequiredActions(constraints: Constraint[]): string[] {
    const actions: string[] = [];

    for (const c of constraints) {
        switch (c.type) {
            case ConstraintType.COVERED_BY: {
                const params = c.params as CoveredByParams;
                actions.push(`拆卸 ${params.coverPartId}`);
                break;
            }
            case ConstraintType.FASTENED_BY: {
                const params = c.params as FastenedByParams;
                params.screwIds.forEach(id => {
                    actions.push(`拆卸螺丝 ${id}`);
                });
                break;
            }
            default:
                break;
        }
    }

    return actions;
}

// ============================================================
// 核心裁决函数
// ============================================================

/**
 * 判断是否可以操作零件
 * 
 * @param partId - 零件ID
 * @param action - 操作类型
 * @returns AdjudicationReport
 */
export function canOperatePart(partId: string, _action: ActionType): AdjudicationReport {
    const part = getPartById(partId);

    if (!part) {
        return createReport(
            AdjudicationResult.BLOCKED,
            partId,
            `零件 ${partId} 不存在`,
            'PART_NOT_FOUND'
        );
    }

    // 检查零件是否已被移除
    const store = useAdjudicationStore.getState();
    if (store.partStates[partId]?.isRemoved) {
        return createReport(
            AdjudicationResult.BLOCKED,
            partId,
            `零件 ${part.displayName} 已被移除`,
            'PART_ALREADY_REMOVED'
        );
    }

    // 检查阻塞约束
    const blockingConstraints = getBlockingConstraints(partId);

    if (blockingConstraints.length > 0) {
        return createReport(
            AdjudicationResult.BLOCKED,
            partId,
            generateBlockingReason(blockingConstraints),
            'CONSTRAINT_NOT_RELEASED',
            blockingConstraints,
            generateRequiredActions(blockingConstraints)
        );
    }

    return createReport(
        AdjudicationResult.ALLOWED,
        partId,
        '允许操作',
        'OK'
    );
}

/**
 * 判断是否可以拆卸螺丝
 * 
 * @param screwId - 螺丝ID
 * @param toolId - 工具ID
 * @returns AdjudicationReport
 */
export function canRemoveScrew(screwId: string, toolId: string | null): AdjudicationReport {
    const screw = getScrewInstance(screwId);

    if (!screw) {
        return createReport(
            AdjudicationResult.BLOCKED,
            screwId,
            `螺丝 ${screwId} 不存在`,
            'SCREW_NOT_FOUND'
        );
    }

    // 检查螺丝是否已退出
    if (isScrewExtracted(screwId)) {
        return createReport(
            AdjudicationResult.BLOCKED,
            screwId,
            '螺丝已经完全退出',
            'SCREW_ALREADY_EXTRACTED'
        );
    }

    // 检查工具匹配
    const toolCheck = checkToolMatch(toolId, screwId);
    if (!toolCheck.matched) {
        return createReport(
            AdjudicationResult.TOOL_MISMATCH,
            screwId,
            toolCheck.message,
            'TOOL_MISMATCH',
            [],
            [`选择 ${toolCheck.requiredTool}`]
        );
    }

    // 检查螺丝所属零件是否可访问（覆盖物是否已拆除）
    if (screw.parentId) {
        const parentPart = getPartById(screw.parentId);
        if (parentPart) {
            // 检查父零件的覆盖约束
            const constraints = getConstraintsByPart(screw.parentId);
            const store = useAdjudicationStore.getState();

            for (const c of constraints) {
                if (c.type === ConstraintType.COVERED_BY && store.constraintStates[c.id]) {
                    const params = c.params as CoveredByParams;
                    const coverPart = getPartById(params.coverPartId);
                    if (!store.partStates[params.coverPartId]?.isRemoved) {
                        return createReport(
                            AdjudicationResult.BLOCKED,
                            screwId,
                            `请先拆卸 ${coverPart?.displayName || params.coverPartId}`,
                            'COVERED_BY_CONSTRAINT',
                            [c],
                            [`拆卸 ${params.coverPartId}`]
                        );
                    }
                }
            }
        }
    }

    return createReport(
        AdjudicationResult.ALLOWED,
        screwId,
        '允许拆卸',
        'OK'
    );
}

/**
 * 判断是否可以分离零件
 * 
 * @param partId - 零件ID
 * @returns AdjudicationReport
 */
export function canDetachPart(partId: string): AdjudicationReport {
    const part = getPartById(partId);

    if (!part) {
        return createReport(
            AdjudicationResult.BLOCKED,
            partId,
            `零件 ${partId} 不存在`,
            'PART_NOT_FOUND'
        );
    }

    // 检查是否已分离
    const store = useAdjudicationStore.getState();
    if (store.partStates[partId]?.isDetached) {
        return createReport(
            AdjudicationResult.BLOCKED,
            partId,
            `零件 ${part.displayName} 已经分离`,
            'PART_ALREADY_DETACHED'
        );
    }

    // 检查所有阻塞约束
    const blockingConstraints = getBlockingConstraints(partId);

    if (blockingConstraints.length > 0) {
        return createReport(
            AdjudicationResult.BLOCKED,
            partId,
            generateBlockingReason(blockingConstraints),
            'CONSTRAINT_NOT_RELEASED',
            blockingConstraints,
            generateRequiredActions(blockingConstraints)
        );
    }

    // 检查该零件关联的螺丝是否都已退出
    const screwIds = getPartScrews(partId);
    if (screwIds.length > 0) {
        const screwCheck = checkPartScrewsExtracted(partId, screwIds);
        if (!screwCheck.allExtracted) {
            return createReport(
                AdjudicationResult.INCOMPLETE,
                partId,
                `还有 ${screwCheck.remainingScrews.length} 颗螺丝未拆除`,
                'SCREWS_NOT_EXTRACTED',
                [],
                screwCheck.remainingScrews.map(id => `拆卸螺丝 ${id}`)
            );
        }
    }

    return createReport(
        AdjudicationResult.ALLOWED,
        partId,
        '允许分离',
        'OK'
    );
}

/**
 * 裁决操作结果（通用入口）
 * 
 * @param action - 操作类型
 * @param targetId - 目标零件/螺丝ID
 * @param toolId - 工具ID（可选）
 * @returns AdjudicationReport
 */
export function adjudicateAction(
    action: ActionType,
    targetId: string,
    toolId?: string | null
): AdjudicationReport {
    switch (action) {
        case ActionType.ROTATE_SCREW:
        case ActionType.EXTRACT_SCREW:
            return canRemoveScrew(targetId, toolId ?? null);

        case ActionType.DETACH_PART:
        case ActionType.REMOVE_PART:
            return canDetachPart(targetId);

        case ActionType.SELECT_TOOL:
            // 选择工具始终允许
            return createReport(
                AdjudicationResult.ALLOWED,
                targetId,
                '工具选择成功',
                'OK'
            );

        default:
            return canOperatePart(targetId, action);
    }
}

/**
 * 验证螺丝拆卸完成
 * 
 * @param screwId - 螺丝ID
 * @returns AdjudicationReport
 */
export function validateScrewExtraction(screwId: string): AdjudicationReport {
    const progress = getScrewProgress(screwId);

    if (progress.overallProgress >= 1) {
        return createReport(
            AdjudicationResult.ALLOWED,
            screwId,
            '螺丝完全退出',
            'OK'
        );
    }

    return createReport(
        AdjudicationResult.INCOMPLETE,
        screwId,
        `螺丝未完全退出，还需旋转 ${progress.remainingRotations.toFixed(1)} 圈`,
        'SCREW_NOT_EXTRACTED',
        [],
        ['继续旋转螺丝']
    );
}

/**
 * 验证零件分离完成
 * 
 * @param partId - 零件ID
 * @returns AdjudicationReport
 */
export function validatePartDetachment(partId: string): AdjudicationReport {
    const store = useAdjudicationStore.getState();

    if (store.partStates[partId]?.isDetached) {
        return createReport(
            AdjudicationResult.ALLOWED,
            partId,
            '零件分离完成',
            'OK'
        );
    }

    // 先检查是否可以分离
    const canDetach = canDetachPart(partId);
    if (canDetach.result !== AdjudicationResult.ALLOWED) {
        return canDetach;
    }

    return createReport(
        AdjudicationResult.INCOMPLETE,
        partId,
        '零件尚未分离',
        'PART_NOT_DETACHED'
    );
}

// ============================================================
// 状态提交函数（裁决通过后调用）
// ============================================================

/**
 * 提交螺丝状态变更（裁决通过后调用）
 */
export function commitScrewExtraction(screwId: string): void {
    const store = useAdjudicationStore.getState();
    store.setScrewState(screwId, ScrewState.EXTRACTED);

    // 记录操作
    store.addActionRecord({
        action: ActionType.EXTRACT_SCREW,
        targetParts: [screwId],
        toolId: store.currentToolId,
        result: AdjudicationResult.ALLOWED,
    });

    // 检查并更新相关约束状态
    updateConstraintsAfterScrewExtraction(screwId);
}

/**
 * 提交零件分离变更（裁决通过后调用）
 */
export function commitPartDetachment(partId: string): void {
    const store = useAdjudicationStore.getState();
    store.setPartDetached(partId);

    // 记录操作
    store.addActionRecord({
        action: ActionType.DETACH_PART,
        targetParts: [partId],
        toolId: store.currentToolId,
        result: AdjudicationResult.ALLOWED,
    });

    // 检查并更新相关约束状态
    updateConstraintsAfterPartRemoval(partId);
}

/**
 * 提交零件移除变更（裁决通过后调用）
 */
export function commitPartRemoval(partId: string): void {
    const store = useAdjudicationStore.getState();
    store.setPartRemoved(partId);

    // 记录操作
    store.addActionRecord({
        action: ActionType.REMOVE_PART,
        targetParts: [partId],
        toolId: store.currentToolId,
        result: AdjudicationResult.ALLOWED,
    });

    // 检查并更新相关约束状态
    updateConstraintsAfterPartRemoval(partId);
}

/**
 * 螺丝退出后更新约束状态
 */
function updateConstraintsAfterScrewExtraction(screwId: string): void {
    const store = useAdjudicationStore.getState();
    const removedParts = new Set(
        Object.entries(store.partStates)
            .filter(([_, state]) => state.isRemoved)
            .map(([id]) => id)
    );
    const extractedScrews = new Set(
        Object.entries(store.screwStates)
            .filter(([_, state]) => state.state === ScrewState.EXTRACTED || state.state === ScrewState.REMOVED)
            .map(([id]) => id)
    );
    extractedScrews.add(screwId);

    // 检查所有约束是否可以解除
    Object.entries(store.constraintStates).forEach(([constraintId, isActive]) => {
        if (isActive) {
            const constraint = getActiveConstraints('').find(c => c.id === constraintId);
            if (constraint && canReleaseConstraint(constraint, removedParts, extractedScrews)) {
                store.setConstraintActive(constraintId, false);
            }
        }
    });
}

/**
 * 零件移除后更新约束状态
 */
function updateConstraintsAfterPartRemoval(partId: string): void {
    const store = useAdjudicationStore.getState();
    const removedParts = new Set(
        Object.entries(store.partStates)
            .filter(([_, state]) => state.isRemoved)
            .map(([id]) => id)
    );
    removedParts.add(partId);

    const extractedScrews = new Set(
        Object.entries(store.screwStates)
            .filter(([_, state]) => state.state === ScrewState.EXTRACTED || state.state === ScrewState.REMOVED)
            .map(([id]) => id)
    );

    // 检查所有约束是否可以解除
    Object.entries(store.constraintStates).forEach(([constraintId, isActive]) => {
        if (isActive) {
            const constraint = getActiveConstraints('').find(c => c.id === constraintId);
            if (constraint && canReleaseConstraint(constraint, removedParts, extractedScrews)) {
                store.setConstraintActive(constraintId, false);
            }
        }
    });
}
