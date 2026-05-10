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
import Atom01Interactive, { type Atom01InteractiveProps } from './Atom01Interactive';
import { ModelLoadingFallback } from './DynamicModelLoader';

export interface Atom01ViewerProps extends Atom01ModelProps {
    width?: string | number;
    height?: string | number;
    backgroundColor?: string;
    showGrid?: boolean;
    interactiveMode?: boolean;
    showSubParts?: Atom01InteractiveProps['showSubParts'];
    explodeAmount?: Atom01InteractiveProps['explodeAmount'];
    explodeStepIndex?: Atom01InteractiveProps['explodeStepIndex'];
    subPartEnabledNames?: Atom01InteractiveProps['subPartEnabledNames'];
    cameraProjection?: 'orthographic' | 'perspective';
    cameraPosition?: [number, number, number];
    cameraTarget?: [number, number, number];
}

const DEFAULT_CAMERA_POSITION: [number, number, number] = [1.5, 1, 1.5];
const DEFAULT_CAMERA_TARGET: [number, number, number] = [0, 0.3, 0];

export const Atom01Viewer: React.FC<Atom01ViewerProps> = ({
    width = '100%',
    height = '600px',
    backgroundColor = '#0a1929',
    showGrid = true,
    interactiveMode = false,
    showSubParts = false,
    explodeAmount = 0,
    explodeStepIndex = null,
    subPartEnabledNames,
    cameraProjection = 'perspective',
    cameraPosition = DEFAULT_CAMERA_POSITION,
    cameraTarget = DEFAULT_CAMERA_TARGET,
    jointAngles,
    faultJoints,
    highlightLinks,
    scale,
    position,
    robotId,
}) => {
    const canvasCamera = cameraProjection === 'orthographic'
        ? { position: cameraPosition, zoom: 170, near: 0.01, far: 100 }
        : { position: cameraPosition, fov: 45, near: 0.01, far: 100 };

    return (
        <div
            data-camera-position={cameraPosition.join(',')}
            data-camera-projection={cameraProjection}
            data-camera-target={cameraTarget.join(',')}
            data-viewer-mode={interactiveMode ? 'interactive' : 'static'}
            style={{ width, height, background: backgroundColor, borderRadius: '8px' }}
        >
            <Canvas
                key={`${cameraProjection}:${cameraPosition.join(',')}:${cameraTarget.join(',')}`}
                orthographic={cameraProjection === 'orthographic'}
                camera={canvasCamera}
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
                <Suspense fallback={<ModelLoadingFallback />}>
                    {interactiveMode ? (
                        <Atom01Interactive
                            robotId={robotId}
                            faultJoints={faultJoints}
                            jointAngles={jointAngles}
                            explodeAmount={explodeAmount}
                            explodeStepIndex={explodeStepIndex}
                            position={position ?? [0, 0.5, 0]}
                            scale={scale}
                            showSubParts={showSubParts}
                            subPartEnabledNames={subPartEnabledNames}
                        />
                    ) : (
                        <Atom01Model
                            robotId={robotId}
                            faultJoints={faultJoints}
                            highlightLinks={highlightLinks}
                            jointAngles={jointAngles}
                            position={position ?? [0, 0.5, 0]}
                            scale={scale}
                        />
                    )}
                </Suspense>

                {/* 控制器 */}
                <OrbitControls
                    enablePan={true}
                    enableZoom={true}
                    enableRotate={true}
                    minDistance={0.5}
                    maxDistance={5}
                    target={cameraTarget}
                />
            </Canvas>
        </div>
    );
};

export default Atom01Viewer;
