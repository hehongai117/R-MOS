"""add schools table and user onboarding fields

Revision ID: 20260515_schools
Revises: 20260507_robot_platform
Create Date: 2026-05-15
"""
from alembic import op
import sqlalchemy as sa

revision = "20260515_schools"
down_revision = "20260507_robot_platform"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "schools",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("province", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_schools_name", "schools", ["name"])

    op.add_column("users", sa.Column("school_name", sa.String(200), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "onboarding_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "onboarding_completed")
    op.drop_column("users", "school_name")
    op.drop_index("ix_schools_name", table_name="schools")
    op.drop_table("schools")
