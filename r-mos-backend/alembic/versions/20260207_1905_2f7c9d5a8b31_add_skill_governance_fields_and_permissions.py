"""add skill governance fields and permissions

Revision ID: 2f7c9d5a8b31
Revises: 6e7f8a9b1c2d
Create Date: 2026-02-07 19:05:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2f7c9d5a8b31"
down_revision: Union[str, None] = "6e7f8a9b1c2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PERMISSION_ROWS = (
    {
        "key": "skills:write",
        "description": "创建与提审技能",
        "resource_type": "skills",
        "action": "write",
    },
    {
        "key": "skills:publish",
        "description": "发布技能",
        "resource_type": "skills",
        "action": "publish",
    },
)


def _permission_exists(bind: sa.engine.Connection, permission_key: str) -> bool:
    result = bind.execute(
        sa.text('SELECT 1 FROM permissions WHERE "key" = :key LIMIT 1'),
        {"key": permission_key},
    )
    return result.scalar_one_or_none() is not None


def _ensure_admin_permission(bind: sa.engine.Connection, permission_key: str) -> None:
    bind.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r
            JOIN permissions p ON p."key" = :permission_key
            WHERE r.name = 'admin'
              AND NOT EXISTS (
                SELECT 1 FROM role_permissions rp
                WHERE rp.role_id = r.id AND rp.permission_id = p.id
              )
            """
        ),
        {"permission_key": permission_key},
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    skill_columns = {column["name"] for column in inspector.get_columns("skills")}
    if "created_by_user_id" not in skill_columns:
        op.add_column("skills", sa.Column("created_by_user_id", sa.String(length=64), nullable=True))
    if "feature_flag" not in skill_columns:
        op.add_column("skills", sa.Column("feature_flag", sa.String(length=128), nullable=True))
    if "rollback_strategy" not in skill_columns:
        op.add_column("skills", sa.Column("rollback_strategy", sa.JSON(), nullable=True))

    skill_indexes = {index["name"] for index in inspector.get_indexes("skills")}
    if "ix_skills_created_by_user_id" not in skill_indexes:
        op.create_index("ix_skills_created_by_user_id", "skills", ["created_by_user_id"], unique=False)

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
        _ensure_admin_permission(bind, row["key"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for permission_key in ("skills:publish", "skills:write"):
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

    skill_indexes = {index["name"] for index in inspector.get_indexes("skills")}
    if "ix_skills_created_by_user_id" in skill_indexes:
        op.drop_index("ix_skills_created_by_user_id", table_name="skills")

    skill_columns = {column["name"] for column in inspector.get_columns("skills")}
    if "rollback_strategy" in skill_columns:
        op.drop_column("skills", "rollback_strategy")
    if "feature_flag" in skill_columns:
        op.drop_column("skills", "feature_flag")
    if "created_by_user_id" in skill_columns:
        op.drop_column("skills", "created_by_user_id")
