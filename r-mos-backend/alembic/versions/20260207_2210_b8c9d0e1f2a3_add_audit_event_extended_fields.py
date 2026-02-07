"""add audit event extended fields

Revision ID: b8c9d0e1f2a3
Revises: 9d8c7b6a5e4f
Create Date: 2026-02-07 22:10:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, None] = "9d8c7b6a5e4f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("audit_events", sa.Column("skill_id", sa.String(length=128), nullable=True))
    op.add_column("audit_events", sa.Column("skill_version", sa.String(length=32), nullable=True))
    op.add_column("audit_events", sa.Column("tool_call_args", sa.JSON(), nullable=True))
    op.add_column("audit_events", sa.Column("side_effects_applied", sa.JSON(), nullable=True))
    op.add_column("audit_events", sa.Column("approval_id", sa.Integer(), nullable=True))

    op.create_foreign_key(
        "fk_audit_events_approval_id",
        "audit_events",
        "approvals",
        ["approval_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_audit_trace_created", "audit_events", ["trace_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_trace_created", table_name="audit_events")
    op.drop_constraint("fk_audit_events_approval_id", "audit_events", type_="foreignkey")

    op.drop_column("audit_events", "approval_id")
    op.drop_column("audit_events", "side_effects_applied")
    op.drop_column("audit_events", "tool_call_args")
    op.drop_column("audit_events", "skill_version")
    op.drop_column("audit_events", "skill_id")
