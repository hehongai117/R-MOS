/**
 * atom01Geometry.ts — 纯函数与几何辅助工具（ATOM-01 专用）
 */

import * as THREE from 'three';
import type { DetailPart } from '../partsManifest';

export const clamp01 = (value: number): number => Math.min(1, Math.max(0, value));

export const smoothstep = (edge0: number, edge1: number, x: number): number => {
    if (edge0 === edge1) return x < edge0 ? 0 : 1;
    const t = clamp01((x - edge0) / (edge1 - edge0));
    return t * t * (3 - 2 * t);
};

export const CATEGORY_PRIORITY: Record<DetailPart['category'], number> = {
    electronics: 1,
    bearing: 2,
    calibration: 3,
    frame: 4,
    misc: 5,
    screw: 6,
    nut: 7,
};

/**
 * 计算爆炸展开轴向，默认沿 Z 轴散开
 */
export function getLinkExplodeAxis(linkName: string): THREE.Vector3 {
    // 根据 link 的特点定制爆炸轴线，大多数可以是局部 Z 轴
    // 例如肩膀沿 Y/X 轴展开等
    if (linkName.includes('pitch')) return new THREE.Vector3(0, 1, 0); // Y轴
    if (linkName.includes('roll')) return new THREE.Vector3(1, 0, 0);  // X轴
    if (linkName.includes('yaw')) return new THREE.Vector3(0, 0, -1);  // -Z轴
    return new THREE.Vector3(0, 0, 1); // 默认 Z 轴
}
