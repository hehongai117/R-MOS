"""add approvals table and command/tool_call links

Revision ID: 9d8c7b6a5e4f
Revises: 7a1b2c3d4e5f
Create Date: 2026-02-07 21:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9d8c7b6a5e4f"
down_revision: Union[str, None] = "7a1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PERMISSION_ROWS = (
    {
        "key": "approvals:grant",
        "description": "审批通过权限",
        "resource_type": "approvals",
        "action": "grant",
    },
    {
        "key": "approvals:reject",
        "description": "审批拒绝权限",
        "resource_type": "approvals",
        "action": "reject",
    },
)


def _permission_exists(bind: sa.engine.Connection, permission_key: str) -> bool:
    result = bind.execute(
        sa.text('SELECT 1 FROM permissions WHERE "key" = :key LIMIT 1'),
        {"key": permission_key},
    )
    return result.scalar_one_or_none() is not None


def _ensure_role_permission(bind: sa.engine.Connection, *, role_name: str, permission_key: str) -> None:
    bind.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r
            JOIN permissions p ON p."key" = :permission_key
            WHERE r.name = :role_name
              AND NOT EXISTS (
                SELECT 1 FROM role_permissions rp
                WHERE rp.role_id = r.id AND rp.permission_id = p.id
              )
            """
        ),
        {"permission_key": permission_key, "role_name": role_name},
    )


def upgrade() -> None:
    op.create_table(
        "approvals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("command_id", sa.Integer(), nullable=False),
        sa.Column("tool_call_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=256), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("decided_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_approvals_id"), "approvals", ["id"], unique=False)
    op.create_index(op.f("ix_approvals_trace_id"), "approvals", ["trace_id"], unique=False)
    op.create_index(op.f("ix_approvals_command_id"), "approvals", ["command_id"], unique=False)
    op.create_index(op.f("ix_approvals_tool_call_id"), "approvals", ["tool_call_id"], unique=False)
    op.create_index(op.f("ix_approvals_status"), "approvals", ["status"], unique=False)
    op.create_index(op.f("ix_approvals_created_by_user_id"), "approvals", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_approvals_decided_by_user_id"), "approvals", ["decided_by_user_id"], unique=False)
    op.create_index(op.f("ix_approvals_decided_at"), "approvals", ["decided_at"], unique=False)
    op.create_index(op.f("ix_approvals_created_at"), "approvals", ["created_at"], unique=False)
    op.create_index("ix_approvals_trace_status", "approvals", ["trace_id", "status"], unique=False)

    op.create_foreign_key(
        "fk_commands_approval_id",
        "commands",
        "approvals",
        ["approval_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_ai_tool_calls_approval_id",
        "ai_tool_calls",
        "approvals",
        ["approval_id"],
        ["id"],
        ondelete="SET NULL",
    )

    bind = op.get_bind()
    for row in PERMISSION_ROWS:
        if not _permission_exists(bind, row["key"]):
            bind.execute(
                sa.text(
                    """
                    INSERT INTO permissions ("key", description, resource_type, action)
                    VALUES (:key, :description, :resource_type, :action)
                    """
                ),
                row,
            )
        _ensure_role_permission(bind, role_name="admin", permission_key=row["key"])
        _ensure_role_permission(bind, role_name="auditor", permission_key=row["key"])


def downgrade() -> None:
    bind = op.get_bind()
    for permission_key in ("approvals:reject", "approvals:grant"):
        bind.execute(
            sa.text(
                """
                DELETE FROM role_permissions
                WHERE permission_id IN (
                    SELECT id FROM permissions WHERE "key" = :permission_key
                )
                """
            ),
            {"permission_key": permission_key},
        )
        bind.execute(
            sa.text('DELETE FROM permissions WHERE "key" = :permission_key'),
            {"permission_key": permission_key},
        )

    op.drop_constraint("fk_ai_tool_calls_approval_id", "ai_tool_calls", type_="foreignkey")
    op.drop_constraint("fk_commands_approval_id", "commands", type_="foreignkey")

    op.drop_index("ix_approvals_trace_status", table_name="approvals")
    op.drop_index(op.f("ix_approvals_created_at"), table_name="approvals")
    op.drop_index(op.f("ix_approvals_decided_at"), table_name="approvals")
    op.drop_index(op.f("ix_approvals_decided_by_user_id"), table_name="approvals")
    op.drop_index(op.f("ix_approvals_created_by_user_id"), table_name="approvals")
    op.drop_index(op.f("ix_approvals_status"), table_name="approvals")
    op.drop_index(op.f("ix_approvals_tool_call_id"), table_name="approvals")
    op.drop_index(op.f("ix_approvals_command_id"), table_name="approvals")
    op.drop_index(op.f("ix_approvals_trace_id"), table_name="approvals")
    op.drop_index(op.f("ix_approvals_id"), table_name="approvals")
    op.drop_table("approvals")
