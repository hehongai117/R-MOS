"""
Incident service for CRUD operations.
"""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import uuid

from app.models.incident import Incident
from app.schemas.incident import (
    IncidentCreate,
    IncidentResponse,
    IncidentListItem,
    IncidentListResponse,
    IncidentStatus,
)


def _to_naive(value: datetime | None) -> datetime | None:
    return value


class IncidentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_incidents(self, page: int, size: int) -> IncidentListResponse:
        count_query = select(func.count()).select_from(Incident)
        total = (await self.db.execute(count_query)).scalar() or 0

        query = select(Incident).offset((page - 1) * size).limit(size)
        rows = (await self.db.execute(query)).scalars().all()

        items = [
            IncidentListItem(
                incident_id=row.id,
                robot_id=row.robot_id,
                incident_type=row.incident_type,
                incident_level=row.incident_level,
                status=row.status,
                event_time_start=row.event_time_start,
                ingest_time=row.ingest_time,
            )
            for row in rows
        ]
        pages = (total + size - 1) // size

        return IncidentListResponse(items=items, total=total, page=page, size=size, pages=pages)

    async def create_incident(self, request: IncidentCreate) -> IncidentResponse:
        incident = Incident(
            id=str(uuid.uuid4()),
            robot_id=request.robot_id,
            task_id=request.task_id,
            incident_type=request.incident_type,
            incident_level=request.incident_level,
            status=(request.status or IncidentStatus.OPEN).value,
            event_time_start=_to_naive(request.event_time_start),
            event_time_end=_to_naive(request.event_time_end),
            human_summary=request.human_summary,
            machine_tags=request.machine_tags,
            related_observation_ids=request.related_observation_ids,
            related_evidence_bundle_ids=request.related_evidence_bundle_ids,
        )
        self.db.add(incident)
        await self.db.commit()
        await self.db.refresh(incident)

        return IncidentResponse(
            incident_id=incident.id,
            robot_id=incident.robot_id,
            task_id=incident.task_id,
            incident_type=incident.incident_type,
            incident_level=incident.incident_level,
            status=incident.status,
            event_time_start=incident.event_time_start,
            event_time_end=incident.event_time_end,
            ingest_time=incident.ingest_time,
            human_summary=incident.human_summary,
            machine_tags=incident.machine_tags,
            related_observation_ids=incident.related_observation_ids,
            related_evidence_bundle_ids=incident.related_evidence_bundle_ids,
        )

    async def get_incident(self, incident_id: str) -> IncidentResponse | None:
        row = await self.db.get(Incident, incident_id)
        if not row:
            return None

        return IncidentResponse(
            incident_id=row.id,
            robot_id=row.robot_id,
            task_id=row.task_id,
            incident_type=row.incident_type,
            incident_level=row.incident_level,
            status=row.status,
            event_time_start=row.event_time_start,
            event_time_end=row.event_time_end,
            ingest_time=row.ingest_time,
            human_summary=row.human_summary,
            machine_tags=row.machine_tags,
            related_observation_ids=row.related_observation_ids,
            related_evidence_bundle_ids=row.related_evidence_bundle_ids,
        )
