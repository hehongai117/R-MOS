# A0 当前静态漂移复算证据

- 版本：0.1.0
- 采集时间：2026-09-02 09:35 CST
- 状态：STATIC PORTION COMPLETE / B-REF BOARD CONFIRMATION PENDING / AG-04 PARTIAL / AG-05 PARTIAL
- 工作区：`/Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime`
- 分支：`audit/phase3-auth-control-realtime`
- 历史事实基线 `B-ASIS`：`29d2a5889e3b320a3e777e3d8c19efbbe31c0294`
- 本轮漂移目标 `D-HEAD`：`981670d4acc99901dc2e0c67f41544562599ede7`
- 复算脚本：[2026-09-02-a0-static-drift-recalculation.py](2026-09-02-a0-static-drift-recalculation.py)
- 前序快照：[2026-08-31-current-environment-and-drift-fingerprint-v0.1.0.md](2026-08-31-current-environment-and-drift-fingerprint-v0.1.0.md)

## 1. 取证边界

本轮只读取 Git 对象、工作区源码、现有依赖环境、配置字段名、本机数据库目标的非敏感部分与本地文件元数据。不启动服务，不连接数据库，不执行迁移，不联网，不读取或输出口令、密钥等配置值，不连接生产、真机、外部 AI 或对象存储。

`D-HEAD` 是本轮新增证据文件之前的干净提交，用于避免证据文件把自己的分母继续推高。本文件进入 Git 后产生的文档差异属于治理记录漂移，不倒改 `D-HEAD` 的应用事实。

## 2. B-REF 与原 Phase 3 干预集复核

- FACT：`361eaac85002eec4e9388ae4d7f30c2e3591eee6` 是 Phase 3 首个应用提交 `341dc20c...` 的直接父提交。
- FACT：`361eaac...` 的提交正文登记了用户对 Phase 2 五项 ADR 决策的确认，同时明确写明“进入 Phase 3 需用户单独批准”。这是 Git 内的二手批准记录，不是原始董事会消息。
- INFERENCE：在现有 Git 与仓库材料中，`361eaac...` 是唯一符合“首个 Phase 3 应用修改前、最近一个登记用户批准的参照提交”的 B-REF 候选；正式固定仍需董事会重新确认。
- FACT：按候选范围 `361eaac85002eec4e9388ae4d7f30c2e3591eee6..B-ASIS` 共 21 个提交；其中 9 个应用、测试或脚本提交，12 个纯文档提交，与[原干预集证据](2026-08-26-a0-phase3-intervention-set-v0.1.0.md)一致，提交差集为 0。
- FACT：9 个非纯文档提交覆盖 56 个去重对象：应用/运行文件 27、测试文件 27、脚本 1、规则文件 1；没有依赖锁文件或迁移变化。
- UNKNOWN：仓库内仍未找到 Phase 3 总体开工或九个提交逐批批准的原始消息链。提交存在不能证明批准充分。
- 裁决：B-REF 候选身份与该候选范围内的 `INTERVENTION-SET` 完整性可以复现；B-REF 正式确认及每项原批准仍保持 `PENDING` / `UNKNOWN + MUST_REVERIFY`，不得改写历史计划来制造批准。

## 3. B-ASIS 到 D-HEAD 的 Git 漂移

复算结果：

| 项目 | B-ASIS | D-HEAD | 差异 |
|---|---:|---:|---:|
| Git 提交 | — | 35 | +35 |
| 跟踪文件 | 1,769 | 1,849 | +80 |
| 发生变化的路径 | — | 93 | +93 |
| 应用类文件 | 431 | 430 | -1 |
| 资产/模块 | 850 | 850 | 0 |
| 迁移 | 40 | 40 | 0 |
| 测试类文件 | 229 | 232 | +3 |
| Markdown | 136 | 188 | +52 |
| 未分类 | 0 | 0 | 0 |

93 个变化路径按影响域归并为：审计材料 39、研究材料 35、其他文档 10、后端应用 6、后端测试 2、CI 配置 1；前端应用、迁移和依赖清单变化均为 0。

只有 4 个提交改变了被审程序、测试或 CI：

| 提交 | 变化 | 当前边界 |
|---|---|---|
| `a8be4c58...` | 修复 integration-ci 的 DEBUG 配置 | 只证明静态配置已改；远程 CI 运行仍 UNKNOWN |
| `8d242faf...` | 生产环境关闭匿名接口契约，删除 adapter 五端点 | M-04/M-05 需按当前基线重验；不能倒改 B-ASIS 历史事实 |
| `56751f5e...` | 实时通道定向投递、并发发送和心跳回执第一轮修复 | F-RT-01/02 定向 E1 通过；F-RT-03 仅防泄露 |
| `f5fc614e...` | 补慢连接清理、教师监控日志和回归保护 | 真实 WebSocket 身份仍缺，M-03 未关闭 |

## 4. 静态对象分母影响

| 对象 | B-ASIS | D-HEAD | 影响 |
|---|---:|---:|---|
| HTTP 路由装饰器 | 181 | 176 | 删除 adapter 的 5 条路由 |
| GET | 87 | 84 | -3 |
| POST | 76 | 75 | -1 |
| DELETE | 5 | 4 | -1 |
| PATCH / PUT | 7 / 6 | 7 / 6 | 不变 |
| WebSocket 路由 | 2 | 2 | 数量不变，实现已变化 |
| 路由模块 | 36 | 35 | adapter 模块退出注册 |
| 静态 ORM 表 | 65 | 65 | 不变 |
| 后端测试文件 / 收集项 | 123 / 971（B-ASIS 历史现场证据） | 124 / 976（本轮现场复算） | 两侧均只表示收集分母；本轮没有重建 B-ASIS 的 971 项运行环境 |

- A1：原 181 HTTP + 2 WebSocket 是 B-ASIS 历史分母；当前静态分母为 176 + 2，正式重开 A1 时必须使用新基线重新做双源差集。
- A2：被删除的 5 条 adapter 路由含 2 条写入口，因此 B-ASIS 的写入口精确分母不能直接当作当前分母。
- A3：表、迁移与依赖清单静态分母未变，但 WebSocket 管理器和教师监控的共享状态行为已变化，相关运行后果仍需重验。
- A4：M-04/M-05 有后续修复，M-03 有部分修复；这些变化均不得把 B-ASIS 历史风险改写成当时已通过。
- A5：CI 配置和测试集合发生变化；本轮没有执行完整套件、远程 CI、恢复、回滚或 E2，故不能产生当前全量 PASS。

## 5. 当前环境静态复比

| 类别 | 2026-08-31 | 2026-09-02 | 裁决 |
|---|---|---|---|
| Python / pip freeze | 3.13.13；84 项；`756df726...3925` | 相同 | 无已观察漂移 |
| `requirements.txt` | `a0d75483...7439` | 相同 | 无已观察漂移 |
| Node / npm | v20.19.2 / 10.8.2 | 相同 | 无已观察漂移 |
| `package-lock.json` | `87888972...412` | 相同 | 无已观察漂移 |
| npm 顶层依赖树 | `0a171fb1...1cdc` | 相同 | 无已观察漂移 |
| `.env` 来源/摘要 | 主工作区 `.env`；`348c2191...3495` | 相同 | 来源风险未消除，值未落证据 |
| `.env` 字段 | 10 个字段 | 相同 10 个字段 | 字段级无已观察漂移 |
| 数据库目标（仅解析，未连接） | 未登记 | `postgresql+asyncpg` / `localhost:5432/rmos` | 已为待批准探针固定精确白名单；运行事实仍 UNKNOWN |

## 6. 忽略资产与测试遗留

2026-09-02 只读复算得到：`r-mos-backend/data` 6 个文件、291,971 bytes；`storage` 28 个文件、504 bytes；`r-mos-frontend/public` 849 个文件、1,036,978,266 bytes；合计 883 个文件、1,037,270,741 bytes。按“相对仓库路径 + `|` + 文件大小 + 换行”排序形成的清单摘要为 `e3b72016b212a8b7371f95ff690a203176c2faf0246918995a72180d4dd6843e`。

2026-08-31 08:24 的前序报告记录合计 880 个文件，本轮为 883。当前清单中有 3 个 18-byte 的 `storage/training-evidence/.../station.jpg` 修改时间晚于该快照，分别为 08:29、08:35、08:38；`data/knowledge_store.json` 修改时间为 08:38。它们与同日上午后端回归执行窗口一致。由于前序证据没有保存逐文件清单，只能写“报告总数相差 3 且当前有 3 个晚于快照的文件”，不能把这三项机械证明为唯一新增内容。

- FACT：本轮文件数、路径、大小和修改时间可现场复算；前序报告记载总数 880。Git 工作区仍干净，说明这些对象未被跟踪或被忽略。
- INFERENCE：三份证据文件和知识文件变化由 2026-08-31 测试产生；时间、目录和开发记录相符。
- UNKNOWN：前序证据没有保存逐文件清单，无法仅靠摘要证明除此之外的内容级变化为 0。因此本项完成归因提示，但不能写成完整历史复比 PASS。

## 7. 当前门禁裁决

| 门禁 | 本轮推进 | 当前状态 |
|---|---|---|
| B-REF | 从 UNKNOWN 推进为唯一可复现候选 | INFERENCE / BOARD CONFIRMATION PENDING |
| INTERVENTION-SET 完整性 | 按候选范围重新枚举 21 个提交，9+12 差集 0 | FACT / CONDITIONAL ON B-REF；原批准仍 UNKNOWN |
| AG-04 | Git、Python、Node、配置字段和本地存储已刷新 | PARTIAL；数据库、运行路由和前端运行入口未采集 |
| AG-05 | B-ASIS→D-HEAD 静态分母及 4 个代码批次已归因 | PARTIAL；运行事实和历史同期指纹仍缺 |

本证据不关闭 AG-02/AG-03，不构成 A0 再批准，不提升 A1～A6、R0、R1、E2/E3/E4、`REL-BLOCK-01` 或生产状态。

## 8. 复现命令

```bash
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python \
  docs/audit/evidence/2026-09-02-a0-static-drift-recalculation.py \
  981670d4acc99901dc2e0c67f41544562599ede7

/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python \
  docs/audit/evidence/2026-08-26-a0-whole-project-source-denominator.py \
  29d2a5889e3b320a3e777e3d8c19efbbe31c0294

git log --reverse --format='%H %s' \
  361eaac85002eec4e9388ae4d7f30c2e3591eee6..29d2a5889e3b320a3e777e3d8c19efbbe31c0294

# B-ASIS 的 123 个测试文件可直接从固定 Git 树复算；971 项是下列历史
# 证据在当时环境的收集结果，本轮不把它伪装成当前重跑结果：
# docs/audit/evidence/2026-08-26-a1-dual-source-diff-v0.1.0.md §4.3
git ls-tree -r --name-only \
  29d2a5889e3b320a3e777e3d8c19efbbe31c0294 -- r-mos-backend/tests \
  | rg '/test_[^/]*\.py$' | wc -l

# 当前后端测试收集分母；只收集，不执行。输出文件位于 /tmp，可删除。
cd r-mos-backend
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python \
  -m pytest --collect-only -qq > /tmp/rmos-a0-pytest-collect.txt \
  2> /tmp/rmos-a0-pytest-collect.err
awk -F': ' '/^tests\// {sum += $2; files += 1} END {print files, sum}' \
  /tmp/rmos-a0-pytest-collect.txt
cd ..

# 依赖和配置摘要；pip 的 cache warning 不影响 stdout 摘要。
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python --version
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python -m pip freeze | shasum -a 256
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python -m pip freeze | wc -l
shasum -a 256 r-mos-backend/requirements.txt \
  r-mos-frontend/package-lock.json \
  /Users/xuhehong/Desktop/r-mos/r-mos-backend/.env
node --version
npm --version
(cd r-mos-frontend && npm ls --depth=0 --json) | shasum -a 256

# 本地资产规范化元数据摘要、逐目录计数/大小和关键修改时间；不读取文件内容。
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python -c \
  "from pathlib import Path; import hashlib; root=Path.cwd(); ps=sum(([p for p in (root/d).rglob('*') if p.is_file()] for d in ('r-mos-backend/data','r-mos-backend/storage','r-mos-frontend/public')),[]); rows=[f'{p.relative_to(root).as_posix()}|{p.stat().st_size}' for p in sorted(ps)]; print(len(rows),sum(p.stat().st_size for p in ps),hashlib.sha256(('\\n'.join(rows)+'\\n').encode()).hexdigest())"
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python -c \
  "from pathlib import Path; root=Path.cwd(); ds=('r-mos-backend/data','r-mos-backend/storage','r-mos-frontend/public'); [(lambda ps: print(d,len(ps),sum(p.stat().st_size for p in ps)))([p for p in (root/d).rglob('*') if p.is_file()]) for d in ds]"
find r-mos-backend/storage/training-evidence -type f \
  -exec stat -f '%Sm|%z|%N' -t '%Y-%m-%dT%H:%M:%S%z' {} + \
  | LC_ALL=C sort
stat -f '%Sm|%z|%N' -t '%Y-%m-%dT%H:%M:%S%z' \
  r-mos-backend/data/knowledge_store.json
```

本轮上述命令退出码均为 0。关键输出分别为：干预集 21 个提交（9 个应用/测试/脚本提交、12 个文档提交）、56 个对象（27 应用/运行、27 测试、1 脚本、1 规则）；测试收集 `124 976`；Python 3.13.13 / 84 项；Node v20.19.2 / npm 10.8.2；资产 `883 1037270741 e3b72016...843e`。静态脚本的完整 JSON 输出不写入仓库，报告表格只摘录其中的确定字段。
