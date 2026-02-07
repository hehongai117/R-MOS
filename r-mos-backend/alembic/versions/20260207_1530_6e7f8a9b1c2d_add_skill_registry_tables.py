"""add skill registry tables

Revision ID: 6e7f8a9b1c2d
Revises: f3c11f7a9a2b
Create Date: 2026-02-07 15:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6e7f8a9b1c2d"
down_revision: Union[str, None] = "9f2b6c1d4e7a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("side_effects", sa.JSON(), nullable=False),
        sa.Column("allowlist_resources", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
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
        sa.UniqueConstraint("skill_id", "version", name="ux_skills_skill_version"),
    )
    op.create_index(op.f("ix_skills_id"), "skills", ["id"], unique=False)
    op.create_index("ix_skills_status_risk", "skills", ["status", "risk_level"], unique=False)
    op.create_index(op.f("ix_skills_created_at"), "skills", ["created_at"], unique=False)

    op.create_table(
        "skill_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("reviewer_user_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_skill_reviews_id"), "skill_reviews", ["id"], unique=False)
    op.create_index(op.f("ix_skill_reviews_skill_id"), "skill_reviews", ["skill_id"], unique=False)
    op.create_index(op.f("ix_skill_reviews_version"), "skill_reviews", ["version"], unique=False)
    op.create_index(op.f("ix_skill_reviews_status"), "skill_reviews", ["status"], unique=False)
    op.create_index(
        op.f("ix_skill_reviews_reviewer_user_id"),
        "skill_reviews",
        ["reviewer_user_id"],
        unique=False,
    )
    op.create_index(op.f("ix_skill_reviews_created_at"), "skill_reviews", ["created_at"], unique=False)

    op.create_table(
        "skill_releases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("released_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("release_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_skill_releases_id"), "skill_releases", ["id"], unique=False)
    op.create_index(op.f("ix_skill_releases_skill_id"), "skill_releases", ["skill_id"], unique=False)
    op.create_index(op.f("ix_skill_releases_version"), "skill_releases", ["version"], unique=False)
    op.create_index(op.f("ix_skill_releases_status"), "skill_releases", ["status"], unique=False)
    op.create_index(
        op.f("ix_skill_releases_released_by_user_id"),
        "skill_releases",
        ["released_by_user_id"],
        unique=False,
    )
    op.create_index(op.f("ix_skill_releases_created_at"), "skill_releases", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_skill_releases_created_at"), table_name="skill_releases")
    op.drop_index(op.f("ix_skill_releases_released_by_user_id"), table_name="skill_releases")
    op.drop_index(op.f("ix_skill_releases_status"), table_name="skill_releases")
    op.drop_index(op.f("ix_skill_releases_version"), table_name="skill_releases")
    op.drop_index(op.f("ix_skill_releases_skill_id"), table_name="skill_releases")
    op.drop_index(op.f("ix_skill_releases_id"), table_name="skill_releases")
    op.drop_table("skill_releases")

    op.drop_index(op.f("ix_skill_reviews_created_at"), table_name="skill_reviews")
    op.drop_index(op.f("ix_skill_reviews_reviewer_user_id"), table_name="skill_reviews")
    op.drop_index(op.f("ix_skill_reviews_status"), table_name="skill_reviews")
    op.drop_index(op.f("ix_skill_reviews_version"), table_name="skill_reviews")
    op.drop_index(op.f("ix_skill_reviews_skill_id"), table_name="skill_reviews")
    op.drop_index(op.f("ix_skill_reviews_id"), table_name="skill_reviews")
    op.drop_table("skill_reviews")

    op.drop_index(op.f("ix_skills_created_at"), table_name="skills")
    op.drop_index("ix_skills_status_risk", table_name="skills")
    op.drop_index(op.f("ix_skills_id"), table_name="skills")
    op.drop_table("skills")
