/**
 * SOPMaintenancePage.tsx - SOP 维保系统页面
 * 
 * 功能：
 * - 爆炸图展示机器人零件
 * - 鼠标悬停高亮零件
 * - 点击选中显示零件信息
 * - 爆炸程度滑块控制
 * - 工具选择与校验
 * - 螺丝信息展示
 */

import { useState, useCallback, Suspense } from 'react';
import { Card, Row, Col, Slider, Typography, Space, Tag, Empty, Descriptions, Button, Segmented, Tabs } from 'antd';
import {
    ToolOutlined,
    PartitionOutlined,
    InfoCircleOutlined,
    EyeOutlined,
    ExpandOutlined,
    SettingOutlined,
    ScanOutlined,
} from '@ant-design/icons';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { Atom01Interactive, PartInfo, PART_METADATA } from '@/components/Viewer3D/Atom01Interactive';
import { CameraController } from '@/components/Viewer3D/CameraController';
import { DisassemblyDemo } from '@/components/Viewer3D/DisassemblyDemo';
import { ToolSelector, ScrewInfo, SOPPlayer } from '@/components/Maintenance';

const { Title, Text } = Typography;

// 分组颜色
const GROUP_COLORS: Record<string, string> = {
    'base': '#722ed1',
    'torso': '#13c2c2',
    'left_arm': '#52c41a',
    'right_arm': '#faad14',
    'left_leg': '#1890ff',
    'right_leg': '#eb2f96',
};

// 分组中文名
const GROUP_NAMES: Record<string, string> = {
    'base': '底座',
    'torso': '躯干',
    'left_arm': '左臂',
    'right_arm': '右臂',
    'left_leg': '左腿',
    'right_leg': '右腿',
};

// 加载指示器
const LoadingFallback = () => (
    <mesh>
        <boxGeometry args={[0.5, 0.5, 0.5]} />
        <meshStandardMaterial color="#4fc3f7" wireframe />
    </mesh>
);

function SOPMaintenancePage() {
    const [explodeAmount, setExplodeAmount] = useState(0);
    const [hoveredPart, setHoveredPart] = useState<PartInfo | null>(null);
    const [selectedPart, setSelectedPart] = useState<PartInfo | null>(null);
    const [viewMode, setViewMode] = useState<'normal' | 'explode' | 'xray'>('normal');
    const [selectedToolId, setSelectedToolId] = useState<string | null>(null);
    const [selectedScrewId, setSelectedScrewId] = useState<string | null>(null);
    const [rightPanelTab, setRightPanelTab] = useState<string>('part');
    const [focusTarget, setFocusTarget] = useState<string | null>(null);
    const [disassemblyPlaying, setDisassemblyPlaying] = useState(false);

    const handlePartHover = useCallback((part: PartInfo | null) => {
        setHoveredPart(part);
    }, []);

    const handlePartSelect = useCallback((part: PartInfo | null) => {
        setSelectedPart(part);
        setSelectedScrewId(null);  // 切换零件时清空螺丝选择
    }, []);

    const handleScrewSelect = useCallback((screwId: string) => {
        setSelectedScrewId(screwId);
        setRightPanelTab('tool');  // 切换到工具面板
    }, []);

    // SOP 播放器回调
    const handleSOPPartSelect = useCallback((partName: string | null) => {
        if (partName) {
            const part = PART_METADATA[partName];
            if (part) {
                setSelectedPart(part);
            }
        } else {
            setSelectedPart(null);
        }
    }, []);

    const handleSOPToolRequired = useCallback((toolId: string | null, screwId: string | null) => {
        if (toolId) setSelectedToolId(toolId);
        if (screwId) setSelectedScrewId(screwId);
    }, []);

    // 双击聚焦
    const handlePartDoubleClick = useCallback((part: PartInfo) => {
        setFocusTarget(part.name);
        // 清除聚焦目标，允许重复双击同一零件
        setTimeout(() => setFocusTarget(null), 100);
    }, []);

    // 获取当前零件的所有同组零件
    const getGroupParts = (group: string) => {
        return Object.values(PART_METADATA).filter(p => p.group === group);
    };

    return (
        <div style={{ height: 'calc(100vh - 120px)', display: 'flex', flexDirection: 'column' }}>
            {/* 顶部标题栏 */}
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: 16
            }}>
                <Title level={3} style={{ margin: 0 }}>
                    <ToolOutlined style={{ marginRight: 8 }} />
                    SOP 维保系统
                </Title>
                <Space>
                    <Segmented
                        value={viewMode}
                        onChange={v => {
                            setViewMode(v as typeof viewMode);
                            if (v === 'explode') {
                                setExplodeAmount(0.6);
                            } else if (v === 'normal') {
                                setExplodeAmount(0);
                            }
                        }}
                        options={[
                            { label: <><EyeOutlined /> 正常</>, value: 'normal' },
                            { label: <><ExpandOutlined /> 爆炸图</>, value: 'explode' },
                            { label: <><ScanOutlined /> 透视</>, value: 'xray' },
                        ]}
                    />
                    {selectedToolId && (
                        <Tag color="green" icon={<ToolOutlined />}>
                            工具已选择
                        </Tag>
                    )}
                    <Tag color="blue">24 个零件</Tag>
                </Space>
            </div>

            {/* 主内容区 */}
            <Row gutter={16} style={{ flex: 1, minHeight: 0 }}>
                {/* 左侧：控制面板 */}
                <Col xs={24} lg={6} style={{ height: '100%', overflowY: 'auto' }}>
                    <Space direction="vertical" style={{ width: '100%' }} size="middle">
                        {/* 爆炸图控制 */}
                        <Card size="small" title={<><PartitionOutlined /> 爆炸图控制</>}>
                            <Space direction="vertical" style={{ width: '100%' }}>
                                <div>
                                    <Text>展开程度: {Math.round(explodeAmount * 100)}%</Text>
                                    <Slider
                                        min={0}
                                        max={1}
                                        step={0.01}
                                        value={explodeAmount}
                                        onChange={setExplodeAmount}
                                    />
                                </div>
                                <Space wrap>
                                    <Button size="small" onClick={() => setExplodeAmount(0)}>收起</Button>
                                    <Button size="small" onClick={() => setExplodeAmount(0.3)}>30%</Button>
                                    <Button size="small" onClick={() => setExplodeAmount(0.6)}>60%</Button>
                                    <Button size="small" onClick={() => setExplodeAmount(1)}>完全展开</Button>
                                </Space>
                                <div style={{ marginTop: 12 }}>
                                    <Button
                                        type={disassemblyPlaying ? 'primary' : 'default'}
                                        size="small"
                                        block
                                        onClick={() => setDisassemblyPlaying(!disassemblyPlaying)}
                                    >
                                        {disassemblyPlaying ? '停止拆卸动画' : '▶ 播放拆卸动画'}
                                    </Button>
                                </div>
                            </Space>
                        </Card>

                        {/* 工具选择器 */}
                        <ToolSelector
                            selectedToolId={selectedToolId}
                            onToolSelect={setSelectedToolId}
                            requiredScrewId={selectedScrewId || undefined}
                        />

                        {/* SOP 播放器 */}
                        <SOPPlayer
                            onExplodeChange={setExplodeAmount}
                            onPartSelect={handleSOPPartSelect}
                            onToolRequired={handleSOPToolRequired}
                            currentToolId={selectedToolId}
                        />

                        {/* 悬停提示 */}
                        <Card size="small" title={<><InfoCircleOutlined /> 当前悬停</>}>
                            {hoveredPart ? (
                                <Space direction="vertical" size="small">
                                    <Text strong>{hoveredPart.displayName}</Text>
                                    <Tag color={GROUP_COLORS[hoveredPart.group]}>
                                        {GROUP_NAMES[hoveredPart.group]}
                                    </Tag>
                                    <Text type="secondary" style={{ fontSize: 12 }}>
                                        {hoveredPart.name}
                                    </Text>
                                </Space>
                            ) : (
                                <Text type="secondary">移动鼠标到零件上查看信息</Text>
                            )}
                        </Card>
                    </Space>
                </Col>

                {/* 中间：3D 视图 */}
                <Col xs={24} lg={12} style={{ height: '100%' }}>
                    <Card
                        size="small"
                        style={{ height: '100%' }}
                        bodyStyle={{ height: 'calc(100% - 40px)', padding: 0, background: '#0a1929', borderRadius: '0 0 8px 8px' }}
                        title="3D 维保视图"
                        extra={
                            <Space>
                                {hoveredPart && (
                                    <Tag color="cyan">{hoveredPart.displayName}</Tag>
                                )}
                                {selectedPart && (
                                    <Tag color="blue">{selectedPart.displayName}</Tag>
                                )}
                            </Space>
                        }
                    >
                        <Canvas
                            camera={{ position: [1.5, 1, 1.5], fov: 45 }}
                            shadows
                            dpr={[1, 2]}
                        >
                            <ambientLight intensity={0.5} />
                            <directionalLight position={[5, 5, 5]} intensity={0.8} castShadow />
                            <directionalLight position={[-5, 3, -5]} intensity={0.4} />

                            <color attach="background" args={['#0a1929']} />

                            <gridHelper args={[3, 30, '#1e3a5f', '#1e3a5f']} position={[0, -0.8, 0]} />

                            {/* 摄像机聚焦控制器 */}
                            <CameraController focusTarget={focusTarget} />

                            <Suspense fallback={<LoadingFallback />}>
                                <Atom01Interactive
                                    scale={2}
                                    position={[0, 0.5, 0]}
                                    explodeAmount={explodeAmount}
                                    xrayMode={viewMode === 'xray'}
                                    onPartHover={handlePartHover}
                                    onPartSelect={handlePartSelect}
                                    onPartDoubleClick={handlePartDoubleClick}
                                    hoveredPart={hoveredPart?.name}
                                    selectedPart={selectedPart?.name}
                                />
                            </Suspense>

                            {/* 拆卸动画演示 */}
                            <DisassemblyDemo
                                isPlaying={disassemblyPlaying}
                                targetPosition={[0, 0.6, 0.08]}
                                onComplete={() => setDisassemblyPlaying(false)}
                            />

                            <OrbitControls
                                enablePan={true}
                                enableZoom={true}
                                enableRotate={true}
                                minDistance={0.5}
                                maxDistance={5}
                                target={[0, 0.3, 0]}
                            />
                        </Canvas>
                    </Card>
                </Col>

                {/* 右侧：信息面板 */}
                <Col xs={24} lg={6} style={{ height: '100%', overflowY: 'auto' }}>
                    <Tabs
                        activeKey={rightPanelTab}
                        onChange={setRightPanelTab}
                        size="small"
                        items={[
                            {
                                key: 'part',
                                label: <><InfoCircleOutlined /> 零件</>
                                ,
                                children: (
                                    <Space direction="vertical" style={{ width: '100%' }} size="middle">
                                        {/* 零件详情 */}
                                        <Card size="small" title={<><InfoCircleOutlined /> 零件详情</>}>
                                            {selectedPart ? (
                                                <Space direction="vertical" style={{ width: '100%' }}>
                                                    <div style={{ textAlign: 'center', padding: '8px 0' }}>
                                                        <Title level={4} style={{ margin: 0 }}>
                                                            {selectedPart.displayName}
                                                        </Title>
                                                        <Tag color={GROUP_COLORS[selectedPart.group]} style={{ marginTop: 8 }}>
                                                            {GROUP_NAMES[selectedPart.group]}
                                                        </Tag>
                                                    </div>

                                                    <Descriptions column={1} size="small">
                                                        <Descriptions.Item label="零件 ID">
                                                            <Text code>{selectedPart.name}</Text>
                                                        </Descriptions.Item>
                                                        <Descriptions.Item label="关联关节">
                                                            <Text code>{selectedPart.jointName || '无'}</Text>
                                                        </Descriptions.Item>
                                                    </Descriptions>

                                                    <Button
                                                        type="default"
                                                        block
                                                        size="small"
                                                        onClick={() => setSelectedPart(null)}
                                                    >
                                                        取消选中
                                                    </Button>
                                                </Space>
                                            ) : (
                                                <Empty
                                                    description="点击零件查看详情"
                                                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                                                />
                                            )}
                                        </Card>

                                        {/* 零件分组 */}
                                        {selectedPart && (
                                            <Card
                                                size="small"
                                                title={`${GROUP_NAMES[selectedPart.group]} 零件列表`}
                                            >
                                                <Space direction="vertical" style={{ width: '100%' }} size="small">
                                                    {getGroupParts(selectedPart.group).map(part => (
                                                        <div
                                                            key={part.name}
                                                            style={{
                                                                padding: '4px 8px',
                                                                borderRadius: 4,
                                                                cursor: 'pointer',
                                                                background: part.name === selectedPart.name
                                                                    ? 'rgba(24, 144, 255, 0.2)'
                                                                    : 'transparent',
                                                                border: part.name === selectedPart.name
                                                                    ? '1px solid #1890ff'
                                                                    : '1px solid transparent',
                                                            }}
                                                            onClick={() => setSelectedPart(part)}
                                                        >
                                                            <Text>{part.displayName}</Text>
                                                        </div>
                                                    ))}
                                                </Space>
                                            </Card>
                                        )}
                                    </Space>
                                ),
                            },
                            {
                                key: 'tool',
                                label: <><SettingOutlined /> 螺丝</>
                                ,
                                children: (
                                    <ScrewInfo
                                        partName={selectedPart?.name || null}
                                        onScrewSelect={handleScrewSelect}
                                        selectedScrewId={selectedScrewId}
                                    />
                                ),
                            },
                        ]}
                    />
                </Col>
            </Row>
        </div>
    );
}

export default SOPMaintenancePage;
