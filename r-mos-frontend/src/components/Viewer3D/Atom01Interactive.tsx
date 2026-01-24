/**
 * Atom01Interactive.tsx - 支持交互的 Atom01 机器人模型
 * 
 * 功能：
 * - 鼠标悬停高亮零件
 * - 点击选中零件
 * - 爆炸图展开控制
 * - 故障高亮
 */

import React, { useRef, useMemo, useEffect, useState, useCallback } from 'react';
import { useFrame, ThreeEvent } from '@react-three/fiber';
import { useGLTF } from '@react-three/drei';
import { getRobotModelBase } from '../../config/robots';
import * as THREE from 'three';

// GLB 模型路径
const MODEL_BASE_PATH = getRobotModelBase('atom01');

// 零件信息接口
export interface PartInfo {
    name: string;
    displayName: string;
    group: 'base' | 'torso' | 'left_arm' | 'right_arm' | 'left_leg' | 'right_leg';
    jointName?: string;
}

// 零件元数据
const PART_METADATA: Record<string, PartInfo> = {
    'base_link': { name: 'base_link', displayName: '髋部底座', group: 'base' },
    'torso_link': { name: 'torso_link', displayName: '躯干', group: 'torso', jointName: 'torso_joint' },
    'left_thigh_yaw_link': { name: 'left_thigh_yaw_link', displayName: '左大腿 Yaw', group: 'left_leg', jointName: 'left_thigh_yaw_joint' },
    'left_thigh_roll_link': { name: 'left_thigh_roll_link', displayName: '左大腿 Roll', group: 'left_leg', jointName: 'left_thigh_roll_joint' },
    'left_thigh_pitch_link': { name: 'left_thigh_pitch_link', displayName: '左大腿 Pitch', group: 'left_leg', jointName: 'left_thigh_pitch_joint' },
    'left_knee_link': { name: 'left_knee_link', displayName: '左膝关节', group: 'left_leg', jointName: 'left_knee_joint' },
    'left_ankle_pitch_link': { name: 'left_ankle_pitch_link', displayName: '左踝 Pitch', group: 'left_leg', jointName: 'left_ankle_pitch_joint' },
    'left_ankle_roll_link': { name: 'left_ankle_roll_link', displayName: '左踝 Roll', group: 'left_leg', jointName: 'left_ankle_roll_joint' },
    'right_thigh_yaw_link': { name: 'right_thigh_yaw_link', displayName: '右大腿 Yaw', group: 'right_leg', jointName: 'right_thigh_yaw_joint' },
    'right_thigh_roll_link': { name: 'right_thigh_roll_link', displayName: '右大腿 Roll', group: 'right_leg', jointName: 'right_thigh_roll_joint' },
    'right_thigh_pitch_link': { name: 'right_thigh_pitch_link', displayName: '右大腿 Pitch', group: 'right_leg', jointName: 'right_thigh_pitch_joint' },
    'right_knee_link': { name: 'right_knee_link', displayName: '右膝关节', group: 'right_leg', jointName: 'right_knee_joint' },
    'right_ankle_pitch_link': { name: 'right_ankle_pitch_link', displayName: '右踝 Pitch', group: 'right_leg', jointName: 'right_ankle_pitch_joint' },
    'right_ankle_roll_link': { name: 'right_ankle_roll_link', displayName: '右踝 Roll', group: 'right_leg', jointName: 'right_ankle_roll_joint' },
    'left_arm_pitch_link': { name: 'left_arm_pitch_link', displayName: '左肩 Pitch', group: 'left_arm', jointName: 'left_arm_pitch_joint' },
    'left_arm_roll_link': { name: 'left_arm_roll_link', displayName: '左肩 Roll', group: 'left_arm', jointName: 'left_arm_roll_joint' },
    'left_arm_yaw_link': { name: 'left_arm_yaw_link', displayName: '左上臂', group: 'left_arm', jointName: 'left_arm_yaw_joint' },
    'left_elbow_pitch_link': { name: 'left_elbow_pitch_link', displayName: '左肘 Pitch', group: 'left_arm', jointName: 'left_elbow_pitch_joint' },
    'left_elbow_yaw_link': { name: 'left_elbow_yaw_link', displayName: '左前臂', group: 'left_arm', jointName: 'left_elbow_yaw_joint' },
    'right_arm_pitch_link': { name: 'right_arm_pitch_link', displayName: '右肩 Pitch', group: 'right_arm', jointName: 'right_arm_pitch_joint' },
    'right_arm_roll_link': { name: 'right_arm_roll_link', displayName: '右肩 Roll', group: 'right_arm', jointName: 'right_arm_roll_joint' },
    'right_arm_yaw_link': { name: 'right_arm_yaw_link', displayName: '右上臂', group: 'right_arm', jointName: 'right_arm_yaw_joint' },
    'right_elbow_pitch_link': { name: 'right_elbow_pitch_link', displayName: '右肘 Pitch', group: 'right_arm', jointName: 'right_elbow_pitch_joint' },
    'right_elbow_yaw_link': { name: 'right_elbow_yaw_link', displayName: '右前臂', group: 'right_arm', jointName: 'right_elbow_yaw_joint' },
};

// Link 名称列表
const LINK_NAMES = Object.keys(PART_METADATA);

// 预加载 GLB 文件
LINK_NAMES.forEach(name => {
    useGLTF.preload(`${MODEL_BASE_PATH}/${name}.glb`);
});

// Props 接口
export interface Atom01InteractiveProps {
    jointAngles?: Record<string, number>;
    faultJoints?: string[];
    explodeAmount?: number;  // 爆炸程度 0~1
    xrayMode?: boolean;      // 透视模式
    scale?: number;
    position?: [number, number, number];
    onPartHover?: (part: PartInfo | null) => void;
    onPartSelect?: (part: PartInfo | null) => void;
    onPartDoubleClick?: (part: PartInfo) => void;  // 双击聚焦
    selectedPart?: string | null;
    hoveredPart?: string | null;
}

// 爆炸偏移量配置
const EXPLODE_OFFSETS: Record<string, [number, number, number]> = {
    'base_link': [0, 0, 0],
    'torso_link': [0, 0, 0.15],
    'left_arm_pitch_link': [-0.1, 0.15, 0.1],
    'left_arm_roll_link': [-0.12, 0.18, 0.1],
    'left_arm_yaw_link': [-0.15, 0.22, 0.05],
    'left_elbow_pitch_link': [-0.18, 0.28, 0],
    'left_elbow_yaw_link': [-0.22, 0.35, -0.05],
    'right_arm_pitch_link': [-0.1, -0.15, 0.1],
    'right_arm_roll_link': [-0.12, -0.18, 0.1],
    'right_arm_yaw_link': [-0.15, -0.22, 0.05],
    'right_elbow_pitch_link': [-0.18, -0.28, 0],
    'right_elbow_yaw_link': [-0.22, -0.35, -0.05],
    'left_thigh_yaw_link': [0, 0.08, -0.05],
    'left_thigh_roll_link': [0, 0.1, -0.1],
    'left_thigh_pitch_link': [0, 0.12, -0.15],
    'left_knee_link': [0, 0.15, -0.25],
    'left_ankle_pitch_link': [0, 0.18, -0.4],
    'left_ankle_roll_link': [0, 0.2, -0.5],
    'right_thigh_yaw_link': [0, -0.08, -0.05],
    'right_thigh_roll_link': [0, -0.1, -0.1],
    'right_thigh_pitch_link': [0, -0.12, -0.15],
    'right_knee_link': [0, -0.15, -0.25],
    'right_ankle_pitch_link': [0, -0.18, -0.4],
    'right_ankle_roll_link': [0, -0.2, -0.5],
};

// 单个可交互 Link 组件
const InteractiveLinkMesh: React.FC<{
    name: string;
    isFault?: boolean;
    isHovered?: boolean;
    isSelected?: boolean;
    explodeAmount?: number;
    xrayMode?: boolean;
    onPointerOver?: (e: ThreeEvent<PointerEvent>) => void;
    onPointerOut?: (e: ThreeEvent<PointerEvent>) => void;
    onClick?: (e: ThreeEvent<MouseEvent>) => void;
    onDoubleClick?: (e: ThreeEvent<MouseEvent>) => void;
}> = ({
    name,
    isFault = false,
    isHovered = false,
    isSelected = false,
    explodeAmount = 0,
    xrayMode = false,
    onPointerOver,
    onPointerOut,
    onClick,
    onDoubleClick,
}) => {
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

        // 高亮和选中效果
        useFrame(({ clock }) => {
            if (meshRef.current) {
                meshRef.current.traverse((child) => {
                    if ((child as THREE.Mesh).isMesh) {
                        const mesh = child as THREE.Mesh;
                        if (mesh.material) {
                            const mat = mesh.material as THREE.MeshStandardMaterial;

                            if (isFault) {
                                // 故障闪烁 - 红色
                                const flash = Math.sin(clock.elapsedTime * 8) > 0;
                                mat.emissive = flash ? new THREE.Color(0xff0000) : new THREE.Color(0x000000);
                                mat.emissiveIntensity = flash ? 0.5 : 0;
                            } else if (isSelected) {
                                // 选中状态 - 蓝色发光
                                mat.emissive = new THREE.Color(0x00aaff);
                                mat.emissiveIntensity = 0.4;
                            } else if (isHovered) {
                                // 悬停状态 - 青色发光
                                mat.emissive = new THREE.Color(0x00ffff);
                                mat.emissiveIntensity = 0.25;
                            } else {
                                // 正常状态
                                mat.emissive = new THREE.Color(0x000000);
                                mat.emissiveIntensity = 0;
                            }

                            // 透视模式
                            if (xrayMode) {
                                mat.transparent = true;
                                mat.opacity = isSelected || isHovered ? 0.8 : 0.3;
                                mat.depthWrite = false;
                            } else {
                                mat.transparent = false;
                                mat.opacity = 1;
                                mat.depthWrite = true;
                            }
                        }
                    }
                });
            }
        });

        // 计算爆炸偏移
        const explodeOffset = EXPLODE_OFFSETS[name] || [0, 0, 0];
        const currentOffset: [number, number, number] = [
            explodeOffset[0] * explodeAmount,
            explodeOffset[1] * explodeAmount,
            explodeOffset[2] * explodeAmount,
        ];

        return (
            <group
                ref={meshRef}
                position={currentOffset}
                onPointerOver={onPointerOver}
                onPointerOut={onPointerOut}
                onClick={onClick}
                onDoubleClick={onDoubleClick}
            >
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
export const Atom01Interactive: React.FC<Atom01InteractiveProps> = ({
    jointAngles = {},
    faultJoints = [],
    explodeAmount = 0,
    xrayMode = false,
    scale = 1,
    position = [0, 0, 0],
    onPartHover,
    onPartSelect,
    onPartDoubleClick,
    selectedPart,
    hoveredPart,
}) => {
    const groupRef = useRef<THREE.Group>(null);
    const jointRefs = useRef<Record<string, THREE.Group | null>>({});
    const [internalHovered, setInternalHovered] = useState<string | null>(null);
    const [internalSelected, setInternalSelected] = useState<string | null>(null);

    // 使用外部状态或内部状态
    const currentHovered = hoveredPart !== undefined ? hoveredPart : internalHovered;
    const currentSelected = selectedPart !== undefined ? selectedPart : internalSelected;

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

    const handlePointerOver = useCallback((partName: string) => (e: ThreeEvent<PointerEvent>) => {
        e.stopPropagation();
        setInternalHovered(partName);
        onPartHover?.(PART_METADATA[partName] || null);
    }, [onPartHover]);

    const handlePointerOut = useCallback(() => {
        setInternalHovered(null);
        onPartHover?.(null);
    }, [onPartHover]);

    const handleClick = useCallback((partName: string) => (e: ThreeEvent<MouseEvent>) => {
        e.stopPropagation();
        const newSelected = currentSelected === partName ? null : partName;
        setInternalSelected(newSelected);
        onPartSelect?.(newSelected ? PART_METADATA[newSelected] : null);
    }, [currentSelected, onPartSelect]);

    const handleDoubleClick = useCallback((partName: string) => (e: ThreeEvent<MouseEvent>) => {
        e.stopPropagation();
        const part = PART_METADATA[partName];
        if (part) {
            onPartDoubleClick?.(part);
        }
    }, [onPartDoubleClick]);

    // 创建交互式 Link 的工厂函数
    const createLink = (name: string) => (
        <InteractiveLinkMesh
            key={name}
            name={name}
            isFault={isFault(name)}
            isHovered={currentHovered === name}
            isSelected={currentSelected === name}
            explodeAmount={explodeAmount}
            xrayMode={xrayMode}
            onPointerOver={handlePointerOver(name)}
            onPointerOut={handlePointerOut}
            onClick={handleClick(name)}
            onDoubleClick={handleDoubleClick(name)}
        />
    );

    return (
        <group ref={groupRef} scale={scale} position={position}>
            <group rotation={[-Math.PI / 2, 0, 0]}>
                <group>
                    {createLink('base_link')}

                    <group
                        ref={el => jointRefs.current['torso_joint'] = el}
                        position={[-0.028, 0, 0.067]}
                    >
                        {createLink('torso_link')}

                        {/* 左臂链 */}
                        <group
                            ref={el => jointRefs.current['left_arm_pitch_joint'] = el}
                            position={[0, 0.122, 0.206]}
                        >
                            {createLink('left_arm_pitch_link')}
                            <group
                                ref={el => jointRefs.current['left_arm_roll_joint'] = el}
                                position={[0.02, 0.056, 0]}
                            >
                                {createLink('left_arm_roll_link')}
                                <group
                                    ref={el => jointRefs.current['left_arm_yaw_joint'] = el}
                                    position={[-0.02, 0, -0.05]}
                                >
                                    {createLink('left_arm_yaw_link')}
                                    <group
                                        ref={el => jointRefs.current['left_elbow_pitch_joint'] = el}
                                        position={[0, 0.02, -0.189]}
                                    >
                                        {createLink('left_elbow_pitch_link')}
                                        <group
                                            ref={el => jointRefs.current['left_elbow_yaw_joint'] = el}
                                            position={[0.05, -0.02, 0]}
                                        >
                                            {createLink('left_elbow_yaw_link')}
                                        </group>
                                    </group>
                                </group>
                            </group>
                        </group>

                        {/* 右臂链 */}
                        <group
                            ref={el => jointRefs.current['right_arm_pitch_joint'] = el}
                            position={[0, -0.122, 0.206]}
                        >
                            {createLink('right_arm_pitch_link')}
                            <group
                                ref={el => jointRefs.current['right_arm_roll_joint'] = el}
                                position={[0.02, -0.056, 0]}
                            >
                                {createLink('right_arm_roll_link')}
                                <group
                                    ref={el => jointRefs.current['right_arm_yaw_joint'] = el}
                                    position={[-0.02, 0, -0.05]}
                                >
                                    {createLink('right_arm_yaw_link')}
                                    <group
                                        ref={el => jointRefs.current['right_elbow_pitch_joint'] = el}
                                        position={[0, -0.02, -0.189]}
                                    >
                                        {createLink('right_elbow_pitch_link')}
                                        <group
                                            ref={el => jointRefs.current['right_elbow_yaw_joint'] = el}
                                            position={[0.05, 0.02, 0]}
                                        >
                                            {createLink('right_elbow_yaw_link')}
                                        </group>
                                    </group>
                                </group>
                            </group>
                        </group>
                    </group>

                    {/* 左腿链 */}
                    <group
                        ref={el => jointRefs.current['left_thigh_yaw_joint'] = el}
                        position={[-0.071, 0.0725, -0.052]}
                    >
                        {createLink('left_thigh_yaw_link')}
                        <group
                            ref={el => jointRefs.current['left_thigh_roll_joint'] = el}
                            position={[-0.018, 0, -0.072]}
                        >
                            {createLink('left_thigh_roll_link')}
                            <group
                                ref={el => jointRefs.current['left_thigh_pitch_joint'] = el}
                                position={[0.061, 0.021, -0.035]}
                            >
                                {createLink('left_thigh_pitch_link')}
                                <group
                                    ref={el => jointRefs.current['left_knee_joint'] = el}
                                    position={[0, 0, -0.25]}
                                >
                                    {createLink('left_knee_link')}
                                    <group
                                        ref={el => jointRefs.current['left_ankle_pitch_joint'] = el}
                                        position={[0, -0.021, -0.3]}
                                    >
                                        {createLink('left_ankle_pitch_link')}
                                        <group
                                            ref={el => jointRefs.current['left_ankle_roll_joint'] = el}
                                            position={[0, 0, 0]}
                                        >
                                            {createLink('left_ankle_roll_link')}
                                        </group>
                                    </group>
                                </group>
                            </group>
                        </group>
                    </group>

                    {/* 右腿链 */}
                    <group
                        ref={el => jointRefs.current['right_thigh_yaw_joint'] = el}
                        position={[-0.071, -0.0725, -0.052]}
                    >
                        {createLink('right_thigh_yaw_link')}
                        <group
                            ref={el => jointRefs.current['right_thigh_roll_joint'] = el}
                            position={[-0.019, 0, -0.072]}
                        >
                            {createLink('right_thigh_roll_link')}
                            <group
                                ref={el => jointRefs.current['right_thigh_pitch_joint'] = el}
                                position={[0.062, -0.021, -0.036]}
                            >
                                {createLink('right_thigh_pitch_link')}
                                <group
                                    ref={el => jointRefs.current['right_knee_joint'] = el}
                                    position={[0, 0, -0.25]}
                                >
                                    {createLink('right_knee_link')}
                                    <group
                                        ref={el => jointRefs.current['right_ankle_pitch_joint'] = el}
                                        position={[0, 0.021, -0.3]}
                                    >
                                        {createLink('right_ankle_pitch_link')}
                                        <group
                                            ref={el => jointRefs.current['right_ankle_roll_joint'] = el}
                                            position={[0, 0, 0]}
                                        >
                                            {createLink('right_ankle_roll_link')}
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

export default Atom01Interactive;
export { PART_METADATA };
