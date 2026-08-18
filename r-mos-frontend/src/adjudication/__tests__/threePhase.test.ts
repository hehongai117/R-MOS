import { describe, it, expect } from 'vitest';
import {
    ActionType,
    ValidationType,
    type StepView,
    type SOPStepAdjudication,
} from '../types/adjudication';

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
