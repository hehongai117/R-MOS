/**
 * Atom01Viewer.tsx - Atom01 机器人 3D 场景容器
 * 
 * 集成 Canvas、灯光、控制器和 Atom01Model
 * 支持 WebSocket 实时数据驱动
 */

import React, { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { Atom01Model, Atom01ModelProps } from './Atom01Model';

// 加载指示器
const LoadingFallback = () => (
    <mesh>
        <boxGeometry args={[0.5, 0.5, 0.5]} />
        <meshStandardMaterial color="#4fc3f7" wireframe />
    </mesh>
);

export interface Atom01ViewerProps extends Atom01ModelProps {
    width?: string | number;
    height?: string | number;
    backgroundColor?: string;
    showGrid?: boolean;
}

export const Atom01Viewer: React.FC<Atom01ViewerProps> = ({
    width = '100%',
    height = '600px',
    backgroundColor = '#0a1929',
    showGrid = true,
    ...modelProps
}) => {
    return (
        <div style={{ width, height, background: backgroundColor, borderRadius: '8px' }}>
            <Canvas
                camera={{ position: [1.5, 1, 1.5], fov: 45 }}
                shadows
                dpr={[1, 2]}
            >
                {/* 环境光 */}
                <ambientLight intensity={0.4} />
                <directionalLight position={[5, 5, 5]} intensity={0.8} castShadow />
                <directionalLight position={[-5, 3, -5]} intensity={0.4} />

                {/* 背景色 */}
                <color attach="background" args={[backgroundColor]} />

                {/* 网格 */}
                {showGrid && (
                    <gridHelper args={[2, 20, '#1e3a5f', '#1e3a5f']} position={[0, -0.8, 0]} />
                )}

                {/* 机器人模型 */}
                <Suspense fallback={<LoadingFallback />}>
                    <Atom01Model {...modelProps} position={[0, 0.5, 0]} />
                </Suspense>

                {/* 控制器 */}
                <OrbitControls
                    enablePan={true}
                    enableZoom={true}
                    enableRotate={true}
                    minDistance={0.5}
                    maxDistance={5}
                    target={[0, 0.3, 0]}
                />
            </Canvas>
        </div>
    );
};

export default Atom01Viewer;
