# Gate-3 最终交付冻结清单（可签收索引）

## 1) 概览

- Gate-3 状态：**完成（冻结）**
- 冻结日期：2026-02-14
- 证据基线 HEAD（生成时）：`142bd5b3d19cb25478736468464e816bb245704c`
- Final Verification Batch commit：`e95d4a7f85a5a86ff3be43ff8b649651af04c27a`
- Final Verification 证据行号：`docs/testing/TEST_REPORT.md:222-258`，`DEVELOPMENT_LOG.md:1992-2023`
- 覆盖范围：J-001/J-002/J-003、M3 Phase5（E2E+EVAL）、APPR 口径收敛、前端最小回归
- 说明：本清单仅做“可复现/可签收”证据索引，不新增任何业务需求或验收口径。

## 2) Test ID 覆盖表

| Test ID | 命令 | 结果 | 证据行号 | commit |
|---|---|---|---|---|
| AUDIT-T008 | `pytest -q tests/unit/test_ai_replay_api.py` | PASS | `DEVELOPMENT_LOG.md:1658-1670` | `9aa3776` |
| E2E-T007 | `GET /api/v1/ai/replay/{trace_id}` + `pytest -q tests/unit/test_ai_replay_api.py` | PASS | `DEVELOPMENT_LOG.md:1655-1670` | `9aa3776` |
| AGENT-T005 | `pytest -q tests/unit -k "j002" -q` | PASS | `DEVELOPMENT_LOG.md:1693-1707`, `docs/testing/TEST_REPORT.md:77-80` | `17fd6a4`, `aa26b68` |
| SEC-T001~SEC-T007 | `pytest -q tests/unit -k "j003" -q` | PASS | `DEVELOPMENT_LOG.md:1734-1758` | `8c9f74c` |
| E2E-T005 | `bash scripts/run_phase3_regression.sh` | PASS | `docs/testing/TEST_REPORT.md:50-53`, `DEVELOPMENT_LOG.md:1801,1779` | `8a906e8`, `38fd9df` |
| E2E-T006 | `bash scripts/run_phase3_regression.sh` | PASS | `docs/testing/TEST_REPORT.md:54-57`, `DEVELOPMENT_LOG.md:1802` | `8a906e8` |
| E2E-T007 | `bash scripts/run_phase3_regression.sh` | PASS | `docs/testing/TEST_REPORT.md:58-61`, `DEVELOPMENT_LOG.md:1803` | `8a906e8` |
| E2E-T008 | `./scripts/run_gate2_smoke.sh` | PASS | `docs/testing/TEST_REPORT.md:62-65`, `DEVELOPMENT_LOG.md:1804,1780` | `8a906e8`, `38fd9df` |
| EVAL-T001 | `pytest -q tests/unit/test_eval_metrics_phase5.py -q` | PASS | `docs/testing/TEST_REPORT.md:69-72`, `DEVELOPMENT_LOG.md:1837` | `aa26b68` |
| EVAL-T002 | `pytest -q tests/unit/test_eval_metrics_phase5.py -q` | PASS | `docs/testing/TEST_REPORT.md:73-76`, `DEVELOPMENT_LOG.md:1837` | `aa26b68` |
| EVAL-T003 | `pytest -q tests/unit/test_eval_metrics_phase5.py -q` | PASS | `docs/testing/TEST_REPORT.md:77-80`, `DEVELOPMENT_LOG.md:1837` | `aa26b68` |
| EVAL-T005 | `pytest -q tests/unit/test_eval_metrics_phase5.py -q` | PASS | `docs/testing/TEST_REPORT.md:81-84`, `DEVELOPMENT_LOG.md:1837` | `aa26b68` |
| EVAL-T006 | `pytest -q tests/unit/test_eval_metrics_phase5.py -q` | PASS | `docs/testing/TEST_REPORT.md:85-88`, `DEVELOPMENT_LOG.md:1837` | `aa26b68` |
| EVAL-T007 | `pytest -q tests/unit/test_eval_metrics_phase5.py -q` | PASS | `docs/testing/TEST_REPORT.md:89-92`, `DEVELOPMENT_LOG.md:1837` | `aa26b68` |
| E2E-T001 | `pytest -q tests/unit -k "E2E-T001 ... EVAL-T008" -q` | PASS | `docs/testing/TEST_REPORT.md:108-111`, `DEVELOPMENT_LOG.md:1889-1892` | `d79a028` |
| E2E-T002 | `pytest -q tests/unit -k "E2E-T001 ... EVAL-T008" -q` | PASS | `docs/testing/TEST_REPORT.md:112-115`, `DEVELOPMENT_LOG.md:1889-1892` | `d79a028` |
| E2E-T003 | `pytest -q tests/unit -k "E2E-T001 ... EVAL-T008" -q` | PASS | `docs/testing/TEST_REPORT.md:116-119`, `DEVELOPMENT_LOG.md:1889-1892` | `d79a028` |
| E2E-T004 | `pytest -q tests/unit -k "E2E-T001 ... EVAL-T008" -q` | PASS | `docs/testing/TEST_REPORT.md:120-123`, `DEVELOPMENT_LOG.md:1889-1892` | `d79a028` |
| EVAL-T008 | `pytest -q tests/unit -k "E2E-T001 ... EVAL-T008" -q` | PASS | `docs/testing/TEST_REPORT.md:127-130`, `DEVELOPMENT_LOG.md:1892` | `d79a028` |
| APPR-T011 | `GET /api/v1/ai/approvals?status=pending`（admin/auditor/teacher） | N/A（替代验证已执行） | `docs/testing/TEST_REPORT.md:141-147,165-175`, `DEVELOPMENT_LOG.md:1905-1929,1950-1953` | `9dbe0df`, `f212af8` |
| APPR-T012 | `GET /api/v1/ai/approvals/{id}` + `GET /api/v1/audit/events?trace_id=...` | N/A（替代验证已执行） | `docs/testing/TEST_REPORT.md:148-153,177-187`, `DEVELOPMENT_LOG.md:1905-1929,1954-1957` | `9dbe0df`, `f212af8` |

## 3) 例外项（N/A）与替代验证

### APPR-T011（N/A）

- 原因：矩阵原口径“teacher 查询 pending 返回 200”与当前实现“仅 admin/auditor 可查询，teacher 返回 403”冲突。
- 替代验证：`admin/auditor=200`、`teacher=403(AUTHZ_002)`，并可在审计中追溯 deny 事件。
- 证据：`docs/testing/TEST_REPORT.md:141-147,165-175`，`DEVELOPMENT_LOG.md:1950-1953`，commit=`9dbe0df`,`f212af8`。

### APPR-T012（N/A）

- 原因：`approvals_received` 聚合字段未实现，且不作为当前 Gate-3 交付门槛。
- 替代验证：审批详情最小字段集可读（200）+ `approval_read` 审计可追溯。
- 证据：`docs/testing/TEST_REPORT.md:148-153,177-187`，`DEVELOPMENT_LOG.md:1954-1957`，commit=`9dbe0df`,`f212af8`。

## 4) 回归门槛（冻结基线）

| 门槛 | 命令 | 最新结果 | 证据行号 | commit |
|---|---|---|---|---|
| 后端单测全量 | `pytest -q tests/unit -q` | PASS | `DEVELOPMENT_LOG.md:1838`, `DEVELOPMENT_LOG.md:1778` | `aa26b68`, `38fd9df` |
| Gate2 smoke | `./scripts/run_gate2_smoke.sh` | PASS | `DEVELOPMENT_LOG.md:1780` | `38fd9df` |
| Phase3 regression | `bash scripts/run_phase3_regression.sh` | PASS | `DEVELOPMENT_LOG.md:1779` | `38fd9df` |
| 前端 build | `npm run build` | PASS（含 chunk 告警） | `docs/testing/TEST_REPORT.md:199-207`, `DEVELOPMENT_LOG.md:1978,1982` | `142bd5b` |
| 前端 test | `npm test` | PASS | `docs/testing/TEST_REPORT.md:211-220`, `DEVELOPMENT_LOG.md:1979` | `142bd5b` |
| Final Verification Batch | `pytest -q tests/unit -q` + `./scripts/run_gate2_smoke.sh` + `bash scripts/run_phase3_regression.sh` + `npm run build` + `npm test` | PASS | `docs/testing/TEST_REPORT.md:222-258`, `DEVELOPMENT_LOG.md:1992-2023` | `e95d4a7` |

## 5) 冻结结论

- 当前 Gate-3 证据链已满足“可复现、可审计、可签收”。
- 后续如需变更，仅允许在新任务中增量追加证据，不回写已冻结口径。

## 6) Step-7 冻结刷新（2026-02-17）

- 冻结时间：2026-02-17 09:35:32 +0800
- 冻结基线 HEAD：`5c0f07ba5337025f3af5a00ac90e499e4ea611c6`
- 生成口径：
  - 仓库快照包仅包含 git tracked 文件（`git ls-files -z | tar --null -T - -czf ...`）
  - 文档证据包按白名单文件生成（`zip -r ...`）

| 产物 | 大小 | SHA-256 | 完整性校验 |
|---|---:|---|---|
| `gate3_delivery_repo_HEAD.tar.gz` | 458 MB | `026fd19347bf6358110a0ea4fe07f1699c3b0b677eeb3b72fa8be8c3a31f9e02` | `gzip -t` 通过 |
| `gate3_delivery_docs_and_evidence.zip` | 88 KB | `2e0ffdb2c421c1f3cd08a343eda8b23f74128f1f70932769016d955ad241a6fc` | `unzip -tq` 通过 |

- 校验命令：
  - `shasum -a 256 gate3_delivery_repo_HEAD.tar.gz gate3_delivery_docs_and_evidence.zip`
