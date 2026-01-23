"""
External assessment integration schemas.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    DIAGNOSIS = "diagnosis"
    PHM = "phm"
    INSURANCE = "insurance"
    ARBITRATION = "arbitration"


class ProviderStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    RETIRED = "retired"


class AssessmentStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    DISPUTED = "disputed"


class ReportFormat(str, Enum):
    PDF = "pdf"
    JSON = "json"
    HTML = "html"
    URL = "url"
    ARCHIVE = "archive"
    OTHER = "other"


class HashAlgo(str, Enum):
    SHA256 = "sha256"


class AuditAction(str, Enum):
    SUBMITTED = "submitted"
    REVOKED = "revoked"
    DISPUTED = "disputed"
    REINSTATED = "reinstated"


class ActorType(str, Enum):
    USER = "user"
    SYSTEM = "system"
    PROVIDER = "provider"


class AssessmentReasonCode(str, Enum):
    INVALID_SIGNATURE = "invalid_signature"
    PROVIDER_WITHDRAWN = "provider_withdrawn"
    EXPIRED = "expired"
    OPERATOR_ERROR = "operator_error"
    LEGAL_HOLD = "legal_hold"
    OTHER = "other"


class AssessmentReasonCodeWithNone(str, Enum):
    NONE = "none"
    INVALID_SIGNATURE = "invalid_signature"
    PROVIDER_WITHDRAWN = "provider_withdrawn"
    EXPIRED = "expired"
    OPERATOR_ERROR = "operator_error"
    LEGAL_HOLD = "legal_hold"
    OTHER = "other"


class AssessmentProviderCreate(BaseModel):
    """Register an external assessment provider."""

    provider_name: str = Field(..., description="Human-readable provider name.")
    provider_type: ProviderType = Field(..., description="Provider classification.")
    endpoint_uri: Optional[str] = Field(None, description="Provider integration endpoint URI.")
    contact_name: Optional[str] = Field(None, description="Human contact name.")
    contact_email: Optional[str] = Field(None, description="Human contact email.")


class AssessmentProviderUpdate(BaseModel):
    """Update provider metadata."""

    provider_name: Optional[str] = Field(None, description="Updated provider name.")
    endpoint_uri: Optional[str] = Field(None, description="Updated provider endpoint URI.")
    contact_name: Optional[str] = Field(None, description="Updated contact name.")
    contact_email: Optional[str] = Field(None, description="Updated contact email.")
    status: Optional[ProviderStatus] = Field(None, description="Provider availability status.")


class AssessmentProviderResponse(BaseModel):
    """Provider registry record."""

    provider_id: str = Field(..., description="Stable provider identifier.")
    provider_name: str = Field(..., description="Human-readable provider name.")
    provider_type: ProviderType = Field(..., description="Provider classification.")
    status: ProviderStatus = Field(..., description="Provider availability status.")
    endpoint_uri: Optional[str] = Field(None, description="Provider integration endpoint URI.")
    contact_name: Optional[str] = Field(None, description="Human contact name.")
    contact_email: Optional[str] = Field(None, description="Human contact email.")
    created_at: datetime = Field(..., description="ingest_time when provider was created.")
    updated_at: datetime = Field(..., description="ingest_time when provider was last updated.")

    class Config:
        from_attributes = True


class AssessmentProviderListResponse(BaseModel):
    """Paginated list of providers."""

    items: List[AssessmentProviderResponse]
    total: int
    page: int
    size: int
    pages: int


class ExternalAssessmentCreate(BaseModel):
    """Submit a reference to an external assessment report."""

    provider_id: str = Field(..., description="Provider identifier.")
    assessment_type: ProviderType = Field(..., description="Assessment classification.")
    provider_assessment_id: Optional[str] = Field(None, description="Provider-side assessment identifier.")
    report_uri: str = Field(..., description="Immutable report reference URI.")
    report_hash: str = Field(..., description="SHA-256 hash of report content.")
    report_hash_algo: HashAlgo = Field(..., description="Hash algorithm for report_hash.")
    report_format: ReportFormat = Field(..., description="Report media format identifier.")
    report_time: datetime = Field(..., description="event_time when provider issued the report.")
    evidence_bundle_ids: Optional[List[str]] = Field(None, description="Referenced evidence bundle identifiers.")
    incident_ids: Optional[List[str]] = Field(None, description="Referenced incident identifiers.")
    observation_ids: Optional[List[str]] = Field(None, description="Referenced observation identifiers.")


class ExternalAssessmentResponse(ExternalAssessmentCreate):
    """Stored assessment reference."""

    assessment_id: str = Field(..., description="Assessment reference identifier.")
    provider_type: ProviderType = Field(..., description="Provider classification snapshot.")
    ingest_time: datetime = Field(..., description="ingest_time when reference was stored.")
    status: AssessmentStatus = Field(..., description="Reference status for audit handling.")
    status_updated_at: datetime = Field(..., description="ingest_time when status last changed.")

    class Config:
        from_attributes = True


class ExternalAssessmentListItem(BaseModel):
    """List item for assessments."""

    assessment_id: str = Field(..., description="Assessment reference identifier.")
    provider_id: str = Field(..., description="Provider identifier.")
    assessment_type: ProviderType = Field(..., description="Assessment classification.")
    status: AssessmentStatus = Field(..., description="Reference status.")
    report_time: datetime = Field(..., description="event_time when report was issued.")
    ingest_time: datetime = Field(..., description="ingest_time when reference was stored.")


class ExternalAssessmentListResponse(BaseModel):
    """Paginated list of assessment references."""

    items: List[ExternalAssessmentListItem]
    total: int
    page: int
    size: int
    pages: int


class AssessmentStatusChangeRequest(BaseModel):
    """Administrative status change request."""

    reason_code: AssessmentReasonCode = Field(..., description="Administrative reason for status change.")
    reason_note: Optional[str] = Field(None, description="Optional administrative note (non-conclusionary).")


class AssessmentAuditEvent(BaseModel):
    """Immutable audit event."""

    audit_id: str = Field(..., description="Audit event identifier.")
    assessment_id: str = Field(..., description="Assessment reference identifier.")
    action: AuditAction = Field(..., description="Administrative action applied.")
    actor_type: ActorType = Field(..., description="Actor category.")
    actor_id: str = Field(..., description="Actor identifier.")
    reason_code: AssessmentReasonCodeWithNone = Field(..., description="Administrative reason code.")
    reason_note: Optional[str] = Field(None, description="Optional administrative note.")
    event_time: datetime = Field(..., description="event_time when action occurred.")
    ingest_time: datetime = Field(..., description="ingest_time when audit record stored.")
    trace_id: str = Field(..., description="Trace identifier for audit correlation.")


class AssessmentAuditTrail(BaseModel):
    """Audit trail for a single assessment reference."""

    assessment_id: str
    events: List[AssessmentAuditEvent]
    total: int
