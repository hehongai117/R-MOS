import { beforeEach, describe, it, expect } from 'vitest';
import { validateStepCompletion } from '../executor/sopExecutor';
import { useAdjudicationStore } from '../core/stateManager';
import {
    AdjudicationResult,
    ActionType,
    ValidationType,
    type StepView,
    type SOPStepAdjudication,
} from '../types/adjudication';

function checklistStep(
    type: ValidationType.KIT_CONFIRMED | ValidationType.CHECKLIST_CONFIRMED,
    confirmedItems: string[],
): SOPStepAdjudication {
    return {
        stepId: type === ValidationType.KIT_CONFIRMED ? 'step_kit' : 'step_verify',
        stepIndex: 1,
        title: type === ValidationType.KIT_CONFIRMED ? '齐套确认' : '验收确认',
        description: '',
        action: type === ValidationType.KIT_CONFIRMED
            ? ActionType.CONFIRM_KIT
            : ActionType.VERIFY_CHECK,
        targetParts: [],
        requiredTool: null,
        preconditions: [],
        failureReasons: [],
        onSuccess: { nextStepId: 'step_002', stateTransition: null },
        onFailure: { action: 'block', message: '检查未完成' },
        phase: type === ValidationType.KIT_CONFIRMED ? 'prep' : 'verify',
        validations: [{
            type,
            params: {
                requiredItems: ['hex_2.5', 'hex_3', '6205-2RS'],
                confirmedItems,
            },
            isRequired: true,
        }],
    } as SOPStepAdjudication;
}

describe('三段式类型扩展', () => {
    it('新增四个 ActionType', () => {
        expect(ActionType.CONFIRM_KIT).toBe('confirm_kit');
        expect(ActionType.INSTALL_PART).toBe('install_part');
        expect(ActionType.TIGHTEN_SCREW).toBe('tighten_screw');
        expect(ActionType.VERIFY_CHECK).toBe('verify_check');
    });

    it('新增三个 ValidationType', () => {
        expect(ValidationType.KIT_CONFIRMED).toBe('kit_confirmed');
        expect(ValidationType.SCREW_ORDER_MATCHED).toBe('screw_order_matched');
        expect(ValidationType.CHECKLIST_CONFIRMED).toBe('checklist_confirmed');
    });

    it('StepView 全字段可选，允许只给 explode', () => {
        const minimal: StepView = { explode: 0.4 };
        const full: StepView = {
            camera: { position: [1, 0.5, 1.2], target: [0, 0.4, 0], fov: 45 },
            visibleLinks: ['left_knee_link'],
            highlight: ['left_knee_link'],
            explode: 0.45,
            screwFocus: ['screw_left_knee_m4x8_001'],
        };
        expect(minimal.explode).toBe(0.4);
        expect(full.camera?.fov).toBe(45);
    });

    it('SOPStepAdjudication 携带 phase 与物料，groupPath/stepView 可缺省', () => {
        // bom_code 为 snake_case：后端 requiredParts 原样透传 sop_steps.required_parts
        // 的 JSON，不做 key 转换（见 sop_service._sop_to_adjudication）
        const step = {
            phase: 'prep',
            requiredParts: [{ bom_code: '6205-2RS', name: '深沟球轴承', qty: 1 }],
        } as Partial<SOPStepAdjudication>;
        expect(step.phase).toBe('prep');
        expect(step.requiredParts?.[0].bom_code).toBe('6205-2RS');
    });
});

describe('齐套与验收 validation', () => {
    it('齐套项未勾满时不通过', () => {
        const result = validateStepCompletion(checklistStep(
            ValidationType.KIT_CONFIRMED,
            ['hex_2.5'],
        ));

        expect(result.allPassed).toBe(false);
        expect(result.failedValidations[0].message).toContain('齐套');
    });

    it('齐套项全部勾选后通过', () => {
        const result = validateStepCompletion(checklistStep(
            ValidationType.KIT_CONFIRMED,
            ['hex_2.5', 'hex_3', '6205-2RS'],
        ));

        expect(result.allPassed).toBe(true);
    });

    it('验收项未勾满时不通过', () => {
        const result = validateStepCompletion(checklistStep(
            ValidationType.CHECKLIST_CONFIRMED,
            ['hex_2.5', 'hex_3'],
        ));

        expect(result.allPassed).toBe(false);
        expect(result.failedValidations[0].message).toContain('验收项');
    });

    it('验收项全部勾选后通过', () => {
        const result = validateStepCompletion(checklistStep(
            ValidationType.CHECKLIST_CONFIRMED,
            ['hex_2.5', 'hex_3', '6205-2RS'],
        ));

        expect(result.allPassed).toBe(true);
    });
});

function orderStep(expected: string[]): SOPStepAdjudication {
    return {
        ...checklistStep(ValidationType.KIT_CONFIRMED, []),
        stepId: 'step_tighten',
        title: '对角拧紧',
        action: ActionType.TIGHTEN_SCREW,
        phase: 'execute',
        validations: [{
            type: ValidationType.SCREW_ORDER_MATCHED,
            params: { expectedOrder: expected },
            isRequired: true,
        }],
    } as SOPStepAdjudication;
}

function pushTighten(screwId: string) {
    useAdjudicationStore.getState().addActionRecord({
        action: ActionType.TIGHTEN_SCREW,
        targetParts: [screwId],
        toolId: 'hex_3',
        result: AdjudicationResult.ALLOWED,
    });
}

describe('对角紧固顺序', () => {
    const DIAGONAL = ['screw_a1', 'screw_a3', 'screw_a2', 'screw_a4'];

    beforeEach(() => useAdjudicationStore.getState().resetState());

    it('顺序错误时不通过', () => {
        pushTighten('screw_a1');
        pushTighten('screw_a2');

        const result = validateStepCompletion(orderStep(DIAGONAL));

        expect(result.allPassed).toBe(false);
        expect(result.failedValidations[0].message).toContain('顺序');
    });

    it('部分完成且顺序正确时不报错，但未拧完仍不通过', () => {
        pushTighten('screw_a1');
        pushTighten('screw_a3');

        const result = validateStepCompletion(orderStep(DIAGONAL));

        expect(result.allPassed).toBe(false);
        expect(result.failedValidations[0].message).not.toContain('顺序错误');
    });

    it('全部按对角顺序拧完后通过', () => {
        DIAGONAL.forEach(pushTighten);

        const result = validateStepCompletion(orderStep(DIAGONAL));

        expect(result.allPassed).toBe(true);
    });
});
