# Service Test Gap Baseline (T-01-4)

Date: 2026-03-05
Method: static mapping by service filename + test file/import references (no pytest-cov plugin).

- Core services scanned: 14
- Covered: 2
- Uncovered: 12

## Covered Core Services

- `app/services/approval_service.py`
  - `tests/unit/test_tool_execution_after_approval_api.py`
- `app/services/preflight_check.py`
  - `tests/unit/test_preflight_check.py`

## Uncovered Core Services

- `app/services/identity/agent_policy_factory.py`
- `app/services/identity/session_initializer.py`
- `app/services/identity/teacher_monitor.py`
- `app/services/intent/training_intent_router.py`
- `app/services/memory/skill_profile_service.py`
- `app/services/memory/training_memory_writer.py`
- `app/services/orchestrator_v2.py`
- `app/services/tool_executor.py`
- `app/services/training/feedback_generator.py`
- `app/services/training/project_generator.py`
- `app/services/training/session_service.py`
- `app/services/training/submission_service.py`
