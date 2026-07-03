"""Add pipeline tables: fault_sop_mappings, task_executions, task_step_results, knowledge_documents

Revision ID: 20260430_pipeline
Revises: 20260309_robot_project_assets
Create Date: 2026-04-30
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '20260430_pipeline'
down_revision: Union[str, None] = '20260309_robot_project_assets'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'fault_sop_mappings',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('fault_type', sa.String(50), nullable=False, index=True),
        sa.Column('sop_id', sa.Integer(), sa.ForeignKey('sops.id'), nullable=False, index=True),
        sa.Column('difficulty', sa.String(20), nullable=False, server_default='beginner'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'task_executions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('task_id', sa.Integer(), sa.ForeignKey('tasks.id'), nullable=False, index=True),
        sa.Column('student_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('sop_id', sa.Integer(), sa.ForeignKey('sops.id'), nullable=True),
        sa.Column('fault_type', sa.String(50), nullable=False, index=True),
        sa.Column('diagnosis_trace_id', sa.String(100), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='in_progress'),
        sa.Column('started_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('total_duration_seconds', sa.Float(), nullable=True),
        sa.Column('report_url', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'task_step_results',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('execution_id', sa.Integer(), sa.ForeignKey('task_executions.id'), nullable=False, index=True),
        sa.Column('step_index', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=True, server_default='pending'),
        sa.Column('evidence_type', sa.String(50), nullable=True),
        sa.Column('evidence_value', sa.JSON(), nullable=True),
        sa.Column('is_compliant', sa.Boolean(), nullable=True),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'knowledge_documents',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('doc_type', sa.String(50), nullable=True, server_default='manual'),
        sa.Column('fault_tags', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('sop_tags', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('source', sa.String(100), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active', index=True),
        sa.Column('risk_level', sa.String(5), nullable=True, server_default='R0'),
        sa.Column('uploaded_by', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('knowledge_documents')
    op.drop_table('task_step_results')
    op.drop_table('task_executions')
    op.drop_table('fault_sop_mappings')
