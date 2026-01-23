/**
 * @description 零件注册表 - 管理所有零件数据
 * @module adjudication/data/partRegistry
 */

import { Part, PartCategory } from '../types/adjudication';

/**
 * Atom01 零件元数据 (从 Atom01Interactive.tsx 迁移并扩展)
 */
export const PART_REGISTRY: Record<string, Part> = {
    // ============================================================
    // 基座
    // ============================================================
    'base_link': {
        id: 'base_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-BASE-001',
        displayName: '髋部底座',
        modelPath: '/models/atom01/base_link.glb',
        parentId: null,
        localPosition: [0, 0, 0],
        localRotation: [0, 0, 0],
    },

    // ============================================================
    // 躯干
    // ============================================================
    'torso_link': {
        id: 'torso_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-TORSO-001',
        displayName: '躯干',
        modelPath: '/models/atom01/torso_link.glb',
        parentId: 'base_link',
        localPosition: [0, 0.15, 0],
        localRotation: [0, 0, 0],
    },

    // ============================================================
    // 左腿 (脚部总成 - 垂直切片优先)
    // ============================================================
    'left_thigh_yaw_link': {
        id: 'left_thigh_yaw_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-LTHIGH-001',
        displayName: '左大腿 Yaw',
        modelPath: '/models/atom01/left_thigh_yaw_link.glb',
        parentId: 'base_link',
        localPosition: [-0.05, -0.1, 0],
        localRotation: [0, 0, 0],
    },
    'left_thigh_roll_link': {
        id: 'left_thigh_roll_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-LTHIGH-002',
        displayName: '左大腿 Roll',
        modelPath: '/models/atom01/left_thigh_roll_link.glb',
        parentId: 'left_thigh_yaw_link',
        localPosition: [0, -0.05, 0],
        localRotation: [0, 0, 0],
    },
    'left_thigh_pitch_link': {
        id: 'left_thigh_pitch_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-LTHIGH-003',
        displayName: '左大腿 Pitch',
        modelPath: '/models/atom01/left_thigh_pitch_link.glb',
        parentId: 'left_thigh_roll_link',
        localPosition: [0, -0.05, 0],
        localRotation: [0, 0, 0],
    },
    'left_knee_link': {
        id: 'left_knee_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-LKNEE-001',
        displayName: '左膝关节',
        modelPath: '/models/atom01/left_knee_link.glb',
        parentId: 'left_thigh_pitch_link',
        localPosition: [0, -0.2, 0],
        localRotation: [0, 0, 0],
    },
    'left_ankle_pitch_link': {
        id: 'left_ankle_pitch_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-LANKLE-001',
        displayName: '左踝 Pitch',
        modelPath: '/models/atom01/left_ankle_pitch_link.glb',
        parentId: 'left_knee_link',
        localPosition: [0, -0.2, 0],
        localRotation: [0, 0, 0],
    },
    'left_ankle_roll_link': {
        id: 'left_ankle_roll_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-LANKLE-002',
        displayName: '左脚底板',
        modelPath: '/models/atom01/left_ankle_roll_link.glb',
        parentId: 'left_ankle_pitch_link',
        localPosition: [0, -0.05, 0],
        localRotation: [0, 0, 0],
    },

    // ============================================================
    // 右腿
    // ============================================================
    'right_thigh_yaw_link': {
        id: 'right_thigh_yaw_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-RTHIGH-001',
        displayName: '右大腿 Yaw',
        modelPath: '/models/atom01/right_thigh_yaw_link.glb',
        parentId: 'base_link',
        localPosition: [0.05, -0.1, 0],
        localRotation: [0, 0, 0],
    },
    'right_thigh_roll_link': {
        id: 'right_thigh_roll_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-RTHIGH-002',
        displayName: '右大腿 Roll',
        modelPath: '/models/atom01/right_thigh_roll_link.glb',
        parentId: 'right_thigh_yaw_link',
        localPosition: [0, -0.05, 0],
        localRotation: [0, 0, 0],
    },
    'right_thigh_pitch_link': {
        id: 'right_thigh_pitch_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-RTHIGH-003',
        displayName: '右大腿 Pitch',
        modelPath: '/models/atom01/right_thigh_pitch_link.glb',
        parentId: 'right_thigh_roll_link',
        localPosition: [0, -0.05, 0],
        localRotation: [0, 0, 0],
    },
    'right_knee_link': {
        id: 'right_knee_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-RKNEE-001',
        displayName: '右膝关节',
        modelPath: '/models/atom01/right_knee_link.glb',
        parentId: 'right_thigh_pitch_link',
        localPosition: [0, -0.2, 0],
        localRotation: [0, 0, 0],
    },
    'right_ankle_pitch_link': {
        id: 'right_ankle_pitch_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-RANKLE-001',
        displayName: '右踝 Pitch',
        modelPath: '/models/atom01/right_ankle_pitch_link.glb',
        parentId: 'right_knee_link',
        localPosition: [0, -0.2, 0],
        localRotation: [0, 0, 0],
    },
    'right_ankle_roll_link': {
        id: 'right_ankle_roll_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-RANKLE-002',
        displayName: '右脚底板',
        modelPath: '/models/atom01/right_ankle_roll_link.glb',
        parentId: 'right_ankle_pitch_link',
        localPosition: [0, -0.05, 0],
        localRotation: [0, 0, 0],
    },

    // ============================================================
    // 脚部软胶覆盖物 (用于约束测试)
    // ============================================================
    'left_foot_rubber': {
        id: 'left_foot_rubber',
        category: PartCategory.COVER,
        bomCode: 'ATOM-01-LFOOT-RUBBER-001',
        displayName: '左脚软胶',
        modelPath: '/models/parts/frames/left_foot_rubber.glb',
        parentId: 'left_ankle_roll_link',
        localPosition: [0, -0.01, 0],
        localRotation: [0, 0, 0],
    },
    'right_foot_rubber': {
        id: 'right_foot_rubber',
        category: PartCategory.COVER,
        bomCode: 'ATOM-01-RFOOT-RUBBER-001',
        displayName: '右脚软胶',
        modelPath: '/models/parts/frames/right_foot_rubber.glb',
        parentId: 'right_ankle_roll_link',
        localPosition: [0, -0.01, 0],
        localRotation: [0, 0, 0],
    },
};

/**
 * 零件-螺丝映射 (为脚部总成垂直切片定义)
 */
export const PART_SCREWS_REGISTRY: Record<string, string[]> = {
    'left_ankle_roll_link': [
        'screw_left_foot_m4x10_001',
        'screw_left_foot_m4x10_002',
        'screw_left_foot_m4x10_003',
        'screw_left_foot_m4x10_004',
    ],
    'left_ankle_pitch_link': [
        'screw_left_ankle_m4x8_001',
        'screw_left_ankle_m4x8_002',
        'screw_left_ankle_m4x8_003',
        'screw_left_ankle_m4x8_004',
    ],
    'right_ankle_roll_link': [
        'screw_right_foot_m4x10_001',
        'screw_right_foot_m4x10_002',
        'screw_right_foot_m4x10_003',
        'screw_right_foot_m4x10_004',
    ],
    'right_ankle_pitch_link': [
        'screw_right_ankle_m4x8_001',
        'screw_right_ankle_m4x8_002',
        'screw_right_ankle_m4x8_003',
        'screw_right_ankle_m4x8_004',
    ],
};

// ============================================================
// 辅助函数
// ============================================================

/**
 * 根据 ID 获取零件信息
 */
export function getPartById(id: string): Part | undefined {
    return PART_REGISTRY[id];
}

/**
 * 获取零件的螺丝列表
 */
export function getPartScrews(partId: string): string[] {
    return PART_SCREWS_REGISTRY[partId] || [];
}

/**
 * 获取指定类型的所有零件
 */
export function getPartsByCategory(category: PartCategory): Part[] {
    return Object.values(PART_REGISTRY).filter(p => p.category === category);
}

/**
 * 获取所有零件 ID 列表
 */
export function getAllPartIds(): string[] {
    return Object.keys(PART_REGISTRY);
}
