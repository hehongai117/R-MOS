# ADR-FE-REDESIGN-001｜前端重构依赖与增量迁移策略

- 状态：Accepted
- 日期：2026-03-06
- 决策范围：`r-mos-frontend` 视觉重构（不包含后端接口新增）

## 背景

前端重构方案引入 `Tailwind CSS`、`shadcn/ui`、`@fontsource/*`、`motion` 等依赖，用于统一视觉语言与组件层样式能力。  
现有系统已存在 `Ant Design`、`react-router`、`zustand`、`three` 体系，且当前质量门禁（`tsc/lint/vitest/build`）已可通过，不能采用“推倒重来”。

同时，后端鉴权 token 为 opaque string，登录返回 `role/default_route`，前端不能依赖 JWT payload 解码做身份恢复。

## 决策

1. 采用“增量迁移”而非全量重写：保留 Ant Design 数据组件，新增 Tailwind + shadcn 仅用于布局与视觉层。
2. 鉴权对齐后端现状：以 `/api/v1/auth/login` 返回体作为身份来源，不做 JWT 解码。
3. 接口优先级：仅使用仓库内已存在的后端路由；缺失接口标记 `BACKLOG/TBD`，不在本轮前端方案中伪造“已实现”。
4. 质量门禁沿用现有 CI：`npx tsc --noEmit`、`npx eslint ... --max-warnings 0`、`npm test`、`npm run build`。

## 备选方案

### 方案 A：仅保留 Ant Design，不引入 Tailwind/shadcn

- 优点：依赖最少、迁移成本低
- 缺点：难以解决当前样式分散与视觉一致性问题

### 方案 B：全量替换为 shadcn/Tailwind（去除 Ant Design）

- 优点：风格统一度最高
- 缺点：重写范围过大，回归风险高，与当前“最小化改动”原则冲突

### 结论

采用“Ant Design 保留 + Tailwind/shadcn 增量接入”的折中方案。

## 影响评估

1. 依赖增加：构建体积和安装时间可能上升。
2. 样式体系切换：需要在迁移期并行维护 AntD Token 与 CSS Tokens。
3. 测试影响：视觉层改造会触发组件测试更新，必须同步补齐证据。
4. 运维影响：无需新增外部服务，不改变后端部署拓扑。

## 迁移策略

1. Phase 0：接口/鉴权对齐与已完成项去重（本轮）
2. Phase 1：令牌体系、鉴权上下文、路由重组
3. Phase 2：核心页面增量视觉改造（按页面逐个回归）
4. Phase 3：收尾清理与联调验证

每个阶段结束必须提供可复现命令与输出摘要，并落 `DEVELOPMENT_LOG.md`。

## 回滚策略

1. 样式回滚：单页面粒度回退到 Ant Design 现状样式，保持功能不变。
2. 依赖回滚：撤销对应页面/组件对新依赖的引用，删除未使用依赖。
3. 路由回滚：保留旧路由别名并恢复旧入口，避免用户导航中断。
4. 质量回滚门禁：回滚后必须重跑 `tsc/lint/test/build`，确保基线恢复。
