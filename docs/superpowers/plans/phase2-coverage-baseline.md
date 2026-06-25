# Phase 2 Quality Hardening — 覆盖率基线

> 记录日期：2026-06-25
> 分支：quality-hardening-phase2
> 工具：pytest-cov>=5.0（后端）、@vitest/coverage-v8@2.1.9（前端）

## 说明

本文档记录 Phase 3 重构目标文件的覆盖率基线，供后续 Task 验证增量与门禁阈值设定。

- **后端行覆盖率**：使用 `r-mos-backend/scripts/coverage_godfiles.sh` 采集（`pytest --cov=app/api/v1/endpoints`）
- **前端行覆盖率**：使用 `npx vitest run --coverage --coverage.provider=v8` 采集，`% Lines` 列

## 6 个目标文件基线

| 文件 | 基线行覆盖率 | 目标 (Phase 3 完成后) | 说明 |
|------|------------|----------------------|------|
| `app/api/v1/endpoints/agent.py` | 67% | ≥ 80% | 后端 Agent 端点 |
| `app/api/v1/endpoints/training.py` | 79% | ≥ 85% | 后端 Training 端点 |
| `app/api/v1/endpoints/teaching.py` | 47% | ≥ 70% | 后端 Teaching 端点 |
| `src/pages/SOPMaintenancePage.tsx` | 53% | ≥ 70% | 前端 SOP 维护页 |
| `src/components/Viewer3D/Atom01Interactive.tsx` | 15% | ≥ 40% | 前端 ATOM-01 3D 交互组件 |
| `src/components/Maintenance/SOPPlayerAdjudicated.tsx` | 0% | ≥ 30% | 前端 SOP 播放器（已裁决） |

## 采集方法

### 后端覆盖率

```bash
bash r-mos-backend/scripts/coverage_godfiles.sh
```

输出：过滤 `endpoints/(agent|training|teaching).py` 行，读取 `% Cover` 列。

### 前端覆盖率

```bash
cd r-mos-frontend
npx vitest run \
  --coverage \
  --coverage.provider=v8 \
  --coverage.reporter=text \
  --coverage.include='src/pages/SOPMaintenancePage.tsx' \
  --coverage.include='src/components/Viewer3D/Atom01Interactive.tsx' \
  --coverage.include='src/components/Maintenance/SOPPlayerAdjudicated.tsx'
```

输出：读取 `% Lines` 列。

## 注意事项

- 后端 `agent.py` 在 `--cov-report=term-missing:skip-covered` 模式下曾被跳过（覆盖率很高行被隐藏），改用 `--cov-report=term-missing` 才显示 67%。
- 前端覆盖率采集需要 `@testing-library/dom`（已追加至 devDependencies）与 `@vitest/coverage-v8@2.1.9`（与 vitest@2.1.9 版本匹配）。
- `SOPPlayerAdjudicated.tsx` 当前 0% 是因为对应测试文件因环境依赖缺失未渲染，属正常基线（无测试覆盖）。
