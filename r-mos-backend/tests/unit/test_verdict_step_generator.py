from __future__ import annotations

from app.services.maintenance.verdict_step_generator import VerdictStepGenerator


def test_verdict_step_generator_derives_verdicts_from_sop_steps() -> None:
    generator = VerdictStepGenerator()
    sop_steps = [
        {
            "step_id": "step_001",
            "title": "检查肘关节总成",
            "description": "确认执行器总成处于断电状态",
            "required_tools": ["hex-key"],
            "model_targets": ["elbow"],
            "preconditions": ["robot_power_off"],
        },
        {
            "step_id": "step_002",
            "title": "复核腕关节",
            "description": "确认连接状态",
            "required_tools": [],
            "model_targets": ["wrist"],
            "preconditions": [],
        },
    ]

    verdict_steps = generator.generate(sop_steps)

    assert [step["step_id"] for step in verdict_steps] == ["step_001", "step_002"]
    assert verdict_steps[0]["validation_type"] == "tool_and_part_confirmation"
    assert verdict_steps[0]["tool_ids"] == ["hex-key"]
    assert verdict_steps[0]["target_parts"] == ["elbow"]
    assert verdict_steps[1]["validation_type"] == "part_confirmation"
