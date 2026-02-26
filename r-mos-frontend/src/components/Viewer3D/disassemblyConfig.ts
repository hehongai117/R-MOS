/**
 * disassemblyConfig.ts - 拆卸动画序列配置
 *
 * 定义螺丝旋转抽离 + 零部件分离的动画序列数据。
 * 螺丝位置基于各 link 接合处推算，后续可通过 SOP 数据精确定义。
 */

/** 螺丝动画配置 */
export interface ScrewAnimConfig {
    /** 唯一 ID */
    id: string;
    /** 螺丝 GLB 路径 (相对于 /models/parts/) */
    glbPath: string;
    /** 螺丝在模型上的 3D 位置 */
    position: [number, number, number];
    /** 旋转轴方向（螺丝朝向），归一化向量 */
    axis: [number, number, number];
    /** 抽离距离（场景单位） */
    extractDistance: number;
    /** 旋转圈数 */
    rotations: number;
    /** 所属 link */
    parentLink: string;
    /** 显示名 */
    label: string;
}

/** 零件分离动画配置 */
export interface PartAnimConfig {
    /** link 名称 */
    linkName: string;
    /** 分离偏移量（最终位置） */
    detachOffset: [number, number, number];
    /** 显示名 */
    label: string;
}

/** 动画时长配置 */
export const ANIM_TIMING = {
    /** 单颗螺丝旋转抽离时长 (秒) */
    SCREW_DURATION: 1.5,
    /** 螺丝间间隔 (秒) */
    SCREW_GAP: 0.3,
    /** 螺丝阶段到零件阶段的过渡间隔 (秒) */
    PHASE_GAP: 0.8,
    /** 单个零件分离时长 (秒) */
    PART_DURATION: 0.8,
    /** 零件间间隔 (秒) */
    PART_GAP: 0.2,
};

/**
 * 螺丝拆卸序列
 *
 * 按拆卸顺序排列。位置基于各 link 接合处推算。
 * 实际螺丝位置可后续通过 SOP 数据精确校准。
 */
export const SCREW_SEQUENCE: ScrewAnimConfig[] = [
    // ---- 躯干固定螺丝 ----
    {
        id: 'screw_torso_01',
        glbPath: 'screws/内六角圆柱头螺钉M3x10.glb',
        position: [0.04, 0.02, 0.52],
        axis: [1, 0, 0],
        extractDistance: 0.08,
        rotations: 3,
        parentLink: 'torso_link',
        label: '躯干螺丝 1',
    },
    {
        id: 'screw_torso_02',
        glbPath: 'screws/内六角圆柱头螺钉M3x10.glb',
        position: [-0.04, 0.02, 0.52],
        axis: [-1, 0, 0],
        extractDistance: 0.08,
        rotations: 3,
        parentLink: 'torso_link',
        label: '躯干螺丝 2',
    },
    {
        id: 'screw_torso_03',
        glbPath: 'screws/内六角圆柱头螺钉M3x10.glb',
        position: [0.04, -0.02, 0.52],
        axis: [1, 0, 0],
        extractDistance: 0.08,
        rotations: 3,
        parentLink: 'torso_link',
        label: '躯干螺丝 3',
    },
    {
        id: 'screw_torso_04',
        glbPath: 'screws/内六角圆柱头螺钉M3x10.glb',
        position: [-0.04, -0.02, 0.52],
        axis: [-1, 0, 0],
        extractDistance: 0.08,
        rotations: 3,
        parentLink: 'torso_link',
        label: '躯干螺丝 4',
    },

    // ---- 左臂肩部螺丝 ----
    {
        id: 'screw_left_shoulder_01',
        glbPath: 'screws/内六角圆柱头螺钉M4x10.glb',
        position: [0.03, 0.1, 0.58],
        axis: [0, 1, 0],
        extractDistance: 0.06,
        rotations: 3,
        parentLink: 'left_arm_pitch_link',
        label: '左肩螺丝',
    },

    // ---- 右臂肩部螺丝 ----
    {
        id: 'screw_right_shoulder_01',
        glbPath: 'screws/内六角圆柱头螺钉M4x10.glb',
        position: [0.03, -0.1, 0.58],
        axis: [0, -1, 0],
        extractDistance: 0.06,
        rotations: 3,
        parentLink: 'right_arm_pitch_link',
        label: '右肩螺丝',
    },

    // ---- 左腿连接螺丝 ----
    {
        id: 'screw_left_hip_01',
        glbPath: 'screws/内六角圆柱头螺钉M4x12.glb',
        position: [0.01, 0.06, 0.38],
        axis: [0, 1, 0],
        extractDistance: 0.06,
        rotations: 3,
        parentLink: 'left_thigh_yaw_link',
        label: '左髋螺丝',
    },

    // ---- 右腿连接螺丝 ----
    {
        id: 'screw_right_hip_01',
        glbPath: 'screws/内六角圆柱头螺钉M4x12.glb',
        position: [0.01, -0.06, 0.38],
        axis: [0, -1, 0],
        extractDistance: 0.06,
        rotations: 3,
        parentLink: 'right_thigh_yaw_link',
        label: '右髋螺丝',
    },
];

/**
 * 零件分离序列（按拆卸顺序排列）
 * 偏移量复用 Atom01Interactive 中的 EXPLODE_OFFSETS，放大到完全分离。
 */
export const PART_SEQUENCE: PartAnimConfig[] = [
    // 先拆外围部件，再拆核心
    { linkName: 'left_elbow_yaw_link', detachOffset: [-0.35, 0.5, -0.1], label: '左前臂' },
    { linkName: 'right_elbow_yaw_link', detachOffset: [-0.35, -0.5, -0.1], label: '右前臂' },
    { linkName: 'left_elbow_pitch_link', detachOffset: [-0.28, 0.42, 0], label: '左肘' },
    { linkName: 'right_elbow_pitch_link', detachOffset: [-0.28, -0.42, 0], label: '右肘' },
    { linkName: 'left_arm_yaw_link', detachOffset: [-0.22, 0.35, 0.08], label: '左上臂' },
    { linkName: 'right_arm_yaw_link', detachOffset: [-0.22, -0.35, 0.08], label: '右上臂' },
    { linkName: 'left_arm_roll_link', detachOffset: [-0.18, 0.28, 0.15], label: '左肩 Roll' },
    { linkName: 'right_arm_roll_link', detachOffset: [-0.18, -0.28, 0.15], label: '右肩 Roll' },
    { linkName: 'left_arm_pitch_link', detachOffset: [-0.15, 0.22, 0.18], label: '左肩' },
    { linkName: 'right_arm_pitch_link', detachOffset: [-0.15, -0.22, 0.18], label: '右肩' },
    { linkName: 'torso_link', detachOffset: [0, 0, 0.25], label: '躯干' },
    { linkName: 'left_ankle_roll_link', detachOffset: [0, 0.3, -0.7], label: '左脚' },
    { linkName: 'right_ankle_roll_link', detachOffset: [0, -0.3, -0.7], label: '右脚' },
    { linkName: 'left_ankle_pitch_link', detachOffset: [0, 0.28, -0.55], label: '左踝' },
    { linkName: 'right_ankle_pitch_link', detachOffset: [0, -0.28, -0.55], label: '右踝' },
    { linkName: 'left_knee_link', detachOffset: [0, 0.24, -0.4], label: '左膝' },
    { linkName: 'right_knee_link', detachOffset: [0, -0.24, -0.4], label: '右膝' },
    { linkName: 'left_thigh_pitch_link', detachOffset: [0, 0.2, -0.25], label: '左大腿' },
    { linkName: 'right_thigh_pitch_link', detachOffset: [0, -0.2, -0.25], label: '右大腿' },
    { linkName: 'left_thigh_roll_link', detachOffset: [0, 0.16, -0.15], label: '左大腿 Roll' },
    { linkName: 'right_thigh_roll_link', detachOffset: [0, -0.16, -0.15], label: '右大腿 Roll' },
    { linkName: 'left_thigh_yaw_link', detachOffset: [0, 0.12, -0.08], label: '左大腿 Yaw' },
    { linkName: 'right_thigh_yaw_link', detachOffset: [0, -0.12, -0.08], label: '右大腿 Yaw' },
];

/**
 * 计算总动画时长
 */
export function getTotalDuration(): number {
    const screwTotal =
        SCREW_SEQUENCE.length * ANIM_TIMING.SCREW_DURATION +
        (SCREW_SEQUENCE.length - 1) * ANIM_TIMING.SCREW_GAP;

    const partTotal =
        PART_SEQUENCE.length * ANIM_TIMING.PART_DURATION +
        (PART_SEQUENCE.length - 1) * ANIM_TIMING.PART_GAP;

    return screwTotal + ANIM_TIMING.PHASE_GAP + partTotal;
}

/**
 * 根据全局时间获取某颗螺丝的动画进度
 * @returns 0~1 的进度值，-1 表示尚未开始
 */
export function getScrewProgress(globalTime: number, screwIndex: number): number {
    const startTime = screwIndex * (ANIM_TIMING.SCREW_DURATION + ANIM_TIMING.SCREW_GAP);
    const localTime = globalTime - startTime;

    if (localTime < 0) return -1;
    if (localTime >= ANIM_TIMING.SCREW_DURATION) return 1;
    return localTime / ANIM_TIMING.SCREW_DURATION;
}

/**
 * 根据全局时间获取某个零件的分离进度
 * @returns 0~1 的进度值，-1 表示尚未开始
 */
export function getPartProgress(globalTime: number, partIndex: number): number {
    const screwPhaseEnd =
        SCREW_SEQUENCE.length * (ANIM_TIMING.SCREW_DURATION + ANIM_TIMING.SCREW_GAP);
    const partPhaseStart = screwPhaseEnd + ANIM_TIMING.PHASE_GAP;

    const startTime =
        partPhaseStart +
        partIndex * (ANIM_TIMING.PART_DURATION + ANIM_TIMING.PART_GAP);

    const localTime = globalTime - startTime;

    if (localTime < 0) return -1;
    if (localTime >= ANIM_TIMING.PART_DURATION) return 1;
    return localTime / ANIM_TIMING.PART_DURATION;
}
