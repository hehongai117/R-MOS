/**
 * 3D 机器人模型常量定义
 * 
 * 定义机器人骨骼结构、关节映射、尺寸和材质配置
 */
import * as THREE from 'three';

// ===== 配置开关 =====

/** 是否使用占位符模型（三维扫描模型上传后设为 false） */
export const USE_PLACEHOLDER = true;

/** 模型基础路径 */
const MODEL_BASE_URL = import.meta.env.VITE_MODEL_BASE_URL || '/models';
export const MODEL_BASE_PATH = `${MODEL_BASE_URL}/humanoid`;

// ===== 关节定义 =====

export interface JointDefinition {
    id: string;
    name: string;
    nameCn: string;
    parent: string;
    axis: 'x' | 'y' | 'z' | 'xy' | 'xz' | 'yz';
    limits: [number, number]; // 角度范围（度）
    defaultAngle: number;
}

export const JOINT_DEFINITIONS: JointDefinition[] = [
    { id: 'J1', name: 'head', nameCn: '头部', parent: 'torso_top', axis: 'y', limits: [-90, 90], defaultAngle: 0 },
    { id: 'J2', name: 'shoulder_left', nameCn: '左肩', parent: 'torso', axis: 'xz', limits: [-180, 180], defaultAngle: 0 },
    { id: 'J3', name: 'elbow_left', nameCn: '左肘', parent: 'upper_arm_left', axis: 'x', limits: [0, 150], defaultAngle: 0 },
    { id: 'J4', name: 'shoulder_right', nameCn: '右肩', parent: 'torso', axis: 'xz', limits: [-180, 180], defaultAngle: 0 },
    { id: 'J5', name: 'elbow_right', nameCn: '右肘', parent: 'upper_arm_right', axis: 'x', limits: [0, 150], defaultAngle: 0 },
    { id: 'J6', name: 'hip_left', nameCn: '左髋', parent: 'torso_bottom', axis: 'xz', limits: [-45, 120], defaultAngle: 0 },
    { id: 'J7', name: 'knee_left', nameCn: '左膝', parent: 'thigh_left', axis: 'x', limits: [0, 150], defaultAngle: 0 },
    { id: 'J8', name: 'hip_right', nameCn: '右髋', parent: 'torso_bottom', axis: 'xz', limits: [-45, 120], defaultAngle: 0 },
    { id: 'J9', name: 'knee_right', nameCn: '右膝', parent: 'thigh_right', axis: 'x', limits: [0, 150], defaultAngle: 0 },
    { id: 'J10', name: 'waist', nameCn: '腰部', parent: 'torso', axis: 'y', limits: [-45, 45], defaultAngle: 0 },
];

// ===== 身体部件尺寸（占位符几何体用） =====

export interface BodyPartDimensions {
    type: 'sphere' | 'box' | 'cylinder';
    // 球体
    radius?: number;
    // 立方体
    width?: number;
    height?: number;
    depth?: number;
    // 圆柱体
    radiusTop?: number;
    radiusBottom?: number;
    cylinderHeight?: number;
    // 位置偏移（相对父级）
    position: [number, number, number];
}

export const BODY_DIMENSIONS: Record<string, BodyPartDimensions> = {
    head: {
        type: 'sphere',
        radius: 0.12,
        position: [0, 0.15, 0],
    },
    torso: {
        type: 'box',
        width: 0.35,
        height: 0.5,
        depth: 0.18,
        position: [0, 0, 0],
    },
    upper_arm_left: {
        type: 'cylinder',
        radiusTop: 0.04,
        radiusBottom: 0.04,
        cylinderHeight: 0.28,
        position: [-0.22, 0.15, 0],
    },
    upper_arm_right: {
        type: 'cylinder',
        radiusTop: 0.04,
        radiusBottom: 0.04,
        cylinderHeight: 0.28,
        position: [0.22, 0.15, 0],
    },
    forearm_left: {
        type: 'cylinder',
        radiusTop: 0.035,
        radiusBottom: 0.035,
        cylinderHeight: 0.25,
        position: [0, -0.28, 0],
    },
    forearm_right: {
        type: 'cylinder',
        radiusTop: 0.035,
        radiusBottom: 0.035,
        cylinderHeight: 0.25,
        position: [0, -0.28, 0],
    },
    thigh_left: {
        type: 'cylinder',
        radiusTop: 0.055,
        radiusBottom: 0.05,
        cylinderHeight: 0.38,
        position: [-0.1, -0.45, 0],
    },
    thigh_right: {
        type: 'cylinder',
        radiusTop: 0.055,
        radiusBottom: 0.05,
        cylinderHeight: 0.38,
        position: [0.1, -0.45, 0],
    },
    calf_left: {
        type: 'cylinder',
        radiusTop: 0.045,
        radiusBottom: 0.04,
        cylinderHeight: 0.35,
        position: [0, -0.38, 0],
    },
    calf_right: {
        type: 'cylinder',
        radiusTop: 0.045,
        radiusBottom: 0.04,
        cylinderHeight: 0.35,
        position: [0, -0.38, 0],
    },
};

// ===== 材质配置 =====

export const MATERIALS = {
    /** 正常状态 - 金属蓝 */
    normal: {
        color: new THREE.Color('#4a90d9'),
        metalness: 0.4,
        roughness: 0.6,
    },
    /** 故障状态 - 红色发光 */
    fault: {
        color: new THREE.Color('#ff4d4f'),
        emissive: new THREE.Color('#ff0000'),
        emissiveIntensity: 0.3,
    },
    /** 高亮状态 - 绿色 */
    highlight: {
        color: new THREE.Color('#52c41a'),
        metalness: 0.5,
        roughness: 0.4,
    },
    /** 关节球 - 深灰色 */
    joint: {
        color: new THREE.Color('#404040'),
        metalness: 0.7,
        roughness: 0.3,
    },
};

// ===== 动画配置 =====

export const ANIMATION_CONFIG = {
    /** 关节角度过渡时间（秒） */
    transitionDuration: 0.15,
    /** 故障闪烁频率（毫秒） */
    faultBlinkRate: 500,
    /** 是否启用平滑插值 */
    enableSmoothing: true,
};

// ===== 场景配置 =====

export const SCENE_CONFIG = {
    camera: {
        position: [3, 2, 3] as [number, number, number],
        fov: 50,
        near: 0.1,
        far: 100,
    },
    lights: {
        ambient: { intensity: 0.5 },
        directional: {
            position: [5, 8, 5] as [number, number, number],
            intensity: 0.8,
            castShadow: true,
        },
        hemisphere: {
            skyColor: '#ffffff',
            groundColor: '#444444',
            intensity: 0.3,
        },
    },
    controls: {
        minDistance: 1,
        maxDistance: 15,
        minPolarAngle: 0.1,
        maxPolarAngle: Math.PI * 0.85,
        enablePan: true,
        enableZoom: true,
        autoRotate: false,
        autoRotateSpeed: 1,
    },
    ground: {
        size: 10,
        color: '#1a1a2e',
        gridColor: '#2d2d44',
    },
};

// ===== WebSocket 配置 =====

export const WS_CONFIG = {
    /** WebSocket 地址 */
    url: `${import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'}/ws/robot/status`,
    /** 重连间隔（毫秒） */
    reconnectInterval: 5000,
    /** 最大重连次数 */
    maxReconnectAttempts: 5,
    /** 数据更新节流（毫秒） */
    throttleMs: 50,
};

// ===== 模型文件映射 =====

export const MODEL_FILES: Record<string, string> = {
    head: `${MODEL_BASE_PATH}/body/head.glb`,
    torso: `${MODEL_BASE_PATH}/body/torso.glb`,
    upper_arm_left: `${MODEL_BASE_PATH}/body/upper_arm_left.glb`,
    upper_arm_right: `${MODEL_BASE_PATH}/body/upper_arm_right.glb`,
    forearm_left: `${MODEL_BASE_PATH}/body/forearm_left.glb`,
    forearm_right: `${MODEL_BASE_PATH}/body/forearm_right.glb`,
    thigh_left: `${MODEL_BASE_PATH}/body/thigh_left.glb`,
    thigh_right: `${MODEL_BASE_PATH}/body/thigh_right.glb`,
    calf_left: `${MODEL_BASE_PATH}/body/calf_left.glb`,
    calf_right: `${MODEL_BASE_PATH}/body/calf_right.glb`,
    joint_head: `${MODEL_BASE_PATH}/joints/joint_head.glb`,
    joint_shoulder: `${MODEL_BASE_PATH}/joints/joint_shoulder.glb`,
    joint_elbow: `${MODEL_BASE_PATH}/joints/joint_elbow.glb`,
    joint_hip: `${MODEL_BASE_PATH}/joints/joint_hip.glb`,
    joint_knee: `${MODEL_BASE_PATH}/joints/joint_knee.glb`,
    joint_waist: `${MODEL_BASE_PATH}/joints/joint_waist.glb`,
};
