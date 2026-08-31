# A0–A6 当前环境与漂移指纹

- 版本：0.1.0
- 采集时间：2026-08-31 08:24 CST
- 工作区：`/Users/xuhehong/Desktop/r-mos/.worktrees/phase3-auth-control-realtime`
- 分支：`audit/phase3-auth-control-realtime`
- 采集时 HEAD：`56751f5e959c60dac880f96db8b630ce73f8e75b`
- 历史事实基线 B-ASIS：`29d2a5889e3b320a3e777e3d8c19efbbe31c0294`
- 证据性质：当前只读快照；不能追溯补造 A0～A6 各阶段当时缺失的同期指纹
- 裁决：**PARTIAL**

## 1. Git 与漂移

现场命令：

```bash
pwd
git branch --show-current
git rev-parse HEAD
git status --short --branch
git rev-list --count 29d2a5889e3b320a3e777e3d8c19efbbe31c0294..HEAD
git diff --name-only 29d2a5889e3b320a3e777e3d8c19efbbe31c0294..HEAD | wc -l
```

结果：

- B-ASIS 到采集时 HEAD 共 31 个提交、81 个已提交文件发生变化；变化同时包含历史审计材料、R0 材料和后续应用点修，不能把当前 HEAD 倒写成原 A0–A6 的同期快照。
- 采集时另有本任务 13 个工作区状态条目：10 个已跟踪文件修改、3 个未跟踪路径；它们是实时通道复验、测试/审计记录及 R0 五域发现材料。
- 已提交的应用漂移至少包括 CI 配置、API 注册、WebSocket 入口和服务；当前未提交漂移又包含 WebSocket 慢连接隔离与教师监控日志真实性修复。
- 上述漂移已明确登记，但尚未逐项回填到 A1～A5 的全部历史精确分母，故 AG-05 只能记为 PARTIAL。

## 2. Python 依赖指纹

现场结果：

| 项目 | 值 |
|---|---|
| 解释器 | `/Users/xuhehong/Desktop/r-mos/r-mos-backend/venv/bin/python` |
| Python | 3.13.13（Anaconda build） |
| 平台 | macOS 26.0.1 arm64 |
| `pip freeze` 项数 | 84 |
| `pip freeze` SHA-256 | `756df7266b29e99a0f9941c7b97277534b408d8f8adf4257ba42b227be463925` |
| `requirements.txt` SHA-256 | `a0d75483af9a9a6f4761d7202d8969ac8151ba4c7f75698e9fdd6e8663a97439` |

`pip freeze` 只读取当前环境；它不能证明 A0～A6 各阶段使用了完全相同的环境。

## 3. Node 与前端依赖指纹

| 项目 | 值 |
|---|---|
| Node | v20.19.2 |
| npm | 10.8.2 |
| `package-lock.json` SHA-256 | `87888972373b95eb1a94aad1f56855eb2bf762c8c143009d8b41380ed79bf412` |
| 顶层 `npm ls --json` SHA-256 | `0a171fb1ac5c2154aa37f9dac5ae041042b7cc0f26b38e2250aa2684a1391cdc` |

本轮没有安装、升级或修复任何依赖。

## 4. 配置来源与脱敏指纹

隔离 worktree 内只有示例/演示配置，没有实际后端 `.env`。本轮测试实际读取主工作区：

`/Users/xuhehong/Desktop/r-mos/r-mos-backend/.env`

只记录哈希和字段名，不保存字段值：

- SHA-256：`348c2191e008c543fda7b87f002a316af09ec24852931fd5bec24065b9083495`
- 字段：`CORS_ORIGINS`、`DATABASE_URL`、`DEBUG`、`DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`LLM_ENABLE_MOCK_FALLBACK`、`LLM_TIMEOUT_SECONDS`、`LOG_LEVEL`、`ROBOT_MODE`、`SECRET_KEY`

这再次确认历史 `.env` 来源问题尚未消失：当前测试环境可以被固定，但不能证明它就是各阶段当时的被审 worktree 配置。配置项 AG-04 记为 PARTIAL。

## 5. 存储元数据指纹

只读取三个现有目录，不读取数据库、不启动服务：

| 路径 | 文件数/占用 |
|---|---|
| `r-mos-backend/data` | 与其余两目录合计 880 个文件；304 KiB |
| `r-mos-backend/storage` | 与其余两目录合计 880 个文件；100 KiB |
| `r-mos-frontend/public` | 与其余两目录合计 880 个文件；1,014,444 KiB |

三目录“路径 + 文件大小”清单 SHA-256 为 `3591751d378e6bebbff1879cebd257b1c2f06fe0eabd3590ee25832b452cb7bd`。这是元数据指纹，不是每个资产的内容哈希，也不能替代对象存储、挂卷或恢复证明。

## 6. 未取得的指纹

以下仍为 UNKNOWN / NOT RUN：

- PostgreSQL 版本、扩展、实际 schema、迁移头和关键数据同期摘要；
- 当前服务进程与运行时路由导出；
- 前端构建产物与浏览器可达入口；
- 生产、预生产、真实机器人、外部 AI 和对象存储；
- A0～A6 每个历史阶段当时的完整前后指纹。

## 7. 对门禁的影响

- AG-04：当前 Git、Python、Node、配置和本地存储元数据已补采，但数据库、运行路由、前端运行入口及历史同期复比仍缺，保持 **PARTIAL / BLOCKED**。
- AG-05：B-ASIS 到当前 HEAD 以及本任务未提交漂移已登记，尚未完成对 A1～A5 全部精确数字的逐项影响复算，保持 **PARTIAL / BLOCKED**。
- 本证据不改变 A0～A6 的 `RETURN FOR REVISION`，也不授权 R1。
