/**
 * @description 零件注册表 - 管理所有零件数据（manifest 驱动）
 * @module adjudication/data/partRegistry
 */

import { Part, PartCategory } from '../types/adjudication';
import type { RobotDataManifest } from '@/components/Viewer3D/assemblyManifest';
import { manifestPartToPart, manifestScrewToPart } from './manifestAdapter';

// ---- Manifest injection layer ----
let _manifestPartRegistry: Record<string, Part> | null = null;
let _manifestScrewRegistry: Record<string, Part> | null = null;
let _manifestPartScrews: Record<string, string[]> | null = null;

/** 从 manifest 注入零件数据（替代硬编码） */
export function injectManifestPartRegistry(manifest: RobotDataManifest): void {
    const modelBase = `/api/v1/robots/${manifest.robotId}/assets`;
    _manifestPartRegistry = {};
    _manifestScrewRegistry = {};
    _manifestPartScrews = {};

    for (const entry of manifest.parts_registry ?? []) {
        _manifestPartRegistry[entry.id] = manifestPartToPart(entry, modelBase);
    }
    for (const entry of manifest.screw_instances ?? []) {
        _manifestScrewRegistry[entry.id] = manifestScrewToPart(entry, modelBase);
        // Build part→screw mapping
        if (!_manifestPartScrews[entry.parent_id]) {
            _manifestPartScrews[entry.parent_id] = [];
        }
        _manifestPartScrews[entry.parent_id].push(entry.id);
    }
}

/** 清除注入的 manifest 数据 */
export function clearManifestPartRegistry(): void {
    _manifestPartRegistry = null;
    _manifestScrewRegistry = null;
    _manifestPartScrews = null;
}

/**
 * @deprecated Empty registry kept for backward compatibility of re-exports.
 */
export const PART_REGISTRY: Record<string, Part> = {};

// ============================================================
// 辅助函数
// ============================================================

/**
 * 根据 ID 获取零件信息
 */
export function getPartById(id: string): Part | undefined {
    return _manifestPartRegistry?.[id] ?? _manifestScrewRegistry?.[id];
}

/**
 * 获取零件的螺丝列表
 */
export function getPartScrews(partId: string): string[] {
    return _manifestPartScrews?.[partId] ?? [];
}

/**
 * 获取指定类型的所有零件
 */
export function getPartsByCategory(category: PartCategory): Part[] {
    if (!_manifestPartRegistry) return [];
    const allParts = { ..._manifestPartRegistry, ..._manifestScrewRegistry };
    return Object.values(allParts).filter(p => p.category === category);
}

/**
 * 获取所有零件 ID 列表
 */
export function getAllPartIds(): string[] {
    if (!_manifestPartRegistry) return [];
    return Object.keys({ ..._manifestPartRegistry, ..._manifestScrewRegistry });
}
