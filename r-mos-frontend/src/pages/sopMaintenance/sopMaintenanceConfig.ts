/**
 * sopMaintenanceConfig.ts - SOP 维保页面常量/类型/纯函数
 *
 * 从 SOPMaintenancePage.tsx 抽离的最独立单元：相机 preset、分组常量、
 * 状态标签映射、工作台 chrome 配置、以及纯派生函数。
 */
import { SOPExecutionState } from '@/adjudication';
import type { CameraPreset } from '@/components/Viewer3D/assemblyTree';
import type { DetailPart } from '@/components/Viewer3D/partsManifest';

export const EXAM_DURATION_MS = 60 * 60 * 1000;
export const EXPLODE_DEFAULT_ON_ENTER = 0.4;
export const COLLAPSED_EPSILON = 0.0001;

export const ISOLATION_FOCUS_PRESET: CameraPreset = {
    position: [0.9, 0, 0.4],
    target: [0, 0, 0],
    fov: 45,
};
export const ISOLATION_TORSO_PRESET: CameraPreset = {
    position: [2.2, 0.6, 1.8],
    target: [0, 0.3, 0.4],
    fov: 48,
};
export const ISOLATION_UPPER_LIMB_PRESET: CameraPreset = {
    position: [1.45, 0, 0.9],
    target: [0, 0, 0.2],
    fov: 46,
};
export const ISOLATION_LOWER_LIMB_PRESET: CameraPreset = {
    position: [1.15, 0, 0.65],
    target: [0, 0, 0.05],
    fov: 45,
};
export const ISOLATION_MODEL_SCALE_OVERRIDES: Partial<Record<string, number>> = {
    base_link: 1.1,
    torso_link: 1.05,
    left_arm_pitch_link: 1.25,
    left_arm_roll_link: 1.25,
    left_arm_yaw_link: 1.25,
    left_elbow_pitch_link: 1.25,
    left_elbow_yaw_link: 1.25,
    right_arm_pitch_link: 1.25,
    right_arm_roll_link: 1.25,
    right_arm_yaw_link: 1.25,
    right_elbow_pitch_link: 1.25,
    right_elbow_yaw_link: 1.25,
    left_thigh_yaw_link: 1.2,
    left_thigh_roll_link: 1.2,
    left_thigh_pitch_link: 1.2,
    left_knee_link: 1.2,
    left_ankle_pitch_link: 1.2,
    left_ankle_roll_link: 1.2,
    right_thigh_yaw_link: 1.2,
    right_thigh_roll_link: 1.2,
    right_thigh_pitch_link: 1.2,
    right_knee_link: 1.2,
    right_ankle_pitch_link: 1.2,
    right_ankle_roll_link: 1.2,
};

// ============================================================
// Gate-1: 视图状态类型
// ============================================================
export type ViewState = 'OVERVIEW' | 'ISOLATED';

export interface BreadcrumbItem {
    nodeId: string | null; // null = 总览
    displayName: string;
}

/**
 * @deprecated 已被 manifest assembly_groups.display_name 替代。
 * 当 manifest 不可用时作为 fallback。
 */
export const GROUP_NAMES: Record<string, string> = {
    'base': '底座',
    'torso': '躯干',
    'left_arm': '左臂',
    'right_arm': '右臂',
    'left_leg': '左腿',
    'right_leg': '右腿',
};

export const SOP_EXECUTION_STATE_TAG_COLOR: Partial<Record<SOPExecutionState, string>> = {
    [SOPExecutionState.IDLE]: 'blue',
    [SOPExecutionState.PRECONDITION_CHECK]: 'gold',
    [SOPExecutionState.EXECUTING]: 'green',
    [SOPExecutionState.VALIDATION]: 'purple',
    [SOPExecutionState.COMPLETE]: 'cyan',
    [SOPExecutionState.FAILED]: 'red',
    [SOPExecutionState.BLOCKED]: 'red',
};

export const SOP_EXECUTION_STATE_LABEL: Partial<Record<SOPExecutionState, string>> = {
    [SOPExecutionState.IDLE]: '就绪',
    [SOPExecutionState.PRECONDITION_CHECK]: '前置检查',
    [SOPExecutionState.EXECUTING]: '执行中',
    [SOPExecutionState.VALIDATION]: '验证中',
    [SOPExecutionState.COMPLETE]: '已完成',
    [SOPExecutionState.FAILED]: '失败',
    [SOPExecutionState.BLOCKED]: '已阻断',
};

/**
 * @deprecated 已被 manifest assembly_groups.child_links 替代。
 * 当 manifest 不可用时作为 fallback。
 */
export const UPPER_BODY_CORE_LINKS = [
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
] as const;

/**
 * @deprecated 已被 manifest assembly_groups.child_links 替代。
 * 当 manifest 不可用时作为 fallback。
 */
export const REMAINING_CORE_LINKS = [
    'base_link',
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

/**
 * 从 manifest 装配组派生上身/下身分组。
 *
 * 分类策略（无需硬编码 key 列表）：
 * - 按 assembly_groups 顺序将所有组分为两半：前半为上身，后半为下身。
 * - 适用于任意机器人型号，只要 manifest 遵循"上肢在前、下肢在后"的排列惯例。
 */
export function buildLinkGroupsFromManifest(
  manifest: { overview_config?: { assembly_groups?: Record<string, { display_name: string; child_links: string[]; explode_dir: number[] }> } } | null
): {
  upperLinks: readonly string[];
  lowerLinks: readonly string[];
  groupNames: Record<string, string>;
} | null {
  const groups = (manifest as any)?.overview_config?.assembly_groups
  if (!groups) return null

  const entries = Object.entries(groups) as [string, { display_name: string; child_links: string[] }][]
  const half = Math.ceil(entries.length / 2)

  const upperLinks: string[] = []
  const lowerLinks: string[] = []
  const groupNames: Record<string, string> = {}

  entries.forEach(([key, group], idx) => {
    groupNames[key] = group.display_name
    if (idx < half) {
      upperLinks.push(...group.child_links)
    } else {
      lowerLinks.push(...group.child_links)
    }
  })

  return { upperLinks, lowerLinks, groupNames }
}

export type WorkspaceVariant = 'runtime' | 'demo';
export type MaintenanceLayoutMode = 'execution' | 'inspector' | 'full';

export interface WorkspaceChrome {
    title: string;
    breadcrumb: string[];
    showDraftEntry: boolean;
}

export const WORKSPACE_CHROME: Record<WorkspaceVariant, WorkspaceChrome> = {
    runtime: {
        title: 'SOP 维保系统',
        breadcrumb: ['维保端', 'SOP 工作台'],
        showDraftEntry: true,
    },
    demo: {
        title: '维保工作台',
        breadcrumb: ['工作台', '维保工作台'],
        showDraftEntry: false,
    },
};

export function resolveScrewSpecIdFromDetailPart(part: DetailPart): string | null {
    const source = `${part.displayName} ${part.path}`;
    const matched = source.match(/M\s*(\d+)\s*[x×]\s*(\d+)/i);
    if (!matched) return null;
    return `M${matched[1]}x${matched[2]}`;
}
