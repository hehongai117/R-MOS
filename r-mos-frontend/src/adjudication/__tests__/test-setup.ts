/**
 * @description 测试入口初始化：注入内存存储并设置标记
 */

import { createJSONStorage } from 'zustand/middleware';

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

const memoryStorage = createMemoryStorage();

(globalThis as any).__RMOS_PERSIST_STORAGE__ = createJSONStorage(() => memoryStorage);
(globalThis as any).__RMOS_TEST_STORAGE_READY__ = true;
