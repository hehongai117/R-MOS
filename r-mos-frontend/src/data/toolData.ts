/**
 * toolData.ts - 工具和螺丝数据定义
 * 
 * 基于 BOM.md 中的机械元器件清单
 */

// 工具类型枚举
export type ToolType = 'hex_key' | 'screwdriver' | 'wrench' | 'pliers' | 'torque_wrench';

// 工具接口
export interface Tool {
    id: string;
    name: string;
    type: ToolType;
    size: string;          // 如 "2.5mm", "3mm"
    icon: string;          // emoji 图标
    description: string;
}

// 螺丝类型
export interface Screw {
    id: string;
    name: string;
    spec: string;          // 规格如 "M3×8"
    standard: string;      // 标准如 "GB/T 70.1-2000"
    quantity: number;      // 机器人上使用数量
    toolId: string;        // 需要的工具 ID
    torque?: number;       // 扭矩 (Nm)
}

// 零件-螺丝映射
export interface PartScrews {
    partName: string;
    screws: {
        screwId: string;
        quantity: number;
        position: string;  // 位置描述
    }[];
}

// 工具库
export const TOOLS: Tool[] = [
    {
        id: 'hex_2.5',
        name: '2.5mm 内六角扳手',
        type: 'hex_key',
        size: '2.5mm',
        icon: '🔧',
        description: '用于 M3 螺丝'
    },
    {
        id: 'hex_3',
        name: '3mm 内六角扳手',
        type: 'hex_key',
        size: '3mm',
        icon: '🔧',
        description: '用于 M4 螺丝'
    },
    {
        id: 'hex_4',
        name: '4mm 内六角扳手',
        type: 'hex_key',
        size: '4mm',
        icon: '🔧',
        description: '用于 M5 螺丝'
    },
    {
        id: 'hex_5',
        name: '5mm 内六角扳手',
        type: 'hex_key',
        size: '5mm',
        icon: '🔧',
        description: '用于 M6 螺丝'
    },
    {
        id: 'torque_wrench',
        name: '扭矩扳手',
        type: 'torque_wrench',
        size: '1-10Nm',
        icon: '🔩',
        description: '精确扭矩控制'
    },
    {
        id: 'pliers',
        name: '尖嘴钳',
        type: 'pliers',
        size: '通用',
        icon: '🔨',
        description: '夹持和取出零件'
    },
];

// 螺丝库（基于 BOM.md）
export const SCREWS: Screw[] = [
    // M3 系列
    {
        id: 'M3x6',
        name: '内六角圆柱头螺钉 M3×6',
        spec: 'M3×6',
        standard: 'GB/T 70.1-2000',
        quantity: 20,
        toolId: 'hex_2.5',
        torque: 0.5
    },
    {
        id: 'M3x8',
        name: '内六角圆柱头螺钉 M3×8',
        spec: 'M3×8',
        standard: 'GB/T 70.1-2000',
        quantity: 50,
        toolId: 'hex_2.5',
        torque: 0.5
    },
    {
        id: 'M3x10',
        name: '内六角圆柱头螺钉 M3×10',
        spec: 'M3×10',
        standard: 'GB/T 70.1-2000',
        quantity: 70,
        toolId: 'hex_2.5',
        torque: 0.5
    },
    {
        id: 'M3x12',
        name: '内六角圆柱头螺钉 M3×12',
        spec: 'M3×12',
        standard: 'GB/T 70.1-2000',
        quantity: 30,
        toolId: 'hex_2.5',
        torque: 0.5
    },
    {
        id: 'M3x16',
        name: '内六角圆柱头螺钉 M3×16',
        spec: 'M3×16',
        standard: 'GB/T 70.1-2000',
        quantity: 100,
        toolId: 'hex_2.5',
        torque: 0.5
    },
    // M4 系列
    {
        id: 'M4x8',
        name: '内六角圆柱头螺钉 M4×8',
        spec: 'M4×8',
        standard: 'GB/T 70.1-2000',
        quantity: 160,
        toolId: 'hex_3',
        torque: 1.2
    },
    {
        id: 'M4x10',
        name: '内六角圆柱头螺钉 M4×10',
        spec: 'M4×10',
        standard: 'GB/T 70.1-2000',
        quantity: 70,
        toolId: 'hex_3',
        torque: 1.2
    },
    {
        id: 'M4x12',
        name: '内六角圆柱头螺钉 M4×12',
        spec: 'M4×12',
        standard: 'GB/T 70.1-2000',
        quantity: 60,
        toolId: 'hex_3',
        torque: 1.2
    },
    {
        id: 'M4x16',
        name: '内六角圆柱头螺钉 M4×16',
        spec: 'M4×16',
        standard: 'GB/T 70.1-2000',
        quantity: 30,
        toolId: 'hex_3',
        torque: 1.2
    },
    // M5 系列
    {
        id: 'M5x10',
        name: '内六角圆柱头螺钉 M5×10',
        spec: 'M5×10',
        standard: 'GB/T 70.1-2000',
        quantity: 70,
        toolId: 'hex_4',
        torque: 2.5
    },
    // M6 系列
    {
        id: 'M6x15',
        name: '内六角沉头螺钉 M6×15',
        spec: 'M6×15',
        standard: 'GB/T 70.3-2008',
        quantity: 2,
        toolId: 'hex_5',
        torque: 4.0
    },
];

// 零件-螺丝映射（简化版，基于机器人结构）
export const PART_SCREWS: PartScrews[] = [
    {
        partName: 'base_link',
        screws: [
            { screwId: 'M4x10', quantity: 8, position: '髋关节固定螺丝' },
            { screwId: 'M3x8', quantity: 4, position: '电源板固定' },
        ]
    },
    {
        partName: 'torso_link',
        screws: [
            { screwId: 'M4x12', quantity: 6, position: '躯干连接螺丝' },
            { screwId: 'M3x10', quantity: 8, position: '胸腔夹板' },
            { screwId: 'M3x8', quantity: 4, position: 'IMU 载板' },
        ]
    },
    {
        partName: 'left_arm_pitch_link',
        screws: [
            { screwId: 'M4x8', quantity: 4, position: '肩部电机固定' },
            { screwId: 'M3x6', quantity: 2, position: '限位销' },
        ]
    },
    {
        partName: 'left_arm_roll_link',
        screws: [
            { screwId: 'M4x8', quantity: 4, position: '肩部 Roll 法兰' },
            { screwId: 'M3x8', quantity: 2, position: '轴承压板' },
        ]
    },
    {
        partName: 'left_arm_yaw_link',
        screws: [
            { screwId: 'M3x10', quantity: 4, position: '手臂连杆' },
        ]
    },
    {
        partName: 'left_elbow_pitch_link',
        screws: [
            { screwId: 'M3x8', quantity: 4, position: '肘部电机' },
        ]
    },
    {
        partName: 'left_elbow_yaw_link',
        screws: [
            { screwId: 'M3x10', quantity: 4, position: '前臂壳体连接' },
            { screwId: 'M3x8', quantity: 2, position: '末端支架定位' },
        ]
    },
    {
        partName: 'right_arm_pitch_link',
        screws: [
            { screwId: 'M4x8', quantity: 4, position: '肩部电机固定' },
            { screwId: 'M3x6', quantity: 2, position: '限位销' },
        ]
    },
    {
        partName: 'right_arm_roll_link',
        screws: [
            { screwId: 'M4x8', quantity: 4, position: '肩部 Roll 法兰' },
            { screwId: 'M3x8', quantity: 2, position: '轴承压板' },
        ]
    },
    {
        partName: 'right_arm_yaw_link',
        screws: [
            { screwId: 'M3x10', quantity: 4, position: '手臂连杆' },
        ]
    },
    {
        partName: 'right_elbow_pitch_link',
        screws: [
            { screwId: 'M3x8', quantity: 4, position: '肘部电机' },
        ]
    },
    {
        partName: 'right_elbow_yaw_link',
        screws: [
            { screwId: 'M3x10', quantity: 4, position: '前臂壳体连接' },
            { screwId: 'M3x8', quantity: 2, position: '末端支架定位' },
        ]
    },
    {
        partName: 'left_thigh_yaw_link',
        screws: [
            { screwId: 'M5x10', quantity: 6, position: '大腿电机固定' },
            { screwId: 'M4x10', quantity: 4, position: '髋夹板' },
        ]
    },
    {
        partName: 'left_thigh_roll_link',
        screws: [
            { screwId: 'M4x12', quantity: 4, position: '滚转轴承座' },
            { screwId: 'M4x8', quantity: 2, position: '编码器支架' },
        ]
    },
    {
        partName: 'left_thigh_pitch_link',
        screws: [
            { screwId: 'M4x12', quantity: 6, position: '大腿内侧板' },
        ]
    },
    {
        partName: 'left_knee_link',
        screws: [
            { screwId: 'M5x10', quantity: 4, position: '膝关节电机' },
            { screwId: 'M4x8', quantity: 4, position: '通用连接件' },
        ]
    },
    {
        partName: 'left_ankle_pitch_link',
        screws: [
            { screwId: 'M4x8', quantity: 4, position: '踝关节连接' },
        ]
    },
    {
        partName: 'left_ankle_roll_link',
        screws: [
            { screwId: 'M4x10', quantity: 4, position: '脚底板固定' },
            { screwId: 'M3x8', quantity: 2, position: '橡胶脚底' },
        ]
    },
    {
        partName: 'right_thigh_yaw_link',
        screws: [
            { screwId: 'M5x10', quantity: 6, position: '大腿电机固定' },
            { screwId: 'M4x10', quantity: 4, position: '髋夹板' },
        ]
    },
    {
        partName: 'right_thigh_roll_link',
        screws: [
            { screwId: 'M4x12', quantity: 4, position: '滚转轴承座' },
            { screwId: 'M4x8', quantity: 2, position: '编码器支架' },
        ]
    },
    {
        partName: 'right_thigh_pitch_link',
        screws: [
            { screwId: 'M4x12', quantity: 6, position: '大腿内侧板' },
        ]
    },
    {
        partName: 'right_knee_link',
        screws: [
            { screwId: 'M5x10', quantity: 4, position: '膝关节电机' },
            { screwId: 'M4x8', quantity: 4, position: '通用连接件' },
        ]
    },
    {
        partName: 'right_ankle_pitch_link',
        screws: [
            { screwId: 'M4x8', quantity: 4, position: '踝关节连接' },
        ]
    },
    {
        partName: 'right_ankle_roll_link',
        screws: [
            { screwId: 'M4x10', quantity: 4, position: '脚底板固定' },
            { screwId: 'M3x8', quantity: 2, position: '橡胶脚底' },
        ]
    },
];

// 辅助函数：根据螺丝ID获取螺丝信息
export const getScrewById = (id: string): Screw | undefined => {
    return SCREWS.find(s => s.id === id);
};

// 辅助函数：根据工具ID获取工具信息
export const getToolById = (id: string): Tool | undefined => {
    return TOOLS.find(t => t.id === id);
};

// 辅助函数：获取零件的螺丝信息
export const getPartScrews = (partName: string): PartScrews | undefined => {
    return PART_SCREWS.find(p => p.partName === partName);
};

// 辅助函数：验证工具是否匹配螺丝
export const verifyToolForScrew = (toolId: string, screwId: string): boolean => {
    const screw = getScrewById(screwId);
    return screw?.toolId === toolId;
};

// 辅助函数：根据螺丝获取推荐工具
export const getRecommendedTool = (screwId: string): Tool | undefined => {
    const screw = getScrewById(screwId);
    if (screw) {
        return getToolById(screw.toolId);
    }
    return undefined;
};
