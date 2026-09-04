# R-MOS 改造阶段交接（新窗口接手用）

- 版本：0.1.0｜日期：2026-09-04
- 交接原因：对话窗口结束
- **接手方式：读完 §1、§2、§7 三节即可开工**，其余按需查

---

## 1. 精确恢复点

| 项 | 值 |
|---|---|
| 工作区 | `/Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime`（**不是主仓**） |
| 分支 | `audit/phase3-auth-control-realtime` |
| HEAD | `3eafa8a4` |
| **是否 push** | **否。自 B-ASIS 起 47 个提交全在本地** |
| 被审基线 `B-ASIS` | `29d2a5889e3b320a3e777e3d8c19efbbe31c0294` |
| 干预前参照 `B-REF` | `361eaac85002eec4e9388ae4d7f30c2e3591eee6` |
| 后端测试 | **992 收集 / 992 通过** |
| 前端测试 | **518 通过 / 2 skipped**，`tsc --noEmit` 无错误 |

### 环境陷阱（**必读，每次运行都要**）

```bash
# 被审 worktree 没有 .env（worktree 不共享未跟踪文件）
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime/r-mos-backend
set -a; . /Users/xuhehong/Desktop/r-mos/r-mos-backend/.env; set +a
unset CORS_ORIGINS        # 该字段以环境变量形态存在时不是 JSON，pydantic-settings 会拒绝解析
export DEBUG=true         # 否则 validate_production() 拒绝启动
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python -m pytest -p no:warnings
```

| 规则 | 说明 |
|---|---|
| 标准解释器 | `/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python`（**唯一**，被审 worktree 无 venv） |
| **不要传 `-q`** | `pytest.ini` 已有 `addopts = -q`，再传一个会变成 `-qq`，**汇总行消失**（踩过两次） |
| **不要传 `--timeout`** | 未装 `pytest-timeout`，会直接报错 |
| 跑完必做 | `git checkout -- r-mos-backend/data/knowledge_store.json` —— **跑测试必污染该文件**（M-15），每轮手动还原 |
| 临时文件 | 一律写 scratchpad，不得污染被审工作区 |

---

## 2. 当前状态：两条线并行

### 线一：审计认证链 —— **卡住**

董事会 2026-09-03 裁定**路线 B**（原话「B」）：
**接受 26 项问题清单为改造输入、明示接受验证等级 E1、暂停 A0–A6 与 R0 认证链、改造即刻开始。**
裁定文件：`docs/plans/2026-09-03-board-decision-suspend-certification-start-remediation-v0.1.0.md`
（含明确承担的代价与重启条件，**接手必读**）。

| 阶段 | 状态 |
|---|---|
| A0 | `REOPENED / IN REVIEW`，未批准 |
| A1–A6 | `RETURN FOR REVISION` / `SUSPENDED` |
| R0 | `RETURN FOR REVISION`，**零合格主参考**（6 个软件候选 G2/G5 不完整全部 NOT_ELIGIBLE） |
| R1 | **BLOCKED**（A6 与 R0 均未批准） |

**唯一硬阻断是 AG-02（M-AUD-06 可理解性门禁）**，其余 AG-01/03/04/05 亦未闭合。

#### M-AUD-06 已实测四轮，状态见 §7

角色独立性要求：出题、答题、评分**必须**分属三个独立会话；
**主审（Claude）不得参与出题、答题、评分**，只能事后复验。
相关文件全部在 scratchpad：

```
FROZEN_QUESTIONS.md   冻结题目（7 题独立出题方起草 + 3 题董事会替换）
FROZEN_RUBRIC.md      冻结评分标准（**绝不可给答题者**）
maud06_2_answer.md    答题提示词
maud06_3_score.md     评分提示词
ANSWERS{2,3,4}.md     历轮作答
SCORE{,2,3,4}.md      历轮评分
```

### 线二：代码改造 —— **进行中，已修 8 项**

| 问题 | 状态 |
|---|---|
| M-10 CI 的 DEBUG 被 YAML 重复键吃掉 | ✅ 关闭 |
| M-04 接口契约匿名可读 | ✅ 关闭 |
| M-05 adapter 域零授权端点 | ✅ 关闭（删端点，能力保留） |
| F-RT-01/02/03 实时通道三缺陷 | ✅ 关闭 |
| M-02 认证身份与业务身份绑定 | ✅ 关闭 |
| **角色来源缺陷**（A6 未覆盖的新发现） | ✅ 关闭 |
| M-01 写路径对象归属 | ⚠️ **部分**（见 §3） |
| M-03 WebSocket 认证 | ⚠️ **部分**（见 §3） |
| M-06 审批闸门 | ⚠️ **部分**（见 §3） |

**授权覆盖率变化**：写端点 92 个中，有身份注入 46→**56**（60%），有授权守卫 10→**36**（39%），
高危端点（路径带对象 ID 且无身份无权限）**24 → 0**。

---

## 3. 三项「部分完成」的**精确剩余边界**（不得当作已关闭）

### M-01 写路径归属

- 13 个端点做了**对象级**归属校验（`ensure_write_owner` / `ensure_teacher_scope_over_student`）
- 11 个端点只是**角色制过渡**（`ensure_role_for_write`）——**同角色之间互不隔离**，
  任意教师仍可修改任意教学内容
- **阻断原因**：`sops`、`fault_cases`、`robot_sop_drafts`、`external_assessments`、
  `assessment_providers` **五张表均无任何创建者/拥有者字段**，数据库不记录归属
- **推进前提**：董事会须先定方向——①补归属字段+迁移（历史行 NULL 如何处置需一并定）；
  或②明确这些对象本就无个人归属，长期采用角色/权限模型

> **口径修正（重要）**：A6 的「94 条写操作仅 10 条有归属校验」隐含「这是代码疏漏」，
> 实际相当一部分是**数据模型缺陷**。两者修复路径完全不同：前者补守卫，后者要改 schema。

### M-03 WebSocket

- ✅ 认证（握手前拒绝，1008 关闭）、✅ 用户维度定向
- ⬜ **`robot_id` 仍不用于数据过滤**——遥测是单一全局流，任何登录用户仍收到全部机器人遥测
- 已在 `websocket.py` 端点 docstring 明确标注，勿因「有认证了」当作完成

### M-06 审批闸门

四处断点解决两处：

| 断点 | 状态 |
|---|---|
| ① 闸门不在执行路径上 | ✅ 已修（分派前阻断） |
| ② message 模式从不建审批记录 | ✅ 已修 |
| ③ 前端 `agent-v2.ts:193` 硬编码 `mode:'message'` | ⬜ command 模式仍永不触发 |
| ④ 批准后执行 `execute_write_tool_stub`（明写「不触发外部 IO」） | ⬜ **「批准即生效」不成立** |

> **④ 解决前不得声称审批闭环已建立。** 推进前提：董事会先定「真实写工具」的范围与安全边界。

---

## 4. 改造期建立的抽象（新增代码请复用，勿另造）

| 抽象 | 位置 | 用途 |
|---|---|---|
| `resolve_actor_identity()` | `authz_guard.py` | **业务身份一律取自认证上下文**；请求体声称他人身份→拒绝（不静默改用，否则冒用不可见） |
| `actor_has_role()` | `authz_guard.py` | 角色判定**唯一入口**，同时认 `account_role`（注册写入）与 `roles`（仅种子写入） |
| `resolve_actor_from_token()` | `authz_guard.py` | 令牌→ActorContext，**HTTP 与 WS 共用** |
| `ensure_write_owner()` | `ownership.py` | 写路径：**仅本人或管理员**（**故意不含**读路径的「同校教师」） |
| `ensure_teacher_scope_over_student()` | `ownership.py` | 教师职权：有管辖权教师或管理员，**所有者本人一律拒绝** |
| `ensure_role_for_write()` | `ownership.py` | 无归属字段对象的**角色制过渡**，文档已声明其局限 |

**贯穿原则：不造第二套。** 本项目病根之一是同一件事多套实现（M-14），
改造时若发现「需要一套新的 X」，先确认现有抽象为何不够用。

---

## 5. 主审在本轮犯过的错（**新窗口最容易重蹈**）

| 教训 | 具体事故 |
|---|---|
| **安全断言必须是行为级** | 曾写「检查源码文本是否含 `school_name`」当安全测试——守卫从未被调用也会绿。已删除重写 |
| **「零测试失败」≠ 守卫生效** | tasks 那批加守卫零失败，实因**那四个端点根本没有 HTTP 层测试**；另写行为测试才确认 |
| **静态扫描必须计入 router 前缀** | 扫描脚本只取装饰器路径，漏 `/pipeline` 前缀。**这正是异源复核在 A1 指出、主审判定成立并写入 0.2.0 的同一缺陷，本轮又犯一次** |
| **批量改签名须逐文件校验落地** | 脚本三次语法失败且中止后续写入，中途的「语法 OK」是因为**文件根本没被改** |
| **假对象不如真类型** | 手写假返回值补两轮属性仍失败，改用 `ModuleDispatchResult` 一次通过 |
| **动手前先查数据模型** | 维保草稿组做到一半才发现无归属字段。此后改为**先做归属字段预查**再动手 |
| **规则方向会反** | 评分若套「仅所有者」＝放行**学生给自己打分**。洞会换位置，不会消失 |
| **测试可能固化漏洞** | 见 §6 |

---

## 6. 测试里固化的漏洞（改端点必然击穿，属正常）

每批加守卫都会击穿一批原本绿着的用例，**它们固化的正是被修的漏洞**：

| 用例 | 原本断言的行为 |
|---|---|
| `test_e2e_teacher_flow` | 以**学生令牌**调 `force-submit`、请求体塞教师 id，**断言返回 200** |
| `test_attempt_status_transitions` | 同一身份「创建 → 标完成 → **给自己打分**」 |
| 三个维保草稿用例 | **教师给自己提交的草稿盖章通过** |
| 大量用例 | 用编造用户 id（10/42/901/1001/3001/7001…） |

> **「编造一个不存在的用户 id 传进去」能一直工作，唯一原因就是端点从不校验归属。**
> 遇到此类失败：**先判断是「测试固化了漏洞」还是「修复打断了合法流程」**，
> 前者按新规格更新断言（`pytest.ini` 对 `characterization` 标记的定义即如此），后者说明改错了。

---

## 7. 下一步（**接手第一件事**）

### M-AUD-06 已四轮实测完毕：**未通过，且已停止重测**

结果：2/10 → 8/10 → 8/10 → **7/10**（通过线 10/10）。
完整结论见 [`docs/audit/evidence/2026-09-04-maud06-final-result-v0.1.0.md`](../audit/evidence/2026-09-04-maud06-final-result-v0.1.0.md)，
四轮题目、作答、评分原件均已归档在 `docs/audit/evidence/2026-09-04-maud06-*`。

**决定性证据：没有任何一道题三轮全错**——6 题始终通过、0 题始终失败、4 题间歇失败。
若报告有实质缺陷，对应题目应每轮均错；实测无一如此，说明**十个概念均已传达到位**，
失分来自评分模型的噪声底（约 45 个必答点须全中，噪声本身即可掉 2–3 题）。

**已停止重测**，理由：继续重跑将退化为「刷到通过为止」，该门禁即失去意义。

#### 接手第一件事：请董事会裁定是否采纳替代方案

主审建议（**主审不自行认定通过**）：

> 以对抗式复核记录替代 M-AUD-06，作为**明示接受的残余风险**。

若董事会采纳，需在路线 B 裁定文件中落记（**已预留位置，见 §9 该文件的「补充裁定」节**）：

1. **M-AUD-06 以替代方式关闭**，标记为残余风险而非通过；
2. **豁免 DIR-07 / M-DEC-02**——指令要求「架构→模块→文件→代码」顺序，
   而路线 B 下的 9 批改造无上层 R1 批准依据，属逆序执行；
   不明示豁免，将来对照指令会出现无解释的违反项。

若董事会不采纳，则 AG-02 保持未闭合，A0 及其后全部阶段维持当前状态。

### 无论 A/B，以下三项均需董事会先定方向

| # | 决策 | 阻断什么 |
|---|---|---|
| 1 | 归属字段补不补、历史行 NULL 如何处置 | M-01 真正关闭 |
| 2 | 「真实写工具」的范围与安全边界 | M-06 断点④ |
| 3 | 是否 push 跑真实 CI | **「CI 可信」这一前提**——M-10 修复后 CI 从未在 GitHub 上真跑过，本地绿≠CI 绿 |

### 不需等决策即可推进的

- 剩余 56 个未加守卫的写端点，其中 **10 个「有权限门但无对象隔离」最该先看**
  （如 `POST /admin/users/{user_id}/role`、`POST /approval/{request_id}/approve`）
- M-15：跑测试污染 `data/knowledge_store.json`，每轮手动还原，**应进改造清单**

---

## 8. 硬性纪律（不得违反）

1. **门禁一条未解除**：`E1 FAIL`、`E2/E3/E4 BLOCKED`、生产启用 BLOCKED、`REL-BLOCK-01` 未清零
2. **不得表述为「审计已通过」**——若材料对外用于投标、尽调或合规，此缺口会被看见
3. **主审不得自评**：M-AUD-06 的出题/答题/评分必须异源
4. **每批改造收尾必做**：全量测试 + `DEVELOPMENT_LOG` 记录 + 还原 knowledge_store + 提交
5. **改动只在被审 worktree**，主仓 `/Users/xuhehong/Desktop/r-mos` 有用户自己的未跟踪文件，不得清理

---

## 9. 关键文件索引

| 用途 | 路径 |
|---|---|
| **董事会指令** | `docs/plans/2026-08-26-rmos-complete-audit-and-modernization-board-directive-v0.2.0.md` |
| **路线 B 裁定** | `docs/plans/2026-09-03-board-decision-suspend-certification-start-remediation-v0.1.0.md` |
| 审计索引（状态表在顶部） | `docs/audit/README.md` |
| A0–A6 当前正式版 | `docs/audit/2026-08-29-a*-v0.2.0.md`、`2026-08-30-a1-*v0.2.1.md`、`2026-09-02-a0-*v0.2.1.md` |
| 26 项问题台账 | `docs/audit/evidence/2026-08-29-a6-corrected-consolidation-ledger-v0.2.0.md` |
| 实时通道新发现 | `docs/audit/evidence/2026-08-29-realtime-channel-new-findings-v0.1.0.md` |
| R0 材料 | `docs/research/rmos-open-source-reference-v0.2.0/` |
| 机械闸门 | `docs/audit/evidence/2026-08-29-a0-a6-remediation-gate.py` |
| **改造全过程记录** | `docs-archive/DEVELOPMENT_LOG.md`（**倒序读最后 10 条即可掌握改造脉络**） |

---

## 10. 新窗口启动提示词

> 接手 R-MOS 改造阶段。工作区在 git worktree
> `/Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime`（不是主仓），
> 分支 `audit/phase3-auth-control-realtime`，HEAD `3eafa8a4`，47 个提交均未 push。
>
> **先读 `docs/handover/2026-09-04-remediation-phase-handover-v0.1.0.md`**，
> 重点 §1 恢复点与环境陷阱、§2 当前状态、§7 下一步。
>
> 现状：董事会已裁定路线 B（暂停审计认证链、接受 26 项问题清单、直接改造）。
> 已修 8 项，其中 M-01/M-03/M-06 为**部分完成**，精确剩余边界见 §3——**不得当作已关闭**。
>
> 环境：被审 worktree 无 `.env`，须
> `set -a; . /Users/xuhehong/Desktop/r-mos/r-mos-backend/.env; set +a` 且 `unset CORS_ORIGINS`、
> `export DEBUG=true`；解释器只有 `/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python`；
> **跑 pytest 不要额外传 `-q`**（会吞掉汇总行）；跑完须还原 `data/knowledge_store.json`。
>
> **务必读 §5「主审犯过的错」与 §6「测试固化的漏洞」**——那些坑很容易重踩，
> 其中「静态扫描漏 router 前缀」是主审判过别人成立、自己又犯的同一错误。
