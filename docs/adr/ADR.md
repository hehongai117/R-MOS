# 架构决策记录

## ADR-TEACH-001
- 决策：使用 `EvidenceLink` 解耦教学域与执行域
- 背景：教学域不应直接依赖裁决域与任务执行细节
- 影响：证据生成可独立升级，教学域仅通过关联查询

## ADR-TEACH-002
- 决策：尝试状态机采用白名单流转
- 背景：避免前端或服务端出现非法回退
- 影响：非法状态流转返回 `INVALID_ATTEMPT_STATUS_TRANSITION`

## ADR-TEACH-003
- 决策：证据生成时机绑定任务完成钩子
- 背景：完成时最稳定地汇总事件与快照
- 影响：任务完成后自动生成 `EvidenceBundle` 与 `EvidenceLink`

## ADR-TEACH-004
- 决策：错误响应格式统一为结构化数据
- 背景：前端需稳定解析错误码与提示
- 影响：`BusinessRuleViolation` 与 `ResourceNotFoundError` 统一格式

## ADR-TEACH-005
- 决策：教学域数据结构输出驼峰命名
- 背景：前端字段命名与交互一致性
- 影响：启用 `populate_by_name=True` 支持下划线入参

## ADR-TEACH-006
- 决策：`metadata` 字段冲突采用别名策略
- 背景：`Base.metadata` 与业务字段冲突
- 影响：使用 `metadata_json` 内部字段，外部保持 `metadata`

## ADR-TEACH-007
- 决策：P0 诊断报告不落库，实时生成
- 背景：Phase2 P0 仅需 UI 展示诊断报告，避免引入新表或缓存一致性复杂度
- 影响：诊断报告每次请求即时生成；如需缓存，仅记录 TODO 不实现

## ADR-OPS-001
- 决策：`seed_teaching_demo.py` 默认禁止隐式建表
- 背景：避免脚本在默认 Postgres 上生成未迁移结构
- 影响：仅允许 `--bootstrap` 或 `ALLOW_BOOTSTRAP=1` 启用建表兜底

## ADR-OPS-002
- 决策：统一开发一键启动命令与前端依赖诊断流程
- 背景：降低环境差异导致的启动失败与排障成本
- 影响：新增 `make dev/dev-backend/dev-frontend` 作为标准入口
