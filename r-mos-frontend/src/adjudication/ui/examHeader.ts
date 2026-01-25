/**
 * @description 考试模式顶部信息辅助函数
 */

export function formatCountdown(ms: number): string {
    const safeMs = Math.max(0, ms);
    const totalSeconds = Math.floor(safeMs / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    const mm = String(minutes).padStart(2, '0');
    const ss = String(seconds).padStart(2, '0');
    return `${mm}:${ss}`;
}

export function isCountdownUrgent(ms: number): boolean {
    return ms <= 5 * 60 * 1000;
}
