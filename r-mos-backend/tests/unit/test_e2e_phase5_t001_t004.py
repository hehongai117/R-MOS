"""Gate-3 M3：Phase5 E2E-T001~T004 自动化入口。"""
from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models as app_models  # noqa: F401  # 确保模型注册完整
from app.core.database import get_db
from app.models.approval import Approval
from app.models.audit_event import AuditEvent
from app.models.base import Base
from app.models.command_runtime import AIToolCall, Command
from app.models.knowledge_chunk import AIKnowledgeChunk
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.timeline import AlignmentMap, MultimodalTimeline, TimelineSegment
from app.models.user import User
from app.services.teaching_service import TeachingService
from main import app


def _build_client() -> tuple[TestClient, async_sessionmaker]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async def init_models() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_models())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.state.test_sessionmaker = session_factory
    return TestClient(app), session_factory


def _register_and_login(client: TestClient, *, email: str, full_name: str) -> tuple[str, int]:
    register_resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "StrongPass123", "full_name": full_name},
    )
    assert register_resp.status_code == 201, (
        f"注册失败: status={register_resp.status_code}, body={register_resp.text[:300]}"
    )
    user_id = int(register_resp.json()["user_id"])

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert login_resp.status_code == 200, (
        f"登录失败: status={login_resp.status_code}, body={login_resp.text[:300]}"
    )
    return login_resp.json()["access_token"], user_id


async def _grant_role_permissions(
    session_factory: async_sessionmaker,
    *,
    email: str,
    role_name: str,
    permission_keys: list[str],
) -> int:
    async with session_factory() as session:
        user_result = await session.execute(select(User).where(User.email == email))
        user = user_result.scalar_one()

        role_result = await session.execute(select(Role).where(Role.name == role_name))
        role = role_result.scalar_one_or_none()
        if role is None:
            role = Role(name=role_name, description=f"{role_name} 角色")
            session.add(role)
            await session.flush()

        for permission_key in permission_keys:
            permission_result = await session.execute(
                select(Permission).where(Permission.key == permission_key)
            )
            permission = permission_result.scalar_one_or_none()
            if permission is None:
                resource_type, action = permission_key.split(":", 1)
                permission = Permission(
                    key=permission_key,
                    description=f"{permission_key} 权限",
                    resource_type=resource_type,
                    action=action,
                )
                session.add(permission)
                await session.flush()

            role_permission_result = await session.execute(
                select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == permission.id,
                )
            )
            if role_permission_result.scalar_one_or_none() is None:
                session.add(RolePermission(role_id=role.id, permission_id=permission.id))

        user_role_result = await session.execute(
            select(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.role_id == role.id,
            )
        )
        if user_role_result.scalar_one_or_none() is None:
            session.add(UserRole(user_id=user.id, role_id=role.id))

        await session.commit()
        return int(user.id)


async def _seed_assignment(
    session_factory: async_sessionmaker,
    *,
    teacher_id: int,
) -> int:
    async with session_factory() as session:
        service = TeachingService(session)
        teaching_class = await service.create_class(name="E2E-T001 班级", teacher_id=teacher_id)
        assignment = await service.create_assignment(class_id=teaching_class.id, title="E2E-T001 查询作业")
        return int(assignment.id)


async def _seed_attempt_with_replayable_refs(
    session_factory: async_sessionmaker,
    *,
    teacher_id: int,
    student_id: int,
) -> tuple[int, str, int, int]:
    async with session_factory() as session:
        service = TeachingService(session)
        teaching_class = await service.create_class(name="E2E-T002 班级", teacher_id=teacher_id)
        assignment = await service.create_assignment(class_id=teaching_class.id, title="E2E-T002 作业")
        await service.enroll_student(class_id=teaching_class.id, student_id=student_id)
        attempt = await service.create_attempt(
            assignment_id=assignment.id,
            student_id=student_id,
            task_id=None,
        )

        timeline = MultimodalTimeline(
            scope_type="attempt",
            scope_id=str(attempt.id),
            trace_id=f"e2e-timeline-{attempt.id}",
            created_by_user_id=str(teacher_id),
        )
        session.add(timeline)
        await session.flush()

        ref_id = f"e2e-ref-{uuid4().hex[:8]}"
        segment = TimelineSegment(
            timeline_id=timeline.id,
            segment_type="event",
            ref_id=ref_id,
            start_ts_ms=1000,
            end_ts_ms=1800,
            payload={
                "step_id": 2,
                "event_id": 201,
                "failure_type": "E_ERROR_OCCURRED",
                "rule_hit": "R-DIAG-001",
            },
        )
        session.add(segment)
        await session.flush()

        alignment = AlignmentMap(
            timeline_id=timeline.id,
            anchor_key="failure_point",
            segment_id=segment.id,
            ref_id=ref_id,
            score=0.95,
        )
        session.add(alignment)
        await session.commit()
        return int(attempt.id), ref_id, int(timeline.id), int(segment.id)


async def _seed_private_chunk(
    session_factory: async_sessionmaker,
    *,
    chunk_id: str,
    owner_user_id: str,
) -> None:
    async with session_factory() as session:
        session.add(
            AIKnowledgeChunk(
                id=chunk_id,
                source_type="evidence",
                source_id=f"SRC-{chunk_id}",
                content="E2E-T004 私有引用分片",
                owner_user_id=owner_user_id,
                course_id="COURSE-001",
                attempt_id=None,
            )
        )
        await session.commit()


async def _runtime_bundle_by_trace(
    session_factory: async_sessionmaker,
    *,
    trace_id: str,
) -> tuple[Command, AIToolCall, Approval]:
    async with session_factory() as session:
        command = (await session.execute(select(Command).where(Command.trace_id == trace_id))).scalar_one()
        tool_call = (
            await session.execute(select(AIToolCall).where(AIToolCall.trace_id == trace_id))
        ).scalar_one()
        approval = (await session.execute(select(Approval).where(Approval.trace_id == trace_id))).scalar_one()
        return command, tool_call, approval


async def _audits_by_trace(
    session_factory: async_sessionmaker,
    *,
    trace_id: str,
) -> list[AuditEvent]:
    async with session_factory() as session:
        result = await session.execute(
            select(AuditEvent)
            .where(AuditEvent.trace_id == trace_id)
            .order_by(AuditEvent.id.asc())
        )
        return list(result.scalars().all())


async def _latest_audit(
    session_factory: async_sessionmaker,
    *,
    trace_id: str,
    action: str,
    decision: str,
) -> AuditEvent | None:
    async with session_factory() as session:
        result = await session.execute(
            select(AuditEvent)
            .where(
                AuditEvent.trace_id == trace_id,
                AuditEvent.action == action,
                AuditEvent.decision == decision,
            )
            .order_by(AuditEvent.id.desc())
        )
        return result.scalars().first()


async def _is_ref_replayable(
    session_factory: async_sessionmaker,
    *,
    timeline_id: int,
    segment_id: int,
    ref_id: str,
) -> bool:
    async with session_factory() as session:
        segment_result = await session.execute(
            select(TimelineSegment).where(
                TimelineSegment.id == segment_id,
                TimelineSegment.timeline_id == timeline_id,
                TimelineSegment.ref_id == ref_id,
            )
        )
        segment = segment_result.scalar_one_or_none()
        if segment is None:
            return False

        alignment_result = await session.execute(
            select(AlignmentMap).where(
                AlignmentMap.timeline_id == timeline_id,
                AlignmentMap.segment_id == segment_id,
                AlignmentMap.ref_id == ref_id,
            )
        )
        alignment = alignment_result.scalar_one_or_none()
        return alignment is not None


@pytest.mark.parametrize("test_id", ["E2E-T001"], ids=["E2E-T001"])
def test_e2e_t001_teacher_dispatch_publish_and_query_assignment(test_id: str) -> None:
    _ = test_id
    client, session_factory = _build_client()
    try:
        teacher_token, teacher_user_id = _register_and_login(
            client,
            email="e2e_t001_teacher@example.com",
            full_name="E2E-T001 教师",
        )
        seeded_assignment_id = asyncio.run(
            _seed_assignment(session_factory, teacher_id=teacher_user_id)
        )

        trace_id = "e2e-t001-trace"
        command_resp = client.post(
            "/api/v1/ai/commands",
            headers={"Authorization": f"Bearer {teacher_token}", "X-Trace-ID": trace_id},
            json={
                "intent": "dispatch",
                "input_text": "创建中级电机故障作业并发布",
                "tool_args": {"difficulty": "intermediate"},
                "side_effects": [],
            },
        )
        assert command_resp.status_code == 201, (
            f"派单失败: status={command_resp.status_code}, body={command_resp.text[:300]}"
        )
        command_payload = command_resp.json()
        assert command_payload["status"] == "waiting_approval"
        assert command_payload["approval_id"] is not None
        assert command_payload["trace_id"] == trace_id

        admin_token, _ = _register_and_login(
            client,
            email="e2e_t001_admin@example.com",
            full_name="E2E-T001 管理员",
        )
        asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="e2e_t001_admin@example.com",
                role_name="admin",
                permission_keys=["approvals:grant", "audit_events:read"],
            )
        )
        grant_resp = client.post(
            f"/api/v1/ai/approvals/{command_payload['approval_id']}/grant",
            headers={"Authorization": f"Bearer {admin_token}", "X-Trace-ID": trace_id},
            json={"reason": "E2E-T001 发布审批通过"},
        )
        assert grant_resp.status_code == 200, (
            f"审批失败: status={grant_resp.status_code}, body={grant_resp.text[:300]}"
        )
        grant_payload = grant_resp.json()
        assert grant_payload["status"] == "granted"
        assert grant_payload["command_status"] == "succeeded"
        assert grant_payload["tool_call_status"] == "success"

        assignment_resp = client.get("/api/v1/assignments")
        assert assignment_resp.status_code == 200, (
            f"查询作业失败: status={assignment_resp.status_code}, body={assignment_resp.text[:300]}"
        )
        assignments = assignment_resp.json()
        assert any(item["id"] == seeded_assignment_id for item in assignments)

        command, tool_call, approval = asyncio.run(
            _runtime_bundle_by_trace(session_factory, trace_id=trace_id)
        )
        assert command.trace_id == tool_call.trace_id == approval.trace_id == trace_id
        assert command.status == "succeeded"
        assert tool_call.status == "success"
        assert approval.status == "granted"
        result_payload = tool_call.result_payload or {}
        assert result_payload.get("mode") == "write_stub"
        assert result_payload.get("tool_name") == "assignments.create_draft"

        audits = asyncio.run(_audits_by_trace(session_factory, trace_id=trace_id))
        actions = [item.action for item in audits]
        required_actions = [
            "command_created",
            "tool_plan_generated",
            "tool_call_pending",
            "approval_created",
            "approval_granted",
            "tool_call_success",
        ]
        for action in required_actions:
            assert action in actions
        assert all(item.trace_id == trace_id for item in audits)
        assert actions.index("command_created") < actions.index("approval_granted") < actions.index("tool_call_success")
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


@pytest.mark.parametrize("test_id", ["E2E-T002"], ids=["E2E-T002"])
def test_e2e_t002_student_fail_replay_report_and_refs_replayable(test_id: str) -> None:
    _ = test_id
    client, session_factory = _build_client()
    try:
        attempt_id, replay_ref_id, timeline_id, segment_id = asyncio.run(
            _seed_attempt_with_replayable_refs(
                session_factory,
                teacher_id=7001,
                student_id=2001,
            )
        )

        trace_id = "e2e-t002-trace"
        replay_resp = client.get(
            f"/api/v1/teaching/attempts/{attempt_id}/replay",
            headers={
                "X-RMOS-Role": "student",
                "X-User-ID": "2001",
                "X-Trace-ID": trace_id,
            },
        )
        assert replay_resp.status_code == 200, (
            f"回放失败: status={replay_resp.status_code}, body={replay_resp.text[:300]}"
        )
        replay_payload = replay_resp.json()
        assert replay_payload["status"] == "ok"
        assert replay_payload["failurePoint"]["failureType"] == "E_ERROR_OCCURRED"
        assert replay_payload["evidenceRefs"]

        card_resp = client.post(
            "/api/v1/evidence_cards",
            json={"attemptId": attempt_id, "cardType": "failure_point"},
            headers={
                "X-RMOS-Role": "teacher",
                "X-User-ID": "7001",
                "X-Trace-ID": trace_id,
            },
        )
        assert card_resp.status_code == 201, (
            f"报告生成失败: status={card_resp.status_code}, body={card_resp.text[:300]}"
        )
        card_payload = card_resp.json()
        assert card_payload["references"]

        replay_ref_ids = {item["refId"] for item in replay_payload["evidenceRefs"]}
        card_ref_ids = {item["refId"] for item in card_payload["references"]}
        assert replay_ref_ids.issubset(card_ref_ids)
        assert replay_ref_id in replay_ref_ids

        assert asyncio.run(
            _is_ref_replayable(
                session_factory,
                timeline_id=timeline_id,
                segment_id=segment_id,
                ref_id=replay_ref_id,
            )
        )

        audits = asyncio.run(_audits_by_trace(session_factory, trace_id=trace_id))
        actions = [item.action for item in audits]
        assert "replay_requested" in actions
        assert "evidence_card_created" in actions
        assert all(item.trace_id == trace_id for item in audits)
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


@pytest.mark.parametrize("test_id", ["E2E-T003"], ids=["E2E-T003"])
def test_e2e_t003_difficulty_suggestion_adopt_and_observable_effect(test_id: str) -> None:
    _ = test_id
    client, session_factory = _build_client()
    try:
        teacher_token, _ = _register_and_login(
            client,
            email="e2e_t003_teacher@example.com",
            full_name="E2E-T003 教师",
        )
        trace_id = "e2e-t003-trace"
        suggest_resp = client.post(
            "/api/v1/ai/commands",
            headers={"Authorization": f"Bearer {teacher_token}", "X-Trace-ID": trace_id},
            json={
                "intent": "dispatch",
                "input_text": "将练习难度调整为 intermediate 并发布建议",
                "tool_args": {"difficulty": "intermediate", "target": "assignment:alpha"},
                "side_effects": [],
            },
        )
        assert suggest_resp.status_code == 201, (
            f"生成建议失败: status={suggest_resp.status_code}, body={suggest_resp.text[:300]}"
        )
        suggest_payload = suggest_resp.json()
        assert suggest_payload["status"] == "waiting_approval"
        approval_id = int(suggest_payload["approval_id"])

        admin_token, _ = _register_and_login(
            client,
            email="e2e_t003_admin@example.com",
            full_name="E2E-T003 管理员",
        )
        asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="e2e_t003_admin@example.com",
                role_name="admin",
                permission_keys=["approvals:grant", "audit_events:read"],
            )
        )
        grant_resp = client.post(
            f"/api/v1/ai/approvals/{approval_id}/grant",
            headers={"Authorization": f"Bearer {admin_token}", "X-Trace-ID": trace_id},
            json={"reason": "采纳难度调整建议"},
        )
        assert grant_resp.status_code == 200, (
            f"采纳失败: status={grant_resp.status_code}, body={grant_resp.text[:300]}"
        )
        grant_payload = grant_resp.json()
        assert grant_payload["status"] == "granted"
        assert grant_payload["command_status"] == "succeeded"
        assert grant_payload["tool_call_status"] == "success"

        replay_resp = client.get(
            f"/api/v1/ai/replay/{trace_id}",
            headers={"Authorization": f"Bearer {admin_token}", "X-Trace-ID": trace_id},
        )
        assert replay_resp.status_code == 200, (
            f"观测失败: status={replay_resp.status_code}, body={replay_resp.text[:300]}"
        )
        replay_payload = replay_resp.json()
        actions = [item["action"] for item in replay_payload["items"]]
        assert "tool_plan_generated" in actions
        assert "approval_granted" in actions
        assert "tool_call_success" in actions

        command, tool_call, approval = asyncio.run(
            _runtime_bundle_by_trace(session_factory, trace_id=trace_id)
        )
        assert command.trace_id == tool_call.trace_id == approval.trace_id == trace_id
        assert command.status == "succeeded"
        assert tool_call.status == "success"
        assert approval.status == "granted"
        result_payload = tool_call.result_payload or {}
        assert result_payload.get("mode") == "write_stub"
        assert "assignments.write" in (result_payload.get("applied_side_effects") or [])

        pending_event = asyncio.run(
            _latest_audit(
                session_factory,
                trace_id=trace_id,
                action="tool_call_pending",
                decision="allow",
            )
        )
        assert pending_event is not None
        assert (pending_event.tool_call_args or {}).get("difficulty") == "intermediate"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


@pytest.mark.parametrize("test_id", ["E2E-T004"], ids=["E2E-T004"])
def test_e2e_t004_http_rag_tool_cross_channel_denied_and_audited(test_id: str) -> None:
    _ = test_id
    client, session_factory = _build_client()
    try:
        owner_token, owner_user_id = _register_and_login(
            client,
            email="e2e_t004_owner@example.com",
            full_name="E2E-T004 资源拥有者",
        )
        attacker_token, _ = _register_and_login(
            client,
            email="e2e_t004_attacker@example.com",
            full_name="E2E-T004 攻击者",
        )
        chunk_id = "e2e-t004-private-ref"
        asyncio.run(
            _seed_private_chunk(
                session_factory,
                chunk_id=chunk_id,
                owner_user_id=str(owner_user_id),
            )
        )
        attempt_id, _, _, _ = asyncio.run(
            _seed_attempt_with_replayable_refs(
                session_factory,
                teacher_id=7001,
                student_id=2101,
            )
        )

        http_trace = "e2e-t004-http-trace"
        http_resp = client.get(
            f"/api/v1/attempts/{attempt_id}",
            headers={
                "X-RMOS-Role": "student",
                "X-User-ID": "2102",
                "X-Trace-ID": http_trace,
            },
        )
        assert http_resp.status_code == 404, (
            f"HTTP 越权应拒绝: status={http_resp.status_code}, body={http_resp.text[:300]}"
        )
        http_payload = http_resp.json()
        assert http_payload["error_type"] == "ReadAccessDeniedError"
        assert http_payload["details"]["code"] == "READ_ACCESS_DENIED"

        rag_trace = "e2e-t004-rag-trace"
        rag_resp = client.post(
            "/api/v1/ai/rag/query",
            headers={"Authorization": f"Bearer {attacker_token}", "X-Trace-ID": rag_trace},
            json={
                "input_text": "读取他人引用",
                "tool_args": {"ref_ids": [chunk_id]},
            },
        )
        assert rag_resp.status_code == 200, (
            f"RAG 访问失败: status={rag_resp.status_code}, body={rag_resp.text[:300]}"
        )
        rag_payload = rag_resp.json()
        assert rag_payload["status"] == "insufficient_data"
        assert (rag_payload["result"].get("citations") or []) == []

        tool_trace = "e2e-t004-tool-trace"
        tool_resp = client.post(
            "/api/v1/ai/commands",
            headers={"Authorization": f"Bearer {attacker_token}", "X-Trace-ID": tool_trace},
            json={
                "intent": "explain",
                "skill_id": "rag.read.query",
                "tool_name": "rag.query",
                "tool_args": {"ref_ids": [chunk_id]},
                "side_effects": [],
            },
        )
        assert tool_resp.status_code == 201, (
            f"Tool 访问失败: status={tool_resp.status_code}, body={tool_resp.text[:300]}"
        )
        tool_payload = tool_resp.json()
        assert tool_payload["status"] == "succeeded"
        assert tool_payload["result"]["status"] == "insufficient_data"
        assert (tool_payload["result"].get("citations") or []) == []

        http_deny = asyncio.run(
            _latest_audit(
                session_factory,
                trace_id=http_trace,
                action="read_access_denied",
                decision="deny",
            )
        )
        assert http_deny is not None
        assert http_deny.resource_id == str(attempt_id)

        rag_deny = asyncio.run(
            _latest_audit(
                session_factory,
                trace_id=rag_trace,
                action="rag_filter_applied",
                decision="deny",
            )
        )
        assert rag_deny is not None
        assert rag_deny.reason and "deny_count" in rag_deny.reason

        tool_deny = asyncio.run(
            _latest_audit(
                session_factory,
                trace_id=tool_trace,
                action="rag_filter_applied",
                decision="deny",
            )
        )
        assert tool_deny is not None
        assert tool_deny.reason and "deny_count" in tool_deny.reason

        owner_command_resp = client.post(
            "/api/v1/ai/commands",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={
                "intent": "explain",
                "skill_id": "rag.read.query",
                "tool_name": "rag.query",
                "tool_args": {"ref_ids": [chunk_id]},
                "side_effects": [],
            },
        )
        assert owner_command_resp.status_code == 201, (
            f"拥有者基线访问失败: status={owner_command_resp.status_code}, body={owner_command_resp.text[:300]}"
        )
        owner_payload = owner_command_resp.json()
        assert owner_payload["result"]["citations"]
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None
