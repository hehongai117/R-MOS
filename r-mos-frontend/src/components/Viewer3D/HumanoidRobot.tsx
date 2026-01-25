/**
 * 人形机器人 3D 模型组件
 * 
 * 使用占位符几何体渲染人形机器人骨骼结构，
 * 支持关节角度动画和故障状态高亮。
 */
import React, { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import {
    BODY_DIMENSIONS,
    MATERIALS,
    ANIMATION_CONFIG,
} from './constants';
import { JointState } from '@/types/robot';

interface HumanoidRobotProps {
    /** 关节状态数组 */
    joints: JointState[];
    /** 是否显示关节标签 */
    showLabels?: boolean;
    /** 是否高亮故障关节 */
    highlightFaults?: boolean;
    /** 动画速度倍率 */
    animationSpeed?: number;
}

// 关节角度缓存，用于平滑插值
const jointAngles: Record<string, number> = {};

/**
 * 创建占位符几何体
 */
const createPlaceholderGeometry = (partName: string): THREE.BufferGeometry => {
    const dims = BODY_DIMENSIONS[partName];
    if (!dims) {
        return new THREE.SphereGeometry(0.05, 16, 16);
    }

    switch (dims.type) {
        case 'sphere':
            return new THREE.SphereGeometry(dims.radius || 0.1, 24, 24);
        case 'box':
            return new THREE.BoxGeometry(
                dims.width || 0.3,
                dims.height || 0.3,
                dims.depth || 0.2
            );
        case 'cylinder':
            return new THREE.CylinderGeometry(
                dims.radiusTop || 0.05,
                dims.radiusBottom || 0.05,
                dims.cylinderHeight || 0.3,
                16
            );
        default:
            return new THREE.SphereGeometry(0.05, 16, 16);
    }
};

/**
 * 单个身体部件组件
 */
const BodyPart: React.FC<{
    name: string;
    hasFault?: boolean;
    children?: React.ReactNode;
}> = ({ name, hasFault = false, children }) => {
    const meshRef = useRef<THREE.Mesh>(null);
    const dims = BODY_DIMENSIONS[name];

    const geometry = useMemo(() => createPlaceholderGeometry(name), [name]);

    const materialProps = hasFault ? MATERIALS.fault : MATERIALS.normal;

    // 故障闪烁动画
    useFrame(({ clock }) => {
        if (hasFault && meshRef.current) {
            const material = meshRef.current.material as THREE.MeshStandardMaterial;
            const blink = Math.sin(clock.elapsedTime * (1000 / ANIMATION_CONFIG.faultBlinkRate) * Math.PI) > 0;
            material.emissiveIntensity = blink ? 0.5 : 0.1;
        }
    });

    const position = dims?.position || [0, 0, 0];

    return (
        <group position={position as [number, number, number]}>
            <mesh ref={meshRef} geometry={geometry} castShadow receiveShadow>
                <meshStandardMaterial
                    color={materialProps.color}
                    metalness={'metalness' in materialProps ? materialProps.metalness : 0.4}
                    roughness={'roughness' in materialProps ? materialProps.roughness : 0.6}
                    emissive={'emissive' in materialProps ? materialProps.emissive : undefined}
                    emissiveIntensity={'emissiveIntensity' in materialProps ? materialProps.emissiveIntensity : 0}
                />
            </mesh>
            {children}
        </group>
    );
};

/**
 * 关节球组件
 */
const JointSphere: React.FC<{
    jointId: string;
    hasFault?: boolean;
}> = ({ jointId: _jointId, hasFault = false }) => {
    const materialProps = hasFault ? MATERIALS.fault : MATERIALS.joint;

    return (
        <mesh castShadow>
            <sphereGeometry args={[0.03, 16, 16]} />
            <meshStandardMaterial
                color={materialProps.color}
                metalness={0.7}
                roughness={0.3}
                emissive={'emissive' in materialProps ? materialProps.emissive : undefined}
                emissiveIntensity={'emissiveIntensity' in materialProps ? materialProps.emissiveIntensity : 0}
            />
        </mesh>
    );
};

/**
 * 可旋转的关节组件
 */
const RotatableJoint: React.FC<{
    jointId: string;
    joints: JointState[];
    axis: 'x' | 'y' | 'z';
    children: React.ReactNode;
}> = ({ jointId, joints, axis, children }) => {
    const groupRef = useRef<THREE.Group>(null);

    useFrame(() => {
        if (!groupRef.current) return;

        const jointState = joints.find(j => j.joint_id === jointId);
        const targetAngle = jointState?.position || 0;
        const targetRad = THREE.MathUtils.degToRad(targetAngle);

        // 平滑插值
        const currentAngle = jointAngles[jointId] || 0;
        const smoothedAngle = THREE.MathUtils.lerp(
            currentAngle,
            targetRad,
            ANIMATION_CONFIG.enableSmoothing ? 0.1 : 1
        );
        jointAngles[jointId] = smoothedAngle;

        // 应用旋转
        switch (axis) {
            case 'x':
                groupRef.current.rotation.x = smoothedAngle;
                break;
            case 'y':
                groupRef.current.rotation.y = smoothedAngle;
                break;
            case 'z':
                groupRef.current.rotation.z = smoothedAngle;
                break;
        }
    });

    return <group ref={groupRef}>{children}</group>;
};

/**
 * 人形机器人主组件
 */
const HumanoidRobot: React.FC<HumanoidRobotProps> = ({
    joints,
    showLabels: _showLabels = false,
    highlightFaults = true,
}) => {
    // 检查关节是否有故障
    const hasFault = (jointId: string): boolean => {
        if (!highlightFaults) return false;
        const joint = joints.find(j => j.joint_id === jointId);
        return !!joint?.error_code;
    };

    return (
        <group>
            {/* 躯干 */}
            <BodyPart name="torso">
                {/* 头部 - J1 */}
                <group position={[0, 0.35, 0]}>
                    <JointSphere jointId="J1" hasFault={hasFault('J1')} />
                    <RotatableJoint jointId="J1" joints={joints} axis="y">
                        <BodyPart name="head" hasFault={hasFault('J1')} />
                    </RotatableJoint>
                </group>

                {/* 左臂 */}
                <group position={[-0.22, 0.2, 0]}>
                    {/* 左肩 - J2 */}
                    <JointSphere jointId="J2" hasFault={hasFault('J2')} />
                    <RotatableJoint jointId="J2" joints={joints} axis="z">
                        <BodyPart name="upper_arm_left" hasFault={hasFault('J2')}>
                            {/* 左肘 - J3 */}
                            <group position={[0, -0.16, 0]}>
                                <JointSphere jointId="J3" hasFault={hasFault('J3')} />
                                <RotatableJoint jointId="J3" joints={joints} axis="x">
                                    <BodyPart name="forearm_left" hasFault={hasFault('J3')} />
                                </RotatableJoint>
                            </group>
                        </BodyPart>
                    </RotatableJoint>
                </group>

                {/* 右臂 */}
                <group position={[0.22, 0.2, 0]}>
                    {/* 右肩 - J4 */}
                    <JointSphere jointId="J4" hasFault={hasFault('J4')} />
                    <RotatableJoint jointId="J4" joints={joints} axis="z">
                        <BodyPart name="upper_arm_right" hasFault={hasFault('J4')}>
                            {/* 右肘 - J5 */}
                            <group position={[0, -0.16, 0]}>
                                <JointSphere jointId="J5" hasFault={hasFault('J5')} />
                                <RotatableJoint jointId="J5" joints={joints} axis="x">
                                    <BodyPart name="forearm_right" hasFault={hasFault('J5')} />
                                </RotatableJoint>
                            </group>
                        </BodyPart>
                    </RotatableJoint>
                </group>

                {/* 左腿 */}
                <group position={[-0.1, -0.3, 0]}>
                    {/* 左髋 - J6 */}
                    <JointSphere jointId="J6" hasFault={hasFault('J6')} />
                    <RotatableJoint jointId="J6" joints={joints} axis="x">
                        <BodyPart name="thigh_left" hasFault={hasFault('J6')}>
                            {/* 左膝 - J7 */}
                            <group position={[0, -0.22, 0]}>
                                <JointSphere jointId="J7" hasFault={hasFault('J7')} />
                                <RotatableJoint jointId="J7" joints={joints} axis="x">
                                    <BodyPart name="calf_left" hasFault={hasFault('J7')} />
                                </RotatableJoint>
                            </group>
                        </BodyPart>
                    </RotatableJoint>
                </group>

                {/* 右腿 */}
                <group position={[0.1, -0.3, 0]}>
                    {/* 右髋 - J8 */}
                    <JointSphere jointId="J8" hasFault={hasFault('J8')} />
                    <RotatableJoint jointId="J8" joints={joints} axis="x">
                        <BodyPart name="thigh_right" hasFault={hasFault('J8')}>
                            {/* 右膝 - J9 */}
                            <group position={[0, -0.22, 0]}>
                                <JointSphere jointId="J9" hasFault={hasFault('J9')} />
                                <RotatableJoint jointId="J9" joints={joints} axis="x">
                                    <BodyPart name="calf_right" hasFault={hasFault('J9')} />
                                </RotatableJoint>
                            </group>
                        </BodyPart>
                    </RotatableJoint>
                </group>
            </BodyPart>
        </group>
    );
};

export default HumanoidRobot;
