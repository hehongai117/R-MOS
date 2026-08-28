# A5 质量与运行证据

- 版本：0.1.0
- 日期：2026-08-28
- 状态：In Review
- 被审基线：`B-ASIS = 29d2a5889e3b320a3e777e3d8c19efbbe31c0294`
- 对应报告：[A5 质量、运行与交付能力审计报告](../2026-08-28-a5-quality-operations-and-delivery-audit-report-v0.1.0.md)

## 1. 方法

AST 遍历 `r-mos-backend/tests/**/test_*.py`，对每个以 `test_` 开头的函数统计：
`assert` 语句数、`pytest.raises` 数、mock 用量（`Mock(`／`patch(`／`AsyncMock(`／`monkeypatch`）、
是否含 skip、以及**是否所有断言都只检查 `status_code`**（定义为「浅断言」）。

**本批未执行任何测试套件**——统计全部为静态结果，不产生新的 PASS/FAIL。

## 2. 后端测试断言质量

| 指标 | 值 |
|---|---:|
| `test_` 函数总数 | 743 |
| `assert` 语句总数 | 2468 |
| 每函数断言数中位数 | 3 |
| 每函数断言数均值 | 3.3 |
| 无 `assert` 语句的函数 | 21 |
| 其中用 `pytest.raises` 表达预期（有效断言） | 18 |
| **真正零断言的函数** | **3** |
| **浅断言函数**（断言全为 `status_code`） | **49** |
| 函数体含 `skip` 字样 | 18 |
| 实际调用跳过机制（`pytest.skip(`／`@pytest.mark.skip`）的出现次数 | 6 |
| 重度 mock（≥5 处）的函数 | 34 |

> pytest 收集到 971 个用例而函数数为 743，差额来自参数化（`@pytest.mark.parametrize`）。

### 2.1 零断言函数（3 个）

| 文件 | 函数 |
|---|---|
| `tests/e2e/test_agent_execute.py` | `test_execute_response_schema` |
| `tests/test_robot_service.py` | `test_file_size_ok` |
| `tests/test_storage.py` | `test_delete_missing_is_noop` |

### 2.2 浅断言函数分布（按文件，前 15）

| 文件 | 浅断言函数数 |
|---|---:|
| `tests/e2e/test_agent_execute.py` | 8 |
| `tests/e2e/test_object_ownership_boundary.py` | 8 |
| `tests/unit/test_teaching_identity_boundary.py` | 6 |
| `tests/unit/test_agent_authz.py` | 5 |
| `tests/unit/test_agent_characterization.py` | 4 |
| `tests/unit/test_robot_asset_boundary.py` | 4 |
| `tests/unit/test_auth_boundary.py` | 3 |
| `tests/unit/test_training_characterization.py` | 3 |
| `tests/unit/test_login_throttle.py` | 2 |
| `tests/unit/test_robot_asset_serving.py` | 2 |
| `tests/regression/test_p0_bugs_2026_07.py` | 1 |
| `tests/test_api_student_robots.py` | 1 |
| `tests/unit/test_agent_workbench_api.py` | 1 |
| `tests/unit/test_teaching_api.py` | 1 |

### 2.3 断言数最少的 10 个函数（排除零断言）

| 文件 | 函数 | 断言 | 行数 |
|---|---|---:|---:|
| `tests/unit/test_audit_query_index_gate.py` | `test_audit_trace_query_explain_uses_trace_index` | 1 | 86 |
| `tests/unit/test_manifest_generator.py` | `test_process_continues_on_parse_error` | 1 | 31 |
| `tests/unit/test_agent_workbench_api.py` | `test_student_command_mode_still_requires_execute_permission` | 1 | 30 |
| `tests/regression/test_p0_bugs_2026_07.py` | `test_p0_2_evaluation_report_invalid_task_returns_4xx_not_500` | 1 | 29 |
| `tests/unit/test_agent_authz.py` | `test_agent_coach_recommend_with_execute_permission` | 1 | 29 |
| `tests/unit/test_deny_audit_entrypoint_gate.py` | `test_deny_audit_entrypoint_is_singleton` | 1 | 29 |
| `tests/test_sop_three_phase.py` | `test_knee_bearing_sop_part_and_screw_ids_exist_in_assembly_manifest` | 1 | 28 |
| `tests/unit/test_agent_authz.py` | `test_agent_evidence_collect_write_endpoint` | 1 | 28 |
| `tests/unit/test_project_sync_for_robot_model.py` | `test_sync_does_not_duplicate_same_filename` | 1 | 28 |
| `tests/load/test_locustfile_smoke.py` | `test_rmos_user_declares_expected_tasks` | 1 | 27 |

## 3. 授权与对象归属测试覆盖

> **本节为异源复核修正后的版本。** 主审前两稿只检索 `== 403`，因此完整漏掉了本库
> **以 404 表达归属拒绝**的整套边界测试。检索安全测试前必须先确认该库的拒绝码约定。

### 3.1 拒绝类断言总量

| 断言 | 数量 | 文件数 |
|---|---:|---:|
| `== 403`（权限拒绝） | 28 | 16 |
| **`== 404`（归属拒绝，不泄露存在性）** | **72** | **15** |
| `== 401`（未认证） | 10 | — |

### 3.2 专门的边界测试文件

**`tests/e2e/test_object_ownership_boundary.py`**（13,930 字节）——对象归属边界，用例包括：

| 用例 | 覆盖 |
|---|---|
| `test_cross_student_read_returns_404`（参数化多条路径模板） | 学生 B 用**自己的合法令牌**读学生 A 的资料／训练／任务／报告／事件 → 404 |
| `test_cross_school_teacher_read_returns_404` | **跨校教师**读学生数据 → 404（租户隔离） |
| `test_cross_user_task_read_returns_404`（参数化 suffix） | 跨用户读任务及其子资源 → 404 |
| `test_legacy_task_without_owner_is_denied` | 无归属的历史任务一律拒绝 |
| `test_cross_user_session_detail_returns_404` | 跨用户读训练会话详情 → 404 |
| `test_cross_user_feedback_read_is_denied_before_lookup` | 反馈在查库**之前**就拒绝（避免时序侧信道） |
| `test_feedback_role_query_param_cannot_grant_teacher_view` | **查询参数提权防护**：`?role=teacher` 不得提升视图 |
| `test_student_can_read_own_data` | 正向边界：本人读自己必须成功 |
| `test_same_school_teacher_can_read_student` | 正向边界：同校教师可读 |

**`tests/unit/test_teaching_identity_boundary.py`**——标题「AUTH-104 / AUTH-101：教学域身份与对象归属边界」，
夹具建「两名同校学生 + 两名教师；班级归教师 A，尝试归学生 A」，覆盖伪造 `X-RMOS-Role`、
省略角色头、伪造 `X-User-ID` 均不得放宽范围，以及本人读自己的正向边界。

其余：`tests/unit/test_authz_guard_api.py`（admin 路由三态）、`tests/e2e/test_e2e_cross_role_access.py`、
`tests/unit/test_agent_authz.py`、`tests/unit/test_auth_boundary.py`、
`tests/unit/test_redteam_batch_j003_api.py`（红队批次）。

### 3.3 仍然存在的缺口：写路径

上述用例集中在**读路径**（跨用户读 → 404）。A4 点名的高危**写**端点中，
`DELETE /sops/{sop_id}`、`POST /maintenance/drafts/{draft_id}/approve`、`POST /adapter/inject-fault`
所在的测试文件既无 `403` 也无归属边界用例。

> **口径声明：** 「所在文件无断言」只能说明该文件层面没有覆盖，
> 端点级的精确结论需逐条读测试体，本批未做 → UNKNOWN。

## 4. CI workflow 逐条解析

| Workflow | 数据库 | 迁移 | 关键步骤 |
|---|---|---|---|
| `backend-ci` | `postgres:16` service | `alembic upgrade head` + **`alembic check`** | PG 门禁测试（审计索引、技能注册迁移）单独跑；**e2e 在独立 `rmos_e2e` 库上跑**（注释：消除 SQLite 方言盲区）；14 个核心服务覆盖率门禁；**主套件裸跑**（不设 `DATABASE_URL`） |
| `integration-ci` | `postgres:16` service | `alembic upgrade head` | 真实启动 `uvicorn`，轮询 `/api/v1/health`（最多 45 次），跑 `tests/e2e/`，**无论成败上传后端日志 artifact** |
| `e2e-browser-ci` | `postgres:16`（独立库 `rmos_e2e_browser`） | `alembic upgrade head` | `python scripts/e2e_preflight.py` + Playwright |
| `frontend-ci` | — | — | `npx tsc --noEmit` → `npx eslint src/ --ext .ts,.tsx --max-warnings 0` → `npm test` → `npx vitest run --coverage` → `npm run build` |

**`backend-ci` 内的原文注释**（解释主套件为何裸跑）：

```
# Postgres 专属门禁单独一步跑：这些测试直读 DATABASE_URL，需要已迁移的真实 PG。
# 主套件保持裸跑（无 DATABASE_URL）——全量测试在 PG env 下存在 asyncpg 跨事件循环
# 问题（Event loop is closed，Linux 上必现），全量迁 PG 属 P2-1 测试体系升级范围。
```

**这是一个被记录在案的已知取舍，不是疏漏。**

## 5. 测试基座

```python
# tests/conftest.py
"sqlite+aiosqlite:///:memory:"        # 引擎
await conn.run_sync(Base.metadata.create_all)   # 建表——不执行 alembic 迁移
```

即：主套件的 971 个用例既没有跑在 PostgreSQL 上，也没有经过 38 个迁移。
迁移正确性由 CI 的 `alembic upgrade head` + `alembic check` 单独保证。

## 6. 局限

1. 断言统计是静态的，**不能评价断言是否切题**——`assert response.status_code == 200` 与
   对返回内容的结构性断言在本统计中都计 1 条。
2. **未执行任何测试**，本批不产生新的 PASS/FAIL。
3. **CI 实际运行历史未核实**（需 GitHub Actions 记录），配置完备 ≠ 持续在跑，记为 UNKNOWN。
4. 授权测试的端点级覆盖度只做到文件级交叉，未逐条读测试体。
