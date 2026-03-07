"""
Feature Flag Service - Phase 1 Week 5

Manages feature toggles for gradual rollout of Agent V2 features.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
import hashlib

from app.core.config import settings


@dataclass
class FeatureFlag:
    """Feature flag definition"""
    name: str
    enabled: bool
    rollout_percentage: int = 100  # 0-100, percentage of users
    conditions: Optional[Dict[str, Any]] = None
    description: str = ""


class FeatureFlagService:
    """
    Feature flag service for managing feature toggles.

    Usage:
        if feature_flags.is_enabled("agent_v2"):
            # Use V2 implementation
        else:
            # Use V1 implementation
    """

    def __init__(self):
        self._flags: Dict[str, FeatureFlag] = {}
        self._initialize_default_flags()

    def _initialize_default_flags(self):
        """Initialize default feature flags"""
        self.register_flag(FeatureFlag(
            name="agent_v2",
            enabled=settings.AGENT_V2_ENABLED,
            rollout_percentage=100 if settings.AGENT_V2_ENABLED else 0,
            description="Enable Agent V2 with Orchestrator, FSM, Idempotency"
        ))
        self.register_flag(FeatureFlag(
            name="agent_v2_fsm",
            enabled=settings.AGENT_V2_ENABLED,
            description="Enable Task FSM (Finite State Machine)"
        ))
        self.register_flag(FeatureFlag(
            name="agent_v2_idempotency",
            enabled=settings.AGENT_V2_ENABLED,
            description="Enable Idempotency Control"
        ))
        self.register_flag(FeatureFlag(
            name="agent_v2_budget",
            enabled=settings.AGENT_V2_ENABLED,
            description="Enable Budget Control"
        ))
        self.register_flag(FeatureFlag(
            name="policy_matrix",
            enabled=True,  # Always enabled as part of Gate-0
            description="Enable Policy Matrix evaluation"
        ))

    def register_flag(self, flag: FeatureFlag):
        """Register a feature flag"""
        self._flags[flag.name] = flag

    def is_enabled(self, flag_name: str, user_id: Optional[str] = None) -> bool:
        """
        Check if a feature flag is enabled for a user.

        Args:
            flag_name: Name of the feature flag
            user_id: Optional user ID for percentage rollout

        Returns:
            True if feature is enabled
        """
        flag = self._flags.get(flag_name)
        if not flag:
            return False

        if not flag.enabled:
            return False

        # Check rollout percentage
        if user_id and flag.rollout_percentage < 100:
            # Use hash of user_id to deterministically assign to rollout group
            user_hash = int(hashlib.md5(user_id.encode()).hexdigest(), 16) % 100
            return user_hash < flag.rollout_percentage

        return True

    def get_flag(self, flag_name: str) -> Optional[FeatureFlag]:
        """Get feature flag by name"""
        return self._flags.get(flag_name)

    def enable_flag(self, flag_name: str):
        """Enable a feature flag"""
        if flag_name in self._flags:
            self._flags[flag_name].enabled = True

    def disable_flag(self, flag_name: str):
        """Disable a feature flag"""
        if flag_name in self._flags:
            self._flags[flag_name].enabled = False

    def set_rollout_percentage(self, flag_name: str, percentage: int):
        """Set rollout percentage for a flag"""
        if flag_name in self._flags:
            self._flags[flag_name].rollout_percentage = max(0, min(100, percentage))

    def list_flags(self) -> Dict[str, FeatureFlag]:
        """List all feature flags"""
        return self._flags.copy()


# Singleton instance
feature_flags = FeatureFlagService()
