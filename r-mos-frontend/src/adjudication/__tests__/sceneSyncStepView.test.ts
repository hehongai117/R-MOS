import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ActionType, type SOPStepAdjudication } from '../types/adjudication';
import { useSOPSceneSync } from '../ui/useSOPSceneSync';

const base = {
    stepId: 's1',
    stepIndex: 1,
    description: '',
    targetParts: [],
    requiredTool: null,
    preconditions: [],
    validations: [],
    failureReasons: [],
    onSuccess: { nextStepId: 'end', stateTransition: null },
    onFailure: { action: 'block' as const, message: '' },
    phase: 'execute' as const,
};

describe('useSOPSceneSync stepView', () => {
    it('bindStep 返回作者化构图，并优先用 highlight 与 explode', () => {
        const camera = {
            position: [1, 1, 1] as [number, number, number],
            target: [0, 0, 0] as [number, number, number],
            fov: 50,
        };
        const step = {
            ...base,
            title: '爆炸到 90%',
            action: ActionType.FOCUS_CAMERA,
            targetParts: ['torso_link'],
            stepView: {
                camera,
                visibleLinks: ['base_link', 'torso_link'],
                highlight: ['left_knee_link'],
                explode: 0.35,
            },
        } as SOPStepAdjudication;
        const { result } = renderHook(() => useSOPSceneSync());

        let intent: ReturnType<typeof result.current.bindStep>;
        act(() => { intent = result.current.bindStep(step, 0); });

        expect(intent!).toMatchObject({
            targetPart: 'left_knee_link',
            explodeAmount: 0.35,
            camera,
            visibleLinks: ['base_link', 'torso_link'],
            highlight: ['left_knee_link'],
        });
    });

    it('stepView 未定义时 targetPart 与 explodeAmount 保持原有启发式', () => {
        const step = {
            ...base,
            title: '爆炸到 90%',
            action: ActionType.FOCUS_CAMERA,
            targetParts: ['torso_link'],
        } as SOPStepAdjudication;
        const { result } = renderHook(() => useSOPSceneSync());

        let intent: ReturnType<typeof result.current.bindStep>;
        act(() => { intent = result.current.bindStep(step, 0); });

        expect(intent!.targetPart).toBe('torso_link');
        expect(intent!.explodeAmount).toBeCloseTo(0.9);
    });

    it('stepView 只给 camera 时 explodeAmount 仍走原有启发式', () => {
        const step = {
            ...base,
            title: '定位',
            action: ActionType.REMOVE_PART,
            stepView: {
                camera: {
                    position: [1, 1, 1],
                    target: [0, 0, 0],
                    fov: 50,
                },
            },
        } as SOPStepAdjudication;
        const { result } = renderHook(() => useSOPSceneSync());

        let intent: ReturnType<typeof result.current.bindStep>;
        act(() => { intent = result.current.bindStep(step, 0); });

        expect(intent!.camera?.fov).toBe(50);
        expect(intent!.explodeAmount).toBeCloseTo(0.62);
    });
});
