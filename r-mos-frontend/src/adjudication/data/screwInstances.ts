/**
 * @description 螺丝实例辅助函数 - 委托给 partRegistry manifest 数据
 * @module adjudication/data/screwInstances
 */

import { getPartById, getPartsByCategory } from './partRegistry';
import { PartCategory, type Part } from '../types/adjudication';

/**
 * 获取螺丝实例
 */
export function getScrewInstance(screwId: string): Part | undefined {
    const part = getPartById(screwId);
    return part?.category === PartCategory.SCREW ? part : undefined;
}

/**
 * 获取所有螺丝实例 ID
 */
export function getAllScrewIds(): string[] {
    return getPartsByCategory(PartCategory.SCREW).map(p => p.id);
}

/**
 * 获取零件的所有螺丝
 */
export function getScrewsByParent(parentId: string): Part[] {
    return getPartsByCategory(PartCategory.SCREW).filter(s => s.parentId === parentId);
}
