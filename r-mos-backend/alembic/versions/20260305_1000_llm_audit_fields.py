"""P1-0: Add LLM audit fields to audit_events table

Revision ID: 20260305_1000
Revises: 20260304_2358_add_severity_level
Create Date: 2026-03-05 10:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20260305_1000_llm_audit_fields'
down_revision = 'add_severity_level'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add LLM audit fields to audit_events table
    op.add_column(
        'audit_events',
        sa.Column('prompt_hash', sa.String(64), nullable=True, index=True, comment='Prompt 内容哈希')
    )
    op.add_column(
        'audit_events',
        sa.Column('response_hash', sa.String(64), nullable=True, index=True, comment='Response 内容哈希')
    )
    op.add_column(
        'audit_events',
        sa.Column('provider', sa.String(32), nullable=True, comment='LLM Provider: openai/anthropic/ollama')
    )
    op.add_column(
        'audit_events',
        sa.Column('model', sa.String(64), nullable=True, comment='模型名称: gpt-4/claude-3/llama2')
    )
    op.add_column(
        'audit_events',
        sa.Column('tokens_in', sa.Integer(), nullable=True, comment='输入 token 数量')
    )
    op.add_column(
        'audit_events',
        sa.Column('tokens_out', sa.Integer(), nullable=True, comment='输出 token 数量')
    )


def downgrade() -> None:
    op.drop_column('audit_events', 'tokens_out')
    op.drop_column('audit_events', 'tokens_in')
    op.drop_column('audit_events', 'model')
    op.drop_column('audit_events', 'provider')
    op.drop_column('audit_events', 'response_hash')
    op.drop_column('audit_events', 'prompt_hash')
