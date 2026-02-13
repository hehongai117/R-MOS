# 测试报告

## 自动生成说明

- 本文件由回归脚本自动创建。

<!-- PHASE3_STEP4_START -->
### Phase3 Step4 单命令回归证据

- 运行时间：2026-02-13T06:14:57.974908+00:00
- 运行标识：a6a4396645f34d7e96fcfdfc305f1ea6
- 后端端口：`8000`
- attempt_id：error=132 skip=133 slow=134

#### 最新一次运行

**openapi**
```
HTTP/1.1 200 OK
```

**diagnosis（attempt_id=132）**
```
{"attemptId": 132, "diagnosisCode": "E_ERROR_OCCURRED", "ruleId": "R-DIAG-001", "severity": "HIGH", "stepDiagnoses": [{"stepIndex": 1, "stepDiagnosisCode": "E_ERROR_OCCURRED", "severity": "HIGH", "findings": ["该步骤存在错误"]}]}
```

**diagnosis（attempt_id=133）**
```
{"attemptId": 133, "diagnosisCode": "E_STEP_SKIPPED", "ruleId": "R-DIAG-002", "severity": "MEDIUM", "stepDiagnoses": [{"stepIndex": 1, "stepDiagnosisCode": "E_STEP_SKIPPED", "severity": "MEDIUM", "findings": ["该步骤被跳过"]}]}
```

**diagnosis（attempt_id=134）**
```
{"attemptId": 134, "diagnosisCode": "E_TOO_SLOW", "ruleId": "R-DIAG-003", "severity": "LOW", "stepDiagnoses": [{"stepIndex": 2, "stepDiagnosisCode": "E_TOO_SLOW", "severity": "LOW", "findings": ["步骤耗时偏长"]}]}
```
<!-- PHASE3_STEP4_END -->

## Gate-3 M3 / Phase5 Test ID 证据映射（收口补齐）

- 证据时间：2026-02-13 14:15 +0800
- 证据来源：
  - `bash /Users/xuhehong/Desktop/r-mos/r-mos-backend/scripts/run_phase3_regression.sh`
  - `./scripts/run_gate2_smoke.sh`
  - `rg -n "EVAL-T00[1-7]|E2E-T00[1-8]|AUDIT-T008" docs -S`
  - `rg -n "EVAL-T00[1-7]|E2E-T00[1-8]|AUDIT-T008" r-mos-backend -S`

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

- EVAL-T001（引用覆盖率）：缺乏数据：未找到入口（rg=0）
- EVAL-T002（幻觉率）：缺乏数据：未找到入口（rg=0）
- EVAL-T003（Read Tool 成功率）：缺乏数据：未找到入口（rg=0）
- EVAL-T005（Red Team 越权用例）：缺乏数据：未找到入口（rg=0）
- EVAL-T006（Red Team 诱导高危）：缺乏数据：未找到入口（rg=0）
- EVAL-T007（Red Team 伪造引用）：缺乏数据：未找到入口（rg=0）
