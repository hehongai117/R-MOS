"""Add agent runtime state tables for persistence

Revision ID: add_agent_runtime_state
Revises:
Create Date: 2026-03-04 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_agent_runtime_state'
down_revision: Union[str, None] = '869864251bc9_fixed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agent runtime snapshots
    op.create_table(
        'agent_runtime_snapshots',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('trace_id', sa.String(64), nullable=False, index=True),
        sa.Column('snapshot_type', sa.String(50), nullable=False),
        sa.Column('sequence_number', sa.Integer, default=0),
        sa.Column('state_data', sa.JSON, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('is_final', sa.Boolean, default=False),
    )
    op.create_index('ix_runtime_snapshot_trace_type_seq', 'agent_runtime_snapshots',
                    ['trace_id', 'snapshot_type', 'sequence_number'])

    # Belief state records
    op.create_table(
        'belief_state_records',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('trace_id', sa.String(64), nullable=False, index=True),
        sa.Column('belief_category', sa.String(50), nullable=False),
        sa.Column('proposition', sa.Text, nullable=False),
        sa.Column('confidence', sa.String(20), nullable=False),
        sa.Column('confidence_value', sa.Float, nullable=False),
        sa.Column('source', sa.String(30), nullable=False),
        sa.Column('evidence_refs', sa.JSON, default=list),
        sa.Column('metadata', sa.JSON, default=dict),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_belief_trace_category', 'belief_state_records', ['trace_id', 'belief_category'])

    # Decision records
    op.create_table(
        'decision_records',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('trace_id', sa.String(64), nullable=False, index=True),
        sa.Column('decision_type', sa.String(50), nullable=False),
        sa.Column('decision_data', sa.JSON, nullable=False),
        sa.Column('input_context', sa.JSON, default=dict),
        sa.Column('output_result', sa.JSON, default=dict),
        sa.Column('risk_level', sa.String(10), nullable=False),
        sa.Column('risk_score', sa.Float, nullable=False),
        sa.Column('requires_approval', sa.Boolean, default=False),
        sa.Column('approval_level', sa.String(20), nullable=True),
        sa.Column('approved_by', sa.String(64), nullable=True),
        sa.Column('approved_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_decision_trace_type', 'decision_records', ['trace_id', 'decision_type'])

    # Approval records
    op.create_table(
        'approval_records',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('trace_id', sa.String(64), nullable=False, index=True),
        sa.Column('decision_id', sa.String(64), nullable=True, index=True),
        sa.Column('priority', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('request_data', sa.JSON, default=dict),
        sa.Column('decision_data', sa.JSON, default=dict),
        sa.Column('requested_by', sa.String(64), nullable=False),
        sa.Column('requested_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('resolved_by', sa.String(64), nullable=True),
        sa.Column('resolved_at', sa.DateTime, nullable=True),
        sa.Column('resolution_note', sa.Text, nullable=True),
    )
    op.create_index('ix_approval_trace_status', 'approval_records', ['trace_id', 'status'])

    # Replay checkpoints
    op.create_table(
        'replay_checkpoints',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('trace_id', sa.String(64), nullable=False, index=True),
        sa.Column('checkpoint_name', sa.String(100), nullable=False),
        sa.Column('sequence_number', sa.Integer, default=0),
        sa.Column('belief_state_snapshot', sa.JSON, default=dict),
        sa.Column('decision_snapshot', sa.JSON, default=dict),
        sa.Column('evidence_snapshot', sa.JSON, default=dict),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_checkpoint_trace_seq', 'replay_checkpoints', ['trace_id', 'sequence_number'])


def downgrade() -> None:
    op.drop_table('replay_checkpoints')
    op.drop_table('approval_records')
    op.drop_table('decision_records')
    op.drop_table('belief_state_records')
    op.drop_table('agent_runtime_snapshots')
