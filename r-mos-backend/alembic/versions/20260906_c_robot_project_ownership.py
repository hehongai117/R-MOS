"""add ownership columns to robot_projects (审计 C-AUTH-03)

机器人项目此前无任何归属字段，他校用户可读他人上传的手册与资产。
按 M-01／裁定 §9-2 已确立的先例补归属维度。

**历史行不回填**：`created_by_user_id` 保持 NULL，语义为「系统内置内容，仅管理员可见」。
与前两次并表一致——真实上传者无从考据，编造归属会把「不知道是谁传的」
伪装成「确知归某人」。

**与教学表的差异**：此处 `school_name` **参与可见性过滤**，
不是纯预留维度——机器人项目的跨校泄漏是实测确认的缺陷。

Revision ID: 20260906_c_project_owner
Revises: 20260904_m02_ownership
"""
import sqlalchemy as sa
from alembic import op

revision = "20260906_c_project_owner"
down_revision = "20260904_m02_ownership"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("robot_projects", sa.Column("created_by_user_id", sa.Integer(), nullable=True))
    op.add_column("robot_projects", sa.Column("school_name", sa.String(200), nullable=True))
    op.create_index("ix_robot_projects_created_by_user_id", "robot_projects", ["created_by_user_id"])
    op.create_index("ix_robot_projects_school_name", "robot_projects", ["school_name"])
    op.create_foreign_key(
        "fk_robot_projects_created_by_user_id",
        "robot_projects", "users", ["created_by_user_id"], ["id"], ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_robot_projects_created_by_user_id", "robot_projects", type_="foreignkey")
    op.drop_index("ix_robot_projects_school_name", table_name="robot_projects")
    op.drop_index("ix_robot_projects_created_by_user_id", table_name="robot_projects")
    op.drop_column("robot_projects", "school_name")
    op.drop_column("robot_projects", "created_by_user_id")
