"""
Policy Matrix Service - Gate-0 Hard Gate Implementation

This module provides policy evaluation and decision-making for the agent system.
It implements the policy matrix for controlling agent actions.

Phase 0: Week 1 - Gate-0 hard gate implementation
"""

from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime


class RiskLevel(str, Enum):
    """Risk levels for agent actions"""
    R0 = "R0"  # Silent - no intervention needed
    R1 = "R1"  # Advisory - suggestion only
    R2 = "R2"  # Warning - requires acknowledgment
    R3 = "R3"  # Blocking - must be approved


class ActionCategory(str, Enum):
    """Categories of agent actions"""
    READ = "read"           # Read operations
    WRITE = "write"         # Write operations
    EXECUTE = "execute"    # Execute operations (task execution)
    DELEGATE = "delegate"   # Delegate to other agents
    ADMIN = "admin"         # Administrative operations


@dataclass
class PolicyRule:
    """A policy rule definition"""
    rule_id: str
    name: str
    description: str
    action_category: ActionCategory
    conditions: Dict[str, Any] = field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.R0
    requires_approval: bool = False
    approval_level: Optional[str] = None  # user, manager, admin
    evidence_required: List[str] = field(default_factory=list)
    enabled: bool = True


@dataclass
class PolicyDecision:
    """Result of policy evaluation"""
    allowed: bool
    risk_level: RiskLevel
    requires_approval: bool
    approval_level: Optional[str]
    evidence_required: List[str]
    conditions: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    matched_rules: List[str] = field(default_factory=list)


class PolicyMatrix:
    """
    Policy Matrix for evaluating agent actions.

    The matrix maps action types + contexts to risk levels and approval requirements.
    """

    def __init__(self):
        self._rules: Dict[str, PolicyRule] = {}
        self._initialize_default_rules()

    def _initialize_default_rules(self):
        """Initialize default policy rules"""
        default_rules = [
            # Read operations - generally low risk
            PolicyRule(
                rule_id="read-kb",
                name="Knowledge Base Read",
                description="Read from knowledge base",
                action_category=ActionCategory.READ,
                risk_level=RiskLevel.R0,
                requires_approval=False,
            ),
            PolicyRule(
                rule_id="read-task",
                name="Task Status Read",
                description="Read task status",
                action_category=ActionCategory.READ,
                risk_level=RiskLevel.R0,
                requires_approval=False,
            ),

            # Write operations - require validation
            PolicyRule(
                rule_id="write-kb",
                name="Knowledge Write",
                description="Create/update knowledge entries",
                action_category=ActionCategory.WRITE,
                risk_level=RiskLevel.R1,
                requires_approval=True,
                approval_level="manager",
                evidence_required=["content_hash", "source_ref"],
            ),
            PolicyRule(
                rule_id="write-task",
                name="Task Write",
                description="Create/update task state",
                action_category=ActionCategory.WRITE,
                risk_level=RiskLevel.R2,
                requires_approval=False,
                evidence_required=["task_id", "user_id"],
            ),
            PolicyRule(
                rule_id="plan-task",
                name="Task Planning",
                description="Generate a maintenance dispatch plan without executing robot actions",
                action_category=ActionCategory.READ,
                risk_level=RiskLevel.R1,
                requires_approval=False,
            ),

            # Execute operations - high risk
            PolicyRule(
                rule_id="execute-task",
                name="Task Execution",
                description="Execute robot task",
                action_category=ActionCategory.EXECUTE,
                risk_level=RiskLevel.R3,
                requires_approval=True,
                approval_level="manager",
                evidence_required=["task_id", "sop_id", "safety_check"],
            ),
            PolicyRule(
                rule_id="execute-robot",
                name="Robot Control",
                description="Direct robot control",
                action_category=ActionCategory.EXECUTE,
                risk_level=RiskLevel.R3,
                requires_approval=True,
                approval_level="admin",
                evidence_required=["robot_id", "command_hash", "safety_check"],
            ),

            # Delegation - medium risk
            PolicyRule(
                rule_id="delegate-coach",
                name="Coach Delegation",
                description="Delegate to coach agent",
                action_category=ActionCategory.DELEGATE,
                risk_level=RiskLevel.R1,
                requires_approval=False,
            ),
            PolicyRule(
                rule_id="delegate-diagnoser",
                name="Diagnoser Delegation",
                description="Delegate to diagnoser agent",
                action_category=ActionCategory.DELEGATE,
                risk_level=RiskLevel.R1,
                requires_approval=False,
            ),

            # Admin operations - highest risk
            PolicyRule(
                rule_id="admin-skill",
                name="Skill Management",
                description="Create/update skills",
                action_category=ActionCategory.ADMIN,
                risk_level=RiskLevel.R2,
                requires_approval=True,
                approval_level="admin",
                evidence_required=["skill_id", "review_id"],
            ),
            PolicyRule(
                rule_id="admin-policy",
                name="Policy Management",
                description="Modify policy rules",
                action_category=ActionCategory.ADMIN,
                risk_level=RiskLevel.R3,
                requires_approval=True,
                approval_level="admin",
                evidence_required=["audit_log"],
            ),
        ]

        for rule in default_rules:
            self._rules[rule.rule_id] = rule

    def evaluate(
        self,
        action: str,
        context: Dict[str, Any],
        user_role: str = "user"
    ) -> PolicyDecision:
        """
        Evaluate an action against the policy matrix.

        Args:
            action: Action identifier
            context: Action context including resource refs, etc.
            user_role: Role of the user making the request

        Returns:
            PolicyDecision with evaluation results
        """
        # Find matching rules
        matched_rules: List[PolicyRule] = []

        for rule in self._rules.values():
            if not rule.enabled:
                continue

            # Check if action matches rule
            if self._action_matches_rule(action, rule):
                # Check conditions
                if self._check_conditions(rule.conditions, context):
                    matched_rules.append(rule)

        if not matched_rules:
            # Default allow for unknown actions
            return PolicyDecision(
                allowed=True,
                risk_level=RiskLevel.R0,
                requires_approval=False,
                approval_level=None,
                evidence_required=[],
                warnings=["No matching policy rule found, default allow"]
            )

        # Get highest risk level from matched rules
        risk_order = [RiskLevel.R0, RiskLevel.R1, RiskLevel.R2, RiskLevel.R3]
        max_risk = max(matched_rules, key=lambda r: risk_order.index(r.risk_level)).risk_level

        # Check if any rule requires approval
        requires_approval = any(r.requires_approval for r in matched_rules)

        # Determine approval level (highest required)
        approval_levels = ["user", "manager", "admin"]
        approval_level = None
        if requires_approval:
            required_levels = [r.approval_level for r in matched_rules if r.approval_level]
            if required_levels:
                approval_level = max(required_levels, key=lambda x: approval_levels.index(x))

        # Collect evidence requirements
        evidence_required = []
        for rule in matched_rules:
            for ev in rule.evidence_required:
                if ev not in evidence_required:
                    evidence_required.append(ev)

        # Determine if allowed based on risk level and approval
        allowed = True
        warnings = []

        if max_risk == RiskLevel.R3 and user_role not in ["admin", "manager"]:
            allowed = False
            warnings.append("R3 risk level requires admin or manager approval")

        return PolicyDecision(
            allowed=allowed,
            risk_level=max_risk,
            requires_approval=requires_approval,
            approval_level=approval_level,
            evidence_required=evidence_required,
            matched_rules=[r.rule_id for r in matched_rules]
        )

    def _action_matches_rule(self, action: str, rule: PolicyRule) -> bool:
        """Check if action matches rule"""
        # Exact match
        if action == rule.rule_id:
            return True

        # Category match
        action_category = self._get_action_category(action)
        if action_category == rule.action_category:
            return True

        # Prefix match
        if action.startswith(rule.rule_id.split("-")[0]):
            return True

        return False

    def _get_action_category(self, action: str) -> Optional[ActionCategory]:
        """Infer action category from action name"""
        action_lower = action.lower()

        if any(kw in action_lower for kw in ["read", "get", "search", "list"]):
            return ActionCategory.READ
        elif any(kw in action_lower for kw in ["create", "update", "write", "delete"]):
            return ActionCategory.WRITE
        elif any(kw in action_lower for kw in ["execute", "run", "start", "stop"]):
            return ActionCategory.EXECUTE
        elif any(kw in action_lower for kw in ["delegate", "coach", "diagnose"]):
            return ActionCategory.DELEGATE
        elif any(kw in action_lower for kw in ["admin", "manage", "config"]):
            return ActionCategory.ADMIN

        return None

    def _check_conditions(self, conditions: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Check if conditions match context"""
        if not conditions:
            return True

        for key, expected in conditions.items():
            if key not in context:
                return False
            if context[key] != expected:
                return False

        return True

    def add_rule(self, rule: PolicyRule):
        """Add a new policy rule"""
        self._rules[rule.rule_id] = rule

    def remove_rule(self, rule_id: str):
        """Remove a policy rule"""
        if rule_id in self._rules:
            del self._rules[rule_id]

    def enable_rule(self, rule_id: str):
        """Enable a policy rule"""
        if rule_id in self._rules:
            self._rules[rule_id].enabled = True

    def disable_rule(self, rule_id: str):
        """Disable a policy rule"""
        if rule_id in self._rules:
            self._rules[rule_id].enabled = False

    def get_rules(self) -> List[PolicyRule]:
        """Get all policy rules"""
        return list(self._rules.values())


# Singleton instance
policy_matrix = PolicyMatrix()
