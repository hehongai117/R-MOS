# Coach Agent Service
# Phase 3: Agent Foundation - Coach Agent

import uuid
import time
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class ActionType(str, Enum):
    """Valid action types"""
    SELECT_TOOL = "select_tool"
    REMOVE_SCREW = "remove_screw"
    DETACH_PART = "detach_part"
    INSPECT = "inspect"
    VERIFY = "verify"
    EXPLAIN = "explain"
    DEMO = "demo"
    CHECKPOINT = "checkpoint"


class RiskLevel(str, Enum):
    """Risk levels"""
    R0 = "R0"  # No risk
    R1 = "R1"  # Low risk
    R2 = "R2"  # Medium risk
    R3 = "R3"  # High risk


class RiskHandling(str, Enum):
    """Risk handling strategies"""
    BLOCK = "block"
    WARN = "warn"
    CONFIRM = "confirm"
    DEMO = "demo"


class ActionSuggestion(BaseModel):
    """Suggested action structure"""
    action_id: str = Field(default_factory=lambda: f"action-{uuid.uuid4().hex[:8]}")
    action_type: ActionType
    target: Optional[str] = None
    targets: List[str] = Field(default_factory=list)

    # Explanation
    explanation: str = ""
    principle: str = ""  # Technical principle

    # Risk
    risk_level: RiskLevel = RiskLevel.R1
    risk_handling: RiskHandling = RiskHandling.WARN

    # Evidence
    evidence_required: List[str] = Field(default_factory=list)
    evidence_produced: List[str] = Field(default_factory=list)

    # Timing
    expected_duration_seconds: int = 0


class CoachOutput(BaseModel):
    """
    Coach Agent Output Structure

    Protocol:
    - next_action: Suggested next action
    - explain: Explanation for current action
    - risk_events: Risk event reports
    """

    # Next action recommendation
    next_action: Optional[ActionSuggestion] = None

    # Explanation for current state/action
    explanation: str = ""
    principle: str = ""  # Technical principle behind the action

    # Risk events (if any)
    risk_events: List[Dict[str, Any]] = Field(default_factory=list)

    # Confidence score
    confidence: float = 1.0

    # Alternative suggestions
    alternatives: List[ActionSuggestion] = Field(default_factory=list)

    # Metadata
    reasoning: str = ""  # Why this recommendation


class CoachAgent:
    """
    Coach Agent

    Responsibilities:
    - Recommend next_action
    - Provide explanations and principles
    - Report risk_events
    - Guide trainee through task steps
    """

    def __init__(self):
        self.task_steps: Dict[str, List[Dict]] = {}

    def analyze_and_recommend(
        self,
        task_id: str,
        current_step: int,
        step_history: List[Dict[str, Any]],
        trainee_action: Optional[Dict[str, Any]] = None
    ) -> CoachOutput:
        """
        Analyze current state and recommend next action

        Args:
            task_id: Current task ID
            current_step: Current step index
            step_history: History of completed steps
            trainee_action: Last action taken by trainee (optional)

        Returns:
            CoachOutput with recommendation
        """
        # Analyze trainee's last action if provided
        if trainee_action:
            analysis = self._analyze_action(trainee_action)
            if analysis["needs_intervention"]:
                return self._create_intervention_output(analysis)

        # Get next step recommendation
        next_step = self._get_next_step(task_id, current_step, step_history)

        if next_step:
            return self._create_next_action_output(next_step)
        else:
            return self._create_completion_output()

    def _analyze_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze trainee's action for issues"""
        # Simplified analysis - in production use more sophisticated logic

        result = {
            "action_id": action.get("action_id"),
            "is_correct": True,
            "needs_intervention": False,
            "issues": [],
            "risk_detected": False
        }

        # Check for potential issues
        action_type = action.get("action_type", "")

        # Check timing
        duration = action.get("duration_ms", 0)
        expected_duration = action.get("expected_duration_ms", 999999)

        if duration < expected_duration * 0.3:
            result["issues"].append("action_too_fast")
            result["needs_intervention"] = True

        # Check if required evidence was collected
        if not action.get("evidence_collected"):
            result["issues"].append("missing_evidence")
            result["needs_intervention"] = True

        return result

    def _get_next_step(
        self,
        task_id: str,
        current_step: int,
        step_history: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Get next step recommendation"""
        # In production, fetch from task plan
        # Simplified here

        steps = self.task_steps.get(task_id, [
            {"step_id": "step-1", "type": "select_tool", "target": "screwdriver"},
            {"step_id": "step-2", "type": "remove_screw", "target": "screw-01"},
            {"step_id": "step-3", "type": "detach_part", "target": "cover"},
            {"step_id": "step-4", "type": "inspect", "target": "internal"},
            {"step_id": "step-5", "type": "verify", "target": "complete"}
        ])

        next_idx = current_step + 1
        if next_idx < len(steps):
            return steps[next_idx]
        return None

    def _create_next_action_output(self, step: Dict[str, Any]) -> CoachOutput:
        """Create output for next action recommendation"""
        action_type = ActionType(step.get("type", "inspect"))
        target = step.get("target", "")

        # Determine risk level based on action type
        risk_level = self._get_risk_for_action(action_type)

        next_action = ActionSuggestion(
            action_type=action_type,
            target=target,
            explanation=self._get_explanation(action_type, target),
            principle=self._get_principle(action_type),
            risk_level=risk_level,
            risk_handling=self._get_risk_handling(risk_level),
            evidence_required=self._get_evidence_requirements(action_type),
            evidence_produced=self._get_evidence_produced(action_type)
        )

        return CoachOutput(
            next_action=next_action,
            explanation=f"下一步操作：{self._get_action_description(action_type, target)}",
            principle=next_action.principle,
            confidence=0.95,
            reasoning=f"根据任务流程，当前应执行{action_type.value}操作"
        )

    def _create_intervention_output(self, analysis: Dict[str, Any]) -> CoachOutput:
        """Create output when intervention is needed"""
        issues = analysis.get("issues", [])

        intervention_action = ActionSuggestion(
            action_type=ActionType.EXPLAIN,
            explanation="我注意到您的操作有些问题，让我来解释一下...",
            risk_level=RiskLevel.R0,
            risk_handling=RiskHandling.WARN
        )

        if "action_too_fast" in issues:
            intervention_action.explanation = "您操作得有点快。请仔细确认每个步骤后再继续，这样能更好地掌握技巧。"
        elif "missing_evidence" in issues:
            intervention_action.explanation = "请确保收集了必要的证据，这有助于后续复盘和诊断。"

        return CoachOutput(
            next_action=intervention_action,
            explanation=intervention_action.explanation,
            risk_events=[{"issue": issue} for issue in issues],
            confidence=0.8,
            reasoning="检测到操作异常，需要干预"
        )

    def _create_completion_output(self) -> CoachOutput:
        """Create output when task is complete"""
        return CoachOutput(
            next_action=None,
            explanation="恭喜！您已完成所有步骤。",
            confidence=1.0,
            reasoning="任务流程已完成"
        )

    def _get_risk_for_action(self, action_type: ActionType) -> RiskLevel:
        """Determine risk level for action type"""
        risk_map = {
            ActionType.SELECT_TOOL: RiskLevel.R0,
            ActionType.REMOVE_SCREW: RiskLevel.R1,
            ActionType.DETACH_PART: RiskLevel.R2,
            ActionType.INSPECT: RiskLevel.R0,
            ActionType.VERIFY: RiskLevel.R0,
            ActionType.EXPLAIN: RiskLevel.R0,
            ActionType.DEMO: RiskLevel.R0,
            ActionType.CHECKPOINT: RiskLevel.R0,
        }
        return risk_map.get(action_type, RiskLevel.R1)

    def _get_risk_handling(self, risk_level: RiskLevel) -> RiskHandling:
        """Determine risk handling strategy"""
        handling_map = {
            RiskLevel.R0: RiskHandling.WARN,
            RiskLevel.R1: RiskHandling.WARN,
            RiskLevel.R2: RiskHandling.CONFIRM,
            RiskLevel.R3: RiskHandling.BLOCK,
        }
        return handling_map.get(risk_level, RiskHandling.WARN)

    def _get_explanation(self, action_type: ActionType, target: str) -> str:
        """Get explanation for action"""
        explanations = {
            ActionType.SELECT_TOOL: f"选择工具：{target}",
            ActionType.REMOVE_SCREW: f"拆卸螺丝：{target}",
            ActionType.DETACH_PART: f"拆卸部件：{target}",
            ActionType.INSPECT: f"检查内部：{target}",
            ActionType.VERIFY: f"验证完成：{target}",
        }
        return explanations.get(action_type, f"执行操作：{action_type.value}")

    def _get_principle(self, action_type: ActionType) -> str:
        """Get technical principle for action"""
        principles = {
            ActionType.SELECT_TOOL: "选择合适工具是安全操作的基础",
            ActionType.REMOVE_SCREW: "均匀用力，避免螺丝损坏",
            ActionType.DETACH_PART: "按顺序拆卸，注意连接件",
            ActionType.INSPECT: "仔细观察，记录异常",
            ActionType.VERIFY: "对照标准，验证完整性",
        }
        return principles.get(action_type, "")

    def _get_action_description(self, action_type: ActionType, target: str) -> str:
        """Get human-readable action description"""
        return f"{action_type.value.replace('_', ' ')} - {target}"

    def _get_evidence_requirements(self, action_type: ActionType) -> List[str]:
        """Get required evidence for action"""
        requirements = {
            ActionType.SELECT_TOOL: [],
            ActionType.REMOVE_SCREW: ["trajectory"],
            ActionType.DETACH_PART: ["trajectory", "screenshot"],
            ActionType.INSPECT: ["screenshot", "sensor_reading"],
            ActionType.VERIFY: ["verdict"],
        }
        return requirements.get(action_type, [])

    def _get_evidence_produced(self, action_type: ActionType) -> List[str]:
        """Get evidence produced by action"""
        produced = {
            ActionType.SELECT_TOOL: ["trajectory"],
            ActionType.REMOVE_SCREW: ["trajectory"],
            ActionType.DETACH_PART: ["trajectory", "screenshot"],
            ActionType.INSPECT: ["screenshot", "sensor_reading"],
            ActionType.VERIFY: ["verdict"],
        }
        return produced.get(action_type, [])


# Singleton instance
coach_agent = CoachAgent()
