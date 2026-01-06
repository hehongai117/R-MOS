# R-MOS Backend 360° 全景深度审计报告

**审计日期**: 2026-01-06
**审计版本**: V2.3
**审计范围**: `r-mos-backend/app/` 全部代码
**审计方法**: 三轮思维模型（静态结构 → 异步流 → 业务逻辑）

---

## 审计摘要

| 类别 | 数量 | 状态 |
|------|------|------|
| 🔴 致命缺陷 (Critical) | 1 | 需立即修复 |
| 🟡 逻辑隐患 (Warnings) | 4 | 建议修复 |
| 🔵 规范建议 (Nitpicks) | 3 | 可选优化 |
| ✅ 核心模块验证通过 | 8 | 无问题 |

---

## 🔴 致命缺陷 (Critical Bugs)

### C-001: TaskResponse 中 status 字段类型不匹配

**位置**: `app/schemas/task.py:25` vs `app/models/task.py:44-48`

**问题描述**:
- Schema 定义 `status: TaskStatus` (枚举类型)
- Model 定义 `status = Column(String(20), ...)` (字符串类型)
- Pydantic 的 `from_attributes = True` 会尝试将字符串转换为枚举，但数据库存储的是字符串值

**风险**:
- 当从数据库读取 Task 并序列化为 TaskResponse 时，如果数据库中存储的状态值与枚举不完全匹配，会导致验证错误
- FastAPI 返回 500 错误

**现状分析**:
```python
# Model (task.py:44-48)
status = Column(
    String(20),
    default=TaskStatus.PENDING.value,  # 存储字符串 "pending"
    nullable=False
)

# Schema (task.py:25)
status: TaskStatus  # 期望枚举类型
```

**修复建议**:
```python
# 方案A: Schema 改为 str 类型
status: str = Field(..., description="任务状态")

# 方案B: 添加验证器自动转换
from pydantic import field_validator

@field_validator('status', mode='before')
@classmethod
def convert_status(cls, v):
    if isinstance(v, str):
        return TaskStatus(v)
    return v
```

**严重程度**: 🔴 Critical - 可能导致 API 返回 500 错误

---

## 🟡 逻辑隐患 (Logical Risks)

### W-001: SOPService.delete_sop 中 task.status 类型处理

**位置**: `app/services/sop_service.py:147-148`

**问题描述**:
```python
"status": t.status.value  # 假设 status 是枚举
```
但 Task.status 在数据库中是 String(20)，直接取 `.value` 会报 AttributeError。

**风险**: 删除 SOP 时如果有关联 Task，会抛出 AttributeError 导致 500 错误。

**修复建议**:
```python
"status": t.status.value if hasattr(t.status, 'value') else t.status
# 或直接使用
"status": t.status if isinstance(t.status, str) else t.status.value
```

---

### W-002: get_task_report 中可能的 None 引用

**位置**: `app/api/v1/endpoints/tasks.py:153`

**问题描述**:
```python
total_duration_seconds=int((task.completed_at - task.started_at).total_seconds())
```
如果 `task.started_at` 为 None（理论上不应该，但防御性编程需要考虑），会抛出 TypeError。

**风险**: 极端情况下报告生成失败。

**修复建议**:
```python
total_duration_seconds=int((task.completed_at - task.started_at).total_seconds())
    if task.started_at and task.completed_at else 0
```

---

### W-003: ScoringService._calculate_stats 中 sop.steps 可能为 None

**位置**: `app/services/scoring_service.py:168`

**问题描述**:
```python
"total_steps": len(sop.steps) if sop else 0
```
虽然有 `if sop` 检查，但如果 SOP 已删除而 Task 仍存在（sop_id 被设为 NULL），`task.sop_id` 存在但 `await self._load_sop(task.sop_id)` 返回 None，这个逻辑是正确的。

**但是**，在 `calculate_score` 的第 103-116 行：
```python
if sop:
    for step in sop.steps:  # sop.steps 已通过 selectinload 预加载
```
如果 SOP 被删除，`sop` 为 None，`step_scores` 将为空列表，这是预期行为。

**状态**: ✅ 代码逻辑正确，无需修改。

---

### W-004: FaultCaseListItem 缺少 Config.from_attributes

**位置**: `app/schemas/fault.py:49-56`

**问题描述**:
```python
class FaultCaseListItem(BaseModel):
    id: int
    fault_code: str
    # ...
    # 缺少 class Config: from_attributes = True
```

在 `FaultCaseService.list_fault_cases` 中手动构造了 FaultCaseListItem，所以目前不会出错。但如果将来直接用 ORM 对象转换，会失败。

**风险**: 低 - 当前代码可正常工作，但不符合统一规范。

**修复建议**:
```python
class FaultCaseListItem(BaseModel):
    # ...
    class Config:
        from_attributes = True
```

---

## 🔵 规范建议 (Nitpicks)

### N-001: WebSocket 端点缺少心跳机制

**位置**: `app/api/v1/endpoints/websocket.py`

**描述**: 当前 WebSocket 端点只是被动等待客户端消息，没有主动推送心跳。如果客户端长时间不发送消息，连接可能被中间代理（如 Nginx）超时断开。

**建议**: 在 MVP 阶段可接受，生产环境应添加服务端心跳。

---

### N-002: 日志记录不统一

**描述**:
- 部分服务使用 `logger.info(f"...")`
- 部分使用 `logger.warning(f"...")`
- 建议统一日志格式，加入 request_id 或 trace_id 以便追踪

---

### N-003: 魔法数字硬编码

**位置**: 多处

**示例**:
- `app/services/scoring_service.py:64`: `stats["skipped_steps"] * 5.0` (跳过扣分)
- `app/services/scoring_service.py:74`: `stats["error_count"] * 10.0` (错误扣分)
- `app/services/scoring_service.py:84`: `15.0` (超时扣分)

**建议**: 将评分规则提取为配置常量或配置类。

---

## ✅ 核心模块验证通过

以下模块经过严格审计，确认逻辑正确、无致命缺陷：

### 1. API 路由参数对齐 ✅

| 文件 | 路径参数 | 函数参数 | 状态 |
|------|----------|----------|------|
| tasks.py | `{task_id}` | `task_id: int` | ✅ 一致 |
| sops.py | `{sop_id}` | `sop_id: int` | ✅ 一致 |
| fault_cases.py | `{fault_case_id}` | `fault_case_id: int` | ✅ 一致 |
| adapter.py | `{fault_code}` | `fault_code: str` | ✅ 一致 |

**结论**: 所有路由参数命名一致，无 `{id}` vs `{item_id}` 混用问题。

---

### 2. 异步 await 使用 ✅

对所有 Service 层进行了遍历检查：

| 服务 | db.execute | db.commit | db.flush | db.refresh | 状态 |
|------|------------|-----------|----------|------------|------|
| TaskService | ✅ | ✅ | ✅ | ✅ | 全部正确 |
| SOPService | ✅ | ✅ | ✅ | ✅ | 全部正确 |
| ScoringService | ✅ | N/A | N/A | N/A | 只读操作 |
| EventService | ✅ | N/A | ✅ | N/A | 全部正确 |
| SnapshotService | ✅ | N/A | ✅ | N/A | 全部正确 |
| FaultCaseService | ✅ | ✅ | N/A | ✅ | 全部正确 |

**结论**: 无 await 遗漏问题。

---

### 3. 事务闭环 (commit + refresh) ✅

| 方法 | commit 后 refresh | 状态 |
|------|-------------------|------|
| TaskService.create_task | ✅ Line 61-62 | 正确 |
| SOPService.create_sop | ✅ Line 64-65 | 正确 |
| FaultCaseService.create_fault_case | ✅ Line 94-95 | 正确 |
| FaultCaseService.update_fault_case | ✅ Line 115-116 | 正确 |

**结论**: 所有创建/更新操作都正确执行了 commit + refresh。

---

### 4. 连接池配置 ✅

**位置**: `app/core/database.py:14-20`

```python
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,  # ✅ 正确配置
    poolclass=NullPool if settings.DEBUG else None
)
```

**结论**: `pool_pre_ping=True` 已正确配置，可检测断开的连接。

---

### 5. 步骤顺序状态机 ✅

**位置**: `app/services/task_service.py:92-265`

**测试场景验证**:

| 场景 | 当前步骤 | 请求步骤 | 预期行为 | 实际代码 |
|------|----------|----------|----------|----------|
| 正常执行 | 0 | 1 | 执行成功 | ✅ Line 134-175 |
| 跳过可跳过步骤 | 0 | 2 | 记录跳过，执行步骤2 | ✅ Line 178-233 |
| 跳过不可跳过步骤 | 0 | 2 (is_critical) | 抛出 409 异常 | ✅ Line 189-198 |
| 乱序执行 | 0 | 5 | 抛出 409 异常 | ✅ Line 236-245 |
| 重复执行 | 2 | 2 | 抛出 409 异常 | ✅ Line 236-245 |

**结论**: 步骤顺序状态机逻辑完整正确。

---

### 6. SnapshotService 容错降级 ✅

**位置**: `app/services/snapshot_service.py:51-100`

```python
try:
    # 正常逻辑
except AdapterConnectionError as e:
    logger.warning(f"Snapshot创建失败（Adapter未连接）: {e}")
    return None  # ✅ 降级返回 None
except ConnectionError as e:
    return None  # ✅ 降级
except NotImplementedError as e:
    return None  # ✅ 降级
except Exception as e:
    logger.error(f"Snapshot创建失败（未知错误）: {e}")
    return None  # ✅ 降级
```

**调用方 TaskService.execute_step**:
```python
snapshot = await self.snapshot_service.create_snapshot(...)
if snapshot:
    snapshot_id = snapshot.id
    # 创建成功事件
else:
    # 创建失败事件（不阻断）
```

**结论**: Snapshot 失败不会阻断 Task 执行，降级策略正确实现。

---

### 7. ScoringService 空列表安全 ✅

**位置**: `app/services/scoring_service.py:153-170`

```python
def _calculate_stats(self, task: Task, events: List[Event], sop: Optional[SOP]) -> Dict[str, Any]:
    skipped_steps = sum(1 for e in events if e.event_type == EventType.STEP_SKIPPED.value)
    error_count = sum(1 for e in events if e.is_error)
    # ...
```

- 当 `events` 为空列表时，`sum(1 for e in events if ...)` 返回 0，不会出错
- 没有除法操作，不存在除以零风险

**结论**: 空列表情况处理正确，无崩溃风险。

---

### 8. SOP 删除保护 ✅

**位置**: `app/services/sop_service.py:103-180`

```python
async def delete_sop(self, sop_id: int, force: bool = False):
    # ...
    if affected_tasks and not force:
        raise BusinessRuleViolation(
            message=f"此SOP被{len(affected_tasks)}个Task引用，删除需要force=true参数",
            code="SOP_REFERENCED_BY_TASKS",
            # ...
        )
```

**测试验证**:
- `force=False` + 有关联 Task → 抛出 409 异常 ✅
- `force=True` + 有关联 Task → 执行删除，Task.sop_id 设为 NULL ✅
- `force=False` + 无关联 Task → 直接删除 ✅

**结论**: SOP 删除保护逻辑正确。

---

## 修复优先级建议

| 优先级 | 问题编号 | 描述 | 预估工时 |
|--------|----------|------|----------|
| P0 | C-001 | TaskResponse status 类型不匹配 | 15 分钟 |
| P1 | W-001 | SOPService 中 status 属性访问 | 10 分钟 |
| P2 | W-002 | get_task_report 防御性检查 | 5 分钟 |
| P3 | W-004 | FaultCaseListItem 添加 Config | 2 分钟 |

---

## 总结

R-MOS Backend V2.3 的代码质量整体良好，核心业务逻辑（Task 状态机、步骤跳过验证、Snapshot 降级、SOP 删除保护、评分计算）均通过了严格审计。

主要风险点集中在 **Task.status 字段的类型处理**，这是一个典型的 ORM 模型与 Pydantic Schema 之间的类型映射问题。建议优先修复 C-001，确保 API 返回稳定。

---

**审计人**: Claude (AI Architect)
**审计工具**: 静态代码分析 + 逻辑模拟
**下一步**: 等待开发团队确认修复方案后执行修复
