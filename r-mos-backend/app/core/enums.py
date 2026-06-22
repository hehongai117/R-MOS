"""
Shared enumerations for R-MOS backend.

Centralises enum types that are used across multiple modules so that
every service imports a single, authoritative definition.
"""

from enum import Enum


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
