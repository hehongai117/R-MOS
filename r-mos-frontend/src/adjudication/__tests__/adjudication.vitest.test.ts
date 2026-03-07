import "./test-setup";
import { describe, expect, it } from "vitest";

import { runAllCoreLogicTests } from "./core_logic.test";
import { runAllP4Tests } from "./p4_mode.test";
import { runAllExamModeTests } from "./examMode.test";
import { runAllTests as runDecisionEngineTests } from "./decisionEngine.test";
import { runFatalFailureTest } from "./sopExecutor.test";
import { runAllHardwareSOPFlowTests } from "./hardwareSopsFlow.test";
import { runAllInteractionGateTests } from "./interactionGate.test";
import { runAllPartCoverageTests } from "./partsCoverage.test";

describe("adjudication legacy suite", () => {
  it("core logic tests should all pass", () => {
    const result = runAllCoreLogicTests();
    expect(result.failed).toBe(0);
    expect(result.passed).toBe(result.total);
  });

  it("p4 mode tests should all pass", () => {
    const result = runAllP4Tests();
    expect(result.failed).toBe(0);
    expect(result.passed).toBe(result.total);
  });

  it("exam mode tests should all pass", () => {
    const result = runAllExamModeTests();
    expect(result.failed).toBe(0);
    expect(result.passed).toBe(result.total);
  });

  it("decision engine tests should all pass", () => {
    const result = runDecisionEngineTests();
    expect(result.failed).toBe(0);
    expect(result.passed).toBe(result.total);
  });

  it("sop fatal test should pass", () => {
    const result = runFatalFailureTest();
    expect(result.passed).toBe(true);
  });

  it("hardware sop full flow tests should all pass", () => {
    const result = runAllHardwareSOPFlowTests();
    expect(result.failed).toBe(0);
    expect(result.passed).toBe(result.total);
  });

  it("interaction gate tests should all pass", () => {
    const result = runAllInteractionGateTests();
    expect(result.failed).toBe(0);
    expect(result.passed).toBe(result.total);
  });

  it("part coverage tests should all pass", () => {
    const result = runAllPartCoverageTests();
    expect(result.failed).toBe(0);
    expect(result.passed).toBe(result.total);
  });
});
