# Phase 4: 后端配置外部化 — 详细实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将后端硬编码的密钥、CORS、seed 数据、mock 参数、LLM prompt 全部外部化为 `.env` / 配置文件 / 模板文件，确保部署环境可配置。

**Architecture:** 利用 Pydantic Settings 的 `.env` 加载能力，将未外部化的配置项迁移到 `Settings` 类。Seed 数据和 LLM prompt 迁移到 YAML 文件，运行时加载。

**Tech Stack:** FastAPI + Pydantic Settings + PyYAML

---

## 文件结构

```
r-mos-backend/
├── app/core/config.py                ← 修改：确认 SECRET_KEY 生产级保护
├── app/adapters/mock.py              ← 修改：fault_effects 从配置读取
├── app/services/llm/prompts.py       ← 修改：system prompt 从 settings 读取
├── app/services/llm/mock_provider.py ← 修改：mock 响应从文件加载
├── data/config/
│   ├── mock_faults.yaml              ← 新建：mock 故障参数
│   └── prompts/
│       ├── system_prompt.txt         ← 新建：系统提示词
│       └── mock_responses.yaml       ← 新建：mock LLM 响应
├── scripts/seed_data.py              ← 修改：从 YAML 读取 seed 数据
└── data/config/seed_sops.yaml        ← 新建：seed SOP 数据
```

---

### Task 29: SECRET_KEY 生产级保护确认

**Files:**
- Modify: `r-mos-backend/app/core/config.py`
- Modify: `r-mos-backend/.env.example`

审计结果显示 SECRET_KEY 已部分外部化：有 `dev-only-change-me` 哨兵值和生产环境检查。此 Task 确认保护措施完善。

- [ ] **Step 1: 确认生产环境保护已存在**

读取 `config.py`，确认第 66-67 行的生产保护：
```python
if not self.DEBUG and self.SECRET_KEY == "dev-only-change-me":
    raise RuntimeError("SECRET_KEY must be changed in production")
```

若已存在且正确，此步骤无需修改。

- [ ] **Step 2: 更新 .env.example**

确认 `.env.example` 中有明确的 SECRET_KEY 说明：

```bash
# 生产环境必须替换为强随机密钥（至少 32 字符）
# 可用 python -c "import secrets; print(secrets.token_urlsafe(32))" 生成
SECRET_KEY=dev-only-change-me
```

- [ ] **Step 3: 确认 .env 不在 git 中**

```bash
git ls-files --error-unmatch .env 2>&1 || echo ".env is not tracked (good)"
grep "^\.env$" .gitignore || echo "WARNING: .env not in .gitignore"
```

- [ ] **Step 4: Commit**

```bash
git add .env.example
git commit -m "docs(config): clarify SECRET_KEY production requirements in .env.example"
```

---

### Task 30: CORS_ORIGINS 环境变量化确认

**Files:**
- Modify: `r-mos-backend/main.py`（根目录）
- Review: `r-mos-backend/app/core/config.py`

审计显示 `CORS_ORIGINS` 已在 Settings 中定义为 `List[str]`。此 Task 确认 CORS 中间件使用 `settings.CORS_ORIGINS`。

- [ ] **Step 1: 检查 main.py 的 CORS 配置**

读取根目录 `main.py`（不是 `app/main.py`），找到 `CORSMiddleware` 配置。确认 `allow_origins` 使用 `settings.CORS_ORIGINS` 而非硬编码列表。

- [ ] **Step 2: 如有硬编码则修复**

如果发现 `allow_origins=["http://localhost:3000", ...]` 硬编码：

```python
# 之前：
# allow_origins=["http://localhost:3000", "http://localhost:5173"]
# 之后：
from app.core.config import settings
allow_origins=settings.CORS_ORIGINS
```

- [ ] **Step 3: Commit（如有修改）**

```bash
git add main.py
git commit -m "fix(cors): use settings.CORS_ORIGINS instead of hardcoded origins"
```

---

### Task 31: Seed 脚本参数化

**Files:**
- Create: `r-mos-backend/data/config/seed_base.yaml`
- Modify: `r-mos-backend/scripts/seed_data.py`

- [ ] **Step 1: 创建 seed 数据配置文件**

创建 `r-mos-backend/data/config/seed_base.yaml`：

```yaml
# R-MOS 基础 seed 数据配置
# 修改此文件来自定义初始数据，无需修改 Python 脚本

robot_model: "MOCK_HUMANOID_V1"

sops:
  - name: "电机过热故障排查"
    category: "thermal"
    difficulty_level: "low"
    estimated_time: 600
    steps:
      - title: "查看电机温度传感器读数"
        description: "打开传感器面板，定位电机温度"
        target_part: "motor_left"
        expected_action: "inspect"
      # ... (从 seed_data.py 提取)

  - name: "关节校准SOP"
    category: "calibration"
    difficulty_level: "medium"
    estimated_time: 900
    steps:
      - title: "进入校准模式"
        description: "通过控制面板进入关节校准模式"
        target_part: "joint_knee"
        expected_action: "configure"
      # ...

  - name: "日常巡检"
    category: "routine"
    difficulty_level: "low"
    estimated_time: 300
    steps:
      - title: "外观检查"
        description: "检查机器人外壳是否有损伤"
        target_part: null
        expected_action: "inspect"
      # ...

fault_cases:
  - fault_code: "E001_OVERHEAT"
    fault_type: "过热"
    severity: "high"
    symptoms: ["温度异常升高", "电机频繁降速"]
    solution_steps: ["检查散热系统", "更换导热硅脂"]
  # ... (从 seed_data.py 提取)
```

- [ ] **Step 2: 修改 seed_data.py 从 YAML 加载**

```python
import yaml
from pathlib import Path

CONFIG_DIR = Path(__file__).parent.parent / "data" / "config"

def load_seed_config():
    with open(CONFIG_DIR / "seed_base.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

async def seed():
    config = load_seed_config()
    robot_model = config["robot_model"]
    
    for sop_data in config["sops"]:
        sop_data["applicable_model"] = robot_model
        # ... create SOP with steps
```

- [ ] **Step 3: 确认 PyYAML 已在 requirements.txt**

```bash
grep pyyaml requirements.txt || echo "pyyaml" >> requirements.txt
```

- [ ] **Step 4: 验证 seed 脚本正常运行**

```bash
python scripts/seed_data.py
```

- [ ] **Step 5: Commit**

```bash
git add data/config/seed_base.yaml scripts/seed_data.py requirements.txt
git commit -m "refactor(seed): load seed data from YAML config instead of hardcoded Python"
```

---

### Task 32: Mock 适配器参数化

**Files:**
- Create: `r-mos-backend/data/config/mock_faults.yaml`
- Modify: `r-mos-backend/app/adapters/mock.py`

- [ ] **Step 1: 创建 mock 故障参数配置**

创建 `r-mos-backend/data/config/mock_faults.yaml`：

```yaml
# Mock 适配器 — 故障效果参数
# 调整这些参数来改变模拟器的故障行为

fault_effects:
  E001_OVERHEAT:
    temperature_increase: 30.0
    torque_multiplier: 0.7
    position_noise: 0.3

  E002_STALL:
    velocity_multiplier: 0.0
    position_frozen: true

  E003_VOLTAGE_DROP:
    battery_drain: 50.0
    torque_multiplier: 0.5

  E004_SENSOR_FAILURE:
    sensor_noise: true

  E005_JOINT_LOOSE:
    position_noise: 0.5
    torque_multiplier: 0.3

# 传感器模拟参数
sensor_defaults:
  imu_gravity_z: 9.8
  imu_noise_stddev: 0.2
  voltage_main: 24.0
  voltage_logic: 5.0
  pressure_baseline: 100.0
  pressure_noise_stddev: 10.0
  battery_drain_rate: 0.1  # per simulation_time unit
```

- [ ] **Step 2: 修改 mock.py 加载配置**

在 `mock.py` 中：

```python
import yaml
from pathlib import Path

_MOCK_CONFIG_PATH = Path(__file__).parent.parent.parent / "data" / "config" / "mock_faults.yaml"

def _load_fault_config() -> dict:
    if _MOCK_CONFIG_PATH.exists():
        with open(_MOCK_CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

# 在类初始化中：
class MockAdapter:
    def __init__(self, config=None):
        # ...existing init...
        _config = _load_fault_config()
        self._fault_effects = _config.get("fault_effects", {
            # 原有硬编码作为 fallback
            "E001_OVERHEAT": {"temperature_increase": 30.0, ...},
            ...
        })
        self._sensor_defaults = _config.get("sensor_defaults", {
            "imu_gravity_z": 9.8,
            ...
        })
```

- [ ] **Step 3: 验证模拟器正常运行**

```bash
python -c "from app.adapters.mock import MockRobotAdapter; a = MockRobotAdapter({}); print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add data/config/mock_faults.yaml app/adapters/mock.py
git commit -m "refactor(mock): load fault effect parameters from YAML config"
```

---

### Task 33: LLM prompt 模板化

**Files:**
- Create: `r-mos-backend/data/config/prompts/system_prompt.txt`
- Modify: `r-mos-backend/app/services/llm/prompts.py`

- [ ] **Step 1: 创建系统提示词模板文件**

创建 `r-mos-backend/data/config/prompts/system_prompt.txt`：

```
你是一个专业的机器人维保培训助手。

专业领域：机器人维护与操作

核心能力：
- 指导学员完成标准维保操作流程
- 诊断和分析机器人故障
- 提供维保知识解答

安全规则：
- 所有操作建议必须符合安全规范
- 涉及高压或危险操作时必须提示安全注意事项
```

- [ ] **Step 2: 修改 prompts.py 从文件加载**

在 `prompts.py` 中修改 `SystemPromptBlock`：

```python
from pathlib import Path
from app.core.config import settings

_PROMPTS_DIR = Path(__file__).parent.parent.parent.parent / "data" / "config" / "prompts"

def _load_system_prompt() -> str:
    """加载系统提示词：settings > 文件 > 硬编码默认"""
    if settings.AI_ASSISTANT_SYSTEM_PROMPT != "你是 R-MOS 维保学习助手，帮助学生理解机器人维保操作。":
        return settings.AI_ASSISTANT_SYSTEM_PROMPT
    
    prompt_file = _PROMPTS_DIR / "system_prompt.txt"
    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8").strip()
    
    return "你是一个专业的机器人维保培训助手。"

@dataclass
class SystemPromptBlock:
    role: str = field(default_factory=_load_system_prompt)
    # ... rest stays the same
```

- [ ] **Step 3: 验证 prompt 加载**

```bash
python -c "
from app.services.llm.prompts import SystemPromptBlock
block = SystemPromptBlock()
print(f'Prompt length: {len(block.role)} chars')
print(block.role[:50])
"
```

Expected: 从 `system_prompt.txt` 加载的内容。

- [ ] **Step 4: Commit**

```bash
git add data/config/prompts/system_prompt.txt app/services/llm/prompts.py
git commit -m "refactor(llm): load system prompt from template file with settings override"
```

---

## 验收标准

- [ ] `SECRET_KEY` 有生产级保护（非默认值时阻止启动）
- [ ] CORS origins 全部从 `settings.CORS_ORIGINS` 读取
- [ ] Seed 脚本从 YAML 加载数据，无 Python 硬编码
- [ ] Mock 故障参数从 YAML 配置读取
- [ ] LLM 系统提示词从模板文件加载，支持 settings 覆盖
- [ ] 所有现有测试和功能正常
