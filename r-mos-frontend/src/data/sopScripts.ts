/**
 * sopScripts.ts - SOP 脚本数据定义
 * 
 * 定义维保 SOP 的 JSON 脚本格式
 */

// SOP 步骤类型
export type SOPStepType = 'highlight' | 'explode' | 'tool_check' | 'action' | 'warning' | 'complete';

// 单个 SOP 步骤
export interface SOPStep {
    id: number;
    type: SOPStepType;
    title: string;
    description: string;
    partName?: string;           // 高亮的零件
    screwId?: string;            // 涉及的螺丝
    toolId?: string;             // 需要的工具
    explodeAmount?: number;      // 爆炸程度
    duration?: number;           // 预计时长(秒)
    warningLevel?: 'info' | 'warning' | 'danger';
}

// SOP 脚本
export interface SOPScript {
    id: string;
    name: string;
    description: string;
    category: 'maintenance' | 'repair' | 'inspection' | 'assembly';
    estimatedTime: number;       // 预计总时长(分钟)
    difficulty: 'easy' | 'medium' | 'hard';
    steps: SOPStep[];
}

// 示例 SOP 脚本：躯干电机更换
export const SOP_TORSO_MOTOR_REPLACEMENT: SOPScript = {
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

// 示例 SOP 脚本：左臂关节检查
export const SOP_LEFT_ARM_INSPECTION: SOPScript = {
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

// 所有可用的 SOP 脚本
export const ALL_SOP_SCRIPTS: SOPScript[] = [
    SOP_TORSO_MOTOR_REPLACEMENT,
    SOP_LEFT_ARM_INSPECTION,
];

// 辅助函数
export const getSOPById = (id: string): SOPScript | undefined => {
    return ALL_SOP_SCRIPTS.find(s => s.id === id);
};

export const formatDuration = (seconds: number): string => {
    if (seconds < 60) return `${seconds}秒`;
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return secs > 0 ? `${minutes}分${secs}秒` : `${minutes}分钟`;
};
