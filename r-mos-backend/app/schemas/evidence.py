"""
Evidence schemas for immutable evidence bundles and items.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    TELEMETRY = "telemetry"
    EVENT = "event"
    SOP_STEP = "sop_step"
    MEDIA = "media"
    DOCUMENT = "document"
    LOG = "log"


class EvidenceBundleType(str, Enum):
    TELEMETRY_SNAPSHOT = "telemetry_snapshot"
    EVENT_LOG = "event_log"
    SOP_EXECUTION = "sop_execution"
    MEDIA = "media"
    MIXED = "mixed"


class HashAlgo(str, Enum):
    SHA256 = "sha256"


class EvidenceItem(BaseModel):
    """Immutable evidence item metadata."""

    evidence_id: str = Field(..., description="Evidence item identifier.")
    evidence_type: EvidenceType = Field(..., description="Evidence classification.")
    content_uri: str = Field(..., description="URI for evidence content.")
    content_hash: str = Field(..., description="SHA-256 hash of evidence content.")
    content_hash_algo: HashAlgo = Field(..., description="Hash algorithm for content_hash.")
    content_mime_type: str = Field(..., description="MIME type of evidence content.")
    size_bytes: int = Field(..., ge=0, description="Content size in bytes.")
    observed_time: datetime = Field(..., description="observed_time when evidence was captured.")
    ingest_time: datetime = Field(..., description="ingest_time when evidence was stored.")
    human_summary: Optional[str] = Field(None, description="Human-readable summary (non-conclusionary).")
    machine_code: Optional[str] = Field(None, description="Machine-readable code for indexing.")
    machine_tags: Optional[List[str]] = Field(None, description="Machine-readable tags for indexing.")


class EvidenceBundleCreate(BaseModel):
    """Create an evidence bundle."""

    bundle_type: EvidenceBundleType = Field(..., description="Bundle classification.")
    observed_time_start: datetime = Field(..., description="observed_time window start.")
    observed_time_end: Optional[datetime] = Field(None, description="observed_time window end.")
    items: List[EvidenceItem] = Field(..., min_length=1, description="Evidence items in the bundle.")
    human_summary: Optional[str] = Field(None, description="Human-readable summary (non-conclusionary).")
    machine_tags: Optional[List[str]] = Field(None, description="Machine-readable tags for indexing.")


class EvidenceBundleResponse(EvidenceBundleCreate):
    """Evidence bundle stored in the system."""

    evidence_bundle_id: str = Field(..., description="Evidence bundle identifier.")
    bundle_hash: str = Field(..., description="SHA-256 hash of the bundle manifest.")
    bundle_hash_algo: HashAlgo = Field(..., description="Hash algorithm for bundle_hash.")
    ingest_time: datetime = Field(..., description="ingest_time when bundle was stored.")
    is_sealed: bool = Field(..., description="Whether the bundle is sealed (immutable).")
    sealed_at: Optional[datetime] = Field(None, description="ingest_time when the bundle was sealed.")

    class Config:
        from_attributes = True


class EvidenceBundleListItem(BaseModel):
    """List item for evidence bundles."""

    evidence_bundle_id: str = Field(..., description="Evidence bundle identifier.")
    bundle_type: EvidenceBundleType = Field(..., description="Bundle classification.")
    observed_time_start: datetime = Field(..., description="observed_time window start.")
    ingest_time: datetime = Field(..., description="ingest_time when bundle was stored.")
    is_sealed: bool = Field(..., description="Whether the bundle is sealed.")


class EvidenceBundleListResponse(BaseModel):
    """Paginated list of evidence bundles."""

    items: List[EvidenceBundleListItem]
    total: int
    page: int
    size: int
    pages: int
