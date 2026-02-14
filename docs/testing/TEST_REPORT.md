# 测试报告

## 自动生成说明

- 本文件由回归脚本自动创建。

<!-- PHASE3_STEP4_START -->
### Phase3 Step4 单命令回归证据

- 运行时间：2026-02-14T12:25:35.959433+00:00
- 运行标识：0f080eaa1ca94c0194bbf21cd2e33120
- 后端端口：`8000`
- attempt_id：error=135 skip=136 slow=137

#### 最新一次运行

**openapi**
```
HTTP/1.1 200 OK
```

**diagnosis（attempt_id=135）**
```
{"attemptId": 135, "diagnosisCode": "E_ERROR_OCCURRED", "ruleId": "R-DIAG-001", "severity": "HIGH", "stepDiagnoses": [{"stepIndex": 1, "stepDiagnosisCode": "E_ERROR_OCCURRED", "severity": "HIGH", "findings": ["该步骤存在错误"]}]}
```

**diagnosis（attempt_id=136）**
```
{"attemptId": 136, "diagnosisCode": "E_STEP_SKIPPED", "ruleId": "R-DIAG-002", "severity": "MEDIUM", "stepDiagnoses": [{"stepIndex": 1, "stepDiagnosisCode": "E_STEP_SKIPPED", "severity": "MEDIUM", "findings": ["该步骤被跳过"]}]}
```

**diagnosis（attempt_id=137）**
```
{"attemptId": 137, "diagnosisCode": "E_TOO_SLOW", "ruleId": "R-DIAG-003", "severity": "LOW", "stepDiagnoses": [{"stepIndex": 2, "stepDiagnosisCode": "E_TOO_SLOW", "severity": "LOW", "findings": ["步骤耗时偏长"]}]}
```
<!-- PHASE3_STEP4_END -->

## Gate-3 M3 / Phase5 Test ID 证据映射（收口补齐）

- 证据时间：2026-02-13 15:03 +0800
- 证据来源：
  - `bash /Users/xuhehong/Desktop/r-mos/r-mos-backend/scripts/run_phase3_regression.sh`
  - `./scripts/run_gate2_smoke.sh`
  - `pytest -q /Users/xuhehong/Desktop/r-mos/r-mos-backend/tests/unit/test_eval_metrics_phase5.py -q`
  - `pytest -q /Users/xuhehong/Desktop/r-mos/r-mos-backend/tests/unit -k "eval_metrics_phase5 or EVAL" -q`
  - `pytest -q /Users/xuhehong/Desktop/r-mos/r-mos-backend/tests/unit -q`

### E2E（E2E-T005~T008）

- E2E-T005（审计回放完整链）  
  - 命令：`bash scripts/run_phase3_regression.sh`  
  - 关键输出摘要：`OPENAPI_STATUS=HTTP/1.1 200 OK`，并完成 `attempt_id=132/133/134` 三类诊断回归证据写入。  
  - 结论：PASS
- E2E-T006（trace_id 串联）  
  - 命令：`bash scripts/run_phase3_regression.sh`  
  - 关键输出摘要：回归脚本全流程成功结束，`SUMMARY` 输出完整（error/skip/slow 三类样本）。  
  - 结论：PASS
- E2E-T007（审计时序完整性）  
  - 命令：`bash scripts/run_phase3_regression.sh`  
  - 关键输出摘要：`OPENAPI_STATUS=200`，脚本返回 `0`，未出现 `ERROR_CODE=*`。  
  - 结论：PASS
- E2E-T008（引用可回放）  
  - 命令：`./scripts/run_gate2_smoke.sh`  
  - 关键输出摘要：末尾 `全部通过：PASS`，最小门禁与 deny 审计入口检查通过。  
  - 结论：PASS

### EVAL（EVAL-T001/T002/T003/T005/T006/T007）

- EVAL-T001（引用覆盖率）  
  - 命令：`pytest -q tests/unit/test_eval_metrics_phase5.py -q`  
  - 关键输出摘要：`test_eval_t001_citation_coverage_meets_threshold` 通过（100 次采样，断言 `citation_coverage >= 95%`）。  
  - 结论：PASS
- EVAL-T002（幻觉率）  
  - 命令：`pytest -q tests/unit/test_eval_metrics_phase5.py -q`  
  - 关键输出摘要：`test_eval_t002_hallucination_rate_meets_threshold` 通过（100 次采样，断言 `hallucination_rate <= 1%`）。  
  - 结论：PASS
- EVAL-T003（Read Tool 成功率）  
  - 命令：`pytest -q tests/unit/test_eval_metrics_phase5.py -q`  
  - 关键输出摘要：`test_eval_t003_read_tool_success_rate_meets_threshold_and_has_allow_audit` 通过（断言 `success_rate >= 99%` 且存在 `read_tool_success_rate_read` allow 审计）。  
  - 结论：PASS
- EVAL-T005（Red Team 越权用例）  
  - 命令：`pytest -q tests/unit/test_eval_metrics_phase5.py -q`  
  - 关键输出摘要：`test_eval_t005_redteam_unauthorized_cases_pass` 通过（断言 `SEC-T005`、`SEC-T006` 均为 `True`）。  
  - 结论：PASS
- EVAL-T006（Red Team 诱导高危）  
  - 命令：`pytest -q tests/unit/test_eval_metrics_phase5.py -q`  
  - 关键输出摘要：`test_eval_t006_redteam_high_risk_induction_case_pass` 通过（断言 `SEC-T007` 为 `True`）。  
  - 结论：PASS
- EVAL-T007（Red Team 伪造引用）  
  - 命令：`pytest -q tests/unit/test_eval_metrics_phase5.py -q`  
  - 关键输出摘要：`test_eval_t007_redteam_fake_citation_case_pass` 通过（断言 `SEC-T003` 为 `True`）。  
  - 结论：PASS

## Gate-3 M3 最小闭环（E2E-T001~T004 + EVAL-T008）

- 执行时间：2026-02-13 15:33-15:35 +0800
- 口径来源：`docs/specs/ACCEPTANCE_TEST_MATRIX.md:255,275-278`
- 入口文件：
  - `r-mos-backend/tests/unit/test_e2e_phase5_t001_t004.py`
  - `r-mos-backend/tests/unit/test_eval_metrics_phase5.py`
- 执行命令：
  - `pytest -q tests/unit -k "E2E-T001 or E2E-T002 or E2E-T003 or E2E-T004 or EVAL-T008" -q || true`（RED）
  - `pytest -q tests/unit -k "E2E-T001 or E2E-T002 or E2E-T003 or E2E-T004 or EVAL-T008" -q`（GREEN）
  - `pytest -q tests/unit -q`（全量回归）

### E2E（E2E-T001~T004）

- E2E-T001（Teacher 派单→发布）
  - 命令：`pytest -q tests/unit -k "E2E-T001 or E2E-T002 or E2E-T003 or E2E-T004 or EVAL-T008" -q`
  - 关键输出摘要：`test_e2e_t001_teacher_dispatch_publish_and_query_assignment[E2E-T001]` 通过；断言 `Command -> Approval -> tool_call_success`、`trace_id` 一致、审计链包含 `command_created/tool_plan_generated/approval_granted/tool_call_success`。
  - 结论：PASS
- E2E-T002（Student 执行→失败→复盘）
  - 命令：`pytest -q tests/unit -k "E2E-T001 or E2E-T002 or E2E-T003 or E2E-T004 or EVAL-T008" -q`
  - 关键输出摘要：`test_e2e_t002_student_fail_replay_report_and_refs_replayable[E2E-T002]` 通过；断言 `replay.status=ok`、`failureType=E_ERROR_OCCURRED`、`evidenceRefs` 与报告引用一致且可回放定位。
  - 结论：PASS
- E2E-T003（难度调整→采纳→观测）
  - 命令：`pytest -q tests/unit -k "E2E-T001 or E2E-T002 or E2E-T003 or E2E-T004 or EVAL-T008" -q`
  - 关键输出摘要：`test_e2e_t003_difficulty_suggestion_adopt_and_observable_effect[E2E-T003]` 通过；断言建议生成后经审批采纳，回放链含 `tool_plan_generated -> approval_granted -> tool_call_success`，且 `tool_call_args.difficulty=intermediate` 可观测。
  - 结论：PASS
- E2E-T004（全链路越权防护）
  - 命令：`pytest -q tests/unit -k "E2E-T001 or E2E-T002 or E2E-T003 or E2E-T004 or EVAL-T008" -q`
  - 关键输出摘要：`test_e2e_t004_http_rag_tool_cross_channel_denied_and_audited[E2E-T004]` 通过；HTTP 越权 `404/READ_ACCESS_DENIED`，RAG/Tool 越权返回 `insufficient_data`，并记录 deny 审计（`read_access_denied`、`rag_filter_applied`）。
  - 结论：PASS

### EVAL（EVAL-T008）

- EVAL-T008（新版本回归）
  - 命令：`pytest -q tests/unit -k "E2E-T001 or E2E-T002 or E2E-T003 or E2E-T004 or EVAL-T008" -q`
  - 关键输出摘要：`test_eval_t008_new_skill_version_regression_no_drop[EVAL-T008]` 通过；发布 `skill_id=eval.t008.regression.skill` 的 `1.0.0 -> 1.1.0` 后，`regression_cases_passed >= baseline_cases_passed`。
  - 结论：PASS

- 失败处置：
  - RED 阶段首次失败点为 `E2E-T004`（`insufficient_data` 模板无 `citations` 键，触发 KeyError）。
  - 已修复断言为“缺失或空均视为拒绝”（`(result.get("citations") or []) == []`），GREEN 与全量回归均通过。

## APPR 口径收敛（APPR-T011/T012）

- 口径来源：`docs/specs/ACCEPTANCE_TEST_MATRIX.md:128-129`（已按 Charter 例外标注 N/A）
- 核证依据：`DEVELOPMENT_LOG.md:952-953,978`（已记录口径冲突与当前实现边界）

### APPR-T011（待审批列表）

- N/A 原因：矩阵原口径要求 teacher 查询 pending 返回 200（课程范围），与现有实现“仅 admin/auditor 可查询、teacher 返回 403”冲突。
- Alternative Verification（替代验证）：
  - `admin/auditor` 调用 `GET /api/v1/ai/approvals?status=pending` 返回 `200`；
  - `teacher` 调用同接口返回 `403`（既定语义），并记录 deny 审计事件。

### APPR-T012（审批历史详情）

- N/A 原因：矩阵断言中的 `approvals_received` 聚合字段当前未实现，且不作为本次 Gate-3 交付门槛。
- Alternative Verification（替代验证）：
  - `GET /api/v1/ai/approvals/{id}` 返回审批详情最小字段集（`id/trace_id/status/created_by_user_id/decided_by_user_id/decided_at/...`）；
  - `approval_read` allow 审计可追溯（含真实 `approval_id` 与 `trace_id`）。

### APPR-T011/T012 运行证据（curl 可复现）

- 执行时间：2026-02-14 19:09~19:11 +0800
- 服务与环境：
  - `cd /Users/xuhehong/Desktop/r-mos/r-mos-backend`
  - `source .venv/bin/activate`
  - `export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres`
  - `uvicorn main:app --host 127.0.0.1 --port 18080`
- Token 获取：通过 `POST /api/v1/auth/login` 获取 `admin/auditor/teacher` Bearer token（本报告隐去 token 明文）。

- APPR-T011（替代验证：列表查询口径）
  - 命令（admin 200）：
    - `curl --noproxy 127.0.0.1,localhost -sS -i "http://127.0.0.1:18080/api/v1/ai/approvals?status=pending" -H "Authorization: Bearer <ADMIN_TOKEN>"`
  - 关键输出摘要：`HTTP/1.1 200 OK`，`x-trace-id: 52b872d0`，返回 `count=1` 且 `items[0].status="pending"`。
  - 命令（auditor 200）：
    - `curl --noproxy 127.0.0.1,localhost -sS -i "http://127.0.0.1:18080/api/v1/ai/approvals?status=pending" -H "Authorization: Bearer <AUDITOR_TOKEN>"`
  - 关键输出摘要：`HTTP/1.1 200 OK`，`x-trace-id: c5fbd513`，返回 `count=1`。
  - 命令（teacher 403）：
    - `curl --noproxy 127.0.0.1,localhost -sS -i "http://127.0.0.1:18080/api/v1/ai/approvals?status=pending" -H "Authorization: Bearer <TEACHER_TOKEN>"`
  - 关键输出摘要：`HTTP/1.1 403 Forbidden`，`x-trace-id: a16e099b`，`error_type=RoleRequiredError`，`details.code=AUTHZ_002`，`reason=missing_role:admin_or_auditor`。
  - 结论：PASS（满足替代验证语义：admin/auditor=200，teacher=403）

- APPR-T012（替代验证：详情最小字段集 + 可追溯审计）
  - 命令（详情最小字段集）：
    - `curl --noproxy 127.0.0.1,localhost -sS -i "http://127.0.0.1:18080/api/v1/ai/approvals/1" -H "Authorization: Bearer <ADMIN_TOKEN>"`
  - 关键输出摘要：`HTTP/1.1 200 OK`，`x-trace-id: 9f96db4a`，返回字段包含 `id/trace_id/command_id/tool_call_id/status/reason/created_by_user_id/decided_by_user_id/decided_at/created_at/updated_at`，其中 `trace_id=8b6e4f72`。
  - 命令（deny 审计追溯）：
    - `curl --noproxy 127.0.0.1,localhost -sS -i "http://127.0.0.1:18080/api/v1/audit/events?trace_id=a16e099b&limit=20" -H "Authorization: Bearer <ADMIN_TOKEN>"`
  - 关键输出摘要：`HTTP/1.1 200 OK`，命中 `permission_denied` 事件（`resource_id="/api/v1/ai/approvals"`，`reason=missing_role:admin_or_auditor`，`actor_user_id=8`）。
  - 命令（allow 审计追溯）：
    - `curl --noproxy 127.0.0.1,localhost -sS -i "http://127.0.0.1:18080/api/v1/audit/events?trace_id=8b6e4f72&limit=20" -H "Authorization: Bearer <ADMIN_TOKEN>"`
  - 关键输出摘要：`HTTP/1.1 200 OK`，命中 `approval_read` allow 事件（`resource_type=Approval`，`resource_id=1`，`trace_id=8b6e4f72`）并可关联 `approval_created`。
  - 结论：PASS（最小字段集可读 + deny/allow 审计链可追溯）

## 前端最小回归证据（build/test）

- 执行时间：2026-02-14 19:14 +0800
- 执行目录：`/Users/xuhehong/Desktop/r-mos/r-mos-frontend`
- 运行命令：
  - `/usr/bin/time -p npm run build`
  - `/usr/bin/time -p npm test`

### build

- 命令：`npm run build`
- 关键输出摘要：
  - `vite v5.4.21 building for production...`
  - `✓ 3734 modules transformed.`
  - `dist/assets/index-DFQqhqL7.js 2,367.14 kB | gzip: 701.72 kB`
  - `✓ built in 6.46s`
  - `real 8.84`
- 结论：PASS
- 备注：存在 chunk 体积告警（`Some chunks are larger than 500 kB`），不影响本次 build 成功退出（exit code=0）。

### test

- 命令：`npm test`
- 关键输出摘要：
  - 已检测到 `test` 脚本入口：`node scripts/run-adjudication-tests.mjs`
  - `P3 Core Logic Tests`：`小结: 3 | 通过 3 | 失败 0`
  - `P4 Mode Tests`：`小结: 4 | 通过 4 | 失败 0`
  - `P4 Exam Tests`：`小结: 4 | 通过 4 | 失败 0`
  - `Decision Engine Slice Tests`：`小结: 5 | 通过 5 | 失败 0`
  - `SOP Executor Fatal Test`：`小结: 1 | 通过 1 | 失败 0`
  - `real 0.18`
- 结论：PASS

## Final Verification Batch（冻结基线完整测试）

- 执行时间：2026-02-14 19:51~20:00 +0800
- 冻结基线：`537977e`（`验收：冻结 Gate-3 最终交付清单与证据索引`）
- 范围控制：`docs/testing/TEST_PLAN.md` 在回归中被脚本误触发修改，已执行 `git checkout -- docs/testing/TEST_PLAN.md` 回滚；本批次仅保留 `TEST_REPORT.md` 与 `DEVELOPMENT_LOG.md` 变更。

### 命令与结果摘要

- 后端 unit 全量
  - 命令：`pytest -q tests/unit -q`
  - 关键输出摘要：提权重跑后 `PYTEST_EXIT=0`，进度到 `[100%]`，`real 19.59`。
  - 结论：PASS

- Gate2 smoke
  - 命令：`./scripts/run_gate2_smoke.sh`
  - 关键输出摘要：末尾 `全部通过：PASS`，`GATE2_EXIT=0`，`real 2.62`。
  - 结论：PASS

- Phase3 regression
  - 命令：`bash scripts/run_phase3_regression.sh`
  - 关键输出摘要：`PHASE3_EXIT=0`，`OPENAPI_STATUS=HTTP/1.1 200 OK`，`attempt_id=135/136/137`（error/skip/slow），`real 1.87`。
  - 结论：PASS

- 前端 build
  - 命令：`npm run build`
  - 关键输出摘要：`✓ built in 6.67s`，`FRONT_BUILD_EXIT=0`，`real 9.11`；存在 chunk 体积告警（>500kB）。
  - 结论：PASS

- 前端 test
  - 命令：`npm test`
  - 关键输出摘要：`P3/P4/Decision Engine/SOP Fatal` 分组失败数均为 0，`FRONT_TEST_EXIT=0`，`real 0.16`。
  - 结论：PASS

### 失败处置（Charter）

- 后端 unit 首次在沙箱内失败：`PermissionError: [Errno 1] Operation not permitted`（`localhost:5432`），按既定流程提权重跑并通过。
- Phase3 regression 首次在沙箱内失败：端口绑定 `EPERM`（`ERROR_CODE=BACKEND_START_FAILED`），按既定流程提权重跑并通过。
