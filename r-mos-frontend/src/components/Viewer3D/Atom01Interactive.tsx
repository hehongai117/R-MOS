/**
 * Atom01Interactive.tsx — 支持悬停/选中/爆炸图/故障高亮的 ATOM-01 交互模型。
 * 子组件已拆分至 atom01/ 子目录（Phase 3 Task 4）。
 */

import React, { useRef, useMemo, useEffect, useState, useCallback } from 'react';
import { ThreeEvent } from '@react-three/fiber';
import { getRobotModelBase } from '../../config/robots';
import * as THREE from 'three';
import { REFERENCE_NODE_IDS, type DetailPart } from './partsManifest';
import { useAtom01AssemblyData } from './hooks/useAtom01AssemblyData';
import { Atom01AssemblyRenderer } from './Atom01AssemblyRenderer';
import type { RobotDataManifest } from './assemblyManifest';
import { buildJointAxisMap, buildPartMetadata, buildExplodeOffsetMap } from './manifestHelpers';
import type { PartInfo } from './atom01/atom01Constants';
import { PART_METADATA, EXPLODE_OFFSETS, JOINTS_AXIS_FALLBACK } from './atom01/atom01Constants';
import { smoothstep } from './atom01/atom01Geometry';
import { InteractiveLinkMesh } from './atom01/InteractiveLinkMesh';
import { SubPartsGroup } from './atom01/SubPartsGroup';

export type { PartInfo };

export interface Atom01InteractiveProps {
    robotId: string;
    jointAngles?: Record<string, number>;
    faultJoints?: string[];
    explodeAmount?: number;
    explodeStepIndex?: number | null;
    showSubParts?: boolean;
    scale?: number;
    position?: [number, number, number];
    onPartHover?: (part: PartInfo | null) => void;
    onPartSelect?: (part: PartInfo | null) => void;
    onPartDoubleClick?: (part: PartInfo) => void;
    selectedPart?: string | null;
    hoveredPart?: string | null;
    visiblePartNames?: string[];
    clickablePartNames?: string[];
    referencePartNames?: string[];
    preserveReferenceInExplode?: boolean;
    fadedPartNames?: string[];       // Gate-1: fade 半透明集合（不可点击）
    fadeOpacity?: number;            // Gate-1: fade 透明度，默认 0.15
    isolationLevel?: number;         // 当前隔离层级 (0=总览, 1=L1, 2=L2)
    l2TargetLink?: string | null;
    l2SelectedPartIdx?: number | null;
    onSubPartSelect?: (linkName: string, partIndex: number, part: DetailPart) => void;
    onSubPartHover?: (linkName: string, partIndex: number | null) => void;
    subPartEnabledNames?: string[];
    fullscreenMode?: boolean;
    onVisibleBoundsChange?: (bounds: { center: [number, number, number]; radius: number }) => void;
    manifest?: RobotDataManifest | null;
}

export const Atom01Interactive: React.FC<Atom01InteractiveProps> = ({
    robotId,
    jointAngles = {},
    faultJoints = [],
    explodeAmount = 0,
    explodeStepIndex = null,
    showSubParts = false,
    scale = 1,
    position = [0, 0, 0],
    onPartHover,
    onPartSelect,
    onPartDoubleClick,
    selectedPart,
    hoveredPart,
    visiblePartNames,
    clickablePartNames,
    referencePartNames,
    preserveReferenceInExplode = true,
    fadedPartNames,
    fadeOpacity = 0.15,
    isolationLevel = 0,
    l2TargetLink = null,
    l2SelectedPartIdx = null,
    onSubPartSelect,
    onSubPartHover,
    subPartEnabledNames,
    fullscreenMode = false,
    onVisibleBoundsChange,
    manifest,
}) => {
    const modelBasePath = useMemo(() => getRobotModelBase(robotId), [robotId]);
    const groupRef = useRef<THREE.Group>(null);
    const jointRefs = useRef<Record<string, THREE.Group | null>>({});
    const [internalHovered, setInternalHovered] = useState<string | null>(null);
    const [internalSelected, setInternalSelected] = useState<string | null>(null);

    const jointAxisMap = useMemo(
        () => ({ ...JOINTS_AXIS_FALLBACK, ...buildJointAxisMap(manifest) }), [manifest]);
    const partMetadata = useMemo(
        () => ({ ...PART_METADATA, ...(buildPartMetadata(manifest) ?? {}) }), [manifest]);
    const explodeOffsets = useMemo(
        () => ({ ...EXPLODE_OFFSETS, ...(buildExplodeOffsetMap(manifest) ?? {}) }), [manifest]);
    const dynamicLinkNames = useMemo(() => Object.keys(partMetadata), [partMetadata]);

    const currentHovered = hoveredPart !== undefined ? hoveredPart : internalHovered;
    const currentSelected = selectedPart !== undefined ? selectedPart : internalSelected;
    const visibleSet = useMemo(
        () => new Set((visiblePartNames && visiblePartNames.length > 0) ? visiblePartNames : dynamicLinkNames),
        [visiblePartNames, dynamicLinkNames]);
    const clickableSet = useMemo(
        () => new Set((clickablePartNames && clickablePartNames.length > 0) ? clickablePartNames : dynamicLinkNames),
        [clickablePartNames, dynamicLinkNames]);
    const referenceSet = useMemo(
        () => new Set((referencePartNames && referencePartNames.length > 0) ? referencePartNames : REFERENCE_NODE_IDS),
        [referencePartNames]);
    const fadedSet = useMemo(() => new Set(fadedPartNames ?? []), [fadedPartNames]);
    const subPartEnabledSet = useMemo(
        () => new Set((subPartEnabledNames && subPartEnabledNames.length > 0) ? subPartEnabledNames : dynamicLinkNames),
        [subPartEnabledNames, dynamicLinkNames]);

    useEffect(() => {
        Object.entries(jointAxisMap).forEach(([jointName, axisVec]) => {
            const jointGroup = jointRefs.current[jointName];
            if (jointGroup && jointAngles[jointName] !== undefined) {
                const angle = jointAngles[jointName];
                const axis = new THREE.Vector3(...axisVec).normalize();
                jointGroup.setRotationFromAxisAngle(axis, angle);
            }
        });
    }, [jointAngles, jointAxisMap]);

    const isFault = (linkName: string) =>
        faultJoints.some(joint => linkName === joint.replace('_joint', '_link'));

    const handlePointerOver = useCallback((partName: string) => (e: ThreeEvent<PointerEvent>) => {
        e.stopPropagation();
        setInternalHovered(partName);
        onPartHover?.(partMetadata[partName] || null);
    }, [onPartHover, partMetadata]);

    const handlePointerOut = useCallback(() => {
        setInternalHovered(null);
        onPartHover?.(null);
    }, [onPartHover]);

    const handleClick = useCallback((partName: string) => (e: ThreeEvent<MouseEvent>) => {
        e.stopPropagation();
        const newSelected = currentSelected === partName ? null : partName;
        setInternalSelected(newSelected);
        onPartSelect?.(newSelected ? partMetadata[newSelected] : null);
    }, [currentSelected, onPartSelect, partMetadata]);

    const handleDoubleClick = useCallback((partName: string) => (e: ThreeEvent<MouseEvent>) => {
        e.stopPropagation();
        const part = partMetadata[partName];
        if (part) onPartDoubleClick?.(part);
    }, [onPartDoubleClick, partMetadata]);

    const subPartsActive = showSubParts && explodeAmount > 0;
    const { adapter: assemblyAdapter, explodeManifest: assemblyExplodeManifest } = useAtom01AssemblyData(subPartsActive, robotId);
    const subPartBaseOpacity = smoothstep(0.12, 0.42, explodeAmount);
    const singleLinkIsolation = visibleSet.size === 1 && isolationLevel <= 1;
    const suppressMainLinkOffset = visibleSet.size === 1 && subPartsActive;

    // 包围盒上报给父组件，用于相机自适应（避免隔离态空白/跑飞）。
    useEffect(() => {
        if (!onVisibleBoundsChange || !groupRef.current) return;
        const frame = requestAnimationFrame(() => {
            if (!groupRef.current) return;
            groupRef.current.updateWorldMatrix(true, true);
            const worldBox = new THREE.Box3();
            const tempBox = new THREE.Box3();
            let hasVisibleMesh = false;
            groupRef.current.traverse((obj: THREE.Object3D) => {
                const mesh = obj as THREE.Mesh;
                if (!mesh.isMesh || !mesh.visible || !mesh.geometry) return;
                const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
                const maxOpacity = materials.reduce((acc, mat) => {
                    if (!mat || typeof (mat as any).opacity !== 'number') return acc;
                    return Math.max(acc, (mat as any).opacity);
                }, 1);
                const hasTransparentMaterial = materials.some((mat) => !!mat && !!(mat as any).transparent);
                if (hasTransparentMaterial && maxOpacity <= 0.02) return;
                const geometry = mesh.geometry as THREE.BufferGeometry;
                if (!geometry.boundingBox) geometry.computeBoundingBox();
                if (!geometry.boundingBox) return;
                tempBox.copy(geometry.boundingBox).applyMatrix4(mesh.matrixWorld);
                const meshSize = tempBox.getSize(new THREE.Vector3());
                if (Math.max(meshSize.x, meshSize.y, meshSize.z) > 6.0) return;
                worldBox.union(tempBox);
                hasVisibleMesh = true;
            });
            if (!hasVisibleMesh || worldBox.isEmpty()) return;
            const center = worldBox.getCenter(new THREE.Vector3());
            const size = worldBox.getSize(new THREE.Vector3());
            const radius = Math.max(size.x, size.y, size.z) * 0.5;
            if (!Number.isFinite(radius) || radius <= 0) return;
            onVisibleBoundsChange({ center: [center.x, center.y, center.z], radius });
        });
        return () => cancelAnimationFrame(frame);
    }, [onVisibleBoundsChange, explodeAmount, showSubParts, subPartsActive, isolationLevel,
        l2TargetLink, l2SelectedPartIdx, scale, position, fullscreenMode,
        visiblePartNames, clickablePartNames, referencePartNames, fadedPartNames, subPartEnabledNames]);

    const createLink = (name: string) => {
        const isFaded = fadedSet.has(name);
        const isVisible = visibleSet.has(name) || referenceSet.has(name) || isFaded;
        if (!isVisible) return null;
        const isClickable = clickableSet.has(name) && !isFaded;
        const isReferencePart = referenceSet.has(name);
        return (
            <React.Fragment key={name}>
                <InteractiveLinkMesh
                    name={name}
                    modelBasePath={modelBasePath}
                    isFault={isFault(name)}
                    isHovered={isClickable && currentHovered === name}
                    isSelected={isClickable && currentSelected === name}
                    explodeAmount={explodeAmount}
                    showSubParts={showSubParts}
                    isReferencePart={isReferencePart}
                    preserveReferenceInExplode={preserveReferenceInExplode}
                    isFaded={isFaded}
                    fadeOpacity={fadeOpacity}
                    suppressExplodeOffset={suppressMainLinkOffset}
                    preferAssemblyView={Boolean(assemblyAdapter?.tree.nodes[name])}
                    explodeOffsetMap={explodeOffsets}
                    onPointerOver={isClickable ? handlePointerOver(name) : undefined}
                    onPointerOut={isClickable ? handlePointerOut : undefined}
                    onClick={isClickable ? handleClick(name) : undefined}
                    onDoubleClick={isClickable ? handleDoubleClick(name) : undefined}
                />
                {subPartsActive && subPartBaseOpacity > 0 && !isFaded && subPartEnabledSet.has(name) && (
                    assemblyAdapter?.tree.nodes[name] ? (
                        <Atom01AssemblyRenderer
                            adapter={assemblyAdapter}
                            rootLinkName={name}
                            baseOpacity={subPartBaseOpacity}
                            explodeManifest={assemblyExplodeManifest}
                            explodeAmount={explodeAmount}
                            explodeStepIndex={explodeStepIndex}
                        />
                    ) : (
                        <SubPartsGroup
                            linkName={name}
                            explodeAmount={explodeAmount}
                            baseOpacity={subPartBaseOpacity}
                            isL2Mode={isolationLevel >= 2 && l2TargetLink === name}
                            showAllInL1={singleLinkIsolation}
                            selectedIdx={l2TargetLink === name ? l2SelectedPartIdx : null}
                            onSubPartSelect={onSubPartSelect}
                            onSubPartHover={onSubPartHover}
                            fullscreenMode={fullscreenMode}
                        />
                    )
                )}
            </React.Fragment>
        );
    };

    return (
        <group ref={groupRef} scale={scale} position={position}>
            <group rotation={[-Math.PI / 2, 0, 0]}>
                <group>
                    {createLink('base_link')}
                    <group ref={el => jointRefs.current['torso_joint'] = el} position={[-0.028, 0, 0.067]}>
                        {createLink('torso_link')}
                        {/* 左臂链 */}
                        <group ref={el => jointRefs.current['left_arm_pitch_joint'] = el} position={[0, 0.122, 0.206]}>
                            {createLink('left_arm_pitch_link')}
                            <group ref={el => jointRefs.current['left_arm_roll_joint'] = el} position={[0.02, 0.056, 0]}>
                                {createLink('left_arm_roll_link')}
                                <group ref={el => jointRefs.current['left_arm_yaw_joint'] = el} position={[-0.02, 0, -0.05]}>
                                    {createLink('left_arm_yaw_link')}
                                    <group ref={el => jointRefs.current['left_elbow_pitch_joint'] = el} position={[0, 0.02, -0.189]}>
                                        {createLink('left_elbow_pitch_link')}
                                        <group ref={el => jointRefs.current['left_elbow_yaw_joint'] = el} position={[0.05, -0.02, 0]}>
                                            {createLink('left_elbow_yaw_link')}
                                        </group>
                                    </group>
                                </group>
                            </group>
                        </group>
                        {/* 右臂链 */}
                        <group ref={el => jointRefs.current['right_arm_pitch_joint'] = el} position={[0, -0.122, 0.206]}>
                            {createLink('right_arm_pitch_link')}
                            <group ref={el => jointRefs.current['right_arm_roll_joint'] = el} position={[0.02, -0.056, 0]}>
                                {createLink('right_arm_roll_link')}
                                <group ref={el => jointRefs.current['right_arm_yaw_joint'] = el} position={[-0.02, 0, -0.05]}>
                                    {createLink('right_arm_yaw_link')}
                                    <group ref={el => jointRefs.current['right_elbow_pitch_joint'] = el} position={[0, -0.02, -0.189]}>
                                        {createLink('right_elbow_pitch_link')}
                                        <group ref={el => jointRefs.current['right_elbow_yaw_joint'] = el} position={[0.05, 0.02, 0]}>
                                            {createLink('right_elbow_yaw_link')}
                                        </group>
                                    </group>
                                </group>
                            </group>
                        </group>
                    </group>
                    {/* 左腿链 */}
                    <group ref={el => jointRefs.current['left_thigh_yaw_joint'] = el} position={[-0.071, 0.0725, -0.052]}>
                        {createLink('left_thigh_yaw_link')}
                        <group ref={el => jointRefs.current['left_thigh_roll_joint'] = el} position={[-0.018, 0, -0.072]}>
                            {createLink('left_thigh_roll_link')}
                            <group ref={el => jointRefs.current['left_thigh_pitch_joint'] = el} position={[0.061, 0.021, -0.035]}>
                                {createLink('left_thigh_pitch_link')}
                                <group ref={el => jointRefs.current['left_knee_joint'] = el} position={[0, 0, -0.25]}>
                                    {createLink('left_knee_link')}
                                    <group ref={el => jointRefs.current['left_ankle_pitch_joint'] = el} position={[0, -0.021, -0.3]}>
                                        {createLink('left_ankle_pitch_link')}
                                        <group ref={el => jointRefs.current['left_ankle_roll_joint'] = el} position={[0, 0, 0]}>
                                            {createLink('left_ankle_roll_link')}
                                        </group>
                                    </group>
                                </group>
                            </group>
                        </group>
                    </group>
                    {/* 右腿链 */}
                    <group ref={el => jointRefs.current['right_thigh_yaw_joint'] = el} position={[-0.071, -0.0725, -0.052]}>
                        {createLink('right_thigh_yaw_link')}
                        <group ref={el => jointRefs.current['right_thigh_roll_joint'] = el} position={[-0.019, 0, -0.072]}>
                            {createLink('right_thigh_roll_link')}
                            <group ref={el => jointRefs.current['right_thigh_pitch_joint'] = el} position={[0.062, -0.021, -0.036]}>
                                {createLink('right_thigh_pitch_link')}
                                <group ref={el => jointRefs.current['right_knee_joint'] = el} position={[0, 0, -0.25]}>
                                    {createLink('right_knee_link')}
                                    <group ref={el => jointRefs.current['right_ankle_pitch_joint'] = el} position={[0, 0.021, -0.3]}>
                                        {createLink('right_ankle_pitch_link')}
                                        <group ref={el => jointRefs.current['right_ankle_roll_joint'] = el} position={[0, 0, 0]}>
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
