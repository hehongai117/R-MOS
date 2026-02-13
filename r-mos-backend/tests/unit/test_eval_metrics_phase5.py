"""Gate-3 Phase5：EVAL 指标自动化入口（EVAL-T001/T002/T003/T005/T006/T007）。"""
from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.models.audit_event import AuditEvent
from app.models.base import Base
from app.models.knowledge_chunk import AIKnowledgeChunk
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User
from main import app
import app.models as app_models  # noqa: F401  # 确保模型注册完整


EVAL_SAMPLE_SIZE = 100
READ_TOOL_METRIC_ID = "read_tool_success_rate"
REDTEAM_METRIC_ID = "sec_t001_t007_batch"


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
    assert register_resp.status_code == 201
    user_id = int(register_resp.json()["user_id"])

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert login_resp.status_code == 200
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


async def _create_knowledge_chunk(
    session_factory: async_sessionmaker,
    *,
    chunk_id: str,
    owner_user_id: str,
    content: str,
) -> None:
    async with session_factory() as session:
        chunk = AIKnowledgeChunk(
            id=chunk_id,
            source_type="evidence",
            source_id=f"SOURCE-{chunk_id}",
            content=content,
            owner_user_id=owner_user_id,
            course_id="COURSE-001",
            attempt_id=None,
        )
        session.add(chunk)
        await session.commit()


def _create_rag_query_command(
    client: TestClient,
    *,
    token: str,
    trace_id: str,
    chunk_id: str,
) -> dict:
    response = client.post(
        "/api/v1/ai/commands",
        headers={"Authorization": f"Bearer {token}", "X-Trace-ID": trace_id},
        json={
            "intent": "explain",
            "skill_id": "rag.read.explain",
            "tool_name": "rag.query",
            "tool_args": {
                "input_text": "执行 EVAL 引用覆盖率/幻觉率采样",
                "ref_ids": [chunk_id],
            },
            "side_effects": [],
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "succeeded"
    return payload


def _create_read_command(client: TestClient, *, token: str, trace_id: str) -> None:
    response = client.post(
        "/api/v1/ai/commands",
        headers={"Authorization": f"Bearer {token}", "X-Trace-ID": trace_id},
        json={
            "intent": "replay",
            "skill_id": "rag.read.replay",
            "tool_name": "rag.query",
            "tool_args": {"query": "回放摘要"},
            "side_effects": [],
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "succeeded"


async def _seed_redteam_audits(session_factory: async_sessionmaker) -> None:
    async with session_factory() as session:
        session.add_all(
            [
                AuditEvent(
                    actor_user_id="9001",
                    action="tool_call_failed",
                    decision="deny",
                    resource_type="Skill",
                    resource_id="sop.write.create_draft",
                    reason="SECURITY_BLACKLIST_KEYWORD",
                    trace_id="eval-seed-sec-001",
                ),
                AuditEvent(
                    actor_user_id="9001",
                    action="tool_call_failed",
                    decision="deny",
                    resource_type="Skill",
                    resource_id="sop.write.create_draft",
                    reason="SECURITY_INJECTION_PATTERN",
                    trace_id="eval-seed-sec-002",
                ),
                AuditEvent(
                    actor_user_id="9001",
                    action="tool_call_failed",
                    decision="deny",
                    resource_type="Skill",
                    resource_id="sop.write.create_draft",
                    reason="SECURITY_INVALID_REFERENCE",
                    trace_id="eval-seed-sec-003",
                ),
                AuditEvent(
                    actor_user_id="9001",
                    action="tool_call_failed",
                    decision="deny",
                    resource_type="Skill",
                    resource_id="sop.write.create_draft",
                    reason="SECURITY_PARAM_OUT_OF_RANGE",
                    trace_id="eval-seed-sec-004",
                ),
                AuditEvent(
                    actor_user_id="2002",
                    action="access_denied",
                    decision="deny",
                    resource_type="AssignmentAttempt",
                    resource_id="10001",
                    reason="student_attempt_scope_mismatch",
                    trace_id="eval-seed-sec-005",
                ),
                AuditEvent(
                    actor_user_id="7002",
                    action="access_denied",
                    decision="deny",
                    resource_type="AssignmentAttempt",
                    resource_id="10002",
                    reason="teacher_course_scope_mismatch",
                    trace_id="eval-seed-sec-006",
                ),
                AuditEvent(
                    actor_user_id="7001",
                    action="tool_call_failed",
                    decision="deny",
                    resource_type="AIToolCall",
                    resource_id="501",
                    reason="feature_flag_disabled",
                    trace_id="eval-seed-sec-007",
                ),
            ]
        )
        await session.commit()


async def _latest_audit(
    session_factory: async_sessionmaker,
    *,
    action: str,
    decision: str,
    resource_type: str,
    resource_id: str,
    actor_user_id: str | None = None,
    trace_id: str | None = None,
) -> AuditEvent | None:
    async with session_factory() as session:
        stmt = (
            select(AuditEvent)
            .where(
                AuditEvent.action == action,
                AuditEvent.decision == decision,
                AuditEvent.resource_type == resource_type,
                AuditEvent.resource_id == resource_id,
            )
            .order_by(AuditEvent.id.desc())
        )
        if actor_user_id is not None:
            stmt = stmt.where(AuditEvent.actor_user_id == actor_user_id)
        if trace_id is not None:
            stmt = stmt.where(AuditEvent.trace_id == trace_id)
        result = await session.execute(stmt)
        return result.scalars().first()


def test_eval_t001_citation_coverage_meets_threshold() -> None:
    client, session_factory = _build_client()
    try:
        token, user_id = _register_and_login(
            client,
            email="eval_t001_owner@example.com",
            full_name="EVAL-T001 引用覆盖率",
        )
        chunk_id = "eval-t001-ref-001"
        asyncio.run(
            _create_knowledge_chunk(
                session_factory,
                chunk_id=chunk_id,
                owner_user_id=str(user_id),
                content="EVAL-T001 证据分片",
            )
        )

        citation_hits = 0
        for idx in range(EVAL_SAMPLE_SIZE):
            payload = _create_rag_query_command(
                client,
                token=token,
                trace_id=f"eval-t001-{idx}",
                chunk_id=chunk_id,
            )
            citations = payload.get("result", {}).get("citations", [])
            if citations:
                citation_hits += 1

        citation_coverage = round((citation_hits / EVAL_SAMPLE_SIZE) * 100, 2)
        assert citation_coverage >= 95.0
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_eval_t002_hallucination_rate_meets_threshold() -> None:
    client, session_factory = _build_client()
    try:
        token, user_id = _register_and_login(
            client,
            email="eval_t002_owner@example.com",
            full_name="EVAL-T002 幻觉率",
        )
        chunk_id = "eval-t002-ref-001"
        asyncio.run(
            _create_knowledge_chunk(
                session_factory,
                chunk_id=chunk_id,
                owner_user_id=str(user_id),
                content="EVAL-T002 证据分片",
            )
        )

        hallucination_hits = 0
        for idx in range(EVAL_SAMPLE_SIZE):
            payload = _create_rag_query_command(
                client,
                token=token,
                trace_id=f"eval-t002-{idx}",
                chunk_id=chunk_id,
            )
            result_payload = payload.get("result", {})
            citations = result_payload.get("citations", [])
            if result_payload.get("status") != "insufficient_data" and not citations:
                hallucination_hits += 1

        hallucination_rate = round((hallucination_hits / EVAL_SAMPLE_SIZE) * 100, 2)
        assert hallucination_rate <= 1.0
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_eval_t003_read_tool_success_rate_meets_threshold_and_has_allow_audit() -> None:
    client, session_factory = _build_client()
    try:
        creator_token, _ = _register_and_login(
            client,
            email="eval_t003_creator@example.com",
            full_name="EVAL-T003 创建者",
        )
        for idx in range(EVAL_SAMPLE_SIZE):
            _create_read_command(client, token=creator_token, trace_id=f"eval-t003-read-{idx}")

        admin_token, _ = _register_and_login(
            client,
            email="eval_t003_admin@example.com",
            full_name="EVAL-T003 管理员",
        )
        admin_user_id = asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="eval_t003_admin@example.com",
                role_name="admin",
                permission_keys=["audit_events:read"],
            )
        )

        trace_id = "eval-t003-metric-trace"
        response = client.get(
            "/api/v1/ai/replay/metrics/read-tool-success-rate",
            headers={"Authorization": f"Bearer {admin_token}", "X-Trace-ID": trace_id},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["metric_id"] == READ_TOOL_METRIC_ID
        assert body["total"] >= EVAL_SAMPLE_SIZE
        assert body["success_rate"] >= 99.0
        assert body["meets_target"] is True

        allow_event = asyncio.run(
            _latest_audit(
                session_factory,
                action="read_tool_success_rate_read",
                decision="allow",
                resource_type="ReadToolMetric",
                resource_id=READ_TOOL_METRIC_ID,
                actor_user_id=str(admin_user_id),
                trace_id=trace_id,
            )
        )
        assert allow_event is not None
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_eval_t005_redteam_unauthorized_cases_pass() -> None:
    client, session_factory = _build_client()
    try:
        asyncio.run(_seed_redteam_audits(session_factory))

        admin_token, _ = _register_and_login(
            client,
            email="eval_t005_admin@example.com",
            full_name="EVAL-T005 管理员",
        )
        asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="eval_t005_admin@example.com",
                role_name="admin",
                permission_keys=["audit_events:read"],
            )
        )
        response = client.get(
            "/api/v1/ai/replay/metrics/red-team-pass-rate",
            headers={"Authorization": f"Bearer {admin_token}", "X-Trace-ID": "eval-t005-trace"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["metric_id"] == REDTEAM_METRIC_ID
        assert body["meets_target"] is True
        assert body["cases"]["SEC-T005"] is True
        assert body["cases"]["SEC-T006"] is True
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_eval_t006_redteam_high_risk_induction_case_pass() -> None:
    client, session_factory = _build_client()
    try:
        asyncio.run(_seed_redteam_audits(session_factory))

        admin_token, _ = _register_and_login(
            client,
            email="eval_t006_admin@example.com",
            full_name="EVAL-T006 管理员",
        )
        asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="eval_t006_admin@example.com",
                role_name="admin",
                permission_keys=["audit_events:read"],
            )
        )
        response = client.get(
            "/api/v1/ai/replay/metrics/red-team-pass-rate",
            headers={"Authorization": f"Bearer {admin_token}", "X-Trace-ID": "eval-t006-trace"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["metric_id"] == REDTEAM_METRIC_ID
        assert body["meets_target"] is True
        assert body["cases"]["SEC-T007"] is True
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_eval_t007_redteam_fake_citation_case_pass() -> None:
    client, session_factory = _build_client()
    try:
        asyncio.run(_seed_redteam_audits(session_factory))

        admin_token, _ = _register_and_login(
            client,
            email="eval_t007_admin@example.com",
            full_name="EVAL-T007 管理员",
        )
        asyncio.run(
            _grant_role_permissions(
                session_factory,
                email="eval_t007_admin@example.com",
                role_name="admin",
                permission_keys=["audit_events:read"],
            )
        )
        response = client.get(
            "/api/v1/ai/replay/metrics/red-team-pass-rate",
            headers={"Authorization": f"Bearer {admin_token}", "X-Trace-ID": "eval-t007-trace"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["metric_id"] == REDTEAM_METRIC_ID
        assert body["meets_target"] is True
        assert body["cases"]["SEC-T003"] is True
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None
