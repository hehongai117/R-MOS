"""UF-08-b: Add training_submissions table

V0.2 Implementation Plan - Phase 2
Training submission storage

Revision ID: 20260305_v02_uf08_submissions
Revises: 20260305_v02_uf06_sessions
Create Date: 2026-03-05 14:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20260305_v02_uf08_submissions'
down_revision = '20260305_v02_uf06_sessions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create training_submissions table
    op.create_table(
        'training_submissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('submission_id', sa.String(36), nullable=False),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('submit_type', sa.String(20), nullable=False),
        sa.Column('submitted_by', sa.Integer(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('score', sa.Numeric(5, 2), nullable=True),
        sa.Column('total_steps', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completed_steps', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_steps', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_duration', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('feedback', sa.JSON(), nullable=True),
        sa.Column('feedback_generated_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['training_sessions.session_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['submitted_by'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_training_submissions_submission_id', 'training_submissions', ['submission_id'], unique=True)
    op.create_index('ix_training_submissions_session_id', 'training_submissions', ['session_id'])
    op.create_index('ix_training_submissions_user_id', 'training_submissions', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_training_submissions_user_id', table_name='training_submissions')
    op.drop_index('ix_training_submissions_session_id', table_name='training_submissions')
    op.drop_index('ix_training_submissions_submission_id', table_name='training_submissions')
    op.drop_table('training_submissions')
