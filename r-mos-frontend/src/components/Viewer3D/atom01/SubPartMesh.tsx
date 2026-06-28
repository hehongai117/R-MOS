/**
 * SubPartMesh.tsx — 单个子零件 GLB 渲染组件
 */

import React, { useMemo } from 'react';
import * as THREE from 'three';
import { CATEGORY_COLORS, type DetailPart } from '../partsManifest';
import { SUBPART_OUTLIER_ABS_MAX_DIM } from './atom01Constants';

/** 单个子零件 GLB */
export const SubPartMesh: React.FC<{ part: DetailPart, gltf: any, isHovered: boolean, opacity: number }> = ({ part, gltf, isHovered, opacity }) => {
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
