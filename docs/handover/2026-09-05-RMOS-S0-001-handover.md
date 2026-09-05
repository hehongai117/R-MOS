# R-MOS 新窗口交接记录（RMOS-S0-001）

> 本文件只保存恢复细节。项目方向、当前阶段和唯一下一步以
> [R-MOS 项目主干](../governance/RMOS_PROJECT_MAINLINE.md)为准。

- 日期：2026-09-05
- 交接原因：S0-001 交付物已提交，等待董事会准确口令

## 1. 主干定位

- 主干任务编号：**RMOS-S0-001**
- 当前阶段：**S0｜统一现状**，阶段状态 **IN PROGRESS**
- 本次批准范围：统一现行状态、冻结整改后的当前基线、生成唯一的当前问题清单
- 完成条件：主干 §3 的 S0 四项通过条件——前三项由执行者达成，
  **第四项「董事会确认唯一下一步」只有董事会能完成**

## 2. 精确现场

- 工作区绝对路径：`/Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime`
  （git worktree，**不是主仓**）
- 分支：`audit/phase3-auth-control-realtime`
- HEAD：`cb00b293303ae9df61f9d496b37f1fdbf2a7e9f0`
- `git status --short`：**空（clean）**
- 是否 push：**是**，与 `origin/audit/phase3-auth-control-realtime` 同步，未 push 提交数 0
- 使用的环境或服务：
  - Python 解释器 `/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python`（**唯一**，本 worktree 无 venv）
  - 本地 PostgreSQL `localhost:5432/rmos`，Alembic head `20260904_m02_ownership`（单一 head）
  - 本 worktree **无 `.env`**（worktree 不共享未跟踪文件），须从主仓加载

### 2.1 环境陷阱（每次运行都要）

```bash
cd /Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime/r-mos-backend
set -a; . /Users/xuhehong/Desktop/r-mos/r-mos-backend/.env; set +a
unset CORS_ORIGINS        # 该字段以环境变量形态存在时不是 JSON，pydantic-settings 拒绝解析
export DEBUG=true         # 否则 validate_production() 拒绝启动
/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python -m pytest -p no:warnings
```

- **不要额外传 `-q`**：`pytest.ini` 已有 `addopts = -q`，再传变 `-qq`，汇总行消失
- **不要传 `--timeout`**：未装 `pytest-timeout`
- Codex 沙箱禁止连 `::1:5432`，其报告恒有 3 项 DB 门禁失败（属环境限制）；
  **涉及 Alembic 实迁的验证必须在本机复跑**

## 3. 已完成

- 完成内容：**RMOS-S0-001 交付物**
  `docs/governance/RMOS-S0-001-current-state-unification-v0.1.0.md`，
  按主干 §2 要求的五项逐项提交
- 验证结果：
  - 后端 **995 passed**；前端 **518 passed / 2 skipped**；`tsc --noEmit` 无错误
  - 问题清单分类经**脚本校验**：26 个 Master_ID 各归一类，无重复、无遗漏
  - Alembic 单一 head，迁移 upgrade→downgrade→upgrade 已在本机 PG 实测
- 证据路径：
  - 异源取证 `docs/audit/evidence/2026-09-05-b-asis-to-head-drift-recomparison-v0.1.0.md`（Codex 执行）
  - 改造过程 `docs-archive/DEVELOPMENT_LOG.md`（倒序读最后若干条）
- 本地提交：`cb00b293`（S0-001 交付物）、`27df7c52`（前端悬空调用修复）
- 是否 push：**是**

## 4. 未完成与新问题

- 未完成项：**S0 第四项通过条件**——董事会尚未以准确口令确认
- 新发现问题（均由异源复比抓出，非主审自查）：
  1. **本轮改造自身造成的退化**：第 11 批删 `/agent/v2/task*` 后端路由时，
     漏删 task 的 3 个前端函数，前端悬空调用 15→21 条。**已修**（`27df7c52`）
  2. **`M-15` 编号指代两件事**：A6 台账是「运行期本地文件未纳入持久卷」，
     前一窗口交接文档用它指「测试污染」。第 14 批记为「M-15 关闭」口径错误，
     **已更正**，M-15 归回「仍存在」
- 当前阻断：无技术阻断；唯一阻断是**等待董事会准确口令**
- 是否涉及安全、权限、数据或机器人风险：
  **本次交接不引入新风险**。既有风险见 S0-001 §2.4 的四项明示接受残余风险
  （AG-02 替代关闭、A0 G05 无备用 P0 渠道、`auth.register` 同校自选、M-06 断点④）

### 4.1 本轮**未执行**的事项（重要，勿误接手）

用户曾提出「结束 A0–A6，继续 R0、R1」。按主干 §5 任务准入第 3 项，
A0–A6 定向重开（7 条口令）、AG-03 P0 主备通道补证、R0 的 G2/G5 取证
**均对应不上主干任务编号，因此一件未做**，登记为 S0-001 §3 冲突 C1。

**A0–A6 是暂停不是撤销。** 若材料需对外用于投标、尽调、认证或合规，
按路线 B 裁定 §4 须从 AG-02 重启认证链；届时本基线与问题清单可直接作为
重开输入，不必重做。

## 5. 唯一下一步

- 从主干复制的唯一下一步：
  **S0-01：统一现行状态，冻结整改后的当前基线，并生成唯一的当前问题清单**
- 下一条可执行动作：**无执行者动作**。交付物已提交，等董事会回复准确口令：

  ```text
  确认主干阶段 S0 完成，进入 S1
  ```

  > **不得用「继续」「确认，继续」或本交接自述替代准确口令**——
  > A0–A6 的 AG-01 被判为批准链缺失，原因正是如此。
- 完成后需提交董事会的内容：已在 `RMOS-S0-001-...-v0.1.0.md` §4、§5 提交完毕

## 6. 新窗口固定提示词

```text
完整读取 docs/governance/RMOS_PROJECT_MAINLINE.md。
现场核对本交接记录中的工作区、分支、HEAD 和 git status。
只执行主干中的唯一下一步；交接文件与主干冲突时，以主干为准并停止报告差异。
保护所有既有未提交内容，不从历史对话反推当前状态。
```

## 7. 交接自检

- [x] 主干文件已完整读取
- [x] 工作区、分支、提交和状态已现场核对（`git branch --show-current` / `rev-parse HEAD` / `status --short` 实跑）
- [x] 本交接没有自行改变当前阶段（仍为 S0 IN PROGRESS）
- [x] 本交接没有复制另一套项目总状态（问题清单只在 S0-001 交付物中，本文件仅引用）
- [x] 唯一下一步与主干一致（逐字复制自主干 §2）
