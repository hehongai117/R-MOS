"""
Decision Recalculation Service - Phase 3 Week 9
Provides decision replay and recalculation capabilities for audit and analysis

Features:
- Replay historical decisions
- Recalculate decisions with different parameters
- Generate decision diff reports
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import time
import hashlib
import json


class DecisionType(str, Enum):
    """Types of decisions that can be recalculated"""
    POLICY_EVALUATION = "policy_evaluation"
    RISK_ASSESSMENT = "risk_assessment"
    APPROVAL_DECISION = "approval_decision"
    COMPENSATION_PLAN = "compensation_plan"
    ERROR_RECOVERY = "error_recovery"


class RecalculationStatus(str, Enum):
    """Status of recalculation"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DecisionRecord:
    """Record of a single decision"""
    decision_id: str
    decision_type: DecisionType
    trace_id: str
    timestamp: int
    input_context: Dict[str, Any]
    decision_result: Dict[str, Any]
    risk_level: str
    policy_rules_matched: List[str]
    approved_by: Optional[str] = None


@dataclass
class RecalculationRequest:
    """Request for decision recalculation"""
    original_decision_id: str
    recalculation_type: str
    modified_params: Dict[str, Any] = field(default_factory=dict)
    include_diff: bool = True


@dataclass
class RecalculationResult:
    """Result of decision recalculation"""
    request_id: str
    original_decision: DecisionRecord
    recalculated_result: Dict[str, Any]
    status: RecalculationStatus
    diff: Optional[Dict[str, Any]] = None
    recalculated_at: int = field(default_factory=lambda: int(time.time() * 1000))
    error: Optional[str] = None


@dataclass
class DecisionDiff:
    """Difference between original and recalculated decision"""
    param_changed: str
    original_value: Any
    new_value: Any
    impact_assessment: str


class DecisionRecalculator:
    """
    Service for replaying and recalculating historical decisions.

    Use cases:
    - Audit trail verification
    - Policy what-if analysis
    - Risk assessment recalculation
    - Compliance verification
    """

    def __init__(self):
        # In-memory storage for decision records (would be DB in production)
        self._decisions: Dict[str, DecisionRecord] = {}
        self._recalculations: Dict[str, RecalculationResult] = {}

    def record_decision(
        self,
        decision_type: DecisionType,
        trace_id: str,
        input_context: Dict[str, Any],
        decision_result: Dict[str, Any],
        risk_level: str,
        policy_rules_matched: List[str],
        approved_by: Optional[str] = None,
    ) -> str:
        """Record a decision for future replay"""
        decision_id = f"dec-{hashlib.md5(f'{trace_id}{time.time()}'.encode()).hexdigest()[:12]}"

        record = DecisionRecord(
            decision_id=decision_id,
            decision_type=decision_type,
            trace_id=trace_id,
            timestamp=int(time.time() * 1000),
            input_context=input_context,
            decision_result=decision_result,
            risk_level=risk_level,
            policy_rules_matched=policy_rules_matched,
            approved_by=approved_by,
        )

        self._decisions[decision_id] = record
        return decision_id

    def get_decision(self, decision_id: str) -> Optional[DecisionRecord]:
        """Get a decision record by ID"""
        return self._decisions.get(decision_id)

    def get_decisions_by_trace(self, trace_id: str) -> List[DecisionRecord]:
        """Get all decisions for a given trace"""
        return [
            d for d in self._decisions.values()
            if d.trace_id == trace_id
        ]

    async def recalculate(
        self,
        request: RecalculationRequest,
        policy_evaluator=None,
    ) -> RecalculationResult:
        """
        Recalculate a decision with modified parameters.

        Args:
            request: The recalculation request
            policy_evaluator: Optional policy evaluator for policy decisions
        """
        request_id = f"rec-{hashlib.md5(f'{request.original_decision_id}{time.time()}'.encode()).hexdigest()[:12]}"

        # Get original decision
        original = self._decisions.get(request.original_decision_id)
        if not original:
            return RecalculationResult(
                request_id=request_id,
                original_decision=None,
                recalculated_result={},
                status=RecalculationStatus.FAILED,
                error=f"Decision {request.original_decision_id} not found",
            )

        # Apply modifications
        modified_context = {**original.input_context, **request.modified_params}

        # Recalculate based on decision type
        recalculated_result = await self._recalculate_by_type(
            original, modified_context, policy_evaluator
        )

        # Generate diff if requested
        diff = None
        if request.include_diff:
            diff = self._generate_diff(original, modified_context, recalculated_result)

        result = RecalculationResult(
            request_id=request_id,
            original_decision=original,
            recalculated_result=recalculated_result,
            status=RecalculationStatus.COMPLETED,
            diff=diff,
        )

        self._recalculations[request_id] = result
        return result

    async def _recalculate_by_type(
        self,
        original: DecisionRecord,
        modified_context: Dict[str, Any],
        policy_evaluator,
    ) -> Dict[str, Any]:
        """Recalculate based on decision type"""
        if original.decision_type == DecisionType.POLICY_EVALUATION:
            return await self._recalculate_policy(original, modified_context, policy_evaluator)
        elif original.decision_type == DecisionType.RISK_ASSESSMENT:
            return self._recalculate_risk(original, modified_context)
        elif original.decision_type == DecisionType.APPROVAL_DECISION:
            return self._recalculate_approval(original, modified_context)
        else:
            return original.decision_result

    async def _recalculate_policy(
        self,
        original: DecisionRecord,
        modified_context: Dict[str, Any],
        policy_evaluator,
    ) -> Dict[str, Any]:
        """Recalculate policy evaluation"""
        if policy_evaluator:
            # Use actual policy evaluator
            decision = await policy_evaluator.evaluate(
                resource_type=modified_context.get("resource_type"),
                action=modified_context.get("action"),
                user_context=modified_context.get("user_context", {}),
            )
            return decision.model_dump()

        # Fallback: simple recalculation
        return {
            "allowed": modified_context.get("allowed", True),
            "risk_level": modified_context.get("risk_level", original.risk_level),
            "conditions": modified_context.get("conditions", []),
            "recalculated": True,
            "original_timestamp": original.timestamp,
        }

    def _recalculate_risk(
        self,
        original: DecisionRecord,
        modified_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Recalculate risk assessment"""
        base_risk = modified_context.get("base_risk", original.decision_result.get("risk_score", 50))

        # Adjust risk based on modified parameters
        modifiers = []
        if modified_context.get("increased_oversight"):
            base_risk *= 0.8
            modifiers.append("increased_oversight: -20%")
        if modified_context.get("additional_evidence"):
            base_risk *= 0.9
            modifiers.append("additional_evidence: -10%")
        if modified_context.get("elevated_threat"):
            base_risk *= 1.3
            modifiers.append("elevated_threat: +30%")

        return {
            "risk_score": min(100, max(0, int(base_risk))),
            "risk_level": self._score_to_level(base_risk),
            "modifiers_applied": modifiers,
            "recalculated": True,
        }

    def _recalculate_approval(
        self,
        original: DecisionRecord,
        modified_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Recalculate approval decision"""
        original_approved = original.decision_result.get("approved", False)

        # Check if conditions changed
        new_conditions = modified_context.get("conditions", original.decision_result.get("conditions", []))

        # If all conditions met, approve
        all_conditions_met = all(c.get("met", False) for c in new_conditions if c.get("required", True))

        return {
            "approved": all_conditions_met or original_approved,
            "conditions": new_conditions,
            "reason": modified_context.get("reason", original.decision_result.get("reason")),
            "recalculated": True,
        }

    def _generate_diff(
        self,
        original: DecisionRecord,
        modified_context: Dict[str, Any],
        recalculated_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate diff between original and recalculated"""
        diffs = []

        # Compare input parameters
        for key, original_value in original.input_context.items():
            if key in modified_context:
                new_value = modified_context[key]
                if original_value != new_value:
                    diffs.append(DecisionDiff(
                        param_changed=key,
                        original_value=original_value,
                        new_value=new_value,
                        impact_assessment=self._assess_impact(key, original_value, new_value),
                    ))

        return {
            "input_diffs": [
                {
                    "param": d.param_changed,
                    "original": d.original_value,
                    "new": d.new_value,
                    "impact": d.impact_assessment,
                }
                for d in diffs
            ],
            "result_comparison": {
                "original_risk": original.risk_level,
                "recalculated_risk": recalculated_result.get("risk_level", recalculated_result.get("risk_score")),
                "decision_changed": original.decision_result.get("allowed") != recalculated_result.get("allowed")
                    if "allowed" in original.decision_result else False,
            },
        }

    def _assess_impact(self, param: str, original: Any) -> str:
        """Assess the impact of parameter change"""
        high_impact_params = {"action", "resource_type", "user_role"}
        medium_impact_params = {"priority", "evidence_refs"}

        if param in high_impact_params:
            return "high"
        elif param in medium_impact_params:
            return "medium"
        return "low"

    def _score_to_level(self, score: float) -> str:
        """Convert numeric score to risk level"""
        if score >= 80:
            return "R3"
        elif score >= 60:
            return "R2"
        elif score >= 40:
            return "R1"
        return "R0"

    def get_recalculation_history(
        self,
        decision_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[RecalculationResult]:
        """Get recalculation history"""
        results = list(self._recalculations.values())

        if decision_id:
            results = [r for r in results if r.original_decision.decision_id == decision_id]

        return sorted(results, key=lambda r: r.recalculated_at, reverse=True)[:limit]


# Singleton instance
decision_recalculator = DecisionRecalculator()
