/**
 * partsManifest.ts - 零件细节模型清单
 *
 * 将 robots/atom01/ 的 link-level 模型映射到 parts/ 下对应的细节子零件。
 * 用于按需加载：用户选中某个 link 时，动态加载对应的所有子零件 GLB。
 *
 * 路径约定：
 *  - frames:  /models/parts/frames/{文件名}.glb
 *  - screws:  /models/parts/screws/{文件名}.glb
 *  - nuts:    /models/parts/nuts/{文件名}.glb
 *  - misc:    /models/parts/misc/{文件名}.glb
 *  - etc.
 */
import overviewNodes from './overview_nodes.json';

export interface DetailPart {
    /** 子零件显示名 */
    displayName: string;
    /** GLB 路径（相对于 /models/parts/） */
    path: string;
    /** 零件分类 */
    category: 'frame' | 'screw' | 'nut' | 'bearing' | 'calibration' | 'electronics' | 'misc';
}

interface OverviewNodesConfig {
    version: string;
    overview_depth: number;
    overview_nodes: string[];
    reference_set: string[];
    camera_presets: {
        L0_OVERVIEW_PRESET: {
            position: [number, number, number];
            target: [number, number, number];
            fov: number;
        };
    };
}

const OVERVIEW_CONFIG = overviewNodes as OverviewNodesConfig;

/** Gate-0 证据源：L0 总览可点击节点集合（8~20） */
export const OVERVIEW_NODE_IDS: string[] = OVERVIEW_CONFIG.overview_nodes;

/** Gate-0 主参照集合（reference_set） */
export const REFERENCE_NODE_IDS: string[] = OVERVIEW_CONFIG.reference_set;

/** Gate-0 固定相机预设 */
export const L0_OVERVIEW_PRESET = {
    position: OVERVIEW_CONFIG.camera_presets.L0_OVERVIEW_PRESET.position as [number, number, number],
    target: OVERVIEW_CONFIG.camera_presets.L0_OVERVIEW_PRESET.target as [number, number, number],
    fov: OVERVIEW_CONFIG.camera_presets.L0_OVERVIEW_PRESET.fov,
};

/** Gate-1/2 密度预算（集中配置） */
export const ISOLATION_DENSITY_CONFIG = {
    N_embed: 16,
    N_fullscreen: 24,
    P_max: Math.floor(16 * 0.5),
    proxy_enable_threshold_px: 24,
} as const;

/** Gate-0 冻结值：无预设相机时用于 bbox fit */
export const BBOX_FIT_PADDING = 1.2 as const;

/** UI 能力开关（可由上层注入覆盖） */
export const UI_CAPABILITIES = {
    allow_toggle_fade_hide: true,
    allow_fullscreen: true,
    allow_cross_jump: true,
} as const;

export function isOverviewNode(nodeId: string): boolean {
    return OVERVIEW_NODE_IDS.includes(nodeId);
}

/**
 * 每个 link 对应的细节子零件列表。
 * frames/ 目录下的 GLB 文件按 `{link_name}.glb`, `{link_name}_1.glb` 等命名，
 * 为 link 的结构子件拆分（前侧板、后侧板等）。
 */
export const DETAIL_PARTS_MAP: Record<string, DetailPart[]> = {
    // ======== 底座 ========
    'base_link': [
        { displayName: '底座结构件', path: 'frames/base_link.glb', category: 'frame' },
        { displayName: '底座结构件 A', path: 'frames/base_link_1.glb', category: 'frame' },
        { displayName: '底座结构件 B', path: 'frames/base_link_2.glb', category: 'frame' },
        { displayName: '底座结构件 C', path: 'frames/base_link_3.glb', category: 'frame' },
        { displayName: '腰部标定件', path: 'calibration/腰部标定件数量1.glb', category: 'calibration' },
    ],

    // ======== 躯干 ========
    'torso_link': [
        { displayName: '躯干结构件', path: 'frames/torso_link.glb', category: 'frame' },
        { displayName: '躯干结构件 A', path: 'frames/torso_link_1.glb', category: 'frame' },
        { displayName: '躯干结构件 B', path: 'frames/torso_link_2.glb', category: 'frame' },
        { displayName: '躯干结构件 C', path: 'frames/torso_link_3.glb', category: 'frame' },
        { displayName: '侧板横板', path: 'misc/侧板横板.glb', category: 'misc' },
        { displayName: '侧板横板 A', path: 'misc/侧板横板_1.glb', category: 'misc' },
        { displayName: 'PCB载板', path: 'misc/PCB载板.glb', category: 'electronics' },
        { displayName: 'PCB载板 A', path: 'misc/PCB载板_1.glb', category: 'electronics' },
        { displayName: 'IMU载板', path: 'misc/IMU载板.glb', category: 'electronics' },
        { displayName: 'IMU载板 A', path: 'misc/IMU载板_1.glb', category: 'electronics' },
        { displayName: 'OPI 5Plus PCB', path: 'misc/OPI_5PLUS_PCBA.glb', category: 'electronics' },
        { displayName: '3D PCB7', path: 'misc/3D_PCB7_2025_07_10.glb', category: 'electronics' },
        { displayName: '把手', path: 'misc/把手.glb', category: 'misc' },
        { displayName: '电池盒', path: 'misc/电池盒粗略尺寸.glb', category: 'misc' },
    ],

    // ======== 左臂 ========
    'left_arm_pitch_link': [
        { displayName: '左肩结构件', path: 'frames/left_arm_pitch_link.glb', category: 'frame' },
        { displayName: '左肩结构件 A', path: 'frames/left_arm_pitch_link_1.glb', category: 'frame' },
        { displayName: '左肩结构件 B', path: 'frames/left_arm_pitch_link_2.glb', category: 'frame' },
        { displayName: '左肩结构件 C', path: 'frames/left_arm_pitch_link_3.glb', category: 'frame' },
    ],
    'left_arm_roll_link': [
        { displayName: '左肩 Roll 结构件', path: 'frames/left_arm_roll_link.glb', category: 'frame' },
        { displayName: '左肩 Roll A', path: 'frames/left_arm_roll_link_1.glb', category: 'frame' },
        { displayName: '左肩 Roll B', path: 'frames/left_arm_roll_link_2.glb', category: 'frame' },
        { displayName: '左肩 Roll C', path: 'frames/left_arm_roll_link_3.glb', category: 'frame' },
    ],
    'left_arm_yaw_link': [
        { displayName: '左上臂结构件', path: 'frames/left_arm_yaw_link.glb', category: 'frame' },
        { displayName: '左上臂 A', path: 'frames/left_arm_yaw_link_1.glb', category: 'frame' },
        { displayName: '左上臂 B', path: 'frames/left_arm_yaw_link_2.glb', category: 'frame' },
        { displayName: '左上臂 C', path: 'frames/left_arm_yaw_link_3.glb', category: 'frame' },
        { displayName: '大臂上部前侧', path: 'misc/大臂上部前侧.glb', category: 'misc' },
        { displayName: '大臂上部后侧', path: 'misc/大臂上部后侧.glb', category: 'misc' },
        { displayName: '大臂下部外侧', path: 'misc/大臂下部外侧.glb', category: 'misc' },
        { displayName: '大臂下部里侧', path: 'misc/大臂下部里侧.glb', category: 'misc' },
        { displayName: '大臂根部前侧', path: 'misc/大臂根部前侧.glb', category: 'misc' },
        { displayName: '大臂根部后侧', path: 'misc/大臂根部后侧.glb', category: 'misc' },
    ],
    'left_elbow_pitch_link': [
        { displayName: '左肘结构件', path: 'frames/left_elbow_pitch_link.glb', category: 'frame' },
        { displayName: '左肘 A', path: 'frames/left_elbow_pitch_link_1.glb', category: 'frame' },
        { displayName: '左肘 B', path: 'frames/left_elbow_pitch_link_2.glb', category: 'frame' },
        { displayName: '左肘 C', path: 'frames/left_elbow_pitch_link_3.glb', category: 'frame' },
        { displayName: '肘部标定件', path: 'calibration/肘部标定件数量2.glb', category: 'calibration' },
    ],
    'left_elbow_yaw_link': [
        { displayName: '左前臂结构件', path: 'frames/left_elbow_yaw_link.glb', category: 'frame' },
        { displayName: '左前臂 A', path: 'frames/left_elbow_yaw_link_1.glb', category: 'frame' },
        { displayName: '左前臂 B', path: 'frames/left_elbow_yaw_link_2.glb', category: 'frame' },
        { displayName: '左前臂 C', path: 'frames/left_elbow_yaw_link_3.glb', category: 'frame' },
        { displayName: '小臂外侧', path: 'misc/小臂外侧.glb', category: 'misc' },
        { displayName: '小臂里侧', path: 'misc/小臂里侧.glb', category: 'misc' },
        { displayName: '手部球型', path: 'misc/手部球型.glb', category: 'misc' },
    ],

    // ======== 右臂 ========
    'right_arm_pitch_link': [
        { displayName: '右肩结构件', path: 'frames/right_arm_pitch_link.glb', category: 'frame' },
        { displayName: '右肩 A', path: 'frames/right_arm_pitch_link_1.glb', category: 'frame' },
        { displayName: '右肩 B', path: 'frames/right_arm_pitch_link_2.glb', category: 'frame' },
        { displayName: '右肩 C', path: 'frames/right_arm_pitch_link_3.glb', category: 'frame' },
    ],
    'right_arm_roll_link': [
        { displayName: '右肩 Roll 结构件', path: 'frames/right_arm_roll_link.glb', category: 'frame' },
        { displayName: '右肩 Roll A', path: 'frames/right_arm_roll_link_1.glb', category: 'frame' },
        { displayName: '右肩 Roll B', path: 'frames/right_arm_roll_link_2.glb', category: 'frame' },
        { displayName: '右肩 Roll C', path: 'frames/right_arm_roll_link_3.glb', category: 'frame' },
    ],
    'right_arm_yaw_link': [
        { displayName: '右上臂结构件', path: 'frames/right_arm_yaw_link.glb', category: 'frame' },
        { displayName: '右上臂 A', path: 'frames/right_arm_yaw_link_1.glb', category: 'frame' },
        { displayName: '右上臂 B', path: 'frames/right_arm_yaw_link_2.glb', category: 'frame' },
        { displayName: '右上臂 C', path: 'frames/right_arm_yaw_link_3.glb', category: 'frame' },
    ],
    'right_elbow_pitch_link': [
        { displayName: '右肘结构件', path: 'frames/right_elbow_pitch_link.glb', category: 'frame' },
        { displayName: '右肘 A', path: 'frames/right_elbow_pitch_link_1.glb', category: 'frame' },
        { displayName: '右肘 B', path: 'frames/right_elbow_pitch_link_2.glb', category: 'frame' },
        { displayName: '右肘 C', path: 'frames/right_elbow_pitch_link_3.glb', category: 'frame' },
    ],
    'right_elbow_yaw_link': [
        { displayName: '右前臂结构件', path: 'frames/right_elbow_yaw_link.glb', category: 'frame' },
        { displayName: '右前臂 A', path: 'frames/right_elbow_yaw_link_1.glb', category: 'frame' },
        { displayName: '右前臂 B', path: 'frames/right_elbow_yaw_link_2.glb', category: 'frame' },
        { displayName: '右前臂 C', path: 'frames/right_elbow_yaw_link_3.glb', category: 'frame' },
    ],

    // ======== 左腿 ========
    'left_thigh_yaw_link': [
        { displayName: '左大腿 Yaw 结构件', path: 'frames/left_thigh_yaw_link.glb', category: 'frame' },
        { displayName: '左大腿 Yaw A', path: 'frames/left_thigh_yaw_link_1.glb', category: 'frame' },
        { displayName: '左大腿 Yaw B', path: 'frames/left_thigh_yaw_link_2.glb', category: 'frame' },
        { displayName: '左大腿 Yaw C', path: 'frames/left_thigh_yaw_link_3.glb', category: 'frame' },
    ],
    'left_thigh_roll_link': [
        { displayName: '左大腿 Roll 结构件', path: 'frames/left_thigh_roll_link.glb', category: 'frame' },
        { displayName: '左大腿 Roll A', path: 'frames/left_thigh_roll_link_1.glb', category: 'frame' },
        { displayName: '左大腿 Roll B', path: 'frames/left_thigh_roll_link_2.glb', category: 'frame' },
        { displayName: '左大腿 Roll C', path: 'frames/left_thigh_roll_link_3.glb', category: 'frame' },
    ],
    'left_thigh_pitch_link': [
        { displayName: '左大腿 Pitch 结构件', path: 'frames/left_thigh_pitch_link.glb', category: 'frame' },
        { displayName: '左大腿 Pitch A', path: 'frames/left_thigh_pitch_link_1.glb', category: 'frame' },
        { displayName: '左大腿 Pitch B', path: 'frames/left_thigh_pitch_link_2.glb', category: 'frame' },
        { displayName: '左大腿 Pitch C', path: 'frames/left_thigh_pitch_link_3.glb', category: 'frame' },
        { displayName: '大腿后侧标定件', path: 'calibration/大腿后侧标定数量1.glb', category: 'calibration' },
    ],
    'left_knee_link': [
        { displayName: '左膝结构件', path: 'frames/left_knee_link.glb', category: 'frame' },
        { displayName: '左膝 A', path: 'frames/left_knee_link_1.glb', category: 'frame' },
        { displayName: '左膝 B', path: 'frames/left_knee_link_2.glb', category: 'frame' },
        { displayName: '左膝 C', path: 'frames/left_knee_link_3.glb', category: 'frame' },
        { displayName: '小腿轴承锁', path: 'bearings/小腿轴承锁.glb', category: 'bearing' },
        { displayName: '膝盖标定件', path: 'calibration/膝盖标定数量2.glb', category: 'calibration' },
    ],
    'left_ankle_pitch_link': [
        { displayName: '左踝 Pitch 结构件', path: 'frames/left_ankle_pitch_link.glb', category: 'frame' },
        { displayName: '左踝 Pitch A', path: 'frames/left_ankle_pitch_link_1.glb', category: 'frame' },
        { displayName: '左踝 Pitch B', path: 'frames/left_ankle_pitch_link_2.glb', category: 'frame' },
        { displayName: '左踝 Pitch C', path: 'frames/left_ankle_pitch_link_3.glb', category: 'frame' },
        { displayName: '脚踝标定件', path: 'calibration/脚踝标定数量2.glb', category: 'calibration' },
    ],
    'left_ankle_roll_link': [
        { displayName: '左踝 Roll 结构件', path: 'frames/left_ankle_roll_link.glb', category: 'frame' },
        { displayName: '左踝 Roll A', path: 'frames/left_ankle_roll_link_1.glb', category: 'frame' },
        { displayName: '左踝 Roll B', path: 'frames/left_ankle_roll_link_2.glb', category: 'frame' },
        { displayName: '左踝 Roll C', path: 'frames/left_ankle_roll_link_3.glb', category: 'frame' },
        { displayName: '20cm脚', path: 'frames/20cm脚.glb', category: 'frame' },
        { displayName: '脚部标定件', path: 'calibration/脚部标定件数量1.glb', category: 'calibration' },
    ],

    // ======== 右腿 ========
    'right_thigh_yaw_link': [
        { displayName: '右大腿 Yaw 结构件', path: 'frames/right_thigh_yaw_link.glb', category: 'frame' },
        { displayName: '右大腿 Yaw A', path: 'frames/right_thigh_yaw_link_1.glb', category: 'frame' },
        { displayName: '右大腿 Yaw B', path: 'frames/right_thigh_yaw_link_2.glb', category: 'frame' },
        { displayName: '右大腿 Yaw C', path: 'frames/right_thigh_yaw_link_3.glb', category: 'frame' },
    ],
    'right_thigh_roll_link': [
        { displayName: '右大腿 Roll 结构件', path: 'frames/right_thigh_roll_link.glb', category: 'frame' },
        { displayName: '右大腿 Roll A', path: 'frames/right_thigh_roll_link_1.glb', category: 'frame' },
        { displayName: '右大腿 Roll B', path: 'frames/right_thigh_roll_link_2.glb', category: 'frame' },
        { displayName: '右大腿 Roll C', path: 'frames/right_thigh_roll_link_3.glb', category: 'frame' },
    ],
    'right_thigh_pitch_link': [
        { displayName: '右大腿 Pitch 结构件', path: 'frames/right_thigh_pitch_link.glb', category: 'frame' },
        { displayName: '右大腿 Pitch A', path: 'frames/right_thigh_pitch_link_1.glb', category: 'frame' },
        { displayName: '右大腿 Pitch B', path: 'frames/right_thigh_pitch_link_2.glb', category: 'frame' },
        { displayName: '右大腿 Pitch C', path: 'frames/right_thigh_pitch_link_3.glb', category: 'frame' },
    ],
    'right_knee_link': [
        { displayName: '右膝结构件', path: 'frames/right_knee_link.glb', category: 'frame' },
        { displayName: '右膝 A', path: 'frames/right_knee_link_1.glb', category: 'frame' },
        { displayName: '右膝 B', path: 'frames/right_knee_link_2.glb', category: 'frame' },
        { displayName: '右膝 C', path: 'frames/right_knee_link_3.glb', category: 'frame' },
        { displayName: '小腿轴承锁', path: 'bearings/小腿轴承锁_2.glb', category: 'bearing' },
    ],
    'right_ankle_pitch_link': [
        { displayName: '右踝 Pitch 结构件', path: 'frames/right_ankle_pitch_link.glb', category: 'frame' },
        { displayName: '右踝 Pitch A', path: 'frames/right_ankle_pitch_link_1.glb', category: 'frame' },
        { displayName: '右踝 Pitch B', path: 'frames/right_ankle_pitch_link_2.glb', category: 'frame' },
        { displayName: '右踝 Pitch C', path: 'frames/right_ankle_pitch_link_3.glb', category: 'frame' },
    ],
    'right_ankle_roll_link': [
        { displayName: '右踝 Roll 结构件', path: 'frames/right_ankle_roll_link.glb', category: 'frame' },
        { displayName: '右踝 Roll A', path: 'frames/right_ankle_roll_link_1.glb', category: 'frame' },
        { displayName: '右踝 Roll B', path: 'frames/right_ankle_roll_link_2.glb', category: 'frame' },
        { displayName: '右踝 Roll C', path: 'frames/right_ankle_roll_link_3.glb', category: 'frame' },
        { displayName: '20cm脚', path: 'frames/20cm脚_3.glb', category: 'frame' },
    ],
};

/** 通用紧固件（不与特定 link 绑定，可全局展示） */
export const COMMON_FASTENERS: DetailPart[] = [
    // 螺丝
    { displayName: 'M3x6 螺钉', path: 'screws/内六角圆柱头螺钉M3x6.glb', category: 'screw' },
    { displayName: 'M3x8 螺钉', path: 'screws/内六角圆柱头螺钉M3x8.glb', category: 'screw' },
    { displayName: 'M3x10 螺钉', path: 'screws/内六角圆柱头螺钉M3x10.glb', category: 'screw' },
    { displayName: 'M3x12 螺钉', path: 'screws/内六角圆柱头螺钉M3x12.glb', category: 'screw' },
    { displayName: 'M3x16 螺钉', path: 'screws/内六角圆柱头螺钉M3x16.glb', category: 'screw' },
    { displayName: 'M4x8 螺钉', path: 'screws/内六角圆柱头螺钉M4x8.glb', category: 'screw' },
    { displayName: 'M4x10 螺钉', path: 'screws/内六角圆柱头螺钉M4x10.glb', category: 'screw' },
    { displayName: 'M4x12 螺钉', path: 'screws/内六角圆柱头螺钉M4x12.glb', category: 'screw' },
    { displayName: 'M4x16 螺钉', path: 'screws/内六角圆柱头螺钉M4x16.glb', category: 'screw' },
    { displayName: 'M5x10 螺钉', path: 'screws/内六角圆柱头螺钉M5x10.glb', category: 'screw' },
    { displayName: 'M6x20 螺钉', path: 'screws/内六角圆柱头螺钉M6x20.glb', category: 'screw' },
    // 螺母
    { displayName: 'M3 螺母', path: 'nuts/1型六角螺母M3.glb', category: 'nut' },
    { displayName: 'M4 螺母', path: 'nuts/1型六角螺母M4.glb', category: 'nut' },
    { displayName: 'M6 螺母', path: 'nuts/1型六角螺母M6.glb', category: 'nut' },
];

/** 零件分类颜色 */
export const CATEGORY_COLORS: Record<DetailPart['category'], string> = {
    frame: '#4fc3f7',
    screw: '#aaaaaa',
    nut: '#ffab40',
    bearing: '#69f0ae',
    calibration: '#ff6e40',
    electronics: '#7c4dff',
    misc: '#e0e0e0',
};

/** 零件分类中文名 */
export const CATEGORY_NAMES: Record<DetailPart['category'], string> = {
    frame: '结构件',
    screw: '螺丝',
    nut: '螺母',
    bearing: '轴承件',
    calibration: '标定件',
    electronics: '电子件',
    misc: '其他',
};

/**
 * 核心零件分类 — 直接在主 3D 视图中显示
 * 非核心零件通过独立小窗查看
 */
const CORE_CATEGORIES: Set<DetailPart['category']> = new Set([
    'electronics',
    'bearing',
    'calibration',
]);

/** 判断是否是核心零件分类 */
export function isCoreCategory(category: DetailPart['category']): boolean {
    return CORE_CATEGORIES.has(category);
}

/** 过滤出某 link 下的核心零件 */
export function getCorePartsForLink(linkName: string): DetailPart[] {
    const parts = DETAIL_PARTS_MAP[linkName];
    if (!parts) return [];
    return parts.filter((p) => isCoreCategory(p.category));
}

/** 过滤出某 link 下的非核心零件 */
export function getNonCorePartsForLink(linkName: string): DetailPart[] {
    const parts = DETAIL_PARTS_MAP[linkName];
    if (!parts) return [];
    return parts.filter((p) => !isCoreCategory(p.category));
}

// ============================================================
// 爆炸图子零件
// ============================================================

/** 过滤出某 link 下用于爆炸图展示的子零件
 *  - 结构件只取 _1 LOD 版本（避免多个 LOD 重叠）
 *  - base_link 的 frame 不展示（作为参考原点）
 */
export function getExplodePartsForLink(linkName: string): DetailPart[] {
    const parts = DETAIL_PARTS_MAP[linkName];
    if (!parts) return [];
    // 同口径精修：爆炸态优先展示结构件（frames），避免异构资产导致遮挡与空画面。
    const frameParts = parts.filter((p) => p.path.startsWith('frames/'));
    const candidateParts = frameParts.length > 0 ? frameParts : parts;
    return candidateParts.filter((p) => {
        // base_link 主壳体作为原点参照，不参与子件散开。
        if (linkName === 'base_link' && p.path === 'frames/base_link.glb') return false;
        return true;
    });
}

const PARTS_BASE = '/models/parts';

/** 预先计算所有爆炸图子零件的 URL（用于预加载） */
export const ALL_EXPLODE_PART_URLS: string[] = Object.keys(DETAIL_PARTS_MAP)
    .flatMap((link) => getExplodePartsForLink(link))
    .map((p) => `${PARTS_BASE}/${p.path}`);
