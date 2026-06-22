/**
 * Shared formatting utilities for R-MOS frontend.
 */

/**
 * Format a date/time value to a zh-CN locale string.
 * Accepts ISO strings, unix timestamps (ms), or null/undefined.
 * Returns '暂无' for falsy input.
 */
export function formatDateTime(value?: string | number | null | undefined): string {
  if (!value) return '暂无'
  return new Date(value).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

/**
 * Convert a duration in seconds to "Xh" or "Xh Ym" display string.
 * Returns '0h' for falsy input.
 */
export function formatHours(seconds?: number | null): string {
  if (!seconds) return '0h'
  return `${(seconds / 3600).toFixed(1)}h`
}

/**
 * Human-readable names for training step IDs shared across teacher and student views.
 */
export const STEP_NAME_MAP: Record<string, string> = {
  prepare_station: '准备工位',
  motor_cover_remove: '拆解电机盖',
  align_reducer: '校准减速器',
  final_check: '最终复核',
}
