# Knowledge Governance Service
# Phase 5: Knowledge Governance

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime, timedelta
import time


class KnowledgeStatus(str, Enum):
    """Knowledge entry status"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    DRAFT = "DRAFT"


class KnowledgeType(str, Enum):
    """Knowledge entry types"""
    SOLUTION = "solution"
    PATTERN = "pattern"
    DOCUMENT = "document"
    TIP = "tip"
    WARNING = "warning"


class RiskLevel(str, Enum):
    """Risk levels"""
    R0 = "R0"
    R1 = "R1"
    R2 = "R2"
    R3 = "R3"


class ExpiryType(str, Enum):
    """Expiry types"""
    TIME_BASED = "time_based"
    USAGE_BASED = "usage_based"
    CONDITION_BASED = "condition_based"


class Scope(BaseModel):
    """Applicable scope for knowledge"""
    device_model: List[str] = Field(default_factory=list)
    part_type: List[str] = Field(default_factory=list)
    version_range: Optional[str] = None
    scenario: List[str] = Field(default_factory=list)


class Contraindications(BaseModel):
    """Contraindications - when NOT to apply this knowledge"""
    device_model: List[str] = Field(default_factory=list)
    part_material: List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)


class Expiry(BaseModel):
    """Expiry conditions"""
    type: ExpiryType
    value: int  # months for time_based, count for usage_based
    review_required: bool = True


class Confidence(BaseModel):
    """Confidence metrics"""
    evidence_count: int = 0
    success_rate: float = 0.0  # 0-1
    reviewer_count: int = 0
    average_rating: Optional[float] = None  # 1-5


class HistoryEntry(BaseModel):
    """Version history entry"""
    version: int
    change: str
    author: str
    timestamp: int


class KnowledgeEntry(BaseModel):
    """
    Knowledge Entry

    Fields from design doc:
    - scope: Applicable scope
    - contraindications: When NOT to apply
    - risk_level: Risk level
    - expiry: Expiry conditions
    - version: Version number
    - history: Version history
    """
    id: str
    type: KnowledgeType

    # Status
    status: KnowledgeStatus = KnowledgeStatus.PENDING

    # Content
    title: str
    content: str
    summary: str = ""

    # Scope (key for knowledge governance!)
    scope: Scope = Field(default_factory=Scope)
    contraindications: Contraindications = Field(default_factory=Contraindications)

    # Risk
    risk_level: RiskLevel = RiskLevel.R1

    # Confidence
    confidence: Confidence = Field(default_factory=Confidence)

    # Expiry
    expiry: Optional[Expiry] = None
    expired_at: Optional[int] = None

    # Version management
    version: int = 1
    history: List[HistoryEntry] = Field(default_factory=list)

    # Provenance
    source_task_id: Optional[str] = None
    source_evidence_ids: List[str] = Field(default_factory=list)
    created_at: int = Field(default_factory=lambda: int(time.time() * 1000))
    created_by: str = ""
    approved_by: Optional[str] = None
    approved_at: Optional[int] = None

    # Metadata
    tags: List[str] = Field(default_factory=list)
    category: str = ""


class ApprovalRequest(BaseModel):
    """Request to approve knowledge"""
    entry_id: str
    reviewer_id: str
    decision: str  # approve, reject
    feedback: str = ""
    rating: Optional[float] = None  # 1-5


class KnowledgeSearchQuery(BaseModel):
    """Search query for knowledge"""
    query: str = ""
    device_model: Optional[str] = None
    part_type: Optional[str] = None
    status: Optional[KnowledgeStatus] = KnowledgeStatus.APPROVED
    risk_level: Optional[RiskLevel] = None
    tags: List[str] = Field(default_factory=list)


class KnowledgeMatch(BaseModel):
    """Matched knowledge entry"""
    entry: KnowledgeEntry
    relevance_score: float  # 0-1
    match_reasons: List[str] = Field(default_factory=list)


class KnowledgeGovernance:
    """
    Knowledge Governance Service

    Responsibilities:
    - Manage knowledge scope and contraindications
    - Approval workflow
    - Expiry mechanism
    - Confidence calculation
    """

    def __init__(self):
        self._knowledge_store: Dict[str, KnowledgeEntry] = {}
        self._approval_requests: Dict[str, ApprovalRequest] = {}

    def create_knowledge(
        self,
        title: str,
        content: str,
        entry_type: KnowledgeType,
        creator_id: str,
        scope: Scope = None,
        risk_level: RiskLevel = RiskLevel.R1,
        source_task_id: str = None,
        source_evidence_ids: List[str] = None
    ) -> KnowledgeEntry:
        """Create new knowledge entry"""
        entry_id = f"kb-{int(time.time() * 1000)}"

        entry = KnowledgeEntry(
            id=entry_id,
            type=entry_type,
            title=title,
            content=content,
            status=KnowledgeStatus.DRAFT,
            scope=scope or Scope(),
            risk_level=risk_level,
            source_task_id=source_task_id,
            source_evidence_ids=source_evidence_ids or [],
            created_by=creator_id,
            history=[HistoryEntry(
                version=1,
                change="Created",
                author=creator_id,
                timestamp=int(time.time() * 1000)
            )]
        )

        self._knowledge_store[entry_id] = entry
        return entry

    def submit_for_review(self, entry_id: str) -> tuple[bool, str]:
        """Submit knowledge for approval"""
        entry = self._knowledge_store.get(entry_id)
        if not entry:
            return False, "Knowledge entry not found"

        if entry.status != KnowledgeStatus.DRAFT:
            return False, f"Cannot submit in {entry.status.value} status"

        entry.status = KnowledgeStatus.PENDING
        return True, "Submitted for review"

    def approve_knowledge(
        self,
        request: ApprovalRequest
    ) -> tuple[bool, str]:
        """Approve or reject knowledge"""
        entry = self._knowledge_store.get(request.entry_id)
        if not entry:
            return False, "Knowledge entry not found"

        if entry.status != KnowledgeStatus.PENDING:
            return False, f"Cannot approve in {entry.status.value} status"

        if request.decision == "approve":
            entry.status = KnowledgeStatus.APPROVED
            entry.approved_by = request.reviewer_id
            entry.approved_at = int(time.time() * 1000)

            # Update confidence if rating provided
            if request.rating:
                self._update_confidence_on_review(entry, request.rating)

            # Set expiry if configured
            if entry.expiry:
                entry.expired_at = self._calculate_expiry(entry.expiry)

            return True, "Approved"
        else:
            entry.status = KnowledgeStatus.REJECTED
            # Add feedback to history
            entry.history.append(HistoryEntry(
                version=entry.version,
                change=f"Rejected: {request.feedback}",
                author=request.reviewer_id,
                timestamp=int(time.time() * 1000)
            ))
            return True, "Rejected"

    def _update_confidence_on_review(
        self,
        entry: KnowledgeEntry,
        rating: float
    ) -> None:
        """Update confidence metrics after review"""
        entry.confidence.reviewer_count += 1
        entry.confidence.evidence_count += len(entry.source_evidence_ids)

        # Update average rating
        current = entry.confidence.average_rating or 0
        count = entry.confidence.reviewer_count
        entry.confidence.average_rating = (current * (count - 1) + rating) / count

        # Calculate success rate (simplified)
        if entry.confidence.success_rate > 0:
            entry.confidence.success_rate = (
                entry.confidence.success_rate * 0.7 + rating / 5.0 * 0.3
            )
        else:
            entry.confidence.success_rate = rating / 5.0

    def _calculate_expiry(self, expiry: Expiry) -> int:
        """Calculate expiry timestamp"""
        if expiry.type == ExpiryType.TIME_BASED:
            return int(time.time() * 1000) + (expiry.value * 30 * 24 * 60 * 60 * 1000)
        # Other expiry types need external triggers
        return 0

    def check_expiry(self) -> List[str]:
        """Check and update expired entries"""
        expired_ids = []
        current_time = int(time.time() * 1000)

        for entry_id, entry in self._knowledge_store.items():
            if entry.status == KnowledgeStatus.APPROVED:
                if entry.expired_at and current_time > entry.expired_at:
                    entry.status = KnowledgeStatus.EXPIRED
                    expired_ids.append(entry_id)

        return expired_ids

    def search_knowledge(
        self,
        query: KnowledgeSearchQuery
    ) -> List[KnowledgeMatch]:
        """Search knowledge with scope matching"""
        results = []

        for entry in self._knowledge_store.values():
            # Filter by status
            if query.status and entry.status != query.status:
                continue

            # Filter by risk level
            if query.risk_level and entry.risk_level != query.risk_level:
                continue

            # Filter by scope
            if query.device_model:
                if query.device_model not in entry.scope.device_model:
                    if entry.scope.device_model:  # Has restrictions but doesn't match
                        continue

            # Filter by tags
            if query.tags:
                if not any(tag in entry.tags for tag in query.tags):
                    continue

            # Check contraindications
            if query.device_model:
                if query.device_model in entry.contraindications.device_model:
                    continue  # Contraindicated

            # Calculate relevance
            score = self._calculate_relevance(entry, query)
            if score > 0:
                results.append(KnowledgeMatch(
                    entry=entry,
                    relevance_score=score,
                    match_reasons=self._get_match_reasons(entry, query)
                ))

        # Sort by relevance
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results

    def _calculate_relevance(
        self,
        entry: KnowledgeEntry,
        query: KnowledgeSearchQuery
    ) -> float:
        """Calculate relevance score"""
        score = 0.0

        # Text match
        if query.query:
            if query.query.lower() in entry.title.lower():
                score += 0.5
            if query.query.lower() in entry.content.lower():
                score += 0.3

        # Scope match
        if query.device_model:
            if query.device_model in entry.scope.device_model:
                score += 0.2

        # Confidence boost
        score += entry.confidence.success_rate * 0.2

        return min(score, 1.0)

    def _get_match_reasons(
        self,
        entry: KnowledgeEntry,
        query: KnowledgeSearchQuery
    ) -> List[str]:
        """Get reasons why this entry matched"""
        reasons = []

        if query.query:
            reasons.append(f"匹配关键词: {query.query}")

        if query.device_model:
            if query.device_model in entry.scope.device_model:
                reasons.append(f"适用于设备: {query.device_model}")

        if entry.confidence.success_rate > 0.8:
            reasons.append(f"高置信度: {entry.confidence.success_rate:.0%}")

        return reasons

    def get_knowledge(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """Get knowledge entry by ID"""
        return self._knowledge_store.get(entry_id)

    def update_knowledge(
        self,
        entry_id: str,
        updates: Dict[str, Any],
        updater_id: str
    ) -> tuple[bool, str]:
        """Update knowledge entry (creates new version)"""
        entry = self._knowledge_store.get(entry_id)
        if not entry:
            return False, "Knowledge entry not found"

        # Only approved entries can be updated
        if entry.status != KnowledgeStatus.APPROVED:
            return False, f"Cannot update in {entry.status.value} status"

        # Create new version
        entry.version += 1
        change_summary = updates.get("change_summary", "Updated")

        entry.history.append(HistoryEntry(
            version=entry.version,
            change=change_summary,
            author=updater_id,
            timestamp=int(time.time() * 1000)
        ))

        # Apply updates
        if "title" in updates:
            entry.title = updates["title"]
        if "content" in updates:
            entry.content = updates["content"]
        if "scope" in updates:
            entry.scope = updates["scope"]

        # Reset to pending for re-approval
        entry.status = KnowledgeStatus.PENDING

        return True, f"Updated to version {entry.version}"

    def get_statistics(self) -> Dict[str, Any]:
        """Get knowledge statistics"""
        stats = {
            "total": len(self._knowledge_store),
            "by_status": {},
            "by_type": {},
            "by_risk_level": {},
            "avg_confidence": 0.0
        }

        total_confidence = 0.0
        count = 0

        for entry in self._knowledge_store.values():
            # By status
            status = entry.status.value
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

            # By type
            t = entry.type.value
            stats["by_type"][t] = stats["by_type"].get(t, 0) + 1

            # By risk
            r = entry.risk_level.value
            stats["by_risk_level"][r] = stats["by_risk_level"].get(r, 0) + 1

            # Confidence
            if entry.status == KnowledgeStatus.APPROVED:
                total_confidence += entry.confidence.success_rate
                count += 1

        if count > 0:
            stats["avg_confidence"] = total_confidence / count

        return stats


# Singleton instance
knowledge_governance = KnowledgeGovernance()
