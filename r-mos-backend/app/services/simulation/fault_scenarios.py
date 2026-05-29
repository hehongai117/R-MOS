"""Fault scenario definitions for 3 polished cases."""
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class FaultScenario:
    """Static scenario definition."""
    fault_type: str
    name: str
    difficulty: str  # beginner / intermediate / advanced
    affected_joints: list[str]
    telemetry_effects: dict
    alert_threshold: dict
    compound_triggers: list[str] = field(default_factory=list)
    ramp_duration: float = 30.0


@dataclass
class ActiveFault:
    """A running fault instance with time-based progression."""
    fault_type: str
    scenario: FaultScenario
    start_time: float = field(default_factory=time.time)

    def progress(self) -> float:
        elapsed = time.time() - self.start_time
        return min(elapsed / self.scenario.ramp_duration, 1.0)

    @property
    def is_complete(self) -> bool:
        return self.progress() >= 1.0

    def current_effects(self) -> dict:
        p = self.progress()
        effects = {}
        for key, target_value in self.scenario.telemetry_effects.items():
            effects[key] = target_value * p
        return effects


def _load_scenario_overrides() -> dict:
    """从 mock_faults.yaml 加载故障场景的 affected_joints"""
    config_path = Path("data/config/mock_faults.yaml")
    try:
        import yaml
        with open(config_path) as f:
            config = yaml.safe_load(f)
        return config.get("fault_scenarios", {})
    except (FileNotFoundError, Exception):
        return {}


_SCENARIO_OVERRIDES = _load_scenario_overrides()


def _get_affected_joints(fault_key: str, default: list[str]) -> list[str]:
    """从 YAML 覆盖中获取 affected_joints，不存在则 fallback 到硬编码默认值"""
    override = _SCENARIO_OVERRIDES.get(fault_key, {})
    return override.get("affected_joints", default)


FAULT_SCENARIOS: dict[str, FaultScenario] = {
    "E001_OVERHEAT": FaultScenario(
        fault_type="E001_OVERHEAT",
        name="关节过热",
        difficulty="beginner",
        affected_joints=_get_affected_joints("E001_OVERHEAT", ["waist"]),
        telemetry_effects={
            "temperature_increase": 35.0,  # 40°C base + 35 = 75°C threshold
            "torque_noise": 0.5,
        },
        alert_threshold={"temperature": 75.0},
        ramp_duration=30.0,
    ),
    "E005_LOOSE": FaultScenario(
        fault_type="E005_LOOSE",
        name="关节松动",
        difficulty="intermediate",
        affected_joints=_get_affected_joints("E005_LOOSE", ["elbow"]),
        telemetry_effects={
            "position_error_increase": 0.14,  # 0.01 base + 0.14 = 0.15 rad
            "vibration_increase": 2.0,
        },
        alert_threshold={"position_error": 0.10},
        ramp_duration=20.0,
    ),
    "E003_VOLTAGE_DROP": FaultScenario(
        fault_type="E003_VOLTAGE_DROP",
        name="电压跌落+过热联动",
        difficulty="advanced",
        affected_joints=_get_affected_joints("E003_VOLTAGE_DROP", ["shoulder", "elbow"]),
        telemetry_effects={
            "voltage_drop": 5.0,  # 24V - 5 = 19V
            "temperature_increase": 25.0,  # secondary effect on affected joints
        },
        alert_threshold={"voltage": 20.0, "temperature": 70.0},
        compound_triggers=["E001_OVERHEAT"],
        ramp_duration=25.0,
    ),
}

# Legacy alias for backward compatibility
DEMO_SCENARIOS = {
    'knee_overheat': {
        'fault_type': 'knee_overheat',
        'joint_id': 'knee_left',
        'ramp_duration': 30.0,
        'target_temp_increase': 30.0,
        'target_torque_noise': 2.0,
    },
}


@dataclass
class GradualFault:
    """A fault that ramps up over a duration rather than appearing instantly (legacy)."""
    fault_type: str
    joint_id: str
    start_time: float = field(default_factory=time.time)
    ramp_duration: float = 30.0
    target_temp_increase: float = 30.0
    target_torque_noise: float = 2.0

    def progress(self) -> float:
        elapsed = time.time() - self.start_time
        return min(elapsed / self.ramp_duration, 1.0)

    def current_temp_increase(self) -> float:
        return self.target_temp_increase * self.progress()

    def current_torque_noise(self) -> float:
        return self.target_torque_noise * self.progress()

    @property
    def is_complete(self) -> bool:
        return self.progress() >= 1.0


def get_scenario(fault_type: str) -> Optional[FaultScenario]:
    """Get scenario definition by fault type."""
    return FAULT_SCENARIOS.get(fault_type)


def inject_fault(fault_type: str) -> ActiveFault:
    """Create an active fault instance."""
    scenario = FAULT_SCENARIOS[fault_type]
    return ActiveFault(fault_type=fault_type, scenario=scenario)
