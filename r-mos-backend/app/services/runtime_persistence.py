"""
Runtime State Persistence Service

Provides database-backed persistence for agent runtime state.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from app.models.agent_runtime import (
    AgentRuntimeSnapshot,
    BeliefStateRecord,
    DecisionRecordDB,
    ApprovalRecordDB,
    ReplayCheckpoint
)


class RuntimeStatePersistence:
    """Database-backed persistence for agent runtime state"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # === Belief State ===

    async def save_belief(self, trace_id: str, belief: Dict[str, Any]) -> BeliefStateRecord:
        """Save a belief to database"""
        record = BeliefStateRecord(
            id=belief.get('id', str(uuid.uuid4())),
            trace_id=trace_id,
            belief_category=belief.get('category', 'unknown'),
            proposition=belief.get('proposition', ''),
            confidence=belief.get('confidence', 'low'),
            confidence_value=belief.get('confidence_value', 0.0),
            source=belief.get('source', 'inference'),
            evidence_refs=belief.get('evidence_refs', []),
            metadata=belief.get('metadata', {}),
        )
        self.session.add(record)
        await self.session.commit()
        return record

    async def get_beliefs_by_trace(self, trace_id: str) -> List[BeliefStateRecord]:
        """Get all beliefs for a trace"""
        result = await self.session.execute(
            select(BeliefStateRecord).where(BeliefStateRecord.trace_id == trace_id)
        )
        return list(result.scalars().all())

    async def clear_beliefs_by_trace(self, trace_id: str) -> None:
        """Clear all beliefs for a trace"""
        await self.session.execute(
            delete(BeliefStateRecord).where(BeliefStateRecord.trace_id == trace_id)
        )
        await self.session.commit()

    # === Decision Records ===

    async def save_decision(self, trace_id: str, decision: Dict[str, Any]) -> DecisionRecordDB:
        """Save a decision to database"""
        record = DecisionRecordDB(
            id=decision.get('id', str(uuid.uuid4())),
            trace_id=trace_id,
            decision_type=decision.get('decision_type', 'unknown'),
            decision_data=decision.get('decision_data', {}),
            input_context=decision.get('input_context', {}),
            output_result=decision.get('output_result', {}),
            risk_level=decision.get('risk_level', 'R0'),
            risk_score=decision.get('risk_score', 0.0),
            requires_approval=decision.get('requires_approval', False),
            approval_level=decision.get('approval_level'),
        )
        self.session.add(record)
        await self.session.commit()
        return record

    async def get_decisions_by_trace(self, trace_id: str) -> List[DecisionRecordDB]:
        """Get all decisions for a trace"""
        result = await self.session.execute(
            select(DecisionRecordDB).where(DecisionRecordDB.trace_id == trace_id)
        )
        return list(result.scalars().all())

    # === Approval Records ===

    async def save_approval(self, trace_id: str, approval: Dict[str, Any]) -> ApprovalRecordDB:
        """Save an approval record to database"""
        record = ApprovalRecordDB(
            id=approval.get('id', str(uuid.uuid4())),
            trace_id=trace_id,
            decision_id=approval.get('decision_id'),
            priority=approval.get('priority', 'normal'),
            status=approval.get('status', 'pending'),
            request_data=approval.get('request_data', {}),
            decision_data=approval.get('decision_data', {}),
            requested_by=approval.get('requested_by', 'system'),
        )
        self.session.add(record)
        await self.session.commit()
        return record

    async def get_approvals_by_trace(self, trace_id: str) -> List[ApprovalRecordDB]:
        """Get all approvals for a trace"""
        result = await self.session.execute(
            select(ApprovalRecordDB).where(ApprovalRecordDB.trace_id == trace_id)
        )
        return list(result.scalars().all())

    # === Replay Checkpoints ===

    async def save_checkpoint(self, trace_id: str, checkpoint: Dict[str, Any]) -> ReplayCheckpoint:
        """Save a replay checkpoint"""
        record = ReplayCheckpoint(
            id=checkpoint.get('id', str(uuid.uuid4())),
            trace_id=trace_id,
            checkpoint_name=checkpoint.get('checkpoint_name', 'default'),
            sequence_number=checkpoint.get('sequence_number', 0),
            belief_state_snapshot=checkpoint.get('belief_state_snapshot', {}),
            decision_snapshot=checkpoint.get('decision_snapshot', {}),
            evidence_snapshot=checkpoint.get('evidence_snapshot', {}),
        )
        self.session.add(record)
        await self.session.commit()
        return record

    async def get_checkpoints_by_trace(self, trace_id: str) -> List[ReplayCheckpoint]:
        """Get all checkpoints for a trace in order"""
        result = await self.session.execute(
            select(ReplayCheckpoint)
            .where(ReplayCheckpoint.trace_id == trace_id)
            .order_by(ReplayCheckpoint.sequence_number)
        )
        return list(result.scalars().all())


# Singleton instance holder
_persistence_instance: Optional[RuntimeStatePersistence] = None


def get_persistence(session: AsyncSession) -> RuntimeStatePersistence:
    """Get or create persistence instance"""
    global _persistence_instance
    _persistence_instance = RuntimeStatePersistence(session)
    return _persistence_instance
