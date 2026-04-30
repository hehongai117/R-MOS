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


def _safe_add_column(table: str, column: sa.Column) -> None:
    try:
        op.add_column(table, column)
    except Exception:
        pass

def _safe_create_index(name: str, table: str, columns: list, **kw) -> None:
    try:
        op.create_index(name, table, columns, **kw)
    except Exception:
        pass

def upgrade() -> None:
    # Add new columns to users table
    _safe_add_column('users', sa.Column('role', sa.String(20), nullable=False, server_default='student'))
    _safe_add_column('users', sa.Column('teacher_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True))
    _safe_add_column('users', sa.Column('class_id', sa.Integer(), nullable=True))
    _safe_add_column('users', sa.Column('hint_level', sa.Integer(), nullable=False, server_default='3'))

    # Create indexes
    _safe_create_index('ix_users_role', 'users', ['role'])
    _safe_create_index('ix_users_teacher_id', 'users', ['teacher_id'])
    _safe_create_index('ix_users_class_id', 'users', ['class_id'])


def downgrade() -> None:
    op.drop_index('ix_users_class_id', table_name='users')
    op.drop_index('ix_users_teacher_id', table_name='users')
    op.drop_index('ix_users_role', table_name='users')
    op.drop_column('users', 'hint_level')
    op.drop_column('users', 'class_id')
    op.drop_column('users', 'teacher_id')
    op.drop_column('users', 'role')
