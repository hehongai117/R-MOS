# R-MOS

R-MOS（Robot Maintenance Operating System）仓库。
本项目的可交付与可复现入口已统一收口，避免多入口漂移。

## 入口索引（唯一事实源）

- `docs/ops/RUNBOOK.md`
- `docs/testing/TEST_REPORT.md`
- `docs/testing/TEST_PLAN.md`
- `docs/adr/ADR.md`
- `DEVELOPMENT_LOG.md`

## 目录说明（当前有效）

- `r-mos-backend/`
  - 后端服务与测试代码（FastAPI + pytest）。
- `r-mos-frontend/`
  - 前端应用与测试代码（Vite + React + Vitest）。
- `docs/`
  - 当前有效文档（计划、评审、测试、运维、ADR）。
- `docs-archive/`
  - 历史归档文档，仅作追溯参考；不作为当前实施事实源。
- `logs/`
  - 本地运行日志目录，已在 `.gitignore` 中忽略，不纳入版本管理。
- `开源机器人/`
  - 第三方开源机器人资料（CAD/安装指南/外部仓库快照），与 `r-mos-backend/`、`r-mos-frontend/` 业务代码隔离，不参与构建与发布。
