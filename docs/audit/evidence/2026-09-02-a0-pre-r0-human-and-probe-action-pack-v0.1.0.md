# A0 至 R0 前置动作包

- 版本：0.1.0
- 日期：2026-09-02
- 状态：READY FOR BOARD / PROBE APPROVAL；A0 仍为 `REOPENED / IN REVIEW`
- 目的：把本地只读工作完成后仍需董事会或外部主体完成的动作收敛成一次可核验输入。
- 静态取证：[A0 当前静态漂移复算](2026-09-02-a0-static-drift-recalculation-v0.1.0.md)
- 待批准探针实现：[A0 指纹探针脚本](2026-09-02-a0-approved-fingerprint-probes.py)
- 董事会指令：[完整审计与架构改造方向指令 0.2.0](../../plans/2026-08-26-rmos-complete-audit-and-modernization-board-directive-v0.2.0.md)

## 1. 不能由主审代办的当前阻断

| 阻断 | 仍需谁做 | 完成证据 |
|---|---|---|
| A0 本机进程、数据库、运行路由、前端入口指纹 | 董事会批准后由主审执行只读探针 | 命令、输入、原始输出、退出码、前后快照和清理记录 |
| A0 总截止日期与 A1 范围 | 董事会确认 | 原始确认全文、时间、报告版本和提交 |
| B-REF 正式边界 | 董事会确认 | 明确确认 `361eaac...` 或给出替代提交及原始批准依据 |
| 八个 P0 主备送达 | 董事会指定通道并确认收件；主审执行测试 | 主、备用各自的发送记录和接收回执 |
| A0 M-AUD-06 | 董事会冻结题目；非主审答题和评分 | 十题、至少三道董事会题、冻结标准、原始回答、逐题评分、10/10、独立性 |
| A0 再批准 | 董事会 | A0 全部门禁闭合后的 `确认 Audit A0` |

在 A0 再批准前，A1～A6 只能作为预先编写材料，不能正式重开、重验或批准；R0 不能开始。

## 2. A0 只读指纹探针申请

四项探针共用以下前后边界。开始前和全部清理后各执行一次，结果必须一致；不一致则停止并把差异记为失败：

```bash
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime
git rev-parse HEAD
git status --porcelain
shasum -a 256 \
  r-mos-backend/data/knowledge_store.json \
  r-mos-backend/requirements.txt \
  r-mos-frontend/package-lock.json \
  /Users/xuhehong/Desktop/r-mos/r-mos-backend/.env
find r-mos-backend/data r-mos-backend/storage r-mos-frontend/public \
  -type f -exec stat -f '%N|%z' {} + | LC_ALL=C sort | shasum -a 256
find r-mos-backend/logs -type f -exec stat -f '%N|%z' {} + \
  | LC_ALL=C sort | shasum -a 256
```

### P-A0-PROC-01｜本机监听与容器映射

- 目的：识别 `8000`、`3000`、`55173` 当前监听者，补齐启动安全初筛中的本机入口事实；只列进程和容器，不发网络请求。
- 输入：本机进程表和 Docker 只读容器清单。
- 预期副作用：读取进程和 Docker socket；不启动、停止、进入或修改任何进程/容器。
- 恢复：无持久化变化；复核 Git 和关键文件摘要。若权限不足，保留原始错误并把容器归属标为 UNKNOWN。

拟执行命令：

```bash
lsof -nP -iTCP:8000 -iTCP:3000 -iTCP:55173 -sTCP:LISTEN
docker ps --no-trunc --format '{{.ID}}|{{.Image}}|{{.Ports}}|{{.Names}}'
```

当前未获批预查只确认 `*:3000` 由 Docker Desktop 后端进程持有；Docker socket 在受限环境中拒绝读取，因此不能确认它是否映射 R-MOS 容器。`8000` 和 `55173` 未见监听。该结果只把公网入口推进到 PARTIAL，不能写成“无部署”或“无暴露”。

### P-A0-DB-01｜数据库版本、扩展、schema 与迁移头

- 目的：补齐 AG-04/AG-05 的当前数据库事实源，只读取版本、扩展、schema、表名和 Alembic 版本，不读取业务行内容。
- 输入：主工作区现有 `.env` 中的 `DATABASE_URL`；当前本机 PostgreSQL。
- 拟执行：`SHOW server_version`、扩展名列表、public schema-only dump 摘要、表名列表、`alembic_version`；执行前后记录 Git、配置摘要和关键本地文件摘要。
- 预期副作用：建立本机数据库连接，可能产生数据库连接日志；不执行写 SQL、不迁移、不建表、不生成测试数据。
- 恢复：关闭连接；核对 Git、schema 版本、表名和关键文件摘要前后一致。若目标不是明确的本机非生产库，立即停止。

拟执行命令。脚本先从 `.env` 单独解析 `DATABASE_URL`，只有驱动为 PostgreSQL、主机精确为 `localhost`、端口为 `5432`、数据库名精确为 `rmos` 时才连接；不会把整个 `.env` 导入当前 shell，也不会打印口令。SQL 全部在 `READ ONLY` 事务中执行；schema dump 固定为 `public`、不含所有者、权限或数据行，且只在 `pg_dump` 退出码为 0 后计算摘要：

```bash
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python \
  docs/audit/evidence/2026-09-02-a0-approved-fingerprint-probes.py db \
  --env-file /Users/xuhehong/Desktop/r-mos/r-mos-backend/.env
```

成功标准：脚本退出码 0；输出中的 `target` 仅为 `localhost:5432/rmos`；`read_transaction` 为 `READ ONLY`；schema dump 退出码为 0。四项探针全部结束后再次执行同一 DB 命令，把两次脱敏 JSON 逐字段比较；表名、Alembic 版本、schema 摘要、Git、配置和关键文件摘要必须无变化。任何一项不符即判探针 FAIL，不重试写操作。

### P-A0-ROUTE-01｜运行时路由注册表

- 目的：在不启动监听端口的情况下导入当前 FastAPI 应用，导出 `app.routes` 的路径、方法和类型，与静态 176 HTTP + 2 WebSocket 分母比较。
- 输入：当前源码、标准 Python、主工作区 `.env`；禁止执行 lifespan。
- 预期副作用：导入应用、初始化日志和读取配置；不监听端口、不发送 HTTP、不连接外部服务、不执行 lifespan。
- 恢复：Python 进程退出；复比 Git、数据库标识和关键文件摘要。若导入触发写入或连接，立即中止并保留失败证据。

拟执行命令。与数据库探针相同，配置只进入这个子进程；脚本只导入应用对象，不执行 lifespan：

```bash
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python \
  docs/audit/evidence/2026-09-02-a0-approved-fingerprint-probes.py routes \
  --env-file /Users/xuhehong/Desktop/r-mos/r-mos-backend/.env
```

成功标准：脚本退出码 0，明确记录未执行 lifespan、未启动监听端口，并在导入 `main` 前禁用应用文件日志；完整路由清单及摘要可与静态分母逐项比较。导入日志不能替代路由输出，仓库内 `logs/` 不得新增或变化。

### P-A0-FE-01｜前端构建入口与回环可达性

- 目的：取得当前前端构建入口和声明路由的第二来源；只在本机回环地址验证页面可达，不登录、不发写请求。
- 输入：现有 `node_modules`、锁文件、当前前端源码。
- 拟执行：构建输出定向写入明确的临时目录；如构建通过，再启动 `127.0.0.1:55173`，仅访问公开页面和静态资源。
- 预期副作用：创建临时构建目录、占用本机端口、读取 npm 缓存；不安装依赖、不连接外网、不启动后端、不写数据库。
- 恢复：停止前端进程，删除明确的临时构建目录，复比仓库和关键文件摘要。

拟执行流程。预览必须在单独的受管终端会话运行，先记录该会话的准确进程号；以下四组不能被误写成一条阻塞命令：

```bash
# 终端 1：执行前边界、声明路由与构建
test ! -e /tmp/rmos-a0-fe-981670d4
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime/r-mos-frontend
rg -n '<Route|path=' src/App.tsx
npm exec vite -- build --outDir /tmp/rmos-a0-fe-981670d4
find /tmp/rmos-a0-fe-981670d4 -type f -exec stat -f '%N|%z' {} + | LC_ALL=C sort

# 终端 2：启动预览并保持前台运行；记录这个会话的准确 PID/会话号
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime/r-mos-frontend
npm run preview -- --host 127.0.0.1 --port 55173 --strictPort

# 终端 1：只读访问公开入口与两条公开声明路由
curl --noproxy 127.0.0.1,localhost -fsS http://127.0.0.1:55173/
curl --noproxy 127.0.0.1,localhost -fsS http://127.0.0.1:55173/login
curl --noproxy 127.0.0.1,localhost -fsS http://127.0.0.1:55173/register

# 终端 2：发送 Ctrl-C，等待该准确会话退出；不得使用 broad pkill
```

成功标准：构建、三次回环请求均退出码 0；静态声明、构建产物和 HTTP 返回形成三份可比证据；预览进程已按准确会话停止。页面返回只证明入口可达，不证明登录、业务流程或后端通过。

预览进程确认停止后，仅删除精确临时目录 `/tmp/rmos-a0-fe-981670d4`；若该目录在执行前已存在则停止，不覆盖。清理前先确认目标仍是这个精确目录：

清理命令：

```bash
test -d /tmp/rmos-a0-fe-981670d4
rm -rf -- /tmp/rmos-a0-fe-981670d4
test ! -e /tmp/rmos-a0-fe-981670d4
```

批准口令：

`批准 A0 只读指纹探针 P-A0-PROC-01/P-A0-DB-01/P-A0-ROUTE-01/P-A0-FE-01`

该口令只批准以上四项，不批准服务联调、登录、数据写入、迁移、种子、外部 AI、生产、真机或对象存储访问。

## 3. 需要重新确认的 A0 治理事项

历史报告曾转录过以下决定，但独立复核没有找到完整原始批准链，因此不能自动继承为当前 PASS：

1. 总墙钟仍以 2026-08-26 为开始日，2026-09-25 到期，2026-09-19 预警；本次重开不延长。
2. 正式确认 `B-REF=361eaac85002eec4e9388ae4d7f30c2e3591eee6`；该提交是首个 Phase 3 应用修改的直接父提交，提交正文登记了 Phase 2 签字，但不能替代本次原始确认。
3. A1 范围沿用董事会指令和 A0 历史范围：覆盖整个 R-MOS 项目；第三方包内部、历史文档主张、生产/真机/课堂操作和 A0–A6 内应用修复按既定规则排除，不把 Phase 3 当审计边界。
4. 当前主通知渠道是否为本任务对话；备用通道的名称、地址和接收人是什么。

建议董事会回复时逐项写明“确认”或给出替代值，不能用单独的“继续”代替。

可直接使用的回复模板：

```text
确认 A0 前置事项：
1. 批准 A0 只读指纹探针 P-A0-PROC-01/P-A0-DB-01/P-A0-ROUTE-01/P-A0-FE-01。
2. 确认 B-REF=361eaac85002eec4e9388ae4d7f30c2e3591eee6。
3. 确认总墙钟仍为 2026-09-25 到期、2026-09-19 预警，本次重开不延期。
4. 确认 A1 范围与排除项按本动作包第 3 节执行。
5. P0 主通道为：<通道、地址、接收人>。
6. P0 备用通道为：<与主通道独立的通道、地址、接收人>。
7. 确认已收到 M-01、M-02、M-03、M-05、M-06、M-07、M-13、M-18a 八个 P0 摘要。
```

第 7 项只形成主通道收件确认；备用通道仍须实际发送测试和八项通知并保存回执。

## 4. 八个 P0 主通道通知正文

以下均为当前 OPEN/REVERIFY，不因文档或局部代码修复自动关闭：

| 编号 | P0 摘要 | 当前边界 |
|---|---|---|
| M-01 | 写入口缺调用者或对象归属校验 | 代表性静态事实成立；精确计数待重建 |
| M-02 | 认证身份与请求业务身份未强制绑定 | OPEN |
| M-03 | WebSocket 无认证、对象过滤和用户维度 | 局部防泄露已修；身份门禁仍 OPEN |
| M-05 | B-ASIS adapter 入口无鉴权依赖 | 当前代码已删除，仍须新基线重验 |
| M-06 | 审批不在真实执行路径且双实现并存 | OPEN |
| M-07 | 机器人契约缺运动控制与急停 | OPEN；软件协议不能代替安全回路 |
| M-13 | 角色多源并存且职责分离失效 | OPEN |
| M-18a | 备份、恢复与回滚能力缺失 | OPEN；E2 BLOCKED |

主通道只有在董事会明确回复已收到这八项后才能形成收件回执；备用通道必须另做非破坏性测试和逐项送达，不能由本文件代替。

## 5. 启动安全初筛当前登记

本节只回答是否发现需要立即隔离的 P0 迹象，不替代 A4。没有证据的外部状态保持 UNKNOWN：

| 检查 | 2026-09-02 当前证据 | 状态与保护决定 |
|---|---|---|
| 公网入口 | 本机 `8000`、`55173` 未见监听；`*:3000` 由 Docker Desktop 后端持有，但受限环境无法读取容器映射；未检查外部部署 | PARTIAL / UNKNOWN；不访问该端口，获批执行 P-A0-PROC-01；不能写成无部署 |
| 未授权机器人控制 | M-07 仍为 OPEN；E3、生产和真机均 BLOCKED；没有当前真实机器人连接证据 | UNKNOWN；维持禁止真机、生产和外部控制通道 |
| 仓库与部署材料密钥 | 对 D-HEAD 的已跟踪应用/配置做私钥头、AWS AKIA 和长 `sk-` 模式的文件名级扫描，命中 0；未检查外部部署密钥 | 当前仓库未命中；外部 UNKNOWN；秘密仍只留字段名和摘要 |
| 跨校数据访问 | 历史动态证据实证同校跨学生写入；跨校动态范围 UNKNOWN；M-01/M-02 仍 OPEN | 已知 P0 保持 OPEN 并进入主备通知；不做越权实测 |
| 生产启用状态 | 当前章程和测试报告均记 `REL-BLOCK-01` 未清零，E2/E3/E4 与生产 BLOCKED；外部实际部署未核实 | BLOCKED / 外部 UNKNOWN；不得启用生产 |
| 安全联锁 | 没有 E3 或物理联锁证据 | UNKNOWN；不连接真机，软件协议不得充当安全回路 |

仓库密钥文件名级扫描复现命令如下；它不输出匹配内容，避免秘密落入日志：

```bash
git grep -IlE -- \
  '-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----|AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9_-]{20,}' \
  981670d4acc99901dc2e0c67f41544562599ede7 -- . \
  ':!docs-archive' ':!docs/audit' ':!docs/research'
```

本轮该命令无输出且退出码为 1，按 `git grep` 语义表示零匹配；退出码大于 1 才表示扫描失败。该限定模式扫描不是完整秘密审计，不能覆盖 Git 历史、忽略文件或外部部署。

## 6. 后续顺序

1. 获批后执行四项只读探针并完成前后复比；
2. 固化 A0 0.2.1 修订报告；
3. 另行冻结 A0 M-AUD-06 十题，执行独立答题和评分；
4. 八个 P0 完成主备送达；
5. 董事会使用 `确认 Audit A0` 再批准；
6. 此后才能依次重开、重验和批准 A1～A6；
7. A6 再批准后，才申请 `确认 Reference R0`。

本动作包不构成探针批准、P0 收件回执、A0 PASS、A1 启动或 R0 启动。

## 7. A0 最终退出门禁清单

只有以下项目逐项存在当前证据，才可向董事会申请 `确认 Audit A0`。任何 `PENDING`、`UNKNOWN` 或失败项都不得用申请动作本身覆盖：

| 编号 | 必须闭合的项目 | 最低证据 |
|---|---|---|
| EXIT-A0-01 | 审计工作区、分支、唯一提交和未提交状态固定 | 当前 HEAD、分支、`git status`、材料清单及提交哈希 |
| EXIT-A0-02 | B-ASIS、B-REF 和干预集边界 | B-ASIS 复算；董事会明确确认 B-REF；21 个提交、9+12、56 个对象可复算 |
| EXIT-A0-03 | 全项目事实源分母 | Git 分类未分类 0；运行对象与 Git 文件分母分开登记 |
| EXIT-A0-04 | 当前环境和漂移 | Git、依赖、配置字段、资产、数据库、运行路由、前端入口均有当前指纹；缺失项只能标 UNKNOWN |
| EXIT-A0-05 | 启动前安全筛查和隔离边界 | 公网入口、未授权机器人控制、密钥暴露、跨校访问、生产启用和安全联锁六项逐项有证据或 UNKNOWN，并有对应保护决定；数据库目标精确白名单；探针前后快照一致 |
| EXIT-A0-06 | 八个 P0 的主通道送达 | 八项逐项发送记录、接收人、时间和实际回执 |
| EXIT-A0-07 | 八个 P0 的独立备用通道送达 | 与主通道独立的通道、逐项发送记录和实际回执 |
| EXIT-A0-08 | 墙钟与预警 | 董事会确认到期日、预警日和本次重开是否延期 |
| EXIT-A0-09 | 事实源分级和冲突登记 | FACT / INFERENCE / UNKNOWN 明确；悬空引用、冲突和历史错误有处置 |
| EXIT-A0-10 | A1 范围和排除项 | 董事会确认全项目范围、运行事实源和排除边界；Phase 3 仅为干预层 |
| EXIT-A0-11 | 审计批次零越界改动 | A0 审计批次内应用、测试、配置、迁移和数据库变化严格为 0；历史漂移只能另行登记，不能替代此门禁 |
| EXIT-A0-12 | M-AUD-02 / M-AUD-03 | 当前报告链接、状态、计数和事实源可机械复算；独立复核无未处置实质问题 |
| EXIT-A0-13 | A0 M-AUD-06 | 另行冻结的十题、原始回答、逐题标准、独立评分、10/10 和角色独立性全部齐全 |
| EXIT-A0-14 | 稳定的 A0 修订报告 | 报告版本、证据链接、当前提交固定；董事会审阅对象唯一 |

申请 `确认 Audit A0` 与董事会实际发出该准确确认是两步。前者不改变状态；只有后者在全部退出门禁已闭合时，才可把 A0 从 `REOPENED / IN REVIEW` 提升为重新批准。随后仍须按 A1→A6 顺序分别重开、重验和批准，不能一次确认跨过六个阶段。
