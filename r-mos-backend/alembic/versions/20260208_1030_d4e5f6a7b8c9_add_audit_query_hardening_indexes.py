"""add audit query hardening indexes

Revision ID: d4e5f6a7b8c9
Revises: c9d0e1f2a3b4
Create Date: 2026-02-08 10:30:00
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_audit_action_created",
        "audit_events",
        ["action", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_actor_created",
        "audit_events",
        ["actor_user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_resource_created",
        "audit_events",
        ["resource_type", "resource_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_approval_created",
        "audit_events",
        ["approval_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_skill_created",
        "audit_events",
        ["skill_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_audit_skill_created", table_name="audit_events")
    op.drop_index("ix_audit_approval_created", table_name="audit_events")
    op.drop_index("ix_audit_resource_created", table_name="audit_events")
    op.drop_index("ix_audit_actor_created", table_name="audit_events")
    op.drop_index("ix_audit_action_created", table_name="audit_events")
