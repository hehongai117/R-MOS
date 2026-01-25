/**
 * @description 状态管理器 - 使用 Zustand 管理全局状态
 * @module adjudication/core/stateManager
 * 
 * 基于规范文档 §5.1 系统状态定义
 */

import { create } from 'zustand';
import { devtools, persist, createJSONStorage } from 'zustand/middleware';
import {
    SystemState,
    ScrewState,
    PartState,
    ScrewInstanceState,
    ActionRecord,
    AdjudicationState,
    OperationMode,
} from '../types/adjudication';
import { getAllConstraints } from '../data/constraintGraph';
import { getAllScrewIds } from '../data/screwInstances';
import { getAllPartIds } from '../data/partRegistry';

// ============================================================
// Store 接口定义
// ============================================================

interface AdjudicationStore extends AdjudicationState {
    // === 状态变更函数 ===

    /** 设置螺丝状态 */
    setScrewState: (screwId: string, state: ScrewState, rotations?: number, displacement?: number) => void;

    /** 设置零件已移除 */
    setPartRemoved: (partId: string) => void;

    /** 设置零件已分离 */
    setPartDetached: (partId: string) => void;

    /** 设置当前工具 */
    setCurrentTool: (toolId: string | null) => void;

    /** 设置约束状态 */
    setConstraintActive: (constraintId: string, isActive: boolean) => void;

    /** 设置系统状态 */
    setSystemState: (state: SystemState) => void;

    /** 设置操作模式 */
    setOperationMode: (mode: OperationMode) => void;

    /** 添加操作记录 */
    addActionRecord: (record: Omit<ActionRecord, 'id' | 'timestamp' | 'stateSnapshot'>) => void;

    /** 重置到初始状态 */
    resetState: () => void;

    // === 查询函数 ===

    /** 获取螺丝状态 */
    getScrewState: (screwId: string) => ScrewInstanceState | undefined;

    /** 检查螺丝是否已完全退出 */
    isScrewExtracted: (screwId: string) => boolean;

    /** 检查零件是否已移除 */
    isPartRemoved: (partId: string) => boolean;

    /** 检查约束是否活跃 */
    isConstraintActive: (constraintId: string) => boolean;

    /** 获取操作历史 */
    getActionHistory: () => ActionRecord[];
}

type MemoryStorage = {
    getItem: (name: string) => string | null;
    setItem: (name: string, value: string) => void;
    removeItem: (name: string) => void;
};

function createMemoryStorage(): MemoryStorage {
    const store = new Map<string, string>();
    return {
        getItem: (name) => store.get(name) ?? null,
        setItem: (name, value) => {
            store.set(name, value);
        },
        removeItem: (name) => {
            store.delete(name);
        },
    };
}

function resolvePersistStorage() {
    const injected = (globalThis as any).__RMOS_PERSIST_STORAGE__;
    if (injected) {
        return injected;
    }
    if (typeof window !== 'undefined' && window.localStorage) {
        return createJSONStorage(() => window.localStorage);
    }
    return createJSONStorage(() => createMemoryStorage());
}

// ============================================================
// 初始状态
// ============================================================

function createInitialScrewStates(): Record<string, ScrewInstanceState> {
    const states: Record<string, ScrewInstanceState> = {};
    getAllScrewIds().forEach(id => {
        states[id] = {
            screwId: id,
            state: ScrewState.SEATED,
            currentRotations: 0,
            zDisplacement: 0,
        };
    });
    return states;
}

function createInitialPartStates(): Record<string, PartState> {
    const states: Record<string, PartState> = {};
    getAllPartIds().forEach(id => {
        states[id] = {
            isRemoved: false,
            isDetached: false,
        };
    });
    return states;
}

function createInitialConstraintStates(): Record<string, boolean> {
    const states: Record<string, boolean> = {};
    getAllConstraints().forEach(c => {
        states[c.id] = c.isActive;
    });
    return states;
}

const INITIAL_STATE: Omit<AdjudicationState, never> = {
    systemState: SystemState.FULLY_ASSEMBLED,
    operationMode: 'maintenance',
    partStates: createInitialPartStates(),
    screwStates: createInitialScrewStates(),
    constraintStates: createInitialConstraintStates(),
    currentToolId: null,
    actionHistory: [],
};

// ============================================================
// Zustand Store 创建
// ============================================================

export const useAdjudicationStore = create<AdjudicationStore>()(
    devtools(
        persist(
            (set, get) => ({
                // 初始状态
                ...INITIAL_STATE,

                // === 状态变更函数 ===

                setScrewState: (screwId, state, rotations, displacement) => {
                    set(
                        (prev) => ({
                            screwStates: {
                                ...prev.screwStates,
                                [screwId]: {
                                    ...prev.screwStates[screwId],
                                    screwId,
                                    state,
                                    currentRotations: rotations ?? prev.screwStates[screwId]?.currentRotations ?? 0,
                                    zDisplacement: displacement ?? prev.screwStates[screwId]?.zDisplacement ?? 0,
                                },
                            },
                        }),
                        false,
                        'setScrewState'
                    );
                },

                setPartRemoved: (partId) => {
                    set(
                        (prev) => ({
                            partStates: {
                                ...prev.partStates,
                                [partId]: {
                                    ...prev.partStates[partId],
                                    isRemoved: true,
                                    isDetached: true,
                                },
                            },
                        }),
                        false,
                        'setPartRemoved'
                    );
                },

                setPartDetached: (partId) => {
                    set(
                        (prev) => ({
                            partStates: {
                                ...prev.partStates,
                                [partId]: {
                                    ...prev.partStates[partId],
                                    isDetached: true,
                                },
                            },
                        }),
                        false,
                        'setPartDetached'
                    );
                },

                setCurrentTool: (toolId) => {
                    set({ currentToolId: toolId }, false, 'setCurrentTool');
                },

                setConstraintActive: (constraintId, isActive) => {
                    set(
                        (prev) => ({
                            constraintStates: {
                                ...prev.constraintStates,
                                [constraintId]: isActive,
                            },
                        }),
                        false,
                        'setConstraintActive'
                    );
                },

                setSystemState: (state) => {
                    set({ systemState: state }, false, 'setSystemState');
                },

                setOperationMode: (mode) => {
                    set({ operationMode: mode }, false, 'setOperationMode');
                },

                addActionRecord: (record) => {
                    const fullRecord: ActionRecord = {
                        id: `action_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
                        timestamp: Date.now(),
                        stateSnapshot: JSON.stringify({
                            systemState: get().systemState,
                            partStates: get().partStates,
                            screwStates: get().screwStates,
                            constraintStates: get().constraintStates,
                        }),
                        ...record,
                    };
                    set(
                        (prev) => ({
                            actionHistory: [...prev.actionHistory, fullRecord],
                        }),
                        false,
                        'addActionRecord'
                    );
                },

                resetState: () => {
                    set(INITIAL_STATE, false, 'resetState');
                },

                // === 查询函数 ===

                getScrewState: (screwId) => {
                    return get().screwStates[screwId];
                },

                isScrewExtracted: (screwId) => {
                    const state = get().screwStates[screwId];
                    return state?.state === ScrewState.EXTRACTED || state?.state === ScrewState.REMOVED;
                },

                isPartRemoved: (partId) => {
                    return get().partStates[partId]?.isRemoved ?? false;
                },

                isConstraintActive: (constraintId) => {
                    return get().constraintStates[constraintId] ?? false;
                },

                getActionHistory: () => {
                    return get().actionHistory;
                },
            }),
            {
                name: 'adjudication-storage',
                storage: resolvePersistStorage(),
                // 只持久化部分状态，排除操作历史（可能很大）
                partialize: (state) => ({
                    systemState: state.systemState,
                    currentToolId: state.currentToolId,
                    operationMode: state.operationMode,
                }),
            }
        ),
        { name: 'AdjudicationStore' }
    )
);

// ============================================================
// 便捷钩子
// ============================================================

/**
 * 获取当前系统状态
 */
export function useSystemState(): SystemState {
    return useAdjudicationStore((state) => state.systemState);
}

/**
 * 获取当前操作模式
 */
export function useOperationMode(): OperationMode {
    return useAdjudicationStore((state) => state.operationMode);
}

/**
 * 获取当前工具
 */
export function useCurrentTool(): string | null {
    return useAdjudicationStore((state) => state.currentToolId);
}

/**
 * 获取螺丝状态
 */
export function useScrewState(screwId: string): ScrewInstanceState | undefined {
    return useAdjudicationStore((state) => state.screwStates[screwId]);
}

/**
 * 获取零件状态
 */
export function usePartState(partId: string): PartState | undefined {
    return useAdjudicationStore((state) => state.partStates[partId]);
}

// ============================================================
// 非 React 环境访问
// ============================================================

/**
 * 获取当前状态快照（非 React 环境使用）
 */
export function getStateSnapshot(): AdjudicationState {
    return useAdjudicationStore.getState();
}

/**
 * 直接设置螺丝状态（非 React 环境使用）
 */
export function setScrewStateDirect(screwId: string, state: ScrewState, rotations?: number, displacement?: number): void {
    useAdjudicationStore.getState().setScrewState(screwId, state, rotations, displacement);
}

/**
 * 直接重置状态（非 React 环境使用）
 */
export function resetStateDirect(): void {
    useAdjudicationStore.getState().resetState();
}
