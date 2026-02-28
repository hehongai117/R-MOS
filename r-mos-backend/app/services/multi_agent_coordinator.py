# Multi-Agent Coordinator
# Phase 6: Integration - Multi-Agent Coordination

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum
import time


class AgentType(str, Enum):
    """Agent types"""
    ORCHESTRATOR = "orchestrator"
    COACH = "coach"
    DIAGNOSER = "diagnoser"
    CURRICULUM = "curriculum"


class AgentRequest(BaseModel):
    """Request to an agent"""
    request_id: str
    agent_type: AgentType
    task_id: str
    user_id: str
    context: Dict[str, Any] = Field(default_factory=dict)
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000))


class AgentResponse(BaseModel):
    """Response from an agent"""
    request_id: str
    agent_type: AgentType
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000))


class CoordinationResult(BaseModel):
    """Result of multi-agent coordination"""
    task_id: str
    user_id: str
    final_action: Optional[Dict[str, Any]] = None
    responses: List[AgentResponse] = Field(default_factory=list)
    consensus: bool = True
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    execution_time_ms: int = 0


class ConflictType(str, Enum):
    """Types of conflicts between agents"""
    ACTION_CONFLICT = "action_conflict"
    STATE_CONFLICT = "state_conflict"
    PRIORITY_CONFLICT = "priority_conflict"
    EVIDENCE_CONFLICT = "evidence_conflict"


class Conflict(BaseModel):
    """Conflict between agents"""
    conflict_id: str
    conflict_type: ConflictType
    agent_a: AgentType
    agent_b: AgentType
    description: str
    resolution: Optional[str] = None


class MultiAgentCoordinator:
    """
    Multi-Agent Coordinator

    Responsibilities:
    - Orchestrate multiple agents (Coach, Diagnoser, Curriculum)
    - Resolve conflicts between agents
    - Ensure consensus on actions
    - Maintain SSOT (Single Source of Truth)
    """

    def __init__(self):
        # Agent instances (in production, these would be LLM-powered)
        self.agents: Dict[AgentType, Any] = {}
        self.conflicts: List[Conflict] = []
        self.task_state: Dict[str, Dict[str, Any]] = {}

    def register_agent(self, agent_type: AgentType, agent_instance: Any) -> None:
        """Register an agent"""
        self.agents[agent_type] = agent_instance

    async def coordinate(
        self,
        task_id: str,
        user_id: str,
        action: str,
        context: Dict[str, Any]
    ) -> CoordinationResult:
        """
        Coordinate multiple agents to reach consensus

        Workflow:
        1. Collect inputs from all relevant agents
        2. Detect conflicts
        3. Resolve conflicts
        4. Return final action
        """
        start_time = int(time.time() * 1000)
        responses: List[AgentResponse] = []
        conflicts: List[Conflict] = []

        # Get current state
        state = self._get_task_state(task_id)
        state["last_action"] = action

        # 1. Collect inputs based on action type
        if action == "start":
            # Start task - get curriculum agent recommendation
            curriculum_response = await self._query_agent(
                AgentType.CURRICULUM, task_id, user_id, context
            )
            responses.append(curriculum_response)

        elif action == "help":
            # Help request - get coach agent recommendation
            coach_response = await self._query_agent(
                AgentType.COACH, task_id, user_id, context
            )
            responses.append(coach_response)

        elif action == "error":
            # Error occurred - get diagnoser analysis
            diagnoser_response = await self._query_agent(
                AgentType.DIAGNOSER, task_id, user_id, context
            )
            responses.append(diagnoser_response)

            # Also get coach recommendation for intervention
            coach_response = await self._query_agent(
                AgentType.COACH, task_id, user_id, context
            )
            responses.append(coach_response)

            # Check for conflicts
            conflicts = self._detect_conflicts(diagnoser_response, coach_response)

        elif action == "step_complete":
            # Step completed - get coach recommendation for next step
            coach_response = await self._query_agent(
                AgentType.COACH, task_id, user_id, context
            )
            responses.append(coach_response)

        # 2. Resolve conflicts
        if conflicts:
            resolved = self._resolve_conflicts(conflicts, responses)
            conflicts = resolved

        # 3. Determine final action
        final_action = self._determine_final_action(responses, conflicts)

        # 4. Update state
        self._update_task_state(task_id, {
            "last_action": action,
            "last_responses": [r.agent_type.value for r in responses],
            "conflicts_resolved": len(conflicts) > 0
        })

        execution_time = int(time.time() * 1000) - start_time

        return CoordinationResult(
            task_id=task_id,
            user_id=user_id,
            final_action=final_action,
            responses=responses,
            consensus=len(conflicts) == 0,
            conflicts=[c.model_dump() for c in conflicts],
            execution_time_ms=execution_time
        )

    async def _query_agent(
        self,
        agent_type: AgentType,
        task_id: str,
        user_id: str,
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Query a specific agent"""
        request_id = f"req-{int(time.time() * 1000)}"

        request = AgentRequest(
            request_id=request_id,
            agent_type=agent_type,
            task_id=task_id,
            user_id=user_id,
            context=context
        )

        # Get agent
        agent = self.agents.get(agent_type)
        if not agent:
            return AgentResponse(
                request_id=request_id,
                agent_type=agent_type,
                success=False,
                error=f"Agent {agent_type} not registered"
            )

        # Call agent (simplified - in production would be async LLM call)
        try:
            # Simplified - would call actual agent method
            data = {"action": f"{agent_type.value}_recommendation"}
            return AgentResponse(
                request_id=request_id,
                agent_type=agent_type,
                success=True,
                data=data
            )
        except Exception as e:
            return AgentResponse(
                request_id=request_id,
                agent_type=agent_type,
                success=False,
                error=str(e)
            )

    def _detect_conflicts(
        self,
        response_a: AgentResponse,
        response_b: AgentResponse
    ) -> List[Conflict]:
        """Detect conflicts between agent responses"""
        conflicts = []

        # Example conflict detection
        action_a = response_a.data.get("action_type")
        action_b = response_b.data.get("action_type")

        if action_a and action_b and action_a != action_b:
            conflicts.append(Conflict(
                conflict_id=f"conflict-{int(time.time() * 1000)}",
                conflict_type=ConflictType.ACTION_CONFLICT,
                agent_a=response_a.agent_type,
                agent_b=response_b.agent_type,
                description=f"Action conflict: {action_a} vs {action_b}"
            ))

        return conflicts

    def _resolve_conflicts(
        self,
        conflicts: List[Conflict],
        responses: List[AgentResponse]
    ) -> List[Conflict]:
        """Resolve conflicts between agents"""
        resolved = []

        for conflict in conflicts:
            # Simple resolution strategy:
            # 1. Prioritize Diagnoser > Coach > Curriculum
            priority = {
                AgentType.DIAGNOSER: 3,
                AgentType.COACH: 2,
                AgentType.CURRICULUM: 1
            }

            agent_a_priority = priority.get(conflict.agent_a, 0)
            agent_b_priority = priority.get(conflict.agent_b, 0)

            if agent_a_priority > agent_b_priority:
                winner = conflict.agent_a
            else:
                winner = conflict.agent_b

            conflict.resolution = f"{winner.value} takes precedence"
            resolved.append(conflict)

        return resolved

    def _determine_final_action(
        self,
        responses: List[AgentResponse],
        conflicts: List[Conflict]
    ) -> Optional[Dict[str, Any]]:
        """Determine final action from responses"""
        if not responses:
            return None

        # Filter successful responses
        successful = [r for r in responses if r.success]
        if not successful:
            return {"error": "No successful responses"}

        # If no conflicts, take the most recent response
        if not conflicts:
            return successful[-1].data

        # If conflicts, use resolved winner
        for conflict in conflicts:
            if conflict.resolution:
                winner_type = conflict.resolution.split()[0]
                for r in successful:
                    if r.agent_type.value == winner_type:
                        return r.data

        return successful[0].data

    def _get_task_state(self, task_id: str) -> Dict[str, Any]:
        """Get task state"""
        if task_id not in self.task_state:
            self.task_state[task_id] = {}
        return self.task_state[task_id]

    def _update_task_state(self, task_id: str, updates: Dict[str, Any]) -> None:
        """Update task state"""
        if task_id not in self.task_state:
            self.task_state[task_id] = {}
        self.task_state[task_id].update(updates)

    def get_conflicts(self) -> List[Conflict]:
        """Get all resolved conflicts"""
        return self.conflicts

    def get_task_state(self, task_id: str) -> Dict[str, Any]:
        """Get full task state"""
        return self.task_state.get(task_id, {})


# Singleton instance
multi_agent_coordinator = MultiAgentCoordinator()
