# R-MOS 机器人数字孪生维保系统｜裁决级规范文档

**文档版本**: V3.0（裁决级）  
**更新日期**: 2026-01-21  
**文档性质**: **系统唯一裁决源**  
**适用对象**: Atom01 人形机器人

---

## 0. 文档裁决声明

### 0.1 文档定位

本文档是 **R-MOS 数字孪生维保系统的唯一裁决源**。

**优先级高于**：
- UI 视觉实现
- 动画效果
- 工程便利性
- 前端开发习惯

**当实现与本文档冲突时，以本文档为准。**

### 0.2 不可违反原则

所有维保操作必须满足三个条件：

| 条件 | 含义 | 验证方式 |
|------|------|----------|
| **可判定** | 操作是否成功有明确标准 | DecisionEngine 返回 true/false |
| **可验证** | 成功判定基于可计算的几何/状态数据 | 非观感、非时间轴 |
| **可回溯** | 任何操作可生成记录用于教学/考核/报告 | ActionLog + StateHistory |

**无法满足以上条件的功能 = 禁止实现。**

### 0.3 禁止事项清单

| 禁止行为 | 正确做法 |
|----------|----------|
| ❌ 动画播放完 = 操作完成 | ✅ 状态机验证通过 = 操作完成 |
| ❌ SOP 作为播放脚本 | ✅ SOP 作为可执行状态机 |
| ❌ 隐含装配逻辑 | ✅ 所有约束数据化存储 |
| ❌ 无法判定对错的实现 | ✅ 必须能判错/给原因/阻止继续 |
| ❌ 纯时间轴完成判定 | ✅ 几何/状态条件判定 |

---

## A. 裁决不可违反条款（System Invariants）

### A.1 裁决优先级公理

* 裁决结果的优先级高于：

  * 动画播放状态
  * UI 交互结果
  * 用户操作意图
* 任何与裁决结果冲突的系统行为，均视为系统错误。

### A.2 完成判定公理

* 任何操作的“完成”必须同时满足：

  * 行为语义完成
  * 结构约束解除
  * 几何判定通过
* 若三者之一未满足，则该操作状态为 **未完成（INCOMPLETE）**。

### A.3 裁决不可绕行公理

* 系统不得提供以下能力：

  * 手动跳过裁决结果
  * 强制推进 SOP 状态
  * 通过动画结束直接标记完成
* 任何绕过裁决层的实现，视为系统非法实现。

### A.4 裁决结果法律效力

* 裁决结果必须是确定性的，不得依赖：

  * UI 配置
  * 运行模式切换
* 同一输入条件下，裁决结果必须全系统一致。

---

## B. 结构约束裁决强制规则（Constraint Enforcement Rules）

### B.1 约束的裁决地位

* 结构约束不是提示信息，而是**强制裁决条件**。
* 任何 ACTIVE 状态的约束，均具有阻断效力。

### B.2 统一因果规则（强制）

> 若某约束满足以下条件：
>
> * 状态为 ACTIVE
> * 其 constrainedPart 被当前 Action 直接或间接影响
>
> 则系统裁决结果必须为 **BLOCKED**。

该规则不允许例外，不允许弱化为 WARNING。

### B.3 约束解除判定

* 约束解除必须满足其定义的解除条件：

  * 指定紧固件已完全移除
  * 覆盖件已处于分离状态
  * 干涉体不再产生几何重叠
* 未显式解除的约束，不得推断为已解除。

### B.4 约束失败的系统后果

* 当裁决结果为 BLOCKED 时：

  * SOP 状态不得前进
  * 动画不得继续播放
  * 系统必须返回失败原因

---

## C. SOP 状态机中的不可逆与致命裁决

### C.1 不可逆步骤（Irreversible Step）定义

* 不可逆步骤指：

  * 一旦执行，将导致结构状态发生不可回退变化
  * 回退将违反真实维保安全或逻辑

示例：

* 强行分离仍被紧固的模组
* 带电状态下拆除关键连接件

### C.2 不可逆步骤裁决规则

* 不可逆步骤一旦进入 EXECUTING 状态：

  * 不允许回滚至前一状态
  * 若验证失败，必须进入 FAILURE 状态

### C.3 致命错误（Fatal Failure）定义

致命错误满足任一条件：

* 违反 ACTIVE 结构约束
* 在不可逆步骤中发生失败
* 使用错误工具作用于关键部件

### C.4 致命错误的系统行为

* 一旦判定为 Fatal Failure：

  * 当前 SOP 立即终止
  * 状态标记为 FAILED_FATAL
  * 禁止继续任何后续操作

### C.5 模式无关性原则

* 不可逆步骤与致命错误规则：

  * 不因 教学 / 考试 / 维保 模式而改变
  * 仅影响系统对用户的反馈形式

---

## 1. 系统能力四级体系

### 1.1 能力层级定义

```
┌─────────────────────────────────────────────────────────────┐
│  L4: SOP 状态机层 (Executable SOP)                         │
│      - 可执行的状态机                                       │
│      - 前置条件 + 操作 + 验证 + 错误裁决                    │
├─────────────────────────────────────────────────────────────┤
│  L3: 行为语义层 (Action Semantics)                         │
│      - 行为原子定义（rotate_screw, extract_screw...）       │
│      - 行为 → 状态变化映射                                  │
├─────────────────────────────────────────────────────────────┤
│  L2: 几何判定层 (Geometry Decision)                        │
│      - 可计算的几何判定                                     │
│      - 螺丝退出判定、干涉检测                               │
├─────────────────────────────────────────────────────────────┤
│  L1: 结构约束层 (Constraint Graph)                         │
│      - 零件唯一标识                                         │
│      - 装配约束关系图                                       │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 系统不承担的能力

为防止过度设计，以下能力**明确不做**：

- ❌ 真实物理仿真（材料形变、碰撞力计算）
- ❌ 材料疲劳/寿命计算
- ❌ 非结构性故障推断（电路故障、软件故障）
- ❌ 实时传感器数据融合（V1.0 不做）

---

## 2. L1: 结构约束层（Constraint Graph）

> **这是整套系统的根节点，所有上层逻辑依赖于此。**

### 2.1 零件唯一性规范

#### 2.1.1 PartID 命名规则

```
格式: {category}_{location}_{name}_{index}

示例:
- frame_torso_chest_rear_splint_001    # 胸腔夹板后
- screw_torso_m3x10_001                # 躯干 M3×10 螺丝 #1
- motor_left_hip_yaw_001               # 左髋 Yaw 电机
```

#### 2.1.2 零件类型枚举

```typescript
enum PartCategory {
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
```

#### 2.1.3 零件数据结构 (Part Schema)

```typescript
interface Part {
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
  screwSpec?: {
    type: string;                       // 'M3×10'
    pitch: number;                      // 螺距 (mm)
    threadLength: number;               // 螺纹长度 (mm)
    requiredTool: string;               // 所需工具 ID
    torque: number;                     // 扭矩 (Nm)
  };
}
```

### 2.2 装配约束模型（Constraint Graph）

#### 2.2.1 约束类型枚举

```typescript
enum ConstraintType {
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
```

#### 2.2.2 约束数据结构 (Constraint Schema)

```typescript
interface Constraint {
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

// 紧固约束参数
interface FastenedByParams {
  screwIds: string[];                 // 螺丝 ID 列表
  minScrewsToRelease: number;         // 需要拆除的最少螺丝数
}

// 覆盖约束参数
interface CoveredByParams {
  coverPartId: string;                // 覆盖物零件 ID
  coverType: 'full' | 'partial';      // 完全覆盖/部分覆盖
}

// 阻挡约束参数
interface BlockedByParams {
  blockingPartId: string;             // 阻挡物零件 ID
  blockingDirection: [number, number, number];  // 阻挡方向向量
}
```

#### 2.2.3 解除条件定义

```typescript
interface ReleaseCondition {
  type: 'all_screws_removed' | 'cover_removed' | 'unlocked' | 'unplugged';
  
  // 具体条件
  requiredActions: {
    action: ActionType;
    targetParts: string[];
    allRequired: boolean;             // true=全部完成，false=任一完成
  }[];
}
```

### 2.3 拆卸合法性裁决规则

#### 2.3.1 裁决时机

在以下时机触发拆卸合法性裁决：

| 时机 | 触发条件 |
|------|----------|
| 尝试选中 | 用户点击/悬停零件时 |
| 尝试操作 | 用户选择工具并尝试操作时 |
| 完成判定 | 操作动画结束前回调时 |

#### 2.3.2 裁决结果类型

```typescript
enum AdjudicationResult {
  ALLOWED = 'allowed',                  // 允许操作
  BLOCKED = 'blocked',                  // 阻断操作（硬性约束未解除）
  WARNING = 'warning',                  // 警告但允许继续（软性约束）
  TOOL_MISMATCH = 'tool_mismatch',      // 工具不匹配
  INCOMPLETE = 'incomplete'             // 操作未完成
}

interface AdjudicationReport {
  result: AdjudicationResult;
  targetPart: string;
  reason: string;                       // 人类可读原因
  reasonCode: string;                   // 错误码
  blockingConstraints: Constraint[];    // 阻止操作的约束列表
  requiredActions: string[];            // 需要先执行的操作
}
```

#### 2.3.3 典型裁决场景

| 场景 | 裁决结果 | 原因 | 系统响应 |
|------|----------|------|----------|
| 拆卸被覆盖的零件 | BLOCKED | 零件被外壳覆盖 | "请先拆卸 {覆盖物名称}" |
| 螺丝未完全拆除就拆零件 | BLOCKED | 紧固约束未解除 | "还有 {n} 颗螺丝未拆除" |
| 工具规格不匹配 | TOOL_MISMATCH | M3 螺丝需要 H2.5 扳手 | "需要 H2.5 内六角扳手" |
| 螺丝只旋转了 2 圈 | INCOMPLETE | Z 轴位移不足 | "螺丝未完全退出" |

---

## 3. L2: 几何判定层（Geometry Decision）

### 3.1 坐标系与参考系标准

```typescript
// 世界坐标系（Three.js 标准）
// X: 右, Y: 上, Z: 前
// 单位: 米 (m)

// 零件局部坐标系
// 原点: 零件几何中心
// 轴向: 继承父零件旋转

// 螺丝轴线坐标系
// Z+: 螺丝旋出方向
// 旋转正方向: 逆时针 (CCW) = 旋出
```

### 3.2 螺丝状态几何判定

#### 3.2.1 螺丝状态定义

```typescript
enum ScrewState {
  SEATED = 'seated',           // 完全拧入
  LOOSENING = 'loosening',     // 正在旋出
  EXTRACTED = 'extracted',     // 完全退出
  REMOVED = 'removed'          // 已移除（飞入收纳盒）
}
```

#### 3.2.2 状态转移几何条件

```typescript
interface ScrewGeometryCondition {
  // 完全退出判定
  extractedCondition: {
    minZDisplacement: number;   // Z 轴最小位移 (mm)
    // 公式: minZDisplacement = threadLength + 1mm 安全余量
  };
  
  // 旋转判定
  rotationCondition: {
    totalRotations: number;     // 总旋转圈数
    // 公式: totalRotations = threadLength / pitch
  };
}

// Atom01 螺丝几何条件表
const SCREW_GEOMETRY_CONDITIONS: Record<string, ScrewGeometryCondition> = {
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
```

### 3.3 零件可分离几何判定

```typescript
interface DetachmentCondition {
  // 所有紧固约束解除
  allFasteningsReleased: boolean;
  
  // 无几何干涉
  noGeometricInterference: boolean;
  
  // 无覆盖约束
  noCoverConstraint: boolean;
}

function canDetachPart(partId: string, state: SystemState): AdjudicationReport {
  const constraints = getActiveConstraints(partId, state);
  
  const blockingConstraints = constraints.filter(c => {
    switch (c.type) {
      case ConstraintType.FASTENED_BY:
        return !allScrewsRemoved(c.params.screwIds, state);
      case ConstraintType.COVERED_BY:
        return !isPartRemoved(c.params.coverPartId, state);
      case ConstraintType.BLOCKED_BY:
        return !isPartRemoved(c.params.blockingPartId, state);
      default:
        return false;
    }
  });
  
  if (blockingConstraints.length > 0) {
    return {
      result: AdjudicationResult.BLOCKED,
      targetPart: partId,
      reason: generateBlockingReason(blockingConstraints),
      reasonCode: 'CONSTRAINT_NOT_RELEASED',
      blockingConstraints,
      requiredActions: generateRequiredActions(blockingConstraints)
    };
  }
  
  return { result: AdjudicationResult.ALLOWED, ... };
}
```

---

## 4. L3: 行为语义层（Action Semantics）

### 4.1 行为原子定义（Action Atoms）

```typescript
enum ActionType {
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
```

### 4.2 行为参数定义

```typescript
interface ActionParams {
  // 螺丝旋转参数
  rotateScrewParams?: {
    screwId: string;
    direction: 'cw' | 'ccw';             // 顺时针/逆时针
    targetRotations: number;             // 目标旋转圈数
    currentRotations: number;            // 当前已旋转圈数
  };
  
  // 工具选择参数
  selectToolParams?: {
    toolId: string;
    previousToolId: string | null;
  };
  
  // 零件分离参数
  detachPartParams?: {
    partId: string;
    direction: [number, number, number]; // 分离方向向量
    distance: number;                    // 分离距离 (m)
  };
}
```

### 4.3 行为 → 状态变化映射

```typescript
interface ActionEffect {
  action: ActionType;
  
  // 前置条件（必须满足才能执行）
  preconditions: Precondition[];
  
  // 状态变更
  stateChanges: StateChange[];
  
  // 成功判定条件
  successCondition: Condition;
  
  // 失败处理
  failureHandler: FailureHandler;
}

// 示例：旋转螺丝的状态变化映射
const ROTATE_SCREW_EFFECT: ActionEffect = {
  action: ActionType.ROTATE_SCREW,
  
  preconditions: [
    { type: 'tool_equipped', toolType: 'hex_key' },
    { type: 'tool_matched', screwSpec: 'current_target' },
    { type: 'screw_accessible', screwId: 'current_target' }
  ],
  
  stateChanges: [
    { 
      target: 'screw.currentRotations', 
      operation: 'increment', 
      value: 'action.targetRotations' 
    },
    { 
      target: 'screw.zDisplacement', 
      operation: 'increment', 
      value: 'action.targetRotations * screw.pitch' 
    }
  ],
  
  successCondition: {
    type: 'geometry_check',
    check: 'screw.zDisplacement >= screw.threadLength'
  },
  
  failureHandler: {
    type: 'incomplete',
    message: '螺丝未完全退出，还需旋转 {remaining} 圈'
  }
};
```

### 4.4 动画与行为的绑定规则（强制）

```typescript
// ❌ 禁止：动画结束 = 操作完成
function onAnimationComplete() {
  setOperationComplete(true);  // 错误！
}

// ✅ 正确：动画回调触发裁决，裁决通过才算完成
function onAnimationComplete() {
  const report = DecisionEngine.adjudicate(currentAction, currentState);
  
  if (report.result === AdjudicationResult.ALLOWED) {
    StateManager.commitStateChange(currentAction);
    setOperationComplete(true);
  } else {
    UIController.showError(report.reason);
    AnimationController.revert(currentAction);
  }
}
```

---

## 5. L4: SOP 状态机层（Executable SOP）

### 5.1 系统状态定义

```typescript
enum SystemState {
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
  VERIFICATION = 'verification'                   // 功能验证中
}
```

### 5.2 SOP Step Schema（规范版）

```typescript
interface SOPStep {
  // 步骤标识
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
}
```

### 5.3 前置条件定义

```typescript
interface SOPPrecondition {
  type: PreconditionType;
  params: Record<string, any>;
  errorMessage: string;                  // 不满足时的提示
}

enum PreconditionType {
  PART_REMOVED = 'part_removed',         // 指定零件已移除
  PART_ACCESSIBLE = 'part_accessible',   // 指定零件可访问
  TOOL_EQUIPPED = 'tool_equipped',       // 指定工具已装备
  SCREWS_REMOVED = 'screws_removed',     // 指定螺丝已拆除
  STATE_REACHED = 'state_reached',       // 达到指定状态
  PREVIOUS_STEP_COMPLETE = 'prev_step'   // 前一步已完成
}

// 示例
const PRECONDITION_EXAMPLE: SOPPrecondition = {
  type: PreconditionType.PART_REMOVED,
  params: { partId: 'cover_torso_front_001' },
  errorMessage: '请先拆卸躯干前盖板'
};
```

### 5.4 完成验证定义

```typescript
interface SOPValidation {
  type: ValidationType;
  params: Record<string, any>;
  isRequired: boolean;                   // 是否必须通过
}

enum ValidationType {
  ALL_SCREWS_EXTRACTED = 'all_screws_extracted',   // 所有螺丝完全退出
  PART_DETACHED = 'part_detached',                 // 零件已分离
  TOOL_MATCHED = 'tool_matched',                   // 工具匹配
  GEOMETRY_CHECK = 'geometry_check',               // 几何条件满足
  STATE_CHECK = 'state_check'                      // 状态检查
}
```

### 5.5 错误裁决定义

```typescript
interface SOPFailureReason {
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

enum ErrorCategory {
  WRONG_ORDER = 'wrong_order',           // 顺序错误
  WRONG_TOOL = 'wrong_tool',             // 工具错误
  INCOMPLETE_ACTION = 'incomplete',      // 操作未完成
  CONSTRAINT_VIOLATION = 'constraint',   // 约束违反
  UNSAFE_OPERATION = 'unsafe'            // 不安全操作
}
```

### 5.6 SOP JSON 完整示例

```json
{
  "sopId": "sop_torso_motor_replacement",
  "title": "躯干电机更换",
  "version": "1.0.0",
  "targetModule": "torso",
  "estimatedTime": 1800,
  "difficulty": "intermediate",
  
  "steps": [
    {
      "stepId": "step_001",
      "stepIndex": 1,
      "title": "选择工具",
      "description": "从工具箱选择 H2.5 内六角扳手",
      "action": "select_tool",
      "targetParts": [],
      "requiredTool": "hex_2.5",
      
      "preconditions": [],
      
      "validations": [
        {
          "type": "tool_equipped",
          "params": { "toolId": "hex_2.5" },
          "isRequired": true
        }
      ],
      
      "failureReasons": [
        {
          "code": "ERR_WRONG_TOOL",
          "category": "wrong_tool",
          "description": "选择了错误的工具",
          "severity": "major",
          "teachingResponse": {
            "showHint": true,
            "hintContent": "躯干螺丝为 M3 规格，需要 H2.5 内六角扳手",
            "allowRetry": true
          },
          "examResponse": {
            "deductPoints": 5,
            "allowContinue": false,
            "recordToReport": true
          }
        }
      ],
      
      "onSuccess": {
        "nextStepId": "step_002",
        "stateTransition": null
      },
      
      "onFailure": {
        "action": "block",
        "message": "请选择正确的工具"
      }
    },
    
    {
      "stepId": "step_002",
      "stepIndex": 2,
      "title": "拆卸躯干固定螺丝",
      "description": "拆卸固定躯干的 4 颗 M3×10 螺丝",
      "action": "rotate_screw",
      "targetParts": [
        "screw_torso_m3x10_001",
        "screw_torso_m3x10_002",
        "screw_torso_m3x10_003",
        "screw_torso_m3x10_004"
      ],
      "requiredTool": "hex_2.5",
      
      "preconditions": [
        {
          "type": "tool_equipped",
          "params": { "toolId": "hex_2.5" },
          "errorMessage": "请先选择 H2.5 内六角扳手"
        }
      ],
      
      "validations": [
        {
          "type": "all_screws_extracted",
          "params": { 
            "screwIds": [
              "screw_torso_m3x10_001",
              "screw_torso_m3x10_002",
              "screw_torso_m3x10_003",
              "screw_torso_m3x10_004"
            ]
          },
          "isRequired": true
        }
      ],
      
      "failureReasons": [
        {
          "code": "ERR_INCOMPLETE",
          "category": "incomplete",
          "description": "螺丝未完全拆除",
          "severity": "major",
          "teachingResponse": {
            "showHint": true,
            "hintContent": "还有 {remaining} 颗螺丝未拆除",
            "allowRetry": true
          },
          "examResponse": {
            "deductPoints": 10,
            "allowContinue": false,
            "recordToReport": true
          }
        }
      ],
      
      "onSuccess": {
        "nextStepId": "step_003",
        "stateTransition": "partial_disassembly"
      },
      
      "onFailure": {
        "action": "block",
        "message": "请完成所有螺丝的拆卸"
      }
    }
  ]
}
```

---

## 6. 错误裁决与评分机制

### 6.1 错误分类体系

| 错误类别 | 代码 | 严重程度 | 考试扣分 |
|----------|------|----------|----------|
| 顺序错误 | ERR_WRONG_ORDER | Critical | -20 |
| 工具错误 | ERR_WRONG_TOOL | Major | -10 |
| 操作未完成 | ERR_INCOMPLETE | Major | -10 |
| 约束违反 | ERR_CONSTRAINT | Critical | -20 |
| 不安全操作 | ERR_UNSAFE | Critical | 终止考试 |

### 6.2 三模式差异对照表

| 行为 | 教学模式 | 考试模式 | 维保模式 |
|------|----------|----------|----------|
| 错误操作 | 提示+允许重试 | 记录扣分+不允许重试 | 提示+记录日志 |
| 跳步操作 | 阻断+显示依赖 | 阻断+重大扣分 | 阻断+显示依赖 |
| 工具不匹配 | 提示正确工具 | 阻断+扣分 | 阻断+提示 |
| 操作超时 | 不限时 | 倒计时扣分 | 不限时 |

### 6.3 裁决报告生成

```typescript
interface AdjudicationReport {
  // 报告元数据
  reportId: string;
  sessionId: string;
  userId: string;
  mode: 'teaching' | 'exam' | 'maintenance';
  timestamp: number;
  
  // SOP 执行情况
  sopId: string;
  sopTitle: string;
  totalSteps: number;
  completedSteps: number;
  
  // 错误记录
  errors: ErrorRecord[];
  
  // 评分（仅考试模式）
  scoring?: {
    totalScore: number;
    maxScore: number;
    deductions: Deduction[];
    grade: 'A' | 'B' | 'C' | 'D' | 'F';
  };
  
  // 时间统计
  timing: {
    startTime: number;
    endTime: number;
    totalDuration: number;
    stepDurations: Record<string, number>;
  };
}
```

---

## 7. 最小垂直切片规范（Mandatory Slice）

### 7.1 验证模块选择：脚部总成

选择脚部总成作为**最小垂直切片**进行完整验证：

| 选择理由 |
|----------|
| 零件数量适中（~20 个） |
| 包含多种约束类型（螺丝、覆盖、干涉） |
| 包含软胶外壳 → 金属骨架 → 电机 三层结构 |
| 故障率较高，实际维保需求大 |

### 7.2 脚部总成零件清单

| 零件 ID | 名称 | 类型 | 约束关系 |
|---------|------|------|----------|
| cover_foot_rubber_001 | 脚底软胶 | COVER | 覆盖 frame_foot_sole |
| frame_foot_sole_001 | 脚底板 | FRAME | 被 4×M3×10 固定 |
| screw_foot_m3x10_001~004 | 脚底螺丝 | SCREW | 紧固 frame_foot_sole |
| frame_ankle_roll_001 | 踝关节横滚 | FRAME | 被 cover 覆盖 |
| motor_ankle_roll_001 | 踝关节电机 | MOTOR | 被 frame 阻挡 |

### 7.3 验收标准

脚部总成切片必须通过以下验收：

| 验收项 | 通过条件 |
|--------|----------|
| 约束图完整 | 所有零件的约束关系已定义 |
| 几何判定 | 螺丝退出判定精确到 0.1mm |
| 顺序裁决 | 违反拆卸顺序时阻断并提示 |
| 工具裁决 | 工具不匹配时阻断并提示 |
| 完成裁决 | 未完全拆卸时阻断并提示 |
| 报告生成 | 能生成完整的裁决报告 |

---

## 8. 实现顺序（强制）

```
┌──────────────────────────────────────────────────────────────┐
│  阶段 1: 数据层实现                                          │
│  - 定义 Part Schema                                          │
│  - 定义 Constraint Schema                                    │
│  - 实现脚部总成的约束图数据                                  │
├──────────────────────────────────────────────────────────────┤
│  阶段 2: 裁决引擎实现                                        │
│  - 实现 DecisionEngine.canOperate()                          │
│  - 实现 DecisionEngine.adjudicate()                          │
│  - 实现几何判定函数                                          │
├──────────────────────────────────────────────────────────────┤
│  阶段 3: 状态机实现                                          │
│  - 实现 StateManager                                          │
│  - 实现 SOPExecutor                                           │
│  - 实现状态转移逻辑                                          │
├──────────────────────────────────────────────────────────────┤
│  阶段 4: 动画与 UI                                           │
│  - 动画必须回调裁决引擎                                      │
│  - UI 状态由 StateManager 驱动                               │
│  - 禁止独立于状态机的 UI 逻辑                                │
└──────────────────────────────────────────────────────────────┘
```

**每个阶段必须通过自测裁决，不通过禁止进入下一阶段。**

---

## 9. 附录

### 9.1 技术栈约束

| 层级 | 技术选型 |
|------|----------|
| 状态管理 | Zustand（全局状态机） |
| 3D 渲染 | Three.js + @react-three/fiber |
| 约束图存储 | JSON 文件 → 未来迁移至后端 |
| 裁决引擎 | 纯 TypeScript 实现 |

### 9.2 命名规范

```
文件命名:
- constraintGraph.ts        # 约束图数据
- decisionEngine.ts         # 裁决引擎
- sopExecutor.ts            # SOP 执行器
- stateManager.ts           # 状态管理器

函数命名:
- canXxx()                  # 判定函数，返回 boolean
- adjudicateXxx()           # 裁决函数，返回 AdjudicationReport
- executeXxx()              # 执行函数，产生状态变更
```

### 9.3 Claude 执行指令

1. **实现顺序不可调整**：必须按 数据层 → 裁决层 → 状态机 → UI 顺序
2. **每层必须自测**：实现完成后需编写单元测试验证
3. **文档优先**：发现规范缺失时，先补文档再写代码
4. **禁止视觉驱动**：所有判定必须基于数据，不可基于动画状态

---

## 最终裁决声明

**本文档的价值不在于篇幅，而在于：任何一个章节缺失，系统就失去裁决能力。**

系统的核心价值是：
- 能判错 ✓
- 能给原因 ✓  
- 能阻止继续 ✓
- 能生成报告 ✓

**如果做不到以上四点，视为实现失败，必须回退重构。**
