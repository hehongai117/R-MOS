/**
 * @description 零件注册表 - 管理所有零件数据
 * @module adjudication/data/partRegistry
 */

import { Part, PartCategory } from '../types/adjudication';
import { getRobotModelBase } from '../../config/robots';
import { FOOT_SCREW_INSTANCES, TORSO_SCREW_INSTANCES } from './screwInstances';

const MODEL_BASE_URL = import.meta.env.VITE_MODEL_BASE_URL || '/models';
const ROBOT_BASE = getRobotModelBase('atom01');
const PARTS_BASE = `${MODEL_BASE_URL}/parts`;

export function getPartRegistryBase(robotId: string = 'atom01'): string {
    return getRobotModelBase(robotId);
}

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
        modelPath: `${ROBOT_BASE}/base_link.glb`,
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
        modelPath: `${ROBOT_BASE}/torso_link.glb`,
        parentId: 'base_link',
        localPosition: [0, 0.15, 0],
        localRotation: [0, 0, 0],
    },
    'frame_torso_chest': {
        id: 'frame_torso_chest',
        category: PartCategory.COVER,
        bomCode: 'ATOM-01-TORSO-CHEST-001',
        displayName: '胸腔夹板',
        modelPath: `${PARTS_BASE}/frames/胸腔前后夹板.glb`,
        parentId: 'torso_link',
        localPosition: [0, 0.18, 0.06],
        localRotation: [0, 0, 0],
    },
    'torso_motor': {
        id: 'torso_motor',
        category: PartCategory.MOTOR,
        bomCode: 'ATOM-01-TORSO-MOTOR-001',
        displayName: '躯干内部电机',
        modelPath: `${PARTS_BASE}/misc/LB22SA2M1_M10.glb`,
        parentId: 'torso_link',
        localPosition: [0, 0.16, 0],
        localRotation: [0, 0, 0],
    },
    'torso_pcb_main': {
        id: 'torso_pcb_main',
        category: PartCategory.PCB,
        bomCode: 'ATOM-01-TORSO-PCB-001',
        displayName: '躯干主控板',
        modelPath: `${PARTS_BASE}/misc/OPI_5PLUS_PCBA.glb`,
        parentId: 'torso_link',
        localPosition: [0, 0.17, -0.02],
        localRotation: [0, 0, 0],
    },

    // ============================================================
    // 左臂
    // ============================================================
    'left_arm_pitch_link': {
        id: 'left_arm_pitch_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-LARM-001',
        displayName: '左肩 Pitch',
        modelPath: `${ROBOT_BASE}/left_arm_pitch_link.glb`,
        parentId: 'torso_link',
        localPosition: [0, 0.122, 0.206],
        localRotation: [0, 0, 0],
    },
    'left_arm_roll_link': {
        id: 'left_arm_roll_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-LARM-002',
        displayName: '左肩 Roll',
        modelPath: `${ROBOT_BASE}/left_arm_roll_link.glb`,
        parentId: 'left_arm_pitch_link',
        localPosition: [0.02, 0.056, 0],
        localRotation: [0, 0, 0],
    },
    'left_arm_yaw_link': {
        id: 'left_arm_yaw_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-LARM-003',
        displayName: '左上臂',
        modelPath: `${ROBOT_BASE}/left_arm_yaw_link.glb`,
        parentId: 'left_arm_roll_link',
        localPosition: [-0.02, 0, -0.05],
        localRotation: [0, 0, 0],
    },
    'left_elbow_pitch_link': {
        id: 'left_elbow_pitch_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-LARM-004',
        displayName: '左肘 Pitch',
        modelPath: `${ROBOT_BASE}/left_elbow_pitch_link.glb`,
        parentId: 'left_arm_yaw_link',
        localPosition: [0, 0.02, -0.189],
        localRotation: [0, 0, 0],
    },
    'left_elbow_yaw_link': {
        id: 'left_elbow_yaw_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-LARM-005',
        displayName: '左前臂',
        modelPath: `${ROBOT_BASE}/left_elbow_yaw_link.glb`,
        parentId: 'left_elbow_pitch_link',
        localPosition: [0.05, -0.02, 0],
        localRotation: [0, 0, 0],
    },

    // ============================================================
    // 右臂
    // ============================================================
    'right_arm_pitch_link': {
        id: 'right_arm_pitch_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-RARM-001',
        displayName: '右肩 Pitch',
        modelPath: `${ROBOT_BASE}/right_arm_pitch_link.glb`,
        parentId: 'torso_link',
        localPosition: [0, 0.122, -0.206],
        localRotation: [0, 0, 0],
    },
    'right_arm_roll_link': {
        id: 'right_arm_roll_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-RARM-002',
        displayName: '右肩 Roll',
        modelPath: `${ROBOT_BASE}/right_arm_roll_link.glb`,
        parentId: 'right_arm_pitch_link',
        localPosition: [0.02, 0.056, 0],
        localRotation: [0, 0, 0],
    },
    'right_arm_yaw_link': {
        id: 'right_arm_yaw_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-RARM-003',
        displayName: '右上臂',
        modelPath: `${ROBOT_BASE}/right_arm_yaw_link.glb`,
        parentId: 'right_arm_roll_link',
        localPosition: [-0.02, 0, 0.05],
        localRotation: [0, 0, 0],
    },
    'right_elbow_pitch_link': {
        id: 'right_elbow_pitch_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-RARM-004',
        displayName: '右肘 Pitch',
        modelPath: `${ROBOT_BASE}/right_elbow_pitch_link.glb`,
        parentId: 'right_arm_yaw_link',
        localPosition: [0, 0.02, 0.189],
        localRotation: [0, 0, 0],
    },
    'right_elbow_yaw_link': {
        id: 'right_elbow_yaw_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-RARM-005',
        displayName: '右前臂',
        modelPath: `${ROBOT_BASE}/right_elbow_yaw_link.glb`,
        parentId: 'right_elbow_pitch_link',
        localPosition: [0.05, -0.02, 0],
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
        modelPath: `${ROBOT_BASE}/left_thigh_yaw_link.glb`,
        parentId: 'base_link',
        localPosition: [-0.05, -0.1, 0],
        localRotation: [0, 0, 0],
    },
    'left_thigh_roll_link': {
        id: 'left_thigh_roll_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-LTHIGH-002',
        displayName: '左大腿 Roll',
        modelPath: `${ROBOT_BASE}/left_thigh_roll_link.glb`,
        parentId: 'left_thigh_yaw_link',
        localPosition: [0, -0.05, 0],
        localRotation: [0, 0, 0],
    },
    'left_thigh_pitch_link': {
        id: 'left_thigh_pitch_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-LTHIGH-003',
        displayName: '左大腿 Pitch',
        modelPath: `${ROBOT_BASE}/left_thigh_pitch_link.glb`,
        parentId: 'left_thigh_roll_link',
        localPosition: [0, -0.05, 0],
        localRotation: [0, 0, 0],
    },
    'left_knee_link': {
        id: 'left_knee_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-LKNEE-001',
        displayName: '左膝关节',
        modelPath: `${ROBOT_BASE}/left_knee_link.glb`,
        parentId: 'left_thigh_pitch_link',
        localPosition: [0, -0.2, 0],
        localRotation: [0, 0, 0],
    },
    'left_ankle_pitch_link': {
        id: 'left_ankle_pitch_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-LANKLE-001',
        displayName: '左踝 Pitch',
        modelPath: `${ROBOT_BASE}/left_ankle_pitch_link.glb`,
        parentId: 'left_knee_link',
        localPosition: [0, -0.2, 0],
        localRotation: [0, 0, 0],
    },
    'left_ankle_roll_link': {
        id: 'left_ankle_roll_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-LANKLE-002',
        displayName: '左脚底板',
        modelPath: `${ROBOT_BASE}/left_ankle_roll_link.glb`,
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
        modelPath: `${ROBOT_BASE}/right_thigh_yaw_link.glb`,
        parentId: 'base_link',
        localPosition: [0.05, -0.1, 0],
        localRotation: [0, 0, 0],
    },
    'right_thigh_roll_link': {
        id: 'right_thigh_roll_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-RTHIGH-002',
        displayName: '右大腿 Roll',
        modelPath: `${ROBOT_BASE}/right_thigh_roll_link.glb`,
        parentId: 'right_thigh_yaw_link',
        localPosition: [0, -0.05, 0],
        localRotation: [0, 0, 0],
    },
    'right_thigh_pitch_link': {
        id: 'right_thigh_pitch_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-RTHIGH-003',
        displayName: '右大腿 Pitch',
        modelPath: `${ROBOT_BASE}/right_thigh_pitch_link.glb`,
        parentId: 'right_thigh_roll_link',
        localPosition: [0, -0.05, 0],
        localRotation: [0, 0, 0],
    },
    'right_knee_link': {
        id: 'right_knee_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-RKNEE-001',
        displayName: '右膝关节',
        modelPath: `${ROBOT_BASE}/right_knee_link.glb`,
        parentId: 'right_thigh_pitch_link',
        localPosition: [0, -0.2, 0],
        localRotation: [0, 0, 0],
    },
    'right_ankle_pitch_link': {
        id: 'right_ankle_pitch_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-RANKLE-001',
        displayName: '右踝 Pitch',
        modelPath: `${ROBOT_BASE}/right_ankle_pitch_link.glb`,
        parentId: 'right_knee_link',
        localPosition: [0, -0.2, 0],
        localRotation: [0, 0, 0],
    },
    'right_ankle_roll_link': {
        id: 'right_ankle_roll_link',
        category: PartCategory.FRAME,
        bomCode: 'ATOM-01-RANKLE-002',
        displayName: '右脚底板',
        modelPath: `${ROBOT_BASE}/right_ankle_roll_link.glb`,
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
        modelPath: `${PARTS_BASE}/frames/软胶_脚底_左.glb`,
        parentId: 'left_ankle_roll_link',
        localPosition: [0, -0.01, 0],
        localRotation: [0, 0, 0],
    },
    'right_foot_rubber': {
        id: 'right_foot_rubber',
        category: PartCategory.COVER,
        bomCode: 'ATOM-01-RFOOT-RUBBER-001',
        displayName: '右脚软胶',
        modelPath: `${PARTS_BASE}/frames/橡胶脚底.glb`,
        parentId: 'right_ankle_roll_link',
        localPosition: [0, -0.01, 0],
        localRotation: [0, 0, 0],
    },
};

/**
 * 全量零件注册表（包含螺丝实例）
 * 作为逻辑层唯一数据源
 */
export const PART_SCHEMA_REGISTRY: Record<string, Part> = {
    ...PART_REGISTRY,
    ...FOOT_SCREW_INSTANCES,
    ...TORSO_SCREW_INSTANCES,
};

/**
 * 零件-螺丝映射 (为脚部总成垂直切片定义)
 */
export const PART_SCREWS_REGISTRY: Record<string, string[]> = {
    'frame_torso_chest': [
        'screw_torso_m3x10_001',
        'screw_torso_m3x10_002',
        'screw_torso_m3x10_003',
        'screw_torso_m3x10_004',
        'screw_torso_m3x10_005',
        'screw_torso_m3x10_006',
        'screw_torso_m3x10_007',
        'screw_torso_m3x10_008',
    ],
    'torso_link': [
        'screw_torso_m4x12_001',
        'screw_torso_m4x12_002',
        'screw_torso_m4x12_003',
        'screw_torso_m4x12_004',
        'screw_torso_m4x12_005',
        'screw_torso_m4x12_006',
    ],
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
    return PART_SCHEMA_REGISTRY[id];
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
    return Object.values(PART_SCHEMA_REGISTRY).filter(p => p.category === category);
}

/**
 * 获取所有零件 ID 列表
 */
export function getAllPartIds(): string[] {
    return Object.keys(PART_SCHEMA_REGISTRY);
}
