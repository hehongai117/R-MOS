"""Add severity_level to sop_steps

Revision ID: add_severity_level
Revises:
Create Date: 2026-03-04 23:58:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_severity_level'
down_revision = 'add_agent_runtime_state'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('sop_steps', sa.Column('severity_level', sa.String(20), nullable=False, server_default='WARN', comment='严重程度等级：INFO/WARN/SAFETY_HALT'))


def downgrade() -> None:
    op.drop_column('sop_steps', 'severity_level')
