# R-MOS 前端重构方案 v1.0
**目标：将 SOPMaintenancePage / MonitorPage 的视觉语言与 AgentWorkbenchPage 完全对齐**
> 执行主体：Codex（GPT-5.4）
> 基准参考：AgentWorkbenchPage.tsx（已验证的 Industrial Precision Dark 风格）
> 生成日期：2026-03-08

---

## 零、重构定位

### 现状差距

| 页面 | 当前风格 | 目标风格 | 工作量 |
|------|---------|---------|-------|
| AgentWorkbenchPage | ✅ shadcn/ui + Tailwind + CSS变量体系 | 基准参考，不动 | 仅补 DiagnosisPanel 细节 |
| MonitorPage | ❌ Ant Design Card/Tag/Statistic，内联style | Industrial Precision Dark | 全量重写 |
| SOPMaintenancePage | ❌ Ant Design 全家桶，1500行，硬编码颜色 | Industrial Precision Dark | 分层重构 |
| DiagnosisPanel | ⚠️ 已存在但样式未见定义 | 补齐像素级规范 | 样式精化 |

### 重构原则
1. **CSS变量体系不新建**：直接复用 AgentWorkbenchPage 已用的变量名，确保一致性
2. **3D层完全不动**：Canvas/OrbitControls/Atom01Interactive/PartInspector 等 three.js 组件不触碰
3. **业务逻辑不动**：adjudication状态机、SOPExecutor、useAdjudicationStore、scoringEngine 不触碰
4. **Ant Design 仅保留无法替代的**：Modal、message（全局通知）可保留，其余替换

---

## 一、Design Token 完整规范

以下所有 Token 均从 AgentWorkbenchPage 现有用法中提取并扩展，Codex 必须严格使用这套变量，**禁止使用任何硬编码颜色值**。

### 1.1 CSS 变量定义
在 `src/index.css` 或 `src/styles/globals.css` 的 `:root` 中确认以下变量存在，如不存在则补充：

```css
:root {
  /* ── 背景层级 ── */
  --bg-base:      #020817;   /* 最底层页面背景 */
  --bg-surface:   #0f172a;   /* 卡片/面板背景 */
  --bg-elevated:  #1e293b;   /* 悬浮/高亮背景 */
  --bg-overlay:   #0d1526;   /* 代码块/数据块背景 */

  /* ── 文字层级 ── */
  --text-primary:   #e2e8f0;  /* 主要文字 */
  --text-secondary: #94a3b8;  /* 次要文字 */
  --text-muted:     #475569;  /* 弱化文字、标签 */
  --text-disabled:  #334155;  /* 禁用状态 */

  /* ── 边框 ── */
  --border-subtle:  #1e293b;  /* 卡片默认边框 */
  --border-default: #334155;  /* 交互元素边框 */
  --border-focus:   #f59e0b44;/* 聚焦态边框 */

  /* ── 主色（Amber Accent） ── */
  --primary:        #f59e0b;  /* 主要强调色 */
  --primary-muted:  #f59e0b14;/* 主色背景 */
  --primary-border: #f59e0b40;/* 主色边框 */

  /* ── 语义色 ── */
  --success:        #22c55e;
  --success-muted:  #22c55e14;
  --warning:        #f59e0b;
  --warning-muted:  #f59e0b14;
  --error:          #ef4444;
  --error-muted:    #ef444414;
  --info:           #3b82f6;
  --info-muted:     #3b82f614;

  /* ── 特殊语义色 ── */
  --amber:          #f59e0b;  /* 证据需求/警告，与 AgentWorkbenchPage 对齐 */

  /* ── 字体 ── */
  --font-sans:  'Rajdhani', 'Inter', system-ui, sans-serif;  /* 标题/数字展示 */
  --font-mono:  'JetBrains Mono', 'Fira Code', monospace;    /* 数据/代码/ID */

  /* ── 阴影 ── */
  --shadow-card:    0 1px 3px rgba(0,0,0,0.4);
  --shadow-glow-primary: 0 0 12px rgba(245,158,11,0.2);
  --shadow-glow-error:   0 0 16px rgba(239,68,68,0.2);
  --shadow-glow-success: 0 0 8px rgba(34,197,94,0.15);
}
```

### 1.2 Tailwind 自定义色（tailwind.config.ts）
确保以下自定义色与 CSS 变量映射，AgentWorkbenchPage 中已有，需确认：

```typescript
// tailwind.config.ts
colors: {
  'bg-base':     'var(--bg-base)',
  'bg-surface':  'var(--bg-surface)',
  'bg-elevated': 'var(--bg-elevated)',
  'bg-overlay':  'var(--bg-overlay)',
  'text-primary':   'var(--text-primary)',
  'text-secondary': 'var(--text-secondary)',
  'text-muted':     'var(--text-muted)',
  'text-disabled':  'var(--text-disabled)',
  'border-subtle':  'var(--border-subtle)',
  'border-default': 'var(--border-default)',
  'primary':        'var(--primary)',
  'primary-muted':  'var(--primary-muted)',
  'success':        'var(--success)',
  'error':          'var(--error)',
  'warning':        'var(--warning)',
  'amber':          'var(--amber)',
}
```

---

## 二、通用组件规范

以下规范是所有页面必须遵守的原子设计规则。

### 2.1 卡片（Card）
不再使用 `antd Card`，统一使用以下结构：

```tsx
// 标准卡片
<div className="rounded-lg border border-border-subtle bg-bg-surface">
  {/* 卡片头部（可选） */}
  <div className="flex items-center justify-between border-b border-border-subtle px-4 py-2.5">
    <span className="text-[11px] uppercase tracking-[0.18em] text-text-muted">
      {title}
    </span>
    {extra}
  </div>
  {/* 卡片内容 */}
  <div className="p-4">
    {children}
  </div>
</div>

// 无头部卡片
<div className="rounded-lg border border-border-subtle bg-bg-surface p-4">
  {children}
</div>
```

**尺寸规范：**
- 卡片圆角：`rounded-lg`（8px）
- 卡片内边距：`p-4`（16px）
- 卡片头部内边距：`px-4 py-2.5`
- 卡片间距：`gap-4`（16px）

### 2.2 数据展示块（Statistic 替代方案）
替代 `antd Statistic`：

```tsx
// 大数值展示
<div className="rounded-lg border border-border-subtle bg-bg-surface p-4">
  <div className="mb-1 text-[10px] uppercase tracking-[0.2em] text-text-muted">
    {label}
  </div>
  <div className="font-[Rajdhani] text-3xl font-bold text-text-primary">
    {value}
    <span className="ml-1 text-base font-normal text-text-muted">{suffix}</span>
  </div>
</div>

// 告警态：数值变红
<div className="rounded-lg border border-error/30 bg-error-muted p-4"
     style={{ boxShadow: 'var(--shadow-glow-error)' }}>
  <div className="mb-1 text-[10px] uppercase tracking-[0.2em] text-text-muted">{label}</div>
  <div className="font-[Rajdhani] text-3xl font-bold text-error">{value}</div>
</div>
```

### 2.3 状态标签（Tag 替代方案）
替代 `antd Tag`：

```tsx
// 基础标签
const statusTagClass = {
  success: 'border-success/30 bg-success/10 text-success',
  error:   'border-error/30  bg-error/10  text-error',
  warning: 'border-warning/30 bg-warning/10 text-warning',
  info:    'border-info/30   bg-info/10   text-info',
  default: 'border-border-default bg-bg-elevated text-text-secondary',
}

<span className={cn(
  'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-mono uppercase tracking-[0.1em]',
  statusTagClass[status]
)}>
  {label}
</span>
```

### 2.4 分隔线
```tsx
<div className="h-px bg-border-subtle" />  {/* 水平分隔线 */}
```

### 2.5 空状态
替代 `antd Empty`：
```tsx
<div className="flex flex-col items-center justify-center py-12 text-text-muted">
  <Icon className="mb-3 h-8 w-8 opacity-30" />
  <p className="text-sm">{description}</p>
</div>
```

### 2.6 字体使用规范

| 场景 | 字体 | 类名 | 字号 | 颜色 |
|------|------|------|------|------|
| 页面大标题 | Rajdhani | `font-[Rajdhani] font-bold` | `text-2xl`（24px） | `text-text-primary` |
| 卡片标题 | 系统 | `font-medium` | `text-sm`（14px） | `text-text-primary` |
| 卡片子标题/标签 | 系统 | `uppercase tracking-[0.18em]` | `text-[11px]` | `text-text-muted` |
| 正文 | 系统 | `leading-7` | `text-sm`（14px） | `text-text-primary` |
| 次要文字 | 系统 | — | `text-xs`（12px） | `text-text-secondary` |
| 数据值/ID/代码 | JetBrains Mono | `font-mono` | `text-sm` | `text-text-primary` |
| 大数字展示 | Rajdhani | `font-[Rajdhani] font-bold` | `text-3xl`（30px） | 按语义色 |

---

## 三、MonitorPage 重构规范

### 3.1 整体布局
保持三栏布局，替换所有 Ant Design 组件，样式完全与 AgentWorkbenchPage 对齐。

**页面背景**：`bg-bg-base`（不需要显式设置，由全局 body 继承）

**顶部状态栏：**
```tsx
<div className="mb-6 flex items-center justify-between">
  {/* 左：标题 */}
  <div>
    <div className="mb-1 text-[10px] uppercase tracking-[0.2em] text-text-muted">
      REALTIME MONITOR
    </div>
    <h1 className="font-[Rajdhani] text-2xl font-bold tracking-wide text-text-primary">
      实时监控
    </h1>
  </div>
  {/* 右：连接状态 */}
  <div className="flex items-center gap-3">
    <span className={cn(
      'h-2 w-2 rounded-full',
      isConnected ? 'bg-success animate-pulse' : 'bg-error'
    )} />
    <span className="font-mono text-xs text-text-muted">
      {getStatusText()}
    </span>
    {status === 'failed' && (
      <button
        onClick={reconnect}
        className="rounded border border-border-default px-2 py-1 text-[11px] text-text-secondary hover:border-primary hover:text-primary"
      >
        重连
      </button>
    )}
  </div>
</div>
```

**断线警告条：**
```tsx
{error && (
  <div className="mb-4 flex items-center gap-3 rounded-lg border border-error/30 bg-error/5 px-4 py-3">
    <WarningOutlined className="text-error" />  {/* 或 lucide AlertTriangle */}
    <div>
      <p className="text-sm font-medium text-error">连接已断开</p>
      <p className="text-xs text-text-muted">{error}</p>
    </div>
  </div>
)}
```

### 3.2 左栏：传感器数据（完整代码规范）

```tsx
<div className="flex flex-col gap-4">

  {/* 电池电量 */}
  <div className={cn(
    'rounded-lg border p-4',
    (batteryLevel ?? 100) > 20
      ? 'border-border-subtle bg-bg-surface'
      : 'border-error/30 bg-error/5',
    { 'box-shadow': (batteryLevel ?? 100) <= 20 ? 'var(--shadow-glow-error)' : 'none' }
  )}>
    <div className="mb-1 text-[10px] uppercase tracking-[0.2em] text-text-muted">
      BATTERY
    </div>
    <div className={cn(
      'font-[Rajdhani] text-3xl font-bold',
      (batteryLevel ?? 100) > 20 ? 'text-text-primary' : 'text-error'
    )}>
      {batteryLevel ?? '--'}
      <span className="ml-1 text-base font-normal text-text-muted">%</span>
    </div>
    {/* 电量进度条 */}
    {batteryLevel !== null && (
      <div className="mt-3 h-1 rounded-full bg-bg-elevated">
        <div
          className={cn('h-full rounded-full transition-all duration-500',
            batteryLevel > 60 ? 'bg-success' :
            batteryLevel > 20 ? 'bg-warning' : 'bg-error'
          )}
          style={{ width: `${batteryLevel}%` }}
        />
      </div>
    )}
  </div>

  {/* 活动故障数 */}
  <div className={cn(
    'rounded-lg border p-4',
    activeFaults.length > 0
      ? 'border-error/30 bg-error/5'
      : 'border-border-subtle bg-bg-surface'
  )}>
    <div className="mb-1 text-[10px] uppercase tracking-[0.2em] text-text-muted">
      ACTIVE FAULTS
    </div>
    <div className={cn(
      'font-[Rajdhani] text-3xl font-bold',
      activeFaults.length > 0 ? 'text-error' : 'text-success'
    )}>
      {activeFaults.length}
      <span className="ml-1 text-base font-normal text-text-muted">个</span>
    </div>
  </div>

  {/* 系统温度 */}
  <div className="rounded-lg border border-border-subtle bg-bg-surface p-4">
    <div className="mb-1 text-[10px] uppercase tracking-[0.2em] text-text-muted">
      SYS TEMP
    </div>
    <div className="font-[Rajdhani] text-3xl font-bold text-text-primary">
      {telemetryData?.sensors?.temperature ?? '--'}
      <span className="ml-1 text-base font-normal text-text-muted">°C</span>
    </div>
  </div>

  {/* IMU 加速度 */}
  <div className="rounded-lg border border-border-subtle bg-bg-surface p-4">
    <div className="mb-2 text-[10px] uppercase tracking-[0.2em] text-text-muted">
      IMU ACCELERATION
    </div>
    <div className="space-y-2">
      {(['x', 'y', 'z'] as const).map((axis) => (
        <div key={axis} className="flex items-center justify-between">
          <span className="font-mono text-xs uppercase text-text-muted">{axis}</span>
          <span className="font-mono text-sm text-text-primary">
            {imuData?.acceleration?.[axis]?.toFixed(3) ?? '--'}
            <span className="ml-1 text-text-muted">m/s²</span>
          </span>
        </div>
      ))}
    </div>
  </div>

</div>
```

### 3.3 中栏：3D视图卡片

```tsx
<div className="rounded-lg border border-border-subtle bg-bg-surface">
  {/* 卡片头部 */}
  <div className="flex items-center justify-between border-b border-border-subtle px-4 py-2.5">
    <span className="text-[11px] uppercase tracking-[0.18em] text-text-muted">
      3D ROBOT VIEW
    </span>
    {activeFaults.length > 0 && (
      <span className="inline-flex items-center gap-1 rounded-full border border-error/30 bg-error/10 px-2 py-0.5 text-[10px] font-mono text-error">
        ⚠ {activeFaults.length} FAULT{activeFaults.length > 1 ? 'S' : ''}
      </span>
    )}
  </div>
  {/* 3D 视图区域（不动） */}
  <div className="p-0">  {/* 3D区域不加padding */}
    <Viewer3DErrorBoundary>
      <RobotViewer height={400} externalData={{ joints: joints3D, connected: isConnected }} />
    </Viewer3DErrorBoundary>
  </div>
</div>

{/* 活动故障列表（3D视图下方） */}
{activeFaults.length > 0 && (
  <div className="mt-4 rounded-lg border border-error/30 bg-error/5 p-4">
    <div className="mb-3 text-[10px] uppercase tracking-[0.2em] text-error">
      ACTIVE FAULTS
    </div>
    <div className="flex flex-wrap gap-2">
      {activeFaults.map((fault: string, index: number) => (
        <span
          key={index}
          className="inline-flex items-center gap-1 rounded-full border border-error/30 bg-error/10 px-3 py-1 font-mono text-[11px] text-error"
        >
          ⚠ {fault}
        </span>
      ))}
    </div>
  </div>
)}
```

### 3.4 右栏：关节状态

```tsx
<div className="rounded-lg border border-border-subtle bg-bg-surface">
  <div className="border-b border-border-subtle px-4 py-2.5">
    <span className="text-[11px] uppercase tracking-[0.18em] text-text-muted">
      JOINT STATUS
    </span>
  </div>
  <div className="space-y-2 p-3">
    {joints.length > 0 ? joints.map((joint: any, index: number) => (
      <div
        key={joint.joint_id || index}
        className={cn(
          'rounded-md border p-2.5 transition-colors',
          joint.error_code
            ? 'border-error/40 bg-error/5'
            : 'border-border-subtle bg-bg-elevated'
        )}
      >
        <div className="flex items-center justify-between">
          <span className="font-mono text-xs text-text-secondary">
            {joint.joint_id || `J${index + 1}`}
          </span>
          <span className={cn(
            'font-mono text-sm font-medium',
            joint.error_code ? 'text-error' : 'text-text-primary'
          )}>
            {joint.position?.toFixed(4) ?? '--'}
          </span>
        </div>
        {joint.error_code && (
          <div className="mt-1.5">
            <span className="inline-flex rounded border border-error/30 bg-error/10 px-1.5 py-0.5 font-mono text-[10px] text-error">
              {joint.error_code}
            </span>
          </div>
        )}
      </div>
    )) : (
      <div className="flex flex-col items-center justify-center py-8 text-text-disabled">
        <span className="mb-2 text-2xl">○</span>
        <span className="text-xs">等待遥测数据...</span>
      </div>
    )}
  </div>
</div>
```

---

## 四、SOPMaintenancePage 重构规范

SOPMaintenancePage 有 1500 行，全量重写风险极高。采用**分层外科手术策略**：只替换可见 UI 层，保留全部业务逻辑。

### 4.1 重构边界

**绝对不动（业务逻辑层）：**
- 所有 `useState`、`useCallback`、`useEffect` 逻辑
- `adjudication` 相关全部逻辑（SOPExecutor、useAdjudicationStore、scoringEngine）
- `useSOPSceneSync`、`formatCountdown`、`isCountdownUrgent`
- Canvas/three.js 相关全部代码
- `ISOLATION_*`、`GROUP_COLORS`、`GROUP_NAMES`、`SOP_EXECUTION_STATE_*` 常量（颜色常量除外）

**需要替换（UI 渲染层）：**
- 所有 `antd` 组件：Card → 自定义、Tag → 自定义标签、Button → shadcn Button、Slider → shadcn Slider、Tabs → shadcn Tabs、Select → shadcn Select、Segmented → 自定义分段控件、Switch → shadcn Switch、Descriptions → 自定义描述列表、Modal → 保留antd（全局弹窗）、message → 保留antd
- 所有内联 `style` 硬编码颜色 → Tailwind 类名

### 4.2 页面顶部区域规范

**考试头部（倒计时 + 评分 + 状态）：**
```tsx
<div className="mb-4 flex items-center justify-between rounded-lg border border-border-subtle bg-bg-surface px-5 py-3">
  
  {/* 左：标题 + 面包屑 */}
  <div className="flex items-center gap-3">
    <h1 className="font-[Rajdhani] text-xl font-bold text-text-primary">
      SOP 维保操作台
    </h1>
    {/* 面包屑 */}
    <div className="flex items-center gap-1 font-mono text-xs text-text-muted">
      {breadcrumbs.map((crumb, i) => (
        <span key={crumb.nodeId ?? 'root'} className="flex items-center gap-1">
          {i > 0 && <span className="text-text-disabled">/</span>}
          <button
            className={cn(
              'hover:text-primary',
              i === breadcrumbs.length - 1 ? 'text-text-secondary' : 'text-text-muted'
            )}
            onClick={() => handleBreadcrumbClick(crumb)}
          >
            {crumb.displayName}
          </button>
        </span>
      ))}
    </div>
  </div>

  {/* 中：倒计时 */}
  <div className={cn(
    'flex items-center gap-2 font-[Rajdhani] text-2xl font-bold',
    isCountdownUrgent(examTimeLeft) ? 'text-error' : 'text-text-primary'
  )}>
    <span className="font-mono text-[10px] font-normal uppercase tracking-[0.2em] text-text-muted mr-2">
      TIME
    </span>
    {formatCountdown(examTimeLeft)}
    {isCountdownUrgent(examTimeLeft) && (
      <span className="inline-block h-2 w-2 rounded-full bg-error animate-pulse" />
    )}
  </div>

  {/* 右：得分 + SOP状态 */}
  <div className="flex items-center gap-4">
    <div className="text-right">
      <div className="text-[10px] uppercase tracking-[0.2em] text-text-muted">SCORE</div>
      <div className="font-[Rajdhani] text-2xl font-bold text-primary">
        {scoreState.currentScore}
      </div>
    </div>
    {/* SOP执行状态标签（替换原 antd Tag） */}
    <span className={cn(
      'rounded-full border px-3 py-1 font-mono text-[11px] uppercase tracking-[0.1em]',
      sopExecutionState === SOPExecutionState.EXECUTING
        ? 'border-success/30 bg-success/10 text-success'
        : sopExecutionState === SOPExecutionState.FAILED
        ? 'border-error/30 bg-error/10 text-error'
        : 'border-border-default bg-bg-elevated text-text-secondary'
    )}>
      {SOP_EXECUTION_STATE_LABEL[sopExecutionState] ?? sopExecutionState}
    </span>
  </div>
</div>
```

### 4.3 主体三栏布局规范

**列宽**：左栏 `w-[280px] shrink-0`、中栏 `flex-1 min-w-0`、右栏 `w-[300px] shrink-0`

```tsx
<div className="flex gap-4 h-[calc(100vh-200px)]">
  {/* 左栏：SOP 步骤 + 工具选择 */}
  <div className="w-[280px] shrink-0 flex flex-col gap-4 overflow-y-auto">
    ...
  </div>
  {/* 中栏：3D 视图（不动） */}
  <div className="flex-1 min-w-0">
    ...
  </div>
  {/* 右栏：零件信息 + 诊断面板 */}
  <div className="w-[300px] shrink-0 flex flex-col gap-4 overflow-y-auto">
    ...
  </div>
</div>
```

### 4.4 SOP 步骤卡片规范

替代左栏的 Ant Design Card 步骤列表：

```tsx
{/* SOP 脚本选择 */}
<div className="rounded-lg border border-border-subtle bg-bg-surface">
  <div className="border-b border-border-subtle px-4 py-2.5">
    <span className="text-[11px] uppercase tracking-[0.18em] text-text-muted">SOP SCRIPT</span>
  </div>
  <div className="p-3">
    {/* 使用 shadcn Select 替换 antd Select */}
    <Select value={selectedScript} onValueChange={handleScriptChange}>
      <SelectTrigger className="w-full border-border-default bg-bg-elevated text-text-primary text-sm">
        <SelectValue placeholder="选择 SOP 脚本" />
      </SelectTrigger>
      <SelectContent className="border-border-default bg-bg-surface">
        {ALL_SOP_SCRIPTS.map(script => (
          <SelectItem key={script.id} value={script.id} className="text-text-primary">
            {script.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  </div>
</div>

{/* 步骤列表 */}
<div className="rounded-lg border border-border-subtle bg-bg-surface">
  <div className="border-b border-border-subtle px-4 py-2.5 flex items-center justify-between">
    <span className="text-[11px] uppercase tracking-[0.18em] text-text-muted">STEPS</span>
    <span className="font-mono text-xs text-text-muted">
      {currentStepIndex + 1} / {totalSteps}
    </span>
  </div>
  <div className="p-2 space-y-1.5">
    {sopSteps.map((step, i) => (
      <div
        key={step.id}
        className={cn(
          'flex items-start gap-2.5 rounded-md border px-3 py-2.5 cursor-pointer transition-colors',
          i === currentStepIndex
            ? 'border-primary/40 bg-primary/5'
            : step.adjudication?.passed
            ? 'border-success/20 bg-success/5'
            : 'border-border-subtle bg-bg-elevated hover:bg-bg-overlay'
        )}
        onClick={() => handleStepClick(step)}
      >
        {/* 步骤序号 */}
        <div className={cn(
          'mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[10px] font-mono',
          i === currentStepIndex
            ? 'border-primary bg-primary/10 text-primary'
            : step.adjudication?.passed
            ? 'border-success bg-success/10 text-success'
            : 'border-border-default bg-bg-surface text-text-muted'
        )}>
          {step.adjudication?.passed ? '✓' : i + 1}
        </div>
        {/* 步骤内容 */}
        <div className="min-w-0 flex-1">
          <p className={cn(
            'text-xs leading-5',
            i === currentStepIndex ? 'text-primary' : 'text-text-secondary'
          )}>
            {step.description}
          </p>
        </div>
      </div>
    ))}
  </div>
</div>
```

### 4.5 爆炸程度滑块规范

替代 antd Slider：

```tsx
<div className="rounded-lg border border-border-subtle bg-bg-surface p-4">
  <div className="mb-3 flex items-center justify-between">
    <span className="text-[10px] uppercase tracking-[0.2em] text-text-muted">EXPLODE</span>
    <span className="font-mono text-xs text-primary">{Math.round(explodeRatio * 100)}%</span>
  </div>
  {/* shadcn Slider */}
  <Slider
    value={[explodeRatio * 100]}
    min={0}
    max={100}
    step={1}
    onValueChange={([v]) => setExplodeRatio(v / 100)}
    className="[&_.slider-thumb]:border-primary [&_.slider-track]:bg-primary"
  />
  <div className="mt-2 flex justify-between text-[10px] text-text-disabled">
    <span>收合</span>
    <span>展开</span>
  </div>
</div>
```

### 4.6 零件信息面板规范

替代右栏的 antd Descriptions + Card：

```tsx
{/* 零件详情 */}
{activeDetailRecord ? (
  <div className="rounded-lg border border-border-subtle bg-bg-surface">
    <div className="border-b border-border-subtle px-4 py-2.5 flex items-center justify-between">
      <span className="text-[11px] uppercase tracking-[0.18em] text-text-muted">PART INFO</span>
      <span className={cn(
        'rounded-full border px-2 py-0.5 font-mono text-[10px]',
        GROUP_COLOR_CLASSES[selectedPart?.group ?? ''] ?? 'border-border-default text-text-muted'
      )}>
        {GROUP_NAMES[selectedPart?.group ?? ''] ?? '—'}
      </span>
    </div>
    <div className="p-4 space-y-3">
      {/* 零件名 */}
      <div>
        <div className="text-[10px] uppercase tracking-[0.15em] text-text-muted mb-1">NAME</div>
        <div className="font-mono text-sm text-text-primary">{activeDetailRecord.displayName}</div>
      </div>
      {/* 描述 */}
      <div>
        <div className="text-[10px] uppercase tracking-[0.15em] text-text-muted mb-1">SUMMARY</div>
        <p className="text-xs leading-5 text-text-secondary">{activeDetailRecord.summary}</p>
      </div>
      {/* 维保要点 */}
      <div className="rounded-md border border-info/20 bg-info/5 p-3">
        <div className="mb-2 text-[10px] uppercase tracking-[0.15em] text-info">MAINTENANCE</div>
        <ul className="space-y-1">
          {activeDetailRecord.maintenancePoints.map((point) => (
            <li key={point} className="flex items-start gap-1.5 text-xs text-text-secondary">
              <span className="mt-1 text-info">⬥</span>
              {point}
            </li>
          ))}
        </ul>
      </div>
    </div>
  </div>
) : (
  <div className="rounded-lg border border-border-subtle bg-bg-surface flex flex-col items-center justify-center py-10 text-text-disabled">
    <span className="mb-2 text-3xl">◎</span>
    <span className="text-xs">点击零件查看详情</span>
  </div>
)}
```

### 4.7 GROUP_COLOR_CLASSES 定义
替代硬编码的 `GROUP_COLORS`（原来是 antd 颜色值），改为 Tailwind 类名映射：

```typescript
// 在组件顶部定义（替代原 GROUP_COLORS Record）
const GROUP_COLOR_CLASSES: Record<string, string> = {
  base:      'border-purple-500/30 bg-purple-500/10 text-purple-400',
  torso:     'border-cyan-500/30   bg-cyan-500/10   text-cyan-400',
  left_arm:  'border-green-500/30  bg-green-500/10  text-green-400',
  right_arm: 'border-amber-500/30  bg-amber-500/10  text-amber-400',
  left_leg:  'border-blue-500/30   bg-blue-500/10   text-blue-400',
  right_leg: 'border-pink-500/30   bg-pink-500/10   text-pink-400',
}
```

### 4.8 考试结束覆盖层规范

```tsx
{examSummaryReport && (
  <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-bg-base/95 p-6 backdrop-blur-sm">
    <div className="w-full max-w-lg rounded-xl border border-border-subtle bg-bg-surface p-8 text-center shadow-2xl">
      <div className="mb-2 text-[11px] uppercase tracking-[0.3em] text-text-muted">
        EXAMINATION COMPLETE
      </div>
      <h2 className="mb-4 font-[Rajdhani] text-3xl font-bold text-text-primary">
        考试结束
      </h2>
      <div className="mb-3 rounded-lg border border-error/30 bg-error/10 px-4 py-2">
        <span className="font-mono text-sm text-error">
          {examSummaryReport.reasonCode}
        </span>
      </div>
      <div className="mb-6 font-[Rajdhani] text-5xl font-bold text-primary">
        {scoreState.currentScore}
        <span className="ml-1 text-xl font-normal text-text-muted">分</span>
      </div>
      <Button onClick={handleResetExam} className="w-full">
        重新开始
      </Button>
    </div>
  </div>
)}
```

---

## 五、DiagnosisPanel 像素级规范

这是新增组件，目前样式不明确，以下是完整的样式定义。

### 5.1 加载态（Skeleton）

```tsx
{isLoading && (
  <div className="space-y-3 animate-pulse">
    <div className="h-4 w-3/4 rounded bg-bg-elevated" />
    <div className="h-20 rounded-lg bg-bg-elevated" />
    <div className="h-4 w-1/2 rounded bg-bg-elevated" />
    <div className="h-32 rounded-lg bg-bg-elevated" />
  </div>
)}
```

### 5.2 空态

```tsx
{!isLoading && !diagnosisResult && (
  <div className="flex flex-col items-center justify-center py-8 text-text-disabled">
    <span className="mb-2 font-mono text-2xl">◈</span>
    <span className="text-xs">等待诊断触发</span>
    <span className="mt-1 text-[11px] text-text-disabled">
      发送"诊断问题"意图后显示
    </span>
  </div>
)}
```

### 5.3 主假设卡片

```tsx
{/* 置信度条 */}
{/* 数值：font-mono text-sm，颜色：text-success（主假设）/ text-text-muted（备选） */}
{/* 条形：h-1.5 rounded-full bg-bg-elevated，填充：bg-success transition-all duration-1000 */}

<div className="rounded-lg border border-success/30 bg-success/5 p-3">
  <div className="mb-2 flex items-center justify-between">
    <span className="text-xs font-medium text-success">
      H1 · {diagnosisResult.primary_hypothesis.fault_type}
    </span>
    <div className="flex items-center gap-2">
      {/* 置信度条 */}
      <div className="h-1.5 w-20 rounded-full bg-bg-elevated">
        <div
          className="h-full rounded-full bg-success transition-all duration-1000"
          style={{ width: `${diagnosisResult.primary_hypothesis.confidence * 100}%` }}
        />
      </div>
      <span className="w-9 text-right font-mono text-xs font-bold text-success">
        {Math.round(diagnosisResult.primary_hypothesis.confidence * 100)}%
      </span>
    </div>
  </div>
  {/* 因果链 */}
  <p className="mb-2 border-l-2 border-success/40 pl-2 text-[11px] leading-5 text-text-muted">
    {diagnosisResult.primary_hypothesis.causal_chain}
  </p>
  {/* 证据标签 */}
  <div className="flex flex-wrap gap-1">
    {diagnosisResult.primary_hypothesis.evidence.map((e, i) => (
      <span
        key={i}
        className="rounded border border-border-default bg-bg-overlay px-1.5 py-0.5 font-mono text-[10px] text-text-muted"
      >
        ⬥ {e}
      </span>
    ))}
  </div>
</div>
```

### 5.4 备选假设列表

```tsx
<div className="grid grid-cols-1 gap-2">
  {diagnosisResult.alternative_hypotheses.map((h, i) => (
    <div key={i} className="rounded-md border border-border-subtle bg-bg-elevated p-2.5">
      <div className="mb-1.5 flex items-center justify-between">
        <span className="text-[11px] text-text-muted">H{i + 2} · {h.fault_type}</span>
        <div className="flex items-center gap-1.5">
          <div className="h-1 w-12 rounded-full bg-bg-surface">
            <div
              className="h-full rounded-full bg-border-default transition-all duration-700"
              style={{ width: `${h.confidence * 100}%` }}
            />
          </div>
          <span className="font-mono text-[10px] text-text-disabled">
            {Math.round(h.confidence * 100)}%
          </span>
        </div>
      </div>
    </div>
  ))}
</div>
```

### 5.5 推荐动作 + 紧急级别

```tsx
{/* 推荐动作 */}
<div className={cn(
  'flex items-center gap-2 rounded-md border px-3 py-2',
  diagnosisResult.recommended_action === 'immediate_stop'
    ? 'border-error/40 bg-error/10'
    : diagnosisResult.recommended_action === 'limited_operation'
    ? 'border-warning/40 bg-warning/10'
    : 'border-info/40 bg-info/10'
)}>
  <span className={cn(
    'font-mono text-[11px] font-bold uppercase',
    diagnosisResult.recommended_action === 'immediate_stop' ? 'text-error' :
    diagnosisResult.recommended_action === 'limited_operation' ? 'text-warning' : 'text-info'
  )}>
    {diagnosisResult.recommended_action.replace(/_/g, ' ')}
  </span>
  {/* 紧急级别圆点 */}
  <div className="ml-auto flex gap-0.5">
    {Array.from({ length: 5 }).map((_, i) => (
      <span
        key={i}
        className={cn(
          'h-1.5 w-1.5 rounded-full',
          i < diagnosisResult.urgency_level
            ? diagnosisResult.urgency_level >= 4 ? 'bg-error'
              : diagnosisResult.urgency_level >= 3 ? 'bg-warning' : 'bg-info'
            : 'bg-bg-elevated'
        )}
      />
    ))}
  </div>
</div>
```

### 5.6 维保步骤列表

```tsx
<div className="space-y-2">
  {maintenancePlan.steps.map((step, i) => (
    <div
      key={step.step_id}
      className="flex gap-2.5 rounded-md border border-border-subtle bg-bg-elevated px-3 py-2.5"
    >
      <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-border-default bg-bg-surface font-mono text-[10px] text-text-muted">
        {step.step_id}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium text-text-primary">{step.action}</p>
        <p className="mt-0.5 text-[11px] leading-4 text-text-muted">{step.detail}</p>
        <div className="mt-1.5 flex gap-2">
          <span className={cn(
            'rounded border px-1.5 py-0.5 font-mono text-[10px]',
            step.risk_level === '高' ? 'border-error/30 text-error' :
            step.risk_level === '中' ? 'border-warning/30 text-warning' :
            'border-border-default text-text-disabled'
          )}>
            风险:{step.risk_level}
          </span>
          <span className="rounded border border-border-default px-1.5 py-0.5 font-mono text-[10px] text-text-disabled">
            {step.estimated_duration}
          </span>
        </div>
      </div>
    </div>
  ))}
</div>
```

### 5.7 孪生验证结果

```tsx
{verificationResult && (
  <div className={cn(
    'rounded-lg border p-3',
    verificationResult.success
      ? 'border-success/30 bg-success/5'
      : 'border-error/30 bg-error/5'
  )}>
    <div className="mb-2 flex items-center gap-2">
      <span className={cn(
        'font-mono text-xs font-bold',
        verificationResult.success ? 'text-success' : 'text-error'
      )}>
        {verificationResult.success ? '✓ 仿真验证通过' : '⚠ 验证未通过'}
      </span>
    </div>
    {/* delta 指标 */}
    <div className="grid grid-cols-2 gap-1.5">
      {Object.entries(verificationResult.delta_summary).map(([k, v]) => (
        <div key={k} className="rounded border border-border-subtle bg-bg-overlay px-2 py-1">
          <div className="font-mono text-[9px] uppercase text-text-disabled">{k}</div>
          <div className="font-mono text-[11px] text-success">{v}</div>
        </div>
      ))}
    </div>
    <p className="mt-2 text-[11px] leading-4 text-text-secondary">
      {verificationResult.verdict}
    </p>
  </div>
)}
```

### 5.8 操作按钮区

```tsx
<div className="flex gap-2 pt-1">
  <Button
    className="flex-1"
    disabled={maintenancePlan?.requires_supervisor || !verificationResult?.success}
    onClick={onConfirmExecution}
  >
    ✓ 确认执行
  </Button>
  <Button
    variant="outline"
    className="shrink-0 border-border-default text-text-secondary hover:border-warning hover:text-warning"
    onClick={onEscalateToTeacher}
  >
    上报教师
  </Button>
</div>
{maintenancePlan?.requires_supervisor && (
  <p className="text-center font-mono text-[10px] text-warning">
    ⚠ 此方案需教师审核后方可执行
  </p>
)}
```

---

## 六、执行顺序与优先级

```
Step 1：确认 CSS 变量和 Tailwind Config 完整（检查 globals.css + tailwind.config.ts）
         耗时：30分钟
         验收：所有 CSS 变量存在，Tailwind 自定义色可用

Step 2：重构 MonitorPage（完整替换，无业务逻辑风险）
         耗时：2-3小时
         验收：npm run build 通过，页面与 AgentWorkbenchPage 视觉一致

Step 3：精化 DiagnosisPanel 样式（按第五章规范对齐）
         耗时：2小时
         验收：DiagnosisPanel 在 AgentWorkbenchPage 和 SOPMaintenancePage 中样式一致

Step 4：分层重构 SOPMaintenancePage
         子步骤：
         4a. 替换顶部考试头部
         4b. 替换左栏 SOP 步骤卡片
         4c. 替换中栏 3D 视图卡片壳（不动 Canvas 内部）
         4d. 替换右栏零件信息面板
         4e. 替换爆炸滑块
         4f. 替换考试结束覆盖层
         每个子步骤后执行 npm run build 验证
         耗时：1天
         验收：全部 build 通过，adjudication 逻辑行为不变
```

---

## 七、禁止事项（给 Codex 的红线）

1. **禁止修改任何 `useAdjudicationStore`、`SOPExecutor`、`scoringEngine` 相关代码**
2. **禁止修改 Canvas / OrbitControls / three.js 相关代码**
3. **禁止删除或修改 `useSOPSceneSync` hook**
4. **禁止引入新的 UI 库**（只用 shadcn/ui + Tailwind，已有的 antd Modal/message 可保留）
5. **禁止使用任何硬编码颜色值**（包括 hex、rgba、antd token），全部用 CSS 变量或 Tailwind 类名
6. **禁止修改 API 调用层**（`@/api/`、`@/hooks/`）
7. **每完成一个 Step 必须执行 `npm run build` 验证，build 失败立即停止**

---

*文档版本：v1.0 | 基准参考：AgentWorkbenchPage.tsx（Claude Opus 4.6 生成版本）*
