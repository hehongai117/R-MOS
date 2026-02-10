"""add evidence cards table

Revision ID: 3c4d5e6f7a8b
Revises: 0a1b2c3d4e5f
Create Date: 2026-02-10 12:45:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3c4d5e6f7a8b"
down_revision: Union[str, None] = "0a1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evidence_cards",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("attempt_id", sa.Integer(), nullable=False),
        sa.Column("card_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("references", sa.JSON(), nullable=False),
        sa.Column("media_preview", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["attempt_id"], ["assignment_attempts.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_evidence_cards_attempt", "evidence_cards", ["attempt_id"], unique=False)
    op.create_index("ix_evidence_cards_created", "evidence_cards", ["created_at"], unique=False)
    op.create_index("ix_evidence_cards_card_type", "evidence_cards", ["card_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_evidence_cards_card_type", table_name="evidence_cards")
    op.drop_index("ix_evidence_cards_created", table_name="evidence_cards")
    op.drop_index("ix_evidence_cards_attempt", table_name="evidence_cards")
    op.drop_table("evidence_cards")
