from __future__ import annotations


class VerdictStepGenerator:
    def generate(self, sop_steps: list[dict]) -> list[dict]:
        verdict_steps: list[dict] = []
        for step in sop_steps:
            tool_ids = list(step.get("required_tools", []))
            target_parts = list(step.get("model_targets", []))
            if tool_ids and target_parts:
                validation_type = "tool_and_part_confirmation"
            elif target_parts:
                validation_type = "part_confirmation"
            else:
                validation_type = "instruction_acknowledgement"

            verdict_steps.append(
                {
                    "step_id": step.get("step_id"),
                    "title": step.get("title"),
                    "tool_ids": tool_ids,
                    "target_parts": target_parts,
                    "preconditions": list(step.get("preconditions", [])),
                    "validation_type": validation_type,
                }
            )
        return verdict_steps
