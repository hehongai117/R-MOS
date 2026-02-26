/**
 * DisassemblyAnimation.tsx - 序列拆卸动画组件
 *
 * 时间轴驱动：
 *   Phase 1 — 螺丝依次旋转抽离（使用真实 GLB 模型）
 *   Phase 2 — 零部件依次从本体分离
 *
 * 替代旧版 DisassemblyDemoAdjudicated 的微小几何体方案。
 */

import React, { useState, useRef, useMemo, useCallback, Suspense } from 'react';
import { useFrame } from '@react-three/fiber';
import { useGLTF } from '@react-three/drei';
import * as THREE from 'three';

import {
    SCREW_SEQUENCE,
    PART_SEQUENCE,
    ANIM_TIMING,
    getScrewProgress,
    getPartProgress,
    getTotalDuration,
    type ScrewAnimConfig,
} from './disassemblyConfig';

// ============================================================
// 单颗螺丝 GLB 渲染
// ============================================================

const PARTS_BASE = '/models/parts';

const ScrewModel: React.FC<{
    config: ScrewAnimConfig;
    progress: number; // -1=未开始, 0~1=动画中
}> = ({ config, progress }) => {
    const { scene } = useGLTF(`${PARTS_BASE}/${config.glbPath}`);

    const clonedScene = useMemo(() => {
        const cloned = scene.clone();
        cloned.traverse((child) => {
            if ((child as THREE.Mesh).isMesh) {
                const mesh = child as THREE.Mesh;
                mesh.material = new THREE.MeshStandardMaterial({
                    color: '#b0b0b0',
                    metalness: 0.85,
                    roughness: 0.15,
                });
            }
        });
        return cloned;
    }, [scene]);

    // 未开始 → 待在原位
    const effectiveProgress = progress < 0 ? 0 : progress;

    // 旋转 + 沿轴抽离
    const rotation = effectiveProgress * config.rotations * Math.PI * 2;
    const offset = effectiveProgress * config.extractDistance;

    // 已完全抽出 → 小缩放淡出
    const scale = progress >= 1 ? Math.max(0, 1 - (progress - 1) * 5) : 1;
    const visible = scale > 0.01;

    // 计算位移（沿 axis 方向）
    const pos: [number, number, number] = [
        config.position[0] + config.axis[0] * offset,
        config.position[1] + config.axis[1] * offset,
        config.position[2] + config.axis[2] * offset,
    ];

    if (!visible) return null;

    return (
        <group position={pos} scale={scale}>
            <group rotation={[0, 0, rotation]}>
                <primitive object={clonedScene} />
            </group>
        </group>
    );
};

// ============================================================
// 动画主组件
// ============================================================

export interface DisassemblyAnimationProps {
    /** 是否播放 */
    isPlaying: boolean;
    /** 演示模式（目前默认 true） */
    demoMode?: boolean;
    /** 动画完成回调 */
    onComplete?: () => void;
    /** 当前播放进度回调 (0~1) */
    onProgress?: (progress: number) => void;
    /** 当前正在拆的零件名回调 */
    onCurrentStep?: (label: string) => void;
    /** Phase 2 驱动父组件的 explodeAmount (0~1) */
    onExplodeAmountChange?: (amount: number) => void;
}

export const DisassemblyAnimation: React.FC<DisassemblyAnimationProps> = ({
    isPlaying,
    onComplete,
    onProgress,
    onCurrentStep,
    onExplodeAmountChange,
}) => {
    const globalTimeRef = useRef(0);
    const [, forceUpdate] = useState(0);
    const completedRef = useRef(false);
    const totalDuration = useMemo(() => getTotalDuration(), []);

    // 重置
    const reset = useCallback(() => {
        globalTimeRef.current = 0;
        completedRef.current = false;
        onExplodeAmountChange?.(0);
    }, [onExplodeAmountChange]);

    // 停止时重置
    if (!isPlaying && globalTimeRef.current > 0) {
        reset();
    }

    useFrame((_, delta) => {
        if (!isPlaying) return;

        globalTimeRef.current += delta;
        const t = globalTimeRef.current;

        // 更新进度
        const progress = Math.min(t / totalDuration, 1);
        onProgress?.(progress);

        // 计算当前步骤标签 + 驱动 explodeAmount
        const screwPhaseEnd =
            SCREW_SEQUENCE.length * (ANIM_TIMING.SCREW_DURATION + ANIM_TIMING.SCREW_GAP);

        if (t < screwPhaseEnd) {
            // Phase 1: 螺丝
            const screwIdx = Math.floor(t / (ANIM_TIMING.SCREW_DURATION + ANIM_TIMING.SCREW_GAP));
            if (screwIdx < SCREW_SEQUENCE.length) {
                onCurrentStep?.(`🔩 ${SCREW_SEQUENCE[screwIdx].label}`);
            }
            onExplodeAmountChange?.(0); // 螺丝阶段保持不爆炸
        } else if (t < screwPhaseEnd + ANIM_TIMING.PHASE_GAP) {
            // 过渡
            onCurrentStep?.('⏳ 准备分离零件...');
            onExplodeAmountChange?.(0);
        } else {
            // Phase 2: 零件分离 — 线性增加 explodeAmount
            const partPhaseStart = screwPhaseEnd + ANIM_TIMING.PHASE_GAP;
            const partPhaseTotal =
                PART_SEQUENCE.length * (ANIM_TIMING.PART_DURATION + ANIM_TIMING.PART_GAP);
            const partTime = t - partPhaseStart;
            const explodeProgress = easeOutCubic(Math.min(partTime / partPhaseTotal, 1));

            onExplodeAmountChange?.(explodeProgress);

            const partIdx = Math.floor(partTime / (ANIM_TIMING.PART_DURATION + ANIM_TIMING.PART_GAP));
            if (partIdx < PART_SEQUENCE.length) {
                onCurrentStep?.(`📦 分离 ${PART_SEQUENCE[partIdx].label}`);
            }
        }

        // 完成
        if (progress >= 1 && !completedRef.current) {
            completedRef.current = true;
            onCurrentStep?.('✅ 拆卸完成');
            onComplete?.();
        }

        // 触发重渲染
        forceUpdate((v) => v + 1);
    });

    if (!isPlaying && globalTimeRef.current === 0) {
        return null; // 未播放时不渲染螺丝
    }

    const t = globalTimeRef.current;

    return (
        <group>
            {/* Phase 1: 螺丝依次抽离 */}
            {SCREW_SEQUENCE.map((screw, i) => {
                const progress = getScrewProgress(t, i);
                return (
                    <Suspense key={screw.id} fallback={null}>
                        <ScrewModel config={screw} progress={progress} />
                    </Suspense>
                );
            })}

            {/* Phase 2: 零件分离 — 通过 partOffsets 传递给父组件 */}
            {/* 零件分离由 Atom01Interactive 的 explodeAmount 机制驱动 */}
            {/* 这里不直接移动 link，而是通过回调通知父组件更新 */}
        </group>
    );
};

/**
 * 获取零件分离偏移量（供 Atom01Interactive 使用）
 * 在播放动画时，计算每个 link 当前应该的实际偏移
 */
export function getPartOffsets(
    globalTime: number,
    isPlaying: boolean,
): Record<string, [number, number, number]> {
    if (!isPlaying || globalTime <= 0) return {};

    const offsets: Record<string, [number, number, number]> = {};

    PART_SEQUENCE.forEach((part, i) => {
        const progress = getPartProgress(globalTime, i);
        if (progress <= 0) return;

        const eased = easeOutCubic(Math.min(progress, 1));
        offsets[part.linkName] = [
            part.detachOffset[0] * eased,
            part.detachOffset[1] * eased,
            part.detachOffset[2] * eased,
        ];
    });

    return offsets;
}

function easeOutCubic(t: number): number {
    return 1 - Math.pow(1 - t, 3);
}

export default DisassemblyAnimation;
