"""UF-10: Add student_skill_profiles and student_weak_steps tables

V0.2 Implementation Plan - Phase 2
Skill profile and weak steps tracking

Revision ID: 20260305_v02_uf10_skill_profiles
Revises: 20260305_v02_uf08_submissions
Create Date: 2026-03-05 15:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20260305_v02_uf10_skill_profiles'
down_revision = '20260305_v02_uf08_submissions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create student_skill_profiles table
    op.create_table(
        'student_skill_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('overall_level', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('total_sessions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_duration', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_trained_at', sa.DateTime(), nullable=True),
        sa.Column('score_safety', sa.Numeric(5, 2), nullable=True),
        sa.Column('score_procedure', sa.Numeric(5, 2), nullable=True),
        sa.Column('score_precision', sa.Numeric(5, 2), nullable=True),
        sa.Column('score_efficiency', sa.Numeric(5, 2), nullable=True),
        sa.Column('score_tools', sa.Numeric(5, 2), nullable=True),
        sa.Column('cert_l1_passed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('cert_l2_passed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('cert_l3_eligible', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index('ix_student_skill_profiles_user_id', 'student_skill_profiles', ['user_id'], unique=True)

    # Create student_weak_steps table
    op.create_table(
        'student_weak_steps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('step_id', sa.String(50), nullable=False),
        sa.Column('sop_id', sa.String(50), nullable=True),
        sa.Column('fail_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_failed_at', sa.DateTime(), nullable=True),
        sa.Column('fail_tags', sa.JSON(), nullable=True),
        sa.Column('is_resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_student_weak_steps_user_id', 'student_weak_steps', ['user_id'])
    op.create_index('ix_student_weak_steps_step_id', 'student_weak_steps', ['step_id'])
    op.create_index('ix_student_weak_steps_user_step', 'student_weak_steps', ['user_id', 'step_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_student_weak_steps_user_step', table_name='student_weak_steps')
    op.drop_index('ix_student_weak_steps_step_id', table_name='student_weak_steps')
    op.drop_index('ix_student_weak_steps_user_id', table_name='student_weak_steps')
    op.drop_table('student_weak_steps')

    op.drop_index('ix_student_skill_profiles_user_id', table_name='student_skill_profiles')
    op.drop_table('student_skill_profiles')
