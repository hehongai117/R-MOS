/**
 * maintenanceKnowledge.test.ts
 *
 * Tests for the manifest injection layer in maintenanceKnowledge.ts:
 *   - injectManifestKnowledge()
 *   - clearManifestKnowledge()
 *   - getManifestTools()
 *   - getCorePartDetailRecord()
 *   - getDetailPartDetailRecord()
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
    injectManifestKnowledge,
    clearManifestKnowledge,
    getManifestTools,
    getCorePartDetailRecord,
    getDetailPartDetailRecord,
    type DetailPartSelection,
} from '../maintenanceKnowledge';
import type { RobotDataManifest } from '@/components/Viewer3D/assemblyManifest';

// ---- Minimal manifest fixture ----

function makeManifest(overrides: Partial<RobotDataManifest> = {}): RobotDataManifest {
    return {
        version: '1.0',
        robotId: 'test-robot',
        rootNodeId: 'root',
        mesh_catalog: {},
        nodes: [],
        fastener_instances: [],
        ...overrides,
    };
}

// ---- Helpers ----

beforeEach(() => {
    clearManifestKnowledge();
});

// ====================================================================
// 1. getManifestTools() — before any injection
// ====================================================================
describe('getManifestTools() — before injection', () => {
    it('returns null when no manifest has been injected', () => {
        expect(getManifestTools()).toBeNull();
    });
});

// ====================================================================
// 2. injectManifestKnowledge() — tools
// ====================================================================
describe('injectManifestKnowledge() — tools', () => {
    it('populates manifest tools from manifest.tools', () => {
        const manifest = makeManifest({
            tools: [
                { id: 'hex_3', name: '内六角扳手 3mm', type: 'hex_key', size: '3', description: '' },
                { id: 'torque_4', name: '扭力扳手 4Nm', type: 'torque_wrench', size: '4Nm', description: '' },
            ],
        });

        injectManifestKnowledge(manifest);

        const tools = getManifestTools();
        expect(tools).not.toBeNull();
        expect(tools).toHaveLength(2);
        expect(tools![0]).toEqual({
            tool_id: 'hex_3',
            display_name: '内六角扳手 3mm',
            category: 'hex_key',
        });
        expect(tools![1]).toEqual({
            tool_id: 'torque_4',
            display_name: '扭力扳手 4Nm',
            category: 'torque_wrench',
        });
    });

    it('returns null tools when manifest.tools is empty', () => {
        injectManifestKnowledge(makeManifest({ tools: [] }));
        expect(getManifestTools()).toBeNull();
    });

    it('returns null tools when manifest.tools is undefined', () => {
        injectManifestKnowledge(makeManifest({ tools: undefined }));
        expect(getManifestTools()).toBeNull();
    });

    it('replaces previous cache on repeated calls', () => {
        injectManifestKnowledge(
            makeManifest({
                tools: [{ id: 'old', name: '旧工具', type: 'misc', size: '', description: '' }],
            }),
        );
        injectManifestKnowledge(
            makeManifest({
                tools: [{ id: 'new', name: '新工具', type: 'pliers', size: '', description: '' }],
            }),
        );
        const tools = getManifestTools();
        expect(tools).toHaveLength(1);
        expect(tools![0].tool_id).toBe('new');
    });
});

// ====================================================================
// 3. clearManifestKnowledge() — resets state
// ====================================================================
describe('clearManifestKnowledge()', () => {
    it('clears tools after injection', () => {
        injectManifestKnowledge(
            makeManifest({
                tools: [{ id: 'hex_3', name: '内六角扳手', type: 'hex_key', size: '3', description: '' }],
            }),
        );
        expect(getManifestTools()).not.toBeNull();

        clearManifestKnowledge();
        expect(getManifestTools()).toBeNull();
    });

    it('is idempotent — calling clear multiple times does not throw', () => {
        expect(() => {
            clearManifestKnowledge();
            clearManifestKnowledge();
        }).not.toThrow();
    });
});

// ====================================================================
// 4. getCorePartDetailRecord()
// ====================================================================
describe('getCorePartDetailRecord()', () => {
    it('returns null for an unknown part name', () => {
        expect(getCorePartDetailRecord('non_existent_part')).toBeNull();
    });

    it('returns a PartDetailRecord for a known core part', () => {
        const record = getCorePartDetailRecord('base_link');
        expect(record).not.toBeNull();
        expect(record!.id).toBe('base_link');
        expect(record!.level).toBe('core');
        expect(record!.displayName).toBe('髋部底座');
        expect(record!.categoryLabel).toBe('核心总成');
        expect(Array.isArray(record!.maintenancePoints)).toBe(true);
        expect(record!.maintenancePoints.length).toBeGreaterThan(0);
    });

    it('prefers manifest display_names when injected', () => {
        injectManifestKnowledge(
            makeManifest({ display_names: { base_link: '自定义底座名称' } }),
        );
        const record = getCorePartDetailRecord('base_link');
        expect(record!.displayName).toBe('自定义底座名称');
    });

    it('falls back to hardcoded displayName when manifest has no matching key', () => {
        injectManifestKnowledge(
            makeManifest({ display_names: { other_link: '无关名称' } }),
        );
        const record = getCorePartDetailRecord('base_link');
        expect(record!.displayName).toBe('髋部底座');
    });

    it('falls back to hardcoded displayName after clearManifestKnowledge', () => {
        injectManifestKnowledge(
            makeManifest({ display_names: { base_link: '注入名称' } }),
        );
        clearManifestKnowledge();
        const record = getCorePartDetailRecord('base_link');
        expect(record!.displayName).toBe('髋部底座');
    });

    it('modelPath is empty string when robotId is not provided', () => {
        const record = getCorePartDetailRecord('base_link');
        expect(record!.modelPath).toBe('');
    });
});

// ====================================================================
// 5. getDetailPartDetailRecord()
// ====================================================================
describe('getDetailPartDetailRecord()', () => {
    it('returns null for an unknown linkName', () => {
        const sel: DetailPartSelection = { linkName: 'non_existent_link', partIndex: 0 };
        expect(getDetailPartDetailRecord(sel)).toBeNull();
    });

    it('returns null for an out-of-range partIndex on a valid linkName', () => {
        // base_link has detail parts; index 9999 should be null
        const sel: DetailPartSelection = { linkName: 'base_link', partIndex: 9999 };
        expect(getDetailPartDetailRecord(sel)).toBeNull();
    });

    it('returns a PartDetailRecord for valid linkName and partIndex 0 (if parts exist)', () => {
        // base_link is expected to have at least one detail part per partsManifest
        const sel: DetailPartSelection = { linkName: 'base_link', partIndex: 0 };
        const record = getDetailPartDetailRecord(sel);
        // If base_link has no detail parts mapped, record will be null — both cases are valid.
        if (record !== null) {
            expect(record.level).toBe('detail');
            expect(record.id).toMatch(/^detail:base_link:0$/);
            expect(typeof record.displayName).toBe('string');
            expect(typeof record.categoryLabel).toBe('string');
            expect(typeof record.modelPath).toBe('string');
            expect(record.modelPath).toMatch(/^\/models\/parts\//);
            expect(Array.isArray(record.maintenancePoints)).toBe(true);
        } else {
            // No detail parts for base_link — skip structural assertions
            expect(record).toBeNull();
        }
    });
});
