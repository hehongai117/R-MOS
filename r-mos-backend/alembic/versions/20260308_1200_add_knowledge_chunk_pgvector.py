"""Add pgvector column for ai_knowledge_chunks semantic search.

Revision ID: 20260308_v03_pgvector_chunks
Revises: 20260305_v02_uf10_skill_profiles
Create Date: 2026-03-08 12:00:00
"""
from __future__ import annotations

import logging

from alembic import op
import sqlalchemy as sa
from sqlalchemy import exc as sa_exc


revision = "20260308_v03_pgvector_chunks"
down_revision = "20260305_v02_uf10_skill_profiles"
branch_labels = None
depends_on = None


logger = logging.getLogger("alembic.runtime.migration")


def _enable_pgvector_extension() -> bool:
    try:
        # Run extension creation outside Alembic's main transaction so a missing
        # pgvector package does not poison the revision bookkeeping transaction.
        with op.get_context().autocommit_block():
            op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    except sa_exc.DBAPIError as exc:
        message = str(exc).lower()
        if "vector.control" in message or "extension" in message:
            logger.warning("pgvector extension unavailable, skipping embedding_vec migration: %s", exc)
            return False
        raise
    return True


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("ai_knowledge_chunks")}

    if not _enable_pgvector_extension():
        return

    if "embedding_vec" not in existing_columns:
        op.execute("ALTER TABLE ai_knowledge_chunks ADD COLUMN embedding_vec vector(1536)")

    op.execute(
        """
        UPDATE ai_knowledge_chunks
        SET embedding_vec = CAST(embedding::text AS vector)
        WHERE embedding IS NOT NULL
          AND embedding_vec IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_ai_knowledge_chunks_embedding_vec
        ON ai_knowledge_chunks
        USING ivfflat (embedding_vec vector_cosine_ops)
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("ai_knowledge_chunks")}

    op.execute("DROP INDEX IF EXISTS ix_ai_knowledge_chunks_embedding_vec")
    if "embedding_vec" in existing_columns:
        op.execute("ALTER TABLE ai_knowledge_chunks DROP COLUMN embedding_vec")
