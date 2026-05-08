"""add robot platform tables

Revision ID: 20260507_robot_platform
Revises: 20260430_pipeline
Create Date: 2026-05-07
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '20260507_robot_platform'
down_revision: Union[str, None] = '20260430_pipeline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. robot_models table
    op.create_table(
        'robot_models',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('brand', sa.String(100), nullable=False, index=True),
        sa.Column('model_name', sa.String(200), nullable=False, index=True),
        sa.Column('version', sa.String(50), nullable=True, server_default='1.0'),
        sa.Column('owner_teacher_id', sa.Integer(),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('visibility', sa.Enum('private', 'shared', name='robotvisibility'),
                  nullable=False, server_default='private'),
        sa.Column('status', sa.Enum('draft', 'analyzing', 'ready', name='robotstatus'),
                  nullable=False, server_default='draft'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('thumbnail_path', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 2. teacher_robot_bindings table
    op.create_table(
        'teacher_robot_bindings',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('teacher_id', sa.Integer(),
                  sa.ForeignKey('users.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('robot_model_id', sa.Integer(),
                  sa.ForeignKey('robot_models.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('binding_type', sa.String(20), nullable=False, server_default='owner'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('teacher_id', 'robot_model_id', name='uq_teacher_robot'),
    )

    # 3. robot_assets table
    op.create_table(
        'robot_assets',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('robot_model_id', sa.Integer(),
                  sa.ForeignKey('robot_models.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('asset_type',
                  sa.Enum('model_glb', 'manifest', 'thumbnail', 'upload_original', name='assettype'),
                  nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 4. analysis_tasks table
    op.create_table(
        'analysis_tasks',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('robot_model_id', sa.Integer(),
                  sa.ForeignKey('robot_models.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('task_type',
                  sa.Enum('pdf_extract', 'cad_parse', 'sop_generate', 'full', name='analysistasktype'),
                  nullable=False),
        sa.Column('status',
                  sa.Enum('pending', 'running', 'completed', 'failed', name='analysistaskstatus'),
                  nullable=False, server_default='pending', index=True),
        sa.Column('input_document_ids', sa.JSON(), nullable=True),
        sa.Column('output_summary', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # 5. Add robot_model_id column to existing tables
    op.add_column('sops',
                  sa.Column('robot_model_id', sa.Integer(),
                            sa.ForeignKey('robot_models.id', ondelete='SET NULL'),
                            nullable=True, index=True))
    op.add_column('fault_sop_mappings',
                  sa.Column('robot_model_id', sa.Integer(),
                            sa.ForeignKey('robot_models.id', ondelete='SET NULL'),
                            nullable=True, index=True))
    op.add_column('knowledge_documents',
                  sa.Column('robot_model_id', sa.Integer(),
                            sa.ForeignKey('robot_models.id', ondelete='SET NULL'),
                            nullable=True, index=True))
    op.add_column('knowledge_documents',
                  sa.Column('generation_status', sa.String(20),
                            server_default='manual', nullable=True))


def downgrade() -> None:
    # Remove columns from existing tables
    op.drop_column('knowledge_documents', 'generation_status')
    op.drop_column('knowledge_documents', 'robot_model_id')
    op.drop_column('fault_sop_mappings', 'robot_model_id')
    op.drop_column('sops', 'robot_model_id')

    # Drop new tables (reverse order)
    op.drop_table('analysis_tasks')
    op.drop_table('robot_assets')
    op.drop_table('teacher_robot_bindings')
    op.drop_table('robot_models')

    # Drop enums
    op.execute("DROP TYPE IF EXISTS analysistaskstatus")
    op.execute("DROP TYPE IF EXISTS analysistasktype")
    op.execute("DROP TYPE IF EXISTS assettype")
    op.execute("DROP TYPE IF EXISTS robotstatus")
    op.execute("DROP TYPE IF EXISTS robotvisibility")
