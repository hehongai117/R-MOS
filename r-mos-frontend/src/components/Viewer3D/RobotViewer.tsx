/**
 * 3D 机器人查看器组件
 * 
 * 整合 Canvas、灯光、控制器和机器人模型
 */
import React, { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Grid, ContactShadows } from '@react-three/drei';
import HumanoidRobot from './HumanoidRobot';
import { useRobotData } from './hooks/useRobotData';
import { SCENE_CONFIG } from './constants';
import { JointState } from '@/types/robot';
import { Alert, Tag, Space } from 'antd';
import { WifiOutlined, DisconnectOutlined } from '@ant-design/icons';

interface RobotViewerProps {
    /** 容器宽度 */
    width?: number | string;
    /** 容器高度 */
    height?: number | string;
    /** 是否自动旋转 */
    autoRotate?: boolean;
    /** 关节点击回调 */
    onJointClick?: (jointId: string) => void;
    /** 是否使用外部数据（不连接 WebSocket） */
    externalData?: {
        joints: JointState[];
        connected?: boolean;
    };
}

/**
 * 场景灯光组件
 */
const SceneLights: React.FC = () => {
    const { lights } = SCENE_CONFIG;

    return (
        <>
            <ambientLight intensity={lights.ambient.intensity} />
            <directionalLight
                position={lights.directional.position}
                intensity={lights.directional.intensity}
                castShadow
                shadow-mapSize={[1024, 1024]}
            />
            <hemisphereLight
                color={lights.hemisphere.skyColor}
                groundColor={lights.hemisphere.groundColor}
                intensity={lights.hemisphere.intensity}
            />
        </>
    );
};

/**
 * 地面网格组件
 */
const Ground: React.FC = () => {
    const { ground } = SCENE_CONFIG;

    return (
        <>
            <Grid
                args={[ground.size, ground.size]}
                cellSize={0.5}
                cellThickness={0.5}
                cellColor={ground.gridColor}
                sectionSize={2}
                sectionThickness={1}
                sectionColor={ground.gridColor}
                fadeDistance={20}
                fadeStrength={1}
                position={[0, -1.2, 0]}
            />
            <ContactShadows
                position={[0, -1.19, 0]}
                opacity={0.4}
                scale={10}
                blur={2}
                far={4}
            />
        </>
    );
};

/**
 * 加载占位符
 */
const LoadingFallback: React.FC = () => (
    <mesh>
        <boxGeometry args={[0.5, 0.5, 0.5]} />
        <meshStandardMaterial color="#666" wireframe />
    </mesh>
);

/**
 * 连接状态指示器
 */
const ConnectionStatus: React.FC<{
    connected: boolean;
    error: Error | null;
    lastUpdate: Date | null;
}> = ({ connected, error, lastUpdate }) => {
    if (error) {
        return (
            <Alert
                type="error"
                message="连接错误"
                description={error.message}
                showIcon
                style={{ marginBottom: 8 }}
            />
        );
    }

    return (
        <Space style={{ marginBottom: 8 }}>
            <Tag
                icon={connected ? <WifiOutlined /> : <DisconnectOutlined />}
                color={connected ? 'success' : 'default'}
            >
                {connected ? '已连接' : '未连接'}
            </Tag>
            {lastUpdate && (
                <Tag color="blue">
                    更新: {lastUpdate.toLocaleTimeString()}
                </Tag>
            )}
        </Space>
    );
};

/**
 * 3D 机器人查看器
 */
const RobotViewer: React.FC<RobotViewerProps> = ({
    width = '100%',
    height = 500,
    autoRotate = false,
    externalData,
}) => {
    // 使用外部数据或 WebSocket 数据
    const wsData = useRobotData();
    const { joints, connected, error, lastUpdate } = externalData
        ? { joints: externalData.joints, connected: externalData.connected ?? true, error: null, lastUpdate: null }
        : wsData;

    const { camera, controls } = SCENE_CONFIG;

    return (
        <div style={{ width, height: typeof height === 'number' ? height + 40 : height }}>
            <ConnectionStatus connected={connected} error={error} lastUpdate={lastUpdate} />

            <div style={{
                width: '100%',
                height,
                background: 'linear-gradient(180deg, #1a1a2e 0%, #16213e 100%)',
                borderRadius: 8,
                overflow: 'hidden',
            }}>
                <Canvas
                    shadows
                    camera={{
                        position: camera.position,
                        fov: camera.fov,
                        near: camera.near,
                        far: camera.far,
                    }}
                >
                    <Suspense fallback={<LoadingFallback />}>
                        <SceneLights />
                        <Ground />

                        <HumanoidRobot
                            joints={joints}
                            highlightFaults={true}
                        />

                        <OrbitControls
                            minDistance={controls.minDistance}
                            maxDistance={controls.maxDistance}
                            minPolarAngle={controls.minPolarAngle}
                            maxPolarAngle={controls.maxPolarAngle}
                            enablePan={controls.enablePan}
                            enableZoom={controls.enableZoom}
                            autoRotate={autoRotate}
                            autoRotateSpeed={controls.autoRotateSpeed}
                        />
                    </Suspense>
                </Canvas>
            </div>
        </div>
    );
};

export default RobotViewer;
