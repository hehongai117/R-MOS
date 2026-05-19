"""
YAML 配置文件验证测试
验证 data/config/ 下的 YAML 配置文件格式正确、字段完整、跨文件引用一致。
"""
import pathlib
import pytest
import yaml

CONFIG_DIR = pathlib.Path(__file__).resolve().parents[2] / "data" / "config"
SEED_FILE = CONFIG_DIR / "seed_base.yaml"
MOCK_FAULTS_FILE = CONFIG_DIR / "mock_faults.yaml"
SYSTEM_PROMPT_FILE = CONFIG_DIR / "prompts" / "system_prompt.txt"

VALID_DIFFICULTY_LEVELS = {"low", "medium", "high"}
VALID_SEVERITY_LEVELS = {"low", "medium", "high"}


@pytest.fixture(scope="module")
def seed_data():
    with open(SEED_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def mock_faults_data():
    with open(MOCK_FAULTS_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ============================================================
# 1. seed_base.yaml 测试
# ============================================================

class TestSeedBaseYaml:

    def test_file_exists(self):
        assert SEED_FILE.exists(), f"seed_base.yaml 不存在: {SEED_FILE}"

    def test_top_level_keys(self, seed_data):
        required_keys = {"robot_model", "sops", "fault_cases"}
        missing = required_keys - set(seed_data.keys())
        assert not missing, f"seed_base.yaml 缺少顶层 key: {missing}"

    def test_sops_is_non_empty_list(self, seed_data):
        sops = seed_data.get("sops")
        assert isinstance(sops, list), "sops 应为列表"
        assert len(sops) > 0, "sops 列表不应为空"

    def test_fault_cases_is_non_empty_list(self, seed_data):
        fault_cases = seed_data.get("fault_cases")
        assert isinstance(fault_cases, list), "fault_cases 应为列表"
        assert len(fault_cases) > 0, "fault_cases 列表不应为空"

    def test_sop_required_fields(self, seed_data):
        required_fields = {"name", "difficulty_level", "estimated_time", "steps"}
        for i, sop in enumerate(seed_data["sops"]):
            missing = required_fields - set(sop.keys())
            assert not missing, f"sops[{i}] (name={sop.get('name', '?')}) 缺少字段: {missing}"

    def test_sop_difficulty_level_valid(self, seed_data):
        for i, sop in enumerate(seed_data["sops"]):
            level = sop.get("difficulty_level")
            assert level in VALID_DIFFICULTY_LEVELS, (
                f"sops[{i}] (name={sop.get('name', '?')}) difficulty_level 值非法: '{level}'，"
                f"合法值: {VALID_DIFFICULTY_LEVELS}"
            )

    def test_sop_estimated_time_positive(self, seed_data):
        for i, sop in enumerate(seed_data["sops"]):
            t = sop.get("estimated_time")
            assert isinstance(t, (int, float)) and t > 0, (
                f"sops[{i}] estimated_time 应为正数，实际: {t}"
            )

    def test_sop_steps_non_empty(self, seed_data):
        for i, sop in enumerate(seed_data["sops"]):
            steps = sop.get("steps")
            assert isinstance(steps, list) and len(steps) > 0, (
                f"sops[{i}] (name={sop.get('name', '?')}) steps 应为非空列表"
            )

    def test_sop_step_required_fields(self, seed_data):
        required_step_fields = {"step_index", "title", "expected_action"}
        for i, sop in enumerate(seed_data["sops"]):
            for j, step in enumerate(sop.get("steps", [])):
                missing = required_step_fields - set(step.keys())
                assert not missing, (
                    f"sops[{i}].steps[{j}] 缺少字段: {missing}"
                )

    def test_sop_step_index_sequential(self, seed_data):
        for i, sop in enumerate(seed_data["sops"]):
            steps = sop.get("steps", [])
            indices = [s.get("step_index") for s in steps]
            assert indices == list(range(1, len(steps) + 1)), (
                f"sops[{i}] (name={sop.get('name', '?')}) step_index 应从1开始连续递增，"
                f"实际: {indices}"
            )

    def test_fault_case_required_fields(self, seed_data):
        required_fields = {"fault_code", "severity", "symptoms"}
        for i, fc in enumerate(seed_data["fault_cases"]):
            missing = required_fields - set(fc.keys())
            assert not missing, (
                f"fault_cases[{i}] (fault_code={fc.get('fault_code', '?')}) 缺少字段: {missing}"
            )

    def test_fault_case_severity_valid(self, seed_data):
        for i, fc in enumerate(seed_data["fault_cases"]):
            severity = fc.get("severity")
            assert severity in VALID_SEVERITY_LEVELS, (
                f"fault_cases[{i}] (fault_code={fc.get('fault_code', '?')}) "
                f"severity 值非法: '{severity}'，合法值: {VALID_SEVERITY_LEVELS}"
            )

    def test_fault_case_fault_code_unique(self, seed_data):
        codes = [fc.get("fault_code") for fc in seed_data["fault_cases"]]
        assert len(codes) == len(set(codes)), f"fault_code 存在重复: {codes}"

    def test_fault_case_symptoms_non_empty(self, seed_data):
        for i, fc in enumerate(seed_data["fault_cases"]):
            symptoms = fc.get("symptoms")
            assert isinstance(symptoms, list) and len(symptoms) > 0, (
                f"fault_cases[{i}] (fault_code={fc.get('fault_code', '?')}) "
                "symptoms 应为非空列表"
            )


# ============================================================
# 2. mock_faults.yaml 测试
# ============================================================

class TestMockFaultsYaml:

    def test_file_exists(self):
        assert MOCK_FAULTS_FILE.exists(), f"mock_faults.yaml 不存在: {MOCK_FAULTS_FILE}"

    def test_top_level_keys(self, mock_faults_data):
        required_keys = {"fault_effects", "sensor_defaults"}
        missing = required_keys - set(mock_faults_data.keys())
        assert not missing, f"mock_faults.yaml 缺少顶层 key: {missing}"

    def test_fault_effects_non_empty(self, mock_faults_data):
        effects = mock_faults_data.get("fault_effects")
        assert isinstance(effects, dict) and len(effects) > 0, (
            "fault_effects 应为非空字典"
        )

    def test_sensor_defaults_non_empty(self, mock_faults_data):
        defaults = mock_faults_data.get("sensor_defaults")
        assert isinstance(defaults, dict) and len(defaults) > 0, (
            "sensor_defaults 应为非空字典"
        )

    def test_sensor_defaults_required_keys(self, mock_faults_data):
        required = {"imu_gravity_z", "voltage_main", "voltage_logic"}
        defaults = mock_faults_data.get("sensor_defaults", {})
        missing = required - set(defaults.keys())
        assert not missing, f"sensor_defaults 缺少必需 key: {missing}"

    def test_sensor_defaults_imu_gravity_z_reasonable(self, mock_faults_data):
        val = mock_faults_data["sensor_defaults"].get("imu_gravity_z")
        assert isinstance(val, (int, float)), "imu_gravity_z 应为数值"
        assert 9.0 <= val <= 10.0, f"imu_gravity_z 应在 9.0~10.0 范围内，实际: {val}"

    def test_sensor_defaults_voltage_main_reasonable(self, mock_faults_data):
        val = mock_faults_data["sensor_defaults"].get("voltage_main")
        assert isinstance(val, (int, float)), "voltage_main 应为数值"
        assert val > 0, f"voltage_main 应为正数，实际: {val}"

    def test_sensor_defaults_voltage_logic_reasonable(self, mock_faults_data):
        val = mock_faults_data["sensor_defaults"].get("voltage_logic")
        assert isinstance(val, (int, float)), "voltage_logic 应为数值"
        assert val > 0, f"voltage_logic 应为正数，实际: {val}"

    def test_fault_codes_match_seed(self, seed_data, mock_faults_data):
        """mock_faults.yaml 中的故障代码应与 seed_base.yaml 中的故障案例一致"""
        seed_codes = {fc["fault_code"] for fc in seed_data["fault_cases"]}
        mock_codes = set(mock_faults_data.get("fault_effects", {}).keys())
        extra_in_mock = mock_codes - seed_codes
        assert not extra_in_mock, (
            f"mock_faults.yaml 中存在 seed_base.yaml 没有的故障代码: {extra_in_mock}"
        )

    def test_all_seed_faults_have_mock_effects(self, seed_data, mock_faults_data):
        """seed_base.yaml 中的每个故障代码都应在 mock_faults.yaml 中有对应效果"""
        seed_codes = {fc["fault_code"] for fc in seed_data["fault_cases"]}
        mock_codes = set(mock_faults_data.get("fault_effects", {}).keys())
        missing_in_mock = seed_codes - mock_codes
        assert not missing_in_mock, (
            f"seed_base.yaml 中的故障代码在 mock_faults.yaml 中缺少效果定义: {missing_in_mock}"
        )

    def test_fault_effects_are_dicts(self, mock_faults_data):
        effects = mock_faults_data.get("fault_effects", {})
        for code, effect in effects.items():
            assert isinstance(effect, dict), (
                f"fault_effects[{code}] 应为字典，实际类型: {type(effect)}"
            )
            assert len(effect) > 0, f"fault_effects[{code}] 不应为空字典"


# ============================================================
# 3. system_prompt.txt 测试
# ============================================================

class TestSystemPromptTxt:

    def test_file_exists(self):
        assert SYSTEM_PROMPT_FILE.exists(), (
            f"system_prompt.txt 不存在: {SYSTEM_PROMPT_FILE}"
        )

    def test_file_non_empty(self):
        content = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8").strip()
        assert len(content) > 0, "system_prompt.txt 内容不应为空"

    def test_file_meaningful_length(self):
        content = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8").strip()
        assert len(content) >= 10, (
            f"system_prompt.txt 内容过短（{len(content)} 字符），可能未正确写入"
        )
