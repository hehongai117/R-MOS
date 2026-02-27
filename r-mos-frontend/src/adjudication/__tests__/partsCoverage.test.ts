/**
 * @description 核心件细节模型覆盖测试（24 核心件）
 * @module adjudication/__tests__/partsCoverage.test
 */

import { existsSync } from 'fs';
import { join } from 'path';
import { PART_METADATA } from '../../components/Viewer3D/Atom01Interactive';
import { DETAIL_PARTS_MAP, getExplodePartsForLink } from '../../components/Viewer3D/partsManifest';

interface TestResult {
    name: string;
    passed: boolean;
    details: string;
}

function runLinkCoverageTest(): TestResult {
    const linkIds = Object.keys(PART_METADATA);
    const issues: string[] = [];

    linkIds.forEach((linkId) => {
        const parts = DETAIL_PARTS_MAP[linkId] ?? [];
        const frameCount = parts.filter((part) => part.category === 'frame').length;
        const screwCount = parts.filter((part) => part.category === 'screw').length;

        if (parts.length < 6) {
            issues.push(`${linkId}: 细节件数量不足（${parts.length}）`);
        }
        if (frameCount < 4) {
            issues.push(`${linkId}: 结构件数量不足（${frameCount}）`);
        }
        if (screwCount < 1) {
            issues.push(`${linkId}: 缺少螺丝模型`);
        }
    });

    return {
        name: 'Detail Coverage: 24核心件',
        passed: issues.length === 0,
        details: issues.length === 0
            ? `核心件覆盖通过：${linkIds.length}/24 均具备结构件与螺丝模型`
            : issues.join('\n'),
    };
}

function runPathExistenceTest(): TestResult {
    const rootPath = join(process.cwd(), 'public/models/parts');
    const missing: string[] = [];

    Object.entries(DETAIL_PARTS_MAP).forEach(([linkId, parts]) => {
        parts.forEach((part) => {
            const fullPath = join(rootPath, part.path);
            if (!existsSync(fullPath)) {
                missing.push(`${linkId}: ${part.path}`);
            }
        });
    });

    return {
        name: 'Detail Coverage: 资源路径存在性',
        passed: missing.length === 0,
        details: missing.length === 0
            ? '所有细节件路径均可在 /public/models/parts 下找到'
            : missing.join('\n'),
    };
}

function runActionTargetCoverageTest(): TestResult {
    const actionTargets = new Set<string>();
    Object.values(DETAIL_PARTS_MAP).forEach((parts) => {
        parts.forEach((part) => {
            if (part.actionTarget) {
                actionTargets.add(part.actionTarget);
            }
        });
    });

    const requiredTargets = [
        'frame_torso_chest',
        'torso_motor',
        'torso_pcb_main',
        'left_foot_rubber',
        'right_foot_rubber',
    ];
    const missingTargets = requiredTargets.filter((target) => !actionTargets.has(target));

    return {
        name: 'Detail Coverage: 关键动作目标映射',
        passed: missingTargets.length === 0,
        details: missingTargets.length === 0
            ? '关键动作目标（躯干盖板/电机/PCB/双脚软胶）均已具备细节件映射'
            : `缺失 actionTarget: ${missingTargets.join(', ')}`,
    };
}

function runExplodeSecondaryTest(): TestResult {
    const torsoL2 = getExplodePartsForLink('torso_link', { includeSecondary: true });
    const leftFootL2 = getExplodePartsForLink('left_ankle_roll_link', { includeSecondary: true });

    const checks = [
        torsoL2.some((part) => part.category === 'screw'),
        torsoL2.some((part) => part.category === 'electronics'),
        leftFootL2.some((part) => part.actionTarget === 'left_foot_rubber'),
    ];

    return {
        name: 'Detail Coverage: L2 全量细节件',
        passed: checks.every(Boolean),
        details: checks.every(Boolean)
            ? 'L2 模式可显示并交互螺丝/电子件/软胶覆盖件'
            : 'L2 次级件显示不完整（缺螺丝或关键覆盖件）',
    };
}

export function runAllPartCoverageTests(): {
    total: number;
    passed: number;
    failed: number;
    results: TestResult[];
} {
    const results = [
        runLinkCoverageTest(),
        runPathExistenceTest(),
        runActionTargetCoverageTest(),
        runExplodeSecondaryTest(),
    ];
    const passed = results.filter((result) => result.passed).length;
    return {
        total: results.length,
        passed,
        failed: results.length - passed,
        results,
    };
}
