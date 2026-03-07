"""
Approval Queue Service - Phase 2 Week 8
Manages approval queues for agent actions requiring authorization

Provides:
- Approval request queue
- Approval workflow management
- Priority-based processing
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import time
import uuid


class ApprovalStatus(str, Enum):
    """Approval status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalPriority(str, Enum):
    """Approval priority"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class ApprovalRequest:
    """Approval request"""
    id: str
    requester_id: str
    resource_type: str
    resource_id: str
    action: str
    priority: ApprovalPriority
    status: ApprovalStatus
    reason: str
    evidence_refs: List[str] = field(default_factory=list)
    created_at: int = field(default_factory=lambda: int(time.time() * 1000))
    expires_at: Optional[int] = None
    approved_by: Optional[str] = None
    approved_at: Optional[int] = None
    rejection_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ApprovalQueue:
    """
    Approval Queue for managing approval requests.

    Features:
    - Priority-based queue
    - Auto-expiration
    - Bulk operations
    """

    def __init__(self, default_ttl_seconds: int = 3600):
        self._requests: Dict[str, ApprovalRequest] = {}
        self._queue_by_status: Dict[ApprovalStatus, List[str]] = {
            ApprovalStatus.PENDING: [],
            ApprovalStatus.APPROVED: [],
            ApprovalStatus.REJECTED: [],
            ApprovalStatus.EXPIRED: [],
        }
        self._default_ttl = default_ttl_seconds

    def create_request(
        self,
        requester_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        reason: str,
        priority: ApprovalPriority = ApprovalPriority.NORMAL,
        evidence_refs: Optional[List[str]] = None,
        ttl_seconds: Optional[int] = None,
    ) -> str:
        """Create a new approval request"""
        request_id = f"apr-{uuid.uuid4().hex[:8]}"

        ttl = ttl_seconds or self._default_ttl

        request = ApprovalRequest(
            id=request_id,
            requester_id=requester_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            priority=priority,
            status=ApprovalStatus.PENDING,
            reason=reason,
            evidence_refs=evidence_refs or [],
            expires_at=int(time.time() * 1000) + (ttl * 1000),
        )

        self._requests[request_id] = request
        self._queue_by_status[ApprovalStatus.PENDING].append(request_id)

        return request_id

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get approval request by ID"""
        return self._requests.get(request_id)

    def approve(
        self,
        request_id: str,
        approved_by: str,
    ) -> bool:
        """Approve a request"""
        if request_id not in self._requests:
            return False

        request = self._requests[request_id]

        if request.status != ApprovalStatus.PENDING:
            return False

        # Check if expired
        if request.expires_at and request.expires_at < int(time.time() * 1000):
            request.status = ApprovalStatus.EXPIRED
            return False

        request.status = ApprovalStatus.APPROVED
        request.approved_by = approved_by
        request.approved_at = int(time.time() * 1000)

        # Move to approved queue
        self._queue_by_status[ApprovalStatus.PENDING].remove(request_id)
        self._queue_by_status[ApprovalStatus.APPROVED].append(request_id)

        return True

    def reject(
        self,
        request_id: str,
        rejection_reason: str,
    ) -> bool:
        """Reject a request"""
        if request_id not in self._requests:
            return False

        request = self._requests[request_id]

        if request.status != ApprovalStatus.PENDING:
            return False

        request.status = ApprovalStatus.REJECTED
        request.rejection_reason = rejection_reason

        # Move to rejected queue
        self._queue_by_status[ApprovalStatus.PENDING].remove(request_id)
        self._queue_by_status[ApprovalStatus.REJECTED].append(request_id)

        return True

    def get_pending_requests(
        self,
        priority: Optional[ApprovalPriority] = None,
        limit: int = 100,
    ) -> List[ApprovalRequest]:
        """Get pending approval requests"""
        pending_ids = self._queue_by_status[ApprovalStatus.PENDING]
        requests = [self._requests[rid] for rid in pending_ids if rid in self._requests]

        # Filter by priority if specified
        if priority:
            requests = [r for r in requests if r.priority == priority]

        # Sort by priority and creation time
        priority_order = {ApprovalPriority.URGENT: 0, ApprovalPriority.HIGH: 1, ApprovalPriority.NORMAL: 2, ApprovalPriority.LOW: 3}
        requests.sort(key=lambda r: (priority_order.get(r.priority, 3), r.created_at))

        return requests[:limit]

    def get_request_history(
        self,
        requester_id: Optional[str] = None,
        status: Optional[ApprovalStatus] = None,
        limit: int = 100,
    ) -> List[ApprovalRequest]:
        """Get approval request history"""
        all_requests = list(self._requests.values())

        # Filter by requester
        if requester_id:
            all_requests = [r for r in all_requests if r.requester_id == requester_id]

        # Filter by status
        if status:
            all_requests = [r for r in all_requests if r.status == status]

        # Sort by creation time (newest first)
        all_requests.sort(key=lambda r: r.created_at, reverse=True)

        return all_requests[:limit]

    def check_expirations(self) -> List[str]:
        """Check and expire old pending requests"""
        current_time = int(time.time() * 1000)
        expired_ids = []

        pending_ids = list(self._queue_by_status[ApprovalStatus.PENDING])

        for request_id in pending_ids:
            request = self._requests[request_id]
            if request.expires_at and request.expires_at < current_time:
                request.status = ApprovalStatus.EXPIRED
                self._queue_by_status[ApprovalStatus.PENDING].remove(request_id)
                self._queue_by_status[ApprovalStatus.EXPIRED].append(request_id)
                expired_ids.append(request_id)

        return expired_ids


# Singleton instance
approval_queue = ApprovalQueue()
