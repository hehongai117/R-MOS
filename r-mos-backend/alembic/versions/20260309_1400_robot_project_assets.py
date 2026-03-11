"""Add robot project asset tables.

Revision ID: 20260309_robot_project_assets
Revises: 20260308_v03_pgvector_chunks
Create Date: 2026-03-09 14:00:00
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260309_robot_project_assets"
down_revision: Union[str, None] = "20260308_v03_pgvector_chunks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


robot_project_status = sa.Enum(
    "uploaded",
    "ingesting",
    "ready",
    "failed",
    name="robotprojectstatus",
    native_enum=False,
)

robot_sop_draft_review_status = sa.Enum(
    "draft_pending_review",
    "approved",
    "rejected",
    name="robotsopdraftreviewstatus",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "robot_projects",
        sa.Column("id", sa.String(length=64), nullable=False, primary_key=True),
        sa.Column("robot_key", sa.String(length=128), nullable=False),
        sa.Column("brand", sa.String(length=128), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=True),
        sa.Column("status", robot_project_status, nullable=False),
        sa.Column("source_package_path", sa.String(length=512), nullable=False),
        sa.Column("ingest_summary_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_robot_projects_brand", "robot_projects", ["brand"], unique=False)
    op.create_index("ix_robot_projects_model", "robot_projects", ["model"], unique=False)
    op.create_index("ix_robot_projects_robot_key", "robot_projects", ["robot_key"], unique=True)
    op.create_index("ix_robot_projects_brand_model", "robot_projects", ["brand", "model"], unique=False)

    op.create_table(
        "robot_project_files",
        sa.Column("id", sa.String(length=64), nullable=False, primary_key=True),
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("filename", sa.String(length=256), nullable=False),
        sa.Column("relative_path", sa.String(length=512), nullable=False),
        sa.Column("file_kind", sa.String(length=64), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("sha256", sa.String(length=128), nullable=True),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("classification_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["project_id"], ["robot_projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_robot_project_files_project_id", "robot_project_files", ["project_id"], unique=False)
    op.create_index("ix_robot_project_files_file_kind", "robot_project_files", ["file_kind"], unique=False)
    op.create_index("ix_robot_project_files_sha256", "robot_project_files", ["sha256"], unique=False)
    op.create_index(
        "ix_robot_project_files_project_kind",
        "robot_project_files",
        ["project_id", "file_kind"],
        unique=False,
    )

    op.create_table(
        "robot_part_manifests",
        sa.Column("id", sa.String(length=64), nullable=False, primary_key=True),
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("manifest_version", sa.String(length=32), nullable=False),
        sa.Column("tree_json", sa.JSON(), nullable=False),
        sa.Column("mapping_json", sa.JSON(), nullable=False),
        sa.Column("viewer_manifest_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["project_id"], ["robot_projects.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("project_id"),
    )
    op.create_index("ix_robot_part_manifests_project", "robot_part_manifests", ["project_id"], unique=False)

    op.create_table(
        "robot_sop_drafts",
        sa.Column("id", sa.String(length=64), nullable=False, primary_key=True),
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("draft_json", sa.JSON(), nullable=False),
        sa.Column("citations_json", sa.JSON(), nullable=True),
        sa.Column("review_status", robot_sop_draft_review_status, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["project_id"], ["robot_projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_robot_sop_drafts_project_id", "robot_sop_drafts", ["project_id"], unique=False)
    op.create_index("ix_robot_sop_drafts_request_id", "robot_sop_drafts", ["request_id"], unique=False)
    op.create_index(
        "ix_robot_sop_drafts_project_status",
        "robot_sop_drafts",
        ["project_id", "review_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_robot_sop_drafts_project_status", table_name="robot_sop_drafts")
    op.drop_index("ix_robot_sop_drafts_request_id", table_name="robot_sop_drafts")
    op.drop_index("ix_robot_sop_drafts_project_id", table_name="robot_sop_drafts")
    op.drop_table("robot_sop_drafts")

    op.drop_index("ix_robot_part_manifests_project", table_name="robot_part_manifests")
    op.drop_table("robot_part_manifests")

    op.drop_index("ix_robot_project_files_project_kind", table_name="robot_project_files")
    op.drop_index("ix_robot_project_files_sha256", table_name="robot_project_files")
    op.drop_index("ix_robot_project_files_file_kind", table_name="robot_project_files")
    op.drop_index("ix_robot_project_files_project_id", table_name="robot_project_files")
    op.drop_table("robot_project_files")

    op.drop_index("ix_robot_projects_brand_model", table_name="robot_projects")
    op.drop_index("ix_robot_projects_robot_key", table_name="robot_projects")
    op.drop_index("ix_robot_projects_model", table_name="robot_projects")
    op.drop_index("ix_robot_projects_brand", table_name="robot_projects")
    op.drop_table("robot_projects")
