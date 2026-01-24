# R-MOS 裁决级系统重构项目交接提示词

**文档版本**: V1.0  
**创建日期**: 2026-01-23  
**用途**: 供接手开发者（Codex 或其他 AI）快速了解项目状态

---

## 你的角色

你是 R-MOS（机器人数字孪生维保系统）的接手开发者。前任 AI 开发者已完成裁决系统核心架构，现在由你继续推进剩余工作。

---

## 项目背景

R-MOS 是一个用于 Atom01 人形机器人的数字孪生维保培训系统。系统需要从当前的"演示级"升级为"裁决级"——即所有维保操作必须经过裁决引擎判定对错，禁止通过动画播放完成直接标记操作成功。

---

## 必读文档（按优先级）

```
1. robot/R-MOS 机器人数字孪生维保系统｜裁决级规范文档.md (V3.0)
   - 系统唯一裁决源，任何冲突以此文档为准
   - 重点阅读：§0 文档裁决声明、§A 不可违反公理、§B 约束强制规则

2. 裁决级系统重构开发计划.md (V1.0)
   - 开发任务分解和阶段定义
   - 当前进度：阶段 0-5 已完成，阶段 6（扩展）待做

3. 交接文档.md (V2.0)
   - 项目结构和技术栈说明
   - 包含文件路径映射

4. r-mos-frontend/src/adjudication/index.ts
   - 新增裁决模块的入口，查看所有可用导出
```

---

## 当前项目状态

### 已完成工作

| 模块 | 文件 | 行数 | 说明 |
|------|------|------|------|
| 类型定义 | `adjudication/types/adjudication.ts` | 347 | 所有枚举、接口、类型 |
| 零件注册表 | `adjudication/data/partRegistry.ts` | 210 | 16 个零件（含脚部总成） |
| 螺丝实例 | `adjudication/data/screwInstances.ts` | 280 | 16 颗螺丝（脚部） |
| 约束图 | `adjudication/data/constraintGraph.ts` | 230 | 6 个约束（脚部） |
| 状态管理 | `adjudication/core/stateManager.ts` | 320 | Zustand store |
| 几何判定 | `adjudication/core/geometryJudge.ts` | 270 | 螺丝退出/工具匹配 |
| 裁决引擎 | `adjudication/core/decisionEngine.ts` | 460 | 核心裁决逻辑 |
| SOP执行器 | `adjudication/executor/sopExecutor.ts` | 580 | 状态机执行 |
| 测试用例 | `adjudication/__tests__/decisionEngine.test.ts` | 340 | TC-001~TC-005 |
| 裁决动画 | `components/Viewer3D/DisassemblyDemoAdjudicated.tsx` | 270 | 替代原版 |
| 裁决播放器 | `components/Maintenance/SOPPlayerAdjudicated.tsx` | 430 | 替代原版 |

### P0 问题状态

全部修复：
- ✅ P0-001: 裁决层已创建
- ✅ P0-002: 动画完成需裁决验证
- ✅ P0-003: SOP 前置条件检查已实现
- ✅ P0-004: 约束图已创建（脚部总成）
- ✅ P0-005: Zustand 状态管理已实现

### TypeScript 编译状态

```
阻塞性错误: 0
警告 (TS6133 unused): 10 个
编译状态: 通过
```

---

## 待完成工作

### 优先级 1（建议先做）

1. **清理 unused import 警告**
   - 文件：`sopExecutor.ts`, `SOPPlayerAdjudicated.tsx`, `decisionEngine.test.ts`
   - 方法：删除未使用的 import

2. **升级 `sopScripts.ts` 为裁决级格式**
   - 当前：脚本级 `SOPStep` 格式
   - 目标：状态机级 `SOPStepAdjudication` 格式（添加 preconditions/validations）
   - 参考：`adjudication/types/adjudication.ts` 中的 `SOPStepAdjudication` 接口

### 优先级 2（推荐做）

3. **改造 `Atom01Interactive.tsx` 接入约束检查**
   - 在 onClick 时调用 `canOperatePart()` 检查约束
   - 阻断被覆盖/被阻挡的零件点击

4. **扩展约束图到其他模块**
   - 当前仅覆盖脚部总成
   - 需要添加：躯干、手臂、腿部等模块的约束

### 优先级 3（可选）

5. **运行 TC-001~TC-005 测试**
   ```typescript
   import { printTestReport } from '@/adjudication/__tests__/decisionEngine.test';
   printTestReport(); // 在浏览器控制台执行
   ```

6. **更新交接文档**
   - 反映新增的 adjudication 模块结构

---

## 关键规范约束（不可违反）

```
❌ 禁止：动画播放完 = 操作完成
✅ 正确：状态机验证通过 = 操作完成

❌ 禁止：手动跳过裁决结果
✅ 正确：必须经过 adjudicateAction() 判定

❌ 禁止：SOP 直接推进步骤
✅ 正确：必须经过 SOPExecutor.canExecuteStep() 检查
```

---

## 代码使用示例

### 裁决操作

```typescript
import { adjudicateAction, ActionType, AdjudicationResult } from '@/adjudication';

// 判断是否可以拆卸零件
const report = adjudicateAction(ActionType.DETACH_PART, 'left_ankle_roll_link');

if (report.result === AdjudicationResult.BLOCKED) {
  console.log('阻断原因:', report.reason);
  console.log('需要先:', report.requiredActions);
}
```

### 使用 SOP 执行器

```typescript
import { createSOPExecutor, SOPScriptAdjudication } from '@/adjudication';

const executor = createSOPExecutor({
  onBlocked: (report) => alert(report.reason),
  onComplete: () => console.log('SOP 完成'),
});

executor.loadSOP(mySOP);
executor.executeStep(); // 执行当前步骤
executor.validateAndAdvance(); // 验证并推进
```

### 状态管理

```typescript
import { useAdjudicationStore, ScrewState } from '@/adjudication';

// 获取状态
const currentTool = useAdjudicationStore((s) => s.currentToolId);

// 修改状态
useAdjudicationStore.getState().setScrewState('screw_id', ScrewState.EXTRACTED);
```

---

## 文件结构

```
r-mos-frontend/src/
├── adjudication/                    # 新增裁决模块 ⭐
│   ├── index.ts                     # 入口导出
│   ├── types/
│   │   └── adjudication.ts          # 类型定义
│   ├── data/
│   │   ├── partRegistry.ts          # 零件注册
│   │   ├── screwInstances.ts        # 螺丝实例
│   │   └── constraintGraph.ts       # 约束图
│   ├── core/
│   │   ├── stateManager.ts          # Zustand 状态
│   │   ├── geometryJudge.ts         # 几何判定
│   │   └── decisionEngine.ts        # 裁决引擎
│   ├── executor/
│   │   └── sopExecutor.ts           # SOP 执行器
│   └── __tests__/
│       └── decisionEngine.test.ts   # 测试用例
├── components/
│   ├── Viewer3D/
│   │   ├── DisassemblyDemo.tsx      # 原版（未改造）
│   │   └── DisassemblyDemoAdjudicated.tsx  # 裁决版 ⭐
│   └── Maintenance/
│       ├── SOPPlayer.tsx            # 原版（未改造）
│       └── SOPPlayerAdjudicated.tsx # 裁决版 ⭐
└── data/
    ├── sopScripts.ts                # 需升级为裁决级格式
    └── toolData.ts                  # 工具和螺丝数据
```

---

## 注意事项

1. **规范文档优先级最高**：任何实现与规范冲突，以规范为准
2. **不要修改原版组件**：创建新的 `*Adjudicated.tsx` 版本
3. **约束图是关键**：扩展其他模块时必须先定义约束关系
4. **测试用例在 `__tests__` 目录**：新功能需补充测试

---

祝开发顺利！如有疑问，优先查阅规范文档 `robot/R-MOS 机器人数字孪生维保系统｜裁决级规范文档.md`。
