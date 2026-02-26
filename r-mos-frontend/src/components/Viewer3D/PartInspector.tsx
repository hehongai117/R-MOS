/**
 * PartInspector.tsx - 独立零件 3D 查看器
 *
 * 用于查看非核心零件（frame, screw, nut, misc）的独立小窗。
 * 包含一个独立 Canvas 和零件选择列表，每次只加载一个 GLB。
 */

import React, { useState, useMemo, Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, useGLTF, Center } from '@react-three/drei';
import * as THREE from 'three';
import { Typography, Tag, Empty, List } from 'antd';
import {
    getNonCorePartsForLink,
    COMMON_FASTENERS,
    CATEGORY_COLORS,
    CATEGORY_NAMES,
    type DetailPart,
} from './partsManifest';

const { Text } = Typography;
const PARTS_BASE_PATH = '/models/parts';

// ============================================================
// 单个 GLB 渲染（在独立 Canvas 内）
// ============================================================

const PartModel: React.FC<{ partPath: string; category: DetailPart['category'] }> = ({
    partPath,
    category,
}) => {
    const { scene } = useGLTF(`${PARTS_BASE_PATH}/${partPath}`);

    const clonedScene = useMemo(() => {
        const cloned = scene.clone();
        const color = new THREE.Color(CATEGORY_COLORS[category]);

        cloned.traverse((child) => {
            if ((child as THREE.Mesh).isMesh) {
                const mesh = child as THREE.Mesh;
                mesh.material = new THREE.MeshStandardMaterial({
                    color,
                    metalness: 0.5,
                    roughness: 0.4,
                });
            }
        });

        return cloned;
    }, [scene, category]);

    return (
        <Center>
            <primitive object={clonedScene} />
        </Center>
    );
};

const PartLoadingBox: React.FC = () => (
    <mesh>
        <boxGeometry args={[0.03, 0.03, 0.03]} />
        <meshStandardMaterial color="#4fc3f7" wireframe />
    </mesh>
);

// ============================================================
// PartInspector 主组件
// ============================================================

export interface PartInspectorProps {
    /** 当前选中的 link 名称 */
    selectedLink: string | null;
    /** 是否显示通用紧固件（螺丝/螺母）*/
    showFasteners?: boolean;
}

export const PartInspector: React.FC<PartInspectorProps> = ({
    selectedLink,
    showFasteners = false,
}) => {
    const [selectedPartIndex, setSelectedPartIndex] = useState<number>(0);

    // 获取零件列表
    const parts = useMemo(() => {
        const linkParts = selectedLink ? getNonCorePartsForLink(selectedLink) : [];
        if (showFasteners) {
            return [...linkParts, ...COMMON_FASTENERS];
        }
        return linkParts;
    }, [selectedLink, showFasteners]);

    // 当 link 切换时重置选中
    React.useEffect(() => {
        setSelectedPartIndex(0);
    }, [selectedLink]);

    const selectedPart = parts[selectedPartIndex] ?? null;

    if (!selectedLink && !showFasteners) {
        return (
            <div style={{ padding: 16, textAlign: 'center' }}>
                <Empty
                    description={<Text style={{ color: '#8899aa' }}>点击零件查看详情</Text>}
                    imageStyle={{ height: 40 }}
                />
            </div>
        );
    }

    if (parts.length === 0) {
        return (
            <div style={{ padding: 16, textAlign: 'center' }}>
                <Text style={{ color: '#8899aa', fontSize: 12 }}>
                    该部位无可查看的非核心零件
                </Text>
            </div>
        );
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            {/* 3D 预览区域 */}
            <div
                style={{
                    width: '100%',
                    height: 200,
                    background: '#0d1b2a',
                    borderRadius: 8,
                    overflow: 'hidden',
                    border: '1px solid rgba(100,180,255,0.15)',
                    position: 'relative',
                }}
            >
                {selectedPart && (
                    <Canvas
                        camera={{ position: [0.1, 0.08, 0.1], fov: 45, near: 0.001, far: 10 }}
                        style={{ width: '100%', height: '100%' }}
                    >
                        <ambientLight intensity={0.6} />
                        <directionalLight position={[2, 3, 2]} intensity={0.8} />
                        <directionalLight position={[-1, -1, -2]} intensity={0.3} />
                        <color attach="background" args={['#0d1b2a']} />
                        <Suspense fallback={<PartLoadingBox />}>
                            <PartModel
                                partPath={selectedPart.path}
                                category={selectedPart.category}
                            />
                        </Suspense>
                        <OrbitControls
                            enablePan={false}
                            enableZoom={true}
                            enableRotate={true}
                            minDistance={0.01}
                            maxDistance={1}
                            autoRotate
                            autoRotateSpeed={2}
                        />
                    </Canvas>
                )}

                {/* 零件名标签 */}
                {selectedPart && (
                    <div
                        style={{
                            position: 'absolute',
                            bottom: 4,
                            left: 0,
                            right: 0,
                            textAlign: 'center',
                            fontSize: 11,
                            color: '#b0c8e8',
                            background: 'rgba(0,0,0,0.5)',
                            padding: '2px 0',
                        }}
                    >
                        {selectedPart.displayName}
                        <Tag
                            color={CATEGORY_COLORS[selectedPart.category]}
                            style={{ marginLeft: 4, fontSize: 10, lineHeight: '14px', padding: '0 4px' }}
                        >
                            {CATEGORY_NAMES[selectedPart.category]}
                        </Tag>
                    </div>
                )}
            </div>

            {/* 零件列表 */}
            <div
                style={{
                    flex: 1,
                    overflowY: 'auto',
                    marginTop: 8,
                    maxHeight: 200,
                }}
            >
                <List
                    size="small"
                    dataSource={parts}
                    renderItem={(part, index) => (
                        <List.Item
                            onClick={() => setSelectedPartIndex(index)}
                            style={{
                                cursor: 'pointer',
                                padding: '4px 8px',
                                background: index === selectedPartIndex
                                    ? 'rgba(24,144,255,0.15)'
                                    : 'transparent',
                                borderRadius: 4,
                                transition: 'background 0.2s',
                                borderBottom: '1px solid rgba(255,255,255,0.04)',
                            }}
                        >
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6, width: '100%' }}>
                                <div
                                    style={{
                                        width: 8,
                                        height: 8,
                                        borderRadius: '50%',
                                        background: CATEGORY_COLORS[part.category],
                                        flexShrink: 0,
                                    }}
                                />
                                <Text
                                    style={{
                                        fontSize: 12,
                                        color: index === selectedPartIndex ? '#69c0ff' : '#b0c8e8',
                                        flex: 1,
                                        overflow: 'hidden',
                                        textOverflow: 'ellipsis',
                                        whiteSpace: 'nowrap',
                                    }}
                                >
                                    {part.displayName}
                                </Text>
                                <Tag
                                    style={{
                                        fontSize: 10,
                                        lineHeight: '14px',
                                        padding: '0 3px',
                                        margin: 0,
                                        flexShrink: 0,
                                    }}
                                    color={CATEGORY_COLORS[part.category]}
                                >
                                    {CATEGORY_NAMES[part.category]}
                                </Tag>
                            </div>
                        </List.Item>
                    )}
                />
            </div>
        </div>
    );
};

export default PartInspector;
