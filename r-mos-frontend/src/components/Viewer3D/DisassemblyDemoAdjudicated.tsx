/**
 * DisassemblyDemoAdjudicated.tsx - 裁决级拆卸动画演示组件
 * 
 * 功能：
 * - 展示工具飞入动画
 * - 螺丝旋转退出效果
 * - 零件分离演示
 * - **接入裁决引擎判定完成状态**
 * - **动画完成后调用裁决，裁决失败则回滚**
 * 
 * 符合规范：
 * - A.3 禁止通过动画结束直接标记完成
 * - 动画回调 → 裁决引擎判定 → 状态提交
 */

import { useRef, useState, useCallback } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import {
    adjudicateAction,
    validateScrewExtraction,
    commitScrewExtraction,
    AdjudicationResult,
    ActionType,
    AdjudicationReport,
    useAdjudicationStore,
} from '@/adjudication';

export interface DisassemblyDemoAdjudicatedProps {
    isPlaying: boolean;
    screwId: string;                           // 目标螺丝 ID
    toolId?: string;                           // 当前工具 ID
    onAdjudicationComplete?: (report: AdjudicationReport) => void;  // 裁决完成回调
    onAdjudicationBlocked?: (report: AdjudicationReport) => void;   // 裁决阻断回调
    onAnimationRollback?: () => void;          // 动画回滚回调
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

type AnimationPhase = 'idle' | 'precondition_check' | 'approach' | 'rotate' | 'detach' | 'adjudication' | 'complete' | 'blocked' | 'rollback';

export const DisassemblyDemoAdjudicated: React.FC<DisassemblyDemoAdjudicatedProps> = ({
    isPlaying,
    screwId,
    toolId,
    onAdjudicationComplete,
    onAdjudicationBlocked,
    onAnimationRollback,
    targetPosition = [0, 0, 0],
}) => {
    const groupRef = useRef<THREE.Group>(null);
    const [animationTime, setAnimationTime] = useState(0);
    const [phase, setPhase] = useState<AnimationPhase>('idle');
    const [lastReport, setLastReport] = useState<AdjudicationReport | null>(null);

    // 动画状态
    const toolPosition = useRef(new THREE.Vector3(0.1, 0.1, 0.1));
    const toolRotation = useRef(new THREE.Euler(0, 0, 0));
    const screwRotation = useRef(0);
    const screwOffset = useRef(0);

    // 保存初始状态用于回滚
    const initialState = useRef({
        toolPosition: new THREE.Vector3(0.1, 0.1, 0.1),
        screwRotation: 0,
        screwOffset: 0,
    });

    // 阶段时长
    const APPROACH_DURATION = 0.8;
    const ROTATE_DURATION = 2.0;
    const DETACH_DURATION = 0.5;
    const ROLLBACK_DURATION = 0.5;

    // 获取当前工具
    const currentToolId = useAdjudicationStore((state) => state.currentToolId);
    const effectiveToolId = toolId ?? currentToolId;

    /**
     * 前置条件检查
     * 规范 B.4：BLOCKED 时动画不得播放
     */
    const checkPreconditions = useCallback((): AdjudicationReport => {
        const report = adjudicateAction(ActionType.EXTRACT_SCREW, screwId, effectiveToolId);
        setLastReport(report);
        return report;
    }, [screwId, effectiveToolId]);

    /**
     * 动画完成后的裁决验证
     * 规范 A.3：禁止通过动画结束直接标记完成
     */
    const performAdjudication = useCallback((): AdjudicationReport => {
        // 验证螺丝是否真正退出
        const report = validateScrewExtraction(screwId);
        setLastReport(report);

        if (report.result === AdjudicationResult.ALLOWED) {
            // 裁决通过，提交状态变更
            commitScrewExtraction(screwId);
            onAdjudicationComplete?.(report);
        } else {
            // 裁决失败，触发回滚
            onAdjudicationBlocked?.(report);
        }

        return report;
    }, [screwId, onAdjudicationComplete, onAdjudicationBlocked]);

    /**
     * 执行回滚动画
     */
    const executeRollback = useCallback(() => {
        setPhase('rollback');
        setAnimationTime(0);
        onAnimationRollback?.();
    }, [onAnimationRollback]);

    useFrame((_, delta) => {
        if (!isPlaying && phase === 'idle') return;

        setAnimationTime(prev => prev + delta);

        const targetVec = new THREE.Vector3(...targetPosition);

        // 阶段0：前置条件检查
        if (phase === 'idle' && isPlaying) {
            setPhase('precondition_check');
            setAnimationTime(0);

            // 执行前置条件检查
            const report = checkPreconditions();

            if (report.result !== AdjudicationResult.ALLOWED) {
                // 前置条件不满足，阻断动画
                setPhase('blocked');
                onAdjudicationBlocked?.(report);
                return;
            }

            // 前置条件满足，保存初始状态用于回滚
            initialState.current = {
                toolPosition: toolPosition.current.clone(),
                screwRotation: screwRotation.current,
                screwOffset: screwOffset.current,
            };

            setPhase('approach');
            setAnimationTime(0);
        }

        // 阶段1：工具接近
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
                // 动画结束，进入裁决阶段
                setPhase('adjudication');
                setAnimationTime(0);

                // 执行裁决
                const report = performAdjudication();

                if (report.result === AdjudicationResult.ALLOWED) {
                    setPhase('complete');
                } else {
                    // 裁决失败，执行回滚
                    executeRollback();
                }
            }
        }

        // 阶段4：回滚动画
        else if (phase === 'rollback') {
            const progress = Math.min(animationTime / ROLLBACK_DURATION, 1);

            // 逐渐恢复到初始状态
            screwRotation.current = initialState.current.screwRotation * (1 - progress) + 0;
            screwOffset.current = initialState.current.screwOffset * (1 - progress) + 0;
            toolPosition.current.lerpVectors(
                toolPosition.current,
                initialState.current.toolPosition,
                easeOutCubic(progress)
            );

            if (progress >= 1) {
                setPhase('blocked');
            }
        }
    });

    // 重置动画
    if (!isPlaying && phase !== 'idle' && phase !== 'complete' && phase !== 'blocked') {
        setPhase('idle');
        setAnimationTime(0);
        toolPosition.current.set(0.1, 0.1, 0.1);
        toolRotation.current.set(0, 0, 0);
        screwRotation.current = 0;
        screwOffset.current = 0;
    }

    // 阻断状态显示红色
    const screwColor = phase === 'blocked' ? '#ff4444' : undefined;

    return (
        <group ref={groupRef}>
            {/* 螺丝 */}
            <group position={targetPosition as unknown as THREE.Vector3Tuple}>
                <Screw rotation={screwRotation.current} offset={screwOffset.current} />
                {screwColor && (
                    <mesh position={[0, 0, screwOffset.current + 0.015]}>
                        <sphereGeometry args={[0.005, 8, 8]} />
                        <meshBasicMaterial color={screwColor} transparent opacity={0.5} />
                    </mesh>
                )}
            </group>

            {/* 工具 */}
            {isPlaying && phase !== 'idle' && phase !== 'blocked' && phase !== 'complete' && (
                <HexKey
                    position={toolPosition.current}
                    rotation={toolRotation.current}
                />
            )}

            {/* 阻断提示（调试用） */}
            {phase === 'blocked' && lastReport && (
                <group position={[targetPosition[0], targetPosition[1] + 0.05, targetPosition[2]]}>
                    {/* 可以添加 3D 文字或图标显示阻断原因 */}
                </group>
            )}
        </group>
    );
};

// 缓动函数
function easeOutCubic(t: number): number {
    return 1 - Math.pow(1 - t, 3);
}

export default DisassemblyDemoAdjudicated;
