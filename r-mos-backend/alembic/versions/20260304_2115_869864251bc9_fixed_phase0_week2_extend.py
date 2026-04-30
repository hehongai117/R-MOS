"""phase0_week2_extend_command_toolcall_skill_models - Minimal additive version

Revision ID: 869864251bc9_fixed
Revises: 3c4d5e6f7a8b
Create Date: 2026-03-04 21:15:00.000000

This is a minimal additive migration that adds only the required columns
for Phase 0 Week 2 extension of command, tool call, and skill models.

Changes:
- Add columns to ai_tool_calls table
- Add columns to commands table
- Add columns to skills table
- Add indexes for new columns
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '869864251bc9_fixed'
down_revision: Union[str, None] = '3c4d5e6f7a8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _safe_add_column(table: str, column: sa.Column) -> None:
    """Add column if it doesn't already exist (SQLite-safe)."""
    try:
        op.add_column(table, column)
    except Exception:
        pass


def _safe_create_index(name: str, table: str, columns: list, **kw) -> None:
    """Create index if it doesn't already exist."""
    try:
        op.create_index(name, table, columns, **kw)
    except Exception:
        pass


def upgrade() -> None:
    # === ai_tool_calls table extensions ===
    _safe_add_column('ai_tool_calls', sa.Column('input_params', sa.JSON(), nullable=True))
    _safe_add_column('ai_tool_calls', sa.Column('execution_time_ms', sa.Integer(), nullable=True))
    _safe_add_column('ai_tool_calls', sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'))
    _safe_add_column('ai_tool_calls', sa.Column('parent_tool_call_id', sa.Integer(), nullable=True))
    _safe_add_column('ai_tool_calls', sa.Column('call_depth', sa.Integer(), nullable=False, server_default='0'))
    _safe_add_column('ai_tool_calls', sa.Column('evidence_collected', sa.JSON(), nullable=False, server_default='{}'))
    _safe_add_column('ai_tool_calls', sa.Column('safety_check_passed', sa.String(length=8), nullable=True))
    _safe_add_column('ai_tool_calls', sa.Column('model_version', sa.String(length=32), nullable=True))

    # Add index for tool_calls status+time
    _safe_create_index('ix_tool_calls_status_time', 'ai_tool_calls', ['status', 'created_at'], unique=False)

    # Add foreign key for parent_tool_call_id (skip on SQLite — no ALTER TABLE ADD FK)
    try:
        op.create_foreign_key(
            'fk_tool_calls_parent',
            'ai_tool_calls',
            'ai_tool_calls',
            ['parent_tool_call_id'],
            ['id'],
            ondelete='SET NULL'
        )
    except Exception:
        pass

    # === commands table extensions ===
    _safe_add_column('commands', sa.Column('resource_ref', sa.JSON(), nullable=True))
    _safe_add_column('commands', sa.Column('policy_context', sa.JSON(), nullable=True))
    _safe_add_column('commands', sa.Column('intent_classification', sa.String(length=64), nullable=True))
    _safe_add_column('commands', sa.Column('idempotency_key', sa.String(length=128), nullable=True))
    _safe_add_column('commands', sa.Column('policy_decision', sa.JSON(), nullable=True))
    _safe_add_column('commands', sa.Column('risk_level', sa.String(length=8), nullable=True))
    _safe_add_column('commands', sa.Column('evidence_refs', sa.JSON(), nullable=False, server_default='[]'))
    _safe_add_column('commands', sa.Column('approved_by', sa.String(length=64), nullable=True))
    _safe_add_column('commands', sa.Column('approved_at', sa.DateTime(), nullable=True))
    _safe_add_column('commands', sa.Column('execution_budget_ms', sa.Integer(), nullable=True))

    # Add indexes for commands
    _safe_create_index('ix_commands_idempotency_key', 'commands', ['idempotency_key'], unique=False)
    _safe_create_index('ix_commands_intent_classification', 'commands', ['intent_classification'], unique=False)
    _safe_create_index('ix_commands_risk_level', 'commands', ['risk_level'], unique=False)
    _safe_create_index('ix_commands_risk_status', 'commands', ['risk_level', 'status'], unique=False)

    # === skills table extensions ===
    _safe_add_column('skills', sa.Column('evidence_requirements', sa.JSON(), nullable=True))
    _safe_add_column('skills', sa.Column('approval_workflow', sa.JSON(), nullable=True))
    _safe_add_column('skills', sa.Column('policy_rules', sa.JSON(), nullable=True))
    _safe_add_column('skills', sa.Column('execution_timeout_ms', sa.Integer(), nullable=True))
    _safe_add_column('skills', sa.Column('deprecated_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # === skills table - remove added columns ===
    op.drop_column('skills', 'deprecated_at')
    op.drop_column('skills', 'execution_timeout_ms')
    op.drop_column('skills', 'policy_rules')
    op.drop_column('skills', 'approval_workflow')
    op.drop_column('skills', 'evidence_requirements')

    # === commands table - remove added columns and indexes ===
    op.drop_index('ix_commands_risk_status', table_name='commands')
    op.drop_index('ix_commands_risk_level', table_name='commands')
    op.drop_index('ix_commands_intent_classification', table_name='commands')
    op.drop_index('ix_commands_idempotency_key', table_name='commands')
    op.drop_column('commands', 'execution_budget_ms')
    op.drop_column('commands', 'approved_at')
    op.drop_column('commands', 'approved_by')
    op.drop_column('commands', 'evidence_refs')
    op.drop_column('commands', 'risk_level')
    op.drop_column('commands', 'policy_decision')
    op.drop_column('commands', 'idempotency_key')
    op.drop_column('commands', 'intent_classification')
    op.drop_column('commands', 'policy_context')
    op.drop_column('commands', 'resource_ref')

    # === ai_tool_calls table - remove added columns and indexes ===
    op.drop_constraint('fk_tool_calls_parent', 'ai_tool_calls', type_='foreignkey')
    op.drop_index('ix_tool_calls_status_time', table_name='ai_tool_calls')
    op.drop_column('ai_tool_calls', 'model_version')
    op.drop_column('ai_tool_calls', 'safety_check_passed')
    op.drop_column('ai_tool_calls', 'evidence_collected')
    op.drop_column('ai_tool_calls', 'call_depth')
    op.drop_column('ai_tool_calls', 'parent_tool_call_id')
    op.drop_column('ai_tool_calls', 'retry_count')
    op.drop_column('ai_tool_calls', 'execution_time_ms')
    op.drop_column('ai_tool_calls', 'input_params')
