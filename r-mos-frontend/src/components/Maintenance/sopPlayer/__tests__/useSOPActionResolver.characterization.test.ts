/**
 * Characterization tests for useSOPActionResolver.
 * Tests the hook's handleActionEvent, resolvePartTargetId, resolveScrewTargetId,
 * and normalizeSpec branches via renderHook — no DOM rendering required.
 */

import { renderHook, act } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { ActionType, useAdjudicationStore } from '@/adjudication'
import type { SOPStepAdjudication } from '@/adjudication'
import { useSOPActionResolver } from '../useSOPActionResolver'

// ---------------------------------------------------------------------------
// Fixture helpers
// ---------------------------------------------------------------------------
const makeStep = (over: Partial<SOPStepAdjudication> = {}): SOPStepAdjudication =>
    ({
        stepId: 'step_0',
        stepIndex: 0,
        title: 'Test step',
        description: 'Test description',
        action: ActionType.FOCUS_CAMERA,
        targetParts: [],
        requiredTool: null,
        preconditions: [],
        validations: [],
        failureReasons: [],
        onSuccess: { nextStepId: 'step_1', stateTransition: null },
        onFailure: { action: 'block', message: 'blocked' },
        ...over,
    }) as SOPStepAdjudication

// ---------------------------------------------------------------------------

describe('useSOPActionResolver characterization', () => {
    beforeEach(() => {
        useAdjudicationStore.getState().resetState()
    })
    afterEach(() => {
        useAdjudicationStore.getState().resetState()
    })

    // -- handleActionEvent null guard -------------------------------------------
    it('handleActionEvent returns false when currentStep is null', () => {
        const { result } = renderHook(() => useSOPActionResolver(null))
        let matched: boolean
        act(() => {
            matched = result.current.handleActionEvent({ seq: 1, type: 'part_selected', partName: 'torso_link' })
        })
        expect(matched!).toBe(false)
    })

    // -- default case -----------------------------------------------------------
    it('handleActionEvent returns false for an unrecognised action type (default branch)', () => {
        const step = makeStep({ action: 'UNKNOWN_ACTION' as ActionType })
        const { result } = renderHook(() => useSOPActionResolver(step))
        let matched: boolean
        act(() => {
            matched = result.current.handleActionEvent({ seq: 1, type: 'part_selected', partName: 'torso_link' })
        })
        expect(matched!).toBe(false)
    })

    // -- normalizeSpec ----------------------------------------------------------
    it('normalizeSpec lowercases and normalises × → x and strips whitespace', () => {
        const { result } = renderHook(() => useSOPActionResolver(null))
        expect(result.current.normalizeSpec('M3×0.5 Socket')).toBe('m3x0.5socket')
        expect(result.current.normalizeSpec('PH 2')).toBe('ph2')
    })

    // -- FOCUS_CAMERA: empty targetParts (doc-bridge shortcut) -----------------
    it('FOCUS_CAMERA returns true immediately when targetParts is empty', () => {
        const step = makeStep({ action: ActionType.FOCUS_CAMERA, targetParts: [] })
        const { result } = renderHook(() => useSOPActionResolver(step))
        let matched: boolean
        act(() => {
            matched = result.current.handleActionEvent({ seq: 1, type: 'part_selected', partName: 'anything' })
        })
        expect(matched!).toBe(true)
    })

    // -- FOCUS_CAMERA: direct targetParts match --------------------------------
    it('FOCUS_CAMERA resolves part via direct targetParts match', () => {
        const step = makeStep({ action: ActionType.FOCUS_CAMERA, targetParts: ['torso_link'] })
        const { result } = renderHook(() => useSOPActionResolver(step))
        let matched: boolean
        act(() => {
            matched = result.current.handleActionEvent({ seq: 1, type: 'part_selected', partName: 'torso_link' })
        })
        expect(matched!).toBe(true)
    })

    // -- FOCUS_CAMERA: no match → false ----------------------------------------
    it('FOCUS_CAMERA returns false when part does not match any targetPart or alias', () => {
        const step = makeStep({ action: ActionType.FOCUS_CAMERA, targetParts: ['some_other_part'] })
        const { result } = renderHook(() => useSOPActionResolver(step))
        let matched: boolean
        act(() => {
            matched = result.current.handleActionEvent({ seq: 1, type: 'part_selected', partName: 'nonexistent_xyz' })
        })
        expect(matched!).toBe(false)
    })

    // -- resolvePartTargetId: alias resolution ----------------------------------
    it('resolvePartTargetId resolves via PART_TARGET_ALIASES (frame_torso_chest → torso_link)', () => {
        const step = makeStep({ targetParts: ['frame_torso_chest'] })
        const { result } = renderHook(() => useSOPActionResolver(step))
        expect(result.current.resolvePartTargetId(step, 'torso_link')).toBe('frame_torso_chest')
    })

    // -- resolvePartTargetId: no match -----------------------------------------
    it('resolvePartTargetId returns null when neither direct nor alias match exists', () => {
        const step = makeStep({ targetParts: ['some_part'] })
        const { result } = renderHook(() => useSOPActionResolver(step))
        expect(result.current.resolvePartTargetId(step, 'nonexistent_xyz_abc')).toBeNull()
    })

    // -- DETACH_PART: alias path → commitPartDetachment ------------------------
    it('DETACH_PART resolves part via alias and commits detachment (returns true)', () => {
        // frame_torso_chest → aliases include torso_link
        const step = makeStep({ action: ActionType.DETACH_PART, targetParts: ['frame_torso_chest'] })
        const { result } = renderHook(() => useSOPActionResolver(step))
        let matched: boolean
        act(() => {
            matched = result.current.handleActionEvent({ seq: 1, type: 'part_selected', partName: 'torso_link' })
        })
        expect(matched!).toBe(true)
    })

    // -- DETACH_PART: no match → false ------------------------------------------
    it('DETACH_PART returns false when part cannot be resolved', () => {
        const step = makeStep({ action: ActionType.DETACH_PART, targetParts: ['frame_torso_chest'] })
        const { result } = renderHook(() => useSOPActionResolver(step))
        let matched: boolean
        act(() => {
            matched = result.current.handleActionEvent({ seq: 1, type: 'part_selected', partName: 'nonexistent_xyz' })
        })
        expect(matched!).toBe(false)
    })

    // -- REMOVE_PART: direct match → commitPartRemoval -------------------------
    it('REMOVE_PART resolves part via direct match and commits removal (returns true)', () => {
        const step = makeStep({ action: ActionType.REMOVE_PART, targetParts: ['torso_link'] })
        const { result } = renderHook(() => useSOPActionResolver(step))
        let matched: boolean
        act(() => {
            matched = result.current.handleActionEvent({ seq: 1, type: 'part_selected', partName: 'torso_link' })
        })
        expect(matched!).toBe(true)
    })

    // -- REMOVE_PART: no match → false ------------------------------------------
    it('REMOVE_PART returns false when part cannot be resolved', () => {
        const step = makeStep({ action: ActionType.REMOVE_PART, targetParts: ['torso_link'] })
        const { result } = renderHook(() => useSOPActionResolver(step))
        let matched: boolean
        act(() => {
            matched = result.current.handleActionEvent({ seq: 1, type: 'part_selected', partName: 'nonexistent_xyz' })
        })
        expect(matched!).toBe(false)
    })

    // -- SELECT_TOOL: matching tool --------------------------------------------
    it('SELECT_TOOL returns true when the correct tool event arrives', () => {
        const step = makeStep({ action: ActionType.SELECT_TOOL, requiredTool: 'hex_2.5' })
        const { result } = renderHook(() => useSOPActionResolver(step))
        let matched: boolean
        act(() => {
            matched = result.current.handleActionEvent({ seq: 1, type: 'tool_selected', toolId: 'hex_2.5' })
        })
        expect(matched!).toBe(true)
    })

    // -- SELECT_TOOL: wrong tool -----------------------------------------------
    it('SELECT_TOOL returns false when a different tool is provided', () => {
        const step = makeStep({ action: ActionType.SELECT_TOOL, requiredTool: 'hex_2.5' })
        const { result } = renderHook(() => useSOPActionResolver(step))
        let matched: boolean
        act(() => {
            matched = result.current.handleActionEvent({ seq: 1, type: 'tool_selected', toolId: 'ph_2' })
        })
        expect(matched!).toBe(false)
    })

    // -- EXTRACT_SCREW: wrong event type → false --------------------------------
    it('EXTRACT_SCREW returns false when event type is not screw_selected', () => {
        const step = makeStep({ action: ActionType.EXTRACT_SCREW, targetParts: ['screw_1'] })
        const { result } = renderHook(() => useSOPActionResolver(step))
        let matched: boolean
        act(() => {
            matched = result.current.handleActionEvent({ seq: 1, type: 'part_selected', partName: 'screw_1' })
        })
        expect(matched!).toBe(false)
    })

    // -- ROTATE_SCREW: wrong event type → false --------------------------------
    it('ROTATE_SCREW returns false when event type is not screw_selected', () => {
        const step = makeStep({ action: ActionType.ROTATE_SCREW, targetParts: ['screw_1'] })
        const { result } = renderHook(() => useSOPActionResolver(step))
        let matched: boolean
        act(() => {
            matched = result.current.handleActionEvent({ seq: 1, type: 'part_selected', partName: 'screw_1' })
        })
        expect(matched!).toBe(false)
    })

    // -- EXTRACT_SCREW: direct screwId match → commitScrewExtraction + true ----
    it('EXTRACT_SCREW returns true when screwId directly matches targetParts (resolveScrewTargetId direct path)', () => {
        const step = makeStep({ action: ActionType.EXTRACT_SCREW, targetParts: ['screw_abc'] })
        const { result } = renderHook(() => useSOPActionResolver(step))
        let matched: boolean
        act(() => {
            // 'screw_abc' is in targetParts → direct match in resolveScrewTargetId → commitScrewExtraction → true
            matched = result.current.handleActionEvent({ seq: 1, type: 'screw_selected', screwId: 'screw_abc' })
        })
        expect(matched!).toBe(true)
    })

    // -- EXTRACT_SCREW: fuzzy path when no screw instance found → null → false -
    it('EXTRACT_SCREW returns false when screwId cannot be resolved via fuzzy matching (no screw instances registered)', () => {
        const step = makeStep({ action: ActionType.EXTRACT_SCREW, targetParts: ['screw_abc'] })
        const { result } = renderHook(() => useSOPActionResolver(step))
        let matched: boolean
        act(() => {
            // 'nonexistent_xyz' not in targetParts → fuzzy loops run but getScrewInstance returns null → null → false
            matched = result.current.handleActionEvent({ seq: 1, type: 'screw_selected', screwId: 'nonexistent_xyz' })
        })
        expect(matched!).toBe(false)
    })

    // -- resolveScrewTargetId: direct return ----------------------------------------
    it('resolveScrewTargetId returns rawScrewId immediately when it is in targetParts', () => {
        const step = makeStep({ targetParts: ['screw_abc'] })
        const { result } = renderHook(() => useSOPActionResolver(step))
        expect(result.current.resolveScrewTargetId(step, 'screw_abc')).toBe('screw_abc')
    })

    // -- resolveScrewTargetId: null when no match ---------------------------------
    it('resolveScrewTargetId returns null when rawScrewId is not in targetParts and fuzzy fails', () => {
        const step = makeStep({ targetParts: ['screw_abc'] })
        const { result } = renderHook(() => useSOPActionResolver(step))
        expect(result.current.resolveScrewTargetId(step, 'no_such_screw')).toBeNull()
    })
})
