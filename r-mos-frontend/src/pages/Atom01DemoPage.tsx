/**
 * Atom01DemoPage.tsx - Atom01 机器人 3D 模型展示页面
 * 
 * 专门的高精度 3D 模型展示页面，突出视觉冲击力
 * 功能：
 * - 全屏 3D 可视化
 * - 关节控制滑块
 * - 故障模拟
 * - 演示模式
 */
import { useState, useCallback, useEffect, useMemo } from 'react';
import { Card, Row, Col, Slider, Switch, Button, Typography, Space, Tag, Segmented } from 'antd';
import {
    RobotOutlined,
    PlayCircleOutlined,
    PauseCircleOutlined,
    ReloadOutlined,
    WarningOutlined,
    EyeOutlined,
    SettingOutlined,
} from '@ant-design/icons';
import { Atom01Viewer } from '@/components/Viewer3D';
import { useAtom01AssemblyData } from '@/components/Viewer3D/hooks/useAtom01AssemblyData';
import { resolveExplodeView } from '@/components/Viewer3D/assemblyManifest';
import { useRobotContextStore } from '@/store/robotContextStore';

const { Title, Text } = Typography;
const DEFAULT_VIEW_ID = 'default_view';
const DEFAULT_CAMERA_POSITION: [number, number, number] = [1.5, 1, 1.5];
const DEFAULT_CAMERA_TARGET: [number, number, number] = [0, 0.3, 0];

// 关节配置（简化版，用于 UI 控制）
const JOINT_GROUPS = {
    torso: [
        { name: 'torso_joint', label: '躯干旋转', min: -3.14, max: 3.14 },
    ],
    leftLeg: [
        { name: 'left_thigh_yaw_joint', label: '左髋 Yaw', min: -1, max: 0.2 },
        { name: 'left_thigh_roll_joint', label: '左髋 Roll', min: -0.2, max: 1 },
        { name: 'left_thigh_pitch_joint', label: '左髋 Pitch', min: -1.57, max: 1.57 },
        { name: 'left_knee_joint', label: '左膝', min: -0.2, max: 2.5 },
        { name: 'left_ankle_pitch_joint', label: '左踝 Pitch', min: -0.6, max: 0.6 },
        { name: 'left_ankle_roll_joint', label: '左踝 Roll', min: -0.5, max: 0.5 },
    ],
    rightLeg: [
        { name: 'right_thigh_yaw_joint', label: '右髋 Yaw', min: -0.2, max: 1 },
        { name: 'right_thigh_roll_joint', label: '右髋 Roll', min: -1, max: 0.2 },
        { name: 'right_thigh_pitch_joint', label: '右髋 Pitch', min: -1.57, max: 1.57 },
        { name: 'right_knee_joint', label: '右膝', min: -0.2, max: 2.5 },
        { name: 'right_ankle_pitch_joint', label: '右踝 Pitch', min: -0.6, max: 0.6 },
        { name: 'right_ankle_roll_joint', label: '右踝 Roll', min: -0.5, max: 0.5 },
    ],
    leftArm: [
        { name: 'left_arm_pitch_joint', label: '左肩 Pitch', min: -3.14, max: 1.57 },
        { name: 'left_arm_roll_joint', label: '左肩 Roll', min: -1.57, max: 1.57 },
        { name: 'left_elbow_pitch_joint', label: '左肘', min: -2.26, max: 0 },
    ],
    rightArm: [
        { name: 'right_arm_pitch_joint', label: '右肩 Pitch', min: -3.14, max: 1.57 },
        { name: 'right_arm_roll_joint', label: '右肩 Roll', min: -1.57, max: 1.57 },
        { name: 'right_elbow_pitch_joint', label: '右肘', min: 0, max: 2.26 },
    ],
};

const NEUTRAL_POSE = Object.values(JOINT_GROUPS)
    .flat()
    .reduce<Record<string, number>>((pose, joint) => {
        pose[joint.name] = 0;
        return pose;
    }, {});

// 预设动作
const PRESET_POSES = {
    stand: NEUTRAL_POSE,  // 零位站立
    walk: {
        left_thigh_pitch_joint: 0.5,
        left_knee_joint: 1.0,
        right_thigh_pitch_joint: -0.3,
        right_knee_joint: 0.2,
        left_arm_pitch_joint: -0.3,
        right_arm_pitch_joint: 0.3,
    },
    squat: {
        left_thigh_pitch_joint: -1.2,
        left_knee_joint: 2.2,
        right_thigh_pitch_joint: -1.2,
        right_knee_joint: 2.2,
    },
    arms_up: {
        left_arm_pitch_joint: -2.5,
        right_arm_pitch_joint: -2.5,
    },
};

function formatExplodeViewLabel(viewId: string): string {
    if (viewId === 'torso_service_view') {
        return '躯干维护视角';
    }

    return viewId
        .replace(/_view$/u, '')
        .split('_')
        .map((segment) => segment[0]?.toUpperCase() + segment.slice(1))
        .join(' ');
}

function Atom01DemoPage() {
    const currentRobot = useRobotContextStore((s) => s.currentRobot);
    const robotId = currentRobot ? String(currentRobot.id) : null;
    const [jointAngles, setJointAngles] = useState<Record<string, number>>({});
    const [faultJoints, setFaultJoints] = useState<string[]>([]);
    const [selectedGroup, setSelectedGroup] = useState<string>('leftLeg');
    const [isAnimating, setIsAnimating] = useState(false);
    const [animationTime, setAnimationTime] = useState(0);
    const [cadExplodeEnabled, setCadExplodeEnabled] = useState(false);
    const [explodeStepIndex, setExplodeStepIndex] = useState(0);
    const [selectedExplodeViewId, setSelectedExplodeViewId] = useState<string>(DEFAULT_VIEW_ID);
    const { explodeManifest, isLoading: isAssemblyLoading, error: assemblyError } = useAtom01AssemblyData(true, robotId ?? undefined);

    // 更新单个关节角度
    const updateJoint = useCallback((jointName: string, value: number) => {
        setJointAngles(prev => ({
            ...prev,
            [jointName]: value,
        }));
    }, []);

    // 重置所有关节
    const resetJoints = useCallback(() => {
        setIsAnimating(false);
        setAnimationTime(0);
        setJointAngles({ ...NEUTRAL_POSE });
        setFaultJoints([]);
    }, []);

    // 应用预设姿态
    const applyPreset = useCallback((preset: keyof typeof PRESET_POSES) => {
        setJointAngles({ ...PRESET_POSES[preset] });
    }, []);

    // 模拟故障
    const toggleFault = useCallback((jointName: string) => {
        setFaultJoints(prev =>
            prev.includes(jointName)
                ? prev.filter(j => j !== jointName)
                : [...prev, jointName]
        );
    }, []);

    // 演示动画
    useEffect(() => {
        if (!isAnimating) return;

        const interval = setInterval(() => {
            setAnimationTime(t => t + 0.05);
        }, 50);

        return () => clearInterval(interval);
    }, [isAnimating]);

    // 根据动画时间更新关节
    useEffect(() => {
        if (!isAnimating) return;

        // 简单的行走动画
        const t = animationTime;
        setJointAngles({
            // 腿部摆动
            left_thigh_pitch_joint: Math.sin(t * 2) * 0.5,
            right_thigh_pitch_joint: Math.sin(t * 2 + Math.PI) * 0.5,
            left_knee_joint: Math.max(0, Math.sin(t * 2) * 0.8 + 0.3),
            right_knee_joint: Math.max(0, Math.sin(t * 2 + Math.PI) * 0.8 + 0.3),
            // 手臂摆动
            left_arm_pitch_joint: Math.sin(t * 2 + Math.PI) * 0.4,
            right_arm_pitch_joint: Math.sin(t * 2) * 0.4,
            // 躯干轻微摆动
            torso_joint: Math.sin(t) * 0.05,
        });
    }, [animationTime, isAnimating]);

    // 获取当前选中的关节组
    const currentJoints = JOINT_GROUPS[selectedGroup as keyof typeof JOINT_GROUPS] || [];
    const maxExplodeStep = useMemo(
        () => explodeManifest?.sequences.reduce((maxStep, sequence) => Math.max(maxStep, sequence.step_index), 0) ?? 0,
        [explodeManifest],
    );
    const explodeViewOptions = useMemo(() => {
        const authoredViews = explodeManifest?.views ?? [];
        return [
            { id: DEFAULT_VIEW_ID, label: '默认视角', focusNodeId: null as string | null },
            ...authoredViews.map((view) => ({
                id: view.id,
                label: formatExplodeViewLabel(view.id),
                focusNodeId: view.focus_node_id,
            })),
        ];
    }, [explodeManifest]);
    const activeExplodeView = useMemo(() => {
        if (!explodeManifest || selectedExplodeViewId === DEFAULT_VIEW_ID) {
            return null;
        }

        return resolveExplodeView(explodeManifest, selectedExplodeViewId);
    }, [explodeManifest, selectedExplodeViewId]);
    const focusedAssemblyNode = cadExplodeEnabled
        ? activeExplodeView?.focus_node_id ?? explodeManifest?.views[0]?.focus_node_id ?? null
        : null;
    const viewerProjection = cadExplodeEnabled && activeExplodeView
        ? activeExplodeView.camera.projection
        : 'perspective';
    const viewerPosition = cadExplodeEnabled && activeExplodeView
        ? activeExplodeView.camera.position
        : DEFAULT_CAMERA_POSITION;
    const viewerTarget = cadExplodeEnabled && activeExplodeView
        ? activeExplodeView.camera.target
        : DEFAULT_CAMERA_TARGET;
    const authoredExplodeActive = cadExplodeEnabled && explodeStepIndex > 0;

    useEffect(() => {
        if (!cadExplodeEnabled && explodeStepIndex !== 0) {
            setExplodeStepIndex(0);
        }
    }, [cadExplodeEnabled, explodeStepIndex]);

    useEffect(() => {
        if (!explodeManifest || selectedExplodeViewId === DEFAULT_VIEW_ID) {
            return;
        }

        const exists = explodeManifest.views.some((view) => view.id === selectedExplodeViewId);
        if (!exists) {
            setSelectedExplodeViewId(DEFAULT_VIEW_ID);
        }
    }, [explodeManifest, selectedExplodeViewId]);

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
                    <RobotOutlined style={{ marginRight: 8 }} />
                    Atom01 机器人 3D 展示
                </Title>
                <Space>
                    <Tag color="blue">23 自由度</Tag>
                    <Tag color="green">高精度模型</Tag>
                    {faultJoints.length > 0 && (
                        <Tag color="error" icon={<WarningOutlined />}>
                            {faultJoints.length} 个故障
                        </Tag>
                    )}
                </Space>
            </div>

            {/* 主内容区 */}
            <Row gutter={16} style={{ flex: 1, minHeight: 0 }}>
                {/* 左侧：控制面板 */}
                <Col xs={24} lg={6} style={{ height: '100%', overflowY: 'auto' }}>
                    <Space direction="vertical" style={{ width: '100%' }} size="middle">
                        {/* 动画控制 */}
                        <Card size="small" title={<><PlayCircleOutlined /> 动画控制</>}>
                            <Space direction="vertical" style={{ width: '100%' }}>
                                <Button
                                    type={isAnimating ? 'default' : 'primary'}
                                    icon={isAnimating ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                                    onClick={() => setIsAnimating(!isAnimating)}
                                    block
                                >
                                    {isAnimating ? '暂停动画' : '播放行走动画'}
                                </Button>
                                <Button icon={<ReloadOutlined />} onClick={resetJoints} block>
                                    重置姿态
                                </Button>
                            </Space>
                        </Card>

                        {/* 预设姿态 */}
                        <Card size="small" title={<><EyeOutlined /> 预设姿态</>}>
                            <Space wrap>
                                <Button size="small" onClick={() => applyPreset('stand')}>站立</Button>
                                <Button size="small" onClick={() => applyPreset('walk')}>行走</Button>
                                <Button size="small" onClick={() => applyPreset('squat')}>下蹲</Button>
                                <Button size="small" onClick={() => applyPreset('arms_up')}>举手</Button>
                            </Space>
                        </Card>

                        <Card size="small" title="准 CAD 装配视图">
                            <Space direction="vertical" style={{ width: '100%' }} size="small">
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <Text>准CAD拆解</Text>
                                    <Switch
                                        aria-label="准CAD拆解"
                                        checked={cadExplodeEnabled}
                                        onChange={setCadExplodeEnabled}
                                        checkedChildren="开"
                                        unCheckedChildren="关"
                                    />
                                </div>

                                {isAssemblyLoading && (
                                    <Text type="secondary">装配视图加载中...</Text>
                                )}
                                {assemblyError && !isAssemblyLoading && (
                                    <Text type="danger">装配数据加载失败，已回退默认视图</Text>
                                )}

                                {!isAssemblyLoading && !assemblyError && (
                                    <>
                                        <Text type="secondary">工程视角</Text>
                                        <Space wrap>
                                            {explodeViewOptions.map(option => (
                                                <Button
                                                    key={option.id}
                                                    size="small"
                                                    type={selectedExplodeViewId === option.id ? 'primary' : 'default'}
                                                    onClick={() => setSelectedExplodeViewId(option.id)}
                                                >
                                                    {option.label}
                                                </Button>
                                            ))}
                                        </Space>

                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <Text type="secondary">爆炸步骤</Text>
                                            <Tag color={authoredExplodeActive ? 'blue' : 'default'}>
                                                {explodeStepIndex}/{maxExplodeStep}
                                            </Tag>
                                        </div>

                                        <Space>
                                            <Button
                                                size="small"
                                                onClick={() => setExplodeStepIndex(step => Math.max(0, step - 1))}
                                                disabled={!cadExplodeEnabled || explodeStepIndex === 0}
                                            >
                                                上一步
                                            </Button>
                                            <Button
                                                size="small"
                                                onClick={() => setExplodeStepIndex(step => Math.min(maxExplodeStep, step + 1))}
                                                disabled={!cadExplodeEnabled || explodeStepIndex >= maxExplodeStep}
                                            >
                                                下一步
                                            </Button>
                                        </Space>

                                        <Text type="secondary">
                                            {focusedAssemblyNode
                                                ? `当前聚焦总成：${focusedAssemblyNode}`
                                                : '当前使用默认总览视角'}
                                        </Text>
                                    </>
                                )}
                            </Space>
                        </Card>

                        {/* 关节控制 */}
                        <Card
                            size="small"
                            title={<><SettingOutlined /> 关节控制</>}
                            extra={
                                <Segmented
                                    size="small"
                                    value={selectedGroup}
                                    onChange={v => setSelectedGroup(v as string)}
                                    options={[
                                        { label: '躯干', value: 'torso' },
                                        { label: '左腿', value: 'leftLeg' },
                                        { label: '右腿', value: 'rightLeg' },
                                        { label: '左臂', value: 'leftArm' },
                                        { label: '右臂', value: 'rightArm' },
                                    ]}
                                />
                            }
                        >
                            <Space direction="vertical" style={{ width: '100%' }} size="small">
                                {currentJoints.map(joint => (
                                    <div key={joint.name}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                                            <Text style={{ fontSize: 12 }}>{joint.label}</Text>
                                            <Space>
                                                <Text type="secondary" style={{ fontSize: 12 }}>
                                                    {(jointAngles[joint.name] ?? 0).toFixed(2)} rad
                                                </Text>
                                                <Switch
                                                    size="small"
                                                    checked={faultJoints.includes(joint.name)}
                                                    onChange={() => toggleFault(joint.name)}
                                                    checkedChildren="故障"
                                                    unCheckedChildren=""
                                                />
                                            </Space>
                                        </div>
                                        <Slider
                                            min={joint.min}
                                            max={joint.max}
                                            step={0.01}
                                            value={jointAngles[joint.name] ?? 0}
                                            onChange={v => updateJoint(joint.name, v)}
                                            disabled={isAnimating}
                                        />
                                    </div>
                                ))}
                            </Space>
                        </Card>
                    </Space>
                </Col>

                {/* 中间：3D 视图 */}
                <Col xs={24} lg={18} style={{ height: '100%' }}>
                    <Card
                        size="small"
                        style={{ height: '100%' }}
                        styles={{ body: { height: 'calc(100% - 40px)', padding: 0 } }}
                        title="3D 机器人视图"
                        extra={
                            <Space>
                                <Text type="secondary">🖱️ 拖拽旋转 | 滚轮缩放</Text>
                            </Space>
                        }
                    >
                        {robotId ? (
                            <Atom01Viewer
                                width="100%"
                                height="100%"
                                robotId={robotId}
                                cameraPosition={viewerPosition}
                                cameraProjection={viewerProjection}
                                cameraTarget={viewerTarget}
                                explodeAmount={authoredExplodeActive ? 1 : 0}
                                explodeStepIndex={authoredExplodeActive ? explodeStepIndex : null}
                                interactiveMode={true}
                                jointAngles={jointAngles}
                                faultJoints={faultJoints}
                                scale={2}
                                showGrid={true}
                                showSubParts={authoredExplodeActive}
                                subPartEnabledNames={focusedAssemblyNode ? [focusedAssemblyNode] : undefined}
                            />
                        ) : (
                            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#4fc3f7', fontSize: 14 }}>
                                请先选择机器人
                            </div>
                        )}
                    </Card>
                </Col>
            </Row>
        </div>
    );
}

export default Atom01DemoPage;
