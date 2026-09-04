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
| HEAD | 见 `git log -1`（2026-09-04 已推进至第 17 批） |
| **是否 push** | **是**。董事会裁定 §9-3 后已 push 至 `origin/audit/phase3-auth-control-realtime` |
| 被审基线 `B-ASIS` | `29d2a5889e3b320a3e777e3d8c19efbbe31c0294` |
| 干预前参照 `B-REF` | `361eaac85002eec4e9388ae4d7f30c2e3591eee6` |
| 后端测试 | **992 通过**（本地 PG 环境；Codex 沙箱下会有 3 项 DB 门禁因禁止连 `::1:5432` 失败，属环境限制） |
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
| ~~跑完必做还原 knowledge_store~~ | **M-15 已关闭**（第 14 批）：conftest 已把该文件重定向到临时目录，跑测试不再污染工作区 |
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

### 线二：代码改造 —— **进行中，已推进至第 14 批**

| 问题 | 状态 |
|---|---|
| M-10 CI 的 DEBUG 被 YAML 重复键吃掉 | ✅ 关闭 |
| M-04 接口契约匿名可读 | ✅ 关闭 |
| M-05 adapter 域零授权端点 | ✅ 关闭（删端点，能力保留） |
| F-RT-01/02/03 实时通道三缺陷 | ✅ 关闭 |
| **角色来源缺陷**（A6 未覆盖的新发现） | ✅ 关闭 |
| **M-01 写路径对象归属** | ✅ **关闭（第 13 批）**——五表补归属字段 + 迁移 + 11 端点按性质重新处置 |
| **M-15 测试污染工作区文件** | ✅ **关闭（第 14 批）** |
| **M-02 认证身份与业务身份绑定** | ✅ **关闭（第 10/11/12 批）**——自述身份写端点 8→2，剩余 2 个均有书面判定（见 §3） |
| M-03 WebSocket | ⚠️ **部分**——认证/定向/**robot_id 授权**已做；数据过滤属新功能（见 §3） |
| M-06 审批闸门 | ⚠️ **部分**（见 §3） |

#### 第 10–17 批新增（2026-09-04）

| 批 | 内容 | 实现方 |
|---|---|---|
| 10 | 创建路径业务身份收敛（`/tasks`、`/pipeline/tasks/from-diagnosis`、`/training/projects/generate`） | Claude |
| 11 | 删除内存态 agent 端点 8 条（裁定 §9-1）+ `approval_queue.py` + 17 条固化被删能力的测试 | Claude |
| 12 | 注册挂靠审计留痕 + 同校约束补行为级覆盖（裁定 §9-4） | Claude |
| 13 | M-01 归属字段与对象级守卫（裁定 §9-2）；**发现并修复 `DELETE /sops/{id}` 守卫困在 docstring 内、从未执行** | Claude |
| 14 | M-15 测试污染 | Codex |
| 15 | WebSocket 的 `robot_id` 访问授权（M-03 剩余可做部分） | Codex |
| 16 | 写端点授权覆盖率复测 + 8 处无争议缺口 | Codex |
| 17 | 证据/事件/观测三表补归属（照搬 §9-2 先例） | Codex |

**授权覆盖率（第 16 批运行期实测）**：87 个写端点，统一守卫 46→**54**，
带对象 ID 的端点 30/44→**33/44**。

> **Codex 的沙箱禁止连本机 PostgreSQL**，因此它报告的全量结果恒有 3 项 DB 门禁失败
> （`test_audit_query_indexes_exist` 等）。**那是环境限制不是缺陷**，主审在无限制环境复跑均为全绿。
> 涉及 Alembic 实迁的验证必须由主审复跑——Codex 写得出迁移，但跑不了。

**授权覆盖率**：删除 8 条内存态路由后写端点为 84 个。逐条数字请**用运行期扫描现算**
（载入真实 `app` 枚举 `APIRoute`），勿引用历史快照——本项目的静态计数已错过两次。

---

## 3. 三项「部分完成」的**精确剩余边界**（不得当作已关闭）

### ~~M-01 写路径归属~~ → **已关闭（第 13 批）**

董事会裁定 §9-2「补归属字段 + 迁移」后已完成：五表补 `created_by_user_id` + `school_name`
（迁移 `20260904_m01_ownership`，已在本地 PG 实跑 upgrade→downgrade→upgrade）。

11 个角色制过渡端点**按性质分三类**处置，而非一律替换：

| 类别 | 处置 |
|---|---|
| 教学内容 | → `ensure_write_owner`（作者或管理员） |
| 审批 | → `ensure_reviewer_not_author`（作者不得自批，**管理员不豁免**） |
| 治理（评估撤销/恢复/机构登记） | **维持 admin-only**：依据是职权而非归属，**不是**待放宽的过渡态 |

**历史行不回填**：`created_by_user_id` 保持 NULL＝系统内置公共内容，仅管理员可改。
`school_name` 为多租户准备维度，**当前不参与任何授权判定**（S-2 才是正式方案）——
勿因该列存在而误认为跨租户隔离已实施。

> **口径修正（保留供参考）**：A6 的「94 条写操作仅 10 条有归属校验」隐含「这是代码疏漏」，
> 实际相当一部分是**数据模型缺陷**。两者修复路径完全不同：前者补守卫，后者要改 schema。

### M-02 认证身份与业务身份绑定（**口径由「已关闭」修正为「部分」**）

上一批记为 ✅ 时，收敛的只是**已有身份注入**的端点。第 10 批用运行期扫描复查，
12 个自述业务身份的写端点中仍有 8 个直接采信调用方自述。现状：

- ✅ 第 10 批收敛 3 个（tasks / pipeline / training projects）
- ✅ 第 11 批随内存态端点删除消失 3 个（approval request/approve、v2 task create）
- ✅ 第 12 批判定 1 个（`auth.register` 的 `teacher_id`：跨校已堵，同校自选为明示接受的残余风险 + 审计留痕）
- ⬜ `POST /agent/coordinate`：经核实**不属**本类（`user_id` 是字符串任务标识，
  内存协调器原样回显、不落库、不参与授权），端点内已有书面判定

### M-03 WebSocket

- ✅ 认证（握手前拒绝，1008 关闭）、✅ 用户维度定向
- ⬜ **`robot_id` 不用于数据过滤**

> **原描述有误导，已更正**：并非「任何登录用户收到**全部机器人**的遥测」。
> `AdapterFactory.get_adapter()`（`adapters/factory.py:60`）是**不接受 robot_id 的全局单例**，
> `_push_telemetry`（`websocket_manager.py:219`）产生的是**唯一一份**遥测——
> 当前架构下压根不存在「机器人 A 的遥测」与「机器人 B 的遥测」之分，**没有可过滤的数据源**。
>
> 真正的按机器人隔离需要多 adapter 实例 + 订阅分发，那是**新功能**，不是补漏洞。
> 可做且已立项的是**授权边界**：`/ws/robot/{robot_id}/status` 此前完全不校验
> 调用者对该 robot_id 有无访问权。先把边界立起来，多源遥测到位时不必回头补。

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
| `ensure_role_for_write()` | `ownership.py` | 仅剩**创建类**（无既存对象可判归属）与**治理类**（admin 职权）在用；不再是「过渡」 |
| `ensure_reviewer_not_author()` | `ownership.py` | **职责分离**：须有审批角色且**不得是作者本人**（管理员不豁免）。方向与归属守卫**相反**——把归属规则套到审批上，放行的恰是「自己批自己」 |

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
| **守卫可能困在 docstring 里** | `DELETE /sops/{id}` 的守卫写在 docstring 内（`"""` 在其后才闭合），**从未执行**。文件确实改过、语法正确、文本里搜得到守卫名——**只是它在字符串里**。判据必须用 AST 比对函数体实际调用，关键字扫描无效 |
| **断言不变 ≠ 语义不变** | 草稿审批换成职责分离后，既有用例仍绿：那位教师正是作者，旧口径因「角色不足」403、新口径因「不得自批」403。**结果相同、理由已变**，注释因此失真 |
| **提问前先读完整段** | 就 `auth.register` 提请裁定时称「学生可挂靠任意教师」，实际同校约束早已存在（第 5 步）。裁定因此有一半落在空处 |

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

#### 董事会已裁定（2026-09-04，原话「采纳替代方案，豁免 DIR-07」）

| 项 | 裁定 |
|---|---|
| **AG-02 / M-AUD-06** | **`CLOSED_BY_ALTERNATIVE`**——以八轮对抗式复核记录替代，**明示接受的残余风险，不得记为「通过」** |
| **DIR-07 / M-DEC-02** | **已豁免**（路线 B 有效期内）——**仅豁免「代码改造须先有 R1 架构批准」这一顺序要求** |

**豁免的边界（接手须严格遵守）：**

- ✅ 豁免：改造无需等待 R1 架构批准；已执行的 9 批无需补依据、无需回退
- ❌ **未豁免**：E1 FAIL、E2/E3/E4 BLOCKED、生产启用 BLOCKED、`REL-BLOCK-01` 未清零——**一条未动**
- ❌ **未豁免**：每批改造仍须全量测试通过、留**行为级**回归测试、记录 `DEVELOPMENT_LOG`
- ❌ **未豁免**：DIR-01~06 其余六项方向要求继续适用

> **豁免的是流程顺序，不是质量标准，更不是安全门禁。**

裁定全文与「对外表述的硬性约束」见
[`docs/plans/2026-09-03-board-decision-suspend-certification-start-remediation-v0.1.0.md`](../plans/2026-09-03-board-decision-suspend-certification-start-remediation-v0.1.0.md) §7–§8。

**审计线到此正式收束。接手直接进入改造，按 §3 推进。**

### 董事会决策进展（2026-09-04 第二批裁定，见裁定文件 §9）

| # | 决策 | 裁定 | 落地 |
|---|---|---|---|
| 1 | 归属字段补不补、历史行 NULL 如何处置 | **补字段 + 迁移；NULL＝系统内置，仅 admin 可改** | ✅ 第 13 批 |
| 2 | 内存态 agent 端点如何处置 | **整体删除** | ✅ 第 11 批 |
| 3 | 是否 push 跑真实 CI | **push** | ✅ 已推送；**CI 结果仍需人工在 GitHub 查看**（本机无 `gh` CLI） |
| 4 | `auth.register` 的 `teacher_id` 自选 | **限同校 + 记审计** | ✅ 第 12 批（同校约束原已存在，本批补审计与行为级覆盖） |

### 仍需董事会先定方向

| # | 决策 | 阻断什么 |
|---|---|---|
| 1 | **「真实写工具」的范围与安全边界** | M-06 断点④——`execute_write_tool_stub` 明写「不触发外部 IO」，**「批准即生效」目前不成立** |
| 2 | 多机器人遥测是否现在做 | M-03 的数据过滤部分。当前是单 adapter 单遥测流，按机器人隔离属**新功能**（多 adapter + 订阅分发），不是补漏洞 |

### 不需等决策即可推进的 —— **已全部做完（截至第 18 批）**

接手时若想「继续改造」，请注意：**清单已空**。剩余各项要么已由董事会裁定维持现状，
要么属于新功能而非补漏洞。**不要为了有事做而改动**——本项目已有的教训是
「为统一而强行改」会制造新缺陷（见 §5）。

若要确认这一判断，用运行期扫描现算，勿引用本文档的历史数字：
载入真实 `main:app` 枚举 `APIRoute`，用 **AST 检查函数体的实际 Call 节点**
（关键字扫描会把困在 docstring 里的守卫算作生效——`DELETE /sops/{id}` 就发生过）。

**终态数字（第 18 批实测）**：自述业务身份的写端点 12→**2**，
且两者均有书面判定——`/agent/coordinate` 的 `user_id` 是字符串任务标识
（不落库、不参与授权，端点内有注释）；`/auth/register` 的 `teacher_id`
见裁定 §9-4（跨校已堵，同校自选为明示接受的残余风险 + 审计留痕）。

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
> 分支 `audit/phase3-auth-control-realtime`，**已推送至 origin**，已推进至第 14 批。
>
> **先读 `docs/handover/2026-09-04-remediation-phase-handover-v0.1.0.md`**，
> 重点 §1 恢复点与环境陷阱、§2 当前状态、§7 下一步。
>
> 现状：董事会已裁定路线 B（暂停审计认证链、接受 26 项问题清单、直接改造），
> 并于 2026-09-04 追加第二批裁定（裁定文件 §9）。
> **M-01、M-15 已关闭**；**M-02 口径由「已关闭」修正为「部分」**；
> M-03、M-06 仍为部分完成，精确剩余边界见 §3——**不得当作已关闭**。
>
> **分工**：Plan/监督/验收＝Claude，Task 实现＝Codex CLI
> （`codex exec --sandbox workspace-write --skip-git-repo-check "<任务书>"`，
> 任务书须含环境陷阱、验收标准、「不要 git commit」）。
>
> 环境：被审 worktree 无 `.env`，须
> `set -a; . /Users/xuhehong/Desktop/r-mos/r-mos-backend/.env; set +a` 且 `unset CORS_ORIGINS`、
> `export DEBUG=true`；解释器只有 `/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python`；
> **跑 pytest 不要额外传 `-q`**（会吞掉汇总行）。
> ~~跑完还原 knowledge_store~~ —— M-15 已关闭，不再需要。
>
> **务必读 §5「主审犯过的错」与 §6「测试固化的漏洞」**——那些坑很容易重踩，
> 其中「静态扫描漏 router 前缀」是主审判过别人成立、自己又犯的同一错误。
>
> 最新一条尤其要记：**守卫可能被困在 docstring 里从不执行**（`DELETE /sops/{id}` 即如此），
> 关键字扫描查不出来，必须用 AST 比对函数体的实际调用。
