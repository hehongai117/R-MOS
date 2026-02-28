# Evidence Enforcement Service
# Phase 3: Evidence Reference Enforcement

from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field
from enum import Enum


class EvidenceRequirement(BaseModel):
    """Required evidence for an action/step"""
    evidence_type: str
    description: str
    required: bool = True


class EvidenceReference(BaseModel):
    """Reference to evidence"""
    evidence_id: str
    evidence_type: str
    description: str = ""


class EvidenceEnforcementConfig(BaseModel):
    """Configuration for evidence enforcement"""
    enforce_evidence_collection: bool = True
    enforce_evidence_references: bool = True
    allow_empty_references: bool = False


class EvidenceEnforcer:
    """
    Evidence Reference Enforcer

    Responsibilities:
    - Validate required evidence is collected before proceeding
    - Enforce evidence references in conclusions/diagnoses
    - Block operations without proper evidence
    """

    def __init__(self, config: EvidenceEnforcementConfig = None):
        self.config = config or EvidenceEnforcementConfig()
        self._evidence_requirements: Dict[str, List[EvidenceRequirement]] = {}
        self._collected_evidence: Dict[str, Set[str]] = {}

    def register_requirements(
        self,
        step_id: str,
        requirements: List[EvidenceRequirement]
    ) -> None:
        """Register evidence requirements for a step"""
        self._evidence_requirements[step_id] = requirements
        self._collected_evidence[step_id] = set()

    def collect_evidence(
        self,
        step_id: str,
        evidence_id: str,
        evidence_type: str
    ) -> bool:
        """
        Record evidence collection

        Returns True if successful
        """
        if step_id not in self._collected_evidence:
            self._collected_evidence[step_id] = set()

        self._collected_evidence[step_id].add(evidence_id)
        return True

    def validate_step_completion(
        self,
        step_id: str
    ) -> tuple[bool, List[str]]:
        """
        Validate that all required evidence is collected for step completion

        Returns:
            (is_valid, missing_evidence_types)
        """
        requirements = self._evidence_requirements.get(step_id, [])
        collected = self._collected_evidence.get(step_id, set())

        missing = []
        for req in requirements:
            if req.required:
                # Check if any collected evidence matches this type
                found = any(
                    ev_type == req.evidence_type
                    for ev_type in collected
                )
                if not found:
                    missing.append(req.evidence_type)

        is_valid = len(missing) == 0
        return is_valid, missing

    def enforce_evidence_references(
        self,
        conclusion: Dict[str, Any],
        available_evidence: List[str]
    ) -> tuple[bool, str]:
        """
        Enforce that conclusions reference evidence

        Args:
            conclusion: The conclusion to validate
            available_evidence: List of available evidence IDs

        Returns:
            (is_valid, error_message)
        """
        if self.config.allow_empty_references:
            return True, ""

        # Check if conclusion has evidence references
        evidence_refs = conclusion.get("evidence_refs", [])

        if not evidence_refs:
            return False, "Conclusion must reference evidence"

        # Verify all referenced evidence exists
        for ref in evidence_refs:
            if ref not in available_evidence:
                return False, f"Referenced evidence {ref} not found"

        return True, ""

    def get_required_evidence(
        self,
        step_id: str
    ) -> List[EvidenceRequirement]:
        """Get required evidence types for a step"""
        return self._evidence_requirements.get(step_id, [])

    def get_collected_evidence(
        self,
        step_id: str
    ) -> Set[str]:
        """Get collected evidence IDs for a step"""
        return self._collected_evidence.get(step_id, set())

    def get_evidence_status(
        self,
        step_id: str
    ) -> Dict[str, Any]:
        """
        Get evidence collection status for a step

        Returns:
            {
                "step_id": str,
                "required": List[str],
                "collected": List[str],
                "missing": List[str],
                "complete": bool
            }
        """
        requirements = self._evidence_requirements.get(step_id, [])
        collected = self._collected_evidence.get(step_id, set())

        required_types = [r.evidence_type for r in requirements if r.required]
        missing_types = []

        for req in requirements:
            if req.required and req.evidence_type not in collected:
                missing_types.append(req.evidence_type)

        return {
            "step_id": step_id,
            "required": required_types,
            "collected": list(collected),
            "missing": missing_types,
            "complete": len(missing_types) == 0
        }

    def can_proceed(
        self,
        step_id: str,
        action_type: str = None
    ) -> tuple[bool, str]:
        """
        Check if can proceed to next step

        Returns:
            (can_proceed, reason)
        """
        if not self.config.enforce_evidence_collection:
            return True, "Evidence collection not enforced"

        is_valid, missing = self.validate_step_completion(step_id)

        if not is_valid:
            return False, f"Missing required evidence: {', '.join(missing)}"

        return True, "All required evidence collected"

    def reset_step(self, step_id: str) -> None:
        """Reset evidence collection for a step (for retry/rollback)"""
        if step_id in self._collected_evidence:
            self._collected_evidence[step_id].clear()

    def get_full_report(self) -> Dict[str, Any]:
        """Get full evidence collection report"""
        report = {
            "steps": {},
            "summary": {
                "total_steps": len(self._evidence_requirements),
                "complete_steps": 0,
                "incomplete_steps": 0
            }
        }

        for step_id in self._evidence_requirements:
            status = self.get_evidence_status(step_id)
            report["steps"][step_id] = status

            if status["complete"]:
                report["summary"]["complete_steps"] += 1
            else:
                report["summary"]["incomplete_steps"] += 1

        return report


# Predefined evidence requirements for common actions
ACTION_EVIDENCE_REQUIREMENTS = {
    "select_tool": [
        EvidenceRequirement(evidence_type="trajectory", description="Tool selection path", required=True)
    ],
    "remove_screw": [
        EvidenceRequirement(evidence_type="trajectory", description="Screw removal motion", required=True),
        EvidenceRequirement(evidence_type="timing", description="Operation timing", required=False)
    ],
    "detach_part": [
        EvidenceRequirement(evidence_type="trajectory", description="Part detachment path", required=True),
        EvidenceRequirement(evidence_type="screenshot", description="Before/after state", required=True),
        EvidenceRequirement(evidence_type="sensor_reading", description="Force/torque data", required=False)
    ],
    "inspect": [
        EvidenceRequirement(evidence_type="screenshot", description="Inspection image", required=True),
        EvidenceRequirement(evidence_type="sensor_reading", description="Inspection data", required=True)
    ],
    "verify": [
        EvidenceRequirement(evidence_type="verdict", description="Verification result", required=True),
        EvidenceRequirement(evidence_type="trajectory", description="Final state", required=False)
    ]
}


# Singleton instance
evidence_enforcer = EvidenceEnforcer()
