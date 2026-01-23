/**
 * useCameraFocus.ts - 摄像机聚焦 Hook
 * 
 * 功能：
 * - 平滑推进到目标位置
 * - 自动计算最佳观察视角
 */

import { useRef, useCallback } from 'react';
import { useThree, useFrame } from '@react-three/fiber';
import * as THREE from 'three';

export interface FocusTarget {
    position: [number, number, number];
    distance?: number;  // 观察距离，默认 0.8
}

// 零件聚焦位置配置（基于 URDF 坐标，Y-up 已转换）
export const PART_FOCUS_POSITIONS: Record<string, FocusTarget> = {
    'base_link': { position: [0, 0.1, 0], distance: 1.0 },
    'torso_link': { position: [0, 0.5, 0], distance: 0.8 },
    'left_arm_pitch_link': { position: [0.15, 0.55, 0], distance: 0.6 },
    'left_arm_roll_link': { position: [0.18, 0.6, 0], distance: 0.5 },
    'left_arm_yaw_link': { position: [0.2, 0.55, 0], distance: 0.5 },
    'left_elbow_pitch_link': { position: [0.25, 0.45, 0], distance: 0.5 },
    'left_elbow_yaw_link': { position: [0.3, 0.35, 0], distance: 0.5 },
    'right_arm_pitch_link': { position: [-0.15, 0.55, 0], distance: 0.6 },
    'right_arm_roll_link': { position: [-0.18, 0.6, 0], distance: 0.5 },
    'right_arm_yaw_link': { position: [-0.2, 0.55, 0], distance: 0.5 },
    'right_elbow_pitch_link': { position: [-0.25, 0.45, 0], distance: 0.5 },
    'right_elbow_yaw_link': { position: [-0.3, 0.35, 0], distance: 0.5 },
    'left_thigh_yaw_link': { position: [0.1, -0.1, 0], distance: 0.7 },
    'left_thigh_roll_link': { position: [0.1, -0.15, 0], distance: 0.6 },
    'left_thigh_pitch_link': { position: [0.1, -0.25, 0], distance: 0.6 },
    'left_knee_link': { position: [0.1, -0.45, 0], distance: 0.6 },
    'left_ankle_pitch_link': { position: [0.1, -0.7, 0], distance: 0.5 },
    'left_ankle_roll_link': { position: [0.1, -0.75, 0], distance: 0.5 },
    'right_thigh_yaw_link': { position: [-0.1, -0.1, 0], distance: 0.7 },
    'right_thigh_roll_link': { position: [-0.1, -0.15, 0], distance: 0.6 },
    'right_thigh_pitch_link': { position: [-0.1, -0.25, 0], distance: 0.6 },
    'right_knee_link': { position: [-0.1, -0.45, 0], distance: 0.6 },
    'right_ankle_pitch_link': { position: [-0.1, -0.7, 0], distance: 0.5 },
    'right_ankle_roll_link': { position: [-0.1, -0.75, 0], distance: 0.5 },
};

export interface UseCameraFocusOptions {
    smoothness?: number;  // 平滑度，0-1，默认 0.05
    defaultDistance?: number;
}

export function useCameraFocus(options: UseCameraFocusOptions = {}) {
    const { smoothness = 0.05, defaultDistance = 0.8 } = options;
    const { camera } = useThree();

    const targetPosition = useRef<THREE.Vector3 | null>(null);
    const targetLookAt = useRef<THREE.Vector3 | null>(null);
    const isAnimating = useRef(false);

    // 开始聚焦动画
    const focusOnPart = useCallback((partName: string) => {
        const focusConfig = PART_FOCUS_POSITIONS[partName];
        if (!focusConfig) return;

        const [x, y, z] = focusConfig.position;
        const distance = focusConfig.distance || defaultDistance;

        // 设置目标注视点
        targetLookAt.current = new THREE.Vector3(x, y, z);

        // 计算摄像机目标位置（从当前方向保持一定距离）
        const direction = new THREE.Vector3()
            .subVectors(camera.position, targetLookAt.current)
            .normalize();

        targetPosition.current = new THREE.Vector3()
            .addVectors(targetLookAt.current, direction.multiplyScalar(distance));

        isAnimating.current = true;
    }, [camera, defaultDistance]);

    // 重置视角
    const resetView = useCallback(() => {
        targetPosition.current = new THREE.Vector3(1.5, 1, 1.5);
        targetLookAt.current = new THREE.Vector3(0, 0.3, 0);
        isAnimating.current = true;
    }, []);

    // 动画帧更新
    useFrame(() => {
        if (!isAnimating.current) return;

        if (targetPosition.current && targetLookAt.current) {
            // 平滑插值摄像机位置
            camera.position.lerp(targetPosition.current, smoothness);

            // 计算当前注视方向并平滑过渡
            const currentLookAt = new THREE.Vector3();
            camera.getWorldDirection(currentLookAt);
            currentLookAt.add(camera.position);
            currentLookAt.lerp(targetLookAt.current, smoothness);
            camera.lookAt(targetLookAt.current);

            // 检查是否到达目标
            const positionDiff = camera.position.distanceTo(targetPosition.current);
            if (positionDiff < 0.01) {
                isAnimating.current = false;
            }
        }
    });

    return {
        focusOnPart,
        resetView,
        isAnimating: isAnimating.current,
    };
}

export default useCameraFocus;
