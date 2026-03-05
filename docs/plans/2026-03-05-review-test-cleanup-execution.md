# R-MOS Review Test Cleanup Execution Plan (Batch Mode)

> Source Plan: `R-MOS_Review_Test_Cleanup_Plan.md`
> Start Date: 2026-03-05
> Execution Rule: 逐项完成即标记、每批次可验证、全程可追溯

## 1. 执行原则

1. 每批次最多 3-6 项任务，完成后必须跑最小验证命令。
2. 每项完成后立即在源计划文档勾选（`[ ] -> [x]`）。
3. 每批次结束必须更新：
   - `docs/review/review-checklist.md`
   - `DEVELOPMENT_LOG.md`
4. 只在当前批次涉及文件做最小化改动。

## 2. 批次拆分

### Batch 1（已完成）

- Phase 0.5：F-01/F-02/F-03/F-04
- Phase 1：R-02-a-1/a-2/a-3/a-4
- Phase 1：R-02-b-1/b-2/b-3
- 阻塞项：R-04-3-a + T-03-b-0
- 产出：
  - `r-mos-backend/tests/conftest.py` fixture 基建
  - `r-mos-backend/tests/load/locustfile.py` 语法修复
  - `docs/review/review-checklist.md` 首版

### Batch 2（已完成）

- Phase 1：R-01-a（agent.py 72 端点审查）
- Phase 1：R-01-b（deprecated 端点调用/审计核查）
- Phase 1：R-01-c（training/teaching/tasks 重点审查）

### Batch 3（已完成）

- Phase 1：R-03-a~R-03-d（前端审查）✅ 已完成
- Phase 1：R-04-1/R-04-2（汇总与分级）✅ 已完成
- Phase 1：R-04-3（红色阻塞项即时修复）✅ 已完成

### Batch 4（已完成）

- Phase 2：T-01 基线测试收集与存量失败修复（T-01-1/2/3/4 ✅）
- Phase 2：T-02 核心 service 单测补全（T-02-a/b/c/d ✅）
- 产出：
  - 新增/补强核心 service 测试：`test_project_generator.py`、`test_session_service.py`、`test_submission_service.py`、`test_feedback_generator.py`
  - 新增/补强身份与权限测试：`test_session_initializer.py`、`test_agent_policy_factory.py`、`test_class_membership.py`
  - 新增/补强记忆与检索测试：`test_training_memory_writer.py`、`test_skill_profile_service.py`、`test_knowledge_hub.py`
  - 扩展 BLOCK 场景：`test_preflight_check.py`
  - 对剩余缺口服务补最小正常流：`test_teacher_monitor.py`、`test_training_intent_router.py`、`test_orchestrator_v2.py`、`test_tool_executor_service.py`

## 3. 每批次验收模板

- Commands Run（可复制）
- Output 摘要（PASS/FAIL + 关键日志）
- Diff Summary（文件清单 + 关键片段）
- Source Plan 勾选状态更新
- DEVELOPMENT_LOG 追加
