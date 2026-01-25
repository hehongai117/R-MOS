/**
 * @description 裁决系统类型定义
 * @module adjudication/types/adjudication
 * 
 * 基于 R-MOS 裁决级规范文档 V3.0
 */

// ============================================================
// 1. 零件相关类型
// ============================================================

/** 零件类型枚举 */
export enum PartCategory {
  FRAME = 'frame',       // 骨架/连杆
  COVER = 'cover',       // 外壳/软胶
  SCREW = 'screw',       // 螺丝
  NUT = 'nut',           // 螺母
  MOTOR = 'motor',       // 电机
  BEARING = 'bearing',   // 轴承
  PCB = 'pcb',           // 电路板
  WIRE = 'wire',         // 线束
  TOOL = 'tool'          // 工具
}

/** 零件数据结构 */
export interface Part {
  id: string;                           // 唯一标识
  category: PartCategory;               // 类型
  bomCode: string;                      // BOM 编码 (ATOM-01-xxx)
  displayName: string;                  // 显示名称
  modelPath: string;                    // GLB 模型路径
  
  // 空间属性
  parentId: string | null;              // 父零件 ID
  localPosition: [number, number, number];  // 相对父零件位置
  localRotation: [number, number, number];  // 相对父零件旋转
  
  // 螺丝专属属性
  screwSpec?: ScrewSpec;
}

/** 螺丝规格 */
export interface ScrewSpec {
  type: string;                       // 'M3×10'
  pitch: number;                      // 螺距 (mm)
  threadLength: number;               // 螺纹长度 (mm)
  requiredTool: string;               // 所需工具 ID
  torque: number;                     // 扭矩 (Nm)
}

// ============================================================
// 2. 约束相关类型
// ============================================================

/** 约束类型枚举 */
export enum ConstraintType {
  // 紧固约束
  FASTENED_BY = 'fastened_by',      // 被螺丝/螺母固定
  
  // 空间约束
  COVERED_BY = 'covered_by',        // 被覆盖（必须先拆覆盖物）
  BLOCKED_BY = 'blocked_by',        // 被阻挡（几何干涉）
  
  // 机构约束
  LOCKED_BY = 'locked_by',          // 被机构锁止
  HINGED_TO = 'hinged_to',          // 铰接于（可旋转但不可分离）
  
  // 连接约束
  WIRED_TO = 'wired_to',            // 线束连接
  PLUGGED_TO = 'plugged_to'         // 插接连接
}

/** 紧固约束参数 */
export interface FastenedByParams {
  screwIds: string[];                 // 螺丝 ID 列表
  minScrewsToRelease: number;         // 需要拆除的最少螺丝数
}

/** 覆盖约束参数 */
export interface CoveredByParams {
  coverPartId: string;                // 覆盖物零件 ID
  coverType: 'full' | 'partial';      // 完全覆盖/部分覆盖
}

/** 阻挡约束参数 */
export interface BlockedByParams {
  blockingPartId: string;             // 阻挡物零件 ID
  blockingDirection: [number, number, number];  // 阻挡方向向量
}

/** 解除条件类型 */
export type ReleaseConditionType = 
  | 'all_screws_removed' 
  | 'cover_removed' 
  | 'unlocked' 
  | 'unplugged';

/** 解除条件 */
export interface ReleaseCondition {
  type: ReleaseConditionType;
  
  // 具体条件
  requiredActions: {
    action: ActionType;
    targetParts: string[];
    allRequired: boolean;             // true=全部完成，false=任一完成
  }[];
}

/** 约束数据结构 */
export interface Constraint {
  id: string;                         // 约束 ID
  type: ConstraintType;               // 约束类型
  
  // 约束双方
  constrainedPart: string;            // 被约束零件 ID
  constrainingPart: string;           // 施加约束的零件 ID
  
  // 约束参数（根据类型不同）
  params: FastenedByParams | CoveredByParams | BlockedByParams;
  
  // 解除条件
  releaseCondition: ReleaseCondition;
  
  // 当前状态
  isActive: boolean;                  // 约束是否生效
}

// ============================================================
// 3. 行为相关类型
// ============================================================

/** 行为类型枚举 */
export enum ActionType {
  // 螺丝操作
  SELECT_TOOL = 'select_tool',           // 选择工具
  APPROACH_SCREW = 'approach_screw',     // 工具接近螺丝
  ROTATE_SCREW = 'rotate_screw',         // 旋转螺丝
  EXTRACT_SCREW = 'extract_screw',       // 抽离螺丝
  COLLECT_SCREW = 'collect_screw',       // 收纳螺丝
  
  // 零件操作
  DETACH_PART = 'detach_part',           // 分离零件
  REMOVE_PART = 'remove_part',           // 移除零件
  FLIP_PART = 'flip_part',               // 翻转零件
  
  // 线束操作
  UNPLUG_CONNECTOR = 'unplug_connector', // 拔出连接器
  
  // 视图操作
  FOCUS_CAMERA = 'focus_camera',         // 聚焦视角
  ENABLE_XRAY = 'enable_xray'            // 启用透视
}

/** 螺丝状态枚举 */
export enum ScrewState {
  SEATED = 'seated',           // 完全拧入
  LOOSENING = 'loosening',     // 正在旋出
  EXTRACTED = 'extracted',     // 完全退出
  REMOVED = 'removed'          // 已移除（飞入收纳盒）
}

/** 零件状态 */
export interface PartState {
  isRemoved: boolean;
  isDetached: boolean;
  position?: [number, number, number];
}

/** 螺丝实例状态 */
export interface ScrewInstanceState {
  screwId: string;
  state: ScrewState;
  currentRotations: number;      // 当前已旋转圈数
  zDisplacement: number;         // Z 轴位移 (mm)
}

// ============================================================
// 4. 裁决相关类型
// ============================================================

/** 裁决结果枚举 */
export enum AdjudicationResult {
  ALLOWED = 'allowed',                  // 允许操作
  BLOCKED = 'blocked',                  // 阻断操作（硬性约束未解除）
  WARNING = 'warning',                  // 警告但允许继续（软性约束）
  TOOL_MISMATCH = 'tool_mismatch',      // 工具不匹配
  INCOMPLETE = 'incomplete'             // 操作未完成
}

/** 裁决报告 */
export interface AdjudicationReport {
  result: AdjudicationResult;
  targetPart: string;
  reason: string;                       // 人类可读原因
  reasonCode: string;                   // 错误码
  blockingConstraints: Constraint[];    // 阻止操作的约束列表
  requiredActions: string[];            // 需要先执行的操作
  timestamp: number;
  // 模式增强信息
  hint?: string;                        // 教学提示
  allowRetry?: boolean;                 // 是否允许重试
  shouldSummarize?: boolean;            // 考试结算信号
}

// ============================================================
// 5. 系统状态类型
// ============================================================

/** 系统状态枚举 */
export enum SystemState {
  // 装配状态
  FULLY_ASSEMBLED = 'fully_assembled',           // 完全装配
  
  // 拆卸进行中
  PARTIAL_DISASSEMBLY = 'partial_disassembly',   // 部分拆卸
  
  // 故障暴露
  FAULT_EXPOSED = 'fault_exposed',               // 故障点暴露
  
  // 维修就绪
  REPAIR_READY = 'repair_ready',                 // 可进行维修
  
  // 重新装配
  REASSEMBLING = 'reassembling',                 // 重新装配中
  
  // 验证状态
  VERIFICATION = 'verification',                  // 功能验证中

  // 致命失败
  FAILED_FATAL = 'failed_fatal'                   // 致命失败（系统锁定，仅允许重置）
}

/** 操作模式 */
export type OperationMode = 'teaching' | 'exam' | 'maintenance';

/** 操作记录 */
export interface ActionRecord {
  id: string;
  action: ActionType;
  targetParts: string[];
  toolId: string | null;
  timestamp: number;
  result: AdjudicationResult;
  stateSnapshot: string;                // JSON 序列化的状态快照
}

/** 全局状态 */
export interface AdjudicationState {
  // 系统状态
  systemState: SystemState;

  // 操作模式
  operationMode: OperationMode;
  
  // 零件状态
  partStates: Record<string, PartState>;
  
  // 螺丝状态
  screwStates: Record<string, ScrewInstanceState>;
  
  // 约束状态
  constraintStates: Record<string, boolean>;
  
  // 当前工具
  currentToolId: string | null;
  
  // 操作历史
  actionHistory: ActionRecord[];
}

// ============================================================
// 6. SOP 相关类型（裁决级）
// ============================================================

/** 前置条件类型 */
export enum PreconditionType {
  PART_REMOVED = 'part_removed',         // 指定零件已移除
  PART_ACCESSIBLE = 'part_accessible',   // 指定零件可访问
  TOOL_EQUIPPED = 'tool_equipped',       // 指定工具已装备
  SCREWS_REMOVED = 'screws_removed',     // 指定螺丝已拆除
  STATE_REACHED = 'state_reached',       // 达到指定状态
  PREVIOUS_STEP_COMPLETE = 'prev_step'   // 前一步已完成
}

/** SOP 前置条件 */
export interface SOPPrecondition {
  type: PreconditionType;
  params: Record<string, unknown>;
  errorMessage: string;                  // 不满足时的提示
}

/** 验证类型 */
export enum ValidationType {
  ALL_SCREWS_EXTRACTED = 'all_screws_extracted',   // 所有螺丝完全退出
  PART_DETACHED = 'part_detached',                 // 零件已分离
  TOOL_MATCHED = 'tool_matched',                   // 工具匹配
  GEOMETRY_CHECK = 'geometry_check',               // 几何条件满足
  STATE_CHECK = 'state_check'                      // 状态检查
}

/** SOP 验证 */
export interface SOPValidation {
  type: ValidationType;
  params: Record<string, unknown>;
  isRequired: boolean;                   // 是否必须通过
}

/** 错误分类 */
export enum ErrorCategory {
  WRONG_ORDER = 'wrong_order',           // 顺序错误
  WRONG_TOOL = 'wrong_tool',             // 工具错误
  INCOMPLETE_ACTION = 'incomplete',      // 操作未完成
  CONSTRAINT_VIOLATION = 'constraint',   // 约束违反
  UNSAFE_OPERATION = 'unsafe'            // 不安全操作
}

/** SOP 失败原因 */
export interface SOPFailureReason {
  code: string;                          // "ERR_WRONG_ORDER"
  category: ErrorCategory;               // 错误分类
  description: string;                   // 人类可读描述
  severity: 'critical' | 'major' | 'minor';
  
  // 教学/考试模式差异
  teachingResponse: {
    showHint: boolean;
    hintContent: string;
    allowRetry: boolean;
  };
  
  examResponse: {
    deductPoints: number;
    allowContinue: boolean;
    recordToReport: boolean;
  };
}

/** SOP 步骤（裁决级） */
export interface SOPStepAdjudication {
  stepId: string;                        // "step_003"
  stepIndex: number;                     // 3
  
  // 步骤内容
  title: string;                         // "拆卸躯干固定螺丝"
  description: string;                   // 详细说明
  
  // 目标零件/操作
  action: ActionType;                    // ROTATE_SCREW
  targetParts: string[];                 // ["screw_torso_m3x10_001", ...]
  
  // 工具要求
  requiredTool: string | null;           // "hex_2.5"
  
  // 前置条件（必须全部满足）
  preconditions: SOPPrecondition[];
  
  // 完成验证（必须全部通过）
  validations: SOPValidation[];
  
  // 错误裁决
  failureReasons: SOPFailureReason[];
  
  // 状态转移
  onSuccess: {
    nextStepId: string;
    stateTransition: SystemState | null;
  };
  
  onFailure: {
    action: 'block' | 'warn' | 'retry';
    message: string;
  };
  
  // 不可逆标记
  isIrreversible?: boolean;

  // 失败即致命
  fatalOnFailure?: boolean;
}

/** SOP 脚本（裁决级） */
export interface SOPScriptAdjudication {
  sopId: string;
  title: string;
  version: string;
  targetModule: string;
  estimatedTime: number;                 // 秒
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  steps: SOPStepAdjudication[];
}

// ============================================================
// 7. 几何判定类型
// ============================================================

/** 螺丝几何条件 */
export interface ScrewGeometryCondition {
  // 完全退出判定
  extractedCondition: {
    minZDisplacement: number;   // Z 轴最小位移 (mm)
  };
  
  // 旋转判定
  rotationCondition: {
    totalRotations: number;     // 总旋转圈数
  };
}

/** Atom01 螺丝几何条件表 */
export const SCREW_GEOMETRY_CONDITIONS: Record<string, ScrewGeometryCondition> = {
  'M3×6':  { extractedCondition: { minZDisplacement: 7 },  rotationCondition: { totalRotations: 12 } },
  'M3×8':  { extractedCondition: { minZDisplacement: 9 },  rotationCondition: { totalRotations: 16 } },
  'M3×10': { extractedCondition: { minZDisplacement: 11 }, rotationCondition: { totalRotations: 20 } },
  'M3×12': { extractedCondition: { minZDisplacement: 13 }, rotationCondition: { totalRotations: 24 } },
  'M3×16': { extractedCondition: { minZDisplacement: 17 }, rotationCondition: { totalRotations: 32 } },
  'M4×8':  { extractedCondition: { minZDisplacement: 9 },  rotationCondition: { totalRotations: 11 } },
  'M4×10': { extractedCondition: { minZDisplacement: 11 }, rotationCondition: { totalRotations: 14 } },
  'M4×12': { extractedCondition: { minZDisplacement: 13 }, rotationCondition: { totalRotations: 17 } },
  'M4×16': { extractedCondition: { minZDisplacement: 17 }, rotationCondition: { totalRotations: 23 } },
  'M5×10': { extractedCondition: { minZDisplacement: 11 }, rotationCondition: { totalRotations: 13 } },
  'M6×20': { extractedCondition: { minZDisplacement: 21 }, rotationCondition: { totalRotations: 20 } },
};
