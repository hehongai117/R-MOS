# A0–A6 审计收官 → R0 开源研究 交接

- 版本：0.1.0
- 日期：2026-08-29
- 交接原因：对话窗口上下文接近上限
- 交接范围：**A0–A6 完整审计已全部完成**；下一步是 R0 开源参考架构研究
- 接手方式：**读完 §1、§4、§5、§7 四节即可开工**，其余按需查

---

## 1. 精确恢复点

| 项 | 值 |
|---|---|
| 工作区 | `/Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime`（**不是主仓**） |
| 分支 | `audit/phase3-auth-control-realtime` |
| HEAD | `c939c2a5`（A6 收官提交） |
| **是否 push** | **否。8 个提交全在本地** |
| 被审基线 | `B-ASIS = 29d2a5889e3b320a3e777e3d8c19efbbe31c0294` |
| Phase 3 前参照 | `B-REF = 361eaac85002eec4e9388ae4d7f30c2e3591eee6` |
| 应用代码改动 | **A0 起全程 0**（只写 `docs/audit/**` 与开发记录） |
| 墙钟 | 2026-08-26 起算，**2026-09-25 到期，09-19 预警**；A0–A6 用时 3 天 |

**提交链（全部未 push）：**

```
f30c564d  A0 收口批准
67a4ce30  A1 全系统功能与资产清单
be72b6e5  A2 用户角色与业务闭环
f87c6303  A2 获确认 + A1 0.1.1 口径修订
d3020017  A3 当前架构与数据边界
cef83be2  A4 安全、控制与实时通道
2da314df  A5 质量、运行与交付能力
c939c2a5  A6 总问题表与决策输入 + A4 0.1.1   ← HEAD
```

---

## 2. 新窗口必读顺序

1. `docs/audit/README.md`（版本 1.1.0）——**实时状态表在最上面，先读它**
2. `docs/audit/2026-08-28-a6-master-audit-report-and-decision-input-v0.1.0.md`——**25 个 Master 问题、三路线比较、三个待决策点**
3. 本交接文档 §4、§5、§7
4. `docs/plans/2026-08-26-rmos-complete-audit-and-modernization-board-directive-v0.2.0.md` §7（R0 研究章程）——**只在要开工 R0 时读**

**不要**靠 git log 或读代码反推进度。

---

## 3. 已完成

| 阶段 | 报告 | 状态 |
|---|---|---|
| A0 | `2026-08-26-a0-baseline-and-source-governance-audit-report-v0.1.1.md` | Approved |
| A1 | `2026-08-26-a1-system-function-and-asset-inventory-v0.1.1.md` | Approved |
| A2 | `2026-08-27-a2-user-roles-and-business-closure-audit-report-v0.1.0.md` | Approved |
| A3 | `2026-08-27-a3-current-architecture-and-data-boundaries-v0.1.0.md` | Approved |
| A4 | `2026-08-28-a4-security-control-and-realtime-audit-report-v0.1.1.md` | Approved |
| A5 | `2026-08-28-a5-quality-operations-and-delivery-audit-report-v0.1.0.md` | Approved |
| **A6** | `2026-08-28-a6-master-audit-report-and-decision-input-v0.1.0.md` | **Ready for Board Review（待确认）** |

每份报告都有配套 evidence 文件在 `docs/audit/evidence/`。

**A6 的核心产出：101 条问题归并为 25 个 Master（P0 8、P1 10、P2 7），未裁决数 0。**
系统画像：**骨架健康、写路径薄弱、运行能力空白**。

---

## 4. 接手第一件事：当前待办

### 4.1 A6 尚未获董事会确认

A6 状态是 `Ready for Board Review`。**用户确认前不得进入 R0。**
确认后需要做的动作（照抄前几轮的模式）：

1. 在 `docs/audit/README.md` 把阶段改为「A6 Approved，进行中：R0」
2. 把 A6 报告首页状态改为 Approved 并注明确认日期与用户原话
3. 追加 `docs-archive/DEVELOPMENT_LOG.md` 记录
4. 提交

### 4.2 八个 P0（改造阶段的输入，本阶段不修）

| Master | 问题 |
|---|---|
| M-01 | 94 条写操作仅 10 条有对象归属校验；46 条写端点拿不到调用者身份，27 条路径带对象 ID |
| M-02 | `force-submit` 校验的是请求体自带的 `teacher_id`（身份冒用，且写入记录当操作人） |
| M-03 | WebSocket 零认证、`robot_id` 不过滤、`send_to_user` 实为全量广播 |
| M-05 | `adapter` 域 5 条端点依赖列表为空，含 `POST /adapter/inject-fault` |
| M-06 | 审批两套实现，实际使用的一套是进程内内存队列不落库 |
| M-07 | 适配器契约无运动控制与急停（阻断 E3） |
| M-13 | `auditor` 拥有 `approvals:grant`/`reject`；角色三处并存且运行期不可维护 |
| M-18a | 无备份脚本、无恢复演练、无真实回滚演练（阻断生产启用） |

### 4.3 不需等任何决策就能动的三件事

`M-04` 网关前缀扩展、`M-05` adapter 补依赖、**`M-10` CI 的 `DEBUG` 一行修复**。
最后一条尤其要紧——`integration-ci` 的 job 有两个 `env:` 块，第二个静默覆盖了第一个的
`DEBUG: "true"`，导致后端启动即被 `validate_production()` 拒绝，**该 workflow 大概率长期是红的**。
修它会直接改变「CI 是否可信」这个前提。

---

## 5. 待用户决策（未答复前不得自行推定）

| # | 决策点 | 影响 |
|---|---|---|
| 1 | **是否申请受控 E2 环境** | 不申请则 A6 三路线比较的运行维度永远 UNKNOWN，路线决策只能基于安全与架构维度。A5 §6 已列好 10 项 E2 采集清单 |
| 2 | **审批保留哪一套**（M-06） | `/agent/approval/*`（有测试无消费者）vs `/ai/approvals/*`（有可达只读消费者但写操作 UI 不可达）。这是唯一需要业务判断的技术收口 |
| 3 | **故障注入是否为产品能力**（M-05） | 决定 `adapter` 域是补授权还是整体删除 |

另需用户明确：**A6 确认后是先做 R0 研究，还是先动 §4.3 的三件事。**

---

## 6. 关于 Codex 的使用（**必读，这是本轮审计最有价值的部分**）

### 6.1 固定调用模板

**只读复核（不需数据库）：**
```bash
codex exec --sandbox read-only -C <被审工作区> -o <结果文件> - < <提示词文件>
```

**需要数据库或网络时（工作目录必须放在仓库外，它就写不到被审工作区）：**
```bash
mkdir -p <scratch>/codex_cwd
cd <scratch>/codex_cwd && codex exec \
  --sandbox workspace-write \
  -c sandbox_workspace_write.network_access=true \
  --skip-git-repo-check \
  -C <scratch>/codex_cwd \
  -o <结果文件> - < <提示词文件>
```

> 只读沙箱**连不上数据库**（TCP 与 Unix 套接字均被拒），A4/A5/A6 都用的第二种。

### 6.2 提示词必须包含的纪律

1. 禁止修改被审仓库；临时文件只写在自己的工作目录
2. 数据库只读；禁止执行测试套件（会有副作用且耗时）
3. **禁止读取 `/private/tmp/claude-501/` 下主审的脚本或结果**
4. 每条结论必须附实际执行的命令
5. **要求它两个方向都查**：是否夸大 / 是否遗漏或美化
6. **额外要求它独立提出主审未列出的问题**——这一条在 A4/A5 各挖出 4 个和 6 个我完全没覆盖的问题

### 6.3 战绩（说明为什么必须用它）

六轮复核累计：**抓出主审 21 条实质错误**、**独立发现 14 个主审完全未覆盖的问题**、**查出 7 处报告间互相矛盾**。
**它的结论要逐条复验，但采纳率极高——本轮 21 条全部成立。**

---

## 7. 固定运行规则（环境陷阱，踩过的坑）

```bash
# 被审工作区没有 .env（git worktree 不共享未跟踪文件）
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime/r-mos-backend
set -a; . /Users/xuhehong/Desktop/r-mos/r-mos-backend/.env; set +a
unset CORS_ORIGINS        # 该字段以环境变量形态存在时不是 JSON，pydantic-settings 会拒绝解析
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python <脚本>
```

| 规则 | 说明 |
|---|---|
| 标准解释器 | `/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python`（**唯一**，被审 worktree 无 venv） |
| PostgreSQL | 需先 `brew services start postgresql@14`；库名 `rmos` |
| 构建产物 | 一律写到 scratchpad，**不得污染被审工作区** |
| 应用代码 | **零改动**。只写 `docs/audit/**`、`docs/handover/**`、`docs-archive/DEVELOPMENT_LOG.md` |
| 每阶段收尾 | 报告 + evidence + README 状态表 + DEVELOPMENT_LOG + 记忆 + 提交，**缺一不可** |

---

## 8. 主审在本轮犯过的错（**新窗口最容易重蹈的**）

| 教训 | 具体事故 |
|---|---|
| **先找出项目自己的抽象，再设计检测** | A4 没找到 `app/services/ownership.py` 的 `ensure_user_scope()`，把归属校验低报了一半（13 vs 26），**把问题说重了** |
| **先确认该库的约定，别用通用假设** | A5 只搜 `403`，而 R-MOS 刻意用 **404** 表达归属拒绝（不泄露存在性），在「有没有越权测试」上**连错两次** |
| **静态匹配必须解析到符号来源** | A3 按类名匹配，在 Pydantic schema 与 ORM 同名时误判、在 `import X as XModel` 别名导入时漏判 |
| **归并要机械提取 + 全文通读双跑** | A6 按「表格 ID 行」提取，结构性漏掉 A3 正文里 4 条无编号问题 |
| **多报告的单一事实包必须做交叉引用检查** | Codex 查出 7 处矛盾：状态未随批准同步、同一事实数字不一致、已修正结论在别处仍是旧版 |
| **边界描述要写清适用范围** | 「无绕过」应写成「`/api/v1` 内无绕过」——前缀级网关管不到前缀外 |
| **文档字符串不是事实源** | 日志文件名（实际 `app_YYYYMMDD.log`）和 `/health` 的 503 都只写在 docstring 里，实现都不是那样 |
| **YAML 重复键静默覆盖** | 配置审计要**解析后看最终值**，不能读源文本 |
| **统计数字必须带口径** | 「零断言 3 个」不说明是否把 `pytest.raises` 算作断言就是误导 |
| **静态分析看不见「检查了错的输入」** | `force-submit` 有管辖权校验但校验的是请求体自带身份，任何「是否存在检查」的扫描都会给它打勾 |

---

## 9. 裁决状态（未变）

| 项 | 状态 |
|---|---|
| E1 软件与主链路 | **FAIL** |
| E2 预生产 / E3 真机 / E4 课堂 | **BLOCKED** |
| 生产启用 | **BLOCKED**，`REL-BLOCK-01` 未清零 |
| 全部审计结论的验证等级 | 上限 **E1**（静态代码、配置、数据库只读） |
| 受控 E2 | **未采集**，10 项运行能力全部 `E2_NOT_COLLECTED`／`E2_HISTORICAL`／`E2_BLOCKED` |

---

## 10. 新窗口启动提示词

> 接手 R-MOS 完整审计项目。工作区在 git worktree
> `/Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime`（不是主仓），
> 分支 `audit/phase3-auth-control-realtime`，HEAD `c939c2a5`，8 个提交均未 push。
>
> 先读 `docs/handover/2026-08-29-audit-a6-to-r0-handover-v0.1.0.md`，
> 再读 `docs/audit/README.md` 顶部的状态表。
>
> 现状：A0–A6 完整审计已全部完成，A0–A5 已获确认，**A6 待我确认**。
> A6 产出 25 个 Master 问题（P0 8、P1 10、P2 7），并给出三个待我决策的点。
>
> 环境陷阱：被审 worktree 没有 `.env`，运行时探测需
> `set -a; . /Users/xuhehong/Desktop/r-mos/r-mos-backend/.env; set +a` 且 `unset CORS_ORIGINS`；
> 标准解释器只有 `/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python`。
> 应用代码保持零改动，只写 `docs/audit/**`。
>
> 每个阶段必须用 Codex 做异源复核（模板见交接文档 §6），它的结论逐条复验后采纳。
> **务必读交接文档 §8「主审犯过的错」——那些坑很容易重踩。**

---

## 11. 本次交接没有做的事

- **没有 push**：8 个提交全在本地，是否 push 由用户决定
- **没有开始 R0**：需 A6 获确认后按指令 §7 章程执行（research 技能链）
- **没有修任何代码**：A0 起应用代码零改动的纪律保持到改造阶段正式启动
- **没有申请 E2 环境**：待用户决策
- **没有动 CLAUDE.md**：其数字声明滞后（22 endpoints/50+ services/32+ models/15+ pages 实际为 37/99/65/27），
  已登记为 M-24，属被审工作区的非审计文件，按纪律未改
