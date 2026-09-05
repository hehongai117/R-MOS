"""
Shared enumerations for R-MOS backend.

Centralises enum types that are used across multiple modules so that
every service imports a single, authoritative definition.
"""

from enum import Enum


class EventType(str, Enum):
    """事件类型枚举（V2.3完整版）"""

    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_PAUSED = "task_paused"          # V2.1.2补充
    TASK_RESUMED = "task_resumed"        # V2.1.2补充
    STEP_EXECUTED = "step_executed"
    STEP_SKIPPED = "step_skipped"        # V2.1.2补充
    STEP_BLOCKED = "step_blocked"         # 安全中断
    STEP_WARNING = "step_warning"        # 步骤警告
    FAULT_DETECTED = "fault_detected"
    FAULT_CLEARED = "fault_cleared"
    SNAPSHOT_CREATED = "snapshot_created"
    SNAPSHOT_FAILED = "snapshot_failed"  # V2.1.2补充


class RiskLevel(str, Enum):
    """Unified risk-level enum.

    Two naming conventions are used across the codebase:

    * **R-series** (R0–R3): used by the policy-matrix / coach-agent /
      knowledge-governance subsystems to describe intervention severity.
    * **Named levels** (LOW/MEDIUM/HIGH/CRITICAL): used by the LLM risk
      scorer (``policy/risk_scorer.py``) to classify numeric score ranges.

    Both sets of values are included here so that the enum is a superset
    of every usage site.
    """

    # R-series (policy / coaching / knowledge subsystems)
    R0 = "R0"          # No risk / silent – no intervention needed
    R1 = "R1"          # Low risk / advisory – suggestion only
    R2 = "R2"          # Medium risk / warning – requires acknowledgment
    R3 = "R3"          # High risk / blocking – must be approved

    # Named levels (LLM risk scorer)
    LOW = "low"         # Score 0-30
    MEDIUM = "medium"   # Score 31-60
    HIGH = "high"       # Score 61-80
    CRITICAL = "critical"  # Score 81-100
