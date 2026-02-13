# AUTHZ_RBAC_SPEC｜注册、用户管理与权限体系规范

> **文档状态**: Final v1.0（一致性修订版 + 审批权限扩展）  
> **目标**: 补齐"用户与权限地基"，为教学闭环、裁决、证据链与 AI 工具调用提供可控边界  
> **依据**: PROJECT_MANUAL.md, 注册_用户管理与权限体系_R-MOS_.md  
> **前置依赖**: 本规范是 AI_TWIN_AGENT_SPEC 与 AI_AUTHZ_INTEGRATION_SPEC 的必需前置

---

## 0. 核心结论

1. **所有写操作必须三要素**: 身份校验（Authentication）+ 权限校验（Authorization）+ 审计记录（Audit）
2. **双层权限控制**: API 级（路由保护）+ 对象级（资源归属与范围校验）
3. **审计可追溯**: 每次 deny 与关键 write 必写 audit_events，支持按 user/resource/time 查询

---

## 1. 范围（In Scope / Out Scope）

### 1.1 In Scope
- 注册 / 登录 / 刷新 / 登出 / 密码找回与重置
- 用户资料管理（CRUD）
- 角色与权限（RBAC）+ 对象级权限规则
- 路由保护（API-level）与资源级权限校验（Object-level）
- 审计日志（关键写操作必须记录）
- Token 管理（access + refresh，支持撤销）
- **审批权限体系**（approvals 资源域）

### 1.2 Out of Scope（本阶段不实现）
- 企业 SSO / OIDC / SAML 集成
- 多租户（Tenant）完整隔离（可预留字段但不实现逻辑）
- 权限可视化管理 UI（后端先提供 API）
- 细粒度 ABAC（Attribute-Based Access Control，可作为后续演进方向）

---

## 2. 背景与现状

### 2.1 现状边界
[source: PROJECT_MANUAL.md#4. 已经实现的功能]
- **已实现路由**: HTTP 65 + WebSocket 1
- **已实现业务闭环**: SOP → Task → Event/Snapshot → Score → Report → EvidenceBundle
- **已实现教学域**: Assignment → Attempt → TaskExecution → DiagnosisService
- **已实现数据模型**: 21 张表，涵盖 SOP/执行、故障、观测/事件、证据、外部评估、教学

### 2.2 已确认缺口
[source: PROJECT_MANUAL.md#6. 当前边界与已知缺口]
- **DEF-SEC-001**: 未实现鉴权/授权，当前 API 基本无身份鉴别
- 部分管理页面仅靠前端入口区分，无后端权限校验

### 2.3 需求驱动
- 教学域与裁决/证据域需区分访问边界（teacher vs student）
- AI 工具调用需继承权限体系（详见 AI_AUTHZ_INTEGRATION_SPEC.md）
- 未来需支持审批流（approval）与高风险动作管控

---

## 3. 角色与权限模型（RBAC V1）

### 3.1 角色定义（Roles）

| 角色 | 职责范围 | 典型权限 |
|------|---------|---------|
| **admin** | 系统全域管理 | 用户/角色管理、全域资源读写、审计查询、高危动作（故障注入）、全域审批权限 |
| **teacher** | 教学域管理 | 课程/班级/作业管理、SOP 管理（可选）、学生 attempt/evidence/diagnosis 评阅、课程范围内审批（medium/high） |
| **student** | 学习与执行 | 执行任务、提交 attempt、仅访问本人资源（attempt/evidence/diagnosis） |
| **auditor** | 审计与合规 | 只读审计日志、只读回放数据、参与 critical 审批（二次确认）、受字段脱敏规则约束（后续） |

[design add: auditor 角色新增，rationale: 支持外部评估/质控/合规场景，符合"可治理"原则]

### 3.2 资源与动作（Resources & Actions）

| 资源类型 | 动作（Actions） | 角色权限映射 |
|---------|----------------|-------------|
| users | read, write | admin: read+write; teacher/student/auditor: read(self) |
| roles | read, write | admin: read+write |
| permissions | read, write | admin: read+write |
| sops | read, write | admin/teacher: read+write; student: read |
| tasks | read, write | admin/teacher: read+write; student: read+write(own) |
| events | read | admin/teacher: read; student: read(own task) |
| snapshots | read | admin/teacher: read; student: read(own task) |
| evidence_bundles | read | admin/teacher: read; student: read(own attempt) |
| diagnoses | read | admin/teacher: read; student: read(own attempt) |
| courses/classes/enrollments | read, write | admin/teacher: read+write; student: read(enrolled) |
| assignments | read, write | admin/teacher: read+write; student: read |
| assignment_attempts | read, write | admin: read+write; teacher: read+write(own course); student: read+write(own) |
| faults (inject/clear) | write | admin: write; teacher: write(if granted); student: deny |
| assessments | read, write | admin: read+write; teacher: read+write(own course); auditor: read |
| audit_events | read | admin/auditor: read |
| **approvals** | read, propose, approve, reject | **见 3.3** |

### 3.3 审批资源域（Approvals）权限映射

**新增资源**: approvals

**权限键定义**:

| Permission Key | 描述 | 默认角色 |
|----------------|------|---------|
| approvals:read | 读取审批记录 | admin, teacher, auditor |
| approvals:propose | 发起审批请求（通常为系统/执行者） | admin, teacher, student（系统代理） |
| approvals:approve | 审批/同意 | admin, teacher, auditor（限 critical） |
| approvals:reject | 拒绝审批 | admin, teacher, auditor（限 critical） |

**角色映射细则**:

| 角色 | approvals:read | approvals:propose | approvals:approve | approvals:reject | 约束 |
|------|---------------|-------------------|-------------------|------------------|------|
| admin | ✓ | ✓ | ✓ | ✓ | 全域，无限制 |
| teacher | ✓（课程范围） | ✓（课程范围） | ✓ | ✓ | 仅限 medium/high，不包含 critical（除非配置为 critical 的第一审批人） |
| student | ✗ | ✗（系统代理） | ✗ | ✗ | 学生不直接审批，系统代其发起 propose |
| auditor | ✓ | ✗ | ✓（仅 critical） | ✓（仅 critical） | 仅参与 critical 的二次确认，不允许普通写操作 |

**硬约束**:
1. **auditor 仅参与 critical 审批**: auditor 的 approvals:approve/reject 权限受 Approval.risk_level=critical 约束，尝试审批 medium/high 必须返回 403
2. **teacher 对 critical 的参与**: teacher 可作为 critical 的第一审批人（如 teacher+auditor 组合），但不能单独完成 critical 审批
3. **propose 权限**: 学生发起的 AI Command 若触发审批，由系统代理执行 propose（actor_user_id 为学生，但 propose 权限由系统持有）

### 3.4 对象级权限规则（Object-level，必备）

| 规则 ID | 规则描述 | 实施位置 |
|---------|---------|---------|
| OBJ-001 | student 只能访问本人的 assignment_attempts 及其关联 evidence/diagnosis | Service 层：AttemptService.get_attempt() |
| OBJ-002 | teacher 只能访问其课程/班级范围内的 attempts/evidence/diagnosis | Service 层：通过 enrollments/courses 关联校验 |
| OBJ-003 | admin 可访问全部；auditor 只读且受字段脱敏规则（后续） | Service 层：role 判断 + 字段过滤器（未来） |
| OBJ-004 | task/event/snapshot 的访问受 task.created_by 或 attempt.user_id 约束 | Service 层：TaskService/EventService/SnapshotService |
| **OBJ-005** | **auditor 仅可审批 risk_level=critical 的 approvals** | Service 层：ApprovalService.approve/reject() |

---

## 4. 全局响应码规则（Global Access Response Policy）

**硬约束**：所有对象级越权必须遵守以下统一策略，禁止二义性。

### 4.1 响应码规则

| 场景 | HTTP Method | 越权情况 | 返回码 | 理由 |
|------|-------------|---------|--------|------|
| 读取资源 | GET | 资源不存在或无权访问 | **404 Not Found** | 防止资源探测，隐藏资源存在性 |
| 创建资源 | POST | 无权限创建 | **403 Forbidden** | 明确告知"禁止该操作" |
| 更新资源 | PATCH/PUT | 无权限更新 | **403 Forbidden** | 明确告知"禁止该操作" |
| 删除资源 | DELETE | 无权限删除 | **403 Forbidden** | 明确告知"禁止该操作" |

### 4.2 审计要求

**所有 deny 场景（无论返回 404 还是 403）必须写入 audit_events**，包含：
- `decision: "deny"`
- `resource_type` 与 `resource_id`（真实 ID，即使返回 404）
- `reason`（如 "not_owner", "not_in_course_scope", "insufficient_role"）

### 4.3 实施指南

**Service 层伪代码**（规范约定）：
```python
# Read 场景（GET）
async def get_attempt(self, attempt_id: UUID, current_user: User) -> Attempt:
    attempt = await self.repo.get_by_id(attempt_id)
    if not attempt:
        raise NotFoundError()  # 真正不存在 → 404
    
    # 对象级权限校验
    if not self._can_access(current_user, attempt):
        await audit_log(
            actor=current_user, 
            action="access_denied",
            resource_type="attempt", 
            resource_id=attempt_id,  # 记录真实 ID
            decision="deny", 
            reason="not_owner"
        )
        raise NotFoundError()  # 越权 → 404（隐藏存在性）
    
    return attempt

# Write 场景（POST/PATCH/DELETE）
async def update_attempt(self, attempt_id: UUID, data, current_user: User):
    attempt = await self.repo.get_by_id(attempt_id)
    if not attempt:
        raise NotFoundError()  # 真正不存在 → 404
    
    # 对象级权限校验
    if not self._can_modify(current_user, attempt):
        await audit_log(
            actor=current_user, 
            action="modify_denied",
            resource_type="attempt", 
            resource_id=attempt_id,
            decision="deny", 
            reason="not_owner"
        )
        raise ForbiddenError()  # 越权 → 403（明确禁止）
    
    # ... 执行更新

# Approval 场景（审批权限校验）
async def approve_approval(self, approval_id: UUID, current_user: User):
    approval = await self.repo.get_by_id(approval_id)
    if not approval:
        raise NotFoundError()
    
    # 权限校验
    if not current_user.has_permission("approvals:approve"):
        await audit_log(
            actor=current_user,
            action="approval_denied",
            resource_type="approval",
            resource_id=approval_id,
            decision="deny",
            reason="missing_permission:approvals:approve"
        )
        raise ForbiddenError()  # 无审批权限 → 403
    
    # auditor 仅可审批 critical（OBJ-005）
    if current_user.has_role("auditor") and approval.risk_level != "critical":
        await audit_log(
            actor=current_user,
            action="approval_denied",
            resource_type="approval",
            resource_id=approval_id,
            decision="deny",
            reason="auditor_only_critical"
        )
        raise ForbiddenError()  # auditor 审批非 critical → 403
    
    # ... 执行审批
```

**关键原则**：
1. Read 越权返回 404（防探测）
2. Write 越权返回 403（明确禁止）
3. 审计必须记录真实 resource_id（即使对外返回 404）

---

## 5. 数据模型（Database Schema）

### 5.1 核心表结构

#### users
```
id: UUID (PK)
email: String (unique, not null)
password_hash: String (not null)
full_name: String (nullable)
is_active: Boolean (default: true)
is_verified: Boolean (default: false)
created_at: DateTime
updated_at: DateTime
last_login_at: DateTime (nullable)
```

#### roles
```
id: UUID (PK)
name: String (unique, not null)  # admin, teacher, student, auditor
description: String (nullable)
created_at: DateTime
updated_at: DateTime
```

#### permissions
```
id: UUID (PK)
key: String (unique, not null)  # 格式: "resource:action", 如 "assignments:write", "approvals:approve"
description: String (nullable)
resource_type: String (not null)  # users, sops, tasks, attempts, approvals, etc.
action: String (not null)  # read, write, delete, propose, approve, reject
created_at: DateTime
```

#### user_roles (多对多关系表)
```
id: UUID (PK)
user_id: UUID (FK -> users.id)
role_id: UUID (FK -> roles.id)
granted_by: UUID (FK -> users.id, nullable)
granted_at: DateTime
expires_at: DateTime (nullable)
```

#### role_permissions (多对多关系表)
```
id: UUID (PK)
role_id: UUID (FK -> roles.id)
permission_id: UUID (FK -> permissions.id)
created_at: DateTime
```

#### refresh_tokens
```
id: UUID (PK)
user_id: UUID (FK -> users.id)
token_hash: String (unique, not null)
is_revoked: Boolean (default: false)
expires_at: DateTime (not null)
created_at: DateTime
```

#### audit_events
```
id: UUID (PK)
actor_user_id: UUID (FK -> users.id, nullable)  # nullable 支持系统自动动作
action: String (not null)  # login, logout, create, update, delete, access_denied, approval_granted, etc.
resource_type: String (nullable)  # sops, tasks, attempts, approvals, etc.
resource_id: UUID (nullable)
decision: String (not null)  # allow, deny
reason: String (nullable)  # 策略命中说明或拒绝原因
request_meta: JSONB (nullable)  # {ip, user_agent, trace_id, endpoint, method}
created_at: DateTime
```

---

## 6. API 设计（v1）

### 6.1 Auth Endpoints

| Method | Path | Auth | Description | Response |
|--------|------|------|-------------|----------|
| POST | /api/v1/auth/register | Public | 用户注册 | {user_id, email, message} |
| POST | /api/v1/auth/login | Public | 登录 | {access_token, refresh_token, expires_in, user} |
| POST | /api/v1/auth/refresh | Public | 刷新 access token | {access_token, expires_in} |
| POST | /api/v1/auth/logout | Auth | 登出（撤销 refresh token） | {message} |
| POST | /api/v1/auth/password/forgot | Public | 发送密码重置邮件 | {message} |
| POST | /api/v1/auth/password/reset | Public | 重置密码（需 token） | {message} |
| GET | /api/v1/auth/me | Auth | 获取当前用户信息 | {user, roles, permissions} |

### 6.2 User Management (Admin Only)

| Method | Path | Auth | Permission | Description |
|--------|------|------|-----------|-------------|
| GET | /api/v1/admin/users | Auth | users:read | 用户列表（支持分页/筛选） |
| POST | /api/v1/admin/users | Auth | users:write | 创建用户 |
| GET | /api/v1/admin/users/{user_id} | Auth | users:read | 用户详情 |
| PATCH | /api/v1/admin/users/{user_id} | Auth | users:write | 更新用户 |
| DELETE | /api/v1/admin/users/{user_id} | Auth | users:write | 删除/禁用用户 |
| POST | /api/v1/admin/users/{user_id}/roles | Auth | users:write | 分配角色 |
| DELETE | /api/v1/admin/users/{user_id}/roles/{role_id} | Auth | users:write | 移除角色 |

### 6.3 Role & Permission Management (Admin Only)

| Method | Path | Auth | Permission | Description |
|--------|------|------|-----------|-------------|
| GET | /api/v1/admin/roles | Auth | roles:read | 角色列表 |
| POST | /api/v1/admin/roles | Auth | roles:write | 创建角色 |
| GET | /api/v1/admin/roles/{role_id} | Auth | roles:read | 角色详情 |
| PATCH | /api/v1/admin/roles/{role_id} | Auth | roles:write | 更新角色 |
| DELETE | /api/v1/admin/roles/{role_id} | Auth | roles:write | 删除角色 |
| GET | /api/v1/admin/permissions | Auth | permissions:read | 权限列表 |
| POST | /api/v1/admin/roles/{role_id}/permissions | Auth | roles:write | 分配权限 |
| DELETE | /api/v1/admin/roles/{role_id}/permissions/{perm_id} | Auth | roles:write | 移除权限 |

### 6.4 Audit Endpoints (Admin / Auditor)

| Method | Path | Auth | Permission | Description |
|--------|------|------|-----------|-------------|
| GET | /api/v1/audit/events | Auth | audit_events:read | 审计日志列表（支持筛选） |
| GET | /api/v1/audit/events/{audit_id} | Auth | audit_events:read | 审计日志详情 |

**Query Parameters for GET /api/v1/audit/events**:
- `user_id` (UUID, optional): 筛选特定用户
- `resource_type` (string, optional): 筛选资源类型
- `resource_id` (UUID, optional): 筛选特定资源
- `action` (string, optional): 筛选动作类型
- `decision` (string, optional): allow / deny
- `from` (ISO datetime, optional): 起始时间
- `to` (ISO datetime, optional): 结束时间
- `page` (int, default: 1)
- `page_size` (int, default: 50, max: 200)

---

## 7. 路由保护与依赖注入规范

### 7.1 API-Level Protection（路由级）

**实施方式**: FastAPI Dependency Injection

```python
# 伪代码示例（规范约定，非实际代码）
from fastapi import Depends, HTTPException, status
from app.core.auth import get_current_user, require_role, require_permission

# 1. 基础认证保护
@app.get("/api/v1/tasks/{task_id}")
async def get_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user)  # 401 if not authenticated
):
    ...

# 2. 角色级保护
@app.get("/api/v1/admin/users")
async def list_users(
    current_user: User = Depends(require_role("admin"))  # 403 if not admin
):
    ...

# 3. 权限级保护（更细粒度）
@app.post("/api/v1/assignments")
async def create_assignment(
    data: AssignmentCreate,
    current_user: User = Depends(require_permission("assignments:write"))
):
    ...

# 4. 审批权限保护
@app.post("/api/v1/ai/approvals/{approval_id}/confirm")
async def approve_approval(
    approval_id: UUID,
    current_user: User = Depends(require_permission("approvals:approve"))
):
    # 内部还需检查 auditor 的 critical 约束（OBJ-005）
    ...
```

**保护策略**:
- 所有 `/api/v1/` 下的路由（除 auth/register, auth/login, auth/refresh, auth/password/forgot, auth/password/reset 外）必须添加 `Depends(get_current_user)`
- `/api/v1/admin/*` 路由必须添加 `Depends(require_role("admin"))`
- 高危路由（如 `/api/v1/adapter/inject-fault`）必须添加额外权限校验

### 7.2 Object-Level Protection（资源级）

**实施位置**: Service 层，在加载资源后立即校验

**校验流程**:
1. **Load Resource**: 从数据库加载资源对象
2. **Check Ownership/Scope**: 校验资源归属或范围
3. **Authorize**: 根据角色与对象关系决定 allow/deny
4. **Audit**: 记录决策（尤其是 deny）
5. **Return**: allow 返回资源；deny 抛异常（遵循 4.1 响应码规则）

**关键原则**（引用 4.1 全局响应码规则）：
- **Read 越权**（GET）→ 404 Not Found
- **Write 越权**（POST/PATCH/DELETE）→ 403 Forbidden
- **审计必须记录真实 resource_id**

---

## 8. 安全策略（V1）

### 8.1 Token 策略
- **Access Token**: 短时有效（15 分钟），包含 user_id、roles、permissions（精简版）
- **Refresh Token**: 长时有效（7 天），存储在 `refresh_tokens` 表，支持撤销
- **Token 格式**: JWT (HS256 或 RS256)
- **撤销机制**: logout 时标记 `refresh_tokens.is_revoked = true`

### 8.2 密码策略
- **强度要求**: 最少 8 字符，必须包含大小写字母、数字、特殊字符
- **哈希算法**: bcrypt（cost factor = 12）或 argon2
- **密码重置**: 发送时效性 token（有效期 1 小时），使用后立即失效

### 8.3 审计策略
- **必须审计的事件**:
  - 登录/登出/刷新失败
  - 所有 deny（遵循 4.2 审计要求）
  - 所有写操作（create/update/delete）
  - 高危动作（inject-fault, publish_grades, bulk_dispatch）
  - **审批动作**（approval_granted, approval_rejected）
- **审计字段**: 见 audit_events 表结构（actor, action, resource, decision, reason, request_meta）

### 8.4 高危动作管控
- **故障注入** (`POST /api/v1/adapter/inject-fault`): 默认仅 admin
- **批量派单** (`POST /api/v1/assignments/bulk-dispatch`): 需 teacher + 审计（未来可升级为审批）
- **评分发布** (`POST /api/v1/assignments/{id}/publish-grades`): 需 teacher + 审计

---

## 9. 失败处理与错误响应

### 9.1 标准错误响应结构
```json
{
  "error": {
    "code": "AUTH_001",  // 错误代码
    "message": "Invalid credentials",  // 用户可读消息
    "details": {  // 可选，调试信息
      "field": "password",
      "reason": "密码错误"
    }
  }
}
```

### 9.2 常见错误代码

| Code | HTTP Status | 描述 | 触发场景 |
|------|-------------|------|---------|
| AUTH_001 | 401 | Invalid credentials | 登录密码错误 |
| AUTH_002 | 401 | Token expired | Access token 过期 |
| AUTH_003 | 401 | Token invalid | Token 格式错误或签名不匹配 |
| AUTH_004 | 401 | Refresh token revoked | Refresh token 已撤销 |
| AUTHZ_001 | 403 | Insufficient permissions | 权限不足（Write 操作） |
| AUTHZ_002 | 403 | Role required | 缺少必需角色 |
| AUTHZ_003 | 403 | Resource access denied | 对象级权限校验失败（Write 操作） |
| AUTHZ_004 | 404 | Resource not found | 对象不存在或无权访问（Read 操作，遵循 4.1） |
| **AUTHZ_005** | **403** | **Auditor role restriction** | auditor 尝试审批非 critical 或执行普通写操作 |
| USER_001 | 400 | Email already exists | 注册时邮箱重复 |
| USER_002 | 400 | Weak password | 密码强度不足 |
| USER_003 | 404 | User not found | 用户不存在 |

### 9.3 失败审计
- 所有 401/403/404（权限相关）必须写入 `audit_events`（遵循 4.2 审计要求），包含：
  - actor_user_id（如有）
  - action: "access_denied" 或具体动作
  - resource_type, resource_id（真实 ID）
  - decision: "deny"
  - reason: 具体拒绝原因
  - request_meta: {ip, endpoint, method}

---

## 10. 验收与测试用例

### 10.1 Authentication Tests

| Test ID | 场景 | 前置条件 | 操作 | 预期结果 |
|---------|------|---------|------|---------|
| AUTH-T001 | 注册成功 | 无 | POST /auth/register (有效数据) | 201, user_id 返回 |
| AUTH-T002 | 注册失败（邮箱重复） | 已存在用户 | POST /auth/register (重复邮箱) | 400, USER_001 |
| AUTH-T003 | 注册失败（弱密码） | 无 | POST /auth/register (密码=123) | 400, USER_002 |
| AUTH-T004 | 登录成功 | 已注册用户 | POST /auth/login (正确凭证) | 200, access_token + refresh_token |
| AUTH-T005 | 登录失败（密码错误） | 已注册用户 | POST /auth/login (错误密码) | 401, AUTH_001 |
| AUTH-T006 | 刷新成功 | 有效 refresh_token | POST /auth/refresh | 200, new access_token |
| AUTH-T007 | 刷新失败（已撤销） | 已登出 | POST /auth/refresh (revoked token) | 401, AUTH_004 |
| AUTH-T008 | 登出成功 | 已登录 | POST /auth/logout | 200, refresh_token 撤销 |
| AUTH-T009 | Access token 过期 | 过期 token | GET /auth/me (过期 token) | 401, AUTH_002 |

### 10.2 Authorization Tests (RBAC)

| Test ID | 场景 | 前置条件 | 操作 | 预期结果 |
|---------|------|---------|------|---------|
| AUTHZ-T001 | Admin 访问 admin 路由 | 已登录 admin | GET /admin/users | 200, 用户列表 |
| AUTHZ-T002 | Teacher 访问 admin 路由 | 已登录 teacher | GET /admin/users | 403, AUTHZ_002 |
| AUTHZ-T003 | Student 访问 admin 路由 | 已登录 student | GET /admin/users | 403, AUTHZ_002 |
| AUTHZ-T004 | 未登录访问受保护路由 | 无 | GET /tasks/123 (无 token) | 401, AUTH_003 |

### 10.3 Object-Level Authorization Tests（遵循 4.1 响应码规则）

| Test ID | 场景 | 前置条件 | 操作 | 预期结果 |
|---------|------|---------|------|---------|
| OBJ-T001 | Student 访问本人 attempt | 已登录 student A, attempt 属于 A | GET /teaching/attempts/{A_attempt_id} | 200, attempt 详情 |
| OBJ-T002 | Student 访问他人 attempt（READ） | 已登录 student A, attempt 属于 B | GET /teaching/attempts/{B_attempt_id} | **404**, AUTHZ_004 + audit_event(deny) |
| OBJ-T003 | Teacher 访问本课程 attempt | 已登录 teacher, attempt 在其课程 | GET /teaching/attempts/{attempt_id} | 200, attempt 详情 |
| OBJ-T004 | Teacher 访问非本课程 attempt（READ） | 已登录 teacher, attempt 在他人课程 | GET /teaching/attempts/{attempt_id} | **404**, AUTHZ_004 + audit_event(deny) |
| OBJ-T005 | Admin 访问任意 attempt | 已登录 admin | GET /teaching/attempts/{any_attempt_id} | 200, attempt 详情 |
| OBJ-T006 | Student 访问本人 evidence | 已登录 student A | GET /teaching/attempts/{A_attempt_id}/evidence | 200, evidence 列表 |
| OBJ-T007 | Student 访问他人 evidence（READ） | 已登录 student A | GET /teaching/attempts/{B_attempt_id}/evidence | **404**, AUTHZ_004 + audit_event(deny) |
| OBJ-T008 | Student 修改他人 attempt（WRITE） | 已登录 student A | PATCH /teaching/attempts/{B_attempt_id} | **403**, AUTHZ_003 + audit_event(deny) |
| OBJ-T009 | Teacher 删除非本课程 attempt（WRITE） | 已登录 teacher | DELETE /teaching/attempts/{other_course_attempt_id} | **403**, AUTHZ_003 + audit_event(deny) |

### 10.4 Approval Permission Tests（新增）

| Test ID | 场景 | 前置条件 | 操作 | 预期结果 |
|---------|------|---------|------|---------|
| APPR-T001 | Teacher 审批 medium 风险 | 已登录 teacher, approval(medium) pending | POST /ai/approvals/{id}/confirm | 200, approval.status=approved + audit_event |
| APPR-T002 | Auditor 审批 critical 风险 | 已登录 auditor, approval(critical) pending（已有 teacher 确认） | POST /ai/approvals/{id}/confirm | 200, approval.status=approved + audit_event |
| APPR-T003 | Auditor 尝试审批 medium 风险 | 已登录 auditor, approval(medium) pending | POST /ai/approvals/{id}/confirm | **403**, AUTHZ_005 + audit_event(deny, reason=auditor_only_critical) |
| APPR-T004 | Student 尝试审批 | 已登录 student, approval pending | POST /ai/approvals/{id}/confirm | 403, AUTHZ_001 (missing approvals:approve) |
| APPR-T005 | Critical 双人确认（teacher+auditor） | 已登录 teacher, approval(critical) pending | 1. Teacher confirm → status=pending（需第二人）<br>2. Auditor confirm → status=approved | 两步完成后 status=approved |
| APPR-T006 | Auditor 缺权时审批失败 | Auditor 角色未分配 approvals:approve | POST /ai/approvals/{id}/confirm | 403, AUTHZ_001 + audit_event |

### 10.5 Audit Tests

| Test ID | 场景 | 前置条件 | 操作 | 预期结果 |
|---------|------|---------|------|---------|
| AUDIT-T001 | Deny 事件被记录（READ） | 已登录 student A | GET /teaching/attempts/{B_attempt_id} | 404 + audit_events 新增记录(decision=deny, resource_id=B_attempt_id) |
| AUDIT-T002 | 写操作被记录 | 已登录 teacher | POST /assignments | 201 + audit_events 新增记录(action=create) |
| AUDIT-T003 | 审计日志可查询（按用户） | 已有审计记录 | GET /audit/events?user_id={A_id} | 200, 返回 A 的所有记录 |
| AUDIT-T004 | 审计日志可查询（按资源） | 已有审计记录 | GET /audit/events?resource_type=attempt | 200, 返回 attempt 相关记录 |
| AUDIT-T005 | 审计日志可查询（按时间） | 已有审计记录 | GET /audit/events?from=2026-02-01&to=2026-02-05 | 200, 返回时间范围内记录 |
| AUDIT-T006 | Deny 事件记录真实 resource_id | 已登录 student A | GET /teaching/attempts/{B_attempt_id} | audit_events 记录含真实 B_attempt_id（即使返回 404） |
| **AUDIT-T007** | **审批动作被记录** | teacher confirm approval | POST /ai/approvals/{id}/confirm | audit_events 新增记录(action=approval_granted, resource_type=approval, resource_id=approval_id) |

### 10.6 High-Risk Action Tests

| Test ID | 场景 | 前置条件 | 操作 | 预期结果 |
|---------|------|---------|------|---------|
| RISK-T001 | Admin 故障注入 | 已登录 admin | POST /adapter/inject-fault | 200 + audit_event(action=inject_fault) |
| RISK-T002 | Teacher 故障注入 | 已登录 teacher | POST /adapter/inject-fault | 403, AUTHZ_001 + audit_event(deny) |
| RISK-T003 | Student 故障注入 | 已登录 student | POST /adapter/inject-fault | 403, AUTHZ_001 + audit_event(deny) |

---

## 11. 迁移与里程碑

### Phase 0: 基础表与依赖（Week 1）
- [ ] 创建 users, roles, permissions, user_roles, role_permissions, refresh_tokens, audit_events 表
- [ ] Alembic 迁移脚本编写与测试
- [ ] 种子数据（默认角色 + 权限，**包含 approvals 权限键**）

### Phase 1: Auth API（Week 2）
- [ ] 实现 POST /auth/register, /auth/login, /auth/refresh, /auth/logout
- [ ] 实现 Token 生成与验证（JWT）
- [ ] 实现密码哈希（bcrypt）
- [ ] 单元测试（AUTH-T001 ~ AUTH-T009）

### Phase 2: RBAC 中间件（Week 3）
- [ ] 实现 get_current_user, require_role, require_permission 依赖
- [ ] 保护现有路由（API-level）
- [ ] 单元测试（AUTHZ-T001 ~ AUTHZ-T004）

### Phase 3: Object-Level 校验（Week 4）
- [ ] AttemptService/EvidenceService/DiagnosisService 增加对象级权限校验（遵循 4.1 响应码规则）
- [ ] TaskService/EventService/SnapshotService 增加对象级权限校验（遵循 4.1 响应码规则）
- [ ] **ApprovalService 增加 auditor critical 约束校验（OBJ-005）**
- [ ] 单元测试（OBJ-T001 ~ OBJ-T009, APPR-T001 ~ APPR-T006）

### Phase 4: 审计与高危动作（Week 5）
- [ ] 实现 audit_log 工具函数（遵循 4.2 审计要求）
- [ ] 在所有 Service 层写操作与 deny 场景插入审计
- [ ] 实现 GET /audit/events API
- [ ] 单元测试（AUDIT-T001 ~ AUDIT-T007, RISK-T001 ~ RISK-T003）

### Phase 5: User/Role Management API（Week 6）
- [ ] 实现 /admin/users, /admin/roles, /admin/permissions CRUD
- [ ] 实现角色分配/撤销
- [ ] 集成测试（端到端场景）

### Phase 6: 前端集成与 E2E 测试（Week 7-8）
- [ ] 前端登录/登出/token 刷新逻辑
- [ ] 前端路由守卫（基于角色）
- [ ] E2E 测试（Playwright/Cypress）

---

## 12. 附录：权限键值规范（Permission Keys）

### 格式
`{resource}:{action}`

### 预定义权限清单

| Permission Key | 描述 | 默认角色 |
|----------------|------|---------|
| users:read | 读取用户信息 | admin |
| users:write | 创建/更新/删除用户 | admin |
| roles:read | 读取角色信息 | admin |
| roles:write | 创建/更新/删除角色 | admin |
| permissions:read | 读取权限信息 | admin |
| permissions:write | 创建/更新/删除权限 | admin |
| sops:read | 读取 SOP | admin, teacher, student |
| sops:write | 创建/更新/删除 SOP | admin, teacher |
| tasks:read | 读取任务 | admin, teacher, student |
| tasks:write | 创建/更新/删除任务 | admin, teacher |
| assignments:read | 读取作业 | admin, teacher, student |
| assignments:write | 创建/更新/删除作业 | admin, teacher |
| assignment_attempts:read | 读取提交（受对象级规则约束） | admin, teacher, student |
| assignment_attempts:write | 创建/更新提交（受对象级规则约束） | admin, teacher, student |
| evidence_bundles:read | 读取证据包（受对象级规则约束） | admin, teacher, student |
| diagnoses:read | 读取诊断（受对象级规则约束） | admin, teacher, student |
| faults:write | 故障注入/清除 | admin |
| assessments:read | 读取评估 | admin, teacher, auditor |
| assessments:write | 创建/更新/删除评估 | admin, teacher |
| audit_events:read | 读取审计日志 | admin, auditor |
| **approvals:read** | **读取审批记录** | **admin, teacher, auditor** |
| **approvals:propose** | **发起审批请求** | **admin, teacher, student（系统代理）** |
| **approvals:approve** | **审批/同意** | **admin, teacher, auditor（限 critical）** |
| **approvals:reject** | **拒绝审批** | **admin, teacher, auditor（限 critical）** |

[design add: approvals 权限键为 AI 审批流提供可落地权限控制，rationale: auditor 参与 critical 审批必须有明确权限基础]

---

## 13. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Token 泄露 | 未授权访问 | 短时 access token + refresh token 撤销机制 + HTTPS 强制 |
| 权限提升攻击 | 越权操作 | 对象级权限校验（遵循 4.1）+ 审计（遵循 4.2）+ 角色分配审批（未来） |
| 审计日志篡改 | 可追溯性失效 | audit_events 表只允许 INSERT（应用层约束） + 数据库备份 |
| 密码暴力破解 | 账户劫持 | 登录失败限流（Rate Limiting）+ 强密码策略 + 邮箱验证 |
| Session fixation | 会话劫持 | 登录后强制刷新 token + secure cookie（未来如用 cookie） |
| 响应码信息泄露 | 资源探测 | Read 越权统一返回 404（遵循 4.1），隐藏资源存在性 |
| **Auditor 权限滥用** | **审批非 critical 动作** | **OBJ-005 约束 + API 层 approvals:approve 检查 risk_level + 审计** |

---

**文档结束**
