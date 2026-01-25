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
    BlockedByParams,
    ScrewState,
} from '../types/adjudication';
import {
    getAllConstraints,
    getConstraintById,
    canReleaseConstraint,
} from '../data/constraintGraph';
import { getPartById, getPartScrews } from '../data/partRegistry';
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

const ERR_CONSTRAINT = 'ERR_CONSTRAINT';
const ERR_INCOMPLETE = 'ERR_INCOMPLETE';

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
 * 构建零件子节点索引
 */
function buildChildrenIndex(): Record<string, string[]> {
    const index: Record<string, string[]> = {};
    const allPartIds = Object.keys(useAdjudicationStore.getState().partStates);

    allPartIds.forEach(id => {
        const part = getPartById(id);
        if (part?.parentId) {
            if (!index[part.parentId]) {
                index[part.parentId] = [];
            }
            index[part.parentId].push(id);
        }
    });

    return index;
}

/**
 * 获取父子链影响范围
 */
function collectStructuralClosure(seedIds: string[]): Set<string> {
    const affected = new Set<string>();
    const childrenIndex = buildChildrenIndex();

    const addDescendants = (rootId: string): void => {
        const queue = [rootId];
        while (queue.length > 0) {
            const current = queue.shift();
            if (!current || affected.has(current)) continue;
            affected.add(current);
            const children = childrenIndex[current] || [];
            children.forEach(childId => queue.push(childId));
        }
    };

    const addAncestors = (rootId: string): void => {
        let current: string | null = rootId;
        while (current) {
            const part = getPartById(current);
            const parentId = part?.parentId ?? null;
            if (parentId && !affected.has(parentId)) {
                affected.add(parentId);
            }
            current = parentId;
        }
    };

    seedIds.forEach(seedId => {
        if (!seedId) return;
        addDescendants(seedId);
        addAncestors(seedId);
    });

    return affected;
}

/**
 * 获取约束链影响范围（按约束关系扩展）
 */
function collectConstraintClosure(seed: Set<string>): Set<string> {
    const affected = new Set(seed);
    const constraints = getAllConstraints();
    let changed = true;

    while (changed) {
        changed = false;
        for (const constraint of constraints) {
            const relatedParts = new Set<string>([
                constraint.constrainedPart,
                constraint.constrainingPart,
            ]);

            if (constraint.type === ConstraintType.FASTENED_BY) {
                const params = constraint.params as FastenedByParams;
                params.screwIds.forEach(id => relatedParts.add(id));
            }

            if (constraint.type === ConstraintType.COVERED_BY) {
                const params = constraint.params as CoveredByParams;
                relatedParts.add(params.coverPartId);
            }

            if (constraint.type === ConstraintType.BLOCKED_BY) {
                const params = constraint.params as BlockedByParams;
                relatedParts.add(params.blockingPartId);
            }

            const intersects = Array.from(relatedParts).some(id => affected.has(id));
            if (intersects) {
                relatedParts.forEach(id => {
                    if (!affected.has(id)) {
                        affected.add(id);
                        changed = true;
                    }
                });
            }
        }
    }

    return affected;
}

/**
 * 获取某个动作影响的零件集合（父子链 + 约束链）
 */
function getAffectedParts(action: ActionType, targetId: string): Set<string> {
    if (action === ActionType.SELECT_TOOL) {
        return new Set();
    }
    const structural = collectStructuralClosure([targetId]);
    return collectConstraintClosure(structural);
}

/**
 * 判断动作是否属于某约束的解除动作
 */
function isActionReleasingConstraint(constraint: Constraint, action: ActionType, targetId: string): boolean {
    return constraint.releaseCondition.requiredActions.some(req => (
        req.action === action && req.targetParts.includes(targetId)
    ));
}

/**
 * 获取阻止操作零件的约束
 */
export function getBlockingConstraints(partId: string, action: ActionType = ActionType.DETACH_PART): Constraint[] {
    const store = useAdjudicationStore.getState();
    const constraints = getAllConstraints();
    const affectedParts = getAffectedParts(action, partId);

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
        if (!affectedParts.has(c.constrainedPart)) return false;
        if (isActionReleasingConstraint(c, action, partId)) return false;
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
export function canOperatePart(partId: string, action: ActionType): AdjudicationReport {
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
    const blockingConstraints = getBlockingConstraints(partId, action);

    if (blockingConstraints.length > 0) {
        return createReport(
            AdjudicationResult.BLOCKED,
            partId,
            generateBlockingReason(blockingConstraints),
            ERR_CONSTRAINT,
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
    const screw = getPartById(screwId);

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

    // 约束强制阻断（B.2）
    const blockingConstraints = getBlockingConstraints(screwId, ActionType.EXTRACT_SCREW);
    if (blockingConstraints.length > 0) {
        return createReport(
            AdjudicationResult.BLOCKED,
            screwId,
            generateBlockingReason(blockingConstraints),
            ERR_CONSTRAINT,
            blockingConstraints,
            generateRequiredActions(blockingConstraints)
        );
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
    const blockingConstraints = getBlockingConstraints(partId, ActionType.DETACH_PART);

    if (blockingConstraints.length > 0) {
        return createReport(
            AdjudicationResult.BLOCKED,
            partId,
            generateBlockingReason(blockingConstraints),
            ERR_CONSTRAINT,
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
                ERR_INCOMPLETE,
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
        ERR_INCOMPLETE
    );
}

// ============================================================
// 完成判定（三元公理）
// ============================================================

function isActionSemanticallyComplete(action: ActionType, targetId: string): boolean {
    const store = useAdjudicationStore.getState();

    switch (action) {
        case ActionType.EXTRACT_SCREW:
        case ActionType.ROTATE_SCREW:
            return store.screwStates[targetId]?.state === ScrewState.EXTRACTED ||
                store.screwStates[targetId]?.state === ScrewState.REMOVED;
        case ActionType.DETACH_PART:
            return store.partStates[targetId]?.isDetached ?? false;
        case ActionType.REMOVE_PART:
            return store.partStates[targetId]?.isRemoved ?? false;
        default:
            return true;
    }
}

function isActionGeometryComplete(action: ActionType, targetId: string): boolean {
    switch (action) {
        case ActionType.EXTRACT_SCREW:
        case ActionType.ROTATE_SCREW:
            return isScrewExtracted(targetId);
        default:
            return true;
    }
}

/**
 * 完成判定：语义 && 约束 && 几何
 */
export function validateActionCompletion(
    action: ActionType,
    targetId: string,
    _toolId?: string | null
): AdjudicationReport {
    const semanticOk = isActionSemanticallyComplete(action, targetId);
    const blockingConstraints = getBlockingConstraints(targetId, action);
    const constraintOk = blockingConstraints.length === 0;
    const geometryOk = isActionGeometryComplete(action, targetId);

    const allComplete = semanticOk && constraintOk && geometryOk;

    if (!constraintOk) {
        return createReport(
            AdjudicationResult.BLOCKED,
            targetId,
            generateBlockingReason(blockingConstraints),
            ERR_CONSTRAINT,
            blockingConstraints,
            generateRequiredActions(blockingConstraints)
        );
    }

    if (!allComplete) {
        return createReport(
            AdjudicationResult.INCOMPLETE,
            targetId,
            '操作未完成（语义/约束/几何未满足）',
            ERR_INCOMPLETE
        );
    }

    return createReport(
        AdjudicationResult.ALLOWED,
        targetId,
        '完成判定通过',
        'OK'
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
            const constraint = getConstraintById(constraintId);
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
            const constraint = getConstraintById(constraintId);
            if (constraint && canReleaseConstraint(constraint, removedParts, extractedScrews)) {
                store.setConstraintActive(constraintId, false);
            }
        }
    });
}
