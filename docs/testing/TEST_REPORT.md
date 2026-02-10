# 测试报告

## 自动生成说明

- 本文件由回归脚本自动创建。

<!-- PHASE3_STEP4_START -->
### Phase3 Step4 单命令回归证据

- 运行时间：2026-02-10T02:58:14.602674+00:00
- 运行标识：ac0e41cc44ff4a2dac6f1c76b78682fe
- 后端端口：`8000`
- attempt_id：error=84 skip=85 slow=86

#### 最新一次运行

**openapi**
```
HTTP/1.1 200 OK
```

**diagnosis（attempt_id=84）**
```
{"attemptId": 84, "diagnosisCode": "E_ERROR_OCCURRED", "ruleId": "R-DIAG-001", "severity": "HIGH", "stepDiagnoses": [{"stepIndex": 1, "stepDiagnosisCode": "E_ERROR_OCCURRED", "severity": "HIGH", "findings": ["该步骤存在错误"]}]}
```

**diagnosis（attempt_id=85）**
```
{"attemptId": 85, "diagnosisCode": "E_STEP_SKIPPED", "ruleId": "R-DIAG-002", "severity": "MEDIUM", "stepDiagnoses": [{"stepIndex": 1, "stepDiagnosisCode": "E_STEP_SKIPPED", "severity": "MEDIUM", "findings": ["该步骤被跳过"]}]}
```

**diagnosis（attempt_id=86）**
```
{"attemptId": 86, "diagnosisCode": "E_TOO_SLOW", "ruleId": "R-DIAG-003", "severity": "LOW", "stepDiagnoses": [{"stepIndex": 2, "stepDiagnosisCode": "E_TOO_SLOW", "severity": "LOW", "findings": ["步骤耗时偏长"]}]}
```
<!-- PHASE3_STEP4_END -->

