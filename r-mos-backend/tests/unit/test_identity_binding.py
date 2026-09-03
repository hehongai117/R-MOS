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
