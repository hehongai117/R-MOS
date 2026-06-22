"""
Observation service for CRUD operations.
"""
from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.observation import Observation
from app.schemas.observation import (
    ObservationCreate,
    ObservationResponse,
    ObservationListItem,
    ObservationListResponse,
)

def _to_naive(value: datetime | None) -> datetime | None:
    return value


class ObservationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_observations(self, page: int, size: int) -> ObservationListResponse:
        count_query = select(func.count()).select_from(Observation)
        total = (await self.db.execute(count_query)).scalar() or 0

        query = select(Observation).offset((page - 1) * size).limit(size)
        rows = (await self.db.execute(query)).scalars().all()

        items = [
            ObservationListItem(
                observation_id=row.id,
                observation_type=row.observation_type,
                robot_id=row.robot_id,
                observed_time=row.observed_time,
                ingest_time=row.ingest_time,
            )
            for row in rows
        ]
        pages = (total + size - 1) // size

        return ObservationListResponse(items=items, total=total, page=page, size=size, pages=pages)

    async def create_observation(self, request: ObservationCreate) -> ObservationResponse:
        ingest_time = datetime.now(timezone.utc)
        observation = Observation(
            id=str(uuid.uuid4()),
            observation_type=request.observation_type.value,
            robot_id=request.robot_id,
            task_id=request.task_id,
            observed_time=_to_naive(request.observed_time),
            event_time=_to_naive(request.event_time),
            ingest_time=ingest_time,
            human_summary=request.human_summary,
            machine_code=request.machine_code,
            metrics=[metric.model_dump() for metric in request.metrics] if request.metrics else None,
            payload_uri=request.payload_uri,
            payload_hash=request.payload_hash,
        )
        self.db.add(observation)
        await self.db.commit()
        await self.db.refresh(observation)

        return ObservationResponse(
            observation_id=observation.id,
            observation_type=observation.observation_type,
            robot_id=observation.robot_id,
            task_id=observation.task_id,
            observed_time=observation.observed_time,
            event_time=observation.event_time,
            ingest_time=observation.ingest_time,
            human_summary=observation.human_summary,
            machine_code=observation.machine_code,
            metrics=observation.metrics,
            payload_uri=observation.payload_uri,
            payload_hash=observation.payload_hash,
        )

    async def get_observation(self, observation_id: str) -> ObservationResponse | None:
        row = await self.db.get(Observation, observation_id)
        if not row:
            return None

        return ObservationResponse(
            observation_id=row.id,
            observation_type=row.observation_type,
            robot_id=row.robot_id,
            task_id=row.task_id,
            observed_time=row.observed_time,
            event_time=row.event_time,
            ingest_time=row.ingest_time,
            human_summary=row.human_summary,
            machine_code=row.machine_code,
            metrics=row.metrics,
            payload_uri=row.payload_uri,
            payload_hash=row.payload_hash,
        )
