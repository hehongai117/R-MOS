# Chrome 手动测试 — 任务交接提示词

> 将以下内容粘贴到新对话窗口中，作为开场消息。

---

## 交接提示词

```
请执行 R-MOS 产品化 Chrome 手动测试计划。

## 背景

我们刚完成了 R-MOS 院校教培产品化的 14 个 Task 改造（分支: feat/phase1-2-fsm-evidence），现在需要用 Chrome 浏览器逐一验证所有功能。

## 测试计划文件

docs/superpowers/plans/2026-05-05-chrome-manual-test.md

这个文件包含 14 个测试 Task、100+ 个验证步骤，请严格按照文件中的步骤执行。

## 执行方式

使用 chrome-devtools MCP 工具操作浏览器。每个 Step：
1. 执行操作（navigate、click、fill、evaluate_script 等）
2. 截图验证结果
3. 记录 PASS / FAIL + 原因

## 启动前置

在开始测试前，必须先确保服务运行：

1. 启动后端：
   cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && source venv/bin/activate && python main.py

2. 启动前端：
   cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npm run dev

3. 运行种子数据（如果数据库是新的）：
   cd /Users/xuhehong/Desktop/r-mos/r-mos-backend
   python scripts/seed_acceptance_users.py
   python scripts/seed_demo_data.py
   python scripts/seed_fault_sops.py

4. 用 chrome-devtools 打开 http://localhost:5173

## 测试账号

| 角色 | 邮箱 | 密码 |
|------|------|------|
| 学生 A | student_a@rmos.test | Student@123 |
| 教师 | teacher1@rmos.test | Teacher@123 |
| 管理员 | admin@rmos.test | Admin@123 |

## 执行规则

- 从 Task 1 开始，按顺序执行到 Task 14
- 每完成一个 Task，汇报: ✅ Task N: [名称] — X/Y steps passed
- 如果有 FAIL 的步骤，记录具体失败原因和截图
- 每 4 个 Task 做一次进度汇总
- 遇到阻塞问题（如服务崩溃）暂停询问我
- 测试发现的 bug 记录但不修复，测试完成后统一处理

## 如果是中断恢复

如果之前已经执行了部分测试任务，请先读取测试计划文件，检查哪些 Task 的 checkbox 已被勾选（- [x]），从下一个未完成的 Task 继续。

开始吧。
```

---

## 补充说明

**项目位置:** `/Users/xuhehong/Desktop/r-mos`
**分支:** `feat/phase1-2-fsm-evidence`
**最新提交:** `1d193fa docs: add Chrome manual test plan (14 test tasks, 100+ steps)`

**产品化 14 Task 全部已完成（提交记录）：**

| # | Commit | Task |
|---|--------|------|
| 1 | 5a64ceb | 生产配置治理 |
| 2 | 8196c8b | 学生任务列表 API |
| 3 | ec0192a | 场景列表 API |
| 4 | e8202ca | AI 助手后端端点 |
| 5 | bfd8d41 | 前端导航分层 |
| 6 | 716fd22 | 学习进度仪表盘 |
| 7 | bd73bdc | MyTasksPage 补全 |
| 8 | 0b03f31 | ScenarioPickerPage 补全 |
| 9 | 3b29a4a | AI 助手前端浮窗 |
| 10 | 0b1e40f | AI 助手集成 SOPPlayer |
| 11 | a123f03 | Docker 部署方案 |
| 12 | 7f60e22 | 代码清理 + ROBOT_MODE 兼容 |
| 13 | 881c974 | 路由整合默认首页 |
| 14 | (冒烟测试通过，无额外提交) | 端到端冒烟测试 |

**关键技术细节（新对话可能需要）：**

- 后端 default_route 对学生返回 `/workbench/training`（auth.py:182），前端 fallback 改为 `/dashboard`
- config.py 中 `ROBOT_MODE="simulation"` 通过 `ROBOT_ADAPTER_TYPE` property 映射为 `"mock"` 给 adapter factory
- AI 助手 LLM 调用会降级到硬编码回复（如果没有配置 DEEPSEEK_API_KEY）
- 前端 Badge 组件支持 variant: default / success / destructive
- ScrollArea 在 AI 助手中替换为原生 div + overflow-y-auto（Radix ref 兼容问题）
