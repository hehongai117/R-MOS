/**
 * 类型定义统一导出入口
 */

// SOP 相关类型
export type {
    SOPStep,
    SOPBase,
    SOP,
    SOPListItem,
    SOPListResponse,
    SOPCreateRequest,
    SOPUpdateRequest,
    SOPDeleteWarning,
    SOPDeleteResponse,
} from './sop'

// Task 相关类型
export { TaskStatus } from './task'
export type {
    Task,
    TaskWithSOP,
    TaskCreateRequest,
    StepExecutionRequest,
    StepExecutionResponse,
    TaskStatusResponse,
} from './task'

// Robot 相关类型
export { RobotStatus } from './robot'
export type {
    JointState,
    IMUData,
    SensorData,
    TelemetryPayload,
    TelemetryMessage,
    RobotInfo,
    PartDefinition,
    RobotStructure,
    FaultInjectionResult,
    FaultClearResult,
    AdapterInfoResponse,
} from './robot'

// Fault 相关类型
export type {
    FaultCaseBase,
    FaultCase,
    FaultCaseListItem,
    FaultCaseListResponse,
    FaultCaseCreateRequest,
    FaultCaseUpdateRequest,
} from './fault'

// Report 相关类型
export type {
    ScoreBreakdown,
    StepScore,
    TaskReport,
    TaskReportSummary,
} from './report'

// API 通用类型
export type {
    ErrorResponse,
    BusinessRuleError,
    NotFoundError,
    ValidationError,
    AdapterConnectionError,
    PaginatedResponse,
    SuccessResponse,
    HealthCheckResponse,
} from './api'
