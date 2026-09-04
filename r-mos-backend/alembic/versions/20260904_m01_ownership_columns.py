"""add ownership columns to five content tables (审计 M-01 / 董事会裁定 §9-2)

五张教学内容表此前无任何创建者字段，因此写路径只能做角色制过渡
（任意教师可改任意教学内容）。本迁移补上归属维度，使 `ensure_write_owner`
可用于对象级校验。

**历史行策略：`created_by_user_id` 保持 NULL，语义为「系统内置公共内容」，
仅管理员可写**——与 `ensure_write_owner` 对无主对象的既定处置一致。
不做数据回填：这些行的真实创建者无从考据，编造归属会把
「不知道是谁建的」伪装成「确知归某人」。

`school_name` 为多租户准备维度，**本迁移不使其参与任何授权判定**。

Revision ID: 20260904_m01_ownership
Revises: 20260817_sop_three_phase
"""
import sqlalchemy as sa
from alembic import op


revision = "20260904_m01_ownership"
down_revision = "20260817_sop_three_phase"
branch_labels = None
depends_on = None

TABLES = (
    "sops",
    "fault_cases",
    "robot_sop_drafts",
    "external_assessments",
    "assessment_providers",
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
