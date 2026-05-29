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
import { PART_SCREWS } from '../../data/toolData';
import overviewNodes from './overview_nodes.json';
import type { RobotDataManifest } from './assemblyManifest';
import { buildCoreLinkList, buildDetailPartsMap, buildDisplayNameMap } from './manifestHelpers';

export type DetailPartCategory =
    | 'frame'
    | 'screw'
    | 'nut'
    | 'bearing'
    | 'calibration'
    | 'electronics'
    | 'misc';

export interface DetailPart {
    /** 子零件显示名 */
    displayName: string;
    /** GLB 路径（相对于 /models/parts/） */
    path: string;
    /** 零件分类 */
    category: DetailPartCategory;
    /** 可选：用于 SOP 动作裁决的目标 ID */
    actionTarget?: string;
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
 * @deprecated Use getCoreLinks() instead.
 */
const CORE_LINKS = [
    'base_link',
    'torso_link',
    'left_arm_pitch_link',
    'left_arm_roll_link',
    'left_arm_yaw_link',
    'left_elbow_pitch_link',
    'left_elbow_yaw_link',
    'right_arm_pitch_link',
    'right_arm_roll_link',
    'right_arm_yaw_link',
    'right_elbow_pitch_link',
    'right_elbow_yaw_link',
    'left_thigh_yaw_link',
    'left_thigh_roll_link',
    'left_thigh_pitch_link',
    'left_knee_link',
    'left_ankle_pitch_link',
    'left_ankle_roll_link',
    'right_thigh_yaw_link',
    'right_thigh_roll_link',
    'right_thigh_pitch_link',
    'right_knee_link',
    'right_ankle_pitch_link',
    'right_ankle_roll_link',
] as const;

type CoreLinkName = typeof CORE_LINKS[number];

/**
 * @deprecated Use getDisplayNames() instead.
 */
const CORE_LINK_DISPLAY_NAMES: Record<CoreLinkName, string> = {
    base_link: '底座',
    torso_link: '躯干',
    left_arm_pitch_link: '左肩俯仰关节',
    left_arm_roll_link: '左肩横滚关节',
    left_arm_yaw_link: '左上臂',
    left_elbow_pitch_link: '左肘俯仰关节',
    left_elbow_yaw_link: '左前臂',
    right_arm_pitch_link: '右肩俯仰关节',
    right_arm_roll_link: '右肩横滚关节',
    right_arm_yaw_link: '右上臂',
    right_elbow_pitch_link: '右肘俯仰关节',
    right_elbow_yaw_link: '右前臂',
    left_thigh_yaw_link: '左髋偏航关节',
    left_thigh_roll_link: '左髋横滚关节',
    left_thigh_pitch_link: '左髋俯仰关节',
    left_knee_link: '左膝关节',
    left_ankle_pitch_link: '左踝俯仰关节',
    left_ankle_roll_link: '左踝横滚关节',
    right_thigh_yaw_link: '右髋偏航关节',
    right_thigh_roll_link: '右髋横滚关节',
    right_thigh_pitch_link: '右髋俯仰关节',
    right_knee_link: '右膝关节',
    right_ankle_pitch_link: '右踝俯仰关节',
    right_ankle_roll_link: '右踝横滚关节',
};

const FRAME_SUFFIXES = ['', '_1', '_2', '_3'] as const;
const FRAME_SLOT_NAMES = ['主体框架', '前盖板', '后盖板', '侧向支撑'] as const;

const SCREW_MODEL_PATH_BY_ID: Record<string, string> = {
    M3x6: 'screws/内六角圆柱头螺钉M3x6.glb',
    M3x8: 'screws/内六角圆柱头螺钉M3x8.glb',
    M3x10: 'screws/内六角圆柱头螺钉M3x10.glb',
    M3x12: 'screws/内六角圆柱头螺钉M3x12.glb',
    M3x16: 'screws/内六角圆柱头螺钉M3x16.glb',
    M4x8: 'screws/内六角圆柱头螺钉M4x8.glb',
    M4x10: 'screws/内六角圆柱头螺钉M4x10.glb',
    M4x12: 'screws/内六角圆柱头螺钉M4x12.glb',
    M4x16: 'screws/内六角圆柱头螺钉M4x16.glb',
    M5x10: 'screws/内六角圆柱头螺钉M5x10.glb',
    M6x15: 'screws/内六角圆柱头螺钉M6x20.glb',
    M6x20: 'screws/内六角圆柱头螺钉M6x20.glb',
};

/**
 * @deprecated Data has been migrated to assembly_manifest.json detail_parts field.
 * Use manifest-injected detail parts via injectManifestViewerData() instead.
 * Kept as fallback for environments without manifest.
 */
const EXTRA_LINK_PARTS: Partial<Record<CoreLinkName, DetailPart[]>> = {
    base_link: [
        { displayName: '髋关节固定座', path: 'frames/髋关节固定.glb', category: 'frame' },
        { displayName: '髋夹板', path: 'frames/髋夹板.glb', category: 'frame' },
        { displayName: '腰部支撑件', path: 'frames/腰部支撑.glb', category: 'frame' },
        { displayName: '电池底盖', path: 'frames/电池底盖.glb', category: 'frame' },
        { displayName: '腰部标定件', path: 'calibration/腰部标定件数量1.glb', category: 'calibration' },
    ],
    torso_link: [
        { displayName: '胸腔前后夹板', path: 'frames/胸腔前后夹板.glb', category: 'frame', actionTarget: 'frame_torso_chest' },
        { displayName: '胸腔后夹板', path: 'frames/胸腔夹板后.glb', category: 'frame' },
        { displayName: '胸腔前盖', path: 'frames/胸腔胸部.glb', category: 'frame' },
        { displayName: '胸腔下盖', path: 'frames/胸腔腹部.glb', category: 'frame' },
        { displayName: '胸腔后背下盖', path: 'frames/胸腔后背下部.glb', category: 'frame' },
        { displayName: '腰部下盖', path: 'frames/腰部下册.glb', category: 'frame' },
        { displayName: '侧板横板', path: 'misc/侧板横板.glb', category: 'misc' },
        { displayName: '躯干电机', path: 'misc/LB22SA2M1_M10.glb', category: 'electronics', actionTarget: 'torso_motor' },
        { displayName: '主控板', path: 'misc/OPI_5PLUS_PCBA.glb', category: 'electronics', actionTarget: 'torso_pcb_main' },
        { displayName: 'PCB 载板', path: 'misc/PCB载板.glb', category: 'electronics' },
        { displayName: 'IMU 载板', path: 'misc/IMU载板.glb', category: 'electronics' },
        { displayName: '扩展板', path: 'misc/3D_PCB7_2025_07_10.glb', category: 'electronics' },
        { displayName: '提手', path: 'misc/把手.glb', category: 'misc' },
        { displayName: '电池仓', path: 'misc/电池盒粗略尺寸.glb', category: 'misc' },
    ],
    left_arm_pitch_link: [
        { displayName: '肩部壳体', path: 'frames/肩膀.glb', category: 'frame' },
        { displayName: '肩部固定件', path: 'frames/肩部固定件数量2.glb', category: 'frame' },
        { displayName: '限位销', path: 'misc/限位销.glb', category: 'misc' },
    ],
    left_arm_roll_link: [
        { displayName: '肩部壳体（副）', path: 'frames/肩膀_1.glb', category: 'frame' },
        { displayName: '肩部固定件（副）', path: 'frames/肩部固定件数量2_1.glb', category: 'frame' },
        { displayName: '输出法兰连杆', path: 'frames/输出法兰连杆.glb', category: 'frame' },
        { displayName: '限位销（副）', path: 'misc/限位销_1.glb', category: 'misc' },
    ],
    left_arm_yaw_link: [
        { displayName: '大臂上部前壳', path: 'misc/大臂上部前侧.glb', category: 'misc' },
        { displayName: '大臂上部后壳', path: 'misc/大臂上部后侧.glb', category: 'misc' },
        { displayName: '大臂下部外壳', path: 'misc/大臂下部外侧.glb', category: 'misc' },
        { displayName: '大臂下部内壳', path: 'misc/大臂下部里侧.glb', category: 'misc' },
        { displayName: '大臂根部前壳', path: 'misc/大臂根部前侧.glb', category: 'misc' },
        { displayName: '大臂根部后壳', path: 'misc/大臂根部后侧.glb', category: 'misc' },
    ],
    left_elbow_pitch_link: [
        { displayName: '通用连接件', path: 'frames/通用连接件.glb', category: 'frame' },
        { displayName: '扩孔法兰', path: 'frames/通用连接件扩孔法兰.glb', category: 'frame' },
        { displayName: '肘部标定件', path: 'calibration/肘部标定件数量2.glb', category: 'calibration' },
    ],
    left_elbow_yaw_link: [
        { displayName: '小臂外壳', path: 'misc/小臂外侧.glb', category: 'misc' },
        { displayName: '小臂内壳', path: 'misc/小臂里侧.glb', category: 'misc' },
        { displayName: '手部球形件', path: 'misc/手部球型.glb', category: 'misc' },
        { displayName: '输出法兰连杆（副）', path: 'frames/输出法兰连杆_1.glb', category: 'frame' },
    ],
    right_arm_pitch_link: [
        { displayName: '肩部壳体', path: 'frames/肩膀_2.glb', category: 'frame' },
        { displayName: '肩部固定件', path: 'frames/肩部固定件数量2_2.glb', category: 'frame' },
        { displayName: '限位销', path: 'misc/限位销_2.glb', category: 'misc' },
    ],
    right_arm_roll_link: [
        { displayName: '肩部壳体（副）', path: 'frames/肩膀_3.glb', category: 'frame' },
        { displayName: '肩部固定件（副）', path: 'frames/肩部固定件数量2_3.glb', category: 'frame' },
        { displayName: '输出法兰连杆', path: 'frames/输出法兰连杆_2.glb', category: 'frame' },
        { displayName: '限位销（副）', path: 'misc/限位销_3.glb', category: 'misc' },
    ],
    right_arm_yaw_link: [
        { displayName: '大臂上部前壳', path: 'misc/大臂上部前侧_1.glb', category: 'misc' },
        { displayName: '大臂上部后壳', path: 'misc/大臂上部后侧_1.glb', category: 'misc' },
        { displayName: '大臂下部外壳', path: 'misc/大臂下部外侧_1.glb', category: 'misc' },
        { displayName: '大臂下部内壳', path: 'misc/大臂下部里侧_1.glb', category: 'misc' },
        { displayName: '大臂根部前壳', path: 'misc/大臂根部前侧_1.glb', category: 'misc' },
        { displayName: '大臂根部后壳', path: 'misc/大臂根部后侧_1.glb', category: 'misc' },
    ],
    right_elbow_pitch_link: [
        { displayName: '通用连接件', path: 'frames/通用连接件_1.glb', category: 'frame' },
        { displayName: '扩孔法兰', path: 'frames/通用连接件扩孔法兰_1.glb', category: 'frame' },
        { displayName: '肘部标定件', path: 'calibration/肘部标定件数量2_1.glb', category: 'calibration' },
    ],
    right_elbow_yaw_link: [
        { displayName: '小臂外壳', path: 'misc/小臂外侧_1.glb', category: 'misc' },
        { displayName: '小臂内壳', path: 'misc/小臂里侧_1.glb', category: 'misc' },
        { displayName: '手部球形件', path: 'misc/手部球型_1.glb', category: 'misc' },
        { displayName: '输出法兰连杆（副）', path: 'frames/输出法兰连杆_3.glb', category: 'frame' },
    ],
    left_thigh_yaw_link: [
        { displayName: '髋夹板', path: 'frames/髋夹板_1.glb', category: 'frame' },
        { displayName: '髋关节固定座', path: 'frames/髋关节固定_1.glb', category: 'frame' },
        { displayName: '大腿根部开孔结构', path: 'frames/大腿根部结构开孔.glb', category: 'frame' },
    ],
    left_thigh_roll_link: [
        { displayName: '大腿内侧板', path: 'frames/大腿内侧.glb', category: 'frame' },
        { displayName: '长连杆', path: 'frames/长连杆.glb', category: 'frame' },
        { displayName: '短连杆', path: 'frames/短连杆.glb', category: 'frame' },
    ],
    left_thigh_pitch_link: [
        { displayName: '大腿内侧板（副）', path: 'frames/大腿内侧_1.glb', category: 'frame' },
        { displayName: '大腿定位块', path: 'frames/大腿定位块数量2.glb', category: 'calibration' },
        { displayName: '大腿后侧标定件', path: 'calibration/大腿后侧标定数量1.glb', category: 'calibration' },
        { displayName: '长连杆（副）', path: 'frames/长连杆_1.glb', category: 'frame' },
    ],
    left_knee_link: [
        { displayName: '小腿结构件', path: 'frames/小腿.glb', category: 'frame' },
        { displayName: '小腿轴承锁', path: 'bearings/小腿轴承锁.glb', category: 'bearing' },
        { displayName: '膝盖标定件', path: 'calibration/膝盖标定数量2.glb', category: 'calibration' },
        { displayName: '短连杆（副）', path: 'frames/短连杆_1.glb', category: 'frame' },
    ],
    left_ankle_pitch_link: [
        { displayName: '脚踝横滚连接件', path: 'frames/脚踝横滚连接件.glb', category: 'frame' },
        { displayName: '扩孔法兰', path: 'frames/通用连接件扩孔法兰_2.glb', category: 'frame' },
        { displayName: '脚踝标定件', path: 'calibration/脚踝标定数量2.glb', category: 'calibration' },
    ],
    left_ankle_roll_link: [
        { displayName: '脚底板', path: 'frames/脚底板.glb', category: 'frame' },
        { displayName: '脚底连杆', path: 'frames/脚底连杆.glb', category: 'frame' },
        { displayName: '脚掌结构件', path: 'frames/20cm脚.glb', category: 'frame' },
        { displayName: '脚底软胶', path: 'frames/软胶_脚底_左.glb', category: 'frame', actionTarget: 'left_foot_rubber' },
        { displayName: '脚部标定件', path: 'calibration/脚部标定件数量1.glb', category: 'calibration' },
    ],
    right_thigh_yaw_link: [
        { displayName: '髋夹板', path: 'frames/髋夹板_2.glb', category: 'frame' },
        { displayName: '髋关节固定座', path: 'frames/髋关节固定_2.glb', category: 'frame' },
        { displayName: '大腿根部开孔结构', path: 'frames/大腿根部结构开孔_1.glb', category: 'frame' },
    ],
    right_thigh_roll_link: [
        { displayName: '大腿内侧板', path: 'frames/大腿内侧_2.glb', category: 'frame' },
        { displayName: '长连杆', path: 'frames/长连杆_2.glb', category: 'frame' },
        { displayName: '短连杆', path: 'frames/短连杆_2.glb', category: 'frame' },
    ],
    right_thigh_pitch_link: [
        { displayName: '大腿内侧板（副）', path: 'frames/大腿内侧_3.glb', category: 'frame' },
        { displayName: '大腿定位块', path: 'frames/大腿定位块数量2_1.glb', category: 'calibration' },
        { displayName: '大腿后侧标定件', path: 'calibration/大腿后侧标定数量1_1.glb', category: 'calibration' },
        { displayName: '长连杆（副）', path: 'frames/长连杆_3.glb', category: 'frame' },
    ],
    right_knee_link: [
        { displayName: '小腿结构件', path: 'frames/小腿_1.glb', category: 'frame' },
        { displayName: '小腿轴承锁', path: 'bearings/小腿轴承锁_2.glb', category: 'bearing' },
        { displayName: '膝盖标定件', path: 'calibration/膝盖标定数量2_1.glb', category: 'calibration' },
        { displayName: '短连杆（副）', path: 'frames/短连杆_3.glb', category: 'frame' },
    ],
    right_ankle_pitch_link: [
        { displayName: '脚踝横滚连接件', path: 'frames/脚踝横滚连接件_1.glb', category: 'frame' },
        { displayName: '扩孔法兰', path: 'frames/通用连接件扩孔法兰_3.glb', category: 'frame' },
        { displayName: '脚踝标定件', path: 'calibration/脚踝标定数量2_1.glb', category: 'calibration' },
    ],
    right_ankle_roll_link: [
        { displayName: '脚底板', path: 'frames/脚底板_1.glb', category: 'frame' },
        { displayName: '脚底连杆', path: 'frames/脚底连杆_1.glb', category: 'frame' },
        { displayName: '脚掌结构件', path: 'frames/20cm脚_3.glb', category: 'frame' },
        { displayName: '脚底软胶', path: 'frames/橡胶脚底.glb', category: 'frame', actionTarget: 'right_foot_rubber' },
        { displayName: '脚部标定件', path: 'calibration/脚部标定件数量1_1.glb', category: 'calibration' },
    ],
};

function buildFrameParts(link: CoreLinkName): DetailPart[] {
    const displayNames = getDisplayNames();
    const baseName = displayNames[link] ?? CORE_LINK_DISPLAY_NAMES[link] ?? link;
    return FRAME_SUFFIXES.map((suffix, idx) => ({
        displayName: `${baseName}${FRAME_SLOT_NAMES[idx]}`,
        path: `frames/${link}${suffix}.glb`,
        category: 'frame' as const,
    }));
}

function buildScrewParts(link: CoreLinkName): DetailPart[] {
    const screwConfig = PART_SCREWS.find((item) => item.partName === link);
    if (!screwConfig) return [];

    return screwConfig.screws.reduce<DetailPart[]>((acc, item, idx) => {
            const path = SCREW_MODEL_PATH_BY_ID[item.screwId];
            if (!path) return acc;
            acc.push({
                displayName: `${item.position}（${item.screwId}）`,
                path,
                category: 'screw' as const,
                actionTarget: `${item.screwId}_${idx + 1}`,
            });
            return acc;
        }, []);
}

function dedupeParts(parts: DetailPart[]): DetailPart[] {
    const seen = new Set<string>();
    return parts.filter((part) => {
        const key = `${part.path}::${part.category}::${part.actionTarget ?? ''}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
    });
}

function buildLinkDetailParts(link: CoreLinkName): DetailPart[] {
    // Prefer manifest-injected detail_parts over hardcoded EXTRA_LINK_PARTS
    const extraParts = (_manifestDetailParts?.[link] ?? EXTRA_LINK_PARTS[link]) ?? [];
    return dedupeParts([
        ...buildFrameParts(link),
        ...extraParts,
        ...buildScrewParts(link),
    ]);
}

// ---- Manifest injection layer ----

let _manifestCoreLinks: string[] | null = null;
let _manifestDisplayNames: Record<string, string> | null = null;
let _manifestDetailParts: Record<string, DetailPart[]> | null = null;

/** 从 manifest 注入核心链接列表、显示名和细节子零件 */
export function injectManifestViewerData(manifest: RobotDataManifest): void {
    _manifestCoreLinks = buildCoreLinkList(manifest);
    _manifestDisplayNames = buildDisplayNameMap(manifest);
    _manifestDetailParts = buildDetailPartsMap(manifest) as Record<string, DetailPart[]> | null;
}

/** 清除注入数据 */
export function clearManifestViewerData(): void {
    _manifestCoreLinks = null;
    _manifestDisplayNames = null;
    _manifestDetailParts = null;
}

/** 获取核心链接列表（优先 manifest，fallback 硬编码） */
export function getCoreLinks(): readonly string[] {
    return _manifestCoreLinks ?? CORE_LINKS;
}

/** 获取显示名映射（优先 manifest，fallback 硬编码） */
export function getDisplayNames(): Record<string, string> {
    return _manifestDisplayNames ?? CORE_LINK_DISPLAY_NAMES;
}

/** 获取每个核心 link 对应的细节子零件列表（懒计算，优先 manifest）。
 *  替代顶层常量 DETAIL_PARTS_MAP，确保 manifest 注入后能拿到最新数据。
 */
export function getDetailPartsMap(): Record<string, DetailPart[]> {
    return getCoreLinks().reduce((acc, link) => {
        acc[link] = buildLinkDetailParts(link as CoreLinkName);
        return acc;
    }, {} as Record<string, DetailPart[]>);
}

/**
 * 每个核心 link 对应的细节子零件列表。
 * 数据来源：
 *  - link 主模型（frames/{link}.glb 系列）
 *  - 机械目录中的盖板/连杆/标定件/电子件
 *  - 工具库定义的螺丝规格映射
 * @deprecated Use getDetailPartsMap() for manifest-aware lazy computation.
 */
export const DETAIL_PARTS_MAP: Record<string, DetailPart[]> = getCoreLinks().reduce((acc, link) => {
    acc[link] = buildLinkDetailParts(link as CoreLinkName);
    return acc;
}, {} as Record<string, DetailPart[]>);

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
export const CATEGORY_COLORS: Record<DetailPartCategory, string> = {
    frame: '#4fc3f7',
    screw: '#aaaaaa',
    nut: '#ffab40',
    bearing: '#69f0ae',
    calibration: '#ff6e40',
    electronics: '#7c4dff',
    misc: '#e0e0e0',
};

/** 零件分类中文名 */
export const CATEGORY_NAMES: Record<DetailPartCategory, string> = {
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
    const parts = getDetailPartsMap()[linkName];
    if (!parts) return [];
    return parts.filter((p) => isCoreCategory(p.category));
}

/** 过滤出某 link 下的非核心零件 */
export function getNonCorePartsForLink(linkName: string): DetailPart[] {
    const parts = getDetailPartsMap()[linkName];
    if (!parts) return [];
    return parts.filter((p) => !isCoreCategory(p.category));
}

// ============================================================
// 爆炸图子零件
// ============================================================

interface ExplodeOptions {
    includeSecondary?: boolean;
}

/** 过滤出某 link 下用于爆炸图展示的子零件
 *  - 默认仅展示 frames（更轻量）
 *  - L2 模式可开启 includeSecondary 展示盖板/螺丝/电子件
 *  - base_link 主壳体不参与散开（作为参考原点）
 */
export function getExplodePartsForLink(linkName: string, options: ExplodeOptions = {}): DetailPart[] {
    const includeSecondary = options.includeSecondary ?? false;
    const parts = getDetailPartsMap()[linkName];
    if (!parts) return [];

    const filtered = parts.filter((part) => !(linkName === 'base_link' && part.path === 'frames/base_link.glb'));
    if (includeSecondary) {
        return filtered;
    }

    const frameOnly = filtered.filter((part) => part.path.startsWith('frames/'));
    return frameOnly.length > 0 ? frameOnly : filtered;
}

const PARTS_BASE = '/models/parts';

/**
 * 预先计算所有爆炸图子零件的 URL（用于预加载）。
 * @deprecated Use getAllExplodePartUrls() for manifest-aware computation.
 */
export const ALL_EXPLODE_PART_URLS: string[] = Array.from(new Set(
    Object.keys(DETAIL_PARTS_MAP)
        .flatMap((link) => getExplodePartsForLink(link))
        .map((part) => `${PARTS_BASE}/${part.path}`),
));

/** 获取所有爆炸图子零件的 URL（manifest 驱动，用于预加载） */
export function getAllExplodePartUrls(): string[] {
    return Array.from(new Set(
        Object.keys(getDetailPartsMap())
            .flatMap((link) => getExplodePartsForLink(link))
            .map((part) => `${PARTS_BASE}/${part.path}`),
    ));
}

/** 获取细节件对应的动作目标（若有） */
export function getDetailPartActionTarget(linkName: string, partIndex: number): string | null {
    const detailPart = getDetailPartsMap()[linkName]?.[partIndex];
    if (!detailPart) return null;
    return detailPart.actionTarget ?? null;
}
