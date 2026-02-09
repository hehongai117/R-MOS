"""add ai knowledge chunks table

Revision ID: f1a2b3c4d5e6
Revises: d4e5f6a7b8c9
Create Date: 2026-02-08 23:15:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_knowledge_chunks",
        sa.Column("id", sa.String(length=64), nullable=False, primary_key=True),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("owner_user_id", sa.String(length=64), nullable=True),
        sa.Column("course_id", sa.String(length=64), nullable=True),
        sa.Column("attempt_id", sa.String(length=64), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_chunks_owner_course",
        "ai_knowledge_chunks",
        ["owner_user_id", "course_id"],
        unique=False,
    )
    op.create_index(
        "ix_chunks_source",
        "ai_knowledge_chunks",
        ["source_type", "source_id"],
        unique=False,
    )
    op.create_index(
        "ix_ai_knowledge_chunks_created_at",
        "ai_knowledge_chunks",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ai_knowledge_chunks_created_at", table_name="ai_knowledge_chunks")
    op.drop_index("ix_chunks_source", table_name="ai_knowledge_chunks")
    op.drop_index("ix_chunks_owner_course", table_name="ai_knowledge_chunks")
    op.drop_table("ai_knowledge_chunks")
