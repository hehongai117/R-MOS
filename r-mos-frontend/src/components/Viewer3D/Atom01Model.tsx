/**
 * Atom01Model.tsx - Atom01 机器人 3D 模型组件
 * 
 * 基于 URDF 定义的关节层级结构，加载并组装 GLB 模型
 * 支持关节角度动画和故障高亮
 * 
 * 坐标系说明：
 * - URDF 和 STL 文件使用 Z-up 坐标系
 * - Three.js 使用 Y-up 坐标系
 * - 解决方案：在最外层 group 上做一次旋转转换
 * 
 * 所有 position 值直接从 URDF 的 joint origin xyz 复制
 */

import React, { useRef, useMemo, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import { useGLTF } from '@react-three/drei';
import { getRobotModelBase } from '../../config/robots';
import * as THREE from 'three';

// GLB 模型路径
const MODEL_BASE_PATH = getRobotModelBase('atom01');

// Link 名称列表
const LINK_NAMES = [
    'base_link', 'torso_link',
    'left_thigh_yaw_link', 'left_thigh_roll_link', 'left_thigh_pitch_link',
    'left_knee_link', 'left_ankle_pitch_link', 'left_ankle_roll_link',
    'right_thigh_yaw_link', 'right_thigh_roll_link', 'right_thigh_pitch_link',
    'right_knee_link', 'right_ankle_pitch_link', 'right_ankle_roll_link',
    'left_arm_pitch_link', 'left_arm_roll_link', 'left_arm_yaw_link',
    'left_elbow_pitch_link', 'left_elbow_yaw_link',
    'right_arm_pitch_link', 'right_arm_roll_link', 'right_arm_yaw_link',
    'right_elbow_pitch_link', 'right_elbow_yaw_link',
];

// 预加载 GLB 文件
LINK_NAMES.forEach(name => {
    useGLTF.preload(`${MODEL_BASE_PATH}/${name}.glb`);
});

// Props 接口
export interface Atom01ModelProps {
    jointAngles?: Record<string, number>;
    faultJoints?: string[];
    highlightLinks?: string[];
    scale?: number;
    position?: [number, number, number];
}

// 单个 Link 组件
const LinkMesh: React.FC<{
    name: string;
    isFault?: boolean;
    isHighlighted?: boolean;
}> = ({ name, isFault = false, isHighlighted = false }) => {
    const meshRef = useRef<THREE.Group>(null);
    const { scene } = useGLTF(`${MODEL_BASE_PATH}/${name}.glb`);

    const clonedScene = useMemo(() => {
        const cloned = scene.clone();
        cloned.traverse((child) => {
            if ((child as THREE.Mesh).isMesh) {
                const mesh = child as THREE.Mesh;
                if (mesh.material) {
                    mesh.material = (mesh.material as THREE.Material).clone();
                }
            }
        });
        return cloned;
    }, [scene]);

    useFrame(({ clock }) => {
        if (meshRef.current) {
            meshRef.current.traverse((child) => {
                if ((child as THREE.Mesh).isMesh) {
                    const mesh = child as THREE.Mesh;
                    if (mesh.material) {
                        const mat = mesh.material as THREE.MeshStandardMaterial;
                        if (isFault) {
                            const flash = Math.sin(clock.elapsedTime * 8) > 0;
                            mat.emissive = flash ? new THREE.Color(0xff0000) : new THREE.Color(0x000000);
                            mat.emissiveIntensity = flash ? 0.5 : 0;
                        } else if (isHighlighted) {
                            mat.emissive = new THREE.Color(0x00d084);
                            mat.emissiveIntensity = 0.28;
                        } else {
                            mat.emissive = new THREE.Color(0x000000);
                            mat.emissiveIntensity = 0;
                        }
                    }
                }
            });
        }
    });

    return (
        <group ref={meshRef}>
            <primitive object={clonedScene} scale={1} />
        </group>
    );
};

// 关节定义
const JOINTS: Record<string, { axis: [number, number, number] }> = {
    'torso_joint': { axis: [0, 0, 1] },
    'left_thigh_yaw_joint': { axis: [-0.5, 0, -0.866] },
    'left_thigh_roll_joint': { axis: [0.866, 0, -0.5] },
    'left_thigh_pitch_joint': { axis: [0, 1, 0] },
    'left_knee_joint': { axis: [0, 1, 0] },
    'left_ankle_pitch_joint': { axis: [0, 1, 0] },
    'left_ankle_roll_joint': { axis: [1, 0, 0] },
    'right_thigh_yaw_joint': { axis: [-0.5, 0, -0.866] },
    'right_thigh_roll_joint': { axis: [0.866, 0, -0.5] },
    'right_thigh_pitch_joint': { axis: [0, 1, 0] },
    'right_knee_joint': { axis: [0, 1, 0] },
    'right_ankle_pitch_joint': { axis: [0, 1, 0] },
    'right_ankle_roll_joint': { axis: [1, 0, 0] },
    'left_arm_pitch_joint': { axis: [0, 1, 0] },
    'left_arm_roll_joint': { axis: [1, 0, 0] },
    'left_arm_yaw_joint': { axis: [0, 0, -1] },
    'left_elbow_pitch_joint': { axis: [0, 1, 0] },
    'left_elbow_yaw_joint': { axis: [0, 0, -1] },
    'right_arm_pitch_joint': { axis: [0, 1, 0] },
    'right_arm_roll_joint': { axis: [1, 0, 0] },
    'right_arm_yaw_joint': { axis: [0, 0, -1] },
    'right_elbow_pitch_joint': { axis: [0, 1, 0] },
    'right_elbow_yaw_joint': { axis: [0, 0, -1] },
};

// 主模型组件
export const Atom01Model: React.FC<Atom01ModelProps> = ({
    jointAngles = {},
    faultJoints = [],
    highlightLinks = [],
    scale = 1,
    position = [0, 0, 0],
}) => {
    const groupRef = useRef<THREE.Group>(null);
    const jointRefs = useRef<Record<string, THREE.Group | null>>({});

    useEffect(() => {
        Object.entries(JOINTS).forEach(([jointName, joint]) => {
            const jointGroup = jointRefs.current[jointName];
            if (jointGroup && jointAngles[jointName] !== undefined) {
                const angle = jointAngles[jointName];
                const axis = new THREE.Vector3(...joint.axis).normalize();
                jointGroup.setRotationFromAxisAngle(axis, angle);
            }
        });
    }, [jointAngles]);

    const isFault = (linkName: string) => {
        return faultJoints.some(joint => {
            const linkFromJoint = joint.replace('_joint', '_link');
            return linkName === linkFromJoint;
        });
    };
    const isHighlighted = (linkName: string) => highlightLinks.includes(linkName);

    return (
        <group ref={groupRef} scale={scale} position={position}>
            {/* 坐标系转换：URDF Z-up -> Three.js Y-up（绕 X 轴旋转 -90°）*/}
            <group rotation={[-Math.PI / 2, 0, 0]}>
                {/* Base Link */}
                <group>
                    <LinkMesh name="base_link" isFault={isFault('base_link')} isHighlighted={isHighlighted('base_link')} />

                    {/* Torso - xyz="-0.028 0 0.067" from URDF */}
                    <group
                        ref={el => jointRefs.current['torso_joint'] = el}
                        position={[-0.028, 0, 0.067]}
                    >
                        <LinkMesh name="torso_link" isFault={isFault('torso_link')} isHighlighted={isHighlighted('torso_link')} />

                        {/* === 左臂链 === */}
                        {/* left_arm_pitch_joint: xyz="0 0.122 0.206" */}
                        <group
                            ref={el => jointRefs.current['left_arm_pitch_joint'] = el}
                            position={[0, 0.122, 0.206]}
                        >
                            <LinkMesh name="left_arm_pitch_link" isFault={isFault('left_arm_pitch_link')} isHighlighted={isHighlighted('left_arm_pitch_link')} />
                            {/* left_arm_roll_joint: xyz="0.02 0.056 0" */}
                            <group
                                ref={el => jointRefs.current['left_arm_roll_joint'] = el}
                                position={[0.02, 0.056, 0]}
                            >
                                <LinkMesh name="left_arm_roll_link" isFault={isFault('left_arm_roll_link')} isHighlighted={isHighlighted('left_arm_roll_link')} />
                                {/* left_arm_yaw_joint: xyz="-0.02 0 -0.05" */}
                                <group
                                    ref={el => jointRefs.current['left_arm_yaw_joint'] = el}
                                    position={[-0.02, 0, -0.05]}
                                >
                                    <LinkMesh name="left_arm_yaw_link" isFault={isFault('left_arm_yaw_link')} isHighlighted={isHighlighted('left_arm_yaw_link')} />
                                    {/* left_elbow_pitch_joint: xyz="0 0.02 -0.189" */}
                                    <group
                                        ref={el => jointRefs.current['left_elbow_pitch_joint'] = el}
                                        position={[0, 0.02, -0.189]}
                                    >
                                        <LinkMesh name="left_elbow_pitch_link" isFault={isFault('left_elbow_pitch_link')} isHighlighted={isHighlighted('left_elbow_pitch_link')} />
                                        {/* left_elbow_yaw_joint: xyz="0.05 -0.02 0" */}
                                        <group
                                            ref={el => jointRefs.current['left_elbow_yaw_joint'] = el}
                                            position={[0.05, -0.02, 0]}
                                        >
                                            <LinkMesh name="left_elbow_yaw_link" isFault={isFault('left_elbow_yaw_link')} isHighlighted={isHighlighted('left_elbow_yaw_link')} />
                                        </group>
                                    </group>
                                </group>
                            </group>
                        </group>

                        {/* === 右臂链 === */}
                        {/* right_arm_pitch_joint: xyz="0 -0.122 0.206" */}
                        <group
                            ref={el => jointRefs.current['right_arm_pitch_joint'] = el}
                            position={[0, -0.122, 0.206]}
                        >
                            <LinkMesh name="right_arm_pitch_link" isFault={isFault('right_arm_pitch_link')} isHighlighted={isHighlighted('right_arm_pitch_link')} />
                            {/* right_arm_roll_joint: xyz="0.02 -0.056 0" */}
                            <group
                                ref={el => jointRefs.current['right_arm_roll_joint'] = el}
                                position={[0.02, -0.056, 0]}
                            >
                                <LinkMesh name="right_arm_roll_link" isFault={isFault('right_arm_roll_link')} isHighlighted={isHighlighted('right_arm_roll_link')} />
                                {/* right_arm_yaw_joint: xyz="-0.02 0 -0.05" */}
                                <group
                                    ref={el => jointRefs.current['right_arm_yaw_joint'] = el}
                                    position={[-0.02, 0, -0.05]}
                                >
                                    <LinkMesh name="right_arm_yaw_link" isFault={isFault('right_arm_yaw_link')} isHighlighted={isHighlighted('right_arm_yaw_link')} />
                                    {/* right_elbow_pitch_joint: xyz="0 -0.02 -0.189" */}
                                    <group
                                        ref={el => jointRefs.current['right_elbow_pitch_joint'] = el}
                                        position={[0, -0.02, -0.189]}
                                    >
                                        <LinkMesh name="right_elbow_pitch_link" isFault={isFault('right_elbow_pitch_link')} isHighlighted={isHighlighted('right_elbow_pitch_link')} />
                                        {/* right_elbow_yaw_joint: xyz="0.05 0.02 0" */}
                                        <group
                                            ref={el => jointRefs.current['right_elbow_yaw_joint'] = el}
                                            position={[0.05, 0.02, 0]}
                                        >
                                            <LinkMesh name="right_elbow_yaw_link" isFault={isFault('right_elbow_yaw_link')} isHighlighted={isHighlighted('right_elbow_yaw_link')} />
                                        </group>
                                    </group>
                                </group>
                            </group>
                        </group>
                    </group>

                    {/* === 左腿链 === */}
                    {/* left_thigh_yaw_joint: xyz="-0.071 0.0725 -0.052" */}
                    <group
                        ref={el => jointRefs.current['left_thigh_yaw_joint'] = el}
                        position={[-0.071, 0.0725, -0.052]}
                    >
                        <LinkMesh name="left_thigh_yaw_link" isFault={isFault('left_thigh_yaw_link')} isHighlighted={isHighlighted('left_thigh_yaw_link')} />
                        <group
                            ref={el => jointRefs.current['left_thigh_roll_joint'] = el}
                            position={[-0.018, 0, -0.072]}
                        >
                            <LinkMesh name="left_thigh_roll_link" isFault={isFault('left_thigh_roll_link')} isHighlighted={isHighlighted('left_thigh_roll_link')} />
                            <group
                                ref={el => jointRefs.current['left_thigh_pitch_joint'] = el}
                                position={[0.061, 0.021, -0.035]}
                            >
                                <LinkMesh name="left_thigh_pitch_link" isFault={isFault('left_thigh_pitch_link')} isHighlighted={isHighlighted('left_thigh_pitch_link')} />
                                <group
                                    ref={el => jointRefs.current['left_knee_joint'] = el}
                                    position={[0, 0, -0.25]}
                                >
                                    <LinkMesh name="left_knee_link" isFault={isFault('left_knee_link')} isHighlighted={isHighlighted('left_knee_link')} />
                                    <group
                                        ref={el => jointRefs.current['left_ankle_pitch_joint'] = el}
                                        position={[0, -0.021, -0.3]}
                                    >
                                        <LinkMesh name="left_ankle_pitch_link" isFault={isFault('left_ankle_pitch_link')} isHighlighted={isHighlighted('left_ankle_pitch_link')} />
                                        <group
                                            ref={el => jointRefs.current['left_ankle_roll_joint'] = el}
                                            position={[0, 0, 0]}
                                        >
                                            <LinkMesh name="left_ankle_roll_link" isFault={isFault('left_ankle_roll_link')} isHighlighted={isHighlighted('left_ankle_roll_link')} />
                                        </group>
                                    </group>
                                </group>
                            </group>
                        </group>
                    </group>

                    {/* === 右腿链 === */}
                    {/* right_thigh_yaw_joint: xyz="-0.071 -0.0725 -0.052" */}
                    <group
                        ref={el => jointRefs.current['right_thigh_yaw_joint'] = el}
                        position={[-0.071, -0.0725, -0.052]}
                    >
                        <LinkMesh name="right_thigh_yaw_link" isFault={isFault('right_thigh_yaw_link')} isHighlighted={isHighlighted('right_thigh_yaw_link')} />
                        <group
                            ref={el => jointRefs.current['right_thigh_roll_joint'] = el}
                            position={[-0.019, 0, -0.072]}
                        >
                            <LinkMesh name="right_thigh_roll_link" isFault={isFault('right_thigh_roll_link')} isHighlighted={isHighlighted('right_thigh_roll_link')} />
                            <group
                                ref={el => jointRefs.current['right_thigh_pitch_joint'] = el}
                                position={[0.062, -0.021, -0.036]}
                            >
                                <LinkMesh name="right_thigh_pitch_link" isFault={isFault('right_thigh_pitch_link')} isHighlighted={isHighlighted('right_thigh_pitch_link')} />
                                <group
                                    ref={el => jointRefs.current['right_knee_joint'] = el}
                                    position={[0, 0, -0.25]}
                                >
                                    <LinkMesh name="right_knee_link" isFault={isFault('right_knee_link')} isHighlighted={isHighlighted('right_knee_link')} />
                                    <group
                                        ref={el => jointRefs.current['right_ankle_pitch_joint'] = el}
                                        position={[0, 0.021, -0.3]}
                                    >
                                        <LinkMesh name="right_ankle_pitch_link" isFault={isFault('right_ankle_pitch_link')} isHighlighted={isHighlighted('right_ankle_pitch_link')} />
                                        <group
                                            ref={el => jointRefs.current['right_ankle_roll_joint'] = el}
                                            position={[0, 0, 0]}
                                        >
                                            <LinkMesh name="right_ankle_roll_link" isFault={isFault('right_ankle_roll_link')} isHighlighted={isHighlighted('right_ankle_roll_link')} />
                                        </group>
                                    </group>
                                </group>
                            </group>
                        </group>
                    </group>
                </group>
            </group>
        </group>
    );
};

export default Atom01Model;
