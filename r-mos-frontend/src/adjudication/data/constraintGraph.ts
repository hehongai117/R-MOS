/**
 * @description 约束图数据 - 脚部总成 + 躯干
 * @module adjudication/data/constraintGraph
 * 
 * 基于规范文档 §2.2 装配约束模型
 */

import {
    Constraint,
    ConstraintType,
    ActionType,
    FastenedByParams,
    CoveredByParams,
} from '../types/adjudication';

/**
 * 脚部总成约束图
 * 用于 TC-001~TC-005 垂直切片测试
 * 
 * 约束关系：
 * - 左脚软胶 覆盖 左脚底板
 * - 左脚底板 被 4颗 M4×10 螺丝固定
 * - 左踝关节 被 4颗 M4×8 螺丝固定
 * 
 * 正确拆卸顺序：
 * 1. 拆卸左脚软胶
 * 2. 拆卸 4 颗脚底板螺丝 (M4×10)
 * 3. 分离脚底板
 * 4. 拆卸 4 颗踝关节螺丝 (M4×8)
 * 5. 分离踝关节
 */
export const FOOT_CONSTRAINTS: Constraint[] = [
    // ============================================================
    // 左脚约束
    // ============================================================

    // 约束1: 左脚底板被软胶覆盖
    {
        id: 'constraint_left_foot_covered_by_rubber',
        type: ConstraintType.COVERED_BY,
        constrainedPart: 'left_ankle_roll_link',
        constrainingPart: 'left_foot_rubber',
        params: {
            coverPartId: 'left_foot_rubber',
            coverType: 'full',
        } as CoveredByParams,
        releaseCondition: {
            type: 'cover_removed',
            requiredActions: [
                {
                    action: ActionType.REMOVE_PART,
                    targetParts: ['left_foot_rubber'],
                    allRequired: true,
                },
            ],
        },
        isActive: true,
    },

    // 约束2: 左脚底板被 4 颗 M4×10 螺丝固定
    {
        id: 'constraint_left_foot_fastened',
        type: ConstraintType.FASTENED_BY,
        constrainedPart: 'left_ankle_roll_link',
        constrainingPart: 'screw_left_foot_m4x10_001', // 代表性螺丝
        params: {
            screwIds: [
                'screw_left_foot_m4x10_001',
                'screw_left_foot_m4x10_002',
                'screw_left_foot_m4x10_003',
                'screw_left_foot_m4x10_004',
            ],
            minScrewsToRelease: 4, // 必须全部拆除
        } as FastenedByParams,
        releaseCondition: {
            type: 'all_screws_removed',
            requiredActions: [
                {
                    action: ActionType.EXTRACT_SCREW,
                    targetParts: [
                        'screw_left_foot_m4x10_001',
                        'screw_left_foot_m4x10_002',
                        'screw_left_foot_m4x10_003',
                        'screw_left_foot_m4x10_004',
                    ],
                    allRequired: true,
                },
            ],
        },
        isActive: true,
    },

    // 约束3: 左踝关节被 4 颗 M4×8 螺丝固定
    {
        id: 'constraint_left_ankle_fastened',
        type: ConstraintType.FASTENED_BY,
        constrainedPart: 'left_ankle_pitch_link',
        constrainingPart: 'screw_left_ankle_m4x8_001',
        params: {
            screwIds: [
                'screw_left_ankle_m4x8_001',
                'screw_left_ankle_m4x8_002',
                'screw_left_ankle_m4x8_003',
                'screw_left_ankle_m4x8_004',
            ],
            minScrewsToRelease: 4,
        } as FastenedByParams,
        releaseCondition: {
            type: 'all_screws_removed',
            requiredActions: [
                {
                    action: ActionType.EXTRACT_SCREW,
                    targetParts: [
                        'screw_left_ankle_m4x8_001',
                        'screw_left_ankle_m4x8_002',
                        'screw_left_ankle_m4x8_003',
                        'screw_left_ankle_m4x8_004',
                    ],
                    allRequired: true,
                },
            ],
        },
        isActive: true,
    },

    // ============================================================
    // 右脚约束 (对称)
    // ============================================================

    // 约束4: 右脚底板被软胶覆盖
    {
        id: 'constraint_right_foot_covered_by_rubber',
        type: ConstraintType.COVERED_BY,
        constrainedPart: 'right_ankle_roll_link',
        constrainingPart: 'right_foot_rubber',
        params: {
            coverPartId: 'right_foot_rubber',
            coverType: 'full',
        } as CoveredByParams,
        releaseCondition: {
            type: 'cover_removed',
            requiredActions: [
                {
                    action: ActionType.REMOVE_PART,
                    targetParts: ['right_foot_rubber'],
                    allRequired: true,
                },
            ],
        },
        isActive: true,
    },

    // 约束5: 右脚底板被 4 颗 M4×10 螺丝固定
    {
        id: 'constraint_right_foot_fastened',
        type: ConstraintType.FASTENED_BY,
        constrainedPart: 'right_ankle_roll_link',
        constrainingPart: 'screw_right_foot_m4x10_001',
        params: {
            screwIds: [
                'screw_right_foot_m4x10_001',
                'screw_right_foot_m4x10_002',
                'screw_right_foot_m4x10_003',
                'screw_right_foot_m4x10_004',
            ],
            minScrewsToRelease: 4,
        } as FastenedByParams,
        releaseCondition: {
            type: 'all_screws_removed',
            requiredActions: [
                {
                    action: ActionType.EXTRACT_SCREW,
                    targetParts: [
                        'screw_right_foot_m4x10_001',
                        'screw_right_foot_m4x10_002',
                        'screw_right_foot_m4x10_003',
                        'screw_right_foot_m4x10_004',
                    ],
                    allRequired: true,
                },
            ],
        },
        isActive: true,
    },

    // 约束6: 右踝关节被 4 颗 M4×8 螺丝固定
    {
        id: 'constraint_right_ankle_fastened',
        type: ConstraintType.FASTENED_BY,
        constrainedPart: 'right_ankle_pitch_link',
        constrainingPart: 'screw_right_ankle_m4x8_001',
        params: {
            screwIds: [
                'screw_right_ankle_m4x8_001',
                'screw_right_ankle_m4x8_002',
                'screw_right_ankle_m4x8_003',
                'screw_right_ankle_m4x8_004',
            ],
            minScrewsToRelease: 4,
        } as FastenedByParams,
        releaseCondition: {
            type: 'all_screws_removed',
            requiredActions: [
                {
                    action: ActionType.EXTRACT_SCREW,
                    targetParts: [
                        'screw_right_ankle_m4x8_001',
                        'screw_right_ankle_m4x8_002',
                        'screw_right_ankle_m4x8_003',
                        'screw_right_ankle_m4x8_004',
                    ],
                    allRequired: true,
                },
            ],
        },
        isActive: true,
    },
];

/**
 * 躯干约束图
 * 用于 torso 约束扩展与裁决测试
 *
 * 约束关系：
 * - 胸腔夹板被 8 颗 M3×10 螺丝固定
 * - 胸腔夹板覆盖内部电机/电路板
 */
export const TORSO_CONSTRAINTS: Constraint[] = [
    // 约束1: 胸腔夹板被 8 颗 M3×10 螺丝固定
    {
        id: 'constraint_torso_chest_fastened',
        type: ConstraintType.FASTENED_BY,
        constrainedPart: 'frame_torso_chest',
        constrainingPart: 'screw_torso_m3x10_001',
        params: {
            screwIds: [
                'screw_torso_m3x10_001',
                'screw_torso_m3x10_002',
                'screw_torso_m3x10_003',
                'screw_torso_m3x10_004',
                'screw_torso_m3x10_005',
                'screw_torso_m3x10_006',
                'screw_torso_m3x10_007',
                'screw_torso_m3x10_008',
            ],
            minScrewsToRelease: 8,
        } as FastenedByParams,
        releaseCondition: {
            type: 'all_screws_removed',
            requiredActions: [
                {
                    action: ActionType.EXTRACT_SCREW,
                    targetParts: [
                        'screw_torso_m3x10_001',
                        'screw_torso_m3x10_002',
                        'screw_torso_m3x10_003',
                        'screw_torso_m3x10_004',
                        'screw_torso_m3x10_005',
                        'screw_torso_m3x10_006',
                        'screw_torso_m3x10_007',
                        'screw_torso_m3x10_008',
                    ],
                    allRequired: true,
                },
            ],
        },
        isActive: true,
    },

    // 约束2: 内部电机被胸腔夹板覆盖
    {
        id: 'constraint_torso_motor_covered',
        type: ConstraintType.COVERED_BY,
        constrainedPart: 'torso_motor',
        constrainingPart: 'frame_torso_chest',
        params: {
            coverPartId: 'frame_torso_chest',
            coverType: 'full',
        } as CoveredByParams,
        releaseCondition: {
            type: 'cover_removed',
            requiredActions: [
                {
                    action: ActionType.REMOVE_PART,
                    targetParts: ['frame_torso_chest'],
                    allRequired: true,
                },
            ],
        },
        isActive: true,
    },

    // 约束3: 电路板被胸腔夹板覆盖
    {
        id: 'constraint_torso_pcb_covered',
        type: ConstraintType.COVERED_BY,
        constrainedPart: 'torso_pcb_main',
        constrainingPart: 'frame_torso_chest',
        params: {
            coverPartId: 'frame_torso_chest',
            coverType: 'full',
        } as CoveredByParams,
        releaseCondition: {
            type: 'cover_removed',
            requiredActions: [
                {
                    action: ActionType.REMOVE_PART,
                    targetParts: ['frame_torso_chest'],
                    allRequired: true,
                },
            ],
        },
        isActive: true,
    },
];

export const ALL_CONSTRAINTS: Constraint[] = [
    ...FOOT_CONSTRAINTS,
    ...TORSO_CONSTRAINTS,
];

// ============================================================
// 约束查询辅助函数
// ============================================================

/**
 * 获取零件的所有约束（作为被约束方）
 */
export function getConstraintsByPart(partId: string): Constraint[] {
    return ALL_CONSTRAINTS.filter(c => c.constrainedPart === partId);
}

/**
 * 获取零件的所有活跃约束
 */
export function getActiveConstraints(partId: string): Constraint[] {
    return ALL_CONSTRAINTS.filter(c => c.constrainedPart === partId && c.isActive);
}

/**
 * 根据 ID 获取约束
 */
export function getConstraintById(constraintId: string): Constraint | undefined {
    return ALL_CONSTRAINTS.find(c => c.id === constraintId);
}

/**
 * 获取所有约束
 */
export function getAllConstraints(): Constraint[] {
    return ALL_CONSTRAINTS;
}

/**
 * 检查约束是否可以解除
 * 注意：这是一个简化版本，完整版需要传入系统状态
 */
export function canReleaseConstraint(
    constraint: Constraint,
    removedParts: Set<string>,
    extractedScrews: Set<string>
): boolean {
    switch (constraint.type) {
        case ConstraintType.COVERED_BY: {
            const params = constraint.params as CoveredByParams;
            return removedParts.has(params.coverPartId);
        }
        case ConstraintType.FASTENED_BY: {
            const params = constraint.params as FastenedByParams;
            const removedCount = params.screwIds.filter(id => extractedScrews.has(id)).length;
            return removedCount >= params.minScrewsToRelease;
        }
        default:
            return false;
    }
}
