# A1 双源枚举差集证据

- 版本：0.1.0
- 日期：2026-08-26
- 状态：Ready for Board Review（随 A1 主报告一并提交）
- 被审基线：`B-ASIS = 29d2a5889e3b320a3e777e3d8c19efbbe31c0294`
- 被审工作区：`/Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime`
- 主审：Claude｜异源复核：Codex（董事会方向指令 0.2.0 §5.8）
- 对应门槛：M-AUD-01（双源分母差集 0，分母内覆盖率 100%）

## 1. 工作区与基线的一致性

A1 的所有静态枚举都在工作区当前文件上执行，因此必须先证明工作区的应用代码等同基线：

```bash
git diff --name-only 29d2a5889e3b320a3e777e3d8c19efbbe31c0294 HEAD
# 输出仅 6 个文档文件：
#   docs-archive/DEVELOPMENT_LOG.md
#   docs/audit/2026-08-26-a0-baseline-and-source-governance-audit-report-v0.1.1.md
#   docs/audit/README.md
#   docs/audit/evidence/2026-08-26-a0-phase3-intervention-set-v0.1.0.md
#   docs/audit/evidence/2026-08-26-a0-whole-project-source-denominator-v0.1.0.md
#   docs/audit/evidence/2026-08-26-a0-whole-project-source-denominator.py
git status --porcelain   # 采集开始时为空
```

结论：`B-ASIS → HEAD` 之间**没有任何应用、测试、配置或数据变化**，工作区静态枚举结果可代表基线。

## 2. 口径与排除项（改口径必须同时改报告）

| 项 | 规定 |
|---|---|
| 静态源范围 | 仅 Git 跟踪的源码文件 |
| 固定排除 | `venv/`、`__pycache__/`（含全部 `.pyc`）、`node_modules/`、构建产物、`.git/` |
| 后端路由静态解析 | **AST**，不是正则；正则会把多行装饰器拆错并把 `.pyc` 计入 |
| 后端路由静态范围 | `app/**/*.py` **加上后端根目录 `*.py`**——真实启动入口 `main.py` 在根上，只扫 `app/` 会漏掉它注册的根路由 |
| 前端页面统计 | `src/**/pages/**/*.tsx`，**排除 `__tests__/`**；`src/pages` 下 37 个 `.tsx` 中有 16 个是测试文件 |
| 运行时源 | `import main` 后的真实注册表、SQLAlchemy `Base.metadata`、PostgreSQL `pg_tables`、alembic 版本图、`vite build --sourcemap` 的模块闭包、`pytest --collect-only`、`vitest list` |
| 秘密处理 | `.env` 只记字段名，不记值 |

> **A0 遗留口径缺陷（本批发现并修正）：** A0 的运行指纹 `FP-CFG-01` 记录了 10 个 `.env` 字段名，但**被审工作区没有 `.env`**（只有 `.env.example`），该指纹实际取自主工作区。Git worktree 不共享未跟踪文件，因此指纹对象与被审对象不是同一个。A1 的运行时探测统一采用「注入主工作区 `.env` 环境变量 + 在被审工作区执行」的方式，并在本文件显式声明；A0 的 `FP-CFG-01` 口径需在其 0.1.2 修订中改写或降为 UNKNOWN。

## 3. 差集总表

| Scope_ID | 对象 | 静态源 | 运行时/构建源 | 仅静态 | 仅运行时 | 归并结果 | 剩余 UNKNOWN |
|---|---|---:|---:|---:|---:|---|---:|
| S-01 | 后端 HTTP 路由 | AST 装饰器 **181** | `app.routes` APIRoute **181** | 0 | 0 | 181，按 (模块, 函数, 方法) 逐条对应 | 0 |
| S-02 | WebSocket 端点 | AST `@router.websocket` **2** | `APIWebSocketRoute` **2** | 0 | 0 | 2，均在 `endpoints/websocket.py` | 0 |
| S-03 | 框架自带路由 | 源码 0 | 运行时 **4** | 0 | 4 | `/openapi.json`、`/docs`、`/docs/oauth2-redirect`、`/redoc`，FastAPI 自带，不计入功能分母 | 0 |
| S-04 | 数据表 | AST `__tablename__` **65** | ORM metadata **65**／数据库 public **66** | 0 | 1 | 65 张业务表；数据库多出的 `alembic_version` 是 Alembic 自带版本表 | 0 |
| S-05 | 迁移 | 版本文件 **38** | alembic 版本图 **38** 节点 | 0 | 0 | 38，单一 head `20260817_sop_three_phase`，base `001`，与数据库 `alembic_version` 一致（三源） | 0 |
| S-06 | 前端页面组件 | `pages/**` 非测试 `.tsx` **27** | 构建图（sourcemap） | 1 | 0 | 27，其中 `ApprovalQueuePage.tsx` 不在构建图内且零引用 | 0 |
| S-07 | 前端路由声明 | `App.tsx` `path="…"` **26** | 构建产物按页分包 chunk | 0 | 0 | 26 条路由（含 `/` 与 `*` 兜底） | 0 |
| S-08 | 前端源码模块 | 非测试 `.ts/.tsx` **195** | sourcemap 模块闭包 **167** | 28 | 0 | 28 项已逐个归因（见 §5） | 0 |
| S-09 | 后端 Python 模块 | 磁盘 **231** | 启动后 `sys.modules` **206** | 25 | 0 | 25 项已逐个归因（22 项延迟导入或脚本消费，3 项零引用） | 0 |
| S-10 | 后端测试 | `tests/` 下 `test_*.py` **123** | `pytest --collect-only` **123 文件 / 971 用例** | 0 | 0 | 123；另有 `r-mos-backend/schemas/tests/` 7 个 `test_*.py` 不在 `testpaths` 内，从未被收集 | 0 |
| S-11 | 前端测试 | `.test.ts(x)` **78** | `vitest list` **70 文件 / 518 用例** | 8 | 0 | 70；差的 8 个是 `src/adjudication/__tests__/` 下无 `describe/it` 的伪测试 | 0 |
| S-12 | 角色 | 代码内无集中枚举（散落字符串 + 前端权限表 3 种） | 数据库 `roles` 表 **4** 行 | 0 | 1 | 4 种角色 `admin/teacher/student/auditor`；`auditor` 只出现在 3 个后端端点，前端无入口 | 0 |

**M-AUD-01 结论：** 12 个 Scope 全部取得两条异源枚举路径，全部差集已解释并归并，未分类项 0，剩余 UNKNOWN 0。

## 4. 复现命令

### 4.1 后端路由 / 数据表 / 迁移 / 模块可达性（一次跑完）

```bash
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime/r-mos-backend
set -a; . /Users/xuhehong/Desktop/r-mos/r-mos-backend/.env; set +a
unset CORS_ORIGINS     # 该字段在环境变量形态下不是 JSON，pydantic-settings 会拒绝解析
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python \
    ../docs/audit/evidence/2026-08-26-a1-dual-source-inventory.py /tmp/a1_inventory.json
```

实际输出（退出码 0 = 所有差集已解释）：

```
路由 静态181 / 运行时181 差集0 | 表 静态65 / metadata65 / 数据库66 差集['alembic_version'] |
迁移 文件38 / 图38 heads=['20260817_sop_three_phase'] 库=['20260817_sop_three_phase'] |
模块 磁盘231 / 启动已导入206 | 数据 非空37 / 空28（估算失真 35 张）
```

### 4.2 前端构建图

```bash
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime/r-mos-frontend
npx vite build --sourcemap --outDir <工作区外的临时目录> --emptyOutDir
# 再从 dist/assets/*.map 的 sources 数组取出 src/ 下的模块集合，即入口可达闭包
```

产物写到工作区之外，被审工作区保持零改动。构建退出码 0，用时 12.4s。

### 4.3 测试枚举

```bash
# 后端：123 文件 / 971 用例
set -a; . /Users/xuhehong/Desktop/r-mos/r-mos-backend/.env; set +a; unset CORS_ORIGINS
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python -m pytest --collect-only -q

# 前端：70 文件 / 518 用例
cd r-mos-frontend && npx vitest list
```

两条命令都只做收集与列举，**没有执行测试**，因此本批不产生任何测试通过/失败裁决。

### 4.4 数据库只读事实

```sql
select tablename from pg_tables where schemaname='public';   -- 66
select version_num from alembic_version;                     -- 20260817_sop_three_phase
select name from roles order by id;                          -- admin, teacher, student, auditor
-- 行数必须逐表精确计数，不能用 pg_stat_user_tables.n_live_tup
select count(*) from public."<每张业务表>";
```

**65 张业务表中 37 张非空、28 张为空。** 数据量最大的：`robot_assets` 33,367、`schools` 2,869、
`access_tokens` 389、`refresh_tokens` 389、`session_step_records` 107、`robot_project_files` 91、`sops` 54、`tasks` 30。

> **口径纠正（MISMATCH-02）：** 本文件初版用 `pg_stat_user_tables.n_live_tup` 判断空表，得出「仅 7 张非空、58 张为空」。
> 该字段是**统计估算值**，在未执行 ANALYZE 的库上会停留在陈旧快照——35 张表的估算与精确值不符，
> 其中 `robot_assets`（实际 33,367 行）、`schools`（2,869 行）、`users`（13 行）的估算全部为 0。
> 异源复核逐表 `count(*)` 后纠正为 37 非空 / 28 空，清点脚本已改为精确计数。

## 5. S-08 的 28 项归因（前端不在构建图的模块）

引用关系用 **TypeScript 模块解析**判定：解析 `@/` 别名与相对路径，按 `.ts`/`.tsx`/`index.ts` 顺序补全，
并把 `vi.mock()` 与动态 `import()` 计为引用。

> **本表已按异源复核结论修正（MISMATCH-01）：** 初版用文件 basename 做相对路径匹配，
> 把 `export … from './data/criticalParts'` 这类**带子目录的再导出**漏判为零引用，
> 又因 barrel 目录名模糊匹配把 `Viewer3D/index.ts` 误判为「仅测试消费」。
> 改用模块解析后，零引用从 8 项收敛为 **6 项**。

| 归因 | 数量 | 说明 |
|---|---:|---|
| 有生产引用但未进构建图 | 18 | 含 7 个纯类型文件（编译期擦除）、3 个 barrel（`common/index.ts` 17 处引用、`Maintenance/index.ts`、`adjudication/index.ts` 13 处引用，均被 Vite 内联展开）、旧 3D 栈的 6 个内层模块（只被同样不可达的模块引用）、`adjudication/data/criticalParts.ts`（被 barrel 再导出但被 tree-shake） |
| 零引用 | 6 | `api/tools.ts`、`Viewer3D/Atom01Viewer.tsx`、`Viewer3D/index.ts`、`Viewer3D/useRobotDataManifest.ts`、`components/knowledge/RobotProjectUploadPanel.tsx`、`pages/admin/ApprovalQueuePage.tsx` |
| 仅测试引用 | 3 | `adjudication/ui/examHeader.ts`（4 处引用，其中唯一的直接 import 来自 `p4_mode.test.ts`——8 个**从未被 vitest 收集**的伪测试之一）、`Viewer3D/ModelPreloader.tsx`、`store/workbenchStore.ts` |
| 构建配置加载 | 1 | `test-setup.ts`，由 `vitest.config.ts` 的 `setupFiles` 直接加载，属正常 |
| **合计** | **28** | 未分类 0 |

**旧 3D 栈的不可达闭包（跨上表两行）：** `Atom01Viewer`（零引用，根节点）→ `Atom01Model`、`DynamicModelLoader`；
`Viewer3D/index.ts`（零引用，另一根节点）→ `RobotViewer` → `HumanoidRobot` → `constants`、`hooks/useRobotData`；
`ModelPreloader` 仅被测试引用。合计 9 个文件构成与现行 `UniversalRobotViewer` 并存的死栈。

## 6. 方法局限（必须随结论一起引用）

1. **路由消费者判定用字符串匹配。** 判断某条后端路由是否被测试或前端调用，依据是测试/源码文本中出现该路由的静态前缀（前端按 `apiClient` 的 `baseURL = ${API_BASE_URL}/api/v1` 去掉 `/api/v1` 后匹配）。对**运行时动态拼接**的路径会漏判，因此 `UNUSED` 是「本批口径下未找到消费者」，不能直接当作删除依据。
2. **启动未导入 ≠ 死代码。** 后端 25 个未导入模块中，22 个能在源码中找到引用（多为 `scheduler` 内部的延迟导入或 `scripts/` 消费），只有 3 个全仓零引用。
3. **本批未执行测试。** 只做 `--collect-only` 与 `list`，因此所有验证等级上限为 E1（自动化测试存在且可被收集），不代表测试通过，更不代表 E2/E3/E4。
4. **数据库是本机开发库的时点快照**，不是交付环境；表为空不等于功能不可用，但可以证明该功能**从未在本库产生过数据**。行数一律用精确 `count(*)`——`pg_stat_user_tables.n_live_tup` 是统计估算值，本审计初版据此得出的空表数错了 30 张。
5. **前端构建图不覆盖运行时按需请求的资源**（如运行时拼出的 URL、后端下发的 manifest），这些对象由 A3 承接。
