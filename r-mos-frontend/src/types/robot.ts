/**
 * Robot 相关类型定义
 * 与后端 adapters/schemas.py 完全对齐 (V2.2)
 */

// 机器人运行状态枚举
export enum RobotStatus {
    OFFLINE = 'offline',
    ONLINE = 'online',
    ERROR = 'error',
    MAINTENANCE = 'maintenance',
}

// 关节状态 - 对齐 JointState
export interface JointState {
    joint_id: string                    // 关节唯一标识
    position: number                    // 当前位置（弧度）
    velocity: number                    // 当前速度（弧度/秒）
    torque?: number                     // 当前扭矩（牛·米）
    current?: number                    // 电机电流（安培）
    temperature?: number                // 关节温度（摄氏度）
    error_code?: string                 // 错误码
}

// IMU数据 - 对齐 IMUData
export interface IMUData {
    acceleration: {                     // 加速度 (m/s²)
        x: number
        y: number
        z: number
    }
    angular_velocity: {                 // 角速度 (rad/s)
        x: number
        y: number
        z: number
    }
    orientation?: {                     // 姿态四元数
        x: number
        y: number
        z: number
        w: number
    }
}

// 传感器数据集合 - 对齐 SensorData
export interface SensorData {
    imu?: IMUData                       // IMU数据
    battery?: number                    // 电池电量（%）
    temperature?: number                // 核心温度（℃）
    voltage?: Record<string, number>    // 各模块电压（V）
    pressure?: Record<string, number>   // 压力传感器（Pa）
}

// 遥测数据载荷 - 对齐 TelemetryPayload
export interface TelemetryPayload {
    joints: JointState[]                // 所有关节状态
    sensors: SensorData                 // 传感器数据
    active_faults: string[]             // 当前活动故障列表
}

// WebSocket遥测消息 - 对齐 TelemetryMessage（V2.2完整定义）
export interface TelemetryMessage {
    type: 'telemetry'                   // 消息类型（固定值）
    timestamp: string                   // ISO 8601格式时间戳
    payload: TelemetryPayload           // 遥测数据载荷
}

// 机器人基础信息 - 对齐 RobotInfo
export interface RobotInfo {
    robot_id: string                    // 机器人唯一标识
    model: string                       // 机器人型号
    firmware_version: string            // 固件版本
    runtime_status: RobotStatus         // 运行状态
    last_update: string                 // 最后更新时间
}

// 部件定义 - 对齐 PartDefinition
export interface PartDefinition {
    id: string                          // 部件唯一标识
    name: string                        // 部件显示名称
    type: 'joint' | 'sensor' | 'power_module' // 部件类型
}

// 机器人结构描述 - 对齐 RobotStructure
export interface RobotStructure {
    joints: PartDefinition[]            // 关节列表
    sensors: PartDefinition[]           // 传感器列表
    power_modules: PartDefinition[]     // 电源模块列表
}

// 故障注入结果 - 对齐 FaultInjectionResult
export interface FaultInjectionResult {
    success: boolean                    // 是否成功
    fault_code: string                  // 故障代码
    target_part: string                 // 目标部件
    severity: 'low' | 'medium' | 'high' // 严重程度
    injected_at: string                 // 注入时间
    message?: string                    // 附加信息
}

// 故障清除结果
export interface FaultClearResult {
    success: boolean
    cleared_faults: string[]
    message?: string
}

// Adapter信息响应
export interface AdapterInfoResponse {
    adapter_type: string
    robot_info: RobotInfo
    connected: boolean
    capabilities: string[]
}
