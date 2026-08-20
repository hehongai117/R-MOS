import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { canInstallPart, canTightenScrew } from '../core/decisionEngine';
import { useAdjudicationStore } from '../core/stateManager';
import { clearManifestPartRegistry, injectManifestPartRegistry } from '../data/partRegistry';
import { AdjudicationResult } from '../types/adjudication';
import type { RobotDataManifest } from '@/components/Viewer3D/assemblyManifest';

/** 最小夹具：ID 与 constraintGraph.ts:273-298 的静态约束对齐 */
function makeTorsoManifest(): RobotDataManifest {
    const part = (id: string, category: string) => ({
        id, category, bom_code: `BOM-${id}`, display_name: id,
        parent_id: null, mesh_id: null,
        local_position: [0, 0, 0], local_rotation: [0, 0, 0], group: 'torso',
    });
    return {
        version: '1.0', robotId: '42', rootNodeId: 'base_link',
        mesh_catalog: {}, nodes: [], fastener_instances: [],
        parts_registry: [
            part('frame_torso_chest', 'frame'),
            part('torso_motor', 'motor'),
            part('torso_pcb_main', 'pcb'),
        ],
        screw_instances: [{
            id: 'screw_torso_m3x10_001',
            bom_code: 'SCR-M3x10',
            parent_id: 'frame_torso_chest',
            position: [0, 0, 0], axis: [0, 0, 1],
            spec: {
                type: 'M3×10', pitch: 0.5, thread_length: 10,
                required_tool: 'hex_2.5', torque_nm: 1.2,
            },
        }],
    } as unknown as RobotDataManifest;
}

describe('装配方向裁决', () => {
    beforeEach(() => {
        injectManifestPartRegistry(makeTorsoManifest());
        useAdjudicationStore.getState().resetState();
    });

    afterEach(() => {
        clearManifestPartRegistry();
    });

    it('零件已在位时无需重复安装', () => {
        const report = canInstallPart('frame_torso_chest');
        expect(report.result).toBe(AdjudicationResult.INCOMPLETE);
        expect(report.reasonCode).toBe('ALREADY_INSTALLED');
    });

    it('依赖件未就位时，禁止安装', () => {
        const store = useAdjudicationStore.getState();
        store.setPartRemoved('frame_torso_chest');
        store.setPartRemoved('torso_motor');

        const report = canInstallPart('frame_torso_chest');
        expect(report.result).toBe(AdjudicationResult.BLOCKED);
        expect(report.reasonCode).toBe('INSTALL_ORDER_VIOLATION');
        expect(report.reason).toContain('torso_motor');
        expect(report.requiredActions.length).toBeGreaterThan(0);
    });

    it('依赖件全部就位后，允许安装', () => {
        useAdjudicationStore.getState().setPartRemoved('frame_torso_chest');

        const report = canInstallPart('frame_torso_chest');
        expect(report.result).toBe(AdjudicationResult.ALLOWED);
    });

    it('拧紧螺丝要求所固定的零件已就位', () => {
        useAdjudicationStore.getState().setPartRemoved('frame_torso_chest');

        const report = canTightenScrew('screw_torso_m3x10_001', 'hex_2.5');
        expect(report.result).toBe(AdjudicationResult.BLOCKED);
        expect(report.reasonCode).toBe('HOST_NOT_INSTALLED');
        expect(report.reason).toContain('frame_torso_chest');
    });

    it('宿主零件在位时允许拧紧', () => {
        const report = canTightenScrew('screw_torso_m3x10_001', 'hex_2.5');
        expect(report.result).toBe(AdjudicationResult.ALLOWED);
    });

    it('工具不匹配时拧紧被拒', () => {
        const report = canTightenScrew('screw_torso_m3x10_001', 'hex_3');
        expect(report.result).toBe(AdjudicationResult.TOOL_MISMATCH);
    });

    it('未知螺丝被拒', () => {
        const report = canTightenScrew('screw_does_not_exist', 'hex_2.5');
        expect(report.result).toBe(AdjudicationResult.BLOCKED);
        expect(report.reasonCode).toBe('UNKNOWN_SCREW');
    });
});
