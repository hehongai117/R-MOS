"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2026-01-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # SOPs表
    op.create_table('sops',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('applicable_model', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('difficulty_level', sa.String(length=20), nullable=True),
        sa.Column('estimated_time', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sops_id'), 'sops', ['id'], unique=False)
    op.create_index(op.f('ix_sops_name'), 'sops', ['name'], unique=False)
    
    # SOP Steps表
    op.create_table('sop_steps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sop_id', sa.Integer(), nullable=False),
        sa.Column('step_index', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('target_part', sa.String(length=100), nullable=True),
        sa.Column('expected_action', sa.String(length=50), nullable=False),
        sa.Column('action_params', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('validation_rules', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_critical', sa.Boolean(), nullable=True),
        sa.Column('timeout_seconds', sa.Integer(), nullable=True),
        sa.Column('allow_skip', sa.Boolean(), nullable=True),
        sa.Column('hints', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('tools_required', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['sop_id'], ['sops.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Tasks表（V2.3：sop_id nullable + SET NULL）
    op.create_table('tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('sop_id', sa.Integer(), nullable=True),  # V2.3修正
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('current_step_index', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('paused_at', sa.DateTime(), nullable=True),
        sa.Column('time_limit', sa.Integer(), nullable=True),
        sa.Column('pass_score', sa.Integer(), nullable=False),
        sa.Column('final_score', sa.Integer(), nullable=True),
        sa.Column('is_passed', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['sop_id'], ['sops.id'], ondelete='SET NULL'),  # V2.3修正
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tasks_id'), 'tasks', ['id'], unique=False)
    
    # Events表
    op.create_table('events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('step_index', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=True),
        sa.Column('target', sa.String(length=100), nullable=True),
        sa.Column('parameters', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('result', sa.String(length=50), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('is_error', sa.Boolean(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_events_task_id'), 'events', ['task_id'], unique=False)
    
    # Snapshots表
    op.create_table('snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('step_index', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('trigger', sa.String(length=50), nullable=False),
        sa.Column('joint_states', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('sensor_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('active_faults', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('adapter_type', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # FaultCases表（故障案例库）
    op.create_table('fault_cases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('fault_code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('affected_parts', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('symptoms', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('diagnosis_steps', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('solution_steps', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_fault_cases_id'), 'fault_cases', ['id'], unique=False)
    op.create_index(op.f('ix_fault_cases_fault_code'), 'fault_cases', ['fault_code'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_fault_cases_fault_code'), table_name='fault_cases')
    op.drop_index(op.f('ix_fault_cases_id'), table_name='fault_cases')
    op.drop_table('fault_cases')
    op.drop_table('snapshots')
    op.drop_table('events')
    op.drop_table('tasks')
    op.drop_table('sop_steps')
    op.drop_table('sops')
