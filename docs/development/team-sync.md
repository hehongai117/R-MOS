# R-MOS 开发团队同步记录

## 基线信息

| 项目 | 值 |
|-----|-----|
| 基线日期 | 2026-02-28 |
| 版本 | v1.0.0-baseline |
| 提交者 | Claude (dry-run) |
| 目的 | CI/CD 门禁验证 + 证据链基线 |

---

## 干跑测试结果 (Dry-Run)

### 测试环境

- Python: 3.x
- 测试框架: 原生 pytest 风格
- 测试路径: `schemas/tests/`

### PR Gates 测试结果

| 测试ID | 场景 | 预期结果 | 实际结果 | 状态 |
|-------|------|---------|---------|------|
| PR-A | Schema变更不bump version | FAIL | FAIL ✓ | 通过 |
| PR-B | 改schemas未获DRI审批 | FAIL | FAIL ✓ | 通过 |
| PR-C | 伪造Evidence破坏hash链 | FAIL | FAIL ✓ | 通过 |
| PR-D | 只加测试/fixtures | PASS | PASS ✓ | 通过 |

### Golden Task 测试结果

| 测试项 | 预期结果 | 实际结果 | 状态 |
|-------|---------|---------|------|
| 证据包生成 | 生成带链式hash的证据 | PASS ✓ | 通过 |
| 服务端签名 | 用私钥签名每条证据 | PASS ✓ | 通过 |
| 链完整性验证 | 检测hash链断裂 | PASS ✓ | 通过 |
| 签名验证 | 验签每条证据 | PASS ✓ | 通过 |
| 审计报告生成 | 输出完整审计记录 | PASS ✓ | 通过 |

---

## 证据链基线 (Evidence Chain Baseline)

### 证据结构

```python
class Evidence(BaseModel):
    id: str                    # 唯一标识
    task_id: str               # 任务ID
    step_id: str               # 步骤ID
    action_id: str             # 动作ID
    type: str                  # trajectory, sensor_reading, screenshot, verdict

    # 存储
    storage_uri: str = ""      # S3/OSS路径

    # 防篡改链
    hash_prev: str = ""        # 前一条证据hash (链式)
    hash_content: str = ""     # 内容SHA256
    signature: str = ""        # 服务端签名

    # 时间戳
    timestamp_client: int      # 客户端时间
    timestamp_server: int      # 服务端强时间

    # 版本
    schema_version: str = "1.0.0"
```

### 链式验证逻辑

```
Chain Validator:
1. 第一条证据 hash_prev 必须为空 ""
2. 第N条证据 hash_prev 必须等于 第N-1条证据 hash_content
3. 任意不匹配 → Chain Broken
```

### 示例证据链

```
Evidence Chain:
  [1] trajectory: action-001
      Hash: e0cc28574d3fac5b...
      Prev: (root)...
  [2] trajectory: action-002
      Hash: 6a8d63281e156f59...
      Prev: e0cc28574d3fac5b...
  [3] sensor_reading: action-003
      Hash: 5d6d75b37f36bfa3...
      Prev: 6a8d63281e156f59...
  [4] screenshot: action-004
      Hash: d90004f23dc40279...
      Prev: 5d6d75b37f36bfa3...
```

---

## DRI 基线 (DRI Baseline)

### Schema 目录 DRI 分配

| 目录 | DRI | 审批要求 |
|-----|-----|---------|
| schemas/fsm/ | @backend | 必审 |
| schemas/evidence/ | @backend | 必审 |
| schemas/agent/ | @ai-engineer | 必审 |
| schemas/knowledge/ | @ai-engineer | 必审 |

### 审批流程

```
PR 创建 → 检查变更文件 → 匹配 DRI → 确认审批 → 合并
```

---

## 版本管理基线

### Schema 版本规则

1. 任何 Schema 字段变更 → 必须 bump version
2. Version 格式: `MAJOR.MINOR.PATCH`
3. 默认版本: `1.0.0`

---

## 回溯判断规则

### 如何判断问题是"新引入"还是"原有"

| 场景 | 判断方法 |
|-----|---------|
| CI 门禁失败 | 检查 PR 是否触发了对应 gate |
| 证据链断裂 | 检查证据是否正确设置 hash_prev |
| 签名验证失败 | 检查是否使用正确密钥签名 |
| 权限问题 | 检查变更是否涉及 schemas/ 目录 |

### 基线对比方法

```bash
# 对比当前代码与基线
git diff v1.0.0-baseline HEAD -- schemas/

# 运行基线测试
PYTHONPATH=. python3 schemas/tests/test_ci_gates.py
PYTHONPATH=. python3 schemas/tests/test_golden_task.py
```

---

## Phase 1/2 开发任务

### Phase 1: 骨架修复 (1周)

- [ ] FSM状态/事件统一 (`schemas/fsm/`)
- [ ] 事件必备字段
- [ ] Action原语增强

### Phase 2: 证据安全 (1周)

- [ ] 证据链实现
- [ ] 服务端签名
- [ ] 防重放机制

---

## 更新日志

| 日期 | 操作者 | 变更内容 |
|-----|-------|---------|
| 2026-02-28 | Claude | 创建基线记录 + 干跑测试 |
