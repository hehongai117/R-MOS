/**
 * @description 简易裁决测试运行器
 * @module adjudication/__tests__/run-adjudication-tests
 */

import './test-setup';
import { runAllTests } from './decisionEngine.test';
import { runFatalFailureTest } from './sopExecutor.test';
import { runAllCoreLogicTests } from './core_logic.test';
import { runAllP4Tests } from './p4_mode.test';
import { runAllExamModeTests } from './examMode.test';
import { runAllHardwareSOPFlowTests } from './hardwareSopsFlow.test';
import { runAllPartCoverageTests } from './partsCoverage.test';
import { runAllInteractionGateTests } from './interactionGate.test';

function printSection(title: string): void {
    console.log('\n' + '='.repeat(72));
    console.log(title);
    console.log('='.repeat(72));
}

function printResults(results: { name: string; passed: boolean; details: string }[]): void {
    results.forEach((result, index) => {
        console.log(`\n[${index + 1}] ${result.name}`);
        console.log('-'.repeat(48));
        console.log(result.details);
        console.log(`状态: ${result.passed ? '✅ PASSED' : '❌ FAILED'}`);
    });
}

function main(): void {
    printSection('P3 Core Logic Tests');
    const core = runAllCoreLogicTests();
    printResults(core.results);
    console.log(`\n小结: ${core.total} | 通过 ${core.passed} | 失败 ${core.failed}`);

    printSection('P4 Mode Tests');
    const p4 = runAllP4Tests();
    printResults(p4.results);
    console.log(`\n小结: ${p4.total} | 通过 ${p4.passed} | 失败 ${p4.failed}`);

    printSection('P4 Exam Tests');
    const exam = runAllExamModeTests();
    printResults(exam.results);
    console.log(`\n小结: ${exam.total} | 通过 ${exam.passed} | 失败 ${exam.failed}`);

    printSection('Decision Engine Slice Tests');
    const decision = runAllTests();
    printResults(decision.results);
    console.log(`\n小结: ${decision.total} | 通过 ${decision.passed} | 失败 ${decision.failed}`);

    printSection('SOP Executor Fatal Test');
    const sop = runFatalFailureTest();
    printResults([sop]);
    console.log(`\n小结: 1 | 通过 ${sop.passed ? 1 : 0} | 失败 ${sop.passed ? 0 : 1}`);

    printSection('Hardware SOP Full Flow Tests');
    const hardware = runAllHardwareSOPFlowTests();
    printResults(hardware.results);
    console.log(`\n小结: ${hardware.total} | 通过 ${hardware.passed} | 失败 ${hardware.failed}`);

    printSection('SOP Interaction Gate Tests');
    const interactionGate = runAllInteractionGateTests();
    printResults(interactionGate.results);
    console.log(`\n小结: ${interactionGate.total} | 通过 ${interactionGate.passed} | 失败 ${interactionGate.failed}`);

    printSection('Part Model Coverage Tests');
    const partCoverage = runAllPartCoverageTests();
    printResults(partCoverage.results);
    console.log(`\n小结: ${partCoverage.total} | 通过 ${partCoverage.passed} | 失败 ${partCoverage.failed}`);

    const failed = core.failed
        + p4.failed
        + exam.failed
        + decision.failed
        + (sop.passed ? 0 : 1)
        + hardware.failed
        + interactionGate.failed
        + partCoverage.failed;
    if (failed > 0) {
        process.exitCode = 1;
    }
}

main();
