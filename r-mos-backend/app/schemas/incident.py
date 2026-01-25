"""
Incident schemas for observed incidents.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class IncidentType(str, Enum):
    OPERATIONAL = "operational"
    SAFETY = "safety"
    MAINTENANCE = "maintenance"
    CONNECTIVITY = "connectivity"
    ENVIRONMENTAL = "environmental"
    UNKNOWN = "unknown"


class IncidentLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class IncidentStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    ARCHIVED = "archived"


class IncidentCreate(BaseModel):
    """Create an incident record."""

    robot_id: str = Field(..., description="Robot identifier associated with the incident.")
    task_id: Optional[int] = Field(None, description="Task identifier associated with the incident.")
    incident_type: IncidentType = Field(..., description="Observed incident category (non-causal).")
    incident_level: IncidentLevel = Field(..., description="Operational severity level.")
    status: Optional[IncidentStatus] = Field(None, description="Incident lifecycle status.")
    event_time_start: datetime = Field(..., description="event_time when the incident window started.")
    event_time_end: Optional[datetime] = Field(None, description="event_time when the incident window ended.")
    human_summary: Optional[str] = Field(None, description="Human-readable summary (non-conclusionary).")
    machine_tags: Optional[List[str]] = Field(None, description="Machine-readable tags for indexing.")
    related_observation_ids: Optional[List[str]] = Field(None, description="Related observation identifiers.")
    related_evidence_bundle_ids: Optional[List[str]] = Field(None, description="Related evidence bundle identifiers.")


class IncidentResponse(IncidentCreate):
    """Incident record returned by the API."""

    incident_id: str = Field(..., description="Incident identifier.")
    status: IncidentStatus = Field(..., description="Incident lifecycle status.")
    ingest_time: datetime = Field(..., description="ingest_time when incident was stored.")

    class Config:
        from_attributes = True


class IncidentListItem(BaseModel):
    """List item for incidents."""

    incident_id: str = Field(..., description="Incident identifier.")
    robot_id: str = Field(..., description="Robot identifier.")
    incident_type: IncidentType = Field(..., description="Observed incident category.")
    incident_level: IncidentLevel = Field(..., description="Operational severity level.")
    status: IncidentStatus = Field(..., description="Incident lifecycle status.")
    event_time_start: datetime = Field(..., description="event_time when incident started.")
    ingest_time: datetime = Field(..., description="ingest_time when incident was stored.")


class IncidentListResponse(BaseModel):
    """Paginated list of incidents."""

    items: List[IncidentListItem]
    total: int
    page: int
    size: int
    pages: int
