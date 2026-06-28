"""
Agent API Schemas
Inline Pydantic models extracted from app/api/v1/endpoints/agent.py (Phase 3 refactor).
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import enum

from app.schemas.report import LLMEvaluationReport


class CoachRecommendRequest(BaseModel):
    task_id: str
    current_step: int
    step_history: List[Dict[str, Any]] = Field(default_factory=list)
    trainee_action: Optional[Dict[str, Any]] = None


class DiagnoseRequest(BaseModel):
    task_id: str
    error_history: List[Dict[str, Any]] = Field(default_factory=list)
    action_history: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)


class KnowledgeSearchRequest(BaseModel):
    query: str = ""
    device_model: Optional[str] = None
    part_type: Optional[str] = None
    status: Optional[str] = "APPROVED"


class KnowledgeCreateRequest(BaseModel):
    title: str
    content: str
    type: str = "solution"
    scope: Optional[Dict[str, Any]] = None
    risk_level: str = "R1"


class KnowledgeApproveRequest(BaseModel):
    decision: str  # approve, reject
    feedback: str = ""
    rating: Optional[float] = None


class CoordinateRequest(BaseModel):
    task_id: str
    user_id: str
    action: str
    context: Dict[str, Any] = Field(default_factory=dict)


class EvidenceCollectRequest(BaseModel):
    step_id: str
    evidence_id: str
    evidence_type: str


class AgentExecuteMode(str, enum.Enum):
    """Execution mode for unified agent endpoint"""
    COMMAND = "command"
    MESSAGE = "message"
    AUTO = "auto"         # Auto-detect based on input


class AgentExecuteRequest(BaseModel):
    """Unified Agent Execute Request - P2-1 Convergence

    Supports both command-style and message-style invocation.
    """
    # Common fields
    user_id: str
    mode: AgentExecuteMode = Field(default=AgentExecuteMode.AUTO, description="Execution mode: command|message|auto")

    # Command mode fields
    intent: Optional[str] = Field(default=None, description="Command intent")
    tool_name: Optional[str] = Field(default=None, description="Tool to execute")
    tool_args: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    skill_id: Optional[str] = Field(default=None, description="Skill ID")
    side_effects: List[str] = Field(default_factory=list, description="Side effects")
    input_text: Optional[str] = Field(default=None, description="Input text for command")

    # Message mode fields
    message: Optional[str] = Field(default=None, description="Natural language message")

    # Shared fields
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    resource_ref: Optional[Dict[str, Any]] = Field(default=None, description="Resource reference")
    policy_context: Optional[Dict[str, Any]] = Field(default=None, description="Policy context")
    intent_classification: Optional[str] = Field(default=None, description="Pre-classified intent")
    telemetry_payload: Optional[Dict[str, Any]] = Field(default=None, description="Telemetry payload for diagnosis flows")
    trace_id: Optional[str] = Field(default=None, description="Trace ID for replay")
    idempotency_key: Optional[str] = Field(default=None, description="Idempotency key")

    class Config:
        json_schema_extra = {
            "examples": [
                # Command mode example
                {
                    "mode": "command",
                    "user_id": "user-123",
                    "intent": "dispatch",
                    "tool_name": "assignments.create_draft",
                    "skill_id": "teaching.dispatch.draft",
                    "tool_args": {"input_text": "Create a task for robot arm maintenance"},
                    "side_effects": ["assignments.write"],
                },
                # Message mode example
                {
                    "mode": "message",
                    "user_id": "user-123",
                    "message": "Help me with the current maintenance task",
                    "context": {"task_id": "task-456"},
                },
            ]
        }


class AgentExecuteResponse(BaseModel):
    """Unified Agent Execute Response"""
    status: str = Field(description="Execution status: success|pending_approval|error")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Execution result")
    trace_id: str = Field(description="Trace ID for this execution")
    from_cache: bool = Field(default=False, description="Whether result was from cache")
    approval_id: Optional[int] = Field(default=None, description="Approval ID if pending")
    mode_used: str = Field(description="Actual mode used: command|message")


class DiagnosisTraceActionRequest(BaseModel):
    action: str = Field(..., description="Action name: confirm_execution | escalate_to_teacher")


class DiagnosisTraceActionResponse(BaseModel):
    trace_id: str
    action: str
    message: str
    recorded: bool = True


class CreateApprovalRequest(BaseModel):
    """Request to create approval"""
    requester_id: str
    resource_type: str
    resource_id: str
    action: str
    reason: str
    priority: str = "normal"
    evidence_refs: Optional[List[str]] = None
    ttl_seconds: Optional[int] = None


class GenerateReportRequest(BaseModel):
    """Request to generate evaluation report"""
    task_id: int
    use_llm: bool = Field(default=True, description="Whether to use LLM for narrative")


class GenerateReportResponse(BaseModel):
    """Response for evaluation report generation"""
    report: LLMEvaluationReport
    bundle_id: Optional[str] = Field(default=None, description="Evidence bundle ID if saved")


class SOPQualityCheckRequest(BaseModel):
    """Request to check SOP quality"""
    sop_id: Optional[int] = Field(default=None, description="Specific SOP ID to check")
    time_range_days: int = Field(default=30, description="Time range in days")


class SOPQualityCheckResponse(BaseModel):
    """Response for SOP quality check"""
    alerts: List[Dict[str, Any]]
    tickets_created: List[Dict[str, Any]]


class GuidanceModeRequest(BaseModel):
    """Request to update guidance mode"""
    mode: str = Field(..., description="Guidance mode: full_time | on_demand | silent")


class LLMPreferenceRequest(BaseModel):
    """Request to update user-level LLM settings."""
    provider: str = Field(..., min_length=1, description="LLM provider, e.g. openai")
    model: str = Field(..., min_length=1, description="Model name")
    base_url: str = Field(..., min_length=1, description="Provider base URL")
    api_key: Optional[str] = Field(default=None, description="User-specific API key")


class UserPreferenceResponse(BaseModel):
    """User preference response"""
    user_id: int
    guidance_mode: str
    guidance_mode_display: str
    preferences: Dict[str, Any]
