"""RMOS-S3-002 模块 H：27 条路由的 HTTP 行为安全网。

本文件只通过真实 HTTP 请求固定当前行为。疑似缺陷不在本批修复；对应测试的
docstring 会明确写出当前行为和待模块 H 改造时处置的事项。
"""
from __future__ import annotations

import asyncio
import io
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models as app_models  # noqa: F401  # 确保所有表都注册到 metadata
from app.core.database import get_db
from app.models.base import Base
from app.models.evidence import EvidenceBundle
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.school import School
from app.models.teaching import EvidenceLink
from app.models.timeline import MultimodalTimeline, TimelineSegment
from app.services.evidence_enforcement import evidence_enforcer
from app.services.teaching_service import TeachingService
from app.services.training.session_service import SessionService
from main import app
from tests.e2e.helpers import E2E_SCHOOL_NAME, register_and_login, set_user_role

pytestmark = [pytest.mark.e2e, pytest.mark.characterization]

NOW = "2026-09-05T08:00:00Z"
HASH = "a" * 64


@pytest.fixture(scope="module")
def module_h_env() -> tuple[TestClient, async_sessionmaker[AsyncSession]]:
    """复用项目既有的内存 SQLite + TestClient 构造方式。"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async def _init() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(School.__table__.insert().values(name=E2E_SCHOOL_NAME))

    asyncio.run(_init())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    app.state.test_sessionmaker = session_factory
    with TestClient(app) as client:
        yield client, session_factory
    app.dependency_overrides.clear()
    app.state.test_sessionmaker = None
    asyncio.run(engine.dispose())


async def _grant_permissions(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    user_id: int,
    role_name: str,
    permission_keys: tuple[str, ...],
) -> None:
    async with session_factory() as session:
        role = Role(name=role_name, description=role_name)
        session.add(role)
        await session.flush()
        for key in permission_keys:
            result = await session.execute(select(Permission).where(Permission.key == key))
            permission = result.scalar_one_or_none()
            if permission is None:
                resource_type, action = key.split(":", 1)
                permission = Permission(
                    key=key,
                    description=key,
                    resource_type=resource_type,
                    action=action,
                )
                session.add(permission)
                await session.flush()
            session.add(RolePermission(role_id=role.id, permission_id=permission.id))
        session.add(UserRole(user_id=user_id, role_id=role.id))
        await session.commit()


@pytest.fixture(scope="module")
def actors(module_h_env) -> dict[str, int | str]:
    client, session_factory = module_h_env
    owner_id, owner_email, owner_login = register_and_login(
        client, email_prefix="module_h_owner"
    )
    other_id, other_email, other_login = register_and_login(
        client, email_prefix="module_h_other"
    )
    student_id, _, student_login = register_and_login(
        client,
        email_prefix="module_h_student",
        role="student",
        teacher_id=owner_id,
    )
    admin_id, _, admin_login = register_and_login(
        client, email_prefix="module_h_admin"
    )
    asyncio.run(set_user_role(session_factory, user_id=admin_id, role="admin"))
    asyncio.run(
        _grant_permissions(
            session_factory,
            user_id=owner_id,
            role_name="module_h_agent_full",
            permission_keys=("agent:read", "agent:execute"),
        )
    )
    asyncio.run(
        _grant_permissions(
            session_factory,
            user_id=other_id,
            role_name="module_h_agent_reader",
            permission_keys=("agent:read",),
        )
    )
    client.headers.pop("Authorization", None)
    return {
        "owner_id": owner_id,
        "owner_email": owner_email,
        "owner_token": owner_login["access_token"],
        "other_id": other_id,
        "other_email": other_email,
        "other_token": other_login["access_token"],
        "student_id": student_id,
        "student_token": student_login["access_token"],
        "admin_id": admin_id,
        "admin_token": admin_login["access_token"],
    }


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _evidence_payload(label: str | None = None) -> dict:
    label = label or uuid4().hex
    return {
        "bundle_type": "event_log",
        "observed_time_start": NOW,
        "items": [
            {
                "evidence_id": f"evidence-{label}-{uuid4().hex}",
                "evidence_type": "event",
                "content_uri": f"memory://{label}",
                "content_hash": HASH,
                "content_hash_algo": "sha256",
                "content_mime_type": "application/json",
                "size_bytes": 12,
                "observed_time": NOW,
                "ingest_time": NOW,
            }
        ],
        "human_summary": f"evidence-{label}",
        "machine_tags": [label],
    }


def _incident_payload(label: str | None = None) -> dict:
    label = label or uuid4().hex
    return {
        "robot_id": f"robot-{label}",
        "incident_type": "operational",
        "incident_level": "warning",
        "event_time_start": NOW,
        "human_summary": f"incident-{label}",
    }


def _observation_payload(label: str | None = None) -> dict:
    label = label or uuid4().hex
    return {
        "observation_type": "event",
        "robot_id": f"robot-{label}",
        "observed_time": NOW,
        "human_summary": f"observation-{label}",
        "metrics": [{"metric_name": "temperature", "metric_value": 42.5, "unit": "C"}],
    }


CORE_RESOURCES = (
    ("evidence", "/api/v1/evidence-bundles", _evidence_payload, "evidence_bundle_id"),
    ("incident", "/api/v1/incidents", _incident_payload, "incident_id"),
    ("observation", "/api/v1/observations", _observation_payload, "observation_id"),
)


@pytest.mark.parametrize(("name", "path", "payload_factory", "id_key"), CORE_RESOURCES)
def test_core_record_create_allows_authenticated_actor_and_returns_content(
    module_h_env, actors, name, path, payload_factory, id_key
) -> None:
    client, _ = module_h_env
    payload = payload_factory(f"allow-{name}")
    response = client.post(path, headers=_auth(actors["owner_token"]), json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body[id_key]
    if name == "evidence":
        assert body["is_sealed"] is True
        assert body["human_summary"] == payload["human_summary"]
        assert body["items"][0]["evidence_id"] == payload["items"][0]["evidence_id"]
    else:
        assert body["robot_id"] == payload["robot_id"]
        assert body["human_summary"] == payload["human_summary"]


@pytest.mark.parametrize(("name", "path", "payload_factory", "id_key"), CORE_RESOURCES)
def test_core_record_create_rejects_anonymous(
    module_h_env, name, path, payload_factory, id_key
) -> None:
    client, _ = module_h_env
    client.headers.pop("Authorization", None)
    response = client.post(path, json=payload_factory(f"anon-{name}"))
    assert response.status_code == 401
    assert response.json()["message"] == "未登录，请先登录后重试"


@pytest.mark.parametrize(("name", "path", "payload_factory", "id_key"), CORE_RESOURCES)
def test_core_record_create_rejects_invalid_body(
    module_h_env, actors, name, path, payload_factory, id_key
) -> None:
    client, _ = module_h_env
    response = client.post(path, headers=_auth(actors["owner_token"]), json={})
    assert response.status_code == 422
    assert response.json()["error_type"] == "ValidationError"


@pytest.mark.parametrize(("name", "path", "payload_factory", "id_key"), CORE_RESOURCES)
def test_core_record_create_allows_student_current_behavior(
    module_h_env, actors, name, path, payload_factory, id_key
) -> None:
    """这是当前行为，疑似缺陷 H-AUTH-01：三类记录没有角色级写入限制，待模块 H 改造时处置。"""
    client, _ = module_h_env
    response = client.post(
        path,
        headers=_auth(actors["student_token"]),
        json=payload_factory(f"student-{name}"),
    )
    assert response.status_code == 201, response.text
    assert response.json()[id_key]


@pytest.mark.parametrize(("name", "path", "payload_factory", "id_key"), CORE_RESOURCES)
def test_core_record_list_and_detail_are_cross_user_visible_current_behavior(
    module_h_env, actors, name, path, payload_factory, id_key
) -> None:
    """这是当前行为，疑似缺陷 H-AUTH-02：列表和详情未按创建者过滤，待模块 H 改造时处置。学校边界未在本用例覆盖。"""
    client, _ = module_h_env
    created = client.post(
        path,
        headers=_auth(actors["owner_token"]),
        json=payload_factory(f"cross-read-{name}"),
    )
    assert created.status_code == 201, created.text
    record_id = created.json()[id_key]

    listing = client.get(path, headers=_auth(actors["other_token"]), params={"page": 1, "size": 100})
    assert listing.status_code == 200, listing.text
    list_body = listing.json()
    assert list_body["page"] == 1
    assert list_body["size"] == 100
    assert record_id in {item[id_key] for item in list_body["items"]}

    detail = client.get(f"{path}/{record_id}", headers=_auth(actors["other_token"]))
    assert detail.status_code == 200, detail.text
    assert detail.json()[id_key] == record_id


@pytest.mark.parametrize(("name", "path", "payload_factory", "id_key"), CORE_RESOURCES)
def test_core_record_detail_missing_returns_404(
    module_h_env, actors, name, path, payload_factory, id_key
) -> None:
    client, _ = module_h_env
    response = client.get(f"{path}/missing-{uuid4()}", headers=_auth(actors["owner_token"]))
    assert response.status_code == 404
    assert "not found" in response.json()["message"].lower()


@pytest.mark.parametrize(("name", "path", "payload_factory", "id_key"), CORE_RESOURCES)
def test_core_record_list_rejects_invalid_page(
    module_h_env, actors, name, path, payload_factory, id_key
) -> None:
    client, _ = module_h_env
    response = client.get(path, headers=_auth(actors["owner_token"]), params={"page": 0})
    assert response.status_code == 422


def _provider_payload(label: str | None = None) -> dict:
    label = label or uuid4().hex
    return {
        "provider_name": f"provider-{label}",
        "provider_type": "diagnosis",
        "endpoint_uri": f"https://example.invalid/{label}",
        "contact_name": "测试联系人",
        "contact_email": f"{label}@example.com",
    }


def _create_provider(client: TestClient, actors: dict, label: str | None = None) -> dict:
    response = client.post(
        "/api/v1/assessment-providers",
        headers=_auth(actors["admin_token"]),
        json=_provider_payload(label),
    )
    assert response.status_code == 201, response.text
    return response.json()


def _assessment_payload(provider_id: str, label: str | None = None) -> dict:
    label = label or uuid4().hex
    return {
        "provider_id": provider_id,
        "assessment_type": "diagnosis",
        "provider_assessment_id": f"external-{label}",
        "report_uri": f"memory://assessment/{label}",
        "report_hash": HASH,
        "report_hash_algo": "sha256",
        "report_format": "json",
        "report_time": NOW,
    }


def _create_assessment(client: TestClient, actors: dict, label: str | None = None) -> dict:
    provider = _create_provider(client, actors, f"assessment-{label or uuid4().hex}")
    response = client.post(
        "/api/v1/assessments",
        headers=_auth(actors["owner_token"]),
        json=_assessment_payload(provider["provider_id"], label),
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_assessment_provider_allows_admin_and_returns_content(module_h_env, actors) -> None:
    client, _ = module_h_env
    body = _create_provider(client, actors, "admin-allow")
    assert body["provider_name"] == "provider-admin-allow"
    assert body["provider_type"] == "diagnosis"
    assert body["status"] == "active"


def test_create_assessment_provider_rejects_teacher(module_h_env, actors) -> None:
    client, _ = module_h_env
    response = client.post(
        "/api/v1/assessment-providers",
        headers=_auth(actors["owner_token"]),
        json=_provider_payload("teacher-denied"),
    )
    assert response.status_code == 403
    assert response.json()["error_type"] == "WriteAccessDeniedError"


def test_create_assessment_provider_rejects_invalid_body(module_h_env, actors) -> None:
    client, _ = module_h_env
    response = client.post(
        "/api/v1/assessment-providers",
        headers=_auth(actors["admin_token"]),
        json={"provider_name": "missing-type"},
    )
    assert response.status_code == 422


def test_provider_list_and_detail_are_cross_user_visible_current_behavior(module_h_env, actors) -> None:
    """这是当前行为，疑似缺陷 H-AUTH-03：学生可读取机构列表、详情和联系方式，待模块 H 改造时处置。学校边界未在本用例覆盖。"""
    client, _ = module_h_env
    provider = _create_provider(client, actors, "cross-user-read")
    provider_id = provider["provider_id"]

    listing = client.get(
        "/api/v1/assessment-providers",
        headers=_auth(actors["student_token"]),
        params={"size": 100},
    )
    assert listing.status_code == 200
    assert provider_id in {item["provider_id"] for item in listing.json()["items"]}

    detail = client.get(
        f"/api/v1/assessment-providers/{provider_id}",
        headers=_auth(actors["student_token"]),
    )
    assert detail.status_code == 200
    assert detail.json()["provider_name"] == provider["provider_name"]


def test_get_assessment_provider_missing_returns_404(module_h_env, actors) -> None:
    client, _ = module_h_env
    response = client.get(
        f"/api/v1/assessment-providers/missing-{uuid4()}",
        headers=_auth(actors["owner_token"]),
    )
    assert response.status_code == 404


def test_update_assessment_provider_allows_admin_and_returns_content(module_h_env, actors) -> None:
    client, _ = module_h_env
    provider = _create_provider(client, actors, "patch-allow")
    response = client.patch(
        f"/api/v1/assessment-providers/{provider['provider_id']}",
        headers=_auth(actors["admin_token"]),
        json={"provider_name": "provider-updated", "status": "suspended"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["provider_name"] == "provider-updated"
    assert response.json()["status"] == "suspended"


def test_update_assessment_provider_rejects_teacher(module_h_env, actors) -> None:
    client, _ = module_h_env
    provider = _create_provider(client, actors, "patch-denied")
    response = client.patch(
        f"/api/v1/assessment-providers/{provider['provider_id']}",
        headers=_auth(actors["owner_token"]),
        json={"provider_name": "must-not-change"},
    )
    assert response.status_code == 403
    assert response.json()["error_type"] == "WriteAccessDeniedError"


def test_update_assessment_provider_missing_returns_404(module_h_env, actors) -> None:
    client, _ = module_h_env
    response = client.patch(
        f"/api/v1/assessment-providers/missing-{uuid4()}",
        headers=_auth(actors["admin_token"]),
        json={"provider_name": "missing"},
    )
    assert response.status_code == 404


def test_update_assessment_provider_rejects_invalid_status(module_h_env, actors) -> None:
    client, _ = module_h_env
    provider = _create_provider(client, actors, "patch-invalid")
    response = client.patch(
        f"/api/v1/assessment-providers/{provider['provider_id']}",
        headers=_auth(actors["admin_token"]),
        json={"status": "unknown"},
    )
    assert response.status_code == 422


def test_create_assessment_allows_teacher_and_returns_content(module_h_env, actors) -> None:
    client, _ = module_h_env
    body = _create_assessment(client, actors, "teacher-allow")
    assert body["assessment_type"] == "diagnosis"
    assert body["provider_assessment_id"] == "external-teacher-allow"
    assert body["status"] == "active"


def test_create_assessment_rejects_student(module_h_env, actors) -> None:
    client, _ = module_h_env
    provider = _create_provider(client, actors, "student-denied")
    response = client.post(
        "/api/v1/assessments",
        headers=_auth(actors["student_token"]),
        json=_assessment_payload(provider["provider_id"], "student-denied"),
    )
    assert response.status_code == 403
    assert response.json()["error_type"] == "WriteAccessDeniedError"


def test_create_assessment_missing_provider_returns_404(module_h_env, actors) -> None:
    client, _ = module_h_env
    response = client.post(
        "/api/v1/assessments",
        headers=_auth(actors["owner_token"]),
        json=_assessment_payload(f"missing-{uuid4()}", "missing-provider"),
    )
    assert response.status_code == 404
    assert "provider" in response.json()["message"].lower()


def test_create_assessment_rejects_invalid_body(module_h_env, actors) -> None:
    client, _ = module_h_env
    response = client.post(
        "/api/v1/assessments",
        headers=_auth(actors["owner_token"]),
        json={"provider_id": "only-one-field"},
    )
    assert response.status_code == 422


def test_create_assessment_accepts_missing_evidence_references_current_behavior(module_h_env, actors) -> None:
    """这是当前行为，疑似缺陷 H-EVID-01：不存在的证据引用仍可用于评估，待模块 H 改造时处置。"""
    client, _ = module_h_env
    provider = _create_provider(client, actors, "missing-references")
    payload = _assessment_payload(provider["provider_id"], "missing-references")
    payload["evidence_bundle_ids"] = [f"missing-{uuid4()}"]
    payload["incident_ids"] = [f"missing-{uuid4()}"]
    payload["observation_ids"] = [f"missing-{uuid4()}"]
    response = client.post(
        "/api/v1/assessments",
        headers=_auth(actors["owner_token"]),
        json=payload,
    )
    assert response.status_code == 201, response.text
    assert response.json()["evidence_bundle_ids"] == payload["evidence_bundle_ids"]


def test_assessment_list_detail_and_audit_are_cross_user_visible_current_behavior(
    module_h_env, actors
) -> None:
    """这是当前行为，疑似缺陷 H-AUTH-04：非创建者学生可读取评估及审计，待模块 H 改造时处置。学校边界未在本用例覆盖。"""
    client, _ = module_h_env
    assessment = _create_assessment(client, actors, "cross-user-read")
    assessment_id = assessment["assessment_id"]

    listing = client.get(
        "/api/v1/assessments",
        headers=_auth(actors["student_token"]),
        params={"size": 100},
    )
    assert listing.status_code == 200
    assert assessment_id in {item["assessment_id"] for item in listing.json()["items"]}

    detail = client.get(
        f"/api/v1/assessments/{assessment_id}",
        headers=_auth(actors["student_token"]),
    )
    assert detail.status_code == 200
    assert detail.json()["report_uri"] == assessment["report_uri"]

    audit = client.get(
        f"/api/v1/assessments/{assessment_id}/audit",
        headers=_auth(actors["student_token"]),
    )
    assert audit.status_code == 200
    assert audit.json()["assessment_id"] == assessment_id
    assert audit.json()["total"] == 1
    assert audit.json()["events"][0]["action"] == "submitted"


def test_get_assessment_missing_returns_404(module_h_env, actors) -> None:
    client, _ = module_h_env
    response = client.get(
        f"/api/v1/assessments/missing-{uuid4()}",
        headers=_auth(actors["owner_token"]),
    )
    assert response.status_code == 404


def test_get_assessment_audit_missing_returns_404(module_h_env, actors) -> None:
    client, _ = module_h_env
    response = client.get(
        f"/api/v1/assessments/missing-{uuid4()}/audit",
        headers=_auth(actors["owner_token"]),
    )
    assert response.status_code == 404


STATUS_CHANGE = {"reason_code": "operator_error", "reason_note": "模块 H 行为测试"}


def test_dispute_assessment_allows_owner_and_returns_content(module_h_env, actors) -> None:
    """这是当前行为，疑似缺陷 H-AUDIT-01：状态变更审计记为 system 而非真实操作者，待模块 H 改造时处置。"""
    client, _ = module_h_env
    assessment = _create_assessment(client, actors, "dispute-owner")
    assessment_id = assessment["assessment_id"]
    response = client.post(
        f"/api/v1/assessments/{assessment_id}/dispute",
        headers=_auth(actors["owner_token"]),
        json=STATUS_CHANGE,
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "disputed"

    audit = client.get(
        f"/api/v1/assessments/{assessment_id}/audit",
        headers=_auth(actors["owner_token"]),
    )
    event = audit.json()["events"][-1]
    assert event["action"] == "disputed"
    assert event["actor_type"] == "system"
    assert event["actor_id"] == "system"


def test_dispute_assessment_rejects_other_teacher(module_h_env, actors) -> None:
    client, _ = module_h_env
    assessment = _create_assessment(client, actors, "dispute-denied")
    response = client.post(
        f"/api/v1/assessments/{assessment['assessment_id']}/dispute",
        headers=_auth(actors["other_token"]),
        json=STATUS_CHANGE,
    )
    assert response.status_code == 403
    assert response.json()["error_type"] == "WriteAccessDeniedError"


def test_dispute_assessment_missing_returns_404(module_h_env, actors) -> None:
    client, _ = module_h_env
    response = client.post(
        f"/api/v1/assessments/missing-{uuid4()}/dispute",
        headers=_auth(actors["owner_token"]),
        json=STATUS_CHANGE,
    )
    assert response.status_code == 404


def test_dispute_assessment_rejects_invalid_reason(module_h_env, actors) -> None:
    client, _ = module_h_env
    assessment = _create_assessment(client, actors, "dispute-invalid")
    response = client.post(
        f"/api/v1/assessments/{assessment['assessment_id']}/dispute",
        headers=_auth(actors["owner_token"]),
        json={"reason_code": "not-a-reason"},
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("action", "expected_status"),
    (("revoke", "revoked"), ("reinstate", "active")),
)
def test_admin_status_change_allows_and_returns_content(
    module_h_env, actors, action, expected_status
) -> None:
    client, _ = module_h_env
    assessment = _create_assessment(client, actors, f"{action}-allow")
    response = client.post(
        f"/api/v1/assessments/{assessment['assessment_id']}/{action}",
        headers=_auth(actors["admin_token"]),
        json=STATUS_CHANGE,
    )
    assert response.status_code == 200, response.text
    assert response.json()["assessment_id"] == assessment["assessment_id"]
    assert response.json()["status"] == expected_status


@pytest.mark.parametrize("action", ("revoke", "reinstate"))
def test_admin_status_change_rejects_teacher(module_h_env, actors, action) -> None:
    client, _ = module_h_env
    assessment = _create_assessment(client, actors, f"{action}-denied")
    response = client.post(
        f"/api/v1/assessments/{assessment['assessment_id']}/{action}",
        headers=_auth(actors["owner_token"]),
        json=STATUS_CHANGE,
    )
    assert response.status_code == 403
    assert response.json()["error_type"] == "WriteAccessDeniedError"


@pytest.mark.parametrize("action", ("revoke", "reinstate"))
def test_admin_status_change_missing_returns_404(module_h_env, actors, action) -> None:
    client, _ = module_h_env
    response = client.post(
        f"/api/v1/assessments/missing-{uuid4()}/{action}",
        headers=_auth(actors["admin_token"]),
        json=STATUS_CHANGE,
    )
    assert response.status_code == 404


@pytest.mark.parametrize("action", ("revoke", "reinstate"))
def test_admin_status_change_rejects_invalid_reason(module_h_env, actors, action) -> None:
    client, _ = module_h_env
    assessment = _create_assessment(client, actors, f"{action}-invalid")
    response = client.post(
        f"/api/v1/assessments/{assessment['assessment_id']}/{action}",
        headers=_auth(actors["admin_token"]),
        json={"reason_code": "not-a-reason"},
    )
    assert response.status_code == 422


async def _seed_attempt_with_timeline(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    teacher_id: int,
    student_id: int,
) -> int:
    async with session_factory() as session:
        service = TeachingService(session)
        teaching_class = await service.create_class(
            name=f"模块 H 班级 {uuid4().hex[:8]}", teacher_id=teacher_id
        )
        assignment = await service.create_assignment(
            class_id=teaching_class.id, title="模块 H 作业"
        )
        await service.enroll_student(class_id=teaching_class.id, student_id=student_id)
        attempt = await service.create_attempt(
            assignment_id=assignment.id, student_id=student_id, task_id=None
        )
        timeline = MultimodalTimeline(
            scope_type="attempt",
            scope_id=str(attempt.id),
            trace_id=f"module-h-{attempt.id}",
            created_by_user_id=str(teacher_id),
        )
        session.add(timeline)
        await session.flush()
        session.add(
            TimelineSegment(
                timeline_id=timeline.id,
                segment_type="event",
                ref_id=f"event-{uuid4().hex}",
                start_ts_ms=1000,
                end_ts_ms=1500,
                payload={"snippet": "真实 HTTP 行为测试事件"},
            )
        )
        await session.commit()
        return attempt.id


def test_create_evidence_card_allows_class_teacher_and_returns_content(module_h_env, actors) -> None:
    client, session_factory = module_h_env
    attempt_id = asyncio.run(
        _seed_attempt_with_timeline(
            session_factory,
            teacher_id=actors["owner_id"],
            student_id=actors["student_id"],
        )
    )
    response = client.post(
        "/api/v1/evidence_cards",
        headers=_auth(actors["owner_token"]),
        json={"attemptId": attempt_id, "cardType": "failure_point"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["attemptId"] == attempt_id
    assert body["cardType"] == "failure_point"
    assert body["title"] == "failure_point 证据卡片"
    assert body["references"][0]["snippet"] == "真实 HTTP 行为测试事件"


def test_create_evidence_card_rejects_other_teacher(module_h_env, actors) -> None:
    client, session_factory = module_h_env
    attempt_id = asyncio.run(
        _seed_attempt_with_timeline(
            session_factory,
            teacher_id=actors["owner_id"],
            student_id=actors["student_id"],
        )
    )
    response = client.post(
        "/api/v1/evidence_cards",
        headers=_auth(actors["other_token"]),
        json={"attemptId": attempt_id, "cardType": "failure_point"},
    )
    assert response.status_code == 403
    assert response.json()["details"]["code"] == "WRITE_ACCESS_DENIED"


def test_create_evidence_card_missing_attempt_returns_404(module_h_env, actors) -> None:
    client, _ = module_h_env
    response = client.post(
        "/api/v1/evidence_cards",
        headers=_auth(actors["owner_token"]),
        json={"attemptId": 99999999, "cardType": "failure_point"},
    )
    assert response.status_code == 404


def test_create_evidence_card_rejects_invalid_body(module_h_env, actors) -> None:
    client, _ = module_h_env
    response = client.post(
        "/api/v1/evidence_cards",
        headers=_auth(actors["owner_token"]),
        json={"attemptId": "not-an-integer", "cardType": "x" * 65},
    )
    assert response.status_code == 422


async def _seed_attempt_evidence(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    teacher_id: int,
    student_id: int,
) -> tuple[int, str]:
    async with session_factory() as session:
        service = TeachingService(session)
        teaching_class = await service.create_class(
            name=f"模块 H 证据班 {uuid4().hex[:8]}", teacher_id=teacher_id
        )
        assignment = await service.create_assignment(
            class_id=teaching_class.id, title="模块 H 证据作业"
        )
        await service.enroll_student(class_id=teaching_class.id, student_id=student_id)
        attempt = await service.create_attempt(
            assignment_id=assignment.id, student_id=student_id, task_id=None
        )
        bundle_id = str(uuid4())
        session.add(
            EvidenceBundle(
                id=bundle_id,
                bundle_type="event_log",
                bundle_hash=HASH,
                bundle_hash_algo="sha256",
                observed_time_start=datetime.now(timezone.utc),
                ingest_time=datetime.now(timezone.utc),
                is_sealed=True,
                sealed_at=datetime.now(timezone.utc),
                machine_tags={"source": "module-h-http-test"},
                created_by_user_id=student_id,
                school_name=E2E_SCHOOL_NAME,
            )
        )
        await session.flush()
        session.add(
            EvidenceLink(
                bundle_id=bundle_id,
                attempt_id=attempt.id,
                task_id=None,
                student_id=student_id,
                class_id=teaching_class.id,
            )
        )
        await session.commit()
        return attempt.id, bundle_id


def test_attempt_evidence_is_cross_user_visible_current_behavior(module_h_env, actors) -> None:
    """这是当前行为，疑似缺陷 H-AUTH-05：他人可读取学生尝试证据，待模块 H 改造时处置。"""
    client, session_factory = module_h_env
    attempt_id, bundle_id = asyncio.run(
        _seed_attempt_evidence(
            session_factory,
            teacher_id=actors["owner_id"],
            student_id=actors["student_id"],
        )
    )
    response = client.get(
        f"/api/v1/attempts/{attempt_id}/evidence",
        headers=_auth(actors["other_token"]),
    )
    assert response.status_code == 200, response.text
    assert response.json() == {
        "bundleId": bundle_id,
        "taskId": None,
        "attemptId": attempt_id,
        "summary": {"source": "module-h-http-test"},
    }


def test_attempt_evidence_missing_returns_404(module_h_env, actors) -> None:
    client, _ = module_h_env
    response = client.get(
        "/api/v1/attempts/99999999/evidence",
        headers=_auth(actors["owner_token"]),
    )
    assert response.status_code == 404


def test_agent_evidence_status_unknown_step_returns_current_content(module_h_env, actors) -> None:
    client, _ = module_h_env
    step_id = f"unknown-{uuid4()}"
    response = client.get(
        f"/api/v1/agent/evidence/status/{step_id}",
        headers=_auth(actors["owner_token"]),
    )
    assert response.status_code == 200
    assert response.json() == {
        "step_id": step_id,
        "required": [],
        "collected": [],
        "missing": [],
        "complete": True,
    }


def test_agent_evidence_requirements_known_action_returns_content(module_h_env, actors) -> None:
    client, _ = module_h_env
    response = client.get(
        "/api/v1/agent/evidence/requirements/inspect",
        headers=_auth(actors["owner_token"]),
    )
    assert response.status_code == 200
    assert response.json()["action_type"] == "inspect"
    assert {item["evidence_type"] for item in response.json()["requirements"]} == {
        "screenshot",
        "sensor_reading",
    }


def test_agent_evidence_requirements_unknown_action_returns_empty(module_h_env, actors) -> None:
    client, _ = module_h_env
    action = f"unknown-{uuid4()}"
    response = client.get(
        f"/api/v1/agent/evidence/requirements/{action}",
        headers=_auth(actors["owner_token"]),
    )
    assert response.status_code == 200
    assert response.json() == {"action_type": action, "requirements": []}


def test_agent_can_proceed_unknown_step_returns_allowed(module_h_env, actors) -> None:
    client, _ = module_h_env
    step_id = f"unknown-{uuid4()}"
    response = client.get(
        f"/api/v1/agent/evidence/can-proceed/{step_id}",
        headers=_auth(actors["owner_token"]),
    )
    assert response.status_code == 200
    assert response.json() == {
        "allowed": True,
        "reason": "All required evidence collected",
    }


def test_agent_collect_is_globally_visible_and_ignores_evidence_type_current_behavior(
    module_h_env, actors
) -> None:
    """这是当前行为，疑似缺陷 H-AGENT-01：证据状态是跨用户单例且记录 ID 而非类型，待模块 H 改造时处置。"""
    client, _ = module_h_env
    step_id = f"shared-{uuid4()}"
    evidence_id = f"evidence-id-{uuid4()}"
    collected = client.post(
        "/api/v1/agent/evidence/collect",
        headers=_auth(actors["owner_token"]),
        json={
            "step_id": step_id,
            "evidence_id": evidence_id,
            "evidence_type": "screenshot",
        },
    )
    assert collected.status_code == 200
    assert collected.json() == {"status": "collected"}

    status = client.get(
        f"/api/v1/agent/evidence/status/{step_id}",
        headers=_auth(actors["other_token"]),
    )
    assert status.status_code == 200
    assert status.json()["collected"] == [evidence_id]
    assert "screenshot" not in status.json()["collected"]


def test_agent_collect_rejects_actor_without_execute_permission(module_h_env, actors) -> None:
    client, _ = module_h_env
    response = client.post(
        "/api/v1/agent/evidence/collect",
        headers=_auth(actors["other_token"]),
        json={"step_id": "denied", "evidence_id": "denied", "evidence_type": "log"},
    )
    assert response.status_code == 403
    assert response.json()["error_type"] == "PermissionDeniedError"


def test_agent_collect_rejects_invalid_body(module_h_env, actors) -> None:
    client, _ = module_h_env
    response = client.post(
        "/api/v1/agent/evidence/collect",
        headers=_auth(actors["owner_token"]),
        json={"step_id": "missing-other-fields"},
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "path",
    (
        "/api/v1/agent/evidence/status/denied",
        "/api/v1/agent/evidence/can-proceed/denied",
        "/api/v1/agent/evidence/requirements/inspect",
    ),
)
def test_agent_evidence_reads_reject_actor_without_read_permission(
    module_h_env, actors, path
) -> None:
    client, _ = module_h_env
    response = client.get(path, headers=_auth(actors["student_token"]))
    assert response.status_code == 403
    assert response.json()["error_type"] == "PermissionDeniedError"


async def _seed_workbench_session(
    session_factory: async_sessionmaker[AsyncSession], *, user_id: int
) -> str:
    async with session_factory() as session:
        return await SessionService(session).create_session(
            user_id=user_id,
            project_id=f"project-{uuid4()}",
            project_snapshot={
                "steps": [
                    {
                        "id": "step-evidence",
                        "title": "采集证据",
                        "instruction": "上传现场图片",
                        "evidence_hint": "工位全景",
                        "tools": [],
                    }
                ]
            },
        )


def _redirect_workbench_storage(monkeypatch, target: Path) -> None:
    from app.services.training.workbench_execution_service import TrainingWorkbenchExecutionService

    original_init = TrainingWorkbenchExecutionService.__init__

    def _init(self, db):
        original_init(self, db)
        self.storage_root = target

    monkeypatch.setattr(TrainingWorkbenchExecutionService, "__init__", _init)


def test_workbench_evidence_upload_allows_owner_and_returns_content(
    module_h_env, actors, monkeypatch, tmp_path
) -> None:
    """这是当前行为，疑似缺陷 H-EVID-02：上传生成的证据包未记录创建者和学校，待模块 H 改造时处置。"""
    client, session_factory = module_h_env
    _redirect_workbench_storage(monkeypatch, tmp_path)
    session_id = asyncio.run(
        _seed_workbench_session(session_factory, user_id=actors["owner_id"])
    )
    response = client.post(
        "/api/v1/training/workbench/evidence",
        headers=_auth(actors["owner_token"]),
        data={"session_id": session_id, "step_id": "step-evidence", "note": "工位已确认"},
        files={"file": ("station.jpg", io.BytesIO(b"representative-image"), "image/jpeg")},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["evidence_bundle_id"]
    assert body["filename"] == "station.jpg"
    assert body["human_summary"] == "工位已确认"
    assert body["content_uri"].startswith(f"local://training-evidence/{session_id}/")

    async def _load_bundle():
        async with session_factory() as session:
            return await session.get(EvidenceBundle, body["evidence_bundle_id"])

    bundle = asyncio.run(_load_bundle())
    assert bundle.created_by_user_id is None
    assert bundle.school_name is None
    assert list(tmp_path.rglob("station.jpg")) == []  # 实际文件名带随机前缀
    assert len(list(tmp_path.rglob("*-station.jpg"))) == 1


def test_workbench_evidence_upload_rejects_other_user(module_h_env, actors) -> None:
    client, session_factory = module_h_env
    session_id = asyncio.run(
        _seed_workbench_session(session_factory, user_id=actors["owner_id"])
    )
    response = client.post(
        "/api/v1/training/workbench/evidence",
        headers=_auth(actors["other_token"]),
        data={"session_id": session_id, "step_id": "step-evidence"},
        files={"file": ("station.jpg", io.BytesIO(b"image"), "image/jpeg")},
    )
    assert response.status_code == 403
    assert response.json()["message"] == "Session access denied"


def test_workbench_evidence_upload_missing_session_returns_404(module_h_env, actors) -> None:
    client, _ = module_h_env
    response = client.post(
        "/api/v1/training/workbench/evidence",
        headers=_auth(actors["owner_token"]),
        data={"session_id": f"missing-{uuid4()}", "step_id": "step-evidence"},
        files={"file": ("station.jpg", io.BytesIO(b"image"), "image/jpeg")},
    )
    assert response.status_code == 404
    assert response.json()["message"] == "Session not found"


def test_workbench_evidence_upload_rejects_missing_file(module_h_env, actors) -> None:
    client, session_factory = module_h_env
    session_id = asyncio.run(
        _seed_workbench_session(session_factory, user_id=actors["owner_id"])
    )
    response = client.post(
        "/api/v1/training/workbench/evidence",
        headers=_auth(actors["owner_token"]),
        data={"session_id": session_id, "step_id": "step-evidence"},
    )
    assert response.status_code == 422
