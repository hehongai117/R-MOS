/**
 * @description 关键部件清单（裁决用）
 * @module adjudication/data/criticalParts
 *
 * 注意：该表是“关键部件”唯一判定来源
 */

export const CRITICAL_PARTS: Record<string, { reason: string }> = {
    // TODO: 根据工艺与安全要求补充
    // 例：'torso_link': { reason: '主结构承力件' },
};

export function isCriticalPart(partId: string): boolean {
    return Boolean(CRITICAL_PARTS[partId]);
}

export function getCriticalPartReason(partId: string): string | null {
    return CRITICAL_PARTS[partId]?.reason ?? null;
}
