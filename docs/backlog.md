# R-MOS Backlog

> Updated: 2026-03-05  
> Source: `docs/review/review-checklist.md` §2 `[延后]`（R-02-a-2）  
> Migration: C-01-c-3（已从 `r-mos-backend/app` 源码移除 TODO/FIXME 注释）  
> Note: R-02-a-2 原 `[延后]` 24 条中，`project_generator` 的 “MemoryHub 实数据接入” 已在前序批次闭环，本页保留 23 条未完成项。

## Open Items

| ID | Area | File | Description | Status |
| --- | --- | --- | --- | --- |
| BL-20260305-01 | tasks | `r-mos-backend/app/api/v1/endpoints/tasks.py` | 补全 `robot_id` 来源（SOP 或其他上下文） | OPEN |
| BL-20260305-02 | identity | `r-mos-backend/app/services/identity/session_initializer.py` | 写入 Redis 会话摘要（`session:{user_id}`，TTL 8h） | OPEN |
| BL-20260305-03 | identity | `r-mos-backend/app/services/identity/session_initializer.py` | 从 Redis 读取预计算推荐 | OPEN |
| BL-20260305-04 | identity | `r-mos-backend/app/services/identity/session_initializer.py` | 活跃会话查询切换到 Redis | OPEN |
| BL-20260305-05 | identity | `r-mos-backend/app/services/identity/session_initializer.py` | 待处理 incidents 统计改为真实查询 | OPEN |
| BL-20260305-06 | identity | `r-mos-backend/app/services/identity/teacher_monitor.py` | teacher 频道订阅维护 | OPEN |
| BL-20260305-07 | intent | `r-mos-backend/app/services/intent/training_intent_router.py` | 使用 LLM 提取参数（场景一） | OPEN |
| BL-20260305-08 | intent | `r-mos-backend/app/services/intent/training_intent_router.py` | 读取 `student_weak_steps` 薄弱步骤 | OPEN |
| BL-20260305-09 | intent | `r-mos-backend/app/services/intent/training_intent_router.py` | LLM 参数提取 + 前置条件校验（场景二） | OPEN |
| BL-20260305-10 | intent | `r-mos-backend/app/services/intent/training_intent_router.py` | `skill_profile` 查询接入 | OPEN |
| BL-20260305-11 | intent | `r-mos-backend/app/services/intent/training_intent_router.py` | `assignment_id` 文本提取与数据库验证 | OPEN |
| BL-20260305-12 | intent | `r-mos-backend/app/services/intent/training_intent_router.py` | `assignments` 表真实查询 | OPEN |
| BL-20260305-13 | intent | `r-mos-backend/app/services/intent/training_intent_router.py` | 使用 LLM 提取 `category` | OPEN |
| BL-20260305-14 | memory | `r-mos-backend/app/services/memory/training_memory_writer.py` | 对话摘要写入情景记忆 | OPEN |
| BL-20260305-15 | memory | `r-mos-backend/app/services/memory/training_memory_writer.py` | 推荐预计算写入缓存 | OPEN |
| BL-20260305-16 | sop | `r-mos-backend/app/services/sop/quality_monitor.py` | 未处理审核工单检测逻辑 | OPEN |
| BL-20260305-17 | sop | `r-mos-backend/app/services/sop/quality_monitor.py` | 工单创建逻辑 | OPEN |
| BL-20260305-18 | training | `r-mos-backend/app/services/training/feedback_generator.py` | `tools_confirmed` 评分细化 | OPEN |
| BL-20260305-19 | training | `r-mos-backend/app/services/training/project_generator.py` | `intent -> mode` 映射规则 | OPEN |
| BL-20260305-20 | training | `r-mos-backend/app/services/training/submission_service.py` | 教师管辖权验证 | OPEN |
| BL-20260305-21 | training | `r-mos-backend/app/services/training/submission_service.py` | 学员通知推送 | OPEN |
| BL-20260305-22 | training | `r-mos-backend/app/services/training/submission_service.py` | `conversation_summary` 补全 | OPEN |
| BL-20260305-23 | training | `r-mos-backend/app/services/training/submission_service.py` | `interaction_log` 补全 | OPEN |
