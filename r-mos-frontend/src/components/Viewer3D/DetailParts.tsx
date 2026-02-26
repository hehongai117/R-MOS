/**
 * DetailParts.tsx - 核心零件模型叠加组件
 *
 * 当用户选中某个 link 时，动态加载并显示该 link 对应的**核心**子零件
 * （electronics, bearing, calibration）。
 *
 * 非核心零件（frame, screw, nut, misc）通过右侧信息面板查看文本详情。
 */

import React, { useMemo, Suspense } from 'react';
import { useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import { CATEGORY_COLORS, getCorePartsForLink, type DetailPart } from './partsManifest';

const PARTS_BASE_PATH = '/models/parts';

/**
 * 单个细节零件 GLB 渲染组件
 */
const SingleDetailPart: React.FC<{
    part: DetailPart;
    highlighted?: boolean;
}> = ({ part, highlighted = false }) => {
    const { scene } = useGLTF(`${PARTS_BASE_PATH}/${part.path}`);

    const clonedScene = useMemo(() => {
        const cloned = scene.clone();
        const color = new THREE.Color(CATEGORY_COLORS[part.category]);

        cloned.traverse((child) => {
            if ((child as THREE.Mesh).isMesh) {
                const mesh = child as THREE.Mesh;
                const mat = new THREE.MeshStandardMaterial({
                    color: color,
                    metalness: 0.6,
                    roughness: 0.4,
                    transparent: true,
                    opacity: highlighted ? 0.9 : 0.7,
                    emissive: highlighted ? color : new THREE.Color(0x000000),
                    emissiveIntensity: highlighted ? 0.3 : 0,
                });
                mesh.material = mat;
            }
        });

        return cloned;
    }, [scene, part.category, highlighted]);

    return <primitive object={clonedScene} />;
};

/**
 * 加载中的占位方块
 */
const DetailLoadingFallback: React.FC = () => (
    <mesh>
        <boxGeometry args={[0.02, 0.02, 0.02]} />
        <meshStandardMaterial color="#4fc3f7" wireframe transparent opacity={0.5} />
    </mesh>
);

/**
 * 零件细节视图 Props
 */
export interface DetailPartsProps {
    /** 当前选中的 link 名称 */
    selectedLink: string | null;
    /** 是否显示细节模型 */
    visible?: boolean;
}

/**
 * 核心零件叠加组件
 *
 * 放置在 Canvas 内 Suspense 内，根据 selectedLink 按需加载对应核心子零件。
 */
export const DetailParts: React.FC<DetailPartsProps> = ({
    selectedLink,
    visible = true,
}) => {
    if (!visible || !selectedLink) return null;

    const coreDetailParts = getCorePartsForLink(selectedLink);
    if (coreDetailParts.length === 0) return null;

    return (
        <group>
            {coreDetailParts.map((part, index) => (
                <Suspense key={`${selectedLink}-${index}`} fallback={<DetailLoadingFallback />}>
                    <SingleDetailPart part={part} />
                </Suspense>
            ))}
        </group>
    );
};

export default DetailParts;
