"""
Phase 2 Contract Tests

Tests for Phase 2 features including:
- Belief state management
- Evidence collection
- Compensation planning
- Approval workflow
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestBeliefStateContract:
    """Test belief state service contracts"""

    @pytest.mark.asyncio
    async def test_belief_confidence_enum(self):
        """Test BeliefConfidence enum values"""
        from app.services.belief_state import BeliefConfidence
        assert BeliefConfidence.VERY_LOW.value == "very_low"
        assert BeliefConfidence.LOW.value == "low"
        assert BeliefConfidence.MEDIUM.value == "medium"
        assert BeliefConfidence.HIGH.value == "high"
        assert BeliefConfidence.VERY_HIGH.value == "very_high"

    @pytest.mark.asyncio
    async def test_belief_source_enum(self):
        """Test BeliefSource enum values"""
        from app.services.belief_state import BeliefSource
        assert BeliefSource.USER_INPUT.value == "user_input"
        assert BeliefSource.OBSERVATION.value == "observation"
        assert BeliefSource.INFERENCE.value == "inference"
        assert BeliefSource.TOOL_RESULT.value == "tool_result"
        assert BeliefSource.COACH_ADVICE.value == "coach_advice"

    @pytest.mark.asyncio
    async def test_belief_state_creation(self):
        """Test BeliefState can be created with trace_id"""
        from app.services.belief_state import BeliefState
        state = BeliefState(trace_id="test-trace-001")
        assert state.trace_id == "test-trace-001"
        assert state.get_all_beliefs() == []


class TestEvidenceCollectorContract:
    """Test evidence collector service contracts"""

    @pytest.mark.asyncio
    async def test_evidence_type_enum(self):
        """Test EvidenceType enum values"""
        from app.services.evidence_collector import EvidenceType
        assert EvidenceType.SCREENSHOT.value == "screenshot"
        assert EvidenceType.TELEMETRY.value == "telemetry"
        assert EvidenceType.USER_INPUT.value == "user_input"
        assert EvidenceType.SAFETY_CHECK.value == "safety_check"

    @pytest.mark.asyncio
    async def test_evidence_status_enum(self):
        """Test EvidenceStatus enum values"""
        from app.services.evidence_collector import EvidenceStatus
        assert EvidenceStatus.COLLECTED.value == "collected"
        assert EvidenceStatus.VALIDATED.value == "validated"
        assert EvidenceStatus.REJECTED.value == "rejected"

    @pytest.mark.asyncio
    async def test_evidence_collector_creation(self):
        """Test EvidenceCollector can be instantiated"""
        from app.services.evidence_collector import EvidenceCollector
        collector = EvidenceCollector()
        assert collector is not None


class TestCompensationPlannerContract:
    """Test compensation planner service contracts"""

    @pytest.mark.asyncio
    async def test_compensation_strategy_enum(self):
        """Test CompensationStrategy enum values"""
        from app.services.compensation_planner import CompensationStrategy
        assert CompensationStrategy.RETRY.value == "retry"
        assert CompensationStrategy.ROLLBACK.value == "rollback"
        assert CompensationStrategy.COMPENSATE.value == "compensate"
        assert CompensationStrategy.SKIP.value == "skip"
        assert CompensationStrategy.FALLBACK.value == "fallback"
        assert CompensationStrategy.ESCALATE.value == "escalate"

    @pytest.mark.asyncio
    async def test_failure_type_enum(self):
        """Test FailureType enum values"""
        from app.services.compensation_planner import FailureType
        assert FailureType.TIMEOUT.value == "timeout"
        assert FailureType.ERROR.value == "error"
        assert FailureType.SAFETY_VIOLATION.value == "safety_violation"
        assert FailureType.UNKNOWN.value == "unknown"

    @pytest.mark.asyncio
    async def test_compensation_planner_creation(self):
        """Test CompensationPlanner can be instantiated"""
        from app.services.compensation_planner import CompensationPlanner
        planner = CompensationPlanner()
        assert planner is not None


class TestApprovalQueueContract:
    """Test approval queue service contracts"""

    @pytest.mark.asyncio
    async def test_approval_priority_enum(self):
        """Test ApprovalPriority enum values"""
        from app.services.approval_queue import ApprovalPriority
        assert ApprovalPriority.LOW.value == "low"
        assert ApprovalPriority.NORMAL.value == "normal"
        assert ApprovalPriority.HIGH.value == "high"
        assert ApprovalPriority.URGENT.value == "urgent"

    @pytest.mark.asyncio
    async def test_approval_status_enum(self):
        """Test ApprovalStatus enum values"""
        from app.services.approval_queue import ApprovalStatus
        assert ApprovalStatus.PENDING.value == "pending"
        assert ApprovalStatus.APPROVED.value == "approved"
        assert ApprovalStatus.REJECTED.value == "rejected"
        assert ApprovalStatus.EXPIRED.value == "expired"
