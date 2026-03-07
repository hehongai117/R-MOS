"""P1-8: Add conversation_turns table

Revision ID: 20260305_1030
Revises: 20260305_1000_llm_audit_fields
Create Date: 2026-03-05 10:30

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20260305_1030_conversation_turns'
down_revision = '20260305_1000_llm_audit_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create conversation_turns table
    op.create_table(
        'conversation_turns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(64), nullable=False),
        sa.Column('task_id', sa.String(64), nullable=True),
        sa.Column('step_index', sa.Integer(), nullable=True),
        sa.Column('role', sa.String(16), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', sa.String(512), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # Create indexes
    op.create_index('ix_conv_session_created', 'conversation_turns', ['session_id', 'created_at'])
    op.create_index('ix_conv_task_created', 'conversation_turns', ['task_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_conv_task_created', table_name='conversation_turns')
    op.drop_index('ix_conv_session_created', table_name='conversation_turns')
    op.drop_table('conversation_turns')
