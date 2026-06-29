/**
 * sopPlayerConfig.ts — SOPPlayerAdjudicated の定数 / 色テーブル / 別名マップ
 *
 * 純粋な定数ファイル。ロジックなし。
 */

import React from 'react';
import {
    ToolOutlined,
    AimOutlined,
    ExpandOutlined,
} from '@ant-design/icons';
import { SOPExecutionState } from '@/adjudication';

// 步骤图标
export const StepIcon: Record<string, React.ReactNode> = {
    'select_tool': React.createElement(ToolOutlined),
    'rotate_screw': React.createElement(AimOutlined),
    'extract_screw': React.createElement(AimOutlined),
    'detach_part': React.createElement(ExpandOutlined),
    'remove_part': React.createElement(ExpandOutlined),
    'focus_camera': React.createElement(AimOutlined),
};

// 执行状态颜色
export const ExecutionStateColor: Record<SOPExecutionState, string> = {
    [SOPExecutionState.IDLE]: '#1890ff',
    [SOPExecutionState.PRECONDITION_CHECK]: '#faad14',
    [SOPExecutionState.EXECUTING]: '#52c41a',
    [SOPExecutionState.VALIDATION]: '#722ed1',
    [SOPExecutionState.COMPLETE]: '#13c2c2',
    [SOPExecutionState.FAILED]: '#ff4d4f',
    [SOPExecutionState.BLOCKED]: '#ff4d4f',
};

// 执行状态文本
export const ExecutionStateText: Record<SOPExecutionState, string> = {
    [SOPExecutionState.IDLE]: '就绪',
    [SOPExecutionState.PRECONDITION_CHECK]: '检查前置条件',
    [SOPExecutionState.EXECUTING]: '执行中',
    [SOPExecutionState.VALIDATION]: '验证中',
    [SOPExecutionState.COMPLETE]: '已完成',
    [SOPExecutionState.FAILED]: '失败',
    [SOPExecutionState.BLOCKED]: '已阻断',
};

/**
 * @deprecated 硬编码的细节零件→核心 link 别名映射。
 * 当 manifest 的 detail_parts 字段可用时，应改用 buildPartTargetAliases(manifest) 动态推导。
 * 目前 manifest 尚未包含完整的 detail_parts 数据，此表作为 fallback 兜底继续使用。
 *
 * TODO: 当 manifest detail_parts 数据完善后，迁移到 buildPartTargetAliases()，
 * 并将其结果通过 props 或 context 传入，以支持多机器人场景。
 */
export const PART_TARGET_ALIASES: Record<string, string[]> = {
    frame_torso_chest: ['torso_link'],
    torso_motor: ['torso_link'],
    torso_pcb_main: ['torso_link'],
    left_foot_rubber: ['left_ankle_roll_link'],
    right_foot_rubber: ['right_ankle_roll_link'],
};

/**
 * 从 manifest 的 detail_parts 动态推导细节零件→核心 link 别名映射。
 *
 * detail_parts 结构：Record<linkId, Array<{ displayName, path, category, actionTarget? }>>
 * - 若 detail part 有 actionTarget，则该 actionTarget 作为细节零件 ID，映射到对应 linkId。
 * - 否则，使用 path 的最后一段（basename，去掉扩展名）作为细节零件 ID。
 *
 * @returns 别名映射表，若 manifest 无 detail_parts 则返回 null（调用方应 fallback 到硬编码表）
 *
 * TODO: 启用此函数需要将 manifest 通过 props 传入 SOPPlayerAdjudicated，
 * 并在 resolvePartTargetId 中合并硬编码表与动态表。
 */
export function buildPartTargetAliases(
    manifest: { detail_parts?: Record<string, Array<{ displayName: string; path: string; category: string; actionTarget?: string }>> } | null
): Record<string, string[]> | null {
    const detailParts = manifest?.detail_parts;
    if (!detailParts) return null;

    const aliases: Record<string, string[]> = {};
    for (const [linkId, parts] of Object.entries(detailParts)) {
        for (const part of parts) {
            // 优先使用 actionTarget 作为细节零件 ID，否则取 path basename
            const partId = part.actionTarget
                ?? part.path.split('/').pop()?.replace(/\.[^.]+$/, '')
                ?? null;
            if (!partId) continue;

            if (!aliases[partId]) {
                aliases[partId] = [];
            }
            if (!aliases[partId].includes(linkId)) {
                aliases[partId].push(linkId);
            }
        }
    }
    return Object.keys(aliases).length > 0 ? aliases : null;
}

// 难度标签颜色
export const difficultyColor: Record<string, string> = {
    'beginner': 'green',
    'intermediate': 'orange',
    'advanced': 'red',
};
