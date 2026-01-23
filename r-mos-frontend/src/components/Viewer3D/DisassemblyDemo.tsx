/**
 * DisassemblyDemo.tsx - 拆卸动画演示组件
 * 
 * 功能：
 * - 展示工具飞入动画
 * - 螺丝旋转退出效果
 * - 零件分离演示
 */

import { useRef, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

export interface DisassemblyDemoProps {
    isPlaying: boolean;
    onComplete?: () => void;
    targetPosition?: [number, number, number];
}

// 简化的螺丝模型
const Screw: React.FC<{ rotation: number; offset: number }> = ({ rotation, offset }) => {
    return (
        <group position={[0, 0, offset]} rotation={[0, 0, rotation]}>
            {/* 螺丝头 */}
            <mesh position={[0, 0, 0.01]}>
                <cylinderGeometry args={[0.008, 0.008, 0.008, 6]} />
                <meshStandardMaterial color="#888888" metalness={0.8} roughness={0.2} />
            </mesh>
            {/* 螺丝杆 */}
            <mesh position={[0, 0, -0.01]}>
                <cylinderGeometry args={[0.003, 0.003, 0.02, 8]} />
                <meshStandardMaterial color="#666666" metalness={0.9} roughness={0.1} />
            </mesh>
        </group>
    );
};

// 简化的内六角扳手模型
const HexKey: React.FC<{ position: THREE.Vector3; rotation: THREE.Euler }> = ({ position, rotation }) => {
    return (
        <group position={position} rotation={rotation}>
            {/* L 形扳手 */}
            <mesh position={[0, 0, 0]}>
                <boxGeometry args={[0.004, 0.004, 0.05]} />
                <meshStandardMaterial color="#333333" metalness={0.7} roughness={0.3} />
            </mesh>
            <mesh position={[0.015, 0, 0.023]} rotation={[0, 0, Math.PI / 2]}>
                <boxGeometry args={[0.004, 0.004, 0.03]} />
                <meshStandardMaterial color="#333333" metalness={0.7} roughness={0.3} />
            </mesh>
        </group>
    );
};

export const DisassemblyDemo: React.FC<DisassemblyDemoProps> = ({
    isPlaying,
    onComplete,
    targetPosition = [0, 0, 0],
}) => {
    const groupRef = useRef<THREE.Group>(null);
    const [animationTime, setAnimationTime] = useState(0);
    const [phase, setPhase] = useState<'idle' | 'approach' | 'rotate' | 'detach' | 'complete'>('idle');

    // 动画状态
    const toolPosition = useRef(new THREE.Vector3(0.1, 0.1, 0.1));
    const toolRotation = useRef(new THREE.Euler(0, 0, 0));
    const screwRotation = useRef(0);
    const screwOffset = useRef(0);

    // 阶段时长
    const APPROACH_DURATION = 0.8;
    const ROTATE_DURATION = 2.0;
    const DETACH_DURATION = 0.5;

    useFrame((_, delta) => {
        if (!isPlaying || phase === 'complete') return;

        setAnimationTime(prev => prev + delta);

        const targetVec = new THREE.Vector3(...targetPosition);

        // 阶段1：工具接近
        if (phase === 'idle') {
            setPhase('approach');
            setAnimationTime(0);
        }
        else if (phase === 'approach') {
            const progress = Math.min(animationTime / APPROACH_DURATION, 1);

            // 工具平滑移动到螺丝位置
            const startPos = new THREE.Vector3(0.1, 0.1, 0.1);
            toolPosition.current.lerpVectors(startPos, targetVec.clone().add(new THREE.Vector3(0, 0, 0.03)), easeOutCubic(progress));

            // 工具旋转对齐
            toolRotation.current.x = -Math.PI / 2;
            toolRotation.current.y = progress * Math.PI / 4;

            if (progress >= 1) {
                setPhase('rotate');
                setAnimationTime(0);
            }
        }
        // 阶段2：螺丝旋转退出
        else if (phase === 'rotate') {
            const progress = Math.min(animationTime / ROTATE_DURATION, 1);

            // 螺丝逆时针旋转 (3圈)
            screwRotation.current = progress * 6 * Math.PI;

            // 螺丝逐渐退出
            screwOffset.current = progress * 0.03;

            // 工具跟随旋转
            toolRotation.current.y = Math.PI / 4 + progress * 6 * Math.PI;
            toolPosition.current.z = targetVec.z + 0.03 + progress * 0.03;

            if (progress >= 1) {
                setPhase('detach');
                setAnimationTime(0);
            }
        }
        // 阶段3：完全分离
        else if (phase === 'detach') {
            const progress = Math.min(animationTime / DETACH_DURATION, 1);

            // 螺丝继续退出
            screwOffset.current = 0.03 + progress * 0.05;

            // 工具退回
            toolPosition.current.z += delta * 0.1;

            if (progress >= 1) {
                setPhase('complete');
                onComplete?.();
            }
        }
    });

    // 重置动画
    if (!isPlaying && phase !== 'idle') {
        setPhase('idle');
        setAnimationTime(0);
        toolPosition.current.set(0.1, 0.1, 0.1);
        toolRotation.current.set(0, 0, 0);
        screwRotation.current = 0;
        screwOffset.current = 0;
    }

    return (
        <group ref={groupRef}>
            {/* 螺丝 */}
            <group position={targetPosition as unknown as THREE.Vector3Tuple}>
                <Screw rotation={screwRotation.current} offset={screwOffset.current} />
            </group>

            {/* 工具 */}
            {isPlaying && phase !== 'idle' && (
                <HexKey
                    position={toolPosition.current}
                    rotation={toolRotation.current}
                />
            )}
        </group>
    );
};

// 缓动函数
function easeOutCubic(t: number): number {
    return 1 - Math.pow(1 - t, 3);
}

export default DisassemblyDemo;
