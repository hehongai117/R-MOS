# ADR-2026-08-21：默认拒绝认证与对象归属

- 状态：Proposed（待用户确认公开路由白名单后转 Accepted）
- 覆盖发现：`AUTH-101`、`AUTH-102`、`AUTH-103`、`AUTH-104`、`AUTH-105`，以及 `RT-101` 的握手认证面
- 上位规则：`AGENTS.md`、`docs/testing/ACCEPTANCE_CHARTER.md` 的 G1
- 落地阶段：Phase 3（本 ADR 不改代码）

## 背景

当前认证是**逐路由自愿加入**，没有任何统一入口：

- `app/api/v1/__init__.py:39-70` 的 28 次 `include_router` 只带 `tags=`，**没有一处 router 级 `dependencies=`**；`main.py:336` 的 `app.include_router(api_router, prefix="/api/v1")` 同样没有。因此是否认证完全取决于每个函数签名里有没有写 `Depends(get_current_actor)`。
- 全仓 `app/api/v1/endpoints/` 下共 182 个路由装饰器，分布在 37 个模块。Phase 1 的动态探针得出 `unprotected_routes=109`——这是**待分类路由数量**，其中包含健康检查、登录等本应公开的入口，不是 109 个漏洞。
- 代表性缺口已逐条确认：`app/api/v1/endpoints/tasks.py` 的 9 个路由中只有 `list_tasks`（113-140 行）声明了 `actor: ActorContext = Depends(get_current_actor)`，创建、开始、执行步骤、暂停、恢复、详情、报告、事件全部只有 `db`。
- `app/api/v1/endpoints/teaching_roster.py` 用可伪造的 `X-RMOS-Role` / `X-User-ID` 头做权限分支，共 10 处。其判断形如 `if x_rmos_role and x_rmos_role.strip().lower() not in {"teacher","admin"}`（159、282 行）——**完全省略该头即可绕过整条判断**；107-109 行的读范围限制也只在 `role == "student"` 时生效。
- `app/services/access_control.py:20-24` 的 `_extract_actor_user_id` 在调用方未显式传 operator 时从 `X-User-ID` 头取审计操作者。
- `tests/unit/test_auth_boundary.py` 的 `_collect_protected_endpoints()` 在遍历路由时执行 `if not _has_auth_dependency(route.dependant): continue`，**主动跳过没有认证依赖的路由**；`test_protected_endpoints_require_token` 只对进入该列表的路由断言 401。漏加认证的接口因此永远不会进入测试矩阵。
- `app/api/v1/endpoints/auth.py:197` 的登录对错误密码只返回统一 401；`app/core/config.py`、`docker-compose.yml`、`r-mos-frontend/nginx.conf` 均无任何限流配置。

两项使改造成本远低于预估的既有事实：

1. **前端已经在发令牌。** `r-mos-frontend/src/api/client.ts:60-68` 的请求拦截器给每个请求挂 `Authorization: Bearer ${token}`，`:76-105` 已实现 401 刷新重试；`src/store/authStore.ts:91-96,155,173` 负责令牌存取与刷新。前端**没有任何一处**发送 `X-RMOS-Role` 或 `X-User-ID`。
2. **拒绝语义与拒绝审计已经写好且合规。** `app/services/access_control.py` 已提供 `raise_read_access_denied`（404 + deny 审计）、`raise_write_access_denied`（403 + deny 审计）、`log_deny_event` / `log_allow_event`，且都以真实 `resource_id` 落审计。`app/services/authz_guard.py:105-159` 的 `require_permission(permission_key, required_role=...)` 已是可复用的路由级守卫，拒绝时同样写审计。

因此本次不是"建设认证体系"，而是**把已有的正确组件接成默认路径，并切断可伪造的旁路**。

## 决策

### D1：默认拒绝 + 显式公开路由白名单

新增 `app/core/public_routes.py`，用 `(method, route_template_path)` 的显式集合登记公开路由。新增网关依赖 `enforce_authenticated`，在 `main.py:336` 一处挂到 `api_router` 上：

```python
app.include_router(api_router, prefix="/api/v1",
                   dependencies=[Depends(enforce_authenticated)])
```

`enforce_authenticated` 命中白名单则放行，否则调用 `get_current_actor`。不在白名单、又没带有效令牌的请求一律 401，**与该路由函数是否声明认证依赖无关**。

为避免网关与端点重复查库，在 `app/services/authz_guard.py` 的 `get_current_actor` 增加 `request: Request` 参数并做请求级缓存（首次解析后写 `request.state.actor`，后续直接返回）。这是约 4 行改动，端点侧继续写 `Depends(get_current_actor)` 不变。

**白名单初稿（须由用户逐条确认后才生效）：**

| 方法 | 路径 | 理由 |
|---|---|---|
| GET | `/api/v1/health` | 存活探针，不返回业务数据 |
| POST | `/api/v1/auth/register` | 注册入口 |
| POST | `/api/v1/auth/login` | 登录入口 |
| POST | `/api/v1/auth/refresh` | 刷新入口，自带刷新令牌校验 |
| GET | `/api/v1/schools` | 注册页学校选择；须先确认返回字段不含敏感信息 |
| GET | `/api/v1/robots/{robot_id}/assets/{file_path:path}` | **仅**在 D3 拆分出"已发布公开资产"专用路径后适用；当前形态不得列入 |

`POST /api/v1/auth/logout`（`auth.py:346`）不列入白名单——注销必须能定位到具体令牌主体。`/`、`/docs`、`/openapi.json` 在 `api_router` 之外，由 `main.py` 单独裁定；生产环境应关闭 `/docs`（见 ADR-runtime）。

其余 176 个路由默认进入必须认证集合。

### D2：身份只来自服务端令牌，客户端头降级为非安全元数据

`X-RMOS-Role` 与 `X-User-ID` 不再参与任何授权分支或审计主体：

- `teaching_roster.py` 的 10 处头读取全部替换为 `actor: ActorContext = Depends(get_current_actor)`，角色取 `actor.roles`，主体取 `actor.user_id`。
- `access_control.py:20-24` 的 `_extract_actor_user_id` 删除头兜底，改为从 `request.state.actor` 取；取不到时写入 `None` 并在 `reason` 标注 `unauthenticated`，**不得**回落到客户端头。
- 角色缺失不再等于"不限制"。`role not in {...}` 一类判断改为白名单式：只有显式命中允许角色才放行。

### D3：对象归属校验统一走既有拒绝语义

所有业务对象读写在服务端用 `ActorContext` 校验归属，拒绝时一律调用 `raise_read_access_denied`（读，404）或 `raise_write_access_denied`（写，403），沿用其真实 `resource_id` 审计。

归属维度按对象逐个明确，最小集合为：

| 对象 | 归属依据 | 当前可用字段 |
|---|---|---|
| Task | 执行者 | `tasks.user_id`（`app/models/task.py:67`，当前 `nullable=True` 且无外键，Phase 3 收紧为非空 + 外键） |
| TaskExecution | 学生 | `task_executions.student_id`（非空、有索引，可直接用） |
| Assignment / Class / Attempt | 班级教师、选课学生 | 现有 roster 关系 |
| RobotModel 及其资产 | 教师所有权与可见性 | `robot_models.owner_teacher_id`、`visibility`、`status`（`app/models/robot_model.py:27-40`） |
| EvidenceBundle | 见 ADR-evidence | 当前**无**归属字段，由该 ADR 补 |

机器人资产按 AUTH-103 拆成两条路径：私有清单与源文件（`robots.py:516`、`543`）要求认证 + 所有权；公开发布资产另开只读路径，只接受不可猜测的发布标识，并校验 `status=READY` 与 `visibility=public`。`robots.py:516` 的资产清单当前会返回存储路径，改造后不得对匿名调用者暴露。

### D4：school 维度纳入校验，但不做数据分库

**当前事实：全仓 ORM 模型中只有 `app/models/user.py:29` 带 `school_name`（String，可空），没有任何 `school_id` 外键，其他业务表均无租户字段。** 因此本阶段的跨校拒绝只能通过"操作者 user → school_name → 目标对象所属 user → school_name"的比较实现。

决策：Phase 3 在 `ActorContext` 增加 `school_name: str | None` 字段（`authz_guard.py:27-34` 的 dataclass 加一个字段，`get_current_actor` 已在查 User，取值零额外查询），跨校比较用它。**不**在本阶段给业务表加租户列、**不**做数据分库，正式租户隔离仍归路线图 S-2。

### D5：登录失败限制

`auth.py:197` 的登录增加按 `(账号, 来源 IP)` 组合计数：15 分钟窗口内失败 5 次，临时锁定 15 分钟，返回明确的受限状态并写审计。**不做永久锁定**（会被用于拒绝服务）。锁定期内正确密码同样拒绝，窗口结束自动恢复；成功登录清零计数。

计数存储使用进程内 TTL 结构（与 ADR-runtime 的单进程单实例决策一致），**不引入 Redis**。

### D6：认证边界测试反转

`tests/unit/test_auth_boundary.py` 的 `_collect_protected_endpoints()` 反转为 `_collect_must_auth_endpoints()`：遍历 `/api/v1` 全部 `APIRoute`，凡不在白名单者一律进入矩阵，并断言 (a) 依赖树含 `get_current_actor` 或被网关覆盖，(b) 无令牌返回 401。现有 `_has_auth_dependency`（29-32 行）与 `_sample_path`（34-56 行）原样复用。

门禁自检：临时把一个非公开路由移出白名单管辖时该测试必须失败。

## 备选

1. **在每个 `include_router` 上挂 `dependencies=[Depends(get_current_actor)]`。** 改动同样小，但 FastAPI 的依赖是叠加的、无法在子路由取消，模块内若有一条真正公开的路由（如已发布资产）就无法豁免，只能把该路由挪出模块。放弃。
2. **用 HTTP 中间件做认证。** 中间件拿不到 FastAPI 的 `get_db` 依赖，需要自建会话与错误映射，且绕过既有异常处理器。放弃。
3. **保留客户端身份头作为过渡兼容开关。** 兼容开关本身就是绕过点，且会让 AUTH-GATE 无法给出"允许 0 次"的结论。明确拒绝。
4. **登录限流放到 Nginx。** 生产可作为纵深防御补充，但当前 `r-mos-frontend/nginx.conf` 只代理前端，且限流结果无法写入应用审计。作为 ADR-runtime 的可选加固项，不替代 D5。

## 影响

**破坏面（已实测，比预估小一个数量级）：**

| 对象 | 位置 | 影响 |
|---|---|---|
| 前端 | 无 | 已发送 Bearer 令牌且已实现 401 刷新；不发身份头。预期无需改造，但须在 Phase 3 用浏览器流程复验 |
| 后端测试 | `tests/unit/test_teaching_characterization.py`（29 处身份头）、`test_attempt_replay_api.py`（8）、`test_evidence_cards_api.py`（6）、`test_teaching_api.py`（4）、`test_api_teaching.py`（3）、`tests/e2e/test_e2e_cross_role_access.py`（1） | 共 51 处，需改为携带真实令牌；其中特征化测试固化的是"头即身份"的旧语义，属于必须重写而非修补 |
| 脚本 | `r-mos-backend/scripts/run_gate2_smoke.sh:126,134` | 2 处，改为先登录取令牌 |
| 文档用例 | `docs/testing/TEST_PLAN.md` 中大量无令牌 `curl` | 随 Phase 3 同步更新 |

`docs-archive/DEVELOPMENT_LOG.md:140` 记录该头机制当初就是"最小门控，待 Gate-1 B-001/B-002 落地后应切换到真实鉴权上下文"——本 ADR 即为该切换。

**性能影响：** 每请求增加一次令牌解析（3 个小查询），因请求级缓存不重复；公开路由不受影响。

**不影响：** 数据结构（除 D4 的 `ActorContext` 内存字段与 D3 提到的 `tasks.user_id` 收紧）、机器人控制语义、证据模型。

## 迁移策略

1. Phase 3 第 1 批只落 D1 + D6：网关、白名单文件、反转后的边界测试。此时业务逻辑不动，效果是"未登录一律 401"。
2. 第 2 批落 D2 + D4：`teaching_roster.py` 与 `access_control.py` 换身份源，`ActorContext` 加 `school_name`。同批重写 51 处测试。
3. 第 3 批落 D3 的资产边界与 D5 的登录限流。
4. `tasks.user_id` 从 `nullable=True` 收紧为非空 + 外键需要 Alembic 迁移与存量回填，与 ADR-robot-binding 的 `robot_id` 迁移**合并为同一个迁移**，避免两次改 `tasks` 表。

数据迁移只涉及 `tasks.user_id`；存量 `user_id IS NULL` 的行处理方式与 `robot_id` 回填一致（见 ADR-robot-binding 迁移策略）。

## 回滚策略

- D1/D2/D6 为纯代码改动，`git revert` 即可；白名单文件删除后系统回到"逐路由自愿"的原状态。
- D4 的 `ActorContext` 字段为内存结构，无迁移。
- D5 的计数为进程内结构，重启即清空，无持久化残留。
- 唯一带迁移的是 `tasks.user_id`，回滚方式随 ADR-robot-binding 的同一迁移 `alembic downgrade -1`。

## 待确认事项（阻塞本 ADR 转 Accepted）

1. **公开路由白名单逐条确认**（D1 表格）。这是安全边界，必须由用户签字，不能由实施方单方面决定。
2. `GET /api/v1/schools` 是否真的需要匿名可读；若注册流程不需要，应移出白名单。
3. `tasks.user_id` 存量为 NULL 的行是否允许豁免归属校验，还是一律回填到某个系统账号。豁免会留下永久后门，建议回填。
