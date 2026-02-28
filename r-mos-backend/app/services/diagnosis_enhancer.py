# Enhanced Diagnosis Service
# Phase 4: Diagnosis Enhancement

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class DiagnosisSeverity(str, Enum):
    """Diagnosis severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class BaselineComparison(BaseModel):
    """Comparison against baseline"""
    baseline_value: float
    actual_value: float
    deviation_percent: float
    within_tolerance: bool


class DiagnosisFinding(BaseModel):
    """Individual diagnosis finding"""
    code: str
    message: str
    severity: DiagnosisSeverity
    evidence_refs: List[str] = Field(default_factory=list)


class DiagnosisRecommendation(BaseModel):
    """Diagnosis recommendation"""
    code: str
    message: str
    priority: str  # high, medium, low
    action_type: Optional[str] = None


class EnhancedDiagnosisReport(BaseModel):
    """Enhanced diagnosis report with Phase 4 features"""
    report_id: str
    task_id: str
    attempt_id: int

    # Root cause
    root_cause: Optional[str] = None
    root_cause_confidence: float = 0.0

    # Findings with evidence references (MUST be non-empty)
    findings: List[DiagnosisFinding] = Field(default_factory=list)

    # Recommendations
    recommendations: List[DiagnosisRecommendation] = Field(default_factory=list)

    # Baseline comparison
    baseline_comparison: Optional[BaselineComparison] = None

    # Metrics
    error_count: int = 0
    skip_count: int = 0
    duration_ms: int = 0

    # Timestamps
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class DiagnosisRule(BaseModel):
    """Diagnosis rule definition"""
    rule_id: str
    name: str
    description: str

    # Conditions
    conditions: Dict[str, Any] = Field(default_factory=dict)

    # Findings to generate
    findings: List[DiagnosisFinding] = Field(default_factory=list)

    # Recommendations
    recommendations: List[DiagnosisRecommendation] = Field(default_factory=list)


# Predefined diagnosis rules
DIAGNOSIS_RULES = {
    "error_repetition": {
        "name": "Error Repetition",
        "description": "Same error repeated multiple times",
        "findings": [
            {
                "code": "ERR_REPEAT",
                "message": "Same error repeated {count} times",
                "severity": "error"
            }
        ],
        "recommendations": [
            {
                "code": "DEMO_REQUIRED",
                "message": "Require demonstration before retry",
                "priority": "high",
                "action_type": "demo"
            }
        ]
    },
    "too_fast": {
        "name": "Operation Too Fast",
        "description": "Actions completed too quickly",
        "findings": [
            {
                "code": "TOO_FAST",
                "message": "Operations completed in {duration}ms (expected >{min}ms)",
                "severity": "warning"
            }
        ],
        "recommendations": [
            {
                "code": "SLOW_DOWN",
                "message": "Slow down and verify each step",
                "priority": "medium",
                "action_type": "checkpoint"
            }
        ]
    },
    "skip_step": {
        "name": "Step Skipped",
        "description": "Mandatory step was skipped",
        "findings": [
            {
                "code": "STEP_SKIP",
                "message": "Step {step_id} was skipped",
                "severity": "error"
            }
        ],
        "recommendations": [
            {
                "code": "REQUIRE_STEP",
                "message": "Complete all mandatory steps",
                "priority": "high",
                "action_type": "explain"
            }
        ]
    },
    "tool_mismatch": {
        "name": "Tool Mismatch",
        "description": "Wrong tool selected",
        "findings": [
            {
                "code": "WRONG_TOOL",
                "message": "Incorrect tool for operation",
                "severity": "error"
            }
        ],
        "recommendations": [
            {
                "code": "SELECT_TOOL",
                "message": "Select appropriate tool",
                "priority": "high",
                "action_type": "demo"
            }
        ]
    }
}


class DiagnosisEnhancer:
    """
    Phase 4: Diagnosis Enhancement

    Features:
    - Root cause determination with confidence
    - Evidence references (must be non-empty)
    - Baseline comparison
    - Intervention plan generation
    """

    def __init__(self):
        self.baseline_metrics: Dict[str, Dict[str, float]] = {}

    def set_baseline(
        self,
        metric_name: str,
        expected_value: float,
        tolerance_percent: float = 20.0
    ) -> None:
        """Set baseline for comparison"""
        self.baseline_metrics[metric_name] = {
            "expected": expected_value,
            "tolerance": tolerance_percent
        }

    def diagnose(
        self,
        task_id: str,
        attempt_id: int,
        error_history: List[Dict[str, Any]],
        action_history: List[Dict[str, Any]],
        evidence_refs: List[str]
    ) -> EnhancedDiagnosisReport:
        """Generate enhanced diagnosis report"""

        report = EnhancedDiagnosisReport(
            report_id=f"diag-{task_id}-{attempt_id}",
            task_id=task_id,
            attempt_id=attempt_id
        )

        # 1. Analyze errors
        report.error_count = len(error_history)
        report.skip_count = sum(1 for a in action_history if a.get("skipped"))
        report.duration_ms = sum(a.get("duration_ms", 0) for a in action_history)

        # 2. Determine root cause
        root_cause = self._determine_root_cause(error_history, action_history)
        report.root_cause = root_cause["type"]
        report.root_cause_confidence = root_cause["confidence"]

        # 3. Generate findings with evidence refs (MUST be non-empty)
        findings = self._generate_findings(error_history, action_history)
        for finding in findings:
            # Ensure each finding has evidence references
            finding.evidence_refs = evidence_refs[:2] if evidence_refs else []
        report.findings = findings

        # 4. Generate recommendations
        report.recommendations = self._generate_recommendations(
            root_cause["type"],
            findings
        )

        # 5. Baseline comparison
        report.baseline_comparison = self._compare_baseline(
            report.duration_ms,
            len(action_history)
        )

        return report

    def _determine_root_cause(
        self,
        error_history: List[Dict],
        action_history: List[Dict]
    ) -> Dict[str, Any]:
        """Determine root cause from history"""
        # Check for error repetition
        error_positions = [e.get("position") for e in error_history]
        position_counts = {}
        for pos in error_positions:
            position_counts[pos] = position_counts.get(pos, 0) + 1

        max_repeat = max(position_counts.values()) if position_counts else 0

        if max_repeat >= 3:
            return {"type": "concept_misunderstanding", "confidence": 0.85}

        # Check for too fast
        avg_duration = sum(a.get("duration_ms", 0) for a in action_history) / max(len(action_history), 1)
        if avg_duration < 5000:  # Less than 5 seconds average
            return {"type": "habit_issue", "confidence": 0.75}

        # Check for skipped steps
        skip_count = sum(1 for a in action_history if a.get("skipped"))
        if skip_count > 0:
            return {"type": "attention_issue", "confidence": 0.7}

        return {"type": "unknown", "confidence": 0.0}

    def _generate_findings(
        self,
        error_history: List[Dict],
        action_history: List[Dict]
    ) -> List[DiagnosisFinding]:
        """Generate diagnosis findings"""
        findings = []

        # Error repetition finding
        error_positions = [e.get("position") for e in error_history]
        position_counts = {}
        for pos in error_positions:
            position_counts[pos] = position_counts.get(pos, 0) + 1

        max_repeat = max(position_counts.values()) if position_counts else 0
        if max_repeat >= 3:
            findings.append(DiagnosisFinding(
                code="ERR_REPEAT",
                message=f"Same error repeated {max_repeat} times",
                severity=DiagnosisSeverity.ERROR
            ))

        # Too fast finding
        avg_duration = sum(a.get("duration_ms", 0) for a in action_history) / max(len(action_history), 1)
        if avg_duration > 0 and avg_duration < 5000:
            findings.append(DiagnosisFinding(
                code="TOO_FAST",
                message=f"Average action duration {avg_duration}ms is too fast",
                severity=DiagnosisSeverity.WARNING
            ))

        # Skip finding
        skip_count = sum(1 for a in action_history if a.get("skipped"))
        if skip_count > 0:
            findings.append(DiagnosisFinding(
                code="STEP_SKIP",
                message=f"{skip_count} steps were skipped",
                severity=DiagnosisSeverity.ERROR
            ))

        return findings

    def _generate_recommendations(
        self,
        root_cause: str,
        findings: List[DiagnosisFinding]
    ) -> List[DiagnosisRecommendation]:
        """Generate recommendations based on root cause and findings"""
        recommendations = []

        # Root cause based recommendations
        cause_recommendations = {
            "concept_misunderstanding": [
                DiagnosisRecommendation(
                    code="DEMO_REQUIRED",
                    message="Require demonstration before retry",
                    priority="high",
                    action_type="demo"
                )
            ],
            "habit_issue": [
                DiagnosisRecommendation(
                    code="FORCE_CHECKPOINT",
                    message="Add mandatory checkpoints",
                    priority="medium",
                    action_type="checkpoint"
                )
            ],
            "attention_issue": [
                DiagnosisRecommendation(
                    code="SIMPLIFY",
                    message="Simplify task into smaller steps",
                    priority="high",
                    action_type="explain"
                )
            ]
        }

        if root_cause in cause_recommendations:
            recommendations.extend(cause_recommendations[root_cause])

        # Finding based recommendations
        for finding in findings:
            if finding.code == "ERR_REPEAT":
                recommendations.append(DiagnosisRecommendation(
                    code="EXPLAIN_PRINCIPLE",
                    message="Explain the underlying principle",
                    priority="high",
                    action_type="explain"
                ))

        return recommendations

    def _compare_baseline(
        self,
        actual_duration_ms: int,
        action_count: int
    ) -> Optional[BaselineComparison]:
        """Compare against baseline metrics"""
        if "duration" not in self.baseline_metrics:
            return None

        baseline = self.baseline_metrics["duration"]
        expected = baseline["expected"]
        tolerance = baseline["tolerance"]

        deviation = ((actual_duration_ms - expected) / expected * 100) if expected > 0 else 0
        within_tolerance = abs(deviation) <= tolerance

        return BaselineComparison(
            baseline_value=expected,
            actual_value=float(actual_duration_ms),
            deviation_percent=deviation,
            within_tolerance=within_tolerance
        )


# Singleton instance
diagnosis_enhancer = DiagnosisEnhancer()
