"""UF-06: Add training_sessions and session_step_records tables

V0.2 Implementation Plan - Phase 1
Training session state machine tables

Revision ID: 20260305_v02_uf06_sessions
Revises: 20260305_v02_uf01_users
Create Date: 2026-03-05 13:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20260305_v02_uf06_sessions'
down_revision = '20260305_v02_uf01_users'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create training_sessions table
    op.create_table(
        'training_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('current_step', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('project_snapshot', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('paused_at', sa.DateTime(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('total_duration', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('score', sa.Numeric(5, 2), nullable=True),
        sa.Column('submit_type', sa.String(20), nullable=True),
        sa.Column('ab_group', sa.String(10), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_training_sessions_session_id', 'training_sessions', ['session_id'], unique=True)
    op.create_index('ix_training_sessions_user_id', 'training_sessions', ['user_id'])
    op.create_index('ix_training_sessions_status', 'training_sessions', ['status'])
    op.create_index('ix_training_sessions_project_id', 'training_sessions', ['project_id'])

    # Create session_step_records table
    op.create_table(
        'session_step_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('record_id', sa.String(36), nullable=False),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('step_id', sa.String(50), nullable=False),
        sa.Column('step_index', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tools_confirmed', sa.JSON(), nullable=True),
        sa.Column('evidence', sa.JSON(), nullable=True),
        sa.Column('verdict_result', sa.JSON(), nullable=True),
        sa.Column('duration_sec', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['training_sessions.session_id'], ondelete='CASCADE'),
    )
    op.create_index('ix_session_step_records_record_id', 'session_step_records', ['record_id'], unique=True)
    op.create_index('ix_session_step_records_session_id', 'session_step_records', ['session_id'])
    op.create_index('ix_session_step_records_status', 'session_step_records', ['status'])


def downgrade() -> None:
    op.drop_index('ix_session_step_records_status', table_name='session_step_records')
    op.drop_index('ix_session_step_records_session_id', table_name='session_step_records')
    op.drop_index('ix_session_step_records_record_id', table_name='session_step_records')
    op.drop_table('session_step_records')

    op.drop_index('ix_training_sessions_project_id', table_name='training_sessions')
    op.drop_index('ix_training_sessions_status', table_name='training_sessions')
    op.drop_index('ix_training_sessions_user_id', table_name='training_sessions')
    op.drop_index('ix_training_sessions_session_id', table_name='training_sessions')
    op.drop_table('training_sessions')
