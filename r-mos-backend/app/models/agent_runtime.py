"""
Agent Runtime State Models

Models for persisting agent runtime state including:
- Belief state
- Decision records
- Evidence snapshots
- Replay metadata
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, Text, Index
from sqlalchemy.orm import relationship

from app.models.base import Base, utcnow


class AgentRuntimeSnapshot(Base):
    """Snapshot of agent runtime state for replay and audit"""
    __tablename__ = "agent_runtime_snapshots"

    id = Column(String(64), primary_key=True)
    trace_id = Column(String(64), nullable=False, index=True)
    snapshot_type = Column(String(50), nullable=False)  # belief_state, decision, evidence, approval
    sequence_number = Column(Integer, default=0)

    # State data (JSON serialized)
    state_data = Column(JSON, nullable=False)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    is_final = Column(Boolean, default=False)

    __table_args__ = (
        Index('ix_runtime_snapshot_trace_type_seq', 'trace_id', 'snapshot_type', 'sequence_number'),
    )


class BeliefStateRecord(Base):
    """Persisted belief state"""
    __tablename__ = "belief_state_records"

    id = Column(String(64), primary_key=True)
    trace_id = Column(String(64), nullable=False, index=True)
    belief_category = Column(String(50), nullable=False)
    proposition = Column(Text, nullable=False)
    confidence = Column(String(20), nullable=False)
    confidence_value = Column(Float, nullable=False)
    source = Column(String(30), nullable=False)
    evidence_refs = Column(JSON, default=list)
    belief_metadata = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        Index('ix_belief_trace_category', 'trace_id', 'belief_category'),
    )


class DecisionRecordDB(Base):
    """Persisted decision record for replay"""
    __tablename__ = "decision_records"

    id = Column(String(64), primary_key=True)
    trace_id = Column(String(64), nullable=False, index=True)
    decision_type = Column(String(50), nullable=False)
    decision_data = Column(JSON, nullable=False)
    input_context = Column(JSON, default=dict)
    output_result = Column(JSON, default=dict)

    # Risk assessment
    risk_level = Column(String(10), nullable=False)
    risk_score = Column(Float, nullable=False)

    # Approval info
    requires_approval = Column(Boolean, default=False)
    approval_level = Column(String(20), nullable=True)
    approved_by = Column(String(64), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index('ix_decision_trace_type', 'trace_id', 'decision_type'),
    )


class ApprovalRecordDB(Base):
    """Persisted approval record"""
    __tablename__ = "approval_records"

    id = Column(String(64), primary_key=True)
    trace_id = Column(String(64), nullable=False, index=True)
    decision_id = Column(String(64), nullable=True, index=True)

    priority = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)
    request_data = Column(JSON, default=dict)
    decision_data = Column(JSON, default=dict)

    requested_by = Column(String(64), nullable=False)
    requested_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    resolved_by = Column(String(64), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_note = Column(Text, nullable=True)

    __table_args__ = (
        Index('ix_approval_trace_status', 'trace_id', 'status'),
    )


class ReplayCheckpoint(Base):
    """Replay checkpoint for trace playback"""
    __tablename__ = "replay_checkpoints"

    id = Column(String(64), primary_key=True)
    trace_id = Column(String(64), nullable=False, index=True)
    checkpoint_name = Column(String(100), nullable=False)
    sequence_number = Column(Integer, default=0)

    # State at checkpoint
    belief_state_snapshot = Column(JSON, default=dict)
    decision_snapshot = Column(JSON, default=dict)
    evidence_snapshot = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index('ix_checkpoint_trace_seq', 'trace_id', 'sequence_number'),
    )
