/**
 * SubPartsGroup.tsx — 某个 link 下所有爆炸图子零件的容器
 */

import React, { Suspense, useMemo, useState } from 'react';
import { useGLTF, Line } from '@react-three/drei';
import * as THREE from 'three';
import { getExplodePartsForLink, CATEGORY_COLORS, type DetailPart } from '../partsManifest';
import { PARTS_GLB_BASE, LINK_SUBPART_TUNING, DEFAULT_SUBPART_TUNING } from './atom01Constants';
import { CATEGORY_PRIORITY, getLinkExplodeAxis, smoothstep } from './atom01Geometry';
import { SubPartMesh } from './SubPartMesh';

/** 某个 link 下所有爆炸图子零件的容器 */
export const SubPartsGroup: React.FC<{
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
    const parts = useMemo(
        () => getExplodePartsForLink(linkName, { includeSecondary: isL2Mode || showAllInL1 }),
        [linkName, isL2Mode, showAllInL1],
    );
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

        // 用中位尺寸做尺度归一，缓解导出单位不一致造成的"零件突然变大"。
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
