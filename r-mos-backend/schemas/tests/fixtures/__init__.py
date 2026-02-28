# Test Fixtures
# Version: 1.0.0

from schemas.fsm import FSMTaskEvent, FSMState, Action
from schemas.evidence import Evidence, EvidenceChainValidator
import time

# Valid FSM Event fixture
VALID_EVENT = FSMTaskEvent(
    event_id="evt-001",
    event_sequence=1,
    task_id="task-001",
    fsm_state_before=FSMState.READY,
    fsm_state_after=FSMState.EXECUTING,
    plan_version=1,
    fsm_version=1,
    actor="trainee",
    source="ui",
    timestamp_client=int(time.time() * 1000),
    timestamp_server=int(time.time() * 1000),
    payload={},
    schema_version="1.0.0"
)

# Valid Evidence chain fixture
VALID_EVIDENCE_CHAIN = [
    Evidence(
        id="ev-001",
        task_id="task-001",
        step_id="step-001",
        action_id="action-001",
        type="trajectory",
        hash_prev="",
        hash_content="abc123",
        signature="sig-001",
        timestamp_server=int(time.time() * 1000),
        schema_version="1.0.0"
    ),
    Evidence(
        id="ev-002",
        task_id="task-001",
        step_id="step-001",
        action_id="action-002",
        type="sensor_reading",
        hash_prev="abc123",
        hash_content="def456",
        signature="sig-002",
        timestamp_server=int(time.time() * 1000),
        schema_version="1.0.0"
    ),
]

# BROKEN CHAIN - hash_prev does not match previous hash_content
BROKEN_EVIDENCE_CHAIN = [
    Evidence(
        id="ev-001",
        task_id="task-001",
        step_id="step-001",
        action_id="action-001",
        type="trajectory",
        hash_prev="",
        hash_content="abc123",
        signature="sig-001",
        timestamp_server=int(time.time() * 1000),
        schema_version="1.0.0"
    ),
    Evidence(
        id="ev-002",
        task_id="task-001",
        step_id="step-001",
        action_id="action-002",
        type="sensor_reading",
        hash_prev="WRONG_HASH",  # <-- This breaks the chain!
        hash_content="def456",
        signature="sig-002",
        timestamp_server=int(time.time() * 1000),
        schema_version="1.0.0"
    ),
]

# Action fixture
VALID_ACTION = Action(
    id="action-001",
    type="select_tool",
    preconditions={"tool_allowed": ["screwdriver_M3"]},
    postconditions={"evidence_produced": ["tool_selection"]},
    rollback_to="checkpoint-001",
    risk_level="R1",
    risk_handling="warn",
    schema_version="1.0.0"
)
