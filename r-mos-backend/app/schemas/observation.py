"""
Observation schemas for raw facts and metrics.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ObservationType(str, Enum):
    TELEMETRY = "telemetry"
    EVENT = "event"
    SOP_STEP = "sop_step"
    OPERATOR_NOTE = "operator_note"
    MEDIA = "media"


class ObservationMetric(BaseModel):
    metric_name: str = Field(..., description="Metric name identifier.")
    metric_value: float = Field(..., description="Metric value.")
    unit: Optional[str] = Field(None, description="Metric unit.")


class ObservationCreate(BaseModel):
    """Create an observation record."""

    observation_type: ObservationType = Field(..., description="Observation classification.")
    robot_id: str = Field(..., description="Robot identifier associated with the observation.")
    task_id: Optional[int] = Field(None, description="Task identifier associated with the observation.")
    observed_time: datetime = Field(..., description="observed_time when data was captured.")
    event_time: Optional[datetime] = Field(None, description="event_time when a discrete event occurred.")
    human_summary: Optional[str] = Field(None, description="Human-readable summary (non-conclusionary).")
    machine_code: Optional[str] = Field(None, description="Machine-readable event or measurement code.")
    metrics: Optional[List[ObservationMetric]] = Field(None, description="Metric samples.")
    payload_uri: Optional[str] = Field(None, description="URI to raw observation payload.")
    payload_hash: Optional[str] = Field(None, description="SHA-256 hash of raw payload.")


class ObservationResponse(ObservationCreate):
    """Observation record returned by the API."""

    observation_id: str = Field(..., description="Observation identifier.")
    ingest_time: datetime = Field(..., description="ingest_time when observation was stored.")

    class Config:
        from_attributes = True


class ObservationListItem(BaseModel):
    """List item for observations."""

    observation_id: str = Field(..., description="Observation identifier.")
    observation_type: ObservationType = Field(..., description="Observation classification.")
    robot_id: str = Field(..., description="Robot identifier.")
    observed_time: datetime = Field(..., description="observed_time when data was captured.")
    ingest_time: datetime = Field(..., description="ingest_time when observation was stored.")


class ObservationListResponse(BaseModel):
    """Paginated list of observations."""

    items: List[ObservationListItem]
    total: int
    page: int
    size: int
    pages: int
