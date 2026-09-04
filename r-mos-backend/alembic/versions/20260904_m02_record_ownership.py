"""add ownership columns to evidence, incident, and observation records

历史行不回填 `created_by_user_id`：NULL 表示系统内置公共内容，仅管理员可改。
真实创建者无从考据，不能编造归属。

`school_name` 仅为多租户准备维度，当前不参与任何授权判定；正式方案见路线图 S-2。

Revision ID: 20260904_m02_ownership
Revises: 20260904_m01_ownership
"""
import sqlalchemy as sa
from alembic import op


revision = "20260904_m02_ownership"
down_revision = "20260904_m01_ownership"
branch_labels = None
depends_on = None

TABLES = (
    "evidence_bundles",
    "incidents",
    "observations",
)


def upgrade() -> None:
    for table in TABLES:
        op.add_column(
            table,
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        )
        op.add_column(table, sa.Column("school_name", sa.String(200), nullable=True))
        op.create_index(
            f"ix_{table}_created_by_user_id", table, ["created_by_user_id"]
        )
        op.create_index(f"ix_{table}_school_name", table, ["school_name"])
        op.create_foreign_key(
            f"fk_{table}_created_by_user_id",
            table,
            "users",
            ["created_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    for table in TABLES:
        op.drop_constraint(f"fk_{table}_created_by_user_id", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_school_name", table_name=table)
        op.drop_index(f"ix_{table}_created_by_user_id", table_name=table)
        op.drop_column(table, "school_name")
        op.drop_column(table, "created_by_user_id")
