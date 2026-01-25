/**
 * CameraController.tsx - 摄像机控制器组件
 * 
 * 功能：
 * - 双击聚焦到零件
 * - 平滑动画过渡
 * - 重置视角
 */

import { useEffect, forwardRef, useImperativeHandle } from 'react';
import { useCameraFocus } from '@/hooks/useCameraFocus';

export interface CameraControllerRef {
    focusOnPart: (partName: string) => void;
    resetView: () => void;
}

export interface CameraControllerProps {
    focusTarget?: string | null;  // 当此值变化时自动聚焦
}

export const CameraController = forwardRef<CameraControllerRef, CameraControllerProps>(
    ({ focusTarget }, ref) => {
        const { focusOnPart, resetView } = useCameraFocus({
            smoothness: 0.08,
            defaultDistance: 0.8,
        });

        // 暴露方法给父组件
        useImperativeHandle(ref, () => ({
            focusOnPart,
            resetView,
        }));

        // 当 focusTarget 变化时自动聚焦
        useEffect(() => {
            if (focusTarget) {
                focusOnPart(focusTarget);
            }
        }, [focusTarget, focusOnPart]);

        return null; // 这是一个无渲染组件
    }
);

CameraController.displayName = 'CameraController';

export default CameraController;
