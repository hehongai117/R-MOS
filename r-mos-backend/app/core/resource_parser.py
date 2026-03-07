"""
Resource Parser - Gate-0 Hard Gate Implementation

This module provides resource reference parsing and validation for the agent system.
It ensures all write requests are properly bound to resources before execution.

Phase 0: Week 1 - Gate-0 hard gate implementation
"""

from typing import Dict, Any, List, Optional, Set, Callable
from enum import Enum
from dataclasses import dataclass, field
import hashlib
import re


class ResourceType(str, Enum):
    """Supported resource types"""
    TASK = "task"
    SOP = "sop"
    KNOWLEDGE = "knowledge"
    ROBOT = "robot"
    USER = "user"
    COURSE = "course"
    ASSIGNMENT = "assignment"
    EVIDENCE = "evidence"


class ResourceAccessLevel(str, Enum):
    """Resource access levels"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


@dataclass
class ResourceRef:
    """Resource reference structure"""
    resource_type: ResourceType
    resource_id: str
    access_level: ResourceAccessLevel
    scope: Optional[str] = None  # personal, course, shared
    owner_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceBindingResult:
    """Result of resource binding validation"""
    is_valid: bool
    resources: List[ResourceRef] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    policy_decision: Optional[str] = None


class ResourceParser:
    """
    Resource Parser for validating and binding resources to requests.

    Responsibilities:
    - Parse resource references from request
    - Validate resource accessibility
    - Enforce resource binding for write operations
    """

    # Resource ID patterns for validation
    RESOURCE_PATTERNS: Dict[ResourceType, str] = {
        ResourceType.TASK: r"^task-[a-zA-Z0-9]{8}$",
        ResourceType.SOP: r"^sop-[a-zA-Z0-9]{8}$",
        ResourceType.KNOWLEDGE: r"^kb-[a-zA-Z0-9]{8}$",
        ResourceType.ROBOT: r"^robot-[a-zA-Z0-9]{8}$",
        ResourceType.USER: r"^user-[a-zA-Z0-9]{8}$",
        ResourceType.COURSE: r"^course-[a-zA-Z0-9]{8}$",
        ResourceType.ASSIGNMENT: r"^assign-[a-zA-Z0-9]{8}$",
        ResourceType.EVIDENCE: r"^ev-[a-zA-Z0-9]{8}$",
    }

    # Default access levels for operations
    OPERATION_ACCESS_LEVELS: Dict[str, ResourceAccessLevel] = {
        "create": ResourceAccessLevel.WRITE,
        "update": ResourceAccessLevel.WRITE,
        "delete": ResourceAccessLevel.WRITE,
        "execute": ResourceAccessLevel.EXECUTE,
        "read": ResourceAccessLevel.READ,
        "search": ResourceAccessLevel.READ,
    }

    def __init__(self):
        self._cache: Dict[str, ResourceBindingResult] = {}
        self._resource_exists_lookup: Optional[Callable[[ResourceRef], bool]] = None

    def set_resource_exists_lookup(self, lookup: Optional[Callable[[ResourceRef], bool]]) -> None:
        """
        Configure a resource existence lookup function.

        The lookup can be backed by database queries in upper layers while keeping
        this parser decoupled from persistence details.
        """
        self._resource_exists_lookup = lookup

    def parse_resource_ref(self, resource_data: Dict[str, Any]) -> ResourceBindingResult:
        """
        Parse and validate a resource reference from request.

        Args:
            resource_data: Resource reference data from request

        Returns:
            ResourceBindingResult with validation status and parsed resources
        """
        errors: List[str] = []
        warnings: List[str] = []
        resources: List[ResourceRef] = []

        # Extract resources from the reference
        resources_list = resource_data.get("resources", [])

        if not resources_list:
            # Try to extract from legacy format
            single_resource = resource_data.get("resource")
            if single_resource:
                resources_list = [single_resource]
            else:
                warnings.append("No resources specified in resource_ref")

        for idx, res in enumerate(resources_list):
            try:
                resource_type = ResourceType(res.get("type", ""))
                resource_id = res.get("id", "")
                access_level = ResourceAccessLevel(res.get("access", "read"))

                # Validate resource ID format
                pattern = self.RESOURCE_PATTERNS.get(resource_type)
                if pattern and not re.match(pattern, resource_id):
                    errors.append(f"Invalid resource ID format for {resource_type}: {resource_id}")
                    continue

                # Create resource reference
                resource_ref = ResourceRef(
                    resource_type=resource_type,
                    resource_id=resource_id,
                    access_level=access_level,
                    scope=res.get("scope"),
                    owner_id=res.get("owner_id"),
                    metadata=res.get("metadata", {})
                )
                resources.append(resource_ref)

            except ValueError as e:
                errors.append(f"Invalid resource at index {idx}: {str(e)}")

        # Check if write operations have proper resource binding
        write_resources = [r for r in resources if r.access_level in
                         [ResourceAccessLevel.WRITE, ResourceAccessLevel.EXECUTE]]

        if write_resources and not resources:
            errors.append("Write operations require resource binding")

        is_valid = len(errors) == 0

        return ResourceBindingResult(
            is_valid=is_valid,
            resources=resources,
            errors=errors,
            warnings=warnings,
            policy_decision="allow" if is_valid else "deny"
        )

    def validate_resource_access(
        self,
        user_id: str,
        resource_refs: List[ResourceRef]
    ) -> tuple[bool, List[str]]:
        """
        Validate user has access to the specified resources.

        Args:
            user_id: User ID
            resource_refs: List of resource references

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors: List[str] = []

        for ref in resource_refs:
            # Check scope-based access
            if ref.scope == "personal" and ref.owner_id and ref.owner_id != user_id:
                errors.append(f"User {user_id} cannot access personal resource {ref.resource_id}")
                continue

            if not self._check_resource_existence(ref):
                errors.append(f"Resource not found or unavailable: {ref.resource_id}")

        return len(errors) == 0, errors

    def _check_resource_existence(self, ref: ResourceRef) -> bool:
        """
        Check whether the resource exists.

        Priority:
        1) Configured lookup callback (typically DB-backed in service layer)
        2) Inline metadata hint: metadata.exists
        3) Default allow for backward compatibility
        """
        if self._resource_exists_lookup is not None:
            try:
                return bool(self._resource_exists_lookup(ref))
            except Exception:
                return False

        metadata_exists = ref.metadata.get("exists")
        if isinstance(metadata_exists, bool):
            return metadata_exists

        return True

    def compute_resource_hash(self, resource_refs: List[ResourceRef]) -> str:
        """
        Compute a hash of the resource references for idempotency.

        Args:
            resource_refs: List of resource references

        Returns:
            SHA256 hash string
        """
        # Sort resources for deterministic hashing
        sorted_resources = sorted(
            [f"{r.resource_type.value}:{r.resource_id}:{r.access_level.value}" for r in resource_refs]
        )
        hash_input = "|".join(sorted_resources)
        return hashlib.sha256(hash_input.encode()).hexdigest()

    def clear_cache(self):
        """Clear the internal cache"""
        self._cache.clear()


# Singleton instance
resource_parser = ResourceParser()
