/**
 * 3D机器人模型组件
 */
import React, { useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import { JointState } from '@/types/robot';

interface RobotModelProps {
  joints: JointState[];
}

const Robot: React.FC<{ joints: JointState[] }> = ({ joints }) => {
  const groupRef = useRef<THREE.Group>(null);

  // 简化的机器人渲染（使用球体和圆柱体表示关节）
  return (
    <group ref={groupRef}>
      {joints.map((joint, index) => (
        <mesh key={joint.joint_id} position={[index * 2, 0, 0]}>
          <sphereGeometry args={[0.5, 32, 32]} />
          <meshStandardMaterial
            color={joint.error_code ? '#ff4d4f' : '#52c41a'}
          />
        </mesh>
      ))}
    </group>
  );
};

const RobotModel: React.FC<RobotModelProps> = ({ joints }) => {
  return (
    <Canvas camera={{ position: [5, 5, 5], fov: 50 }}>
      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} />
      <Robot joints={joints} />
      <OrbitControls />
    </Canvas>
  );
};

export default RobotModel;
