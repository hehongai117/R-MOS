"""2026-07 全量测试规划暴露的 8 个 P0 真实 bug 的回归集。

来源：docs/2026-07-02-full-test-plan.md §P0 表。
每个测试断言修复后的正确行为；这些断言永不放松（regression marker）。

夹具构造参照对应特征测试：
  - tests/unit/test_agent_characterization.py  → P0#1/2/3/4/5
  - tests/unit/test_training_characterization.py → P0#6
  - tests/unit/test_teaching_characterization.py → P0#7/8

helpers 实际使用的函数：tests/e2e/helpers.register_and_login
（helpers.py 中无 login_as_teacher；用 register_and_login(role="teacher") 替代）
"""
from __future__ import annotations

import asyncio
import json

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.teaching import Assignment, AssignmentAttempt, TeachingClass
from app.models.user import User

from tests.e2e import helpers

pytestmark = pytest.mark.regression


# ─────────────────────────────────────────────────────────────────────────────
# 内部辅助：授权（与 agent_characterization 同款，但不新增 fixture）
# ─────────────────────────────────────────────────────────────────────────────

async def _grant_agent_permissions(
    session_factory: async_sessionmaker,
    *,
    email: str,
    permission_keys: list[str],
) -> None:
    """给已注册用户授予 agent_user 角色和指定权限。"""
    async with session_factory() as session:
        user_result = await session.execute(select(User).where(User.email == email))
        user = user_result.scalar_one()

        role_result = await session.execute(select(Role).where(Role.name == "agent_user"))
        role = role_result.scalar_one_or_none()
        if role is None:
            role = Role(name="agent_user", description="agent user 角色")
            session.add(role)
            await session.flush()

        for pkey in permission_keys:
            perm_result = await session.execute(
                select(Permission).where(Permission.key == pkey)
            )
            perm = perm_result.scalar_one_or_none()
            if perm is None:
                resource_type, action = pkey.split(":", 1)
                perm = Permission(
                    key=pkey,
                    description=f"{pkey} 权限",
                    resource_type=resource_type,
                    action=action,
                )
                session.add(perm)
                await session.flush()

            rp_result = await session.execute(
                select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == perm.id,
                )
            )
            if rp_result.scalar_one_or_none() is None:
                session.add(RolePermission(role_id=role.id, permission_id=perm.id))

        ur_result = await session.execute(
            select(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.role_id == role.id,
            )
        )
        if ur_result.scalar_one_or_none() is None:
            session.add(UserRole(user_id=user.id, role_id=role.id))

        await session.commit()


async def _seed_attempt_no_task(
    session_factory: async_sessionmaker,
    *,
    student_id: int,
) -> int:
    """创建 class→assignment→attempt 链（attempt.task_id = None），返回 attempt_id。"""
    async with session_factory() as session:
        teaching_class = TeachingClass(name="回归测试班级", teacher_id=1)
        session.add(teaching_class)
        await session.flush()

        assignment = Assignment(class_id=teaching_class.id, title="回归测试作业")
        session.add(assignment)
        await session.flush()

        attempt = AssignmentAttempt(
            assignment_id=assignment.id,
            student_id=student_id,
            task_id=None,  # 关键：无关联 task → P0#7 触发场景
            attempt_index=1,
            status="in_progress",
        )
        session.add(attempt)
        await session.commit()
        return attempt.id


# ─────────────────────────────────────────────────────────────────────────────
# P0#1: POST /agent/v2/policy/evaluate 曾因 dataclass 调 .model_dump() 而 500
# 端点: POST /api/v1/agent/v2/policy/evaluate
# 根因: PolicyDecision 是 dataclass，错误调用 .model_dump()；修复用 dataclasses.asdict()
# ─────────────────────────────────────────────────────────────────────────────

def test_p0_1_policy_evaluate_returns_200_not_500(e2e_env):
    """Bug#1: POST /agent/v2/policy/evaluate 曾因 dataclass 调 .model_dump() 而 500。

    修复后：endpoint 用 dataclasses.asdict() 序列化 PolicyDecision，返回 200
    + 含 allowed/risk_level/requires_approval 的决策字段。
    """
    client, session_factory = e2e_env
    _user_id, email, login_data = helpers.register_and_login(
        client,
        email_prefix="reg_p0_1",
        role="teacher",
    )
    token = login_data["access_token"]
    asyncio.run(
        _grant_agent_permissions(
            session_factory,
            email=email,
            permission_keys=["agent:execute"],
        )
    )

    resp = client.post(
        "/api/v1/agent/v2/policy/evaluate",
        headers={"Authorization": f"Bearer {token}"},
        params={"action": "read_sop"},
        json={"user_id": "u1", "resource_type": "sops"},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    # 必须断言的正确行为：返回结构含 decision 字段（allowed / risk_level / requires_approval）
    assert isinstance(body.get("allowed"), bool), f"缺少 allowed 字段: {body}"
    assert "risk_level" in body, f"缺少 risk_level 字段: {body}"
    assert "requires_approval" in body, f"缺少 requires_approval 字段: {body}"


# ─────────────────────────────────────────────────────────────────────────────
# P0#2: POST /agent/evaluation/report 对无效 task_id 曾 500（ValueError 未捕获）
# 端点: POST /api/v1/agent/evaluation/report
# 根因: ReportGenerator 抛 ValueError 未被 endpoint 捕获，直接 500
# ─────────────────────────────────────────────────────────────────────────────

def test_p0_2_evaluation_report_invalid_task_returns_4xx_not_500(e2e_env):
    """Bug#2: POST /agent/evaluation/report 对无效 task_id 曾 500（ValueError 未捕获）。

    修复后：endpoint 捕获 ValueError，返回 404（明确的客户端错误），绝不是 500。
    """
    client, session_factory = e2e_env
    _user_id, email, login_data = helpers.register_and_login(
        client,
        email_prefix="reg_p0_2",
        role="teacher",
    )
    token = login_data["access_token"]
    asyncio.run(
        _grant_agent_permissions(
            session_factory,
            email=email,
            permission_keys=["agent:read"],
        )
    )

    resp = client.post(
        "/api/v1/agent/evaluation/report",
        headers={"Authorization": f"Bearer {token}"},
        json={"task_id": 999999, "use_llm": False},
    )
    # 必须断言的正确行为：明确的客户端错误，绝不是 500
    assert resp.status_code in (400, 404, 422), (
        f"期望 4xx 客户端错误, 实际 {resp.status_code}: {resp.text}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# P0#3: POST /agent/sop/quality/check（全扫）曾 500（SOP.is_active 不存在）
# 端点: POST /api/v1/agent/sop/quality/check
# 根因: SOPQualityMonitor 引用不存在的 SOP.is_active 字段
# ─────────────────────────────────────────────────────────────────────────────

def test_p0_3_sop_quality_full_scan_no_500(e2e_env):
    """Bug#3: POST /agent/sop/quality/check（全扫模式）曾 500（SOP.is_active 不存在）。

    修复后：不再使用 SOP.is_active，全扫模式返回 200，含 alerts/tickets_created 结构。
    """
    client, session_factory = e2e_env
    _user_id, email, login_data = helpers.register_and_login(
        client,
        email_prefix="reg_p0_3",
        role="teacher",
    )
    token = login_data["access_token"]
    asyncio.run(
        _grant_agent_permissions(
            session_factory,
            email=email,
            permission_keys=["agent:execute"],
        )
    )

    resp = client.post(
        "/api/v1/agent/sop/quality/check",
        headers={"Authorization": f"Bearer {token}"},
        json={"time_range_days": 30},  # 无 sop_id → 全扫模式
    )
    # 必须断言的正确行为：≠500；返回结构含扫描结果
    assert resp.status_code != 500, f"不应 500: {resp.text}"
    assert resp.status_code == 200, f"期望 200, 实际 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert "alerts" in body, f"缺少 alerts 字段: {body}"
    assert "tickets_created" in body, f"缺少 tickets_created 字段: {body}"


# ─────────────────────────────────────────────────────────────────────────────
# P0#4: GET /agent/approval/history 曾恒空（参数顺序错位）
# 端点: GET /api/v1/agent/approval/history
# 根因: get_request_history(limit) 把 limit 传给了 requester_id 参数位置
# ─────────────────────────────────────────────────────────────────────────────

def test_p0_4_approval_history_returns_records(e2e_env):
    """Bug#4: GET /agent/approval/history 曾恒空（limit 传给了 requester_id）。

    修复后：先创建 1 条审批请求，GET /approval/history 能查到它（非空）。
    """
    client, session_factory = e2e_env
    _user_id, email, login_data = helpers.register_and_login(
        client,
        email_prefix="reg_p0_4",
        role="teacher",
    )
    token = login_data["access_token"]
    asyncio.run(
        _grant_agent_permissions(
            session_factory,
            email=email,
            permission_keys=["agent:read", "agent:execute"],
        )
    )

    # 先建 1 条审批请求进入内存队列
    unique_resource_id = "regression-p0-4-resource-001"
    create_resp = client.post(
        "/api/v1/agent/approval/request",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "requester_id": "reg_p0_4_user",
            "resource_type": "sops",
            "resource_id": unique_resource_id,
            "action": "sops.write",
            "reason": "P0#4 regression test",
            "priority": "high",
            "evidence_refs": [],
            "ttl_seconds": 3600,
        },
    )
    assert create_resp.status_code == 200, f"创建审批失败: {create_resp.text}"

    resp = client.get(
        "/api/v1/agent/approval/history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert "requests" in body, f"缺少 requests 字段: {body}"
    # 必须断言的正确行为：建 1 条审批后查询非空（曾恒空）
    assert isinstance(body["requests"], list), "requests 不是列表"
    assert any(r["resource_id"] == unique_resource_id for r in body["requests"]), (
        f"历史列表应包含刚创建的审批请求 resource_id={unique_resource_id}，实际: {body['requests']}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# P0#5: POST /agent/execute（command 模式）曾恒 error（Command kwarg 用错）
# 端点: POST /api/v1/agent/execute
# 根因: Command(user_id=...) 用错 kwarg（应 actor_user_id）导致 Command 构造失败
# ─────────────────────────────────────────────────────────────────────────────

def test_p0_5_agent_execute_command_mode_succeeds(e2e_env):
    """Bug#5: POST /agent/execute（command 模式）曾恒 error（Command kwarg 用错）。

    修复后：无副作用 command 正常执行，status="success"（而非 "error"）。
    """
    client, session_factory = e2e_env
    _user_id, email, login_data = helpers.register_and_login(
        client,
        email_prefix="reg_p0_5",
        role="teacher",
    )
    token = login_data["access_token"]
    asyncio.run(
        _grant_agent_permissions(
            session_factory,
            email=email,
            permission_keys=["agent:execute"],
        )
    )

    resp = client.post(
        "/api/v1/agent/execute",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "user_id": "user-p0-5-cmd",
            "mode": "command",
            "intent": "dispatch",
            "tool_name": "sops.read",
            "tool_args": {},
            "side_effects": [],
        },
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    # 必须断言的正确行为：非 error 结果（曾恒 error：Command kwarg 用错）
    assert body.get("status") != "error", (
        f"status 不应为 error，实际: {body}"
    )
    assert body.get("status") == "success", (
        f"无副作用 command 应返回 status=success，实际: {body}"
    )
    assert body.get("mode_used") == "command", f"mode_used 应为 command，实际: {body}"


# ─────────────────────────────────────────────────────────────────────────────
# P0#6: POST /training/workbench/draft — JSONDecodeError 曾走死代码返回 400
# 端点: POST /api/v1/training/workbench/draft
# 根因: except ValueError 在 except json.JSONDecodeError 之前（后者是子类）→ 死代码
# ─────────────────────────────────────────────────────────────────────────────

def test_p0_6_workbench_draft_json_decode_error_returns_502(e2e_env, monkeypatch):
    """Bug#6: POST /training/workbench/draft JSONDecodeError 曾走 ValueError 分支返回 400（死代码 bug）。

    修复后：except json.JSONDecodeError 排在 except ValueError 之前，AI 结果解析失败
    正确返回 502（网关级错误），而非误判为 400 输入错误。
    """
    import app.api.v1.endpoints.training as training_endpoints

    client, session_factory = e2e_env
    _user_id, email, login_data = helpers.register_and_login(
        client,
        email_prefix="reg_p0_6",
        role="teacher",
    )
    token = login_data["access_token"]

    async def _fake_draft_json_error(
        self, *, user_id, robot_model, robot_id, task_summary, focus_prompt
    ):
        raise json.JSONDecodeError("AI 返回了坏 JSON", "", 0)

    monkeypatch.setattr(
        "app.services.training.workbench_draft_generator.TrainingWorkbenchDraftGenerator.generate",
        _fake_draft_json_error,
    )

    resp = client.post(
        "/api/v1/training/workbench/draft",
        headers={"Authorization": f"Bearer {token}"},
        json={"robot_model": "ABB-IRB120", "task_summary": "关节电机盖拆装", "focus_prompt": "强调工具确认"},
    )
    # 必须断言的正确行为：JSONDecodeError → 502（修复前因死代码进 ValueError 分支返回 400）
    assert resp.status_code == 502, (
        f"JSONDecodeError 应返回 502，实际 {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    # 响应体包含训练草案相关错误描述
    assert "训练草案" in body.get("message", ""), (
        f"message 应含 '训练草案'，实际: {body}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# P0#7: GET /teaching/attempts/{id}/diagnosis（attempt 无 task_id）曾 500
# 端点: GET /api/v1/attempts/{attempt_id}/diagnosis
# 根因: 未处理空 task_id，EvidenceFallbackError(task_id=None) 未被捕获 → 500
# ─────────────────────────────────────────────────────────────────────────────

def test_p0_7_diagnosis_null_task_id_no_500(e2e_env):
    """Bug#7: GET /attempts/{id}/diagnosis（attempt 无 task_id）曾 500。

    修复后：attempt 未关联 task（task_id=None）是数据状态，endpoint 返回 ≠500
    的结构化错误或降级响应（404 或含诊断错误描述的响应）。
    """
    client, session_factory = e2e_env
    attempt_id = asyncio.run(
        _seed_attempt_no_task(session_factory, student_id=20241)
    )

    resp = client.get(f"/api/v1/attempts/{attempt_id}/diagnosis")
    # 必须断言的正确行为：≠500（曾因 task_id=None 未处理而 500）
    assert resp.status_code != 500, (
        f"不应 500，实际 {resp.status_code}: {resp.text}"
    )
    # 修复后返回 404 + 含 "诊断" 的错误消息（或其他结构化错误响应）
    assert resp.status_code == 404, (
        f"期望 404，实际 {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert "诊断" in body.get("message", ""), (
        f"message 应含 '诊断'，实际: {body}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# P0#8: teaching._raise_not_found 的 404 响应 error_type 曾为 'HTTPException'
# 端点: 任意 teaching 404 路径（使用 GET /api/v1/attempts/9999/diagnosis）
# 根因: ResourceNotFoundError 被转成通用 HTTPException，丢失类型信息
# ─────────────────────────────────────────────────────────────────────────────

def test_p0_8_not_found_error_type_is_resource_not_found(e2e_env):
    """Bug#8: teaching._raise_not_found 的 404 响应 error_type 曾错为 'HTTPException'。

    修复后：_raise_not_found 直接 raise ResourceNotFoundError，全局 handler 将其
    正确序列化为 error_type='ResourceNotFoundError'，而不是 'HTTPException'。
    """
    client, session_factory = e2e_env

    # 使用不存在的 attempt_id 触发 _raise_not_found 路径
    resp = client.get("/api/v1/attempts/9999/diagnosis")

    assert resp.status_code == 404, (
        f"期望 404，实际 {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    # 必须断言的正确行为：error_type 为资源未找到类型，不是 'HTTPException'
    assert body.get("error_type") == "ResourceNotFoundError", (
        f"error_type 应为 'ResourceNotFoundError'，实际: {body.get('error_type')!r}。"
        f"完整响应: {body}"
    )
    assert "9999" in str(body.get("details", "")), (
        f"details 应含 attempt_id 9999，实际: {body}"
    )
