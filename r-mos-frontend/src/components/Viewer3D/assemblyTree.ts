/**
 * assemblyTree.ts — 装配树数据 & 多级隔离集合查询
 *
 * 层级模型:
 *   L0: overview_nodes (12 组大部件)
 *   L1: links within group (各 link)
 *   L2: detail parts within link (从 DETAIL_PARTS_MAP)
 *   Leaf: 无子节点的最终零件
 *
 * 白名单：纯数据层，规格 §12.1 允许新增。
 */

import { OVERVIEW_NODE_IDS, REFERENCE_NODE_IDS, DETAIL_PARTS_MAP, type DetailPart } from './partsManifest';
import type { RobotDataManifest } from './assemblyManifest';

// ============================================================
// 1. L0 overview_node → 后代 link 映射
// ============================================================

export const ASSEMBLY_GROUPS: Record<string, {
    displayName: string;
    childLinks: string[];
    explodeDir: [number, number, number];
}> = {
    'base_link': {
        displayName: '髋部底座',
        childLinks: ['base_link'],
        explodeDir: [0, 0, -1],
    },
    'torso_link': {
        displayName: '躯干',
        childLinks: ['torso_link'],
        explodeDir: [0, 0, 1],
    },
    'left_arm_yaw_link': {
        displayName: '左上臂',
        childLinks: ['left_arm_pitch_link', 'left_arm_roll_link', 'left_arm_yaw_link'],
        explodeDir: [0, 1, 0],
    },
    'left_elbow_yaw_link': {
        displayName: '左前臂',
        childLinks: ['left_elbow_pitch_link', 'left_elbow_yaw_link'],
        explodeDir: [0, 1, -1],
    },
    'right_arm_yaw_link': {
        displayName: '右上臂',
        childLinks: ['right_arm_pitch_link', 'right_arm_roll_link', 'right_arm_yaw_link'],
        explodeDir: [0, -1, 0],
    },
    'right_elbow_yaw_link': {
        displayName: '右前臂',
        childLinks: ['right_elbow_pitch_link', 'right_elbow_yaw_link'],
        explodeDir: [0, -1, -1],
    },
    'left_thigh_pitch_link': {
        displayName: '左大腿',
        childLinks: ['left_thigh_yaw_link', 'left_thigh_roll_link', 'left_thigh_pitch_link'],
        explodeDir: [0, 1, -1],
    },
    'left_knee_link': {
        displayName: '左小腿',
        childLinks: ['left_knee_link', 'left_ankle_pitch_link'],
        explodeDir: [0, 1, -1],
    },
    'left_ankle_roll_link': {
        displayName: '左脚',
        childLinks: ['left_ankle_roll_link'],
        explodeDir: [0, 1, -1],
    },
    'right_thigh_pitch_link': {
        displayName: '右大腿',
        childLinks: ['right_thigh_yaw_link', 'right_thigh_roll_link', 'right_thigh_pitch_link'],
        explodeDir: [0, -1, -1],
    },
    'right_knee_link': {
        displayName: '右小腿',
        childLinks: ['right_knee_link', 'right_ankle_pitch_link'],
        explodeDir: [0, -1, -1],
    },
    'right_ankle_roll_link': {
        displayName: '右脚',
        childLinks: ['right_ankle_roll_link'],
        explodeDir: [0, -1, -1],
    },
};

// ============================================================
// 2. L1 查询函数（Gate-1 已有）
// ============================================================

export function getDescendantLinks(overviewNodeId: string): string[] {
    return ASSEMBLY_GROUPS[overviewNodeId]?.childLinks ?? [];
}

export function getOverviewNodeDisplayName(nodeId: string): string {
    return ASSEMBLY_GROUPS[nodeId]?.displayName ?? nodeId;
}

export function getIsolationSets(selectedNodeId: string): {
    targetLinks: string[];
    fadeLinks: string[];
    referenceLinks: string[];
} {
    const targetLinks = getDescendantLinks(selectedNodeId);
    const targetSet = new Set(targetLinks);
    const referenceSet = new Set(REFERENCE_NODE_IDS);

    const fadeLinks: string[] = [];
    for (const overviewId of OVERVIEW_NODE_IDS) {
        if (overviewId === selectedNodeId) continue;
        const children = getDescendantLinks(overviewId);
        for (const link of children) {
            if (!targetSet.has(link) && !referenceSet.has(link)) {
                fadeLinks.push(link);
            }
        }
    }

    const referenceLinks = REFERENCE_NODE_IDS.filter(id => !targetSet.has(id));
    return { targetLinks, fadeLinks, referenceLinks };
}

// ============================================================
// 3. L2 查询函数（Gate-2 新增）
// ============================================================

/** 获取某 link 的 detail parts 列表 */
export function getLinkDetailParts(linkName: string): DetailPart[] {
    return DETAIL_PARTS_MAP[linkName] ?? [];
}

/** 判断 link 是否有子零件（用于 L1→L2 钻入判断） */
export function linkHasDetailParts(linkName: string): boolean {
    return (DETAIL_PARTS_MAP[linkName]?.length ?? 0) > 0;
}

/** 获取 link 的显示名称（从 PART_METADATA 或 fallback） */
export function getLinkDisplayName(linkName: string): string {
    // 尝试从 ASSEMBLY_GROUPS 的 childLinks 反查所属组的 displayName
    // 但这里更合理的是使用 PART_METADATA 中的 displayName
    // 这个函数从调用方传入的上下文获取，此处提供基础 fallback
    const readableNames: Record<string, string> = {
        'base_link': '髋部底座',
        'torso_link': '躯干',
        'left_arm_pitch_link': '左肩 Pitch',
        'left_arm_roll_link': '左肩 Roll',
        'left_arm_yaw_link': '左上臂',
        'left_elbow_pitch_link': '左肘 Pitch',
        'left_elbow_yaw_link': '左前臂',
        'right_arm_pitch_link': '右肩 Pitch',
        'right_arm_roll_link': '右肩 Roll',
        'right_arm_yaw_link': '右上臂',
        'right_elbow_pitch_link': '右肘 Pitch',
        'right_elbow_yaw_link': '右前臂',
        'left_thigh_yaw_link': '左大腿 Yaw',
        'left_thigh_roll_link': '左大腿 Roll',
        'left_thigh_pitch_link': '左大腿 Pitch',
        'left_knee_link': '左膝关节',
        'left_ankle_pitch_link': '左踝 Pitch',
        'left_ankle_roll_link': '左踝 Roll',
        'right_thigh_yaw_link': '右大腿 Yaw',
        'right_thigh_roll_link': '右大腿 Roll',
        'right_thigh_pitch_link': '右大腿 Pitch',
        'right_knee_link': '右膝关节',
        'right_ankle_pitch_link': '右踝 Pitch',
        'right_ankle_roll_link': '右踝 Roll',
    };
    return readableNames[linkName] ?? linkName;
}

/**
 * 查找 link 所属的 overview group ID
 */
export function findOverviewGroupForLink(linkName: string): string | null {
    for (const [groupId, group] of Object.entries(ASSEMBLY_GROUPS)) {
        if (group.childLinks.includes(linkName)) {
            return groupId;
        }
    }
    return null;
}

// ============================================================
// 4. 相机预设
// ============================================================

export interface CameraPreset {
    position: [number, number, number];
    target: [number, number, number];
    fov: number;
}

export const L1_CAMERA_PRESETS: Record<string, CameraPreset> = {
    'base_link': { position: [0.8, 0.3, -0.2], target: [0, 0.3, -0.1], fov: 45 },
    'torso_link': { position: [0.8, 0.5, 0.8], target: [0, 0.5, 0.5], fov: 45 },
    'left_arm_yaw_link': { position: [0.5, 1.2, 0.8], target: [0, 0.7, 0.5], fov: 45 },
    'left_elbow_yaw_link': { position: [0.3, 1.2, 0.3], target: [-0.2, 0.8, 0.2], fov: 45 },
    'right_arm_yaw_link': { position: [0.5, -0.6, 0.8], target: [0, -0.1, 0.5], fov: 45 },
    'right_elbow_yaw_link': { position: [0.3, -0.6, 0.3], target: [-0.2, -0.2, 0.2], fov: 45 },
    'left_thigh_pitch_link': { position: [0.8, 0.8, -0.3], target: [0, 0.4, -0.3], fov: 45 },
    'left_knee_link': { position: [0.8, 0.8, -0.8], target: [0, 0.4, -0.7], fov: 45 },
    'left_ankle_roll_link': { position: [0.6, 0.8, -1.2], target: [0, 0.4, -1.0], fov: 45 },
    'right_thigh_pitch_link': { position: [0.8, -0.4, -0.3], target: [0, -0.1, -0.3], fov: 45 },
    'right_knee_link': { position: [0.8, -0.4, -0.8], target: [0, -0.1, -0.7], fov: 45 },
    'right_ankle_roll_link': { position: [0.6, -0.4, -1.2], target: [0, -0.1, -1.0], fov: 45 },
};

export function getL1CameraPreset(overviewNodeId: string): CameraPreset | undefined {
    return L1_CAMERA_PRESETS[overviewNodeId];
}

/**
 * L2 相机预设 — 聚焦到单个 link 的子零件。
 * 使用对应 L1 预设但缩短距离以放大。
 */
export function getL2CameraPreset(linkName: string): CameraPreset {
    const groupId = findOverviewGroupForLink(linkName);
    const l1 = groupId ? L1_CAMERA_PRESETS[groupId] : undefined;
    if (l1) {
        // 缩短相机距离 60%，保持方向
        const dx = l1.position[0] - l1.target[0];
        const dy = l1.position[1] - l1.target[1];
        const dz = l1.position[2] - l1.target[2];
        return {
            position: [
                l1.target[0] + dx * 0.6,
                l1.target[1] + dy * 0.6,
                l1.target[2] + dz * 0.6,
            ],
            target: l1.target,
            fov: 40,
        };
    }
    // fallback
    return { position: [0.5, 0.5, 0.5], target: [0, 0.3, 0], fov: 40 };
}

// ============================================================
// 5. Manifest-driven 函数（manifest 优先，硬编码数据兜底）
// ============================================================

/** 从 manifest 构建装配组（替代硬编码 ASSEMBLY_GROUPS） */
export function buildAssemblyGroupsFromManifest(
    manifest: RobotDataManifest
): Record<string, { displayName: string; childLinks: string[]; explodeDir: [number, number, number] }> {
    const groups = manifest.overview_config?.assembly_groups;
    if (!groups) return ASSEMBLY_GROUPS; // fallback

    const result: Record<string, { displayName: string; childLinks: string[]; explodeDir: [number, number, number] }> = {};
    for (const [key, val] of Object.entries(groups)) {
        result[key] = {
            displayName: val.display_name,
            childLinks: val.child_links,
            explodeDir: val.explode_dir as [number, number, number],
        };
    }
    return result;
}

/** 从 manifest 获取 L1 相机预设（替代硬编码 L1_CAMERA_PRESETS） */
export function getCameraPresetFromManifest(
    manifest: RobotDataManifest,
    nodeId: string
): CameraPreset | null {
    const preset = manifest.camera_presets?.[nodeId];
    if (!preset) return null;
    return {
        position: preset.position as [number, number, number],
        target: preset.target as [number, number, number],
        fov: preset.fov,
    };
}

/** 从 manifest 获取显示名（替代硬编码 readableNames） */
export function getDisplayNameFromManifest(
    manifest: RobotDataManifest,
    nodeId: string
): string {
    return manifest.display_names?.[nodeId] ?? nodeId.replace(/_/g, ' ');
}
