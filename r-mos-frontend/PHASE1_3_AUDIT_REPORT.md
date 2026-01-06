# R-MOS 前端 360° 全景交互审计报告

**审计时间**: 2026-01-06 20:15  
**审计范围**: Phase 1-6 所有页面组件  
**审计角色**: 极度苛刻的前端体验架构师

---

## 第一轮：视觉反馈与组件健壮性 (The Component Health Pass)

### 1.1 异步状态闭环检查

| 页面 | loading 设置 | loading 重置 | 错误处理 | 评估 |
|------|:------------:|:------------:|:--------:|:----:|
| `SOPListPage` | ✅ L22 | ✅ L33 (finally) | ✅ message.error | ✅ |
| `TaskExecutionPage` | ✅ L28 | ✅ L39 (finally) | ✅ message.error | ✅ |
| `HomePage` | ✅ L73 | ✅ L91 (finally) | ⚠️ 无错误处理 | 🟡 |
| `MonitorPage` | ✅ (WebSocket) | ✅ (hook 内) | ✅ Alert + message | ✅ |
| `ReportPage` | ✅ L66 | ✅ L73 (finally) | ✅ Result 组件 | ✅ |
| `FaultManagePage` | ✅ L47 | ✅ L55 (finally) | ✅ message.error | ✅ |

### 1.2 空状态处理检查

| 页面 | 空状态组件 | 评估 |
|------|:----------:|:----:|
| `SOPListPage` | ⚠️ 依赖 Ant Table 默认 | 🟡 无自定义空状态 |
| `FaultManagePage` | ⚠️ 依赖 Ant Table 默认 | 🟡 无自定义空状态 |
| `HomePage` (List) | ✅ `locale={{ emptyText }}` | ✅ |
| `MonitorPage` (关节) | ✅ L144-146 显示等待文案 | ✅ |

---

## 第二轮：路由流转与参数完整性 (The Navigation Pass)

### 2.1 链路追踪

**SOPListPage → createTask → TaskExecutionPage**

```
1. SOPListPage: handleCreateTask(sop) 
   → createTask({ title, sop_id: sop.id })  ✅ sop_id 传递正确
   
2. createTask 返回 Task: { id: 2, ... }
   → navigate(`/tasks/${task.id}`)  ✅ taskId 正确拼接
   
3. TaskExecutionPage: useParams<{ taskId }>() 
   → loadTask(parseInt(taskId))  ✅ 参数提取正确
```

**TaskExecutionPage → ReportPage**

```
1. Modal.success: onOk => navigate(`/reports/${task.id}`)  ✅
2. ReportPage: useParams<{ taskId }>()  ✅
```

### 2.2 路由守卫（404 处理）

| 页面 | 404 处理 | 评估 |
|------|:--------:|:----:|
| `TaskExecutionPage` | ❌ 无处理 | 🔴 **BLOCKER** |
| `ReportPage` | ✅ Result status="error" | ✅ |

**问题详情**：
- `TaskExecutionPage` L99-101：当 `getTask(999)` 返回 404 时，`catch` 只显示 message.error，但页面停留在 `loading || !task` 状态，显示简陋的 "加载中..." 文本，**无返回按钮，用户被困**。

---

## 第三轮：实时性与防御性逻辑 (The Real-time Defense Pass)

### 3.1 WebSocket 生命线

| 检查项 | 状态 | 位置 |
|--------|:----:|:----:|
| 组件卸载时关闭连接 | ✅ | `useWebSocket.ts` L143: `return => disconnect()` |
| 重连机制 | ✅ | L107-117: 最多重试 3 次 |
| 错误提示 | ✅ | L116: `message.error` |
| 清除定时器 | ✅ | L127: `clearTimeout` |

### 3.2 表单护栏

| 页面 | 前端校验 | 提交状态锁 | 评估 |
|------|:--------:|:----------:|:----:|
| `FaultManagePage` | ✅ Form rules | ✅ submitting 状态 | ✅ |
| `SOPListPage` (创建任务按钮) | N/A | ✅ creating 状态 | ✅ |

### 3.3 其他发现

| 问题 | 位置 | 严重程度 |
|------|------|:--------:|
| `HomePage` 使用硬编码模拟数据 | L82-89 | 🔵 建议 |
| `TaskExecutionPage` 暂停/恢复无 loading 状态 | L75-96 | 🟡 |
| `SOPListPage` "创建SOP" 按钮无功能 | L119-121 | 🟡 |
| `ReportPage` API 路径硬编码含 `/api/v1` | L67 | 🔵 建议 |

---

## 问题汇总

### 🔴 交互阻断 (Blocker) - 1 个

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| B1 | TaskExecutionPage 缺少 404 处理 | L99-101 | 用户访问不存在任务时被困，无法返回 |

**修复方案**：
```tsx
// TaskExecutionPage.tsx L27-41
const loadTask = async (id: number) => {
  setLoading(true);
  try {
    const taskData = await getTask(id) as TaskWithSOP;
    setTask(taskData);
    if (taskData.sop?.steps) {
      setSteps(taskData.sop.steps as SOPStep[]);
    }
  } catch (error: any) {
    // 新增：区分 404 和其他错误
    if (error.response?.status === 404) {
      message.error('任务不存在');
      navigate('/sops'); // 返回 SOP 列表
    } else {
      message.error('加载任务失败');
    }
  } finally {
    setLoading(false);
  }
};
```

---

### 🟡 体验缺陷 (UX Issues) - 4 个

| # | 问题 | 位置 | 修复建议 |
|---|------|------|----------|
| U1 | HomePage 加载失败无错误提示 | L76-94 | 添加 catch 和 message.error |
| U2 | SOPListPage 缺少自定义空状态 | L124-138 | 添加 `locale={{ emptyText: <Empty /> }}` |
| U3 | 暂停/恢复按钮无 loading 反馈 | L75-96 | 添加 pausing/resuming 状态变量 |
| U4 | "创建SOP" 按钮无功能 | L119-121 | 添加 onClick 或显示为 disabled |

---

### 🔵 代码建议 (Suggestions) - 3 个

| # | 问题 | 位置 | 建议 |
|---|------|------|------|
| S1 | HomePage 使用硬编码数据 | L82-89 | 调用真实 API 获取统计数据 |
| S2 | ReportPage API 路径硬编码 | L67 | 使用 `getTaskReport` API 函数 |
| S3 | Steps 组件可考虑使用 status 属性 | TaskExecutionPage | 高亮当前步骤、标记完成步骤 |

---

### ✅ 核心流程验证通过

| 流程 | 状态 |
|------|:----:|
| SOP列表加载 → 显示表格 → 分页 | ✅ 完整闭环 |
| 创建任务 → 跳转执行页 → 参数传递 | ✅ 完整闭环 |
| 任务执行 → 步骤推进 → 完成弹窗 → 跳转报告 | ✅ 完整闭环 |
| WebSocket 连接 → 数据展示 → 断连重试 → 卸载清理 | ✅ 完整闭环 |
| 故障管理 CRUD → 表单校验 → 提交状态锁 | ✅ 完整闭环 |
| 报告页加载失败 → 错误展示 → 返回按钮 | ✅ 完整闭环 |

---

## 修复优先级

| 优先级 | 问题 | 预估工时 |
|:------:|------|:--------:|
| P0 | B1: TaskExecutionPage 404 处理 | 10 分钟 |
| P1 | U1: HomePage 错误处理 | 5 分钟 |
| P1 | U2: 列表空状态 | 5 分钟 |
| P2 | U3: 暂停/恢复 loading | 10 分钟 |
| P2 | U4: 创建SOP 按钮 | 5 分钟 |
| P3 | S1-S3: 代码优化 | 20 分钟 |

---

## 审计结论

**整体评分**: ⭐⭐⭐⭐ (4/5)

**优点**：
- 异步状态管理规范，loading/finally 配合良好
- WebSocket 生命周期管理完善
- 表单提交有前端校验和状态锁
- 路由参数传递清晰

**待改进**：
- 1 个 Blocker 需立即修复
- 空状态和边缘场景处理需加强
- 部分硬编码数据待替换为真实 API

**建议**：优先修复 P0 级别问题后再进行下一阶段开发。
