/**
 * DisassemblyDemoAdjudicated.tsx - 裁决级拆卸动画演示组件
 *
 * 功能：
 * - 展示工具飞入动画
 * - 螺丝旋转退出效果
 * - 零件分离演示
 * - 接入裁决引擎判定完成状态
 * - 动画完成后调用裁决，裁决失败则回滚
 */

import { useCallback, useRef, useState } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

import {
  ActionType,
  AdjudicationReport,
  AdjudicationResult,
  adjudicateAction,
  commitScrewExtraction,
  useAdjudicationStore,
  validateScrewExtraction,
} from '@/adjudication';

export interface DisassemblyDemoAdjudicatedProps {
  isPlaying: boolean;
  screwId: string;
  toolId?: string;
  onAdjudicationComplete?: (report: AdjudicationReport) => void;
  onAdjudicationBlocked?: (report: AdjudicationReport) => void;
  onAnimationRollback?: () => void;
  targetPosition?: [number, number, number];
}

const Screw: React.FC<{ rotation: number; offset: number }> = ({ rotation, offset }) => (
  <group position={[0, 0, offset]} rotation={[0, 0, rotation]}>
    <mesh position={[0, 0, 0.01]}>
      <cylinderGeometry args={[0.008, 0.008, 0.008, 6]} />
      <meshStandardMaterial color="#888888" metalness={0.8} roughness={0.2} />
    </mesh>
    <mesh position={[0, 0, -0.01]}>
      <cylinderGeometry args={[0.003, 0.003, 0.02, 8]} />
      <meshStandardMaterial color="#666666" metalness={0.9} roughness={0.1} />
    </mesh>
  </group>
);

const HexKey: React.FC<{ position: THREE.Vector3; rotation: THREE.Euler }> = ({
  position,
  rotation,
}) => (
  <group position={position} rotation={rotation}>
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

type AnimationPhase =
  | 'idle'
  | 'precondition_check'
  | 'approach'
  | 'rotate'
  | 'detach'
  | 'adjudication'
  | 'complete'
  | 'blocked'
  | 'rollback';

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

  const toolPosition = useRef(new THREE.Vector3(0.1, 0.1, 0.1));
  const toolRotation = useRef(new THREE.Euler(0, 0, 0));
  const screwRotation = useRef(0);
  const screwOffset = useRef(0);

  const initialState = useRef({
    toolPosition: new THREE.Vector3(0.1, 0.1, 0.1),
    screwRotation: 0,
    screwOffset: 0,
  });

  const APPROACH_DURATION = 0.8;
  const ROTATE_DURATION = 2.0;
  const DETACH_DURATION = 0.5;
  const ROLLBACK_DURATION = 0.5;

  const currentToolId = useAdjudicationStore((state) => state.currentToolId);
  const effectiveToolId = toolId ?? currentToolId ?? undefined;

  const checkPreconditions = useCallback((): AdjudicationReport => {
    const report = adjudicateAction(ActionType.EXTRACT_SCREW, screwId, effectiveToolId);
    setLastReport(report);
    return report;
  }, [effectiveToolId, screwId]);

  const performAdjudication = useCallback((): AdjudicationReport => {
    const report = validateScrewExtraction(screwId);
    setLastReport(report);

    if (report.result === AdjudicationResult.ALLOWED) {
      commitScrewExtraction(screwId);
      onAdjudicationComplete?.(report);
    } else {
      onAdjudicationBlocked?.(report);
    }

    return report;
  }, [onAdjudicationBlocked, onAdjudicationComplete, screwId]);

  const executeRollback = useCallback(() => {
    setPhase('rollback');
    setAnimationTime(0);
    onAnimationRollback?.();
  }, [onAnimationRollback]);

  useFrame((_, delta) => {
    if (!isPlaying && phase === 'idle') {
      return;
    }

    setAnimationTime((prev) => prev + delta);

    const targetVec = new THREE.Vector3(...targetPosition);

    if (phase === 'idle' && isPlaying) {
      setPhase('precondition_check');
      setAnimationTime(0);

      const report = checkPreconditions();
      if (report.result !== AdjudicationResult.ALLOWED) {
        setPhase('blocked');
        onAdjudicationBlocked?.(report);
        return;
      }

      initialState.current = {
        toolPosition: toolPosition.current.clone(),
        screwRotation: screwRotation.current,
        screwOffset: screwOffset.current,
      };

      setPhase('approach');
      setAnimationTime(0);
    } else if (phase === 'approach') {
      const progress = Math.min(animationTime / APPROACH_DURATION, 1);
      const startPos = new THREE.Vector3(0.1, 0.1, 0.1);
      toolPosition.current.lerpVectors(
        startPos,
        targetVec.clone().add(new THREE.Vector3(0, 0, 0.03)),
        easeOutCubic(progress),
      );
      toolRotation.current.x = -Math.PI / 2;
      toolRotation.current.y = progress * Math.PI / 4;

      if (progress >= 1) {
        setPhase('rotate');
        setAnimationTime(0);
      }
    } else if (phase === 'rotate') {
      const progress = Math.min(animationTime / ROTATE_DURATION, 1);
      screwRotation.current = progress * 6 * Math.PI;
      screwOffset.current = progress * 0.03;
      toolRotation.current.y = Math.PI / 4 + progress * 6 * Math.PI;
      toolPosition.current.z = targetVec.z + 0.03 + progress * 0.03;

      if (progress >= 1) {
        setPhase('detach');
        setAnimationTime(0);
      }
    } else if (phase === 'detach') {
      const progress = Math.min(animationTime / DETACH_DURATION, 1);
      screwOffset.current = 0.03 + progress * 0.05;
      toolPosition.current.z += delta * 0.1;

      if (progress >= 1) {
        setPhase('adjudication');
        setAnimationTime(0);

        const report = performAdjudication();
        if (report.result === AdjudicationResult.ALLOWED) {
          setPhase('complete');
        } else {
          executeRollback();
        }
      }
    } else if (phase === 'rollback') {
      const progress = Math.min(animationTime / ROLLBACK_DURATION, 1);
      screwRotation.current = initialState.current.screwRotation * (1 - progress);
      screwOffset.current = initialState.current.screwOffset * (1 - progress);
      toolPosition.current.lerpVectors(
        toolPosition.current,
        initialState.current.toolPosition,
        easeOutCubic(progress),
      );

      if (progress >= 1) {
        setPhase('blocked');
      }
    }
  });

  if (!isPlaying && phase !== 'idle' && phase !== 'complete' && phase !== 'blocked') {
    setPhase('idle');
    setAnimationTime(0);
    toolPosition.current.set(0.1, 0.1, 0.1);
    toolRotation.current.set(0, 0, 0);
    screwRotation.current = 0;
    screwOffset.current = 0;
  }

  const screwColor = phase === 'blocked' ? '#ff4444' : undefined;

  return (
    <group ref={groupRef}>
      <group position={targetPosition as unknown as THREE.Vector3Tuple}>
        <Screw rotation={screwRotation.current} offset={screwOffset.current} />
        {screwColor ? (
          <mesh position={[0, 0, screwOffset.current + 0.015]}>
            <sphereGeometry args={[0.005, 8, 8]} />
            <meshBasicMaterial color={screwColor} transparent opacity={0.5} />
          </mesh>
        ) : null}
      </group>

      {isPlaying &&
      phase !== 'idle' &&
      phase !== 'blocked' &&
      phase !== 'complete' ? (
        <HexKey
          position={toolPosition.current}
          rotation={toolRotation.current}
        />
      ) : null}

      {phase === 'blocked' && lastReport ? (
        <group position={[targetPosition[0], targetPosition[1] + 0.05, targetPosition[2]]} />
      ) : null}
    </group>
  );
};

function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}

export default DisassemblyDemoAdjudicated;
