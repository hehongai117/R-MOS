# Conflict Arbitrator
# Phase 6: Integration - Conflict Resolution

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum
import time


class ConflictSeverity(str, Enum):
    """Conflict severity"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConflictSource(str, Enum):
    """Source of conflict"""
    AGENT_VS_AGENT = "agent_vs_agent"
    AGENT_VS_USER = "agent_vs_user"
    USER_VS_SYSTEM = "user_vs_system"
    STATE_VS_RULE = "state_vs_rule"


class ArbitrationStrategy(str, Enum):
    """Arbitration strategies"""
    PRIORITY_BASED = "priority_based"
    EVIDENCE_BASED = "evidence_based"
    USER_OVERRIDE = "user_override"
    SYSTEM_DEFAULT = "system_default"


class ConflictCase(BaseModel):
    """Conflict case for arbitration"""
    case_id: str
    conflict_type: str
    source: ConflictSource
    severity: ConflictSeverity

    # Parties involved
    party_a: Dict[str, Any]
    party_b: Dict[str, Any]

    # Evidence
    evidence_refs: List[str] = Field(default_factory=list)

    # Resolution
    strategy: Optional[ArbitrationStrategy] = None
    resolution: Optional[str] = None
    winner: Optional[str] = None

    # Metadata
    created_at: int = Field(default_factory=lambda: int(time.time() * 1000))
    resolved_at: Optional[int] = None


class ArbitrationRule(BaseModel):
    """Rule for conflict resolution"""
    rule_id: str
    name: str
    description: str

    # Conditions that trigger this rule
    conditions: Dict[str, Any] = Field(default_factory=dict)

    # Resolution strategy
    strategy: ArbitrationStrategy

    # Priority (higher wins)
    priority: int = 0

    # Winner when triggered
    winner_override: Optional[str] = None


# Predefined arbitration rules
ARBITRATION_RULES = [
    ArbitrationRule(
        rule_id="safety_first",
        name="Safety First",
        description="Safety-related conflicts always favor safety",
        conditions={"context.safety_related": True},
        strategy=ArbitrationStrategy.PRIORITY_BASED,
        priority=100,
        winner_override="system"
    ),
    ArbitrationRule(
        rule_id="instructor_override",
        name="Instructor Override",
        description="Instructor decisions override others",
        conditions={"actor.role": "instructor"},
        strategy=ArbitrationStrategy.PRIORITY_BASED,
        priority=90,
        winner_override="instructor"
    ),
    ArbitrationRule(
        rule_id="evidence_wins",
        name="Evidence Wins",
        description="Decision with more evidence wins",
        conditions={"type": "evidence_dispute"},
        strategy=ArbitrationStrategy.EVIDENCE_BASED,
        priority=50
    ),
    ArbitrationRule(
        rule_id="coach_recommendation",
        name="Coach Priority",
        description="Coach recommendations take precedence in normal flow",
        conditions={"source": "coach"},
        strategy=ArbitrationStrategy.PRIORITY_BASED,
        priority=30,
        winner_override="coach"
    ),
    ArbitrationRule(
        rule_id="diagnoser_authority",
        name="Diagnoser Authority",
        description="Diagnoser decisions on root cause are authoritative",
        conditions={"context.root_cause_analysis": True},
        strategy=ArbitrationStrategy.PRIORITY_BASED,
        priority=80,
        winner_override="diagnoser"
    )
]


class ConflictArbitrator:
    """
    Conflict Arbitrator

    Responsibilities:
    - Detect conflicts between agents/users
    - Apply arbitration rules
    - Resolve conflicts with proper strategy
    - Log all arbitration decisions
    """

    def __init__(self):
        self.rules: List[ArbitrationRule] = ARBITRATION_RULES
        self.cases: Dict[str, ConflictCase] = {}

    def register_rule(self, rule: ArbitrationRule) -> None:
        """Register a new arbitration rule"""
        self.rules.append(rule)
        # Sort by priority (highest first)
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def arbitrate(
        self,
        conflict_type: str,
        source: ConflictSource,
        party_a: Dict[str, Any],
        party_b: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> ConflictCase:
        """
        Arbitrate a conflict

        Steps:
        1. Create conflict case
        2. Match applicable rules
        3. Apply resolution strategy
        4. Return resolution
        """
        case_id = f"case-{int(time.time() * 1000)}"
        context = context or {}

        # Determine severity
        severity = self._determine_severity(conflict_type, party_a, party_b)

        case = ConflictCase(
            case_id=case_id,
            conflict_type=conflict_type,
            source=source,
            severity=severity,
            party_a=party_a,
            party_b=party_b,
            evidence_refs=context.get("evidence_refs", [])
        )

        # Match rules
        applicable_rules = self._match_rules(case, context)

        if applicable_rules:
            # Apply first matching rule (highest priority)
            rule = applicable_rules[0]
            case.strategy = rule.strategy
            case.resolution = self._apply_strategy(
                rule.strategy, case, rule, context
            )

            if rule.winner_override:
                case.winner = rule.winner_override
            else:
                case.winner = self._determine_winner(case, rule.strategy)
        else:
            # Default resolution
            case.strategy = ArbitrationStrategy.SYSTEM_DEFAULT
            case.resolution = "No specific rule matched, using default"
            case.winner = self._determine_winner(case, ArbitrationStrategy.SYSTEM_DEFAULT)

        case.resolved_at = int(time.time() * 1000)
        self.cases[case_id] = case

        return case

    def _determine_severity(
        self,
        conflict_type: str,
        party_a: Dict[str, Any],
        party_b: Dict[str, Any]
    ) -> ConflictSeverity:
        """Determine conflict severity"""
        # Safety-related conflicts are critical
        if conflict_type == "safety":
            return ConflictSeverity.CRITICAL

        # High-risk actions
        if party_a.get("risk_level") == "R3" or party_b.get("risk_level") == "R3":
            return ConflictSeverity.HIGH

        # Medium for other agent conflicts
        if conflict_type == "agent_vs_agent":
            return ConflictSeverity.MEDIUM

        return ConflictSeverity.LOW

    def _match_rules(
        self,
        case: ConflictCase,
        context: Dict[str, Any]
    ) -> List[ArbitrationRule]:
        """Match applicable rules for this conflict"""
        matched = []

        for rule in self.rules:
            if self._rule_matches(rule, case, context):
                matched.append(rule)

        return matched

    def _rule_matches(
        self,
        rule: ArbitrationRule,
        case: ConflictCase,
        context: Dict[str, Any]
    ) -> bool:
        """Check if rule matches the conflict"""
        conditions = rule.conditions

        # Check condition keywords in context
        for key, value in conditions.items():
            if "." in key:  # Nested key
                parts = key.split(".")
                current = context
                for part in parts:
                    if part not in current:
                        return False
                    current = current[part]
                if current != value:
                    return False
            else:
                if context.get(key) != value:
                    return False

        return True

    def _apply_strategy(
        self,
        strategy: ArbitrationStrategy,
        case: ConflictCase,
        rule: ArbitrationRule,
        context: Dict[str, Any]
    ) -> str:
        """Apply resolution strategy"""
        if strategy == ArbitrationStrategy.PRIORITY_BASED:
            return f"Priority-based resolution: {rule.name}"
        elif strategy == ArbitrationStrategy.EVIDENCE_BASED:
            return f"Evidence-based resolution: comparing {len(case.evidence_refs)} evidence items"
        elif strategy == ArbitrationStrategy.USER_OVERRIDE:
            return "User override applied"
        else:
            return f"System default resolution: {rule.name}"

    def _determine_winner(
        self,
        case: ConflictCase,
        strategy: ArbitrationStrategy
    ) -> str:
        """Determine winning party"""
        if strategy == ArbitrationStrategy.EVIDENCE_BASED:
            # More evidence wins
            evidence_a = len(case.party_a.get("evidence", []))
            evidence_b = len(case.party_b.get("evidence", []))
            return "party_a" if evidence_a >= evidence_b else "party_b"

        # Default: party_a wins
        return "party_a"

    def get_case(self, case_id: str) -> Optional[ConflictCase]:
        """Get conflict case by ID"""
        return self.cases.get(case_id)

    def get_cases(
        self,
        status: str = None,
        severity: ConflictSeverity = None
    ) -> List[ConflictCase]:
        """Get cases with optional filters"""
        results = list(self.cases.values())

        if status:
            results = [c for c in results if c.resolution is not None]

        if severity:
            results = [c for c in results if c.severity == severity]

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Get arbitration statistics"""
        total = len(self.cases)
        resolved = sum(1 for c in self.cases.values() if c.resolved_at)

        by_severity = {}
        by_source = {}
        by_type = {}

        for case in self.cases.values():
            by_severity[case.severity.value] = by_severity.get(case.severity.value, 0) + 1
            by_source[case.source.value] = by_source.get(case.source.value, 0) + 1
            by_type[case.conflict_type] = by_type.get(case.conflict_type, 0) + 1

        return {
            "total_cases": total,
            "resolved_cases": resolved,
            "by_severity": by_severity,
            "by_source": by_source,
            "by_type": by_type
        }


# Singleton instance
conflict_arbitrator = ConflictArbitrator()
