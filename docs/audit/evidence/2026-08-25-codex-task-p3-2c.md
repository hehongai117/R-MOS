# 任务：补齐对象归属校验（R-MOS P3-2c，AUTH-101 的归属半边）

工作区 `/Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime`，
分支 `audit/phase3-auth-control-realtime`，当前 HEAD `f4c4a752`。后端在 `r-mos-backend`。

Python 只用 `/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python`，
**工作目录必须是本工作区的 `r-mos-backend`**（不是主工作区）。

## 背景（事实，已实测核实）

P3-1 的默认拒绝网关只解决了「匿名」。**认证通过之后，大量接口不比较调用者与目标对象的归属**：
任何已登录学生用自己的合法令牌，就能读别的学生的技能画像、薄弱步骤、训练会话、任务与报告。

实测普查：`app/api/v1/endpoints/` 下 180 条路由中 **130 条**在函数签名层面
拿不到调用者身份（连 `actor` 参数都没有）。`rg 'actor\.school_name' app/` → **0**，
即 ADR-AUTHN D4 的跨校维度只落了载体、没有任何消费方。

## 已经写好的失败测试（**不要修改它的任何断言**）

`r-mos-backend/tests/e2e/test_object_ownership_boundary.py`

当前 **12 failed / 3 passed**。你的任务是让它全绿，**不准改断言、不准删用例、
不准加豁免名单、不准把 assert 改成 warning**。若你认为某条断言本身写错了，
停下来在最终回复里说明，不要自行修改。

跑它：

```bash
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime/r-mos-backend
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python -m dotenv \
  -f /Users/xuhehong/Desktop/r-mos/r-mos-backend/.env run -- \
  /Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python -m pytest \
  tests/e2e/test_object_ownership_boundary.py -o addopts='' -q
```

## 本批范围：**只改这 8 条路由**，不要扩大

| 文件 | 函数 | 归属依据 |
|---|---|---|
| `app/api/v1/endpoints/training.py` | `get_student_skill_profile` | 路径参数 `user_id` |
| `training.py` | `get_student_weak_steps` | 路径参数 `user_id` |
| `training.py` | `get_user_sessions` | 路径参数 `user_id` |
| `training.py` | `get_session_detail` | `training_sessions.user_id` |
| `training.py` | `get_training_feedback` | 该 `session_id` 对应会话的 `user_id` |
| `app/api/v1/endpoints/tasks.py` | `get_task` | `tasks.user_id` |
| `tasks.py` | `get_task_report` | `tasks.user_id` |
| `tasks.py` | `get_task_events` | `tasks.user_id` |

**其余路由一律不动**（`assessments.py`、`agent_*`、`maintenance.py`、`sops.py`、
`adapter.py` 等留给后续批次；`adapter.py` 属 P3-4）。

## 归属规则（必须完全按这个来）

放行条件，满足任一即可：

1. `actor.user_id == 目标用户 id`（本人）
2. `actor` 是**管理员**
3. `actor` 是**教师**，且**与目标用户同校**

否则一律拒绝。

### 两套角色的坑（**这是本批最容易做错的地方**）

系统里有两套角色，`app/services/authz_guard.py` 的 `ActorContext` docstring 写得很清楚：

- `actor.roles` / `actor.permissions`：RBAC 表（`roles`/`user_roles`/`permissions`）。
  **注册流程不写 `user_roles`，只有 seed 脚本会写**，所以正常注册的用户这两个集合**恒为空**。
- `actor.account_role`：`users.role` 列（`student`/`teacher`/`admin`），注册时写入。

**特权判断必须走 `account_role`。** 只用 `actor.roles` 会把所有正常注册的教师
判成学生，测试里 `test_same_school_teacher_can_read_student` 会红。
参照本仓已有的正确写法 `app/api/v1/endpoints/robots.py` 的 `_get_visible_robot_or_404`：
`if "admin" in actor.roles or actor.account_role == "admin"`。

### 跨校比较

用 `actor.school_name`（P3-2b 已加进 `ActorContext`，`get_current_actor` 里取值零额外查询）
与目标用户的 `users.school_name` 比较。**这是全仓第一个消费方**。
两边都为空（`None`）时**不得**当作同校放行——按拒绝处理。

### 无主对象

`tasks.user_id` 当前 `nullable=True` 且无外键（收紧留给 P3-4 的合并迁移）。
在收紧之前，`user_id IS NULL` 的任务对**非管理员**一律拒绝。不要留豁免开关。

## 拒绝语义（G1，不得自创）

**不要写 `raise HTTPException(404)`。** 必须走本仓已有的
`app/services/access_control.py:110` 的 `raise_read_access_denied`：

```python
await raise_read_access_denied(
    db, request,
    action="...",            # 如 "read_skill_profile"
    resource_type="...",     # 如 "user" / "task" / "training_session"
    resource_id=<真实目标编号>,   # 必须是真实编号，不能是 None、不能脱敏
    reason="...",            # 如 "cross_user_access"
)
```

它会先写一条 `decision="deny"` 的审计（`actor_user_id` 自动取
`request.state.actor`，即令牌主体），再抛 `ReadAccessDeniedError` → 对外 **404**。
异常到 404 的映射 `main.py` 里已有，不用改。

端点需要 `request: Request` 参数才能调它。

## 建议的落地方式（避免 8 处复制粘贴）

新建 `app/services/ownership.py`，放两个小函数，8 个端点都调它：

```python
async def ensure_user_scope(db, request, actor, target_user_id, *, action, resource_type) -> None
    """本人 / 管理员 / 同校教师 放行，否则 raise_read_access_denied。"""

async def ensure_task_scope(db, request, actor, task, *, action) -> None
    """按 tasks.user_id 走同一套规则；user_id 为 NULL 时非管理员拒绝。"""
```

不要建类、不要做注册表、不要加配置项——两个函数就够。

## 验证（必须全部实际跑过，把真实输出贴进最终回复）

```bash
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime/r-mos-backend
# 1. 本批门禁
<venv python> -m dotenv -f <主工作区 .env> run -- <venv python> -m pytest \
  tests/e2e/test_object_ownership_boundary.py -o addopts='' -q
# 2. 后端全量（基线 956 passed，不允许留任何新的红）
<venv python> -m dotenv -f <主工作区 .env> run -- <venv python> -m pytest
```

**全量跑完后必须检查 `r-mos-backend/data/knowledge_store.json` 是否被测试改写。**
它会被改写（生成编号与时间）。用 `git checkout -- r-mos-backend/data/knowledge_store.json`
恢复，并在回复里说明你做了这一步。

### 关于全量里可能变红的既有测试

有些既有用例可能假设"任何人都能读任意用户的画像/任务"。**这类用例固化的是错误语义，
应当改写为携带正确身份或断言 404**——但你必须在最终回复里**逐条列出**你改了哪些、
为什么、改前改后断言分别是什么。**不准为了让全量变绿而放宽本批新门禁。**

## 硬约束

- **不要碰前端。** 这一批是纯后端。
- 不要改 `DATABASE_URL`、CORS、`.env`、`vite.config.ts`、任何代理配置。
- **不要写 Alembic 迁移。** `tasks.user_id` 的收紧按 ADR-ROBOT 的迁移策略与
  `robot_model_id` 合并为同一个迁移，属 P3-4，本批不做。
- **不要 git commit、不要 push、不要建分支。** 改完把工作区留在未提交状态。
- 不要改任何文档（`AGENTS.md`、`TEST_REPORT.md`、`DEVELOPMENT_LOG.md`、
  交接文档、修复矩阵）。**裁决与报告回填由我来写，不外包。**
- 不要顺手修 `robots.py:150` 的 `get_robot` 403/404 口径不一致（既有问题，单独立项）。
- 不要合并两套角色系统（独立的权限决策，须用户拍板）。
- 不要装依赖、不要联网、不要启动服务、不要操作真机。

## 最终回复里要写清楚

1. `git status --short` 的实际输出；
2. 两条验证命令的真实结果（通过/失败数，不要写"应该通过"）；
3. 你改写的既有测试逐条清单（改前断言 → 改后断言 → 理由）；
4. `knowledge_store.json` 的处理情况；
5. 任何你认为断言写错、但按要求没有自行修改的地方。
