"""add timeline foundation tables

Revision ID: 0a1b2c3d4e5f
Revises: f1a2b3c4d5e6
Create Date: 2026-02-10 12:15:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0a1b2c3d4e5f"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "multimodal_timelines",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("scope_type", sa.String(length=64), nullable=False),
        sa.Column("scope_id", sa.String(length=64), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_timeline_scope", "multimodal_timelines", ["scope_type", "scope_id"], unique=False)

    op.create_table(
        "timeline_segments",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("timeline_id", sa.Integer(), nullable=False),
        sa.Column("segment_type", sa.String(length=32), nullable=False),
        sa.Column("ref_id", sa.String(length=64), nullable=True),
        sa.Column("start_ts_ms", sa.BigInteger(), nullable=False),
        sa.Column("end_ts_ms", sa.BigInteger(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["timeline_id"], ["multimodal_timelines.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_segments_timeline_start",
        "timeline_segments",
        ["timeline_id", "start_ts_ms"],
        unique=False,
    )

    op.create_table(
        "alignment_map",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("timeline_id", sa.Integer(), nullable=False),
        sa.Column("anchor_key", sa.String(length=128), nullable=False),
        sa.Column("segment_id", sa.Integer(), nullable=False),
        sa.Column("ref_id", sa.String(length=64), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["timeline_id"], ["multimodal_timelines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["segment_id"], ["timeline_segments.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_alignment_anchor", "alignment_map", ["timeline_id", "anchor_key"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_alignment_anchor", table_name="alignment_map")
    op.drop_table("alignment_map")
    op.drop_index("ix_segments_timeline_start", table_name="timeline_segments")
    op.drop_table("timeline_segments")
    op.drop_index("ix_timeline_scope", table_name="multimodal_timelines")
    op.drop_table("multimodal_timelines")
