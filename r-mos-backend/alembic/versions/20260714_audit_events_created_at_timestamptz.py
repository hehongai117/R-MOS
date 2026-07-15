"""audit_events.created_at back to TIMESTAMPTZ (align ORM TZDateTime)

背景：20260515_timestamptz 曾将该列转为 TIMESTAMPTZ，但后续 autogenerate
迁移 092b0539cc93 依据当时仍为 naive DateTime 的 ORM 定义把它回退成了
TIMESTAMP WITHOUT TIME ZONE。ORM 现已改为 TZDateTime（P2-1a Task 3），
本迁移将列重新转为 TIMESTAMPTZ，消除 ORM/迁移链类型漂移（alembic check 门禁）。

Revision ID: 20260714_audit_tz
Revises: 092b0539cc93
Create Date: 2026-07-14
"""
from alembic import op

revision = "20260714_audit_tz"
down_revision = "092b0539cc93"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE audit_events
            ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE audit_events
            ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC'
    """)
