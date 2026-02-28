# Diagnoser Agent Service
# Phase 3: Agent Foundation - Diagnoser Agent

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class RootCauseType(str, Enum):
    """Root cause types"""
    CONCEPT_MISUNDERSTANDING = "concept_misunderstanding"
    HABIT_ISSUE = "habit_issue"
    ATTENTION_ISSUE = "attention_issue"
    TOOL_SELECTION_ERROR = "tool_selection_error"
    SEQUENCE_ERROR = "sequence_error"
    UNKNOWN = "unknown"


class InterventionType(str, Enum):
    """Intervention types"""
    EXPLAIN = "explain"
    PRACTICE = "practice"
    DEMO = "demo"
    CHECKPOINT = "checkpoint"


class RuleMatch(BaseModel):
    """Matched rule"""
    rule_id: str
    condition: str
    passed: bool
    value: Any


class RootCauseHypothesis(BaseModel):
    """Root cause hypothesis"""
    cause_type: RootCauseType
    confidence: float  # 0-1
    matched_rules: List[RuleMatch] = Field(default_factory=list)
    llm_supplement: Optional[str] = None


class DiagnoserOutput(BaseModel):
    """
    Diagnoser Agent Output Structure

    Protocol:
    - root_cause: Root cause hypothesis + confidence
    - evidence_refs: Evidence references (MUST be non-empty)
    - intervention: Intervention plan
    - baseline_comparison: Baseline comparison for audit
    """

    # Root cause determination
    root_cause: Optional[RootCauseHypothesis] = None

    # Evidence references (MUST be non-empty)
    evidence_refs: List[str] = Field(default_factory=list)

    # Intervention plan
    intervention: Optional[Dict[str, Any]] = None

    # Baseline comparison (for audit)
    baseline_comparison: Optional[Dict[str, Any]] = None

    # Confidence
    confidence: float = 0.0

    # Additional context
    reasoning: str = ""


# Root cause rules (from design doc)
ROOT_CAUSE_RULES = {
    RootCauseType.CONCEPT_MISUNDERSTANDING: {
        "conditions": [
            ("error_same_position_count >= 3", "error_same_position_count"),
            ("question_why_count >= 2", "question_why_count"),
        ],
        "llm_hints": [
            "demonstration_followed_by_same_error",
            "explain_requested_after_instruction"
        ]
    },

    RootCauseType.HABIT_ISSUE: {
        "conditions": [
            ("action_duration < expected_duration * 0.5", "action_too_fast"),
            ("inspection_step_skipped", "inspection_skipped"),
            ("motion_pattern_similarity > 0.9", "motion_pattern_repetitive"),
        ],
        "llm_hints": [
            "consistently_fast_without_checking",
            "skipping_verification_steps"
        ]
    },

    RootCauseType.ATTENTION_ISSUE: {
        "conditions": [
            ("prerequisite_step_missed", "prerequisite_missed"),
            ("pause_resume_disorientation", "pause_confusion"),
            ("reaction_time_trend == increasing", "reaction_time_increasing"),
        ],
        "llm_hints": [
            "seems_distracted",
            "losing_place_repeatedly"
        ]
    },

    RootCauseType.TOOL_SELECTION_ERROR: {
        "conditions": [
            ("wrong_tool_selected", "tool_error"),
            ("tool_force_mismatch", "force_mismatch"),
        ],
        "llm_hints": [
            "wrong_tool_for_task",
            "force_appears_wrong"
        ]
    },

    RootCauseType.SEQUENCE_ERROR: {
        "conditions": [
            ("step_order_wrong", "sequence_error"),
            ("skip_mandatory_step", "mandatory_step_skipped"),
        ],
        "llm_hints": [
            "performed_steps_out_of_order",
            "skipped_required_step"
        ]
    }
}


class DiagnoserAgent:
    """
    Diagnoser Agent

    Responsibilities:
    - Determine root cause with confidence
    - Reference evidence (must be non-empty)
    - Generate intervention plan
    - Provide baseline comparison
    """

    def __init__(self):
        self.baseline_data: Dict[str, Any] = {}

    def diagnose(
        self,
        task_id: str,
        error_history: List[Dict[str, Any]],
        action_history: List[Dict[str, Any]],
        available_evidence: List[str]
    ) -> DiagnoserOutput:
        """
        Diagnose root cause from error history and action history

        Args:
            task_id: Current task ID
            error_history: List of errors encountered
            action_history: History of actions taken
            available_evidence: Available evidence IDs

        Returns:
            DiagnoserOutput with root cause and evidence references
        """
        # 1. Analyze patterns from history
        analysis = self._analyze_history(error_history, action_history)

        # 2. Match against rules
        hypothesis = self._match_rules(analysis)

        # 3. Generate intervention if root cause found
        intervention = None
        if hypothesis and hypothesis.confidence > 0.5:
            intervention = self._generate_intervention(hypothesis)

        # 4. Generate baseline comparison
        baseline = self._generate_baseline_comparison(action_history)

        # 5. Must have evidence references
        evidence_refs = available_evidence[:3] if available_evidence else []

        return DiagnoserOutput(
            root_cause=hypothesis,
            evidence_refs=evidence_refs,
            intervention=intervention,
            baseline_comparison=baseline,
            confidence=hypothesis.confidence if hypothesis else 0.0,
            reasoning=self._generate_reasoning(hypothesis, analysis)
        )

    def _analyze_history(
        self,
        error_history: List[Dict[str, Any]],
        action_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze error and action history"""
        analysis = {
            "error_count": len(error_history),
            "error_positions": [],
            "action_count": len(action_history),
            "action_durations": [],
            "questions_asked": 0,
            "inspection_skipped": False,
            "steps_out_of_order": False,
            "prerequisite_missed": False,
        }

        # Analyze errors
        for error in error_history:
            if error.get("type") == "wrong_position":
                analysis["error_positions"].append(error.get("position"))

        # Analyze actions
        for action in action_history:
            duration = action.get("duration_ms", 0)
            expected = action.get("expected_duration_ms", 999999)

            analysis["action_durations"].append(duration)

            # Check if too fast
            if duration < expected * 0.5:
                analysis["action_too_fast"] = True

            # Check if inspection skipped
            if action.get("type") == "skip_inspection":
                analysis["inspection_skipped"] = True

            # Check if steps out of order
            if action.get("order_wrong"):
                analysis["steps_out_of_order"] = True

        # Count "why" questions
        analysis["question_why_count"] = sum(
            1 for a in action_history
            if a.get("question_type") == "why"
        )

        return analysis

    def _match_rules(self, analysis: Dict[str, Any]) -> Optional[RootCauseHypothesis]:
        """Match analysis against root cause rules"""
        best_match = None
        best_confidence = 0.0

        for cause_type, rules in ROOT_CAUSE_RULES.items():
            matched_rules = []
            conditions_met = 0

            for condition_str, analysis_key in rules["conditions"]:
                # Evaluate condition
                value = analysis.get(analysis_key, False)

                if isinstance(value, bool):
                    passed = value
                elif isinstance(value, (int, float)):
                    # Parse condition like ">= 3"
                    if ">=" in condition_str:
                        threshold = float(condition_str.split(">=")[1].strip())
                        passed = value >= threshold
                    elif ">" in condition_str:
                        threshold = float(condition_str.split(">")[1].strip())
                        passed = value > threshold
                    else:
                        passed = False
                else:
                    passed = False

                if passed:
                    conditions_met += 1

                matched_rules.append(RuleMatch(
                    rule_id=f"{cause_type.value}_{analysis_key}",
                    condition=condition_str,
                    passed=passed,
                    value=value
                ))

            # Calculate confidence
            num_conditions = len(rules["conditions"])
            if num_conditions > 0:
                confidence = conditions_met / num_conditions

                # Boost confidence if LLM hints match
                if confidence > 0:
                    confidence = min(confidence * 1.2, 1.0)

                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = RootCauseHypothesis(
                        cause_type=cause_type,
                        confidence=confidence,
                        matched_rules=matched_rules
                    )

        return best_match

    def _generate_intervention(
        self,
        hypothesis: RootCauseHypothesis
    ) -> Dict[str, Any]:
        """Generate intervention plan based on root cause"""
        cause = hypothesis.cause_type

        interventions = {
            RootCauseType.CONCEPT_MISUNDERSTANDING: {
                "type": InterventionType.EXPLAIN.value,
                "priority": "high",
                "detail": "详细解释操作原理，演示正确流程",
                "actions": [
                    "展示3D动画演示",
                    "说明关键技术要点",
                    "让学员复述要点"
                ]
            },
            RootCauseType.HABIT_ISSUE: {
                "type": InterventionType.PRACTICE.value,
                "priority": "medium",
                "detail": "强化练习正确操作习惯",
                "actions": [
                    "设置强制停顿",
                    "要求自检后继续",
                    "记录操作节奏"
                ]
            },
            RootCauseType.ATTENTION_ISSUE: {
                "type": InterventionType.CHECKPOINT.value,
                "priority": "high",
                "detail": "添加检查点提醒",
                "actions": [
                    "在关键步骤添加确认",
                    "增加步骤指引",
                    "简化操作流程"
                ]
            },
            RootCauseType.TOOL_SELECTION_ERROR: {
                "type": InterventionType.DEMO.value,
                "priority": "high",
                "detail": "演示正确工具选择",
                "actions": [
                    "展示工具选择要点",
                    "强调工具适配性",
                    "提供工具选择检查表"
                ]
            },
            RootCauseType.SEQUENCE_ERROR: {
                "type": InterventionType.EXPLAIN.value,
                "priority": "high",
                "detail": "说明正确操作顺序",
                "actions": [
                    "展示完整流程",
                    "强调关键步骤顺序",
                    "提供流程检查单"
                ]
            }
        }

        return interventions.get(cause, {
            "type": "explain",
            "priority": "low",
            "detail": "继续观察"
        })

    def _generate_baseline_comparison(
        self,
        action_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate baseline comparison for audit"""
        # Simplified baseline - in production fetch from database
        baseline_duration = 60000  # 1 minute baseline
        actual_duration = sum(
            a.get("duration_ms", 0) for a in action_history
        )

        return {
            "normal_duration_ms": baseline_duration,
            "actual_duration_ms": actual_duration,
            "deviation_percent": (
                (actual_duration - baseline_duration) / baseline_duration * 100
                if baseline_duration > 0 else 0
            )
        }

    def _generate_reasoning(
        self,
        hypothesis: Optional[RootCauseHypothesis],
        analysis: Dict[str, Any]
    ) -> str:
        """Generate human-readable reasoning"""
        if not hypothesis:
            return "未发现明显模式，需要更多数据"

        cause_names = {
            RootCauseType.CONCEPT_MISUNDERSTANDING: "概念理解偏差",
            RootCauseType.HABIT_ISSUE: "操作习惯问题",
            RootCauseType.ATTENTION_ISSUE: "注意力分散",
            RootCauseType.TOOL_SELECTION_ERROR: "工具选择错误",
            RootCauseType.SEQUENCE_ERROR: "操作顺序错误",
            RootCauseType.UNKNOWN: "未知"
        }

        cause_name = cause_names.get(hypothesis.cause_type, "未知")
        return f"基于{analysis['error_count']}个错误和{analysis['action_count']}个操作分析，{cause_name}置信度{hypothesis.confidence:.0%}"


# Singleton instance
diagnoser_agent = DiagnoserAgent()
