"""add three-phase columns to sop_steps

Revision ID: 20260817_sop_three_phase
Revises: 20260714_audit_tz
"""
import sqlalchemy as sa
from alembic import op


revision = "20260817_sop_three_phase"
down_revision = "20260714_audit_tz"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sop_steps",
        sa.Column("phase", sa.String(20), nullable=False, server_default="execute"),
    )
    op.add_column("sop_steps", sa.Column("group_path", sa.String(200), nullable=True))
    op.add_column("sop_steps", sa.Column("step_view", sa.JSON(), nullable=True))
    op.add_column("sop_steps", sa.Column("required_parts", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("sop_steps", "required_parts")
    op.drop_column("sop_steps", "step_view")
    op.drop_column("sop_steps", "group_path")
    op.drop_column("sop_steps", "phase")
