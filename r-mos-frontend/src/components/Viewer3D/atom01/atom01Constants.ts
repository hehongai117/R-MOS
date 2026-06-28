/**
 * atom01Constants.ts — 硬编码回退常量（ATOM-01 专用）
 *
 * @deprecated 在 manifest 可用时请使用 buildPartMetadata / buildExplodeOffsetMap / buildJointAxisMap。
 */

// ---------------------------------------------------------------------------
// PartInfo 类型（从主文件移出，Atom01Interactive.tsx 重新 re-export）
// ---------------------------------------------------------------------------
export interface PartInfo {
    name: string;
    displayName: string;
    group: 'base' | 'torso' | 'left_arm' | 'right_arm' | 'left_leg' | 'right_leg';
    jointName?: string;
}

// ---------------------------------------------------------------------------
// PART_METADATA
// ---------------------------------------------------------------------------
/**
 * @deprecated Hardcoded fallback — use buildPartMetadata(manifest) when manifest is available.
 * Kept to ensure part metadata works without a manifest.
 */
export const PART_METADATA: Record<string, PartInfo> = {
    'base_link': { name: 'base_link', displayName: '髋部底座', group: 'base' },
    'torso_link': { name: 'torso_link', displayName: '躯干', group: 'torso', jointName: 'torso_joint' },
    'left_thigh_yaw_link': { name: 'left_thigh_yaw_link', displayName: '左大腿 Yaw', group: 'left_leg', jointName: 'left_thigh_yaw_joint' },
    'left_thigh_roll_link': { name: 'left_thigh_roll_link', displayName: '左大腿 Roll', group: 'left_leg', jointName: 'left_thigh_roll_joint' },
    'left_thigh_pitch_link': { name: 'left_thigh_pitch_link', displayName: '左大腿 Pitch', group: 'left_leg', jointName: 'left_thigh_pitch_joint' },
    'left_knee_link': { name: 'left_knee_link', displayName: '左膝关节', group: 'left_leg', jointName: 'left_knee_joint' },
    'left_ankle_pitch_link': { name: 'left_ankle_pitch_link', displayName: '左踝 Pitch', group: 'left_leg', jointName: 'left_ankle_pitch_joint' },
    'left_ankle_roll_link': { name: 'left_ankle_roll_link', displayName: '左踝 Roll', group: 'left_leg', jointName: 'left_ankle_roll_joint' },
    'right_thigh_yaw_link': { name: 'right_thigh_yaw_link', displayName: '右大腿 Yaw', group: 'right_leg', jointName: 'right_thigh_yaw_joint' },
    'right_thigh_roll_link': { name: 'right_thigh_roll_link', displayName: '右大腿 Roll', group: 'right_leg', jointName: 'right_thigh_roll_joint' },
    'right_thigh_pitch_link': { name: 'right_thigh_pitch_link', displayName: '右大腿 Pitch', group: 'right_leg', jointName: 'right_thigh_pitch_joint' },
    'right_knee_link': { name: 'right_knee_link', displayName: '右膝关节', group: 'right_leg', jointName: 'right_knee_joint' },
    'right_ankle_pitch_link': { name: 'right_ankle_pitch_link', displayName: '右踝 Pitch', group: 'right_leg', jointName: 'right_ankle_pitch_joint' },
    'right_ankle_roll_link': { name: 'right_ankle_roll_link', displayName: '右踝 Roll', group: 'right_leg', jointName: 'right_ankle_roll_joint' },
    'left_arm_pitch_link': { name: 'left_arm_pitch_link', displayName: '左肩 Pitch', group: 'left_arm', jointName: 'left_arm_pitch_joint' },
    'left_arm_roll_link': { name: 'left_arm_roll_link', displayName: '左肩 Roll', group: 'left_arm', jointName: 'left_arm_roll_joint' },
    'left_arm_yaw_link': { name: 'left_arm_yaw_link', displayName: '左上臂', group: 'left_arm', jointName: 'left_arm_yaw_joint' },
    'left_elbow_pitch_link': { name: 'left_elbow_pitch_link', displayName: '左肘 Pitch', group: 'left_arm', jointName: 'left_elbow_pitch_joint' },
    'left_elbow_yaw_link': { name: 'left_elbow_yaw_link', displayName: '左前臂', group: 'left_arm', jointName: 'left_elbow_yaw_joint' },
    'right_arm_pitch_link': { name: 'right_arm_pitch_link', displayName: '右肩 Pitch', group: 'right_arm', jointName: 'right_arm_pitch_joint' },
    'right_arm_roll_link': { name: 'right_arm_roll_link', displayName: '右肩 Roll', group: 'right_arm', jointName: 'right_arm_roll_joint' },
    'right_arm_yaw_link': { name: 'right_arm_yaw_link', displayName: '右上臂', group: 'right_arm', jointName: 'right_arm_yaw_joint' },
    'right_elbow_pitch_link': { name: 'right_elbow_pitch_link', displayName: '右肘 Pitch', group: 'right_arm', jointName: 'right_elbow_pitch_joint' },
    'right_elbow_yaw_link': { name: 'right_elbow_yaw_link', displayName: '右前臂', group: 'right_arm', jointName: 'right_elbow_yaw_joint' },
};

// ---------------------------------------------------------------------------
// SubPart tuning
// ---------------------------------------------------------------------------
export type LinkSubPartTuning = {
    maxValidRadius: number;
    maxRenderRadius: number;
    spreadBoost: number;
    l1MaxParts: number;
};

export const DEFAULT_SUBPART_TUNING: LinkSubPartTuning = {
    maxValidRadius: 0.18,
    maxRenderRadius: 0.09,
    spreadBoost: 1,
    l1MaxParts: 8,
};

export const LINK_SUBPART_TUNING: Partial<Record<string, LinkSubPartTuning>> = {
    base_link: { maxValidRadius: 0.16, maxRenderRadius: 0.065, spreadBoost: 2.0, l1MaxParts: 10 },
    torso_link: { maxValidRadius: 0.14, maxRenderRadius: 0.045, spreadBoost: 2.2, l1MaxParts: 8 },
    left_arm_pitch_link: { maxValidRadius: 0.16, maxRenderRadius: 0.08, spreadBoost: 1.45, l1MaxParts: 8 },
    left_arm_roll_link: { maxValidRadius: 0.16, maxRenderRadius: 0.08, spreadBoost: 1.45, l1MaxParts: 8 },
    left_arm_yaw_link: { maxValidRadius: 0.16, maxRenderRadius: 0.075, spreadBoost: 1.6, l1MaxParts: 10 },
    left_elbow_pitch_link: { maxValidRadius: 0.16, maxRenderRadius: 0.075, spreadBoost: 1.55, l1MaxParts: 8 },
    left_elbow_yaw_link: { maxValidRadius: 0.16, maxRenderRadius: 0.075, spreadBoost: 1.55, l1MaxParts: 10 },
    right_arm_pitch_link: { maxValidRadius: 0.16, maxRenderRadius: 0.08, spreadBoost: 1.45, l1MaxParts: 8 },
    right_arm_roll_link: { maxValidRadius: 0.16, maxRenderRadius: 0.08, spreadBoost: 1.45, l1MaxParts: 8 },
    right_arm_yaw_link: { maxValidRadius: 0.16, maxRenderRadius: 0.075, spreadBoost: 1.6, l1MaxParts: 8 },
    right_elbow_pitch_link: { maxValidRadius: 0.16, maxRenderRadius: 0.075, spreadBoost: 1.55, l1MaxParts: 8 },
    right_elbow_yaw_link: { maxValidRadius: 0.16, maxRenderRadius: 0.075, spreadBoost: 1.55, l1MaxParts: 8 },
    left_thigh_yaw_link: { maxValidRadius: 0.17, maxRenderRadius: 0.07, spreadBoost: 1.35, l1MaxParts: 10 },
    left_thigh_roll_link: { maxValidRadius: 0.17, maxRenderRadius: 0.07, spreadBoost: 1.35, l1MaxParts: 10 },
    left_thigh_pitch_link: { maxValidRadius: 0.17, maxRenderRadius: 0.07, spreadBoost: 1.35, l1MaxParts: 10 },
    left_knee_link: { maxValidRadius: 0.17, maxRenderRadius: 0.07, spreadBoost: 1.25, l1MaxParts: 10 },
    left_ankle_pitch_link: { maxValidRadius: 0.17, maxRenderRadius: 0.075, spreadBoost: 1.15, l1MaxParts: 10 },
    left_ankle_roll_link: { maxValidRadius: 0.17, maxRenderRadius: 0.075, spreadBoost: 1.2, l1MaxParts: 10 },
    right_thigh_yaw_link: { maxValidRadius: 0.17, maxRenderRadius: 0.07, spreadBoost: 1.35, l1MaxParts: 10 },
    right_thigh_roll_link: { maxValidRadius: 0.17, maxRenderRadius: 0.07, spreadBoost: 1.35, l1MaxParts: 10 },
    right_thigh_pitch_link: { maxValidRadius: 0.17, maxRenderRadius: 0.07, spreadBoost: 1.35, l1MaxParts: 10 },
    right_knee_link: { maxValidRadius: 0.17, maxRenderRadius: 0.07, spreadBoost: 1.25, l1MaxParts: 10 },
    right_ankle_pitch_link: { maxValidRadius: 0.17, maxRenderRadius: 0.075, spreadBoost: 1.15, l1MaxParts: 10 },
    right_ankle_roll_link: { maxValidRadius: 0.17, maxRenderRadius: 0.075, spreadBoost: 1.2, l1MaxParts: 10 },
};

export const SUBPART_OUTLIER_ABS_MAX_DIM = 3.5;
export const CORE_OUTLIER_ABS_MAX_DIM = 6.0;

export const PARTS_GLB_BASE = '/models/parts';

// ---------------------------------------------------------------------------
// EXPLODE_OFFSETS
// ---------------------------------------------------------------------------
/**
 * @deprecated Hardcoded fallback — use buildExplodeOffsetMap(manifest) when manifest is available.
 * Kept to ensure explode view works without a manifest.
 */
export const EXPLODE_OFFSETS: Record<string, [number, number, number]> = {
    'base_link': [0, 0, 0],
    'torso_link': [0, 0, 0.4],
    'left_arm_pitch_link': [-0.3, 0.4, 0.3],
    'left_arm_roll_link': [-0.35, 0.5, 0.3],
    'left_arm_yaw_link': [-0.4, 0.6, 0.15],
    'left_elbow_pitch_link': [-0.5, 0.75, 0],
    'left_elbow_yaw_link': [-0.6, 0.9, -0.15],
    'right_arm_pitch_link': [-0.3, -0.4, 0.3],
    'right_arm_roll_link': [-0.35, -0.5, 0.3],
    'right_arm_yaw_link': [-0.4, -0.6, 0.15],
    'right_elbow_pitch_link': [-0.5, -0.75, 0],
    'right_elbow_yaw_link': [-0.6, -0.9, -0.15],
    'left_thigh_yaw_link': [0, 0.25, -0.15],
    'left_thigh_roll_link': [0, 0.3, -0.3],
    'left_thigh_pitch_link': [0, 0.35, -0.45],
    'left_knee_link': [0, 0.4, -0.7],
    'left_ankle_pitch_link': [0, 0.5, -1.0],
    'left_ankle_roll_link': [0, 0.55, -1.3],
    'right_thigh_yaw_link': [0, -0.25, -0.15],
    'right_thigh_roll_link': [0, -0.3, -0.3],
    'right_thigh_pitch_link': [0, -0.35, -0.45],
    'right_knee_link': [0, -0.4, -0.7],
    'right_ankle_pitch_link': [0, -0.5, -1.0],
    'right_ankle_roll_link': [0, -0.55, -1.3],
};

// ---------------------------------------------------------------------------
// JOINTS / JOINTS_AXIS_FALLBACK
// ---------------------------------------------------------------------------
/**
 * @deprecated Hardcoded fallback — use buildJointAxisMap(manifest) when manifest is available.
 * Kept to ensure joint animation works without a manifest.
 */
export const JOINTS: Record<string, { axis: [number, number, number] }> = {
    'torso_joint': { axis: [0, 0, 1] },
    'left_thigh_yaw_joint': { axis: [-0.5, 0, -0.866] },
    'left_thigh_roll_joint': { axis: [0.866, 0, -0.5] },
    'left_thigh_pitch_joint': { axis: [0, 1, 0] },
    'left_knee_joint': { axis: [0, 1, 0] },
    'left_ankle_pitch_joint': { axis: [0, 1, 0] },
    'left_ankle_roll_joint': { axis: [1, 0, 0] },
    'right_thigh_yaw_joint': { axis: [-0.5, 0, -0.866] },
    'right_thigh_roll_joint': { axis: [0.866, 0, -0.5] },
    'right_thigh_pitch_joint': { axis: [0, 1, 0] },
    'right_knee_joint': { axis: [0, 1, 0] },
    'right_ankle_pitch_joint': { axis: [0, 1, 0] },
    'right_ankle_roll_joint': { axis: [1, 0, 0] },
    'left_arm_pitch_joint': { axis: [0, 1, 0] },
    'left_arm_roll_joint': { axis: [1, 0, 0] },
    'left_arm_yaw_joint': { axis: [0, 0, -1] },
    'left_elbow_pitch_joint': { axis: [0, 1, 0] },
    'left_elbow_yaw_joint': { axis: [0, 0, -1] },
    'right_arm_pitch_joint': { axis: [0, 1, 0] },
    'right_arm_roll_joint': { axis: [1, 0, 0] },
    'right_arm_yaw_joint': { axis: [0, 0, -1] },
    'right_elbow_pitch_joint': { axis: [0, 1, 0] },
    'right_elbow_yaw_joint': { axis: [0, 0, -1] },
};

/** Flattened fallback: same data as JOINTS but in the format returned by buildJointAxisMap. */
export const JOINTS_AXIS_FALLBACK: Record<string, [number, number, number]> = Object.fromEntries(
    Object.entries(JOINTS).map(([k, v]) => [k, v.axis])
);
