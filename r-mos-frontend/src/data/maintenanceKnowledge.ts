import { PART_METADATA, type PartInfo } from '@/components/Viewer3D/Atom01Interactive';
import { getLinkDisplayName } from '@/components/Viewer3D/assemblyTree';
import { CATEGORY_NAMES, DETAIL_PARTS_MAP, type DetailPart } from '@/components/Viewer3D/partsManifest';
import { type RobotDataManifest } from '@/components/Viewer3D/assemblyManifest';
import { getRobotModelBase } from '@/config/robots';
import {
    SCREWS,
    getPartScrews,
    getScrewById,
    getToolById,
    type Screw,
} from './toolData';

// ---- Manifest injection layer ----

let _manifestDisplayNames: Record<string, string> | null = null;
let _manifestTools: Array<{ tool_id: string; display_name: string; category: string }> | null = null;

/**
 * Inject manifest-derived knowledge so that lookup functions prefer manifest
 * data over hardcoded fallbacks. Call this whenever a RobotDataManifest loads.
 * Safe to call multiple times — each call replaces the previous cache.
 */
export function injectManifestKnowledge(manifest: RobotDataManifest): void {
    _manifestDisplayNames = manifest.display_names
        ? { ...manifest.display_names }
        : null;

    if (manifest.tools && manifest.tools.length > 0) {
        _manifestTools = manifest.tools.map((t) => ({
            tool_id: t.id,
            display_name: t.name,
            category: t.type,
        }));
    } else {
        _manifestTools = null;
    }
}

/**
 * Clear the manifest cache. After this call all lookup functions fall back
 * to hardcoded data again (useful for testing or robot context switches).
 */
export function clearManifestKnowledge(): void {
    _manifestDisplayNames = null;
    _manifestTools = null;
}

/**
 * Returns injected manifest tool entries, or null if no manifest has been
 * injected. Consumers can use this to resolve tool display names from the
 * manifest before falling back to toolData.ts.
 */
export function getManifestTools(): Array<{ tool_id: string; display_name: string; category: string }> | null {
    return _manifestTools;
}

type CoreGroup = PartInfo['group'];

export interface DetailPartSelection {
    linkName: string;
    partIndex: number;
}

export interface PartDetailRecord {
    id: string;
    level: 'core' | 'detail';
    displayName: string;
    categoryLabel: string;
    modelPath: string;
    parentDisplayName: string;
    maintenancePoints: string[];
    summary: string;
    jointName?: string;
}

export interface ScrewDetailRecord {
    screwId: string;
    spec: string;
    quantity: number;
    position: string;
    tool: string;
    torque: number | null;
}

export function getMaintenanceKnowledgeBase(robotId: string): string {
    return getRobotModelBase(robotId);
}

const GROUP_NAMES: Record<CoreGroup, string> = {
    base: '底座',
    torso: '躯干',
    left_arm: '左臂',
    right_arm: '右臂',
    left_leg: '左腿',
    right_leg: '右腿',
};

const GROUP_MAINTENANCE_HINTS: Record<CoreGroup, string[]> = {
    base: [
        '检查主承载面是否有裂纹或磕碰，确认地面接触稳定。',
        '复核电源板固定螺丝是否松动，确认线束无拉扯应力。',
        '复装后执行站立姿态校验，观察底座是否偏摆。',
    ],
    torso: [
        '检查胸腔夹板与主壳连接面，确认无形变与干涉。',
        '复核主控板/IMU 载板固定状态，线束避让无压线。',
        '开机后检查温升与姿态数据稳定性。',
    ],
    left_arm: [
        '检查肩部与肘部连接法兰，确认无轴向窜动。',
        '重点复核限位与编码器区域螺丝，防止回零漂移。',
        '复装后执行臂部全程运动，确认无异响卡滞。',
    ],
    right_arm: [
        '检查肩部与肘部连接法兰，确认无轴向窜动。',
        '重点复核限位与编码器区域螺丝，防止回零漂移。',
        '复装后执行臂部全程运动，确认无异响卡滞。',
    ],
    left_leg: [
        '检查髋-膝-踝连杆紧固状态，确认行走载荷链完整。',
        '复核踝部固定面和脚底接触面，避免偏载。',
        '复装后执行步态测试，观察支撑相稳定性。',
    ],
    right_leg: [
        '检查髋-膝-踝连杆紧固状态，确认行走载荷链完整。',
        '复核踝部固定面和脚底接触面，避免偏载。',
        '复装后执行步态测试，观察支撑相稳定性。',
    ],
};

const CATEGORY_MAINTENANCE_HINTS: Record<DetailPart['category'], string[]> = {
    frame: [
        '确认结构件贴合面无毛刺与变形。',
        '复装前清理配合面并做防松处理。',
        '装配后复核与相邻件的干涉间隙。',
    ],
    screw: [
        '确认螺纹完整且无滑牙。',
        '按对角顺序紧固，避免局部应力集中。',
        '按工艺扭矩复检一次并记录。',
    ],
    nut: [
        '确认螺母规格匹配且无滑丝。',
        '与螺钉配套更换时优先成套替换。',
        '复装后做防松标记并复检。',
    ],
    bearing: [
        '检查轴承座与轴向定位面是否磨损。',
        '确认转动顺畅、无卡滞和异常间隙。',
        '必要时补充润滑并复测回差。',
    ],
    calibration: [
        '拆装前记录标定件原始位置。',
        '复装后执行对应关节标定流程。',
        '保存标定结果并验证重复性。',
    ],
    electronics: [
        '确认板卡固定点和绝缘垫片状态正常。',
        '线束接口插拔到位并有防松处理。',
        '复装后执行上电自检与通信检查。',
    ],
    misc: [
        '确认安装孔位与配合面清洁完整。',
        '与相邻件复装时先做定位再紧固。',
        '完成后做外观与功能联检。',
    ],
};

const CORE_FALLBACK_SCREWS: Record<CoreGroup, Array<{ screwId: string; quantity: number; position: string }>> = {
    base: [
        { screwId: 'M4x10', quantity: 6, position: '底座主承载连接位' },
        { screwId: 'M3x8', quantity: 4, position: '载板固定点' },
    ],
    torso: [
        { screwId: 'M4x12', quantity: 6, position: '躯干框架连接位' },
        { screwId: 'M3x10', quantity: 6, position: '电子件安装位' },
    ],
    left_arm: [
        { screwId: 'M4x8', quantity: 4, position: '肩/肘法兰连接位' },
        { screwId: 'M3x8', quantity: 4, position: '限位与支架连接位' },
    ],
    right_arm: [
        { screwId: 'M4x8', quantity: 4, position: '肩/肘法兰连接位' },
        { screwId: 'M3x8', quantity: 4, position: '限位与支架连接位' },
    ],
    left_leg: [
        { screwId: 'M5x10', quantity: 4, position: '腿部载荷连接位' },
        { screwId: 'M4x10', quantity: 4, position: '踝部连接位' },
    ],
    right_leg: [
        { screwId: 'M5x10', quantity: 4, position: '腿部载荷连接位' },
        { screwId: 'M4x10', quantity: 4, position: '踝部连接位' },
    ],
};

const CATEGORY_FALLBACK_SCREWS: Record<DetailPart['category'], Array<{ screwId: string; quantity: number; position: string }>> = {
    frame: [{ screwId: 'M4x10', quantity: 4, position: '结构件安装孔位' }],
    screw: [{ screwId: 'M3x8', quantity: 1, position: '紧固件本体' }],
    nut: [{ screwId: 'M3x8', quantity: 1, position: '螺母配套孔位' }],
    bearing: [{ screwId: 'M4x8', quantity: 2, position: '轴承压板固定位' }],
    calibration: [{ screwId: 'M3x8', quantity: 2, position: '标定件定位孔位' }],
    electronics: [{ screwId: 'M3x6', quantity: 2, position: '电子件固定孔位' }],
    misc: [{ screwId: 'M3x8', quantity: 2, position: '通用安装孔位' }],
};

function normalizeSpec(text: string): string {
    return text.toLowerCase().replace(/×/g, 'x').replace(/\s+/g, '');
}

function findScrewBySpec(text: string): Screw | null {
    const match = text.match(/m\s*(\d+)\s*[x×]\s*(\d+)/i);
    if (!match) return null;
    const normalized = normalizeSpec(`M${match[1]}x${match[2]}`);
    return SCREWS.find((item) => normalizeSpec(item.spec) === normalized) ?? null;
}

function mapScrewRecord(
    screwId: string,
    quantity: number,
    position: string,
): ScrewDetailRecord {
    const screw = getScrewById(screwId);
    const tool = screw ? getToolById(screw.toolId) : undefined;
    return {
        screwId,
        spec: screw?.spec ?? screwId,
        quantity,
        position,
        tool: tool?.name ?? '通用工具',
        torque: screw?.torque ?? null,
    };
}

export function getDetailPartSelection(selection: DetailPartSelection): DetailPart | null {
    const parts = DETAIL_PARTS_MAP[selection.linkName];
    if (!parts) return null;
    return parts[selection.partIndex] ?? null;
}

export function getCorePartDetailRecord(partName: string, robotId?: string): PartDetailRecord | null {
    const part = PART_METADATA[partName];
    if (!part) return null;

    const robotModelBase = robotId ? getMaintenanceKnowledgeBase(robotId) : '';
    const detailCount = DETAIL_PARTS_MAP[partName]?.length ?? 0;

    // Prefer manifest display name when available
    const manifestDisplayName = _manifestDisplayNames?.[partName] ?? null;
    const displayName = manifestDisplayName ?? part.displayName;

    return {
        id: part.name,
        level: 'core',
        displayName,
        categoryLabel: '核心总成',
        modelPath: robotModelBase ? `${robotModelBase}/${part.name}.glb` : '',
        parentDisplayName: GROUP_NAMES[part.group],
        maintenancePoints: GROUP_MAINTENANCE_HINTS[part.group],
        summary: `该核心件隶属${GROUP_NAMES[part.group]}，下挂 ${detailCount} 个细节零件，维保时建议先核对紧固状态再执行动作校验。`,
        jointName: part.jointName,
    };
}

export function getDetailPartDetailRecord(selection: DetailPartSelection): PartDetailRecord | null {
    const part = getDetailPartSelection(selection);
    if (!part) return null;

    return {
        id: `detail:${selection.linkName}:${selection.partIndex}`,
        level: 'detail',
        displayName: part.displayName,
        categoryLabel: CATEGORY_NAMES[part.category],
        modelPath: `/models/parts/${part.path}`,
        parentDisplayName: getLinkDisplayName(selection.linkName),
        maintenancePoints: CATEGORY_MAINTENANCE_HINTS[part.category],
        summary: `该细节件归属 ${getLinkDisplayName(selection.linkName)}，类别为 ${CATEGORY_NAMES[part.category]}，拆装后需复核配合面与紧固状态。`,
    };
}

export function getCoreScrewRecords(partName: string): ScrewDetailRecord[] {
    const partScrews = getPartScrews(partName);
    if (partScrews && partScrews.screws.length > 0) {
        return partScrews.screws.map((item) => mapScrewRecord(item.screwId, item.quantity, item.position));
    }

    const part = PART_METADATA[partName];
    if (!part) return [];

    return CORE_FALLBACK_SCREWS[part.group].map((item) =>
        mapScrewRecord(item.screwId, item.quantity, item.position),
    );
}

export function getDetailScrewRecords(selection: DetailPartSelection): ScrewDetailRecord[] {
    const part = getDetailPartSelection(selection);
    if (!part) return [];

    if (part.category === 'screw') {
        const screw = findScrewBySpec(`${part.displayName} ${part.path}`);
        if (screw) {
            return [mapScrewRecord(screw.id, 1, `${part.displayName} 本体`)];
        }
    }

    if (part.category === 'nut') {
        const nutMatch = part.displayName.match(/M\s*(\d+)/i);
        if (nutMatch) {
            const matchedScrew = SCREWS.find((item) => item.spec.startsWith(`M${nutMatch[1]}×`));
            if (matchedScrew) {
                return [mapScrewRecord(matchedScrew.id, 1, `${part.displayName} 配套紧固位`)];
            }
        }
    }

    const parentScrews = getCoreScrewRecords(selection.linkName);
    if (parentScrews.length > 0) {
        return parentScrews.map((item) => ({
            ...item,
            quantity: Math.max(1, Math.ceil(item.quantity / 2)),
            position: `${part.displayName} / ${item.position}`,
        }));
    }

    return CATEGORY_FALLBACK_SCREWS[part.category].map((item) =>
        mapScrewRecord(item.screwId, item.quantity, `${part.displayName} / ${item.position}`),
    );
}
