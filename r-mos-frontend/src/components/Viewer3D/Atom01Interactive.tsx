/**
 * Atom01Interactive.tsx - 支持交互的 Atom01 机器人模型
 * 
 * 功能：
 * - 鼠标悬停高亮零件
 * - 点击选中零件
 * - 爆炸图展开控制
 * - 故障高亮
 */

import React, { Suspense, useRef, useMemo, useEffect, useState, useCallback } from 'react';
import { useFrame, ThreeEvent } from '@react-three/fiber';
import { useGLTF, Line } from '@react-three/drei';
import { getRobotModelBase } from '../../config/robots';
import * as THREE from 'three';
import { getExplodePartsForLink, CATEGORY_COLORS, REFERENCE_NODE_IDS, type DetailPart } from './partsManifest';

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

const clamp01 = (value: number): number => Math.min(1, Math.max(0, value));

const smoothstep = (edge0: number, edge1: number, x: number): number => {
    if (edge0 === edge1) return x < edge0 ? 0 : 1;
    const t = clamp01((x - edge0) / (edge1 - edge0));
    return t * t * (3 - 2 * t);
};

const CATEGORY_PRIORITY: Record<DetailPart['category'], number> = {
    electronics: 1,
    bearing: 2,
    calibration: 3,
    frame: 4,
    misc: 5,
    screw: 6,
    nut: 7,
};

type LinkSubPartTuning = {
    maxValidRadius: number;
    maxRenderRadius: number;
    spreadBoost: number;
    l1MaxParts: number;
};

const DEFAULT_SUBPART_TUNING: LinkSubPartTuning = {
    maxValidRadius: 0.18,
    maxRenderRadius: 0.09,
    spreadBoost: 1,
    l1MaxParts: 8,
};

const LINK_SUBPART_TUNING: Partial<Record<string, LinkSubPartTuning>> = {
    base_link: { maxValidRadius: 0.16, maxRenderRadius: 0.065, spreadBoost: 2.0, l1MaxParts: 10 },
    torso_link: { maxValidRadius: 0.14, maxRenderRadius: 0.045, spreadBoost: 2.2, l1MaxParts: 8 },
    left_arm_pitch_link: { maxValidRadius: 0.16, maxRenderRadius: 0.08, spreadBoost: 1.45, l1MaxParts: 8 },
    left_arm_roll_link: { maxValidRadius: 0.16, maxRenderRadius: 0.08, spreadBoost: 1.45, l1MaxParts: 8 },
    left_arm_yaw_link: { maxValidRadius: 0.16, maxRenderRadius: 0.075, spreadBoost: 1.6, l1MaxParts: 10 },
    left_elbow_pitch_link: { maxValidRadius: 0.16, maxRenderRadius: 0.075, spreadBoost: 1.55, l1MaxParts: 8 },
    left_elbow_yaw_link: { maxValidRadius: 0.16, maxRenderRadius: 0.075, spreadBoost: 1.55, l1MaxParts: 10 },
    right_arm_pitch_link: { maxValidRadius: 0.16, maxRenderRadius: 0.08, spreadBoost: 1.45, l1MaxParts: 8 },
    right_arm_roll_link: { maxValidRadius: 0.16, maxRenderRadius: 0.08, spreadBoost: 1.45, l1MaxParts: 8 },
    right_arm_yaw_link: { maxValidRadius: 0.16, maxRenderRadius: 0.075, spreadBoost: 1.6, l1MaxParts: 8 },
    right_elbow_pitch_link: { maxValidRadius: 0.16, maxRenderRadius: 0.075, spreadBoost: 1.55, l1MaxParts: 8 },
    right_elbow_yaw_link: { maxValidRadius: 0.16, maxRenderRadius: 0.075, spreadBoost: 1.55, l1MaxParts: 8 },
    left_thigh_yaw_link: { maxValidRadius: 0.17, maxRenderRadius: 0.07, spreadBoost: 1.35, l1MaxParts: 10 },
    left_thigh_roll_link: { maxValidRadius: 0.17, maxRenderRadius: 0.07, spreadBoost: 1.35, l1MaxParts: 10 },
    left_thigh_pitch_link: { maxValidRadius: 0.17, maxRenderRadius: 0.07, spreadBoost: 1.35, l1MaxParts: 10 },
    left_knee_link: { maxValidRadius: 0.17, maxRenderRadius: 0.07, spreadBoost: 1.25, l1MaxParts: 10 },
    left_ankle_pitch_link: { maxValidRadius: 0.17, maxRenderRadius: 0.075, spreadBoost: 1.15, l1MaxParts: 10 },
    left_ankle_roll_link: { maxValidRadius: 0.17, maxRenderRadius: 0.075, spreadBoost: 1.2, l1MaxParts: 10 },
    right_thigh_yaw_link: { maxValidRadius: 0.17, maxRenderRadius: 0.07, spreadBoost: 1.35, l1MaxParts: 10 },
    right_thigh_roll_link: { maxValidRadius: 0.17, maxRenderRadius: 0.07, spreadBoost: 1.35, l1MaxParts: 10 },
    right_thigh_pitch_link: { maxValidRadius: 0.17, maxRenderRadius: 0.07, spreadBoost: 1.35, l1MaxParts: 10 },
    right_knee_link: { maxValidRadius: 0.17, maxRenderRadius: 0.07, spreadBoost: 1.25, l1MaxParts: 10 },
    right_ankle_pitch_link: { maxValidRadius: 0.17, maxRenderRadius: 0.075, spreadBoost: 1.15, l1MaxParts: 10 },
    right_ankle_roll_link: { maxValidRadius: 0.17, maxRenderRadius: 0.075, spreadBoost: 1.2, l1MaxParts: 10 },
};

const SUBPART_OUTLIER_ABS_MAX_DIM = 3.5;
const CORE_OUTLIER_ABS_MAX_DIM = 6.0;

// 预加载 GLB 文件
LINK_NAMES.forEach(name => {
    useGLTF.preload(`${MODEL_BASE_PATH}/${name}.glb`);
});

// Props 接口
export interface Atom01InteractiveProps {
    jointAngles?: Record<string, number>;
    faultJoints?: string[];
    explodeAmount?: number;  // 爆炸程度 0~1
    showSubParts?: boolean;  // 爆炸时显示子零件
    scale?: number;
    position?: [number, number, number];
    onPartHover?: (part: PartInfo | null) => void;
    onPartSelect?: (part: PartInfo | null) => void;
    onPartDoubleClick?: (part: PartInfo) => void;  // 双击聚焦
    selectedPart?: string | null;
    hoveredPart?: string | null;
    visiblePartNames?: string[];     // 可见零件白名单
    clickablePartNames?: string[];   // 可点击零件白名单
    referencePartNames?: string[];   // 主参照集合
    preserveReferenceInExplode?: boolean; // explode 状态保留主参照可见
    fadedPartNames?: string[];       // Gate-1: fade 半透明集合（不可点击）
    fadeOpacity?: number;            // Gate-1: fade 透明度，默认 0.15，范围 [0.08, 0.25]
    // Gate-2: L2 子零件级交互
    isolationLevel?: number;         // 当前隔离层级 (0=总览, 1=L1, 2=L2)
    l2TargetLink?: string | null;    // L2: 正在查看子零件的 link
    l2SelectedPartIdx?: number | null; // L2: 选中的子零件索引（叶子高亮）
    onSubPartSelect?: (linkName: string, partIndex: number, part: DetailPart) => void;
    onSubPartHover?: (linkName: string, partIndex: number | null) => void;
    subPartEnabledNames?: string[];  // 仅这些 link 渲染子零件
    fullscreenMode?: boolean;
    onVisibleBoundsChange?: (bounds: { center: [number, number, number]; radius: number }) => void;
}

// ============================================================
// 子零件渲染组件
// ============================================================

const PARTS_GLB_BASE = '/models/parts';

/** 单个子零件 GLB */
const SubPartMesh: React.FC<{ part: DetailPart, gltf: any, isHovered: boolean, opacity: number }> = ({ part, gltf, isHovered, opacity }) => {
    const clonedScene = useMemo(() => {
        const cloned = gltf.scene.clone();
        // 子件 GLB 可能保留原装配坐标，先归零中心避免铺满视图。
        const centerBox = new THREE.Box3().setFromObject(cloned);
        const center = centerBox.getCenter(new THREE.Vector3());
        cloned.position.sub(center);

        // 资产兼容：部分子件文件包含异常超大网格，剔除体积极端 outlier 以减少整屏遮挡。
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

        if (meshVolumes.length > 0) {
            const sortedVolume = meshVolumes.map(item => item.volume).sort((a, b) => a - b);
            const sortedDim = meshVolumes.map(item => item.maxDim).sort((a, b) => a - b);
            const medianVolume = sortedVolume[Math.floor(sortedVolume.length / 2)] ?? 0;
            const medianDim = sortedDim[Math.floor(sortedDim.length / 2)] ?? 0;
            const outlierVolumeThreshold = medianVolume > 0 ? medianVolume * 45 : Number.POSITIVE_INFINITY;
            const outlierDimThreshold = Math.max(medianDim * 10, SUBPART_OUTLIER_ABS_MAX_DIM);

            meshVolumes.forEach(({ mesh, volume, maxDim, minDim }) => {
                const hasExtremeDim = maxDim > outlierDimThreshold;
                const hasExtremeVolume = medianVolume > 0 && volume > outlierVolumeThreshold;
                const hasFlatPlaneOutlier = medianDim > 0 && hasExtremeDim && minDim < medianDim * 0.12;
                if ((hasExtremeDim && hasExtremeVolume) || hasFlatPlaneOutlier) {
                    mesh.visible = false;
                }
            });
        }

        const color = new THREE.Color(CATEGORY_COLORS[part.category]);

        cloned.traverse((child: THREE.Object3D) => {
            if ((child as THREE.Mesh).isMesh) {
                const mesh = child as THREE.Mesh;
                mesh.material = new THREE.MeshStandardMaterial({
                    color,
                    metalness: 0.1, // 降低金属感，否则在无环境光贴图(HDRI)的情况下会变成死黑
                    roughness: 0.6, // 提高粗糙度使漫反射更均匀
                    transparent: true,
                    opacity: opacity,
                    emissive: isHovered ? new THREE.Color(0x00ffff) : new THREE.Color(0x000000),
                    emissiveIntensity: isHovered ? 0.3 : 0,
                    depthWrite: opacity > 0.5
                });
            }
        });

        return cloned;
    }, [gltf.scene, part.category, isHovered, opacity]);

    return <primitive object={clonedScene} />;
};

/**
 * 计算爆炸展开轴向，默认沿 Z 轴散开
 */
function getLinkExplodeAxis(linkName: string): THREE.Vector3 {
    // 根据 link 的特点定制爆炸轴线，大多数可以是局部 Z 轴
    // 例如肩膀沿 Y/X 轴展开等
    if (linkName.includes('pitch')) return new THREE.Vector3(0, 1, 0); // Y轴
    if (linkName.includes('roll')) return new THREE.Vector3(1, 0, 0);  // X轴
    if (linkName.includes('yaw')) return new THREE.Vector3(0, 0, -1);  // -Z轴
    return new THREE.Vector3(0, 0, 1); // 默认 Z 轴
}

/** 某个 link 下所有爆炸图子零件的容器 */
const SubPartsGroup: React.FC<{
    linkName: string;
    explodeAmount: number;
    baseOpacity: number;
    // Gate-2: L2 模式 props
    isL2Mode?: boolean;          // 是否处于 L2 模式
    selectedIdx?: number | null; // L2 选中的子零件索引
    onSubPartSelect?: (linkName: string, partIndex: number, part: DetailPart) => void;
    onSubPartHover?: (linkName: string, partIndex: number | null) => void;
    fullscreenMode?: boolean;
    showAllInL1?: boolean;
}> = ({
    linkName,
    explodeAmount,
    baseOpacity,
    isL2Mode = false,
    selectedIdx = null,
    onSubPartSelect,
    onSubPartHover,
    fullscreenMode = false,
    showAllInL1 = false,
}) => {
    const parts = useMemo(() => getExplodePartsForLink(linkName), [linkName]);
    const gltfUrls = useMemo(() => parts.map(p => `${PARTS_GLB_BASE}/${p.path}`), [parts]);

    // 并发加载该 link 下的所有子零件
    const gltfs = useGLTF(gltfUrls);

    const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

    // 计算包围盒后进行多轴分簇布局，避免单轴串排。
    const subPartData = useMemo(() => {
        const axis = getLinkExplodeAxis(linkName);
        const normalizedAxis = axis.clone().normalize();
        const helper = Math.abs(normalizedAxis.y) > 0.9
            ? new THREE.Vector3(1, 0, 0)
            : new THREE.Vector3(0, 1, 0);
        const baseX = helper.clone().cross(normalizedAxis).normalize();
        const baseY = normalizedAxis.clone().cross(baseX).normalize();

        const raw = parts.map((part, i) => {
            const gltf = Array.isArray(gltfs) ? gltfs[i] : (gltfs as any);
            const box = new THREE.Box3().setFromObject(gltf.scene);
            const size = box.getSize(new THREE.Vector3());
            const radius = Math.max(size.x, size.y, size.z);
            return {
                part,
                gltf,
                partIndex: i,
                radius: Math.max(radius, 0.02),
                categoryPriority: CATEGORY_PRIORITY[part.category] ?? 9,
            };
        });

        const tuning = LINK_SUBPART_TUNING[linkName] ?? DEFAULT_SUBPART_TUNING;

        // 过滤异常超大子件（通常来自导出带整机坐标的污染件），保底保留半径最小的若干件。
        const maxValidRadius = tuning.maxValidRadius;
        const sortedByRadius = [...raw].sort((a, b) => a.radius - b.radius);
        let filteredRaw = raw.filter(item => item.radius <= maxValidRadius);
        if (filteredRaw.length === 0) {
            filteredRaw = sortedByRadius.slice(0, Math.min(3, sortedByRadius.length));
        }
        if (!isL2Mode && !showAllInL1) {
            filteredRaw = [...filteredRaw]
                .sort((a, b) => {
                    if (a.categoryPriority !== b.categoryPriority) {
                        return a.categoryPriority - b.categoryPriority;
                    }
                    return a.radius - b.radius;
                })
                .slice(0, Math.min(tuning.l1MaxParts, filteredRaw.length));
        }

        // 用中位尺寸做尺度归一，缓解导出单位不一致造成的“零件突然变大”。
        const sortedRadius = filteredRaw.map(item => item.radius).sort((a, b) => a - b);
        const medianRadius = sortedRadius[Math.floor(sortedRadius.length / 2)] ?? 0.03;

        const groups = new Map<string, number[]>();
        filteredRaw.forEach((item, idx) => {
            const groupKey = item.part.category;
            if (!groups.has(groupKey)) {
                groups.set(groupKey, []);
            }
            groups.get(groupKey)?.push(idx);
        });

        const groupKeys = [...groups.keys()].sort((a, b) => {
            const pa = CATEGORY_PRIORITY[a as DetailPart['category']] ?? 99;
            const pb = CATEGORY_PRIORITY[b as DetailPart['category']] ?? 99;
            return pa - pb;
        });

        const offsets: Array<{
            scale: number;
            offset: [number, number, number];
            proxyRadius: number;
        }> = new Array(filteredRaw.length);
        const goldenAngle = Math.PI * (3 - Math.sqrt(5));

        groupKeys.forEach((groupKey, groupIndex) => {
            const memberIdx = groups.get(groupKey) ?? [];
            const groupAngle = (Math.PI * 2 * groupIndex) / Math.max(groupKeys.length, 1);
            const localX = baseX.clone().applyAxisAngle(normalizedAxis, groupAngle * 0.35);
            const localY = baseY.clone().applyAxisAngle(normalizedAxis, groupAngle * 0.35);
            const groupDir = baseX.clone().multiplyScalar(Math.cos(groupAngle)).add(
                baseY.clone().multiplyScalar(Math.sin(groupAngle)),
            ).normalize();

            memberIdx.forEach((originalIndex, localIndex) => {
                const current = filteredRaw[originalIndex];
                // 大尺寸异常件需要更强缩放，避免单件撑满视野造成遮挡/折叠观感。
                const rawScale = medianRadius / current.radius;
                const maxRenderRadius = fullscreenMode
                    ? tuning.maxRenderRadius * 1.2
                    : tuning.maxRenderRadius;
                const capScale = maxRenderRadius / current.radius;
                const scale = Math.min(
                    THREE.MathUtils.clamp(rawScale, 0.06, 2.4),
                    THREE.MathUtils.clamp(capScale, 0.02, 2.4),
                );
                const normalizedRadius = Math.min(current.radius * scale, medianRadius * 1.4);
                const ringRadius = (0.06 + (0.035 * Math.sqrt(localIndex + 1)) + (normalizedRadius * 0.65))
                    * tuning.spreadBoost;
                const spiralAngle = localIndex * goldenAngle;

                const spread = localX.clone().multiplyScalar(Math.cos(spiralAngle) * ringRadius).add(
                    localY.clone().multiplyScalar(Math.sin(spiralAngle) * ringRadius),
                );
                const cluster = groupDir.clone().multiplyScalar((0.1 + normalizedRadius * 0.7) * tuning.spreadBoost);
                const axial = normalizedAxis.clone().multiplyScalar(
                    (0.03 + (0.012 * groupIndex) + (0.016 * Math.floor(localIndex / 5)))
                    * Math.max(1, tuning.spreadBoost * 0.85),
                );
                const offsetVec = cluster.add(spread).add(axial);
                const proxyRadius = Math.max(normalizedRadius * 0.55, fullscreenMode ? 0.04 : 0.03);

                offsets[originalIndex] = {
                    scale,
                    offset: [offsetVec.x, offsetVec.y, offsetVec.z],
                    proxyRadius,
                };
            });
        });

        return filteredRaw.map((item, idx) => ({
            part: item.part,
            gltf: item.gltf,
            partIndex: item.partIndex,
            scale: offsets[idx]?.scale ?? 1,
            offset: offsets[idx]?.offset ?? [0, 0, 0],
            proxyRadius: offsets[idx]?.proxyRadius ?? (fullscreenMode ? 0.04 : 0.03),
        }));
    }, [parts, gltfs, linkName, fullscreenMode, isL2Mode, showAllInL1]);

    if (parts.length === 0) return null;

    // 子零件分离动画使用平滑曲线，避免 0.3 附近突变。
    const factor = smoothstep(0.18, 0.75, explodeAmount);

    return (
        <group>
            {subPartData.map((data, i) => {
                const logicalIndex = data.partIndex ?? i;
                const finalOffset: [number, number, number] = [
                    data.offset[0] * factor,
                    data.offset[1] * factor,
                    data.offset[2] * factor
                ];

                const isHovered = hoveredIdx === logicalIndex;
                const isSelected = isL2Mode && selectedIdx === logicalIndex;
                const isIsolating = hoveredIdx !== null || (isL2Mode && selectedIdx !== null);

                // Gate-2: L2 模式下 — 选中件全不透明，非选中件 fade
                let targetOpacity: number;
                if (isL2Mode && selectedIdx !== null) {
                    targetOpacity = isSelected ? 0.95 : (isHovered ? 0.6 : 0.12);
                } else {
                    targetOpacity = isIsolating && !isHovered ? 0.05 : 0.85;
                }
                const finalRenderOpacity = targetOpacity * baseOpacity;

                return (
                    <group key={`${linkName}-sub-${i}`}>
                        <group
                            position={finalOffset}
                            scale={data.scale}
                            onPointerOver={(e) => {
                                e.stopPropagation();
                                setHoveredIdx(logicalIndex);
                                onSubPartHover?.(linkName, logicalIndex);
                            }}
                            onPointerOut={(e) => {
                                e.stopPropagation();
                                setHoveredIdx(null);
                                onSubPartHover?.(linkName, null);
                            }}
                            onClick={(e) => {
                                if (isL2Mode) {
                                    e.stopPropagation();
                                    onSubPartSelect?.(linkName, logicalIndex, data.part);
                                }
                            }}
                        >
                            <Suspense fallback={null}>
                                <SubPartMesh
                                    part={data.part}
                                    gltf={data.gltf}
                                    isHovered={isHovered || isSelected}
                                    opacity={finalRenderOpacity}
                                />
                            </Suspense>
                        </group>

                        {/* 小件点击代理：保证低投影面积模型仍可稳定命中 */}
                        <mesh
                            position={finalOffset}
                            onPointerOver={(e) => {
                                e.stopPropagation();
                                setHoveredIdx(logicalIndex);
                                onSubPartHover?.(linkName, logicalIndex);
                            }}
                            onPointerOut={(e) => {
                                e.stopPropagation();
                                setHoveredIdx(null);
                                onSubPartHover?.(linkName, null);
                            }}
                            onClick={(e) => {
                                if (isL2Mode) {
                                    e.stopPropagation();
                                    onSubPartSelect?.(linkName, logicalIndex, data.part);
                                }
                            }}
                        >
                            <sphereGeometry args={[data.proxyRadius, 12, 12]} />
                            <meshBasicMaterial transparent opacity={0.001} depthWrite={false} />
                        </mesh>

                        {/* 引导线 (Trail Line) */}
                        {factor > 0.05 && (!isIsolating || isHovered || isSelected) && (
                            <Line
                                points={[[0, 0, 0], finalOffset]}
                                color={isSelected ? "#00aaff" : (isHovered ? "#00ffff" : CATEGORY_COLORS[data.part.category])}
                                opacity={(isHovered || isSelected ? 0.9 : (fullscreenMode ? 0.6 : 0.4)) * baseOpacity}
                                transparent
                                dashed={true}
                                dashSize={0.02}
                                dashScale={1}
                                dashOffset={0}
                                gapSize={0.01}
                                lineWidth={isSelected ? (fullscreenMode ? 3 : 2) : (fullscreenMode ? 2 : 1)}
                            />
                        )}
                    </group>
                );
            })}
        </group>
    );
};

// 爆炸偏移量配置 — 加大间距以容纳子零件
const EXPLODE_OFFSETS: Record<string, [number, number, number]> = {
    'base_link': [0, 0, 0],
    'torso_link': [0, 0, 0.4],
    'left_arm_pitch_link': [-0.3, 0.4, 0.3],
    'left_arm_roll_link': [-0.35, 0.5, 0.3],
    'left_arm_yaw_link': [-0.4, 0.6, 0.15],
    'left_elbow_pitch_link': [-0.5, 0.75, 0],
    'left_elbow_yaw_link': [-0.6, 0.9, -0.15],
    'right_arm_pitch_link': [-0.3, -0.4, 0.3],
    'right_arm_roll_link': [-0.35, -0.5, 0.3],
    'right_arm_yaw_link': [-0.4, -0.6, 0.15],
    'right_elbow_pitch_link': [-0.5, -0.75, 0],
    'right_elbow_yaw_link': [-0.6, -0.9, -0.15],
    'left_thigh_yaw_link': [0, 0.25, -0.15],
    'left_thigh_roll_link': [0, 0.3, -0.3],
    'left_thigh_pitch_link': [0, 0.35, -0.45],
    'left_knee_link': [0, 0.4, -0.7],
    'left_ankle_pitch_link': [0, 0.5, -1.0],
    'left_ankle_roll_link': [0, 0.55, -1.3],
    'right_thigh_yaw_link': [0, -0.25, -0.15],
    'right_thigh_roll_link': [0, -0.3, -0.3],
    'right_thigh_pitch_link': [0, -0.35, -0.45],
    'right_knee_link': [0, -0.4, -0.7],
    'right_ankle_pitch_link': [0, -0.5, -1.0],
    'right_ankle_roll_link': [0, -0.55, -1.3],
};

// 单个可交互 Link 组件
const InteractiveLinkMesh: React.FC<{
    name: string;
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
}> = ({
    name,
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
}) => {
        const meshRef = useRef<THREE.Group>(null);
        const { scene } = useGLTF(`${MODEL_BASE_PATH}/${name}.glb`);
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

        // 资产兼容：剔除体积极端 outlier 网格（常见于导出污染导致的“整屏遮挡板”）。
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
        // 单节点隔离态下保证核心件最小视觉尺寸，避免“小灰点”不可辨识。
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
                                    const referenceFloor = name === 'torso_link' ? 0.2 : 0.35;
                                    // 单节点研究态：核心本体保持“半隐藏”可辨识
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
        const explodeOffset = EXPLODE_OFFSETS[name] || [0, 0, 0];
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
    // Gate-2
    isolationLevel = 0,
    l2TargetLink = null,
    l2SelectedPartIdx = null,
    onSubPartSelect,
    onSubPartHover,
    subPartEnabledNames,
    fullscreenMode = false,
    onVisibleBoundsChange,
}) => {
    const groupRef = useRef<THREE.Group>(null);
    const jointRefs = useRef<Record<string, THREE.Group | null>>({});
    const [internalHovered, setInternalHovered] = useState<string | null>(null);
    const [internalSelected, setInternalSelected] = useState<string | null>(null);

    // 使用外部状态或内部状态
    const currentHovered = hoveredPart !== undefined ? hoveredPart : internalHovered;
    const currentSelected = selectedPart !== undefined ? selectedPart : internalSelected;
    const visibleSet = useMemo(
        () => new Set((visiblePartNames && visiblePartNames.length > 0) ? visiblePartNames : LINK_NAMES),
        [visiblePartNames],
    );
    const clickableSet = useMemo(
        () => new Set((clickablePartNames && clickablePartNames.length > 0) ? clickablePartNames : LINK_NAMES),
        [clickablePartNames],
    );
    const referenceSet = useMemo(
        () => new Set((referencePartNames && referencePartNames.length > 0) ? referencePartNames : REFERENCE_NODE_IDS),
        [referencePartNames],
    );
    const fadedSet = useMemo(
        () => new Set(fadedPartNames ?? []),
        [fadedPartNames],
    );
    const subPartEnabledSet = useMemo(
        () => new Set((subPartEnabledNames && subPartEnabledNames.length > 0) ? subPartEnabledNames : LINK_NAMES),
        [subPartEnabledNames],
    );

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

    // 是否启用子零件替换（explode > 0 且 showSubParts 开启）
    const subPartsActive = showSubParts && explodeAmount > 0;
    const subPartBaseOpacity = smoothstep(0.12, 0.42, explodeAmount);
    const singleLinkIsolation = visibleSet.size === 1 && isolationLevel <= 1;
    const suppressMainLinkOffset = visibleSet.size === 1 && subPartsActive;

    // 将当前可见内容的包围盒上报给父组件，用于相机自适应（避免隔离态空白/跑飞）。
    useEffect(() => {
        if (!onVisibleBoundsChange) return;
        if (!groupRef.current) return;

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
                // 忽略纯点击代理和近乎不可见对象，避免包围盒被虚拟命中体放大。
                if (hasTransparentMaterial && maxOpacity <= 0.02) return;

                const geometry = mesh.geometry as THREE.BufferGeometry;
                if (!geometry.boundingBox) {
                    geometry.computeBoundingBox();
                }
                if (!geometry.boundingBox) return;
                tempBox.copy(geometry.boundingBox).applyMatrix4(mesh.matrixWorld);
                const meshSize = tempBox.getSize(new THREE.Vector3());
                const meshMaxDim = Math.max(meshSize.x, meshSize.y, meshSize.z);
                // 过滤资产异常大面片，避免相机被错误拉远导致“零件极小/空屏”。
                if (meshMaxDim > CORE_OUTLIER_ABS_MAX_DIM) return;
                worldBox.union(tempBox);
                hasVisibleMesh = true;
            });

            if (!hasVisibleMesh || worldBox.isEmpty()) return;

            const center = worldBox.getCenter(new THREE.Vector3());
            const size = worldBox.getSize(new THREE.Vector3());
            const radius = Math.max(size.x, size.y, size.z) * 0.5;
            if (!Number.isFinite(radius) || radius <= 0) return;

            onVisibleBoundsChange({
                center: [center.x, center.y, center.z],
                radius,
            });
        });

        return () => cancelAnimationFrame(frame);
    }, [
        onVisibleBoundsChange,
        explodeAmount,
        showSubParts,
        subPartsActive,
        isolationLevel,
        l2TargetLink,
        l2SelectedPartIdx,
        scale,
        position,
        fullscreenMode,
        visiblePartNames,
        clickablePartNames,
        referencePartNames,
        fadedPartNames,
        subPartEnabledNames,
    ]);

    // 创建交互式 Link 的工厂函数
    const createLink = (name: string) => {
        const isFaded = fadedSet.has(name);
        const isVisible = visibleSet.has(name) || referenceSet.has(name) || isFaded;
        if (!isVisible) return null;

        // fade 和 reference (非 target) 不可点击
        const isClickable = clickableSet.has(name) && !isFaded;
        const isReferencePart = referenceSet.has(name);

        return (
            <React.Fragment key={name}>
                <InteractiveLinkMesh
                    name={name}
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
                    onPointerOver={isClickable ? handlePointerOver(name) : undefined}
                    onPointerOut={isClickable ? handlePointerOut : undefined}
                    onClick={isClickable ? handleClick(name) : undefined}
                    onDoubleClick={isClickable ? handleDoubleClick(name) : undefined}
                />
                {subPartsActive && subPartBaseOpacity > 0 && !isFaded && subPartEnabledSet.has(name) && (
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
                )}
            </React.Fragment>
        );
    };

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
