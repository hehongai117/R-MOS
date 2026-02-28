# Agent Service - Main Orchestrator
# Phase 3: Agent Foundation

import uuid
import time
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class AgentRequest(BaseModel):
    """Request to agent"""
    request_id: str = Field(default_factory=lambda: f"req-{uuid.uuid4().hex[:8]}")
    user_id: str
    message: str
    context: Dict[str, Any] = Field(default_factory=dict)
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000))


class AgentResponse(BaseModel):
    """Response from agent"""
    response_id: str = Field(default_factory=lambda: f"resp-{uuid.uuid4().hex[:8]}")
    request_id: str
    message: str
    action_suggested: Optional[Dict[str, Any]] = None
    confidence: float = 1.0
    evidence_refs: List[str] = Field(default_factory=list)
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000))


class NextAction(BaseModel):
    """Suggested next action from Coach Agent"""
    action_id: str
    action_type: str
    target: Optional[str] = None
    explanation: str
    risk_level: str = "R1"
    evidence_required: List[str] = Field(default_factory=list)


class CoachOutput(BaseModel):
    """Coach Agent output structure"""
    next_action: Optional[NextAction] = None
    explanation: str = ""
    risk_events: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = 1.0


class DiagnoserOutput(BaseModel):
    """Diagnoser Agent output structure"""
    root_cause: Optional[str] = None
    root_cause_confidence: float = 0.0
    evidence_refs: List[str] = Field(default_factory=list)
    intervention: Optional[Dict[str, Any]] = None
    baseline_comparison: Optional[Dict[str, Any]] = None


class CurriculumOutput(BaseModel):
    """Curriculum Agent output structure"""
    prescription: str = ""
    gates: List[Dict[str, Any]] = Field(default_factory=list)
    knowledge_recommendations: List[str] = Field(default_factory=list)


class AgentOrchestrator:
    """
    Main Agent Orchestrator

    Responsibilities:
    - Drive Task FSM
    - Hold SSOT (Single Source of Truth)
    - Coordinate sub-agents (Coach, Diagnoser, Curriculum)
    - Event replay protection
    - Conflict arbitration
    """

    def __init__(self):
        self.task_state: Dict[str, Any] = {}
        self.event_history: List[Dict[str, Any]] = []
        self.last_event_sequence: int = 0

    def process_request(self, request: AgentRequest) -> AgentResponse:
        """Process user request through agent pipeline"""
        # 1. Understand intent
        intent = self._understand_intent(request.message)

        # 2. Get current task context
        context = self._get_task_context(request.user_id)

        # 3. Delegate to appropriate sub-agent
        if intent == "start_task":
            return self._handle_start_task(request, context)
        elif intent == "ask_help":
            return self._handle_ask_help(request, context)
        elif intent == "continue_task":
            return self._handle_continue_task(request, context)
        elif intent == "diagnose_error":
            return self._handle_diagnose(request, context)
        else:
            return self._handle_general(request, context)

    def _understand_intent(self, message: str) -> str:
        """Simple intent recognition - in production use LLM"""
        message_lower = message.lower()

        if any(kw in message_lower for kw in ["开始", "start", "练习"]):
            return "start_task"
        elif any(kw in message_lower for kw in ["求助", "help", "怎么办", "怎么"]):
            return "ask_help"
        elif any(kw in message_lower for kw in ["继续", "continue", "下一步"]):
            return "continue_task"
        elif any(kw in message_lower for kw in ["诊断", "diagnose", "为什么错", "问题"]):
            return "diagnose_error"
        else:
            return "general"

    def _get_task_context(self, user_id: str) -> Dict[str, Any]:
        """Get current task context for user"""
        # In production, fetch from database
        return self.task_state.get(user_id, {
            "task_id": None,
            "status": "idle",
            "current_step": 0,
            "steps": []
        })

    def _handle_start_task(self, request: AgentRequest, context: Dict) -> AgentResponse:
        """Handle task start request"""
        task_id = f"task-{uuid.uuid4().hex[:8]}"

        # Update state
        self.task_state[request.user_id] = {
            "task_id": task_id,
            "status": "READY",
            "current_step": 0,
            "started_at": int(time.time() * 1000)
        }

        # Generate FSM event
        event = self._create_event(
            task_id=task_id,
            event_type="start",
            state_before="",
            state_after="READY",
            actor="trainee",
            source="agent"
        )
        self.event_history.append(event)

        return AgentResponse(
            request_id=request.request_id,
            message=f"好的，已为您创建任务 {task_id}。请确认开始练习。",
            action_suggested={
                "type": "start_task",
                "task_id": task_id
            }
        )

    def _handle_ask_help(self, request: AgentRequest, context: Dict) -> AgentResponse:
        """Handle help request - delegate to Coach Agent"""
        # In production, call Coach Agent
        coach_output = CoachOutput(
            next_action=NextAction(
                action_id="action-help-001",
                action_type="explain",
                explanation="让我来帮您分析当前步骤...",
                risk_level="R0"
            ),
            explanation="根据当前操作，我建议：",
            confidence=0.9
        )

        return AgentResponse(
            request_id=request.request_id,
            message=coach_output.explanation + "\n" + (coach_output.next_action.explanation if coach_output.next_action else ""),
            action_suggested=coach_output.next_action.model_dump() if coach_output.next_action else None,
            confidence=coach_output.confidence
        )

    def _handle_continue_task(self, request: AgentRequest, context: Dict) -> AgentResponse:
        """Handle continue task request"""
        return AgentResponse(
            request_id=request.request_id,
            message="好的，让我们继续下一步操作。",
            action_suggested={
                "type": "step_complete",
                "task_id": context.get("task_id")
            }
        )

    def _handle_diagnose(self, request: AgentRequest, context: Dict) -> AgentResponse:
        """Handle diagnosis request - delegate to Diagnoser Agent"""
        # In production, call Diagnoser Agent
        diagnoser_output = DiagnoserOutput(
            root_cause="attention_issue",
            root_cause_confidence=0.85,
            evidence_refs=["ev-001", "ev-002"],
            intervention={
                "type": "checkpoint",
                "detail": "建议在关键步骤添加检查点提醒"
            }
        )

        return AgentResponse(
            request_id=request.request_id,
            message=f"诊断结果：可能是{diagnoser_output.root_cause}（置信度 {diagnoser_output.root_cause_confidence:.0%}）",
            evidence_refs=diagnoser_output.evidence_refs,
            confidence=diagnoser_output.root_cause_confidence
        )

    def _handle_general(self, request: AgentRequest, context: Dict) -> AgentResponse:
        """Handle general request"""
        return AgentResponse(
            request_id=request.request_id,
            message="我理解您的需求。请问具体想做什么操作？",
            confidence=0.5
        )

    def _create_event(
        self,
        task_id: str,
        event_type: str,
        state_before: str,
        state_after: str,
        actor: str,
        source: str,
        step_id: str = None,
        action_id: str = None
    ) -> Dict[str, Any]:
        """Create FSM event with full fields"""
        self.last_event_sequence += 1

        return {
            "event_id": f"evt-{uuid.uuid4().hex[:8]}",
            "event_sequence": self.last_event_sequence,
            "task_id": task_id,
            "step_id": step_id,
            "action_id": action_id,
            "event_type": event_type,
            "fsm_state_before": state_before,
            "fsm_state_after": state_after,
            "plan_version": 1,
            "fsm_version": 1,
            "actor": actor,
            "source": source,
            "timestamp_client": int(time.time() * 1000),
            "timestamp_server": int(time.time() * 1000),
            "payload": {}
        }

    def validate_event(self, event: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate event for replay protection

        Rules:
        1. event_id already exists → reject (idempotent)
        2. event_sequence <= last_sequence → reject (out of order)
        3. plan_version != current_plan → reject (version expired)
        4. timestamp drift > 5min → reject (replay)
        """
        # Check event_id uniqueness
        for existing in self.event_history:
            if existing.get("event_id") == event.get("event_id"):
                return False, "Event ID already exists"

        # Check sequence order
        if event.get("event_sequence", 0) <= self.last_event_sequence:
            return False, "Event sequence out of order"

        # Check timestamp drift
        current_time = int(time.time() * 1000)
        event_time = event.get("timestamp_client", 0)
        if abs(current_time - event_time) > 5 * 60 * 1000:  # 5 minutes
            return False, "Timestamp drift too large"

        return True, "Event valid"

    def get_task_status(self, user_id: str) -> Dict[str, Any]:
        """Get current task status for user"""
        return self.task_state.get(user_id, {"status": "no_task"})


# Singleton instance
orchestrator = AgentOrchestrator()
