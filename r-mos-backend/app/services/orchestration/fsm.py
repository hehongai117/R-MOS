"""
Task FSM types: TaskFSMState, TaskEventType, TaskContext, ModuleDispatchResult.

Verbatim move from orchestrator_v2.py (Phase 3 refactor).
"""

import time
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass, field

from app.core.resource_parser import ResourceRef


class TaskFSMState(str, Enum):
    """Task FSM States"""
    IDLE = "idle"
    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskEventType(str, Enum):
    """Task FSM Events"""
    CREATE = "create"
    START = "start"
    PAUSE = "pause"
    RESUME = "resume"
    COMPLETE = "complete"
    FAIL = "fail"
    CANCEL = "cancel"
    APPROVE = "approve"
    REJECT = "reject"


@dataclass
class TaskContext:
    """Task execution context"""
    task_id: str
    user_id: str
    trace_id: str
    state: TaskFSMState = TaskFSMState.IDLE
    current_step: int = 0
    total_steps: int = 0
    skill_id: Optional[str] = None
    resource_refs: List[ResourceRef] = field(default_factory=list)
    evidence_collected: List[str] = field(default_factory=list)
    created_at: int = field(default_factory=lambda: int(time.time() * 1000))
    started_at: Optional[int] = None
    completed_at: Optional[int] = None
    budget_used_ms: int = 0
    budget_limit_ms: int = 300000  # 5 minutes default
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModuleDispatchResult:
    """Result of module dispatch"""
    module_id: str
    module_name: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    execution_time_ms: int = 0
    evidence_required: List[str] = field(default_factory=list)
