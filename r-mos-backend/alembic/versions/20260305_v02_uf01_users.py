"""UF-01-a: Add role fields to users table

V0.2 Implementation Plan - Phase 1
Add role, teacher_id, class_id, hint_level to users table

Revision ID: 20260305_v02_uf01_users
Revises: 20260305_1100
Create Date: 2026-03-05 11:30:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20260305_v02_uf01_users'
down_revision = '20260305_1100'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to users table
    op.add_column('users', sa.Column('role', sa.String(20), nullable=False, server_default='student'))
    op.add_column('users', sa.Column('teacher_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True))
    op.add_column('users', sa.Column('class_id', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('hint_level', sa.Integer(), nullable=False, server_default='3'))

    # Create indexes
    op.create_index('ix_users_role', 'users', ['role'])
    op.create_index('ix_users_teacher_id', 'users', ['teacher_id'])
    op.create_index('ix_users_class_id', 'users', ['class_id'])


def downgrade() -> None:
    op.drop_index('ix_users_class_id', table_name='users')
    op.drop_index('ix_users_teacher_id', table_name='users')
    op.drop_index('ix_users_role', table_name='users')
    op.drop_column('users', 'hint_level')
    op.drop_column('users', 'class_id')
    op.drop_column('users', 'teacher_id')
    op.drop_column('users', 'role')
