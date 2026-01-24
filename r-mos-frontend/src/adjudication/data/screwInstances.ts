/**
 * @description 螺丝实例数据 - 脚部总成
 * @module adjudication/data/screwInstances
 */

import { Part, PartCategory } from '../types/adjudication';

const MODEL_BASE_URL = import.meta.env.VITE_MODEL_BASE_URL || '/models';
const PARTS_BASE = `${MODEL_BASE_URL}/parts`;

/**
 * 脚部总成螺丝实例定义
 * 用于 TC-001~TC-005 垂直切片测试
 */
export const FOOT_SCREW_INSTANCES: Record<string, Part> = {
    // ============================================================
    // 左脚脚底板螺丝 (M4×10, 4颗)
    // ============================================================
    'screw_left_foot_m4x10_001': {
        id: 'screw_left_foot_m4x10_001',
        category: PartCategory.SCREW,
        bomCode: 'ATOM-01-SCREW-M4X10',
        displayName: '左脚底板螺丝 #1',
        modelPath: `${PARTS_BASE}/screws/M4x10.glb`,
        parentId: 'left_ankle_roll_link',
        localPosition: [0.02, 0, 0.02],
        localRotation: [0, 0, 0],
        screwSpec: {
            type: 'M4×10',
            pitch: 0.7,
            threadLength: 10,
            requiredTool: 'hex_3',
            torque: 1.2,
        },
    },
    'screw_left_foot_m4x10_002': {
        id: 'screw_left_foot_m4x10_002',
        category: PartCategory.SCREW,
        bomCode: 'ATOM-01-SCREW-M4X10',
        displayName: '左脚底板螺丝 #2',
        modelPath: `${PARTS_BASE}/screws/M4x10.glb`,
        parentId: 'left_ankle_roll_link',
        localPosition: [-0.02, 0, 0.02],
        localRotation: [0, 0, 0],
        screwSpec: {
            type: 'M4×10',
            pitch: 0.7,
            threadLength: 10,
            requiredTool: 'hex_3',
            torque: 1.2,
        },
    },
    'screw_left_foot_m4x10_003': {
        id: 'screw_left_foot_m4x10_003',
        category: PartCategory.SCREW,
        bomCode: 'ATOM-01-SCREW-M4X10',
        displayName: '左脚底板螺丝 #3',
        modelPath: `${PARTS_BASE}/screws/M4x10.glb`,
        parentId: 'left_ankle_roll_link',
        localPosition: [0.02, 0, -0.02],
        localRotation: [0, 0, 0],
        screwSpec: {
            type: 'M4×10',
            pitch: 0.7,
            threadLength: 10,
            requiredTool: 'hex_3',
            torque: 1.2,
        },
    },
    'screw_left_foot_m4x10_004': {
        id: 'screw_left_foot_m4x10_004',
        category: PartCategory.SCREW,
        bomCode: 'ATOM-01-SCREW-M4X10',
        displayName: '左脚底板螺丝 #4',
        modelPath: `${PARTS_BASE}/screws/M4x10.glb`,
        parentId: 'left_ankle_roll_link',
        localPosition: [-0.02, 0, -0.02],
        localRotation: [0, 0, 0],
        screwSpec: {
            type: 'M4×10',
            pitch: 0.7,
            threadLength: 10,
            requiredTool: 'hex_3',
            torque: 1.2,
        },
    },

    // ============================================================
    // 左踝关节螺丝 (M4×8, 4颗)
    // ============================================================
    'screw_left_ankle_m4x8_001': {
        id: 'screw_left_ankle_m4x8_001',
        category: PartCategory.SCREW,
        bomCode: 'ATOM-01-SCREW-M4X8',
        displayName: '左踝关节螺丝 #1',
        modelPath: `${PARTS_BASE}/screws/M4x8.glb`,
        parentId: 'left_ankle_pitch_link',
        localPosition: [0.015, 0, 0.015],
        localRotation: [0, 0, 0],
        screwSpec: {
            type: 'M4×8',
            pitch: 0.7,
            threadLength: 8,
            requiredTool: 'hex_3',
            torque: 1.2,
        },
    },
    'screw_left_ankle_m4x8_002': {
        id: 'screw_left_ankle_m4x8_002',
        category: PartCategory.SCREW,
        bomCode: 'ATOM-01-SCREW-M4X8',
        displayName: '左踝关节螺丝 #2',
        modelPath: `${PARTS_BASE}/screws/M4x8.glb`,
        parentId: 'left_ankle_pitch_link',
        localPosition: [-0.015, 0, 0.015],
        localRotation: [0, 0, 0],
        screwSpec: {
            type: 'M4×8',
            pitch: 0.7,
            threadLength: 8,
            requiredTool: 'hex_3',
            torque: 1.2,
        },
    },
    'screw_left_ankle_m4x8_003': {
        id: 'screw_left_ankle_m4x8_003',
        category: PartCategory.SCREW,
        bomCode: 'ATOM-01-SCREW-M4X8',
        displayName: '左踝关节螺丝 #3',
        modelPath: `${PARTS_BASE}/screws/M4x8.glb`,
        parentId: 'left_ankle_pitch_link',
        localPosition: [0.015, 0, -0.015],
        localRotation: [0, 0, 0],
        screwSpec: {
            type: 'M4×8',
            pitch: 0.7,
            threadLength: 8,
            requiredTool: 'hex_3',
            torque: 1.2,
        },
    },
    'screw_left_ankle_m4x8_004': {
        id: 'screw_left_ankle_m4x8_004',
        category: PartCategory.SCREW,
        bomCode: 'ATOM-01-SCREW-M4X8',
        displayName: '左踝关节螺丝 #4',
        modelPath: `${PARTS_BASE}/screws/M4x8.glb`,
        parentId: 'left_ankle_pitch_link',
        localPosition: [-0.015, 0, -0.015],
        localRotation: [0, 0, 0],
        screwSpec: {
            type: 'M4×8',
            pitch: 0.7,
            threadLength: 8,
            requiredTool: 'hex_3',
            torque: 1.2,
        },
    },

    // ============================================================
    // 右脚脚底板螺丝 (M4×10, 4颗)
    // ============================================================
    'screw_right_foot_m4x10_001': {
        id: 'screw_right_foot_m4x10_001',
        category: PartCategory.SCREW,
        bomCode: 'ATOM-01-SCREW-M4X10',
        displayName: '右脚底板螺丝 #1',
        modelPath: `${PARTS_BASE}/screws/M4x10.glb`,
        parentId: 'right_ankle_roll_link',
        localPosition: [0.02, 0, 0.02],
        localRotation: [0, 0, 0],
        screwSpec: {
            type: 'M4×10',
            pitch: 0.7,
            threadLength: 10,
            requiredTool: 'hex_3',
            torque: 1.2,
        },
    },
    'screw_right_foot_m4x10_002': {
        id: 'screw_right_foot_m4x10_002',
        category: PartCategory.SCREW,
        bomCode: 'ATOM-01-SCREW-M4X10',
        displayName: '右脚底板螺丝 #2',
        modelPath: `${PARTS_BASE}/screws/M4x10.glb`,
        parentId: 'right_ankle_roll_link',
        localPosition: [-0.02, 0, 0.02],
        localRotation: [0, 0, 0],
        screwSpec: {
            type: 'M4×10',
            pitch: 0.7,
            threadLength: 10,
            requiredTool: 'hex_3',
            torque: 1.2,
        },
    },
    'screw_right_foot_m4x10_003': {
        id: 'screw_right_foot_m4x10_003',
        category: PartCategory.SCREW,
        bomCode: 'ATOM-01-SCREW-M4X10',
        displayName: '右脚底板螺丝 #3',
        modelPath: `${PARTS_BASE}/screws/M4x10.glb`,
        parentId: 'right_ankle_roll_link',
        localPosition: [0.02, 0, -0.02],
        localRotation: [0, 0, 0],
        screwSpec: {
            type: 'M4×10',
            pitch: 0.7,
            threadLength: 10,
            requiredTool: 'hex_3',
            torque: 1.2,
        },
    },
    'screw_right_foot_m4x10_004': {
        id: 'screw_right_foot_m4x10_004',
        category: PartCategory.SCREW,
        bomCode: 'ATOM-01-SCREW-M4X10',
        displayName: '右脚底板螺丝 #4',
        modelPath: `${PARTS_BASE}/screws/M4x10.glb`,
        parentId: 'right_ankle_roll_link',
        localPosition: [-0.02, 0, -0.02],
        localRotation: [0, 0, 0],
        screwSpec: {
            type: 'M4×10',
            pitch: 0.7,
            threadLength: 10,
            requiredTool: 'hex_3',
            torque: 1.2,
        },
    },

    // ============================================================
    // 右踝关节螺丝 (M4×8, 4颗)
    // ============================================================
    'screw_right_ankle_m4x8_001': {
        id: 'screw_right_ankle_m4x8_001',
        category: PartCategory.SCREW,
        bomCode: 'ATOM-01-SCREW-M4X8',
        displayName: '右踝关节螺丝 #1',
        modelPath: `${PARTS_BASE}/screws/M4x8.glb`,
        parentId: 'right_ankle_pitch_link',
        localPosition: [0.015, 0, 0.015],
        localRotation: [0, 0, 0],
        screwSpec: {
            type: 'M4×8',
            pitch: 0.7,
            threadLength: 8,
            requiredTool: 'hex_3',
            torque: 1.2,
        },
    },
    'screw_right_ankle_m4x8_002': {
        id: 'screw_right_ankle_m4x8_002',
        category: PartCategory.SCREW,
        bomCode: 'ATOM-01-SCREW-M4X8',
        displayName: '右踝关节螺丝 #2',
        modelPath: `${PARTS_BASE}/screws/M4x8.glb`,
        parentId: 'right_ankle_pitch_link',
        localPosition: [-0.015, 0, 0.015],
        localRotation: [0, 0, 0],
        screwSpec: {
            type: 'M4×8',
            pitch: 0.7,
            threadLength: 8,
            requiredTool: 'hex_3',
            torque: 1.2,
        },
    },
    'screw_right_ankle_m4x8_003': {
        id: 'screw_right_ankle_m4x8_003',
        category: PartCategory.SCREW,
        bomCode: 'ATOM-01-SCREW-M4X8',
        displayName: '右踝关节螺丝 #3',
        modelPath: `${PARTS_BASE}/screws/M4x8.glb`,
        parentId: 'right_ankle_pitch_link',
        localPosition: [0.015, 0, -0.015],
        localRotation: [0, 0, 0],
        screwSpec: {
            type: 'M4×8',
            pitch: 0.7,
            threadLength: 8,
            requiredTool: 'hex_3',
            torque: 1.2,
        },
    },
    'screw_right_ankle_m4x8_004': {
        id: 'screw_right_ankle_m4x8_004',
        category: PartCategory.SCREW,
        bomCode: 'ATOM-01-SCREW-M4X8',
        displayName: '右踝关节螺丝 #4',
        modelPath: `${PARTS_BASE}/screws/M4x8.glb`,
        parentId: 'right_ankle_pitch_link',
        localPosition: [-0.015, 0, -0.015],
        localRotation: [0, 0, 0],
        screwSpec: {
            type: 'M4×8',
            pitch: 0.7,
            threadLength: 8,
            requiredTool: 'hex_3',
            torque: 1.2,
        },
    },
};

/**
 * 获取螺丝实例
 */
export function getScrewInstance(screwId: string): Part | undefined {
    return FOOT_SCREW_INSTANCES[screwId];
}

/**
 * 获取所有螺丝实例 ID
 */
export function getAllScrewIds(): string[] {
    return Object.keys(FOOT_SCREW_INSTANCES);
}

/**
 * 获取零件的所有螺丝
 */
export function getScrewsByParent(parentId: string): Part[] {
    return Object.values(FOOT_SCREW_INSTANCES).filter(s => s.parentId === parentId);
}
