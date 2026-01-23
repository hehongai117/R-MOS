"""
Assessment provider and external assessment services.
"""
from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import (
    AssessmentProvider,
    ExternalAssessment,
    AssessmentAuditEvent as AssessmentAuditEventModel,
)
from app.schemas.assessment import (
    AssessmentProviderCreate,
    AssessmentProviderUpdate,
    AssessmentProviderResponse,
    AssessmentProviderListResponse,
    ExternalAssessmentCreate,
    ExternalAssessmentResponse,
    ExternalAssessmentListItem,
    ExternalAssessmentListResponse,
    AssessmentAuditTrail,
    AssessmentAuditEvent,
    AssessmentStatus,
    AuditAction,
    ActorType,
    AssessmentReasonCodeWithNone,
    AssessmentReasonCode,
    AssessmentStatusChangeRequest,
)


def _to_naive(value: datetime | None) -> datetime | None:
    if value and value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value

class AssessmentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_providers(self, page: int, size: int) -> AssessmentProviderListResponse:
        count_query = select(func.count()).select_from(AssessmentProvider)
        total = (await self.db.execute(count_query)).scalar() or 0

        query = select(AssessmentProvider).offset((page - 1) * size).limit(size)
        rows = (await self.db.execute(query)).scalars().all()
        pages = (total + size - 1) // size

        items = [
            AssessmentProviderResponse(
                provider_id=row.id,
                provider_name=row.provider_name,
                provider_type=row.provider_type,
                status=row.status,
                endpoint_uri=row.endpoint_uri,
                contact_name=row.contact_name,
                contact_email=row.contact_email,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

        return AssessmentProviderListResponse(items=items, total=total, page=page, size=size, pages=pages)

    async def create_provider(self, request: AssessmentProviderCreate) -> AssessmentProviderResponse:
        now = datetime.utcnow()
        provider = AssessmentProvider(
            id=str(uuid.uuid4()),
            provider_name=request.provider_name,
            provider_type=request.provider_type.value,
            status="active",
            endpoint_uri=request.endpoint_uri,
            contact_name=request.contact_name,
            contact_email=request.contact_email,
            created_at=now,
            updated_at=now,
        )
        self.db.add(provider)
        await self.db.commit()
        await self.db.refresh(provider)

        return AssessmentProviderResponse(
            provider_id=provider.id,
            provider_name=provider.provider_name,
            provider_type=provider.provider_type,
            status=provider.status,
            endpoint_uri=provider.endpoint_uri,
            contact_name=provider.contact_name,
            contact_email=provider.contact_email,
            created_at=provider.created_at,
            updated_at=provider.updated_at,
        )

    async def get_provider(self, provider_id: str) -> AssessmentProviderResponse | None:
        row = await self.db.get(AssessmentProvider, provider_id)
        if not row:
            return None

        return AssessmentProviderResponse(
            provider_id=row.id,
            provider_name=row.provider_name,
            provider_type=row.provider_type,
            status=row.status,
            endpoint_uri=row.endpoint_uri,
            contact_name=row.contact_name,
            contact_email=row.contact_email,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def update_provider(
        self,
        provider_id: str,
        request: AssessmentProviderUpdate,
    ) -> AssessmentProviderResponse | None:
        provider = await self.db.get(AssessmentProvider, provider_id)
        if not provider:
            return None

        if request.provider_name is not None:
            provider.provider_name = request.provider_name
        if request.endpoint_uri is not None:
            provider.endpoint_uri = request.endpoint_uri
        if request.contact_name is not None:
            provider.contact_name = request.contact_name
        if request.contact_email is not None:
            provider.contact_email = request.contact_email
        if request.status is not None:
            provider.status = request.status.value
        provider.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(provider)

        return AssessmentProviderResponse(
            provider_id=provider.id,
            provider_name=provider.provider_name,
            provider_type=provider.provider_type,
            status=provider.status,
            endpoint_uri=provider.endpoint_uri,
            contact_name=provider.contact_name,
            contact_email=provider.contact_email,
            created_at=provider.created_at,
            updated_at=provider.updated_at,
        )

    async def list_assessments(self, page: int, size: int) -> ExternalAssessmentListResponse:
        count_query = select(func.count()).select_from(ExternalAssessment)
        total = (await self.db.execute(count_query)).scalar() or 0

        query = select(ExternalAssessment).offset((page - 1) * size).limit(size)
        rows = (await self.db.execute(query)).scalars().all()
        pages = (total + size - 1) // size

        items = [
            ExternalAssessmentListItem(
                assessment_id=row.id,
                provider_id=row.provider_id,
                assessment_type=row.assessment_type,
                status=row.status,
                report_time=row.report_time,
                ingest_time=row.ingest_time,
            )
            for row in rows
        ]

        return ExternalAssessmentListResponse(items=items, total=total, page=page, size=size, pages=pages)

    async def create_assessment(self, request: ExternalAssessmentCreate) -> ExternalAssessmentResponse | None:
        provider = await self.db.get(AssessmentProvider, request.provider_id)
        if not provider:
            return None

        now = datetime.utcnow()
        assessment = ExternalAssessment(
            id=str(uuid.uuid4()),
            provider_id=request.provider_id,
            provider_type=provider.provider_type,
            assessment_type=request.assessment_type.value,
            provider_assessment_id=request.provider_assessment_id,
            report_uri=request.report_uri,
            report_hash=request.report_hash,
            report_hash_algo=request.report_hash_algo.value,
            report_format=request.report_format.value,
            report_time=_to_naive(request.report_time),
            ingest_time=now,
            status=AssessmentStatus.ACTIVE.value,
            status_updated_at=now,
            evidence_bundle_ids=request.evidence_bundle_ids,
            incident_ids=request.incident_ids,
            observation_ids=request.observation_ids,
        )
        self.db.add(assessment)

        await self._add_audit_event(
            assessment_id=assessment.id,
            action=AuditAction.SUBMITTED,
            actor_type=ActorType.SYSTEM,
            actor_id="system",
            reason_code=AssessmentReasonCodeWithNone.NONE,
            reason_note=None,
        )

        await self.db.commit()
        await self.db.refresh(assessment)

        return ExternalAssessmentResponse(
            assessment_id=assessment.id,
            provider_id=assessment.provider_id,
            provider_type=assessment.provider_type,
            assessment_type=assessment.assessment_type,
            provider_assessment_id=assessment.provider_assessment_id,
            report_uri=assessment.report_uri,
            report_hash=assessment.report_hash,
            report_hash_algo=assessment.report_hash_algo,
            report_format=assessment.report_format,
            report_time=assessment.report_time,
            ingest_time=assessment.ingest_time,
            status=assessment.status,
            status_updated_at=assessment.status_updated_at,
            evidence_bundle_ids=assessment.evidence_bundle_ids,
            incident_ids=assessment.incident_ids,
            observation_ids=assessment.observation_ids,
        )

    async def get_assessment(self, assessment_id: str) -> ExternalAssessmentResponse | None:
        row = await self.db.get(ExternalAssessment, assessment_id)
        if not row:
            return None

        return ExternalAssessmentResponse(
            assessment_id=row.id,
            provider_id=row.provider_id,
            provider_type=row.provider_type,
            assessment_type=row.assessment_type,
            provider_assessment_id=row.provider_assessment_id,
            report_uri=row.report_uri,
            report_hash=row.report_hash,
            report_hash_algo=row.report_hash_algo,
            report_format=row.report_format,
            report_time=row.report_time,
            ingest_time=row.ingest_time,
            status=row.status,
            status_updated_at=row.status_updated_at,
            evidence_bundle_ids=row.evidence_bundle_ids,
            incident_ids=row.incident_ids,
            observation_ids=row.observation_ids,
        )

    async def change_assessment_status(
        self,
        assessment_id: str,
        new_status: AssessmentStatus,
        action: AuditAction,
        request: AssessmentStatusChangeRequest,
        actor_type: ActorType = ActorType.SYSTEM,
        actor_id: str = "system",
    ) -> ExternalAssessmentResponse | None:
        assessment = await self.db.get(ExternalAssessment, assessment_id)
        if not assessment:
            return None

        now = datetime.utcnow()
        assessment.status = new_status.value
        assessment.status_updated_at = now

        await self._add_audit_event(
            assessment_id=assessment.id,
            action=action,
            actor_type=actor_type,
            actor_id=actor_id,
            reason_code=request.reason_code,
            reason_note=request.reason_note,
        )

        await self.db.commit()
        await self.db.refresh(assessment)

        return ExternalAssessmentResponse(
            assessment_id=assessment.id,
            provider_id=assessment.provider_id,
            provider_type=assessment.provider_type,
            assessment_type=assessment.assessment_type,
            provider_assessment_id=assessment.provider_assessment_id,
            report_uri=assessment.report_uri,
            report_hash=assessment.report_hash,
            report_hash_algo=assessment.report_hash_algo,
            report_format=assessment.report_format,
            report_time=assessment.report_time,
            ingest_time=assessment.ingest_time,
            status=assessment.status,
            status_updated_at=assessment.status_updated_at,
            evidence_bundle_ids=assessment.evidence_bundle_ids,
            incident_ids=assessment.incident_ids,
            observation_ids=assessment.observation_ids,
        )

    async def get_audit_trail(self, assessment_id: str) -> AssessmentAuditTrail | None:
        assessment = await self.db.get(ExternalAssessment, assessment_id)
        if not assessment:
            return None

        query = select(AssessmentAuditEventModel).where(
            AssessmentAuditEventModel.assessment_id == assessment_id
        ).order_by(AssessmentAuditEventModel.event_time)
        rows = (await self.db.execute(query)).scalars().all()

        events = [
            AssessmentAuditEvent(
                audit_id=row.id,
                assessment_id=row.assessment_id,
                action=row.action,
                actor_type=row.actor_type,
                actor_id=row.actor_id,
                reason_code=row.reason_code,
                reason_note=row.reason_note,
                event_time=row.event_time,
                ingest_time=row.ingest_time,
                trace_id=row.trace_id,
            )
            for row in rows
        ]

        return AssessmentAuditTrail(
            assessment_id=assessment_id,
            events=events,
            total=len(events),
        )

    async def _add_audit_event(
        self,
        assessment_id: str,
        action: AuditAction,
        actor_type: ActorType,
        actor_id: str,
        reason_code: AssessmentReasonCodeWithNone | AssessmentReasonCode,
        reason_note: str | None,
    ) -> None:
        event = AssessmentAuditEventModel(
            id=str(uuid.uuid4()),
            assessment_id=assessment_id,
            action=action.value,
            actor_type=actor_type.value,
            actor_id=actor_id,
            reason_code=reason_code.value if hasattr(reason_code, "value") else str(reason_code),
            reason_note=reason_note,
            event_time=datetime.utcnow(),
            ingest_time=datetime.utcnow(),
            trace_id=str(uuid.uuid4()),
        )
        self.db.add(event)
