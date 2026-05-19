"""
MockRobotAdapter YAML 驱动配置测试

验证 Phase 4 模块化后 MockRobotAdapter 能正确从 data/config/mock_faults.yaml
加载故障效果和传感器默认值，并在 YAML 不可用时优雅回退到内置默认值。
"""
import pathlib
import pytest

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

# ---------------------------------------------------------------------------
# 路径常量
# ---------------------------------------------------------------------------
CONFIG_DIR = pathlib.Path(__file__).resolve().parents[2] / "data" / "config"
MOCK_FAULTS_FILE = CONFIG_DIR / "mock_faults.yaml"

# 期望的故障代码集合（与 seed_base.yaml / mock_faults.yaml 对齐）
EXPECTED_FAULT_CODES = {"E001_OVERHEAT", "E002_STALL", "E003_VOLTAGE_DROP", "E004_SENSOR_FAILURE", "E005_JOINT_LOOSE"}

# 期望的传感器默认值 key 集合
EXPECTED_SENSOR_KEYS = {"imu_gravity_z", "imu_noise_stddev", "voltage_main", "voltage_logic",
                        "pressure_baseline", "pressure_noise_stddev", "battery_drain_rate"}


# ---------------------------------------------------------------------------
# 1. 基础初始化测试：适配器能正常实例化且属性存在
# ---------------------------------------------------------------------------

class TestMockAdapterInit:

    def test_adapter_instantiates_without_error(self):
        """适配器应能无错误地实例化"""
        from app.adapters.mock import MockRobotAdapter
        adapter = MockRobotAdapter()
        assert adapter is not None

    def test_fault_effects_attribute_exists(self):
        """实例应包含 _fault_effects 属性"""
        from app.adapters.mock import MockRobotAdapter
        adapter = MockRobotAdapter()
        assert hasattr(adapter, "_fault_effects"), "_fault_effects 属性不存在"

    def test_fault_effects_is_dict(self):
        """_fault_effects 应为非空字典"""
        from app.adapters.mock import MockRobotAdapter
        adapter = MockRobotAdapter()
        assert isinstance(adapter._fault_effects, dict)
        assert len(adapter._fault_effects) > 0, "_fault_effects 不应为空字典"

    def test_fault_effects_contains_expected_codes(self):
        """_fault_effects 应包含全部 5 个标准故障代码"""
        from app.adapters.mock import MockRobotAdapter
        adapter = MockRobotAdapter()
        loaded_codes = set(adapter._fault_effects.keys())
        missing = EXPECTED_FAULT_CODES - loaded_codes
        assert not missing, f"_fault_effects 缺少故障代码: {missing}"


# ---------------------------------------------------------------------------
# 2. YAML 加载验证：故障效果已从 YAML 加载
# ---------------------------------------------------------------------------

class TestFaultEffectsFromYaml:

    @pytest.fixture(scope="class")
    def yaml_data(self):
        if not _HAS_YAML:
            pytest.skip("pyyaml 未安装，跳过 YAML 直接读取校验")
        with open(MOCK_FAULTS_FILE, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_yaml_fault_effects_match_adapter(self, yaml_data):
        """适配器中 _fault_effects 的内容应与 YAML 文件一致"""
        from app.adapters.mock import MockRobotAdapter
        adapter = MockRobotAdapter()
        yaml_effects = yaml_data.get("fault_effects", {})
        assert adapter._fault_effects == yaml_effects, (
            "适配器 _fault_effects 与 mock_faults.yaml fault_effects 不一致"
        )

    def test_e001_overheat_has_temperature_increase(self):
        """E001_OVERHEAT 效果应包含 temperature_increase 字段"""
        from app.adapters.mock import MockRobotAdapter
        adapter = MockRobotAdapter()
        effect = adapter._fault_effects.get("E001_OVERHEAT", {})
        assert "temperature_increase" in effect, "E001_OVERHEAT 缺少 temperature_increase"
        assert isinstance(effect["temperature_increase"], (int, float))
        assert effect["temperature_increase"] > 0

    def test_e002_stall_has_position_frozen(self):
        """E002_STALL 效果应包含 position_frozen 字段"""
        from app.adapters.mock import MockRobotAdapter
        adapter = MockRobotAdapter()
        effect = adapter._fault_effects.get("E002_STALL", {})
        assert "position_frozen" in effect, "E002_STALL 缺少 position_frozen"
        assert effect["position_frozen"] is True

    def test_e003_voltage_drop_has_battery_drain(self):
        """E003_VOLTAGE_DROP 效果应包含 battery_drain 字段"""
        from app.adapters.mock import MockRobotAdapter
        adapter = MockRobotAdapter()
        effect = adapter._fault_effects.get("E003_VOLTAGE_DROP", {})
        assert "battery_drain" in effect, "E003_VOLTAGE_DROP 缺少 battery_drain"
        assert effect["battery_drain"] > 0

    def test_e004_sensor_failure_has_sensor_noise(self):
        """E004_SENSOR_FAILURE 效果应包含 sensor_noise 字段"""
        from app.adapters.mock import MockRobotAdapter
        adapter = MockRobotAdapter()
        effect = adapter._fault_effects.get("E004_SENSOR_FAILURE", {})
        assert "sensor_noise" in effect, "E004_SENSOR_FAILURE 缺少 sensor_noise"
        assert effect["sensor_noise"] is True

    def test_e005_joint_loose_has_position_noise(self):
        """E005_JOINT_LOOSE 效果应包含 position_noise 字段"""
        from app.adapters.mock import MockRobotAdapter
        adapter = MockRobotAdapter()
        effect = adapter._fault_effects.get("E005_JOINT_LOOSE", {})
        assert "position_noise" in effect, "E005_JOINT_LOOSE 缺少 position_noise"
        assert effect["position_noise"] > 0


# ---------------------------------------------------------------------------
# 3. 传感器默认值验证
# ---------------------------------------------------------------------------

class TestSensorDefaultsFromYaml:

    @pytest.fixture(scope="class")
    def yaml_data(self):
        if not _HAS_YAML:
            pytest.skip("pyyaml 未安装，跳过 YAML 直接读取校验")
        with open(MOCK_FAULTS_FILE, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_module_sensor_defaults_match_yaml(self, yaml_data):
        """模块级 _SENSOR_DEFAULTS 应与 YAML sensor_defaults 一致"""
        from app.adapters import mock as mock_module
        yaml_defaults = yaml_data.get("sensor_defaults", {})
        assert mock_module._SENSOR_DEFAULTS == yaml_defaults, (
            "模块 _SENSOR_DEFAULTS 与 mock_faults.yaml sensor_defaults 不一致"
        )

    def test_sensor_defaults_contains_expected_keys(self, yaml_data):
        """传感器默认值应包含全部预期 key"""
        from app.adapters import mock as mock_module
        missing = EXPECTED_SENSOR_KEYS - set(mock_module._SENSOR_DEFAULTS.keys())
        assert not missing, f"_SENSOR_DEFAULTS 缺少 key: {missing}"

    def test_imu_gravity_z_reasonable(self, yaml_data):
        """imu_gravity_z 应在合理物理范围内（9.0~10.0）"""
        from app.adapters import mock as mock_module
        val = mock_module._SENSOR_DEFAULTS.get("imu_gravity_z")
        assert isinstance(val, (int, float))
        assert 9.0 <= val <= 10.0, f"imu_gravity_z 超出范围: {val}"

    def test_voltage_main_positive(self):
        """voltage_main 应为正数"""
        from app.adapters import mock as mock_module
        val = mock_module._SENSOR_DEFAULTS.get("voltage_main")
        assert isinstance(val, (int, float)) and val > 0

    def test_voltage_logic_positive(self):
        """voltage_logic 应为正数"""
        from app.adapters import mock as mock_module
        val = mock_module._SENSOR_DEFAULTS.get("voltage_logic")
        assert isinstance(val, (int, float)) and val > 0

    def test_battery_drain_rate_positive(self):
        """battery_drain_rate 应为正数"""
        from app.adapters import mock as mock_module
        val = mock_module._SENSOR_DEFAULTS.get("battery_drain_rate")
        assert isinstance(val, (int, float)) and val > 0


# ---------------------------------------------------------------------------
# 4. Fallback 逻辑验证：YAML 不可用时回退到内置默认值
# ---------------------------------------------------------------------------

class TestYamlFallback:

    def test_fallback_returns_default_fault_effects(self, tmp_path, monkeypatch):
        """当 mock_faults.yaml 不存在时，应回退使用内置 _DEFAULT_FAULT_EFFECTS"""
        import app.adapters.mock as mock_module

        # 临时指向不存在的路径
        fake_path = tmp_path / "nonexistent_mock_faults.yaml"
        monkeypatch.setattr(mock_module, "_MOCK_CONFIG_PATH", fake_path)

        fault_effects, sensor_defaults = mock_module._load_mock_config()

        # 回退结果应与内置默认值相同
        assert fault_effects == mock_module._DEFAULT_FAULT_EFFECTS, (
            "YAML 不存在时应回退到 _DEFAULT_FAULT_EFFECTS"
        )
        assert sensor_defaults == mock_module._DEFAULT_SENSOR_DEFAULTS, (
            "YAML 不存在时应回退到 _DEFAULT_SENSOR_DEFAULTS"
        )

    def test_fallback_contains_all_fault_codes(self, tmp_path, monkeypatch):
        """Fallback 时，_DEFAULT_FAULT_EFFECTS 也应包含全部 5 个故障代码"""
        import app.adapters.mock as mock_module

        fake_path = tmp_path / "nonexistent.yaml"
        monkeypatch.setattr(mock_module, "_MOCK_CONFIG_PATH", fake_path)

        fault_effects, _ = mock_module._load_mock_config()
        missing = EXPECTED_FAULT_CODES - set(fault_effects.keys())
        assert not missing, f"Fallback _DEFAULT_FAULT_EFFECTS 缺少故障代码: {missing}"

    def test_fallback_on_invalid_yaml(self, tmp_path, monkeypatch):
        """当 YAML 文件格式损坏时，应回退到内置默认值（不抛出异常）"""
        if not _HAS_YAML:
            pytest.skip("pyyaml 未安装，无法测试 YAML 解析错误场景")
        import app.adapters.mock as mock_module

        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("fault_effects: [invalid: yaml: content", encoding="utf-8")
        monkeypatch.setattr(mock_module, "_MOCK_CONFIG_PATH", bad_yaml)

        # 应不抛异常，并返回默认值
        try:
            fault_effects, sensor_defaults = mock_module._load_mock_config()
            # 若解析成功（部分 YAML 容错），也应满足基本结构
            assert isinstance(fault_effects, dict)
            assert isinstance(sensor_defaults, dict)
        except Exception as e:
            pytest.fail(f"_load_mock_config 在 YAML 损坏时抛出了异常: {e}")

    def test_fallback_on_empty_yaml(self, tmp_path, monkeypatch):
        """当 YAML 文件为空时，应回退到内置默认值"""
        import app.adapters.mock as mock_module

        empty_yaml = tmp_path / "empty.yaml"
        empty_yaml.write_text("", encoding="utf-8")
        monkeypatch.setattr(mock_module, "_MOCK_CONFIG_PATH", empty_yaml)

        fault_effects, sensor_defaults = mock_module._load_mock_config()

        # 空文件 yaml.safe_load 返回 None，data.get() 应回退到默认值
        assert fault_effects == mock_module._DEFAULT_FAULT_EFFECTS
        assert sensor_defaults == mock_module._DEFAULT_SENSOR_DEFAULTS


# ---------------------------------------------------------------------------
# 5. 集成验证：fault_effects 影响实际 inject_fault 行为
# ---------------------------------------------------------------------------

class TestFaultEffectsIntegration:

    @pytest.mark.asyncio
    async def test_inject_fault_uses_loaded_fault_code(self):
        """inject_fault 应能识别 YAML 中定义的所有故障代码"""
        from app.adapters.mock import MockRobotAdapter
        adapter = MockRobotAdapter()
        await adapter.connect()

        for fault_code in EXPECTED_FAULT_CODES:
            result = await adapter.inject_fault(
                fault_code=fault_code,
                target_part="knee_right",
                severity="medium",
            )
            assert result.success is True, f"{fault_code} 注入失败"
            await adapter.clear_fault(fault_code)

        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_unknown_fault_code_raises(self):
        """注入 YAML 中未定义的故障代码应抛出 ValueError"""
        from app.adapters.mock import MockRobotAdapter
        adapter = MockRobotAdapter()
        await adapter.connect()

        with pytest.raises(ValueError, match="Unknown fault code"):
            await adapter.inject_fault(
                fault_code="E999_NONEXISTENT",
                target_part="knee_right",
                severity="low",
            )

        await adapter.disconnect()
