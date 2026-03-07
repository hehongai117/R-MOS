"""
Compensation Planner Service - Phase 2 Week 7
Handles failure analysis and compensation plan generation

Provides:
- Failure analysis
- Compensation strategy selection
- Plan generation and execution tracking
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import time
import uuid


class FailureType(str, Enum):
    """Types of failures"""
    TIMEOUT = "timeout"
    ERROR = "error"
    SAFETY_VIOLATION = "safety_violation"
    RESOURCE_UNAVAILABLE = "resource_unavailable"
    USER_CANCELLED = "user_cancelled"
    DEPENDENCY_FAILED = "dependency_failed"
    VALIDATION_FAILED = "validation_failed"
    UNKNOWN = "unknown"


class CompensationStrategy(str, Enum):
    """Compensation strategies"""
    RETRY = "retry"
    ROLLBACK = "rollback"
    COMPENSATE = "compensate"
    SKIP = "skip"
    FALLBACK = "fallback"
    ESCALATE = "escalate"


class PlanStatus(str, Enum):
    """Plan execution status"""
    PENDING = "pending"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


@dataclass
class FailureRecord:
    """Record of a failure"""
    failure_id: str
    failure_type: FailureType
    message: str
    context: Dict[str, Any]
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))
    severity: str = "medium"
    root_cause: str = ""
    affected_steps: List[str] = field(default_factory=list)


@dataclass
class CompensationAction:
    """Individual compensation action"""
    action_id: str
    action_type: str
    description: str
    target_step_id: Optional[str] = None
    estimated_duration_ms: int = 0
    risk_level: str = "R1"


@dataclass
class CompensationPlan:
    """Compensation plan"""
    plan_id: str
    failure_id: str
    status: PlanStatus
    strategy: CompensationStrategy
    actions: List[CompensationAction]
    estimated_duration_ms: int
    created_at: int = field(default_factory=lambda: int(time.time() * 1000))
    approved_by: Optional[str] = None
    executed_at: Optional[int] = None


class CompensationPlanner:
    """
    Service for generating and managing compensation plans.

    Features:
    - Failure analysis
    - Strategy selection
    - Plan generation
    - Execution tracking
    """

    def __init__(self):
        self._failures: Dict[str, FailureRecord] = {}
        self._plans: Dict[str, CompensationPlan] = {}

    def analyze_failure(
        self,
        failure_type: str,
        failure_message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> FailureRecord:
        """Analyze a failure and return failure record"""
        try:
            ftype = FailureType(failure_type)
        except ValueError:
            ftype = FailureType.UNKNOWN

        # Analyze root cause and affected steps
        root_cause = self._analyze_root_cause(ftype, failure_message, context)
        affected_steps = self._identify_affected_steps(ftype, context)

        failure = FailureRecord(
            failure_id=f"fail-{uuid.uuid4().hex[:8]}",
            failure_type=ftype,
            message=failure_message,
            context=context or {},
            severity=self._calculate_severity(ftype, context),
            root_cause=root_cause,
            affected_steps=affected_steps,
        )

        self._failures[failure.failure_id] = failure
        return failure

    def _analyze_root_cause(self, failure_type: FailureType, message: str, context: Optional[Dict[str, Any]]) -> str:
        """Analyze root cause of failure"""
        cause_map = {
            FailureType.TIMEOUT: "操作超时，资源响应时间超过预期阈值",
            FailureType.ERROR: "执行过程中发生错误",
            FailureType.SAFETY_VIOLATION: "违反安全策略被强制中断",
            FailureType.RESOURCE_UNAVAILABLE: "所需资源不可用",
            FailureType.USER_CANCELLED: "用户主动取消操作",
            FailureType.DEPENDENCY_FAILED: "依赖的操作或服务失败",
            FailureType.VALIDATION_FAILED: "验证检查未通过",
            FailureType.UNKNOWN: "未知原因导致的失败",
        }
        return cause_map.get(failure_type, "未知原因")

    def _identify_affected_steps(self, failure_type: FailureType, context: Optional[Dict[str, Any]]) -> List[str]:
        """Identify affected steps based on failure type"""
        if context and "current_step" in context:
            current_step = context.get("current_step")
            return [f"step-{current_step}", f"step-{current_step + 1}"]

        # Default affected steps based on failure type
        if failure_type == FailureType.SAFETY_VIOLATION:
            return ["current_step", "all_subsequent"]
        elif failure_type == FailureType.DEPENDENCY_FAILED:
            return ["current_step", "dependent_steps"]
        return ["current_step"]

    def _calculate_severity(self, failure_type: FailureType, context: Dict[str, Any]) -> str:
        """Calculate failure severity"""
        if failure_type == FailureType.SAFETY_VIOLATION:
            return "critical"
        elif failure_type == FailureType.TIMEOUT:
            return "high"
        elif failure_type == FailureType.RESOURCE_UNAVAILABLE:
            return "medium"
        return "low"

    def generate_compensation_plan(
        self,
        failure: FailureRecord,
        preferred_strategy: Optional[str] = None,
    ) -> CompensationPlan:
        """Generate compensation plan for a failure"""
        # Determine strategy
        if preferred_strategy:
            try:
                strategy = CompensationStrategy(preferred_strategy)
            except ValueError:
                strategy = self._select_strategy(failure.failure_type)
        else:
            strategy = self._select_strategy(failure.failure_type)

        # Generate actions based on strategy
        actions = self._generate_actions(strategy, failure)

        # Calculate estimated duration
        estimated_duration = sum(a.estimated_duration_ms for a in actions)

        plan = CompensationPlan(
            plan_id=f"plan-{uuid.uuid4().hex[:8]}",
            failure_id=failure.failure_id,
            status=PlanStatus.PENDING,
            strategy=strategy,
            actions=actions,
            estimated_duration_ms=estimated_duration,
        )

        self._plans[plan.plan_id] = plan
        return plan

    def _select_strategy(self, failure_type: FailureType) -> CompensationStrategy:
        """Select compensation strategy based on failure type"""
        strategy_map = {
            FailureType.TIMEOUT: CompensationStrategy.RETRY,
            FailureType.ERROR: CompensationStrategy.COMPENSATE,
            FailureType.SAFETY_VIOLATION: CompensationStrategy.ESCALATE,
            FailureType.RESOURCE_UNAVAILABLE: CompensationStrategy.FALLBACK,
            FailureType.USER_CANCELLED: CompensationStrategy.ROLLBACK,
            FailureType.DEPENDENCY_FAILED: CompensationStrategy.RETRY,
            FailureType.VALIDATION_FAILED: CompensationStrategy.COMPENSATE,
            FailureType.UNKNOWN: CompensationStrategy.ESCALATE,
        }
        return strategy_map.get(failure_type, CompensationStrategy.ESCALATE)

    def _generate_actions(self, strategy: CompensationStrategy, failure: FailureRecord) -> List[CompensationAction]:
        """Generate compensation actions based on strategy"""
        actions = []

        if strategy == CompensationStrategy.RETRY:
            actions.append(CompensationAction(
                action_id=f"act-{uuid.uuid4().hex[:8]}",
                action_type="retry",
                description=f"重试失败操作: {failure.message}",
                estimated_duration_ms=5000,
                risk_level="R1",
            ))
        elif strategy == CompensationStrategy.ROLLBACK:
            actions.append(CompensationAction(
                action_id=f"act-{uuid.uuid4().hex[:8]}",
                action_type="rollback",
                description="回滚到上一个稳定状态",
                estimated_duration_ms=10000,
                risk_level="R2",
            ))
        elif strategy == CompensationStrategy.COMPENSATE:
            actions.append(CompensationAction(
                action_id=f"act-{uuid.uuid4().hex[:8]}",
                action_type="compensate",
                description="执行补偿操作",
                estimated_duration_ms=8000,
                risk_level="R2",
            ))
        elif strategy == CompensationStrategy.SKIP:
            actions.append(CompensationAction(
                action_id=f"act-{uuid.uuid4().hex[:8]}",
                action_type="skip",
                description="跳过当前步骤",
                estimated_duration_ms=1000,
                risk_level="R1",
            ))
        elif strategy == CompensationStrategy.FALLBACK:
            actions.append(CompensationAction(
                action_id=f"act-{uuid.uuid4().hex[:8]}",
                action_type="fallback",
                description="使用备用方案",
                estimated_duration_ms=5000,
                risk_level="R2",
            ))
        elif strategy == CompensationStrategy.ESCALATE:
            actions.append(CompensationAction(
                action_id=f"act-{uuid.uuid4().hex[:8]}",
                action_type="escalate",
                description="升级处理",
                estimated_duration_ms=0,
                risk_level="R3",
            ))

        return actions

    def get_plan(self, plan_id: str) -> Optional[CompensationPlan]:
        """Get compensation plan by ID"""
        return self._plans.get(plan_id)

    def update_plan_status(
        self,
        plan_id: str,
        status: str,
        approved_by: Optional[str] = None,
    ) -> bool:
        """Update plan status"""
        plan = self._plans.get(plan_id)
        if not plan:
            return False

        try:
            plan.status = PlanStatus(status)
        except ValueError:
            return False

        if status == "approved" and approved_by:
            plan.approved_by = approved_by
        elif status == "completed":
            plan.executed_at = int(time.time() * 1000)

        return True

    def get_failure_history(self) -> List[FailureRecord]:
        """Get failure history"""
        return list(self._failures.values())

    def get_plans_by_status(self, status: str) -> List[CompensationPlan]:
        """Get plans by status"""
        try:
            plan_status = PlanStatus(status)
        except ValueError:
            return []

        return [p for p in self._plans.values() if p.status == plan_status]


# Singleton instance
compensation_planner = CompensationPlanner()
