/**
 * useDisassemblyAnimation.ts - 拆卸动画 Hook
 * 
 * 功能：
 * - 工具飞入对齐动画
 * - 螺丝旋转退出动画
 * - 零件分离动画
 */

import { useRef, useCallback, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

// 动画状态枚举
export type AnimationState = 'idle' | 'tool_approach' | 'screw_rotate' | 'part_detach' | 'complete';

// 动画配置
export interface DisassemblyAnimationConfig {
    toolApproachDuration: number;  // 工具接近时间(秒)
    screwRotateDuration: number;   // 螺丝旋转时间(秒)
    screwRotations: number;        // 螺丝旋转圈数
    partDetachDuration: number;    // 零件分离时间(秒)
    partDetachDistance: number;    // 零件分离距离
}

const DEFAULT_CONFIG: DisassemblyAnimationConfig = {
    toolApproachDuration: 0.8,
    screwRotateDuration: 1.5,
    screwRotations: 3,
    partDetachDuration: 0.5,
    partDetachDistance: 0.1,
};

export interface DisassemblyAnimationResult {
    state: AnimationState;
    progress: number;              // 当前动画进度 0-1
    toolPosition: THREE.Vector3;
    toolRotation: THREE.Euler;
    screwRotation: number;
    partOffset: THREE.Vector3;
    startAnimation: (targetPosition: THREE.Vector3) => void;
    stopAnimation: () => void;
    resetAnimation: () => void;
}

export function useDisassemblyAnimation(
    config: Partial<DisassemblyAnimationConfig> = {}
): DisassemblyAnimationResult {
    const mergedConfig = { ...DEFAULT_CONFIG, ...config };

    const [state, setState] = useState<AnimationState>('idle');
    const [progress, setProgress] = useState(0);

    const animationRef = useRef({
        startTime: 0,
        targetPosition: new THREE.Vector3(0, 0, 0),
        initialToolPosition: new THREE.Vector3(0.5, 0.5, 0.5),
        isRunning: false,
    });

    const toolPosition = useRef(new THREE.Vector3(0.5, 0.5, 0.5));
    const toolRotation = useRef(new THREE.Euler(0, 0, 0));
    const screwRotation = useRef(0);
    const partOffset = useRef(new THREE.Vector3(0, 0, 0));

    // 开始动画
    const startAnimation = useCallback((targetPosition: THREE.Vector3) => {
        animationRef.current.startTime = 0;
        animationRef.current.targetPosition = targetPosition.clone();
        animationRef.current.initialToolPosition = toolPosition.current.clone();
        animationRef.current.isRunning = true;
        setState('tool_approach');
        setProgress(0);
    }, []);

    // 停止动画
    const stopAnimation = useCallback(() => {
        animationRef.current.isRunning = false;
        setState('idle');
    }, []);

    // 重置动画
    const resetAnimation = useCallback(() => {
        animationRef.current.isRunning = false;
        setState('idle');
        setProgress(0);
        toolPosition.current.set(0.5, 0.5, 0.5);
        toolRotation.current.set(0, 0, 0);
        screwRotation.current = 0;
        partOffset.current.set(0, 0, 0);
    }, []);

    // 动画帧更新
    useFrame((_, delta) => {
        if (!animationRef.current.isRunning) return;

        animationRef.current.startTime += delta;
        const elapsed = animationRef.current.startTime;

        const {
            toolApproachDuration,
            screwRotateDuration,
            screwRotations,
            partDetachDuration,
            partDetachDistance,
        } = mergedConfig;

        // 阶段1：工具接近
        if (state === 'tool_approach') {
            const phaseProgress = Math.min(elapsed / toolApproachDuration, 1);
            setProgress(phaseProgress * 0.25);  // 0-25%

            // 平滑移动工具到目标位置
            toolPosition.current.lerpVectors(
                animationRef.current.initialToolPosition,
                animationRef.current.targetPosition,
                easeOutCubic(phaseProgress)
            );

            // 工具旋转对齐
            toolRotation.current.z = phaseProgress * Math.PI / 4;

            if (phaseProgress >= 1) {
                setState('screw_rotate');
                animationRef.current.startTime = 0;
            }
        }

        // 阶段2：螺丝旋转
        else if (state === 'screw_rotate') {
            const phaseProgress = Math.min(elapsed / screwRotateDuration, 1);
            setProgress(0.25 + phaseProgress * 0.5);  // 25-75%

            // 螺丝逆时针旋转
            screwRotation.current = phaseProgress * screwRotations * Math.PI * 2;

            // 螺丝逐渐退出
            partOffset.current.z = phaseProgress * 0.02;

            // 工具跟随旋转
            toolRotation.current.z = Math.PI / 4 + phaseProgress * screwRotations * Math.PI * 2;

            if (phaseProgress >= 1) {
                setState('part_detach');
                animationRef.current.startTime = 0;
            }
        }

        // 阶段3：零件分离
        else if (state === 'part_detach') {
            const phaseProgress = Math.min(elapsed / partDetachDuration, 1);
            setProgress(0.75 + phaseProgress * 0.25);  // 75-100%

            // 零件向外移动
            partOffset.current.z = 0.02 + phaseProgress * partDetachDistance;

            // 工具退回
            toolPosition.current.z += delta * 0.2;

            if (phaseProgress >= 1) {
                setState('complete');
                animationRef.current.isRunning = false;
                setProgress(1);
            }
        }
    });

    return {
        state,
        progress,
        toolPosition: toolPosition.current,
        toolRotation: toolRotation.current,
        screwRotation: screwRotation.current,
        partOffset: partOffset.current,
        startAnimation,
        stopAnimation,
        resetAnimation,
    };
}

// 缓动函数
function easeOutCubic(t: number): number {
    return 1 - Math.pow(1 - t, 3);
}

export default useDisassemblyAnimation;
