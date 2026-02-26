/**
 * sopScripts.ts - SOP 脚本数据定义（裁决级）
 *
 * 说明：
 * - 该文件已升级为裁决级 SOP 数据结构
 * - 旧版脚本与类型已标记为 Legacy，仅供兼容旧组件
 */

import {
    ActionType,
    SOPScriptAdjudication,
    SOPFailureReason,
    SOPPrecondition,
    SOPValidation,
    PreconditionType,
    ValidationType,
    ErrorCategory,
    SystemState,
} from '@/adjudication';
import { DOCUMENT_SOP_SCRIPTS } from './documentSOPScripts';

// ============================================================
// Legacy（旧版）数据结构：仅供兼容旧组件
// ============================================================

/** @deprecated Legacy SOP 步骤类型 */
export type LegacySOPStepType = 'highlight' | 'explode' | 'tool_check' | 'action' | 'warning' | 'complete';

/** @deprecated Legacy SOP 步骤 */
export interface LegacySOPStep {
    id: number;
    type: LegacySOPStepType;
    title: string;
    description: string;
    partName?: string;
    screwId?: string;
    toolId?: string;
    explodeAmount?: number;
    duration?: number;
    warningLevel?: 'info' | 'warning' | 'danger';
}

/** @deprecated Legacy SOP 脚本 */
export interface LegacySOPScript {
    id: string;
    name: string;
    description: string;
    category: 'maintenance' | 'repair' | 'inspection' | 'assembly';
    estimatedTime: number;
    difficulty: 'easy' | 'medium' | 'hard';
    steps: LegacySOPStep[];
}

/** @deprecated Legacy SOP 脚本：躯干电机更换 */
export const LEGACY_SOP_TORSO_MOTOR_REPLACEMENT: LegacySOPScript = {
    id: 'sop-torso-motor-001',
    name: '躯干电机更换',
    description: '更换机器人躯干部位的 DM 10010L 电机',
    category: 'repair',
    estimatedTime: 30,
    difficulty: 'medium',
    steps: [
        {
            id: 1,
            type: 'warning',
            title: '安全准备',
            description: '确保机器人已断电，并将其固定在维修台上。',
            warningLevel: 'danger',
            duration: 60,
        },
        {
            id: 2,
            type: 'explode',
            title: '展开视图',
            description: '将爆炸图展开至 60%，便于观察躯干结构。',
            explodeAmount: 0.6,
            duration: 5,
        },
        {
            id: 3,
            type: 'highlight',
            title: '定位躯干',
            description: '找到机器人躯干部件（torso_link）。',
            partName: 'torso_link',
            duration: 10,
        },
        {
            id: 4,
            type: 'tool_check',
            title: '准备工具',
            description: '选择 3mm 内六角扳手，用于拆卸 M4×12 螺丝。',
            toolId: 'hex_3',
            screwId: 'M4x12',
            duration: 15,
        },
        {
            id: 5,
            type: 'action',
            title: '拆卸螺丝',
            description: '逆时针旋转，拧下 6 颗 M4×12 躯干连接螺丝。',
            partName: 'torso_link',
            screwId: 'M4x12',
            toolId: 'hex_3',
            duration: 120,
        },
        {
            id: 6,
            type: 'tool_check',
            title: '更换工具',
            description: '选择 2.5mm 内六角扳手，用于拆卸 M3×10 螺丝。',
            toolId: 'hex_2.5',
            screwId: 'M3x10',
            duration: 10,
        },
        {
            id: 7,
            type: 'action',
            title: '拆卸胸腔夹板',
            description: '拧下 8 颗 M3×10 胸腔夹板螺丝。',
            partName: 'torso_link',
            screwId: 'M3x10',
            toolId: 'hex_2.5',
            duration: 180,
        },
        {
            id: 8,
            type: 'warning',
            title: '断开电机连接线',
            description: '小心断开电机的 CAN 总线和电源线。',
            warningLevel: 'warning',
            duration: 30,
        },
        {
            id: 9,
            type: 'action',
            title: '取出旧电机',
            description: '轻轻取出损坏的 DM 10010L 电机。',
            partName: 'torso_link',
            duration: 60,
        },
        {
            id: 10,
            type: 'action',
            title: '安装新电机',
            description: '将新电机放入正确位置，对齐螺丝孔。',
            partName: 'torso_link',
            duration: 60,
        },
        {
            id: 11,
            type: 'action',
            title: '连接电机线缆',
            description: '重新连接 CAN 总线和电源线。',
            partName: 'torso_link',
            duration: 30,
        },
        {
            id: 12,
            type: 'action',
            title: '安装胸腔夹板',
            description: '使用 M3×10 螺丝固定胸腔夹板（扭矩 0.5 Nm）。',
            partName: 'torso_link',
            screwId: 'M3x10',
            toolId: 'hex_2.5',
            duration: 180,
        },
        {
            id: 13,
            type: 'action',
            title: '安装躯干螺丝',
            description: '使用 M4×12 螺丝固定躯干（扭矩 1.2 Nm）。',
            partName: 'torso_link',
            screwId: 'M4x12',
            toolId: 'hex_3',
            duration: 120,
        },
        {
            id: 14,
            type: 'explode',
            title: '收起视图',
            description: '将爆炸图收起，恢复正常视图。',
            explodeAmount: 0,
            duration: 5,
        },
        {
            id: 15,
            type: 'complete',
            title: '完成',
            description: '电机更换完成！请进行功能测试。',
            duration: 0,
        },
    ],
};

/** @deprecated Legacy SOP 脚本：左臂关节检查 */
export const LEGACY_SOP_LEFT_ARM_INSPECTION: LegacySOPScript = {
    id: 'sop-left-arm-inspect-001',
    name: '左臂关节检查',
    description: '检查左臂各关节的连接状态和螺丝松动情况',
    category: 'inspection',
    estimatedTime: 15,
    difficulty: 'easy',
    steps: [
        {
            id: 1,
            type: 'highlight',
            title: '定位左肩',
            description: '检查左肩 Pitch 关节。',
            partName: 'left_arm_pitch_link',
            duration: 30,
        },
        {
            id: 2,
            type: 'highlight',
            title: '检查左肩 Roll',
            description: '检查左肩 Roll 关节螺丝。',
            partName: 'left_arm_roll_link',
            duration: 30,
        },
        {
            id: 3,
            type: 'highlight',
            title: '检查左上臂',
            description: '检查左上臂关节连接。',
            partName: 'left_arm_yaw_link',
            duration: 30,
        },
        {
            id: 4,
            type: 'highlight',
            title: '检查左肘',
            description: '检查左肘 Pitch 关节。',
            partName: 'left_elbow_pitch_link',
            duration: 30,
        },
        {
            id: 5,
            type: 'highlight',
            title: '检查左前臂',
            description: '检查左前臂连接状态。',
            partName: 'left_elbow_yaw_link',
            duration: 30,
        },
        {
            id: 6,
            type: 'complete',
            title: '检查完成',
            description: '左臂所有关节检查完毕。',
            duration: 0,
        },
    ],
};

/** @deprecated Legacy SOP 脚本集合 */
export const LEGACY_ALL_SOP_SCRIPTS: LegacySOPScript[] = [
    LEGACY_SOP_TORSO_MOTOR_REPLACEMENT,
    LEGACY_SOP_LEFT_ARM_INSPECTION,
];

/** @deprecated Legacy SOP 查询 */
export const getLegacySOPById = (id: string): LegacySOPScript | undefined => {
    return LEGACY_ALL_SOP_SCRIPTS.find(s => s.id === id);
};

// ============================================================
// 裁决级 SOP 数据结构
// ============================================================

const DEFAULT_FAILURE_REASONS: SOPFailureReason[] = [
    {
        code: 'ERR_CONSTRAINT',
        category: ErrorCategory.CONSTRAINT_VIOLATION,
        description: '存在 ACTIVE 结构约束，禁止操作',
        severity: 'critical',
        teachingResponse: {
            showHint: true,
            hintContent: '请先解除相关约束后再继续',
            allowRetry: true,
        },
        examResponse: {
            deductPoints: 5,
            allowContinue: false,
            recordToReport: true,
        },
    },
    {
        code: 'ERR_INCOMPLETE',
        category: ErrorCategory.INCOMPLETE_ACTION,
        description: '操作未完成（语义/约束/几何未满足）',
        severity: 'major',
        teachingResponse: {
            showHint: true,
            hintContent: '请完成当前步骤的所有动作',
            allowRetry: true,
        },
        examResponse: {
            deductPoints: 3,
            allowContinue: false,
            recordToReport: true,
        },
    },
];

const BLOCK_ON_FAILURE = { action: 'block' as const, message: '裁决未通过，操作被阻断' };

const makeToolPrecondition = (toolId: string, message: string): SOPPrecondition => ({
    type: PreconditionType.TOOL_EQUIPPED,
    params: { toolId },
    errorMessage: message,
});

const makeAllScrewsValidation = (screwIds: string[]): SOPValidation => ({
    type: ValidationType.ALL_SCREWS_EXTRACTED,
    params: { screwIds },
    isRequired: true,
});

/** 裁决级 SOP：躯干电机更换 */
export const SOP_TORSO_MOTOR_REPLACEMENT: SOPScriptAdjudication = {
    sopId: 'sop-torso-motor-001',
    title: '躯干电机更换',
    version: '1.0.0',
    targetModule: 'torso',
    estimatedTime: 30 * 60,
    difficulty: 'intermediate',
    steps: [
        {
            stepId: 'step_001',
            stepIndex: 1,
            title: '安全准备',
            description: '确保机器人已断电，并将其固定在维修台上。',
            action: ActionType.FOCUS_CAMERA,
            targetParts: [],
            requiredTool: null,
            preconditions: [],
            validations: [],
            failureReasons: DEFAULT_FAILURE_REASONS,
            onSuccess: { nextStepId: 'step_002', stateTransition: null },
            onFailure: BLOCK_ON_FAILURE,
        },
        {
            stepId: 'step_002',
            stepIndex: 2,
            title: '展开视图',
            description: '将爆炸图展开至 60%，便于观察躯干结构。',
            action: ActionType.FOCUS_CAMERA,
            targetParts: [],
            requiredTool: null,
            preconditions: [],
            validations: [],
            failureReasons: DEFAULT_FAILURE_REASONS,
            onSuccess: { nextStepId: 'step_003', stateTransition: null },
            onFailure: BLOCK_ON_FAILURE,
        },
        {
            stepId: 'step_003',
            stepIndex: 3,
            title: '定位躯干',
            description: '找到机器人躯干部件（torso_link）。',
            action: ActionType.FOCUS_CAMERA,
            targetParts: ['torso_link'],
            requiredTool: null,
            preconditions: [],
            validations: [],
            failureReasons: DEFAULT_FAILURE_REASONS,
            onSuccess: { nextStepId: 'step_004', stateTransition: null },
            onFailure: BLOCK_ON_FAILURE,
        },
        {
            stepId: 'step_004',
            stepIndex: 4,
            title: '准备工具',
            description: '选择 3mm 内六角扳手，用于拆卸 M4×12 螺丝。',
            action: ActionType.SELECT_TOOL,
            targetParts: [],
            requiredTool: 'hex_3',
            preconditions: [],
            validations: [
                { type: ValidationType.TOOL_MATCHED, params: { toolId: 'hex_3' }, isRequired: true },
            ],
            failureReasons: DEFAULT_FAILURE_REASONS,
            onSuccess: { nextStepId: 'step_005', stateTransition: null },
            onFailure: BLOCK_ON_FAILURE,
        },
        {
            stepId: 'step_005',
            stepIndex: 5,
            title: '拆卸螺丝',
            description: '逆时针旋转，拧下 6 颗 M4×12 躯干连接螺丝。',
            action: ActionType.ROTATE_SCREW,
            targetParts: [
                'screw_torso_m4x12_001',
                'screw_torso_m4x12_002',
                'screw_torso_m4x12_003',
                'screw_torso_m4x12_004',
                'screw_torso_m4x12_005',
                'screw_torso_m4x12_006',
            ],
            requiredTool: 'hex_3',
            preconditions: [
                makeToolPrecondition('hex_3', '请先选择 3mm 内六角扳手'),
            ],
            validations: [
                makeAllScrewsValidation([
                    'screw_torso_m4x12_001',
                    'screw_torso_m4x12_002',
                    'screw_torso_m4x12_003',
                    'screw_torso_m4x12_004',
                    'screw_torso_m4x12_005',
                    'screw_torso_m4x12_006',
                ]),
            ],
            failureReasons: DEFAULT_FAILURE_REASONS,
            onSuccess: { nextStepId: 'step_006', stateTransition: null },
            onFailure: BLOCK_ON_FAILURE,
        },
        {
            stepId: 'step_006',
            stepIndex: 6,
            title: '更换工具',
            description: '选择 2.5mm 内六角扳手，用于拆卸 M3×10 螺丝。',
            action: ActionType.SELECT_TOOL,
            targetParts: [],
            requiredTool: 'hex_2.5',
            preconditions: [],
            validations: [
                { type: ValidationType.TOOL_MATCHED, params: { toolId: 'hex_2.5' }, isRequired: true },
            ],
            failureReasons: DEFAULT_FAILURE_REASONS,
            onSuccess: { nextStepId: 'step_007', stateTransition: null },
            onFailure: BLOCK_ON_FAILURE,
        },
        {
            stepId: 'step_007',
            stepIndex: 7,
            title: '拆卸胸腔夹板',
            description: '拧下 8 颗 M3×10 胸腔夹板螺丝。',
            action: ActionType.ROTATE_SCREW,
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
            requiredTool: 'hex_2.5',
            preconditions: [
                makeToolPrecondition('hex_2.5', '请先选择 2.5mm 内六角扳手'),
            ],
            validations: [
                makeAllScrewsValidation([
                    'screw_torso_m3x10_001',
                    'screw_torso_m3x10_002',
                    'screw_torso_m3x10_003',
                    'screw_torso_m3x10_004',
                    'screw_torso_m3x10_005',
                    'screw_torso_m3x10_006',
                    'screw_torso_m3x10_007',
                    'screw_torso_m3x10_008',
                ]),
            ],
            failureReasons: DEFAULT_FAILURE_REASONS,
            onSuccess: { nextStepId: 'step_008', stateTransition: null },
            onFailure: BLOCK_ON_FAILURE,
        },
        {
            stepId: 'step_008',
            stepIndex: 8,
            title: '断开电机连接线',
            description: '小心断开电机的 CAN 总线和电源线。',
            action: ActionType.UNPLUG_CONNECTOR,
            targetParts: ['torso_link'],
            requiredTool: null,
            preconditions: [],
            validations: [],
            failureReasons: DEFAULT_FAILURE_REASONS,
            onSuccess: { nextStepId: 'step_009', stateTransition: null },
            onFailure: BLOCK_ON_FAILURE,
            isIrreversible: true,
            fatalOnFailure: true,
        },
        {
            stepId: 'step_009',
            stepIndex: 9,
            title: '取出旧电机',
            description: '轻轻取出损坏的 DM 10010L 电机。',
            action: ActionType.REMOVE_PART,
            targetParts: ['torso_link'],
            requiredTool: null,
            preconditions: [],
            validations: [],
            failureReasons: DEFAULT_FAILURE_REASONS,
            onSuccess: { nextStepId: 'step_010', stateTransition: null },
            onFailure: BLOCK_ON_FAILURE,
        },
        {
            stepId: 'step_010',
            stepIndex: 10,
            title: '安装新电机',
            description: '将新电机放入正确位置，对齐螺丝孔。',
            action: ActionType.REMOVE_PART,
            targetParts: ['torso_link'],
            requiredTool: null,
            preconditions: [],
            validations: [],
            failureReasons: DEFAULT_FAILURE_REASONS,
            onSuccess: { nextStepId: 'step_011', stateTransition: null },
            onFailure: BLOCK_ON_FAILURE,
        },
        {
            stepId: 'step_011',
            stepIndex: 11,
            title: '连接电机线缆',
            description: '重新连接 CAN 总线和电源线。',
            action: ActionType.UNPLUG_CONNECTOR,
            targetParts: ['torso_link'],
            requiredTool: null,
            preconditions: [],
            validations: [],
            failureReasons: DEFAULT_FAILURE_REASONS,
            onSuccess: { nextStepId: 'step_012', stateTransition: null },
            onFailure: BLOCK_ON_FAILURE,
        },
        {
            stepId: 'step_012',
            stepIndex: 12,
            title: '安装胸腔夹板',
            description: '使用 M3×10 螺丝固定胸腔夹板（扭矩 0.5 Nm）。',
            action: ActionType.ROTATE_SCREW,
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
            requiredTool: 'hex_2.5',
            preconditions: [
                makeToolPrecondition('hex_2.5', '请先选择 2.5mm 内六角扳手'),
            ],
            validations: [
                makeAllScrewsValidation([
                    'screw_torso_m3x10_001',
                    'screw_torso_m3x10_002',
                    'screw_torso_m3x10_003',
                    'screw_torso_m3x10_004',
                    'screw_torso_m3x10_005',
                    'screw_torso_m3x10_006',
                    'screw_torso_m3x10_007',
                    'screw_torso_m3x10_008',
                ]),
            ],
            failureReasons: DEFAULT_FAILURE_REASONS,
            onSuccess: { nextStepId: 'step_013', stateTransition: null },
            onFailure: BLOCK_ON_FAILURE,
        },
        {
            stepId: 'step_013',
            stepIndex: 13,
            title: '安装躯干螺丝',
            description: '使用 M4×12 螺丝固定躯干（扭矩 1.2 Nm）。',
            action: ActionType.ROTATE_SCREW,
            targetParts: [
                'screw_torso_m4x12_001',
                'screw_torso_m4x12_002',
                'screw_torso_m4x12_003',
                'screw_torso_m4x12_004',
                'screw_torso_m4x12_005',
                'screw_torso_m4x12_006',
            ],
            requiredTool: 'hex_3',
            preconditions: [
                makeToolPrecondition('hex_3', '请先选择 3mm 内六角扳手'),
            ],
            validations: [
                makeAllScrewsValidation([
                    'screw_torso_m4x12_001',
                    'screw_torso_m4x12_002',
                    'screw_torso_m4x12_003',
                    'screw_torso_m4x12_004',
                    'screw_torso_m4x12_005',
                    'screw_torso_m4x12_006',
                ]),
            ],
            failureReasons: DEFAULT_FAILURE_REASONS,
            onSuccess: { nextStepId: 'step_014', stateTransition: null },
            onFailure: BLOCK_ON_FAILURE,
        },
        {
            stepId: 'step_014',
            stepIndex: 14,
            title: '收起视图',
            description: '将爆炸图收起，恢复正常视图。',
            action: ActionType.FOCUS_CAMERA,
            targetParts: [],
            requiredTool: null,
            preconditions: [],
            validations: [],
            failureReasons: DEFAULT_FAILURE_REASONS,
            onSuccess: { nextStepId: 'step_015', stateTransition: null },
            onFailure: BLOCK_ON_FAILURE,
        },
        {
            stepId: 'step_015',
            stepIndex: 15,
            title: '完成',
            description: '电机更换完成！请进行功能测试。',
            action: ActionType.FOCUS_CAMERA,
            targetParts: [],
            requiredTool: null,
            preconditions: [],
            validations: [],
            failureReasons: DEFAULT_FAILURE_REASONS,
            onSuccess: { nextStepId: 'end', stateTransition: SystemState.VERIFICATION },
            onFailure: BLOCK_ON_FAILURE,
        },
    ],
};

/** 裁决级 SOP：左臂关节检查 */
export const SOP_LEFT_ARM_INSPECTION: SOPScriptAdjudication = {
    sopId: 'sop-left-arm-inspect-001',
    title: '左臂关节检查',
    version: '1.0.0',
    targetModule: 'left_arm',
    estimatedTime: 15 * 60,
    difficulty: 'beginner',
    steps: [
        {
            stepId: 'step_001',
            stepIndex: 1,
            title: '定位左肩',
            description: '检查左肩 Pitch 关节。',
            action: ActionType.FOCUS_CAMERA,
            targetParts: ['left_arm_pitch_link'],
            requiredTool: null,
            preconditions: [],
            validations: [],
            failureReasons: DEFAULT_FAILURE_REASONS,
            onSuccess: { nextStepId: 'step_002', stateTransition: null },
            onFailure: BLOCK_ON_FAILURE,
        },
        {
            stepId: 'step_002',
            stepIndex: 2,
            title: '检查左肩 Roll',
            description: '检查左肩 Roll 关节螺丝。',
            action: ActionType.FOCUS_CAMERA,
            targetParts: ['left_arm_roll_link'],
            requiredTool: null,
            preconditions: [],
            validations: [],
            failureReasons: DEFAULT_FAILURE_REASONS,
            onSuccess: { nextStepId: 'step_003', stateTransition: null },
            onFailure: BLOCK_ON_FAILURE,
        },
        {
            stepId: 'step_003',
            stepIndex: 3,
            title: '检查左上臂',
            description: '检查左上臂关节连接。',
            action: ActionType.FOCUS_CAMERA,
            targetParts: ['left_arm_yaw_link'],
            requiredTool: null,
            preconditions: [],
            validations: [],
            failureReasons: DEFAULT_FAILURE_REASONS,
            onSuccess: { nextStepId: 'step_004', stateTransition: null },
            onFailure: BLOCK_ON_FAILURE,
        },
        {
            stepId: 'step_004',
            stepIndex: 4,
            title: '检查左肘',
            description: '检查左肘 Pitch 关节。',
            action: ActionType.FOCUS_CAMERA,
            targetParts: ['left_elbow_pitch_link'],
            requiredTool: null,
            preconditions: [],
            validations: [],
            failureReasons: DEFAULT_FAILURE_REASONS,
            onSuccess: { nextStepId: 'step_005', stateTransition: null },
            onFailure: BLOCK_ON_FAILURE,
        },
        {
            stepId: 'step_005',
            stepIndex: 5,
            title: '检查左前臂',
            description: '检查左前臂连接状态。',
            action: ActionType.FOCUS_CAMERA,
            targetParts: ['left_elbow_yaw_link'],
            requiredTool: null,
            preconditions: [],
            validations: [],
            failureReasons: DEFAULT_FAILURE_REASONS,
            onSuccess: { nextStepId: 'step_006', stateTransition: null },
            onFailure: BLOCK_ON_FAILURE,
        },
        {
            stepId: 'step_006',
            stepIndex: 6,
            title: '检查完成',
            description: '左臂所有关节检查完毕。',
            action: ActionType.FOCUS_CAMERA,
            targetParts: [],
            requiredTool: null,
            preconditions: [],
            validations: [],
            failureReasons: DEFAULT_FAILURE_REASONS,
            onSuccess: { nextStepId: 'end', stateTransition: SystemState.VERIFICATION },
            onFailure: BLOCK_ON_FAILURE,
        },
    ],
};

// 所有可用的裁决级 SOP 脚本
export const ALL_SOP_SCRIPTS: SOPScriptAdjudication[] = [
    ...DOCUMENT_SOP_SCRIPTS,
    SOP_TORSO_MOTOR_REPLACEMENT,
    SOP_LEFT_ARM_INSPECTION,
];

// 辅助函数
export const getSOPById = (id: string): SOPScriptAdjudication | undefined => {
    return ALL_SOP_SCRIPTS.find(s => s.sopId === id);
};

export const formatDuration = (seconds: number): string => {
    if (seconds < 60) return `${seconds}秒`;
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return secs > 0 ? `${minutes}分${secs}秒` : `${minutes}分钟`;
};
