"""add commands and ai_tool_calls tables

Revision ID: 7a1b2c3d4e5f
Revises: 2f7c9d5a8b31
Create Date: 2026-02-07 20:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7a1b2c3d4e5f"
down_revision: Union[str, None] = "2f7c9d5a8b31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "commands",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("actor_user_id", sa.String(length=64), nullable=True),
        sa.Column("intent", sa.String(length=128), nullable=False),
        sa.Column("skill_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("approval_id", sa.Integer(), nullable=True),
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
        sa.UniqueConstraint("trace_id", name="ux_commands_trace_id"),
    )
    op.create_index(op.f("ix_commands_id"), "commands", ["id"], unique=False)
    op.create_index(op.f("ix_commands_trace_id"), "commands", ["trace_id"], unique=False)
    op.create_index(op.f("ix_commands_actor_user_id"), "commands", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_commands_intent"), "commands", ["intent"], unique=False)
    op.create_index(op.f("ix_commands_skill_id"), "commands", ["skill_id"], unique=False)
    op.create_index(op.f("ix_commands_status"), "commands", ["status"], unique=False)
    op.create_index(op.f("ix_commands_approval_id"), "commands", ["approval_id"], unique=False)
    op.create_index(op.f("ix_commands_created_at"), "commands", ["created_at"], unique=False)

    op.create_table(
        "ai_tool_calls",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("command_id", sa.Integer(), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("actor_user_id", sa.String(length=64), nullable=True),
        sa.Column("skill_id", sa.String(length=128), nullable=True),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("side_effects", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("approval_id", sa.Integer(), nullable=True),
        sa.Column("result_payload", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["command_id"], ["commands.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_tool_calls_id"), "ai_tool_calls", ["id"], unique=False)
    op.create_index(op.f("ix_ai_tool_calls_command_id"), "ai_tool_calls", ["command_id"], unique=False)
    op.create_index(op.f("ix_ai_tool_calls_trace_id"), "ai_tool_calls", ["trace_id"], unique=False)
    op.create_index(op.f("ix_ai_tool_calls_actor_user_id"), "ai_tool_calls", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_ai_tool_calls_skill_id"), "ai_tool_calls", ["skill_id"], unique=False)
    op.create_index(op.f("ix_ai_tool_calls_status"), "ai_tool_calls", ["status"], unique=False)
    op.create_index(op.f("ix_ai_tool_calls_approval_id"), "ai_tool_calls", ["approval_id"], unique=False)
    op.create_index(op.f("ix_ai_tool_calls_created_at"), "ai_tool_calls", ["created_at"], unique=False)
    op.create_index("ix_tool_calls_trace_skill", "ai_tool_calls", ["trace_id", "skill_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tool_calls_trace_skill", table_name="ai_tool_calls")
    op.drop_index(op.f("ix_ai_tool_calls_created_at"), table_name="ai_tool_calls")
    op.drop_index(op.f("ix_ai_tool_calls_approval_id"), table_name="ai_tool_calls")
    op.drop_index(op.f("ix_ai_tool_calls_status"), table_name="ai_tool_calls")
    op.drop_index(op.f("ix_ai_tool_calls_skill_id"), table_name="ai_tool_calls")
    op.drop_index(op.f("ix_ai_tool_calls_actor_user_id"), table_name="ai_tool_calls")
    op.drop_index(op.f("ix_ai_tool_calls_trace_id"), table_name="ai_tool_calls")
    op.drop_index(op.f("ix_ai_tool_calls_command_id"), table_name="ai_tool_calls")
    op.drop_index(op.f("ix_ai_tool_calls_id"), table_name="ai_tool_calls")
    op.drop_table("ai_tool_calls")

    op.drop_index(op.f("ix_commands_created_at"), table_name="commands")
    op.drop_index(op.f("ix_commands_approval_id"), table_name="commands")
    op.drop_index(op.f("ix_commands_status"), table_name="commands")
    op.drop_index(op.f("ix_commands_skill_id"), table_name="commands")
    op.drop_index(op.f("ix_commands_intent"), table_name="commands")
    op.drop_index(op.f("ix_commands_actor_user_id"), table_name="commands")
    op.drop_index(op.f("ix_commands_trace_id"), table_name="commands")
    op.drop_index(op.f("ix_commands_id"), table_name="commands")
    op.drop_table("commands")
