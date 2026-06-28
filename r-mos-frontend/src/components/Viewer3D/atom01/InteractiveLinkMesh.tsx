/**
 * InteractiveLinkMesh.tsx — 单个可交互 Link 组件
 */

import React, { useRef, useMemo } from 'react';
import { useFrame, ThreeEvent } from '@react-three/fiber';
import { useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import { smoothstep } from './atom01Geometry';
import { EXPLODE_OFFSETS, CORE_OUTLIER_ABS_MAX_DIM } from './atom01Constants';

// 单个可交互 Link 组件
export const InteractiveLinkMesh: React.FC<{
    name: string;
    modelBasePath: string;
    isFault?: boolean;
    isHovered?: boolean;
    isSelected?: boolean;
    explodeAmount?: number;
    showSubParts?: boolean;
    onPointerOver?: (e: ThreeEvent<PointerEvent>) => void;
    onPointerOut?: (e: ThreeEvent<PointerEvent>) => void;
    onClick?: (e: ThreeEvent<MouseEvent>) => void;
    onDoubleClick?: (e: ThreeEvent<MouseEvent>) => void;
    isReferencePart?: boolean;
    preserveReferenceInExplode?: boolean;
    isFaded?: boolean;            // Gate-1: fade 模式
    fadeOpacity?: number;         // Gate-1: fade 透明度
    suppressExplodeOffset?: boolean; // 单节点隔离态下抑制 link 级偏移，避免核心件跑离视野中心
    preferAssemblyView?: boolean; // 装配树已覆盖时，降低旧主模型的遮挡感
    explodeOffsetMap?: Record<string, [number, number, number]>; // 合并后的爆炸偏移量（manifest 优先覆盖硬编码）
}> = ({
    name,
    modelBasePath,
    isFault = false,
    isHovered = false,
    isSelected = false,
    explodeAmount = 0,
    showSubParts = false,
    onPointerOver,
    onPointerOut,
    onClick,
    onDoubleClick,
    isReferencePart = false,
    preserveReferenceInExplode = true,
    isFaded = false,
    fadeOpacity: fadedOpacityProp = 0.15,
    suppressExplodeOffset = false,
    preferAssemblyView = false,
    explodeOffsetMap,
}) => {
        const meshRef = useRef<THREE.Group>(null);
        const { scene } = useGLTF(`${modelBasePath}/${name}.glb`);
        const isolationVisualMode = showSubParts && explodeAmount > 0;

    const clonedScene = useMemo(() => {
        const cloned = scene.clone();

        // 隔离爆炸态：核心 link 可能保留装配坐标偏移，先做中心归一避免镜头跑飞。
        if (isolationVisualMode) {
            const centerBox = new THREE.Box3().setFromObject(cloned);
            const center = centerBox.getCenter(new THREE.Vector3());
            if (Number.isFinite(center.x) && Number.isFinite(center.y) && Number.isFinite(center.z)) {
                cloned.position.sub(center);
            }
        }

        // 资产兼容：剔除体积极端 outlier 网格（常见于导出污染导致的"整屏遮挡板"）。
        const meshVolumes: Array<{ mesh: THREE.Mesh; volume: number; maxDim: number; minDim: number }> = [];
        cloned.traverse((child: THREE.Object3D) => {
            if ((child as THREE.Mesh).isMesh) {
                const mesh = child as THREE.Mesh;
                const meshBox = new THREE.Box3().setFromObject(mesh);
                const size = meshBox.getSize(new THREE.Vector3());
                const volume = Math.max(size.x * size.y * size.z, 0);
                const maxDim = Math.max(size.x, size.y, size.z);
                const minDim = Math.min(size.x, size.y, size.z);
                meshVolumes.push({ mesh, volume, maxDim, minDim });
            }
        });

        if (isolationVisualMode && meshVolumes.length > 0) {
            const sortedVolume = meshVolumes.map(item => item.volume).sort((a, b) => a - b);
            const sortedDim = meshVolumes.map(item => item.maxDim).sort((a, b) => a - b);
            const medianVolume = sortedVolume[Math.floor(sortedVolume.length / 2)] ?? 0;
            const medianDim = sortedDim[Math.floor(sortedDim.length / 2)] ?? 0;
            const outlierVolumeThreshold = medianVolume > 0 ? medianVolume * 45 : Number.POSITIVE_INFINITY;
            const outlierDimThreshold = Math.max(medianDim * 9, CORE_OUTLIER_ABS_MAX_DIM);

            meshVolumes.forEach(({ mesh, volume, maxDim, minDim }) => {
                const hasExtremeDim = maxDim > outlierDimThreshold;
                const hasExtremeVolume = medianVolume > 0 && volume > outlierVolumeThreshold;
                const hasFlatPlaneOutlier = medianDim > 0 && hasExtremeDim && minDim < medianDim * 0.15;
                if ((hasExtremeDim && hasExtremeVolume) || hasFlatPlaneOutlier) {
                    mesh.visible = false;
                }
            });
        }

        cloned.traverse((child) => {
            if ((child as THREE.Mesh).isMesh) {
                const mesh = child as THREE.Mesh;
                if (mesh.material) {
                    mesh.material = (mesh.material as THREE.Material).clone();
                }
            }
        });
        return cloned;
    }, [scene, isolationVisualMode]);

    const coreVisualScale = useMemo(() => {
        if (!isolationVisualMode) return 1;
        const box = new THREE.Box3().setFromObject(clonedScene);
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        if (!Number.isFinite(maxDim) || maxDim <= 0) return 1;
        // 单节点研究态下保证核心件最小视觉尺寸，避免"小灰点"不可辨识。
        const minVisualDim = 0.18;
        return THREE.MathUtils.clamp(minVisualDim / maxDim, 1, 2.2);
    }, [clonedScene, isolationVisualMode]);

        // 高亮和选中效果
        useFrame(({ clock }) => {
            if (meshRef.current) {
                meshRef.current.traverse((child) => {
                    if ((child as THREE.Mesh).isMesh) {
                        const mesh = child as THREE.Mesh;
                        if (mesh.material) {
                            const mat = mesh.material as THREE.MeshStandardMaterial;

                            // 默认材质状态
                            let currentOpacity = 1;
                            let isVisible = true;
                            let isDepthWrite = true;
                            let isTransparent = false;

                            // Gate-1: fade 模式 — 固定半透明，保留空间参照
                            if (isFaded) {
                                currentOpacity = fadedOpacityProp;
                                isVisible = true;
                                isDepthWrite = false;
                                isTransparent = true;
                            } else if (showSubParts && explodeAmount > 0) {
                                // 平滑隐藏主模型，降低 0.15~0.3 的视觉断层。
                                const fadeProgress = smoothstep(0.2, 0.6, explodeAmount);
                                currentOpacity = 1 - fadeProgress;

                                // reference_set 在爆炸态下保留最低可见度，防止主参照丢失
                                if (isReferencePart && preserveReferenceInExplode) {
                                    const referenceFloor = preferAssemblyView
                                        ? (name === 'torso_link' ? 0.05 : 0.08)
                                        : (name === 'torso_link' ? 0.2 : 0.35);
                                    // 单节点研究态：核心本体保持"半隐藏"可辨识
                                    currentOpacity = Math.max(currentOpacity, referenceFloor);
                                }

                                isVisible = currentOpacity > 0.05;
                                isDepthWrite = currentOpacity > 0.5;
                                isTransparent = currentOpacity < 1;
                            } else {
                                currentOpacity = 1;
                                isVisible = true;
                                isDepthWrite = true;
                                isTransparent = false;
                            }

                            if (isFault) {
                                // 故障闪烁 - 红色
                                const flash = Math.sin(clock.elapsedTime * 8) > 0;
                                mat.emissive = flash ? new THREE.Color(0xff0000) : new THREE.Color(0x000000);
                                mat.emissiveIntensity = flash ? 0.5 : 0;
                            } else if (isSelected && isVisible) {
                                // 选中状态 - 蓝色发光
                                mat.emissive = new THREE.Color(0x00aaff);
                                mat.emissiveIntensity = 0.4;
                            } else if (isHovered && isVisible) {
                                // 悬停状态 - 青色发光
                                mat.emissive = new THREE.Color(0x00ffff);
                                mat.emissiveIntensity = 0.25;
                            } else {
                                // 正常状态
                                mat.emissive = new THREE.Color(0x000000);
                                mat.emissiveIntensity = 0;
                            }

                            mat.transparent = isTransparent;
                            mat.opacity = currentOpacity;
                            mat.depthWrite = isDepthWrite;
                            mat.visible = isVisible;
                        }
                    }
                });
            }
        });

        // 计算爆炸主要偏移（平滑达到峰值，避免突然弹出）
        // 优先使用从 manifest 合并的 explodeOffsetMap，回退到硬编码 EXPLODE_OFFSETS
        const explodeOffset = (explodeOffsetMap ?? EXPLODE_OFFSETS)[name] || [0, 0, 0];
        const primaryExplodeFactor = smoothstep(0, 0.45, explodeAmount);
        const explodeOffsetFactor = suppressExplodeOffset ? 0 : 1;
        const currentOffset: [number, number, number] = [
            explodeOffset[0] * primaryExplodeFactor * explodeOffsetFactor,
            explodeOffset[1] * primaryExplodeFactor * explodeOffsetFactor,
            explodeOffset[2] * primaryExplodeFactor * explodeOffsetFactor,
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
                <primitive object={clonedScene} scale={coreVisualScale} />
            </group>
        );
    };
