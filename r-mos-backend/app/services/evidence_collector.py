"""
Evidence Collector Service - Phase 2 Week 6
Collects and manages evidence for agent actions

Provides:
- Evidence collection for different action types
- Evidence validation
- Evidence chain tracking
"""

from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import time
import uuid


class EvidenceType(str, Enum):
    """Types of evidence"""
    SCREENSHOT = "screenshot"
    TELEMETRY = "telemetry"
    USER_INPUT = "user_input"
    SYSTEM_LOG = "system_log"
    COACH_RECOMMENDATION = "coach_recommendation"
    DIAGNOSIS_RESULT = "diagnosis_result"
    KNOWLEDGE_REFERENCE = "knowledge_reference"
    APPROVAL = "approval"
    SAFETY_CHECK = "safety_check"
    ERROR_LOG = "error_log"


class EvidenceStatus(str, Enum):
    """Evidence status"""
    PENDING = "pending"
    COLLECTED = "collected"
    VALIDATED = "validated"
    REJECTED = "rejected"


@dataclass
class Evidence:
    """Single evidence item"""
    id: str
    type: EvidenceType
    trace_id: str
    step_id: Optional[str]
    content: Any  # Can be URL, JSON, text, etc.
    status: EvidenceStatus
    collected_at: int = field(default_factory=lambda: int(time.time() * 1000))
    validated_at: Optional[int] = None
    collected_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidenceRequirement:
    """Required evidence for an action"""
    type: EvidenceType
    description: str
    required: bool = True
    validation_rules: Dict[str, Any] = field(default_factory=dict)


class EvidenceCollector:
    """
    Evidence Collector for agent actions.

    Collects and validates evidence for:
    - Task execution
    - Safety checks
    - Decision justification
    - Audit trail
    """

    # Default evidence requirements by action type
    DEFAULT_REQUIREMENTS: Dict[str, List[EvidenceRequirement]] = {
        "execute-task": [
            EvidenceRequirement(
                type=EvidenceType.SAFETY_CHECK,
                description="Safety check result",
                required=True,
            ),
            EvidenceRequirement(
                type=EvidenceType.USER_INPUT,
                description="User confirmation",
                required=True,
            ),
        ],
        "write-kb": [
            EvidenceRequirement(
                type=EvidenceType.KNOWLEDGE_REFERENCE,
                description="Source knowledge reference",
                required=True,
            ),
            EvidenceRequirement(
                type=EvidenceType.APPROVAL,
                description="Approval record",
                required=False,
            ),
        ],
        "delegate-coach": [
            EvidenceRequirement(
                type=EvidenceType.COACH_RECOMMENDATION,
                description="Coach recommendation",
                required=True,
            ),
        ],
        "delegate-diagnoser": [
            EvidenceRequirement(
                type=EvidenceType.DIAGNOSIS_RESULT,
                description="Diagnosis result",
                required=True,
            ),
        ],
    }

    def __init__(self):
        self._evidence: Dict[str, Evidence] = {}  # evidence_id -> Evidence
        self._evidence_by_trace: Dict[str, Set[str]] = {}  # trace_id -> set of evidence_ids
        self._evidence_by_step: Dict[str, Set[str]] = {}  # step_id -> set of evidence_ids

    def collect_evidence(
        self,
        evidence_type: EvidenceType,
        trace_id: str,
        step_id: Optional[str],
        content: Any,
        collected_by: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Collect a new evidence item"""
        evidence_id = f"ev-{uuid.uuid4().hex[:12]}"

        evidence = Evidence(
            id=evidence_id,
            type=evidence_type,
            trace_id=trace_id,
            step_id=step_id,
            content=content,
            status=EvidenceStatus.COLLECTED,
            collected_by=collected_by,
            metadata=metadata or {},
        )

        self._evidence[evidence_id] = evidence

        # Index by trace
        if trace_id not in self._evidence_by_trace:
            self._evidence_by_trace[trace_id] = set()
        self._evidence_by_trace[trace_id].add(evidence_id)

        # Index by step
        if step_id:
            if step_id not in self._evidence_by_step:
                self._evidence_by_step[step_id] = set()
            self._evidence_by_step[step_id].add(evidence_id)

        return evidence_id

    def validate_evidence(
        self,
        evidence_id: str,
        validation_result: bool,
        validation_message: Optional[str] = None,
    ) -> bool:
        """Validate evidence"""
        if evidence_id not in self._evidence:
            return False

        evidence = self._evidence[evidence_id]

        if validation_result:
            evidence.status = EvidenceStatus.VALIDATED
            evidence.validated_at = int(time.time() * 1000)
            evidence.metadata["validation_message"] = validation_message
        else:
            evidence.status = EvidenceStatus.REJECTED
            evidence.metadata["validation_message"] = validation_message

        return validation_result

    def get_evidence(self, evidence_id: str) -> Optional[Evidence]:
        """Get evidence by ID"""
        return self._evidence.get(evidence_id)

    def get_evidence_by_trace(self, trace_id: str) -> List[Evidence]:
        """Get all evidence for a trace"""
        evidence_ids = self._evidence_by_trace.get(trace_id, set())
        return [self._evidence[eid] for eid in evidence_ids if eid in self._evidence]

    def get_evidence_by_step(self, step_id: str) -> List[Evidence]:
        """Get all evidence for a step"""
        evidence_ids = self._evidence_by_step.get(step_id, set())
        return [self._evidence[eid] for eid in evidence_ids if eid in self._evidence]

    def get_evidence_summary(self, trace_id: str) -> Dict[str, Any]:
        """Get evidence summary for a trace"""
        evidence_list = self.get_evidence_by_trace(trace_id)

        summary = {
            "trace_id": trace_id,
            "total_count": len(evidence_list),
            "by_type": {},
            "by_status": {},
            "evidence_ids": [e.id for e in evidence_list],
        }

        # Count by type
        for ev in evidence_list:
            t = ev.type.value
            summary["by_type"][t] = summary["by_type"].get(t, 0) + 1

        # Count by status
        for ev in evidence_list:
            s = ev.status.value
            summary["by_status"][s] = summary["by_status"].get(s, 0) + 1

        return summary

    def check_requirements(
        self,
        action_type: str,
        trace_id: str,
    ) -> tuple[bool, List[str], List[str]]:
        """
        Check if all required evidence is collected for an action.

        Returns:
            (all_collected, collected_types, missing_types)
        """
        requirements = self.DEFAULT_REQUIREMENTS.get(action_type, [])
        if not requirements:
            return True, [], []

        evidence_list = self.get_evidence_by_trace(trace_id)
        collected_types = set(e.type.value for e in evidence_list)

        missing_types = []
        for req in requirements:
            if req.required and req.type.value not in collected_types:
                missing_types.append(req.type.value)

        all_collected = len(missing_types) == 0

        return all_collected, list(collected_types), missing_types

    def get_requirements(self, action_type: str) -> List[EvidenceRequirement]:
        """Get evidence requirements for an action type"""
        return self.DEFAULT_REQUIREMENTS.get(action_type, [])

    def can_proceed(
        self,
        action_type: str,
        trace_id: str,
    ) -> tuple[bool, str]:
        """
        Check if can proceed with action based on evidence.

        Returns:
            (allowed, reason)
        """
        all_collected, collected, missing = self.check_requirements(action_type, trace_id)

        if not all_collected:
            return False, f"Missing required evidence: {', '.join(missing)}"

        # Check for rejected evidence
        evidence_list = self.get_evidence_by_trace(trace_id)
        rejected = [e for e in evidence_list if e.status == EvidenceStatus.REJECTED]

        if rejected:
            return False, f"Evidence rejected: {', '.join(e.id for e in rejected)}"

        return True, "All evidence collected and validated"

    def get_evidence_chain(self, trace_id: str) -> List[Dict[str, Any]]:
        """Get evidence chain for a trace (ordered by time)"""
        evidence_list = self.get_evidence_by_trace(trace_id)
        evidence_list.sort(key=lambda e: e.collected_at)

        chain = []
        for ev in evidence_list:
            chain.append({
                "id": ev.id,
                "type": ev.type.value,
                "status": ev.status.value,
                "collected_at": ev.collected_at,
                "validated_at": ev.validated_at,
                "collected_by": ev.collected_by,
                "step_id": ev.step_id,
            })

        return chain


# Singleton instance
evidence_collector = EvidenceCollector()
