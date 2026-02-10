"""Gate-2 E-001：Tool Executor 最小读链路测试。"""
from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.api.v1.endpoints.ai_commands as ai_commands_endpoint
from app.core.database import get_db
from app.models.approval import Approval
from app.models.audit_event import AuditEvent
from app.models.base import Base
from app.models.command_runtime import AIToolCall, Command
from app.models.knowledge_chunk import AIKnowledgeChunk
from main import app
import app.models as app_models  # noqa: F401  # 确保模型全部注册


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


def _register_and_login(client: TestClient, *, email: str) -> str:
    register_resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "StrongPass123", "full_name": "工具调用用户"},
    )
    assert register_resp.status_code == 201

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert login_resp.status_code == 200
    return login_resp.json()["access_token"]


async def _query_audits_by_trace(
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


async def _latest_command_and_tool_call(
    session_factory: async_sessionmaker,
    *,
    trace_id: str,
) -> tuple[Command | None, AIToolCall | None]:
    async with session_factory() as session:
        command_result = await session.execute(
            select(Command)
            .where(Command.trace_id == trace_id)
            .order_by(Command.id.desc())
        )
        command = command_result.scalars().first()

        tool_result = await session.execute(
            select(AIToolCall)
            .where(AIToolCall.trace_id == trace_id)
            .order_by(AIToolCall.id.desc())
        )
        tool_call = tool_result.scalars().first()

        return command, tool_call


async def _latest_runtime_bundle(
    session_factory: async_sessionmaker,
    *,
    trace_id: str,
) -> tuple[Command | None, AIToolCall | None, Approval | None]:
    async with session_factory() as session:
        command_result = await session.execute(
            select(Command)
            .where(Command.trace_id == trace_id)
            .order_by(Command.id.desc())
        )
        command = command_result.scalars().first()

        tool_result = await session.execute(
            select(AIToolCall)
            .where(AIToolCall.trace_id == trace_id)
            .order_by(AIToolCall.id.desc())
        )
        tool_call = tool_result.scalars().first()

        approval_result = await session.execute(
            select(Approval)
            .where(Approval.trace_id == trace_id)
            .order_by(Approval.id.desc())
        )
        approval = approval_result.scalars().first()

        return command, tool_call, approval


async def _create_knowledge_chunk(
    session_factory: async_sessionmaker,
    *,
    chunk_id: str,
    owner_user_id: str,
    content: str = "证据片段",
) -> AIKnowledgeChunk:
    async with session_factory() as session:
        chunk = AIKnowledgeChunk(
            id=chunk_id,
            source_type="evidence",
            source_id="EVID-001",
            content=content,
            owner_user_id=owner_user_id,
            course_id="COURSE-001",
        )
        session.add(chunk)
        await session.commit()
        await session.refresh(chunk)
        return chunk


def test_ai_command_read_tool_success_records_trace_audits() -> None:
    client, session_factory = _build_client()
    try:
        token = _register_and_login(client, email="command_read_success@example.com")
        response = client.post(
            "/api/v1/ai/commands",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "intent": "get_robot_structure",
                "skill_id": "robot.read.structure",
                "tool_name": "robot.get_structure",
                "tool_args": {"robot_id": "R-001"},
                "side_effects": [],
            },
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["status"] == "succeeded"
        trace_id = payload["trace_id"]
        assert trace_id

        audits = asyncio.run(_query_audits_by_trace(session_factory, trace_id=trace_id))
        actions = [event.action for event in audits]
        assert "command_created" in actions
        assert "tool_call_pending" in actions
        assert "tool_call_success" in actions

        command, tool_call = asyncio.run(
            _latest_command_and_tool_call(session_factory, trace_id=trace_id)
        )
        assert command is not None
        assert command.status == "succeeded"
        assert tool_call is not None
        assert tool_call.status == "success"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_ai_command_dispatch_without_tool_name_builds_minimal_plan_and_waiting_approval() -> None:
    client, session_factory = _build_client()
    try:
        token = _register_and_login(client, email="command_dispatch_planner@example.com")
        response = client.post(
            "/api/v1/ai/commands",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "intent": "dispatch",
                "input_text": "创建中级电机故障作业",
                "tool_args": {"course_id": "COURSE-001"},
                "side_effects": [],
            },
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["status"] == "waiting_approval"
        assert payload["approval_id"] is not None
        assert payload["trace_id"]

        result_payload = payload["result"]
        assert result_payload["status"] == "waiting_approval"
        assert result_payload["sop_draft_id"].startswith("sop-draft-")
        assert result_payload["task_chain_draft_id"].startswith("task-chain-")
        assert result_payload["rubric_draft_id"].startswith("rubric-")
        assert result_payload["citations"]
        assert result_payload["tool_plan"]["tool_name"] == "assignments.create_draft"
        assert result_payload["tool_plan"]["side_effects"] == ["assignments.write"]

        trace_id = payload["trace_id"]
        audits = asyncio.run(_query_audits_by_trace(session_factory, trace_id=trace_id))
        actions = [event.action for event in audits]
        assert "command_created" in actions
        assert "tool_plan_generated" in actions
        assert "tool_call_pending" in actions
        assert "approval_created" in actions
        tool_plan_generated = next(event for event in audits if event.action == "tool_plan_generated")
        assert tool_plan_generated.trace_id == trace_id
        assert tool_plan_generated.reason == "dispatch_minimal_planner"
        assert tool_plan_generated.resource_type == "Command"
        approval_created = next(event for event in audits if event.action == "approval_created")
        assert approval_created.trace_id == trace_id
        assert approval_created.reason == "approval_pending_created"
        assert approval_created.resource_type == "Approval"
        assert approval_created.tool_call_args is not None
        assert approval_created.tool_call_args.get("input_text") == "创建中级电机故障作业"

        command, tool_call, approval = asyncio.run(
            _latest_runtime_bundle(session_factory, trace_id=trace_id)
        )
        assert command is not None
        assert tool_call is not None
        assert approval is not None
        assert command.status == "waiting_approval"
        assert tool_call.status == "pending"
        assert tool_call.side_effects == ["assignments.write"]
        assert command.approval_id == approval.id
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_ai_command_no_result_returns_insufficient_data_template(monkeypatch) -> None:
    client, session_factory = _build_client()
    try:
        def _fake_execute_read_tool(
            *,
            intent: str,
            tool_name: str,
            skill_id: str | None,
            tool_args: dict[str, object],
        ) -> dict[str, object]:
            return {
                "tool_name": tool_name,
                "intent": intent,
                "skill_id": skill_id,
                "summary": "fake-rag-result",
                "echo_args": dict(tool_args),
                "status": "ok",
                "hits": [],
                "items": [],
            }

        monkeypatch.setattr(ai_commands_endpoint, "execute_read_tool", _fake_execute_read_tool)

        token = _register_and_login(client, email="command_rag_insufficient_data@example.com")
        response = client.post(
            "/api/v1/ai/commands",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "intent": "explain",
                "skill_id": "rag.read.explain",
                "tool_name": "rag.query",
                "tool_args": {"input_text": "主题A-空命中"},
                "side_effects": [],
            },
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["status"] == "succeeded"
        result_payload = payload["result"]
        assert result_payload["status"] == "insufficient_data"
        assert result_payload["query"] == "主题A-空命中"
        assert isinstance(result_payload["missing_items"], list)
        assert result_payload["missing_items"]

        trace_id = payload["trace_id"]
        audits = asyncio.run(_query_audits_by_trace(session_factory, trace_id=trace_id))
        actions = [event.action for event in audits]
        assert "command_created" in actions
        assert "tool_call_pending" in actions
        assert "tool_call_success" in actions
        assert any(event.action == "tool_call_success" and event.reason == "insufficient_data" for event in audits)
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_ai_command_force_empty_without_monkeypatch_returns_insufficient_data_template() -> None:
    client, session_factory = _build_client()
    try:
        token = _register_and_login(client, email="command_rag_force_empty@example.com")
        response = client.post(
            "/api/v1/ai/commands",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "intent": "explain",
                "skill_id": "rag.read.explain",
                "tool_name": "rag.query",
                "tool_args": {"input_text": "主题B-强制空命中", "force_empty": True},
                "side_effects": [],
            },
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["status"] == "succeeded"
        result_payload = payload["result"]
        assert result_payload["status"] == "insufficient_data"
        assert result_payload["query"] == "主题B-强制空命中"

        trace_id = payload["trace_id"]
        audits = asyncio.run(_query_audits_by_trace(session_factory, trace_id=trace_id))
        assert any(event.action == "tool_call_success" and event.reason == "insufficient_data" for event in audits)
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_ai_command_write_tool_keeps_pending_without_success_audit() -> None:
    client, session_factory = _build_client()
    try:
        token = _register_and_login(client, email="command_write_pending@example.com")
        response = client.post(
            "/api/v1/ai/commands",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "intent": "create_sop_draft",
                "skill_id": "sop.write.create_draft",
                "tool_name": "sops.create_draft",
                "tool_args": {"title": "高压柜巡检"},
                "side_effects": ["sops.write"],
            },
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["status"] == "pending_approval"
        trace_id = payload["trace_id"]
        assert trace_id

        audits = asyncio.run(_query_audits_by_trace(session_factory, trace_id=trace_id))
        actions = [event.action for event in audits]
        assert "command_created" in actions
        assert "tool_call_pending" in actions
        assert "tool_call_success" not in actions

        command, tool_call = asyncio.run(
            _latest_command_and_tool_call(session_factory, trace_id=trace_id)
        )
        assert command is not None
        assert command.status == "pending_approval"
        assert tool_call is not None
        assert tool_call.status == "pending"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_rag_query_returns_verifiable_citations_rag_t007() -> None:
    client, session_factory = _build_client()
    try:
        register_resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "citation_owner@example.com",
                "password": "StrongPass123",
                "full_name": "引用拥有者",
            },
        )
        assert register_resp.status_code == 201
        owner_user_id = str(register_resp.json()["user_id"])
        owner_login = client.post(
            "/api/v1/auth/login",
            json={"email": "citation_owner@example.com", "password": "StrongPass123"},
        )
        assert owner_login.status_code == 200
        owner_token = owner_login.json()["access_token"]

        chunk_id = "chunk-rag-t007-001"
        asyncio.run(
            _create_knowledge_chunk(
                session_factory,
                chunk_id=chunk_id,
                owner_user_id=owner_user_id,
                content="RAG-T007 最小引用证据",
            )
        )

        cmd_resp = client.post(
            "/api/v1/ai/commands",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={
                "intent": "explain",
                "skill_id": "rag.read.explain",
                "tool_name": "rag.query",
                "tool_args": {
                    "input_text": "检索可验证引用",
                    "ref_ids": [chunk_id],
                },
                "side_effects": [],
            },
        )
        assert cmd_resp.status_code == 201
        payload = cmd_resp.json()
        assert payload["status"] == "succeeded"
        citations = payload["result"]["citations"]
        assert citations and citations[0]["ref_id"] == chunk_id

        citation_resp = client.get(
            f"/api/v1/ai/citations/{chunk_id}",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert citation_resp.status_code == 200
        citation_payload = citation_resp.json()
        assert citation_payload["ref_id"] == chunk_id
        assert citation_payload["content"] == "RAG-T007 最小引用证据"
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_citation_scope_mismatch_returns_404_and_records_deny_audit() -> None:
    client, session_factory = _build_client()
    try:
        owner_register = client.post(
            "/api/v1/auth/register",
            json={
                "email": "citation_owner_2@example.com",
                "password": "StrongPass123",
                "full_name": "引用拥有者2",
            },
        )
        assert owner_register.status_code == 201
        owner_user_id = str(owner_register.json()["user_id"])

        student_register = client.post(
            "/api/v1/auth/register",
            json={
                "email": "citation_student@example.com",
                "password": "StrongPass123",
                "full_name": "学生",
            },
        )
        assert student_register.status_code == 201
        student_login = client.post(
            "/api/v1/auth/login",
            json={"email": "citation_student@example.com", "password": "StrongPass123"},
        )
        assert student_login.status_code == 200
        student_token = student_login.json()["access_token"]

        chunk_id = "chunk-rag-t007-002"
        asyncio.run(
            _create_knowledge_chunk(
                session_factory,
                chunk_id=chunk_id,
                owner_user_id=owner_user_id,
                content="仅拥有者可读的证据",
            )
        )

        deny_resp = client.get(
            f"/api/v1/ai/citations/{chunk_id}",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert deny_resp.status_code == 404
        body = deny_resp.json()
        assert body["error_type"] == "ReadAccessDeniedError"
        assert body["details"]["code"] == "READ_ACCESS_DENIED"
        assert body["details"]["details"]["resource_id"] == chunk_id

        async def assert_deny_audit() -> None:
            async with session_factory() as session:
                result = await session.execute(
                    select(AuditEvent)
                    .where(
                        AuditEvent.action == "access_denied",
                        AuditEvent.resource_type == "AIKnowledgeChunk",
                        AuditEvent.resource_id == chunk_id,
                        AuditEvent.decision == "deny",
                    )
                    .order_by(AuditEvent.id.desc())
                )
                event = result.scalars().first()
                assert event is not None
                assert event.reason == "citation_scope_mismatch"

        asyncio.run(assert_deny_audit())
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_rag_query_endpoint_returns_insufficient_data_template_rag_t006() -> None:
    client, session_factory = _build_client()
    try:
        token = _register_and_login(client, email="rag_query_t006@example.com")
        response = client.post(
            "/api/v1/ai/rag/query",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "input_text": "不存在的主题-H002",
                "tool_args": {"force_empty": True},
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "insufficient_data"
        result_payload = payload["result"]
        assert result_payload["status"] == "insufficient_data"
        assert result_payload["query"] == "不存在的主题-H002"
        assert payload["trace_id"]

        audits = asyncio.run(_query_audits_by_trace(session_factory, trace_id=payload["trace_id"]))
        assert any(
            event.action == "rag_query"
            and event.decision == "allow"
            and event.reason == "insufficient_data"
            for event in audits
        )
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None


def test_rag_query_endpoint_returns_verifiable_citations_rag_t007() -> None:
    client, session_factory = _build_client()
    try:
        register_resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "rag_query_owner@example.com",
                "password": "StrongPass123",
                "full_name": "RAG查询拥有者",
            },
        )
        assert register_resp.status_code == 201
        owner_user_id = str(register_resp.json()["user_id"])
        owner_login = client.post(
            "/api/v1/auth/login",
            json={"email": "rag_query_owner@example.com", "password": "StrongPass123"},
        )
        assert owner_login.status_code == 200
        owner_token = owner_login.json()["access_token"]

        chunk_id = "chunk-rag-h002-001"
        asyncio.run(
            _create_knowledge_chunk(
                session_factory,
                chunk_id=chunk_id,
                owner_user_id=owner_user_id,
                content="H-002 引用可验证片段",
            )
        )

        response = client.post(
            "/api/v1/ai/rag/query",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={
                "input_text": "检索H-002引用",
                "tool_args": {"ref_ids": [chunk_id]},
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        citations = payload["result"]["citations"]
        assert citations and citations[0]["ref_id"] == chunk_id

        citation_resp = client.get(
            f"/api/v1/ai/citations/{chunk_id}",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert citation_resp.status_code == 200
        assert citation_resp.json()["ref_id"] == chunk_id

        audits = asyncio.run(_query_audits_by_trace(session_factory, trace_id=payload["trace_id"]))
        assert any(
            event.action == "rag_query"
            and event.decision == "allow"
            and event.reason == "query_success"
            for event in audits
        )
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.state.test_sessionmaker = None
