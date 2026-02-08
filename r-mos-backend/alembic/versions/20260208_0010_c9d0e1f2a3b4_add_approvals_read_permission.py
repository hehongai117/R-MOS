"""add approvals read permission

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-02-08 00:10:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PERMISSION = {
    "key": "approvals:read",
    "description": "审批查询权限",
    "resource_type": "approvals",
    "action": "read",
}


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
    bind = op.get_bind()
    if not _permission_exists(bind, PERMISSION["key"]):
        bind.execute(
            sa.text(
                """
                INSERT INTO permissions ("key", description, resource_type, action)
                VALUES (:key, :description, :resource_type, :action)
                """
            ),
            PERMISSION,
        )

    _ensure_role_permission(bind, role_name="admin", permission_key=PERMISSION["key"])
    _ensure_role_permission(bind, role_name="auditor", permission_key=PERMISSION["key"])


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions WHERE "key" = :permission_key
            )
            """
        ),
        {"permission_key": PERMISSION["key"]},
    )
    bind.execute(
        sa.text('DELETE FROM permissions WHERE "key" = :permission_key'),
        {"permission_key": PERMISSION["key"]},
    )
