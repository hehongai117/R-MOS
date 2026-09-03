"""认证身份与业务身份绑定的回归测试（审计 M-02）。

修复前的真实缺陷：写端点把请求体自带的 `user_id` / `teacher_id` 当作操作人，
`force-submit` 甚至用它做管辖权判定。任意登录用户只要在请求体里声称自己是教师，
即可强制提交他人的训练会话——e2e 用例曾把该行为断言为 200。
"""
from uuid import uuid4

import pytest

from app.services.authz_guard import ActorContext, resolve_actor_identity
from app.core.exceptions import AccessDeniedError


def _actor(uid: int) -> ActorContext:
    return ActorContext(user_id=uid, email=f"u{uid}@x.com", roles=set(), permissions=set())


@pytest.mark.regression
def test_body_identity_matching_token_is_accepted():
    assert resolve_actor_identity(
        _actor(7), 7, action="a", resource_type="R"
    ) == 7


@pytest.mark.regression
def test_absent_body_identity_falls_back_to_token():
    """请求体不声明身份时，一律使用认证身份。"""
    assert resolve_actor_identity(
        _actor(7), None, action="a", resource_type="R"
    ) == 7


@pytest.mark.regression
def test_body_identity_differing_from_token_is_rejected():
    """**核心回归**：声称他人身份必须被拒绝，而不是静默改用认证身份。

    静默改用会让冒用尝试不可见；此处要求它可见且被拒。
    """
    with pytest.raises(AccessDeniedError) as exc:
        resolve_actor_identity(_actor(7), 999, action="force_submit", resource_type="TrainingSession")
    assert exc.value.reason == "identity_mismatch_between_token_and_body"


@pytest.mark.regression
def test_string_and_int_identity_compare_by_value():
    """令牌身份为 int、请求体为 str 时不得因类型差异误判为冒用。"""
    assert resolve_actor_identity(_actor(7), "7", action="a", resource_type="R") == 7
    with pytest.raises(AccessDeniedError):
        resolve_actor_identity(_actor(7), "8", action="a", resource_type="R")


# ---------------------------------------------------------------------------
# 角色来源（本轮新发现，A6 的 26 项未覆盖）
# ---------------------------------------------------------------------------

def _actor_with(account_role: str = "", roles: set[str] | None = None) -> ActorContext:
    return ActorContext(
        user_id=1, email="u@x.com", roles=roles or set(),
        permissions=set(), account_role=account_role,
    )


@pytest.mark.regression
def test_actor_has_role_accepts_registration_role():
    """**核心回归**：正常注册用户只有 `users.role`，RBAC `user_roles` 为空。

    修复前 `_require_teacher_or_admin` 只查 `actor.roles`，导致正常注册的教师
    对全部 12 个机器人端点一律 403（已实测确认），整个域只有种子账号可用。
    """
    from app.services.authz_guard import actor_has_role

    assert actor_has_role(_actor_with(account_role="teacher"), "teacher", "admin")
    assert actor_has_role(_actor_with(account_role="admin"), "teacher", "admin")


@pytest.mark.regression
def test_actor_has_role_still_accepts_rbac_roles():
    """种子账号只有 RBAC 角色、`account_role` 为空，必须继续放行。"""
    from app.services.authz_guard import actor_has_role

    assert actor_has_role(_actor_with(roles={"admin"}), "admin")


@pytest.mark.regression
def test_actor_has_role_does_not_widen_permissions():
    """修复不得变成放宽：学生仍不具备教师/管理员角色。"""
    from app.services.authz_guard import actor_has_role

    assert not actor_has_role(_actor_with(account_role="student"), "teacher", "admin")
    assert not actor_has_role(_actor_with(), "teacher", "admin")
