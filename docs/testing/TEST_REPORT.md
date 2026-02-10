# 测试报告

## 自动生成说明

- 本文件由回归脚本自动创建。

<!-- PHASE3_STEP4_START -->
### Phase3 Step4 单命令回归证据

- 运行时间：2026-02-10T04:57:13.812941+00:00
- 运行标识：ab59da29cfd7450e8743939cc8d66294
- 后端端口：`8000`
- attempt_id：error=117 skip=118 slow=119

#### 最新一次运行

**openapi**
```
HTTP/1.1 200 OK
```

**diagnosis（attempt_id=117）**
```
{"attemptId": 117, "diagnosisCode": "E_ERROR_OCCURRED", "ruleId": "R-DIAG-001", "severity": "HIGH", "stepDiagnoses": [{"stepIndex": 1, "stepDiagnosisCode": "E_ERROR_OCCURRED", "severity": "HIGH", "findings": ["该步骤存在错误"]}]}
```

**diagnosis（attempt_id=118）**
```
{"attemptId": 118, "diagnosisCode": "E_STEP_SKIPPED", "ruleId": "R-DIAG-002", "severity": "MEDIUM", "stepDiagnoses": [{"stepIndex": 1, "stepDiagnosisCode": "E_STEP_SKIPPED", "severity": "MEDIUM", "findings": ["该步骤被跳过"]}]}
```

**diagnosis（attempt_id=119）**
```
{"attemptId": 119, "diagnosisCode": "E_TOO_SLOW", "ruleId": "R-DIAG-003", "severity": "LOW", "stepDiagnoses": [{"stepIndex": 2, "stepDiagnosisCode": "E_TOO_SLOW", "severity": "LOW", "findings": ["步骤耗时偏长"]}]}
```
<!-- PHASE3_STEP4_END -->

