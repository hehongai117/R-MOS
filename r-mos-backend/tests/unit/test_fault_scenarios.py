"""Fault scenario definitions tests."""
from app.services.simulation.fault_scenarios import (
    FAULT_SCENARIOS,
    FaultScenario,
    inject_fault,
    get_scenario,
)


def test_three_scenarios_defined():
    """3 fault scenarios exist."""
    assert "E001_OVERHEAT" in FAULT_SCENARIOS
    assert "E005_LOOSE" in FAULT_SCENARIOS
    assert "E003_VOLTAGE_DROP" in FAULT_SCENARIOS


def test_e001_scenario_structure():
    """E001 scenario has correct structure."""
    scenario = get_scenario("E001_OVERHEAT")
    assert scenario is not None
    assert scenario.fault_type == "E001_OVERHEAT"
    assert scenario.affected_joints == ["waist"]
    assert scenario.difficulty == "beginner"
    assert scenario.telemetry_effects["temperature_increase"] == 35.0


def test_e003_compound_scenario():
    """E003 compound scenario triggers E001 as secondary."""
    scenario = get_scenario("E003_VOLTAGE_DROP")
    assert scenario.difficulty == "advanced"
    assert scenario.compound_triggers == ["E001_OVERHEAT"]
    assert "shoulder" in scenario.affected_joints or "elbow" in scenario.affected_joints


def test_inject_fault_creates_active_fault():
    """inject_fault returns active fault with progress tracking."""
    fault = inject_fault("E001_OVERHEAT")
    assert fault.fault_type == "E001_OVERHEAT"
    assert fault.progress() >= 0.0
    assert not fault.is_complete
