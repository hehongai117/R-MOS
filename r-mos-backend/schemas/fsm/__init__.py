# FSM Schema Definitions
# Version: 1.0.0

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class FSMState(str, Enum):
    """Task FSM states"""
    READY = "READY"
    EXECUTING = "EXECUTING"
    PAUSED = "PAUSED"
    WAITING_CONFIRM = "WAITING_CONFIRM"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"


class TaskEvent(str, Enum):
    """Task FSM events"""
    START = "start"
    STEP_COMPLETE = "step_complete"
    ERROR = "error"
    SKIP_STEP = "skip_step"
    FORCE_CONTINUE = "force_continue"
    EVIDENCE_MISSING = "evidence_missing"
    RISK_ESCALATE = "risk_escalate"
    PAUSE_REQUEST = "pause_request"
    RESUME = "resume"
    ROLLBACK = "rollback"
    ABORT = "abort"
    COMPLETE = "complete"


class Actor(str, Enum):
    """Who can trigger events"""
    TRAINEE = "trainee"
    ENGINEER = "engineer"
    INSTRUCTOR = "instructor"
    SYSTEM = "system"


class EventSource(str, Enum):
    """Where events originate"""
    D3 = "3d"
    RULE = "rule"
    TOOL = "tool"
    UI = "ui"
    AGENT = "agent"


class RiskLevel(str, Enum):
    """Risk levels"""
    R0 = "R0"  # No risk
    R1 = "R1"  # Low risk
    R2 = "R2"  # Medium risk
    R3 = "R3"  # High risk


class FSMTaskEvent(BaseModel):
    """FSM Task Event"""
    event_id: str = Field(..., description="Unique event ID")
    event_sequence: int = Field(..., description="Sequential event number")

    task_id: str
    step_id: Optional[str] = None
    action_id: Optional[str] = None

    fsm_state_before: FSMState
    fsm_state_after: FSMState

    plan_version: int = Field(default=1, description="Task plan version")
    fsm_version: int = Field(default=1, description="FSM definition version")

    actor: str = Field(..., description="trainee|engineer|instructor|system")
    source: str = Field(..., description="3d|rule|tool|ui|agent")

    timestamp_client: int
    timestamp_server: int

    payload: dict = Field(default_factory=dict)

    schema_version: str = Field(default="1.0.0", description="This schema version")


class Action(BaseModel):
    """Action primitive for task execution"""
    id: str
    type: str  # select_tool, remove_screw, detach_part, inspect, verify

    # Target (what the action operates on)
    target: Optional[str] = None
    targets: list[str] = Field(default_factory=list)

    # Preconditions (requirements before action can execute)
    preconditions: dict = Field(default_factory=dict)

    # Postconditions (expected state after action completes)
    postconditions: dict = Field(default_factory=dict)

    # Rollback
    rollback_to: str = ""
    rollback_checkpoint_id: Optional[str] = None

    # Risk management
    risk_level: str = "R1"  # R0, R1, R2, R3
    risk_handling: str = "warn"  # block, warn, confirm, demo

    # Tools (whitelist)
    allowed_tools: list[str] = Field(default_factory=list)

    # Evidence requirements
    evidence_required: list[str] = Field(default_factory=list)
    evidence_produced: list[str] = Field(default_factory=list)

    schema_version: str = Field(default="1.0.0")
