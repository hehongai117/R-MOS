# 注册流程优化：学校校验 + 角色绑定 + 教师 Onboarding

## 背景

当前注册流程只采集邮箱/密码/姓名，默认角色 student，无学校归属、无教师绑定、无机器人绑定。导致新注册用户无法看到任何机器人模型，无法使用平台核心功能。

## 目标

1. 教师注册时选择学校（白名单校验），注册后强制完成机器人选择才能使用平台
2. 学生注册时选择学校 + 绑定教师，注册后自动关联教师名下机器人
3. 学校名称来自教育部官方名录，写入数据库白名单表

## 用户流程

### 教师注册流程

```
Step 1: 输入邮箱、密码、姓名，选择角色「教师」
Step 2: 输入学校全称（自动补全，后端校验白名单）
Step 3: 注册成功 → 自动登录 → 跳转「机器人选择页」
Step 4: 勾选 1~5 台机器人 → 创建 TeacherRobotBinding → 进入 Dashboard
```

- 教师未完成机器人选择（`onboarding_completed = false`）时，前端拦截所有路由到机器人选择页
- 机器人选择页展示所有 `status = ready` 的机器人，教师勾选后批量创建绑定

### 学生注册流程

```
Step 1: 输入邮箱、密码、姓名，选择角色「学生」
Step 2: 输入学校全称（自动补全，后端校验白名单）
Step 3: 显示该校已注册教师列表（姓名 + 邮箱），选择一位教师
Step 4: 注册成功（teacher_id 已绑定）→ 自动登录 → 进入 Dashboard
```

- 如果该校没有已注册教师，提示「该校暂无教师，请联系教师先注册」，阻止注册
- 学生注册完成后立即可通过教师的机器人绑定看到模型

## 数据模型变更

### 新增表：`schools`（学校白名单）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer, PK | 自增主键 |
| name | String(200), unique, index | 学校全称（教育部名录） |
| province | String(50) | 省份（辅助筛选） |
| created_at | DateTime | 创建时间 |

数据来源：教育部官方高等学校名录，通过种子脚本一次性导入。

### `users` 表变更

| 字段 | 变更 | 说明 |
|------|------|------|
| role | 去掉默认值，注册时必填 | `student` / `teacher` |
| school_name | 新增, String(200), not null for new users | 学校全称，关联 schools.name |
| onboarding_completed | 新增, Boolean, default=True | 仅教师使用，注册时设为 False，完成机器人选择后设为 True |

- 学生注册时 `onboarding_completed` 直接为 True（无 onboarding 步骤）
- 存量用户（已有的 demo/test 账号）`onboarding_completed` 默认 True，不受影响

## API 变更

### 修改：`POST /api/v1/auth/register`

请求体新增字段：

```json
{
  "email": "user@example.com",
  "password": "StrongPass123",
  "full_name": "张三",
  "role": "teacher",
  "school_name": "北京理工大学",
  "teacher_id": null
}
```

- `role`：必填，`student` 或 `teacher`
- `school_name`：必填，必须存在于 `schools` 表
- `teacher_id`：学生必填，教师不填；后端校验该教师存在且同校

响应新增：注册成功后自动签发 token（与登录响应一致），前端无需再调登录接口。

```json
{
  "user_id": 24,
  "email": "user@example.com",
  "message": "注册成功",
  "access_token": "access_xxx",
  "refresh_token": "refresh_xxx",
  "token_type": "bearer",
  "expires_in": 900,
  "role": "teacher",
  "default_route": "/onboarding/robots",
  "onboarding_completed": false
}
```

- 教师 `default_route` 为 `/onboarding/robots`，`onboarding_completed` 为 false
- 学生 `default_route` 为 `/dashboard`，`onboarding_completed` 为 true

### 新增：`GET /api/v1/schools`（公开，无需认证）

搜索学校名称，用于注册页自动补全。

```
GET /api/v1/schools?q=北京理工&limit=10
```

响应：

```json
{
  "items": [
    { "id": 1, "name": "北京理工大学", "province": "北京市" },
    { "id": 2, "name": "北京理工大学珠海学院", "province": "广东省" }
  ]
}
```

### 新增：`GET /api/v1/schools/{school_name}/teachers`（公开，无需认证）

获取指定学校的教师列表，用于学生注册时选择教师。

```
GET /api/v1/schools/北京理工大学/teachers
```

响应：

```json
{
  "items": [
    { "id": 18, "full_name": "王老师", "email": "wang@rmos.demo" }
  ]
}
```

- 仅返回 `role = teacher` 且 `school_name` 匹配的用户
- 返回字段有限（id、姓名、邮箱），不暴露敏感信息

### 新增：`POST /api/v1/onboarding/robots`（需认证，教师角色）

教师完成机器人选择。

```json
{
  "robot_ids": [1, 3, 5]
}
```

校验：
- 当前用户必须是教师且 `onboarding_completed = false`
- `robot_ids` 长度 1~5
- 每个 robot_id 对应 `status = ready` 的机器人

处理：
- 批量创建 `TeacherRobotBinding`
- 更新 `users.onboarding_completed = true`

响应：

```json
{
  "message": "机器人选择完成",
  "bound_count": 3
}
```

### 修改：`POST /api/v1/auth/login`

响应新增 `onboarding_completed` 字段。前端据此决定是否跳转 onboarding 页。

## 前端变更

### 注册页改造（`RegisterPage.tsx`）

改为分步表单：

```
Step 1: 邮箱 + 密码 + 姓名 + 角色选择（教师/学生 Radio）
Step 2: 学校名称输入（带自动补全，调用 GET /api/v1/schools?q=xxx）
Step 3（仅学生）: 教师选择列表（调用 GET /api/v1/schools/{name}/teachers）
→ 提交注册
```

- 使用 Ant Design Steps + Form 组件
- 学校输入用 AutoComplete，输入时实时搜索
- 教师列表用 Radio.Group，每项显示姓名 + 邮箱

### 新增教师 Onboarding 页（`/onboarding/robots`）

- 展示所有 `status = ready` 的机器人卡片（缩略图 + 名称 + 描述）
- Checkbox 多选，最多 5 个，最少 1 个
- 确认按钮调用 `POST /api/v1/onboarding/robots`
- 完成后跳转 Dashboard

### 路由守卫增强

在 `ProtectedRoute.tsx` 或 `AppLayout` 中：

```typescript
if (user.role === 'teacher' && !user.onboarding_completed) {
  return <Navigate to="/onboarding/robots" replace />
}
```

- 教师未完成 onboarding 时，除 `/onboarding/robots` 外所有路由都重定向
- `authStore` 中的 user 对象需新增 `onboarding_completed` 字段

### 登录流程适配

登录响应中 `onboarding_completed = false` 时：
- `default_route` 设为 `/onboarding/robots`
- 前端按 `default_route` 跳转

## 文件改动清单

### 后端（~6 文件）

| 文件 | 改动 |
|------|------|
| `app/models/school.py` | **新建** School ORM 模型 |
| `app/models/user.py` | 新增 `school_name`、`onboarding_completed` 字段 |
| `app/schemas/auth.py` | RegisterRequest 加字段，RegisterResponse 加 token 字段 |
| `app/api/v1/endpoints/auth.py` | 注册逻辑：校验学校、角色分流、学生绑教师、教师设 onboarding |
| `app/api/v1/endpoints/schools.py` | **新建** 学校搜索 + 教师列表端点 |
| `app/api/v1/endpoints/onboarding.py` | **新建** 教师机器人选择端点 |
| `scripts/seed_schools.py` | **新建** 学校名录导入脚本 |
| Alembic migration | 新增 schools 表 + users 表新增字段 |

### 前端（~4 文件）

| 文件 | 改动 |
|------|------|
| `src/pages/RegisterPage.tsx` | 改为分步表单（角色 → 学校 → 教师选择） |
| `src/pages/OnboardingRobotsPage.tsx` | **新建** 教师机器人选择页 |
| `src/api/auth.ts` | 新增学校搜索、教师列表、onboarding API |
| `src/store/authStore.ts` | user 对象加 `onboarding_completed` |
| `src/components/auth/ProtectedRoute.tsx` | 增加 onboarding 路由守卫 |
| `src/App.tsx` | 新增 `/onboarding/robots` 路由 |

## 边界情况

- **存量用户**：`school_name` 允许 null（存量用户不受影响），`onboarding_completed` 默认 true
- **学校无教师**：学生注册 Step 3 显示「该校暂无教师，请联系教师先注册」，禁止提交
- **教师重复选择**：如果教师已完成 onboarding，访问 `/onboarding/robots` 重定向到 Dashboard
- **机器人不足 1 台**：系统中无 ready 机器人时，onboarding 页提示「暂无可用机器人」
- **密码强度**：保持现有校验规则不变
