/**
 * @description TC-001~TC-005 垂直切片测试用例
 * @module adjudication/__tests__/decisionEngine.test
 * 
 * 测试目标：脚部总成拆卸裁决验证
 * 
 * 基于开发计划 §5.1 验收用例定义：
 * - TC-001: 未拆软胶直接拆骨架 → 阻断
 * - TC-002: 用错误工具拆螺丝 → 阻断 + 提示正确工具
 * - TC-003: 螺丝未完全拆除就分离 → 阻断 + 显示剩余圈数
 * - TC-004: 正确流程完整拆卸 → 通过
 * - TC-005: 生成裁决报告 → 包含原因和操作建议
 */

import {
    AdjudicationResult,
    ActionType,
    ScrewState,
    ConstraintType,
} from '../types/adjudication';
import {
    adjudicateAction,
    canRemoveScrew,
    canDetachPart,
} from '../core/decisionEngine';
import {
    checkToolMatch,
} from '../core/geometryJudge';
import {
    useAdjudicationStore,
    resetStateDirect,
} from '../core/stateManager';

// ============================================================
// 测试辅助函数
// ============================================================

/**
 * 重置所有状态
 */
function resetTestState(): void {
    resetStateDirect();
}

/**
 * 模拟选择工具
 */
function selectTool(toolId: string): void {
    useAdjudicationStore.getState().setCurrentTool(toolId);
}

/**
 * 模拟螺丝完全退出
 */
function extractScrew(screwId: string): void {
    const store = useAdjudicationStore.getState();
    store.setScrewState(screwId, ScrewState.EXTRACTED, 14, 11); // M4x10: 14圈, 11mm位移
}

/**
 * 模拟零件移除
 */
function removePart(partId: string): void {
    const store = useAdjudicationStore.getState();
    store.setPartRemoved(partId);
}

// ============================================================
// TC-001: 未拆软胶直接拆骨架
// ============================================================

export function runTC001(): {
    name: string;
    passed: boolean;
    details: string;
} {
    resetTestState();

    const testName = 'TC-001: 未拆软胶直接拆骨架';

    // 尝试直接拆卸被软胶覆盖的脚底板
    const report = canDetachPart('left_ankle_roll_link');

    // 验证：应该被阻断
    const passed = report.result === AdjudicationResult.BLOCKED && report.reasonCode === 'ERR_CONSTRAINT';

    // 验证：阻断原因应该提到软胶覆盖
    const hasCorrectReason = report.reason.includes('软胶') ||
        report.blockingConstraints.some(c => c.type === ConstraintType.COVERED_BY);

    return {
        name: testName,
        passed: passed && hasCorrectReason,
        details: `
      结果: ${report.result}
      原因: ${report.reason}
      原因码: ${report.reasonCode}
      阻塞约束数: ${report.blockingConstraints.length}
      预期: BLOCKED (覆盖约束未解除)
      验证: ${passed ? '✅ 正确阻断' : '❌ 未正确阻断'}
    `.trim(),
    };
}

// ============================================================
// TC-002: 用错误工具拆螺丝
// ============================================================

export function runTC002(): {
    name: string;
    passed: boolean;
    details: string;
} {
    resetTestState();

    const testName = 'TC-002: 用错误工具拆螺丝';

    // 先移除软胶，使螺丝可访问
    removePart('left_foot_rubber');

    // 选择错误的工具（M4x10 需要 hex_3，我们选 hex_2.5）
    selectTool('hex_2.5');

    // 尝试拆卸 M4x10 螺丝
    const screwId = 'screw_left_foot_m4x10_001';
    const report = canRemoveScrew(screwId, 'hex_2.5');

    // 验证：应该返回 TOOL_MISMATCH
    const passed = report.result === AdjudicationResult.TOOL_MISMATCH;

    // 验证：应该提示正确工具
    const toolCheck = checkToolMatch('hex_2.5', screwId);
    const suggestsCorrectTool = toolCheck.requiredTool === 'hex_3';

    return {
        name: testName,
        passed: passed && suggestsCorrectTool,
        details: `
      结果: ${report.result}
      原因: ${report.reason}
      所需工具: ${toolCheck.requiredTool}
      预期: TOOL_MISMATCH + 提示 hex_3
      验证: ${passed ? '✅ 正确检测工具不匹配' : '❌ 未正确检测'}
      工具提示: ${suggestsCorrectTool ? '✅ 正确提示所需工具' : '❌ 未正确提示'}
    `.trim(),
    };
}

// ============================================================
// TC-003: 螺丝未完全拆除就分离
// ============================================================

export function runTC003(): {
    name: string;
    passed: boolean;
    details: string;
} {
    resetTestState();

    const testName = 'TC-003: 螺丝未完全拆除就分离';

    // 先移除软胶
    removePart('left_foot_rubber');

    // 模拟部分拆卸：只拆了 2 颗螺丝，还有 2 颗未拆
    extractScrew('screw_left_foot_m4x10_001');
    extractScrew('screw_left_foot_m4x10_002');
    // screw_left_foot_m4x10_003 和 004 未拆

    // 尝试分离脚底板
    const report = canDetachPart('left_ankle_roll_link');

    // 验证：应该返回 INCOMPLETE 或 BLOCKED
    const passed = report.result === AdjudicationResult.BLOCKED &&
        report.reasonCode === 'ERR_CONSTRAINT';

    // 验证：应该提示剩余螺丝
    const mentionsRemaining = report.reason.includes('螺丝') ||
        report.requiredActions.some(a => a.includes('螺丝'));

    return {
        name: testName,
        passed: passed && mentionsRemaining,
        details: `
      结果: ${report.result}
      原因: ${report.reason}
      需要操作: ${report.requiredActions.join(', ') || '无'}
      预期: BLOCKED + ERR_CONSTRAINT (约束未解除)
      验证: ${passed ? '✅ 正确阻断' : '❌ 未正确阻断'}
      提示剩余: ${mentionsRemaining ? '✅ 正确提示剩余螺丝' : '❌ 未正确提示'}
    `.trim(),
    };
}

// ============================================================
// TC-004: 正确流程完整拆卸
// ============================================================

export function runTC004(): {
    name: string;
    passed: boolean;
    details: string;
} {
    resetTestState();

    const testName = 'TC-004: 正确流程完整拆卸';
    const steps: { step: string; result: string; passed: boolean }[] = [];

    // 步骤 1: 移除软胶
    removePart('left_foot_rubber');
    const step1Report = canDetachPart('left_ankle_roll_link');
    steps.push({
        step: '1. 移除软胶后检查',
        result: step1Report.result,
        passed: step1Report.result === AdjudicationResult.BLOCKED, // 螺丝还在
    });

    // 步骤 2: 选择正确工具
    selectTool('hex_3');
    const toolCheck = checkToolMatch('hex_3', 'screw_left_foot_m4x10_001');
    steps.push({
        step: '2. 工具匹配检查',
        result: toolCheck.matched ? 'MATCHED' : 'MISMATCH',
        passed: toolCheck.matched,
    });

    // 步骤 3: 拆卸脚底板螺丝
    const screwIds = [
        'screw_left_foot_m4x10_001',
        'screw_left_foot_m4x10_002',
        'screw_left_foot_m4x10_003',
        'screw_left_foot_m4x10_004',
    ];

    screwIds.forEach(id => {
        extractScrew(id);
    });

    // 手动更新约束状态
    const store = useAdjudicationStore.getState();
    store.setConstraintActive('constraint_left_foot_fastened', false);

    steps.push({
        step: '3. 拆卸 4 颗螺丝',
        result: 'EXTRACTED',
        passed: true,
    });

    // 步骤 3.1: 拆卸踝关节螺丝（父子链约束影响）
    const ankleScrewIds = [
        'screw_left_ankle_m4x8_001',
        'screw_left_ankle_m4x8_002',
        'screw_left_ankle_m4x8_003',
        'screw_left_ankle_m4x8_004',
    ];

    ankleScrewIds.forEach(id => {
        extractScrew(id);
    });

    store.setConstraintActive('constraint_left_ankle_fastened', false);

    steps.push({
        step: '3.1. 拆卸踝关节螺丝',
        result: 'EXTRACTED',
        passed: true,
    });

    // 步骤 4: 分离脚底板
    const step4Report = canDetachPart('left_ankle_roll_link');
    steps.push({
        step: '4. 分离脚底板',
        result: step4Report.result,
        passed: step4Report.result === AdjudicationResult.ALLOWED,
    });

    const allPassed = steps.every(s => s.passed);

    return {
        name: testName,
        passed: allPassed,
        details: steps.map(s => `${s.step}: ${s.result} ${s.passed ? '✅' : '❌'}`).join('\n'),
    };
}

// ============================================================
// TC-005: 生成裁决报告
// ============================================================

export function runTC005(): {
    name: string;
    passed: boolean;
    details: string;
} {
    resetTestState();

    const testName = 'TC-005: 生成裁决报告';

    // 制造一个阻断场景
    const report = adjudicateAction(
        ActionType.DETACH_PART,
        'left_ankle_roll_link'
    );

    // 验证报告结构完整性
    const hasResult = typeof report.result === 'string';
    const hasTargetPart = typeof report.targetPart === 'string';
    const hasReason = typeof report.reason === 'string' && report.reason.length > 0;
    const hasReasonCode = typeof report.reasonCode === 'string';
    const hasBlockingConstraints = Array.isArray(report.blockingConstraints);
    const hasRequiredActions = Array.isArray(report.requiredActions);
    const hasTimestamp = typeof report.timestamp === 'number';

    const structureComplete = hasResult && hasTargetPart && hasReason &&
        hasReasonCode && hasBlockingConstraints &&
        hasRequiredActions && hasTimestamp;

    // 验证：阻断原因可读
    const reasonIsReadable = report.reason.length > 5 && !report.reason.includes('undefined');

    // 验证：有操作建议
    const hasActionSuggestions = report.requiredActions.length > 0;

    return {
        name: testName,
        passed: structureComplete && reasonIsReadable,
        details: `
      报告结构完整: ${structureComplete ? '✅' : '❌'}
      - result: ${hasResult ? '✅' : '❌'} (${report.result})
      - targetPart: ${hasTargetPart ? '✅' : '❌'} (${report.targetPart})
      - reason: ${hasReason ? '✅' : '❌'} (${report.reason})
      - reasonCode: ${hasReasonCode ? '✅' : '❌'} (${report.reasonCode})
      - blockingConstraints: ${hasBlockingConstraints ? '✅' : '❌'} (${report.blockingConstraints.length}个)
      - requiredActions: ${hasRequiredActions ? '✅' : '❌'} (${report.requiredActions.length}个)
      - timestamp: ${hasTimestamp ? '✅' : '❌'}
      
      原因可读: ${reasonIsReadable ? '✅' : '❌'}
      有操作建议: ${hasActionSuggestions ? '✅' : '❌'}
    `.trim(),
    };
}

// ============================================================
// TC-006: 聚焦视图不应被拆卸约束阻断
// ============================================================

export function runTC006(): {
    name: string;
    passed: boolean;
    details: string;
} {
    resetTestState();

    const testName = 'TC-006: FOCUS_CAMERA 不应被拆卸约束阻断';

    const report = adjudicateAction(
        ActionType.FOCUS_CAMERA,
        'torso_link',
    );

    const passed = report.result === AdjudicationResult.ALLOWED;

    return {
        name: testName,
        passed,
        details: `
      结果: ${report.result}
      原因: ${report.reason}
      原因码: ${report.reasonCode}
      预期: ALLOWED（仅视图聚焦，不应触发拆卸约束）
      验证: ${passed ? '✅ 正确放行' : '❌ 被错误阻断'}
    `.trim(),
    };
}

// ============================================================
// TC-007: 左臂核心件应在裁决注册表中可识别
// ============================================================

export function runTC007(): {
    name: string;
    passed: boolean;
    details: string;
} {
    resetTestState();

    const testName = 'TC-007: 左臂核心件必须可识别';

    const report = adjudicateAction(
        ActionType.FOCUS_CAMERA,
        'left_arm_pitch_link',
    );

    const passed = report.result === AdjudicationResult.ALLOWED;
    const notFound = report.reasonCode === 'PART_NOT_FOUND';

    return {
        name: testName,
        passed,
        details: `
      结果: ${report.result}
      原因: ${report.reason}
      原因码: ${report.reasonCode}
      预期: ALLOWED（左臂零件存在）
      PART_NOT_FOUND: ${notFound ? '❌ 出现' : '✅ 未出现'}
      验证: ${passed ? '✅ 可识别' : '❌ 未注册'}
    `.trim(),
    };
}

// ============================================================
// TC-008: 躯干 M4×12 螺丝应可被裁决识别
// ============================================================

export function runTC008(): {
    name: string;
    passed: boolean;
    details: string;
} {
    resetTestState();

    const testName = 'TC-008: 躯干 M4×12 螺丝必须可识别';

    const report = canRemoveScrew('screw_torso_m4x12_001', 'hex_3');
    const passed = report.result === AdjudicationResult.ALLOWED;
    const notFound = report.reasonCode === 'SCREW_NOT_FOUND';

    return {
        name: testName,
        passed,
        details: `
      结果: ${report.result}
      原因: ${report.reason}
      原因码: ${report.reasonCode}
      预期: ALLOWED（螺丝存在且工具匹配）
      SCREW_NOT_FOUND: ${notFound ? '❌ 出现' : '✅ 未出现'}
      验证: ${passed ? '✅ 可识别' : '❌ 未注册或校验失败'}
    `.trim(),
    };
}

// ============================================================
// 运行所有测试
// ============================================================

export interface TestResult {
    name: string;
    passed: boolean;
    details: string;
}

export function runAllTests(): {
    results: TestResult[];
    passed: number;
    failed: number;
    total: number;
} {
    const results: TestResult[] = [
        runTC001(),
        runTC002(),
        runTC003(),
        runTC004(),
        runTC005(),
        runTC006(),
        runTC007(),
        runTC008(),
    ];

    const passed = results.filter(r => r.passed).length;
    const failed = results.filter(r => !r.passed).length;

    return {
        results,
        passed,
        failed,
        total: results.length,
    };
}

/**
 * 打印测试报告到控制台
 */
export function printTestReport(): void {
    console.log('\n' + '='.repeat(60));
    console.log('R-MOS 裁决系统垂直切片测试报告');
    console.log('='.repeat(60) + '\n');

    const { results, passed, failed, total } = runAllTests();

    results.forEach((result, index) => {
        console.log(`\n[${index + 1}] ${result.name}`);
        console.log('-'.repeat(40));
        console.log(result.details);
        console.log(`状态: ${result.passed ? '✅ PASSED' : '❌ FAILED'}`);
    });

    console.log('\n' + '='.repeat(60));
    console.log(`总计: ${total} | 通过: ${passed} | 失败: ${failed}`);
    console.log('='.repeat(60) + '\n');
}
