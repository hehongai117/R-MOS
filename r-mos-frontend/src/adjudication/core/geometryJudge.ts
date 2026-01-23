/**
 * @description 几何判定模块 - 基于几何条件判断操作状态
 * @module adjudication/core/geometryJudge
 * 
 * 基于规范文档 §3 L2: 几何判定层
 */

import {
    ScrewState,
    ScrewGeometryCondition,
    SCREW_GEOMETRY_CONDITIONS,
} from '../types/adjudication';
import { getScrewInstance } from '../data/screwInstances';
import { useAdjudicationStore } from './stateManager';

// ============================================================
// 几何条件查询
// ============================================================

/**
 * 获取螺丝类型的几何条件
 */
export function getScrewGeometryCondition(screwType: string): ScrewGeometryCondition | undefined {
    return SCREW_GEOMETRY_CONDITIONS[screwType];
}

/**
 * 根据螺丝ID获取其几何条件
 */
export function getScrewGeometryConditionById(screwId: string): ScrewGeometryCondition | undefined {
    const screw = getScrewInstance(screwId);
    if (!screw?.screwSpec) return undefined;
    return getScrewGeometryCondition(screw.screwSpec.type);
}

// ============================================================
// 螺丝状态几何判定
// ============================================================

/**
 * 判断螺丝是否完全退出
 * 
 * 判定条件：
 * 1. Z 轴位移 >= minZDisplacement
 * 2. 旋转圈数 >= totalRotations
 * 
 * @param screwId - 螺丝ID
 * @returns boolean - 是否完全退出
 */
export function isScrewExtracted(screwId: string): boolean {
    const store = useAdjudicationStore.getState();
    const screwState = store.screwStates[screwId];

    if (!screwState) return false;
    if (screwState.state === ScrewState.EXTRACTED || screwState.state === ScrewState.REMOVED) {
        return true;
    }

    const condition = getScrewGeometryConditionById(screwId);
    if (!condition) return false;

    return screwState.zDisplacement >= condition.extractedCondition.minZDisplacement;
}

/**
 * 获取螺丝退出进度
 * 
 * @param screwId - 螺丝ID
 * @returns { rotationProgress, displacementProgress, overallProgress } - 进度信息
 */
export function getScrewProgress(screwId: string): {
    rotationProgress: number;
    displacementProgress: number;
    overallProgress: number;
    remainingRotations: number;
    remainingDisplacement: number;
} {
    const store = useAdjudicationStore.getState();
    const screwState = store.screwStates[screwId];
    const condition = getScrewGeometryConditionById(screwId);

    if (!screwState || !condition) {
        return {
            rotationProgress: 0,
            displacementProgress: 0,
            overallProgress: 0,
            remainingRotations: 0,
            remainingDisplacement: 0,
        };
    }

    const rotationProgress = Math.min(
        screwState.currentRotations / condition.rotationCondition.totalRotations,
        1
    );

    const displacementProgress = Math.min(
        screwState.zDisplacement / condition.extractedCondition.minZDisplacement,
        1
    );

    // 综合进度取两者较小值（必须同时满足）
    const overallProgress = Math.min(rotationProgress, displacementProgress);

    const remainingRotations = Math.max(
        condition.rotationCondition.totalRotations - screwState.currentRotations,
        0
    );

    const remainingDisplacement = Math.max(
        condition.extractedCondition.minZDisplacement - screwState.zDisplacement,
        0
    );

    return {
        rotationProgress,
        displacementProgress,
        overallProgress,
        remainingRotations,
        remainingDisplacement,
    };
}

/**
 * 计算螺丝旋转后的位移
 * 
 * @param screwId - 螺丝ID
 * @param rotations - 旋转圈数
 * @returns 位移量 (mm)
 */
export function calculateDisplacementFromRotation(screwId: string, rotations: number): number {
    const screw = getScrewInstance(screwId);
    if (!screw?.screwSpec) return 0;

    return rotations * screw.screwSpec.pitch;
}

/**
 * 验证螺丝旋转是否有效
 * 
 * @param screwId - 螺丝ID
 * @param deltaRotations - 新增旋转圈数
 * @returns { valid, newState, message }
 */
export function validateScrewRotation(screwId: string, deltaRotations: number): {
    valid: boolean;
    newState: ScrewState | null;
    newRotations: number;
    newDisplacement: number;
    message: string;
} {
    const store = useAdjudicationStore.getState();
    const screwState = store.screwStates[screwId];
    const condition = getScrewGeometryConditionById(screwId);
    const screw = getScrewInstance(screwId);

    if (!screwState) {
        return {
            valid: false,
            newState: null,
            newRotations: 0,
            newDisplacement: 0,
            message: `螺丝 ${screwId} 不存在`,
        };
    }

    if (screwState.state === ScrewState.EXTRACTED || screwState.state === ScrewState.REMOVED) {
        return {
            valid: false,
            newState: screwState.state,
            newRotations: screwState.currentRotations,
            newDisplacement: screwState.zDisplacement,
            message: '螺丝已经完全退出',
        };
    }

    if (!condition || !screw?.screwSpec) {
        return {
            valid: false,
            newState: null,
            newRotations: 0,
            newDisplacement: 0,
            message: '无法获取螺丝几何条件',
        };
    }

    const newRotations = screwState.currentRotations + deltaRotations;
    const newDisplacement = newRotations * screw.screwSpec.pitch;

    // 判断新状态
    let newState: ScrewState = ScrewState.LOOSENING;
    if (newDisplacement >= condition.extractedCondition.minZDisplacement) {
        newState = ScrewState.EXTRACTED;
    }

    return {
        valid: true,
        newState,
        newRotations,
        newDisplacement,
        message: newState === ScrewState.EXTRACTED
            ? '螺丝完全退出'
            : `螺丝正在旋出，还需 ${(condition.rotationCondition.totalRotations - newRotations).toFixed(1)} 圈`,
    };
}

// ============================================================
// 零件可分离几何判定
// ============================================================

/**
 * 检查零件的所有螺丝是否都已退出
 * 
 * @param partId - 零件ID
 * @param screwIds - 该零件的螺丝列表
 * @returns { allExtracted, extractedCount, totalCount, remainingScrews }
 */
export function checkPartScrewsExtracted(_partId: string, screwIds: string[]): {
    allExtracted: boolean;
    extractedCount: number;
    totalCount: number;
    remainingScrews: string[];
} {
    const store = useAdjudicationStore.getState();

    const extractedScrews = screwIds.filter(id => {
        const state = store.screwStates[id];
        return state?.state === ScrewState.EXTRACTED || state?.state === ScrewState.REMOVED;
    });

    const remainingScrews = screwIds.filter(id => !extractedScrews.includes(id));

    return {
        allExtracted: extractedScrews.length === screwIds.length,
        extractedCount: extractedScrews.length,
        totalCount: screwIds.length,
        remainingScrews,
    };
}

// ============================================================
// 工具匹配判定
// ============================================================

/**
 * 检查工具是否匹配螺丝
 * 
 * @param toolId - 工具ID
 * @param screwId - 螺丝ID
 * @returns { matched, requiredTool, message }
 */
export function checkToolMatch(toolId: string | null, screwId: string): {
    matched: boolean;
    requiredTool: string | null;
    message: string;
} {
    const screw = getScrewInstance(screwId);

    if (!screw?.screwSpec) {
        return {
            matched: false,
            requiredTool: null,
            message: `无法获取螺丝 ${screwId} 的规格`,
        };
    }

    const requiredTool = screw.screwSpec.requiredTool;

    if (!toolId) {
        return {
            matched: false,
            requiredTool,
            message: '请先选择工具',
        };
    }

    if (toolId !== requiredTool) {
        // 映射工具ID到友好名称
        const toolNames: Record<string, string> = {
            'hex_2.5': '2.5mm 内六角扳手',
            'hex_3': '3mm 内六角扳手',
            'hex_4': '4mm 内六角扳手',
            'hex_5': '5mm 内六角扳手',
        };

        return {
            matched: false,
            requiredTool,
            message: `工具不匹配，需要 ${toolNames[requiredTool] || requiredTool}`,
        };
    }

    return {
        matched: true,
        requiredTool,
        message: '工具匹配',
    };
}
