"""
RBAC 模型（Gate-1 / B-001）。
"""
from sqlalchemy import Column, ForeignKey, Index, Integer, String, UniqueConstraint

from .base import Base, TimestampMixin


class Role(Base, TimestampMixin):
    """角色定义。"""

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), nullable=False, unique=True, index=True)
    description = Column(String(255), nullable=True)


class Permission(Base, TimestampMixin):
    """权限定义（resource:action）。"""

    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("key", name="ux_permissions_key"),
        Index("ix_permissions_resource_action", "resource_type", "action"),
    )

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(128), nullable=False, unique=True, index=True)
    description = Column(String(255), nullable=True)
    resource_type = Column(String(64), nullable=False)
    action = Column(String(32), nullable=False)


class UserRole(Base, TimestampMixin):
    """用户-角色关联。"""

    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="ux_user_roles_user_role"),
        Index("ix_user_roles_user_id", "user_id"),
        Index("ix_user_roles_role_id", "role_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)


class RolePermission(Base, TimestampMixin):
    """角色-权限关联。"""

    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="ux_role_permissions_role_perm"),
        Index("ix_role_permissions_role_id", "role_id"),
        Index("ix_role_permissions_permission_id", "permission_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permissions.id"), nullable=False)
