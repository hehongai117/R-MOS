# 测试报告

## 自动生成说明

- 本文件由回归脚本自动创建。

<!-- PHASE3_STEP4_START -->
### Phase3 Step4 单命令回归证据

- 运行时间：2026-03-06T04:20:06.774229+00:00
- 运行标识：c979ee4cae194bc6b0fd5a11a2cd82ed
- 后端端口：`8000`
- attempt_id：error=145 skip=146 slow=147

#### 最新一次运行

**openapi**
```
HTTP/1.1 200 OK
```

**diagnosis（attempt_id=145）**
```
{"attemptId": 145, "diagnosisCode": "E_ERROR_OCCURRED", "ruleId": "R-DIAG-001", "severity": "HIGH", "stepDiagnoses": [{"stepIndex": 1, "stepDiagnosisCode": "E_ERROR_OCCURRED", "severity": "HIGH", "findings": ["该步骤存在错误"]}]}
```

**diagnosis（attempt_id=146）**
```
{"attemptId": 146, "diagnosisCode": "E_STEP_SKIPPED", "ruleId": "R-DIAG-002", "severity": "MEDIUM", "stepDiagnoses": [{"stepIndex": 1, "stepDiagnosisCode": "E_STEP_SKIPPED", "severity": "MEDIUM", "findings": ["该步骤被跳过"]}]}
```

**diagnosis（attempt_id=147）**
```
{"attemptId": 147, "diagnosisCode": "E_TOO_SLOW", "ruleId": "R-DIAG-003", "severity": "LOW", "stepDiagnoses": [{"stepIndex": 2, "stepDiagnosisCode": "E_TOO_SLOW", "severity": "LOW", "findings": ["步骤耗时偏长"]}]}
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

## Step-2｜Batch-1 全集回归（2026-02-15）

- 执行时间：2026-02-14 22:52 ~ 2026-02-15 09:07 +0800
- 执行目标：按统一口径执行后端 unit、Gate2 smoke、Phase3 regression、前端 build/test。
- 固定约束：`.venv`、`DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres`、未修改 CORS/代理规则。

### 命令结果（退出码 + 关键输出 + 耗时）

- 后端 unit（首轮沙箱）
  - 命令：`pytest -q tests/unit -q`
  - 退出码：`1`
  - 关键输出：`PermissionError: [Errno 1] Operation not permitted`（连接 `localhost:5432`）
  - 耗时：`DURATION_SEC=21`（`real 20.71`）
- 后端 unit（提权重跑）
  - 命令：`pytest -q tests/unit -q`
  - 退出码：`0`
  - 关键输出：`.......................................................................  [100%]`
  - 耗时：`DURATION_SEC=21`（`real 20.15`）

- Gate2 smoke
  - 命令：`./scripts/run_gate2_smoke.sh`
  - 退出码：`0`
  - 关键输出：`全部通过：PASS`
  - 耗时：`DURATION_SEC=3`（`real 2.80`）

- Phase3 regression（首轮沙箱）
  - 命令：`bash scripts/run_phase3_regression.sh`
  - 退出码：`10`
  - 关键输出：`ERROR_CODE=BACKEND_START_FAILED`，端口绑定 `EPERM`
  - 耗时：`DURATION_SEC=3`（`real 3.19`）
- Phase3 regression（提权重跑）
  - 命令：`bash scripts/run_phase3_regression.sh`
  - 退出码：`0`
  - 关键输出：`OPENAPI_STATUS=HTTP/1.1 200 OK`，`attempt_id=138/139/140`
  - 耗时：`DURATION_SEC=2`（`real 1.93`）

- 前端 build
  - 命令：`npm run build`
  - 退出码：`0`
  - 关键输出：`✓ built in 7.42s`（含 chunk>500kB 告警）
  - 耗时：`DURATION_SEC=10`（`real 10.02`）

- 前端 test
  - 命令：`npm test`
  - 退出码：`0`
  - 关键输出：`P3/P4/Decision Engine/SOP Fatal` 分组失败数均为 `0`
  - 耗时：`DURATION_SEC=0`（`real 0.24`）

### Batch-1 结论

- 最终结论：PASS（全部命令在有效执行环境下通过）
- 失败处置：仅存在沙箱限制导致的首轮失败，提权重跑后全部恢复为 PASS。

## Step-3｜功能可用性核证（2026-02-15）

- 执行时间：2026-02-15 09:02 ~ 09:15 +0800
- 判定口径：`主路径 PASS + 安全语义 PASS + 审计追溯 PASS + Test ID 证据完整`。

| 功能域 | 覆盖 Test IDs（主） | 执行入口 | 主路径 | 负路径 | 审计追溯 | 结论 |
|---|---|---|---|---|---|---|
| AUTH 认证会话 | AUTH-T001~T009 | `pytest -q tests/unit/test_auth_api.py -q` | PASS (`......... [100%]`) | PASS（重复邮箱/弱密码/错密/撤销 token） | PASS（鉴权失败路径可追溯，trace 与错误码稳定） | 可用 |
| AUTHZ + OBJ + AUDIT 基线 | AUTHZ-T001~T007, OBJ-T001~T009, AUDIT-T001/T006 | `pytest -q tests/unit/test_authz_guard_api.py tests/unit/test_teaching_api.py tests/unit/test_deny_audit_entrypoint_gate.py -q` | PASS (`.......................... [100%]`) | PASS（READ 越权 404、WRITE 越权 403） | PASS（deny 事件含真实 `resource_id`） | 可用 |
| SKILL 治理 | SKILL-T001~T010 | `pytest -q tests/unit/test_skill_governance_api.py tests/unit/test_skill_registry_migration_gate.py -q` | PASS (`......... [100%]`) | PASS（RISK-001/002/critical 门禁拒绝） | PASS（发布/拒绝审计链完整） | 可用 |
| APPROVAL 审批链 | APPR-T001~T010（含 T011/T012 替代验证入口） | `pytest -q tests/unit/test_approval_api.py tests/unit/test_approval_query_api.py tests/unit/test_approval_read_api.py tests/unit/test_tool_execution_after_approval_api.py -q` | PASS (`................. [100%]`) | PASS（teacher 越权 403/404，未登录 401） | PASS（`approval_query/approval_read/approval_granted|rejected` 可追溯） | 可用 |
| RAG + SEC + AGENT 防护 | RAG-T001~T008, SEC-T001~T008, AGENT 关键门禁 | `pytest -q tests/unit/test_ai_commands_api.py tests/unit/test_tool_security_guard_api.py tests/unit/test_redteam_batch_j003_api.py -q` | PASS (`.................... [100%]`) | PASS（越权过滤/注入/伪造引用拒绝） | PASS（`rag_filter_applied` 与 deny 审计链可追溯） | 可用 |
| E2E Trace + Eval 指标 | E2E-T001~T004, EVAL-T001/T002/T003/T005/T006/T007/T008, AUDIT-T008 | `pytest -q tests/unit/test_audit_events_api.py tests/unit/test_e2e_phase5_t001_t004.py tests/unit/test_eval_metrics_phase5.py -q` | PASS (`................ [100%]`) | PASS（跨通道越权拒绝语义正确） | PASS（`trace_id` 串联 Command→Approval→Audit） | 可用 |

### Step-3 结论

- 功能可用性判定：当前核证范围内全部“可用”。
- 未发现“主路径通过但安全/审计失败”的冲突项。

## Step-4｜缺陷收敛（2026-02-15）

- 缺陷分级策略：P0（阻断交付）> P1（高风险）> P2（可延期/环境噪声）。
- 分级结果：`P0=0`，`P1=0`，`P2=2`（均为执行环境限制，非业务缺陷）。

| Defect ID | 级别 | 触发点 | 根因 | 修复动作 | 回归命令 | 状态 |
|---|---|---|---|---|---|---|
| B1-ENV-001 | P2 | Batch-1 后端 unit 首轮失败 | 沙箱限制 `localhost:5432` 连接，触发 `PermissionError` | 按流程提权重跑；不改业务代码 | `pytest -q tests/unit -q` | Closed |
| B1-ENV-002 | P2 | Batch-1 phase3 首轮失败 | 沙箱端口绑定 `EPERM`，`ERROR_CODE=BACKEND_START_FAILED` | 按流程提权重跑；不改业务代码 | `bash scripts/run_phase3_regression.sh` | Closed |

### Step-4 结论

- P0 缺陷：无。
- P1 缺陷：无。
- 代码修复提交：无（本步无业务代码缺陷，不产生“缺陷修复 commit”）。

## Step-5｜Batch-2 全集回归与 Batch-1 对比（2026-02-15）

- 执行时间：2026-02-15 09:21 ~ 09:24 +0800
- 执行目标：重复 Step-2 全量命令并做回归差异比对。

### Batch-1 vs Batch-2 对比

| 项目 | Batch-1 | Batch-2 | 对比结论 |
|---|---|---|---|
| 后端 unit | EXIT=0，`[100%]`，`real 20.15` | EXIT=0，`[100%]`，`real 19.46` | 无回归（更快） |
| Gate2 smoke | EXIT=0，`全部通过：PASS`，`real 2.80` | EXIT=0，`全部通过：PASS`，`real 2.74` | 无回归 |
| Phase3 regression | EXIT=0，`OPENAPI_STATUS=200`，`attempt_id=138/139/140`，`real 1.93` | EXIT=0，`OPENAPI_STATUS=200`，`attempt_id=141/142/143`，`real 3.44` | 无功能回归（耗时波动） |
| 前端 build | EXIT=0，`✓ built in 7.42s`，`real 10.02` | EXIT=0，`✓ built in 11.33s`，`real 15.75` | 无回归（耗时上升） |
| 前端 test | EXIT=0，分组失败数均为 0，`real 0.24` | EXIT=0，分组失败数均为 0，`real 0.36` | 无回归 |

### Step-5 结论

- 回归判定：无功能回归。
- 风险提示：本次观察到前端 build 与 phase3 执行耗时上升，但退出码与功能断言均稳定 PASS。

## Step-6｜瘦身治理（2026-02-15）

### 清理清单

- 已删除旧离线包（将于 Step-7 重新生成）：
  - `gate3_delivery_docs_and_evidence.zip`
  - `gate3_delivery_repo_HEAD.tar.gz`
- 已恢复回归脚本引入的噪声改动：
  - `docs/testing/TEST_PLAN.md`（撤销重复 `T18 失败原因` 行）
- 已规范 `.gitignore`：
  - 新增 `/gate3_delivery_*.zip`
  - 新增 `/gate3_delivery_*.tar.gz`

### 影响说明

- 对业务代码：无影响。
- 对测试行为：无影响（仅清理历史产物与忽略规则）。
- 对交付流程：有正向影响（避免旧包混入，Step-7 产物唯一且可核验）。

## Step-7｜冻结交付与校验（2026-02-17）

- 冻结索引更新：`docs/testing/FINAL_DELIVERY_INDEX_GATE3.md` 已追加 Step-7 冻结刷新段。
- 离线包：
  - `gate3_delivery_repo_HEAD.tar.gz`（git tracked 快照）
  - `gate3_delivery_docs_and_evidence.zip`（文档证据白名单）
- SHA-256：
  - `026fd19347bf6358110a0ea4fe07f1699c3b0b677eeb3b72fa8be8c3a31f9e02  gate3_delivery_repo_HEAD.tar.gz`
  - `2e0ffdb2c421c1f3cd08a343eda8b23f74128f1f70932769016d955ad241a6fc  gate3_delivery_docs_and_evidence.zip`
- 完整性检查：
  - `gzip -t gate3_delivery_repo_HEAD.tar.gz`：PASS
  - `unzip -tq gate3_delivery_docs_and_evidence.zip`：PASS

## Step-8｜签收准备（签收汇报稿）

### Go / No-Go 结论

- 结论：**GO（建议签收）**
- 判定依据：
  - Batch-1 与 Batch-2 全集回归均通过。
  - Step-3 功能可用性表全部“可用”。
  - Step-4 缺陷池 `P0=0`、`P1=0`（仅环境限制类 P2 已闭环）。
  - Step-7 离线包与 SHA-256 校验通过。

### 残余风险

- 风险1：测试输出存在历史 warning（`datetime.utcnow()`、Pydantic v2 迁移提示、偶发 aiosqlite thread warning）。
  - 等级：P2
  - 建议：后续专项技术债处理，不阻断本次签收。
- 风险2：`phase3` 与前端 `build` 耗时较 Batch-1 有波动。
  - 等级：P2
  - 建议：纳入后续性能观测，不阻断本次签收。

### 回滚方案（可执行）

1. 代码回滚到冻结基线提交：`git checkout <frozen_commit>`（或按发布系统回滚到上个稳定版本）。
2. 数据层回滚：按既有 Alembic 回退策略执行 `alembic -c alembic.ini downgrade -1`（仅在变更涉及迁移时触发）。
3. 运行回归确认：
   - `pytest -q tests/unit -q`
   - `./scripts/run_gate2_smoke.sh`
   - `bash scripts/run_phase3_regression.sh`
   - `npm run build && npm test`
4. 交付包回滚：使用上一版 `gate3_delivery_repo_HEAD.tar.gz` 与 `gate3_delivery_docs_and_evidence.zip`（按 SHA-256 验签后恢复）。

## Phase 2 补充记录（2026-03-05）｜T-04 风险闭环 + T-05 框架迁移

### T-04 未闭环风险闭环（核心服务覆盖率门禁）

- 命令：
  - `cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && source .venv/bin/activate && export DATABASE_URL=sqlite+aiosqlite:///./rmos_main.db && pytest tests/ --cov=app.services.approval_service --cov=app.services.preflight_check --cov=app.services.identity.agent_policy_factory --cov=app.services.identity.session_initializer --cov=app.services.identity.teacher_monitor --cov=app.services.intent.training_intent_router --cov=app.services.memory.skill_profile_service --cov=app.services.memory.training_memory_writer --cov=app.services.orchestrator_v2 --cov=app.services.tool_executor --cov=app.services.training.feedback_generator --cov=app.services.training.project_generator --cov=app.services.training.session_service --cov=app.services.training.submission_service --cov-report=html:coverage/services-core --cov-report=term-missing --cov-fail-under=70`
- 输出摘要：
  - `378 passed, 1 skipped, 0 failed`
  - `Required test coverage of 70% reached. Total coverage: 74.63%`
- 结论：PASS（T-04 覆盖率风险闭环）

### T-05 前端测试框架迁移（自定义 runner -> Vitest）

- 迁移动作：
  - `r-mos-frontend/package.json`：`test` 脚本改为 `vitest run`
  - 新增 `r-mos-frontend/vitest.config.ts`
  - 新增 `src/adjudication/__tests__/adjudication.vitest.test.ts`
  - 删除旧 runner：`scripts/run-adjudication-tests.mjs`、`src/adjudication/__tests__/run-adjudication-tests.ts`
- 验证命令：
  - `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npm test`
  - `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npm run build`
- 输出摘要：
  - `npm test` -> `8 passed`
  - `npm run build` -> PASS（存在 chunk size warning）
- 结论：PASS（T-05-1/2/3 完成）

## Phase 3 补充记录（2026-03-05）｜T-08 集成测试执行与报告

### T-08 全量 E2E 复验（fresh evidence）

- 命令：
  - `cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && source .venv/bin/activate && export DATABASE_URL=sqlite+aiosqlite:///./rmos_main.db && pytest tests/e2e/ -v --tb=long`
- 输出摘要：
  - `collected 16`
  - `16 passed, 0 failed`
  - 存在既有 warning：Pydantic v2 deprecation、`datetime.utcnow()` deprecation（不影响通过判定）

### T-08 报告产出

- 报告文件：
  - `docs/testing/integration-test-report.md`
- 证据日志：
  - `docs/review/e2e-tests-t08-2026-03-05.log`
  - `docs/review/e2e-tests-t08-2026-03-05-rerun.log`
- 结论：
  - T-08-1 / T-08-2 / T-08-3 全部完成，当前集成测试口径 PASS。

## 2026-03-06 全量门禁复验（Postgres 基线）

### 执行命令

- 后端迁移：
  - `cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && source .venv/bin/activate && export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres && alembic upgrade head`
- 前端门禁：
  - `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npx tsc --noEmit`
  - `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npx eslint src/ --ext .ts,.tsx --max-warnings 0`
  - `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npm test`
  - `cd /Users/xuhehong/Desktop/r-mos/r-mos-frontend && npm run build`
- 后端门禁：
  - `cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && source .venv/bin/activate && export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres && pytest tests/unit -q`
  - `cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && source .venv/bin/activate && export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres && pytest tests/e2e -q`
  - `cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres && ./scripts/run_gate2_smoke.sh --e2e --audit`
  - `cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && bash scripts/run_phase3_regression.sh`

### 输出摘要

- 前端：
  - `npx tsc --noEmit` PASS
  - `npx eslint src/ --ext .ts,.tsx --max-warnings 0` PASS
  - `npm test` PASS（`8 files, 22 tests`）
  - `npm run build` PASS（入口产物 `dist/assets/index-Cm5MBKYF.js = 686.61 kB`）
- 后端：
  - `alembic upgrade head` PASS
  - `pytest tests/unit -q` PASS
  - `pytest tests/e2e -q` PASS
  - `./scripts/run_gate2_smoke.sh --e2e --audit` PASS（`全部通过：PASS`，`AUDIT-T006` 通过）
  - `bash scripts/run_phase3_regression.sh` PASS（`attempt_id error=145 skip=146 slow=147`）

### 过程修复

- `tests/unit/test_skill_registry_migration_gate.py`
  - 现象：asyncpg 对 Postgres `timestamp without time zone` 列插入 aware datetime 时失败，报 `can't subtract offset-naive and offset-aware datetimes`
  - 修复：将测试用 `created_at/updated_at` 改为 naive UTC 时间，避免门禁误报
  - 复验：单测重跑 PASS，随后 `pytest tests/unit -q` 全量 PASS

### 浏览器联调前置条件核实

- 服务探活：
  - `curl --noproxy 127.0.0.1,localhost http://127.0.0.1:8000/api/v1/health` -> PASS
  - `curl --noproxy 127.0.0.1,localhost -I http://127.0.0.1:55173/` -> `HTTP/1.1 200 OK`
- 真实登录口径：
  - `admin@rmos.test / Admin@123` -> 200，但返回 `role=student`
  - `teacher1@rmos.test / Teacher@123` -> 401
  - `student_a@rmos.test / Student@123` -> 401
- 数据库核对：
  - `psql -d postgres -At -c "select id,email,role from users where email in (...)"` 仅返回 `16|admin@rmos.test|student`

### 结论

- 全量门禁：PASS
- 浏览器三角色联调：阻塞，原因如下
  - DevTools MCP 持续报 `Transport closed`，无法执行浏览器自动化
  - 当前 Postgres 种子口径缺少 teacher/admin 可登录账号，且 `admin@rmos.test` 实际角色与验收矩阵不一致
- 建议后续动作：
  - 先恢复标准 seed 用户口径
  - 再复做 student / teacher / admin 登录、默认跳转、刷新保持、退出登录的浏览器回归

## 2026-03-06 验收账号口径修复补记

### 修复动作

- 新增脚本：
  - `r-mos-backend/scripts/seed_acceptance_users.py`
- 修复内容：
  - 补齐 `admin@rmos.test`、`teacher1@rmos.test`、`teacher2@rmos.test`、`student_a@rmos.test`、`student_b@rmos.test`
  - 同步 `users.role`
  - 同步 `roles / permissions / user_roles / role_permissions`
  - 补最小教学关系：`Acceptance Class 1 -> course-1 -> teacher1 -> student_a/student_b`，`Acceptance Class 2 -> course-2 -> teacher2`

### 复验命令

- 账号种子：
  - `cd /Users/xuhehong/Desktop/r-mos/r-mos-backend && source .venv/bin/activate && export DATABASE_URL=postgresql+asyncpg://postgres@localhost:5432/postgres && python scripts/seed_acceptance_users.py`
- 三角色登录：
  - `POST /api/v1/auth/login` with `admin@rmos.test / Admin@123`
  - `POST /api/v1/auth/login` with `teacher1@rmos.test / Teacher@123`
  - `POST /api/v1/auth/login` with `student_a@rmos.test / Student@123`
- 关键接口：
  - `GET /api/v1/admin/users?limit=10` with admin token
  - `GET /api/v1/classes` with teacher token
  - `GET /api/v1/students/21/profile` with student token

### 输出摘要

- 脚本幂等执行 PASS；稳定输出：
  - `admin -> id=16 role=admin`
  - `teacher1 -> id=19 role=teacher`
  - `teacher2 -> id=20 role=teacher`
  - `student_a -> id=21 role=student`
  - `student_b -> id=22 role=student`
- 登录返回：
  - admin -> `role=admin`, `default_route=/admin/console`
  - teacher1 -> `role=teacher`, `default_route=/workbench/teaching`
  - student_a -> `role=student`, `default_route=/workbench/training`
- 关键接口：
  - `GET /api/v1/admin/users?limit=10` -> 200
  - `GET /api/v1/classes` -> 200，包含 `Acceptance Class 1/2`
  - `GET /api/v1/students/21/profile` -> 200

### 浏览器层阻塞现状

- DevTools MCP 仍然 `Transport closed`
- AppleScript DOM 注入被 Chrome 设置拦截：
  - 需手工开启 `View > Developer > Allow JavaScript from Apple Events`
- AppleScript 键盘输入也被系统权限拦截：
  - `System Events` 当前不允许发送按键

### 结论

- 账号与 RBAC 口径：已修复
- API 级三角色联调：PASS
- 浏览器 UI 自动化：仍阻塞，但阻塞点已收敛为本机工具/权限，不再是代码或 seed 问题
