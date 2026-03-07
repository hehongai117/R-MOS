"""
BeliefState Service - Phase 2 Week 6
Agent belief state management for state estimation and tracking

Manages the agent's belief about:
- Current task state
- World model (robot state, environment)
- User intent
- Evidence collected
"""

from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import time
import uuid


class BeliefConfidence(str, Enum):
    """Confidence levels for beliefs"""
    VERY_LOW = "very_low"      # 0-25%
    LOW = "low"                # 25-50%
    MEDIUM = "medium"          # 50-75%
    HIGH = "high"              # 75-90%
    VERY_HIGH = "very_high"    # 90-100%


class BeliefSource(str, Enum):
    """Source of belief"""
    USER_INPUT = "user_input"
    OBSERVATION = "observation"
    INFERENCE = "inference"
    TOOL_RESULT = "tool_result"
    COACH_ADVICE = "coach_advice"


@dataclass
class Belief:
    """Single belief item"""
    id: str
    category: str  # task_state, world_model, user_intent, evidence
    proposition: str  # The belief statement
    confidence: BeliefConfidence
    confidence_value: float  # 0.0 - 1.0
    source: BeliefSource
    evidence_refs: List[str] = field(default_factory=list)
    created_at: int = field(default_factory=lambda: int(time.time() * 1000))
    updated_at: int = field(default_factory=lambda: int(time.time() * 1000))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorldModel:
    """World model - agent's understanding of the environment"""
    robot_state: Dict[str, Any] = field(default_factory=dict)
    environment_state: Dict[str, Any] = field(default_factory=dict)
    task_progress: Dict[str, Any] = field(default_factory=dict)
    last_update: int = field(default_factory=lambda: int(time.time() * 1000))


class BeliefState:
    """
    Belief State Manager for the agent.

    Maintains the agent's belief state including:
    - Task beliefs
    - World model
    - User intent beliefs
    - Evidence tracking
    """

    def __init__(self, trace_id: str):
        self.trace_id = trace_id
        self._beliefs: Dict[str, Belief] = {}  # belief_id -> Belief
        self._beliefs_by_category: Dict[str, Set[str]] = {}  # category -> set of belief_ids
        self._world_model = WorldModel()
        self._revision_history: List[Dict[str, Any]] = []
        self._last_revision = 0

    def add_belief(
        self,
        category: str,
        proposition: str,
        confidence: BeliefConfidence,
        confidence_value: float,
        source: BeliefSource,
        evidence_refs: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add a new belief"""
        belief_id = f"belief-{uuid.uuid4().hex[:8]}"

        belief = Belief(
            id=belief_id,
            category=category,
            proposition=proposition,
            confidence=confidence,
            confidence_value=confidence_value,
            source=source,
            evidence_refs=evidence_refs or [],
            metadata=metadata or {},
        )

        self._beliefs[belief_id] = belief

        # Index by category
        if category not in self._beliefs_by_category:
            self._beliefs_by_category[category] = set()
        self._beliefs_by_category[category].add(belief_id)

        # Record revision
        self._record_revision("add", belief_id)

        return belief_id

    def update_belief(
        self,
        belief_id: str,
        proposition: Optional[str] = None,
        confidence: Optional[BeliefConfidence] = None,
        confidence_value: Optional[float] = None,
        evidence_refs: Optional[List[str]] = None,
    ) -> bool:
        """Update an existing belief"""
        if belief_id not in self._beliefs:
            return False

        belief = self._beliefs[belief_id]

        if proposition:
            belief.proposition = proposition
        if confidence:
            belief.confidence = confidence
        if confidence_value is not None:
            belief.confidence_value = confidence_value
        if evidence_refs:
            belief.evidence_refs = evidence_refs

        belief.updated_at = int(time.time() * 1000)

        # Record revision
        self._record_revision("update", belief_id)

        return True

    def remove_belief(self, belief_id: str) -> bool:
        """Remove a belief"""
        if belief_id not in self._beliefs:
            return False

        belief = self._beliefs[belief_id]

        # Remove from category index
        category = belief.category
        if category in self._beliefs_by_category:
            self._beliefs_by_category[category].discard(belief_id)

        # Remove belief
        del self._beliefs[belief_id]

        # Record revision
        self._record_revision("remove", belief_id)

        return True

    def get_belief(self, belief_id: str) -> Optional[Belief]:
        """Get a belief by ID"""
        return self._beliefs.get(belief_id)

    def get_beliefs_by_category(self, category: str) -> List[Belief]:
        """Get all beliefs in a category"""
        belief_ids = self._beliefs_by_category.get(category, set())
        return [self._beliefs[bid] for bid in belief_ids if bid in self._beliefs]

    def get_all_beliefs(self) -> List[Belief]:
        """Get all beliefs"""
        return list(self._beliefs.values())

    def get_belief_summary(self) -> Dict[str, Any]:
        """Get summary of all beliefs"""
        summary = {
            "trace_id": self.trace_id,
            "total_beliefs": len(self._beliefs),
            "by_category": {},
            "by_confidence": {},
            "by_source": {},
            "world_model": {
                "robot_state": self._world_model.robot_state,
                "task_progress": self._world_model.task_progress,
                "last_update": self._world_model.last_update,
            },
        }

        # Count by category
        for category, belief_ids in self._beliefs_by_category.items():
            summary["by_category"][category] = len(belief_ids)

        # Count by confidence
        for belief in self._beliefs.values():
            conf = belief.confidence.value
            summary["by_confidence"][conf] = summary["by_confidence"].get(conf, 0) + 1

        # Count by source
        for belief in self._beliefs.values():
            src = belief.source.value
            summary["by_source"][src] = summary["by_source"].get(src, 0) + 1

        return summary

    def update_world_model(
        self,
        robot_state: Optional[Dict[str, Any]] = None,
        environment_state: Optional[Dict[str, Any]] = None,
        task_progress: Optional[Dict[str, Any]] = None,
    ):
        """Update the world model"""
        if robot_state:
            self._world_model.robot_state.update(robot_state)
        if environment_state:
            self._world_model.environment_state.update(environment_state)
        if task_progress:
            self._world_model.task_progress.update(task_progress)

        self._world_model.last_update = int(time.time() * 1000)

        # Record revision
        self._record_revision("world_model_update", None)

    def get_world_model(self) -> WorldModel:
        """Get current world model"""
        return self._world_model

    def get_low_confidence_beliefs(self, threshold: float = 0.5) -> List[Belief]:
        """Get beliefs with confidence below threshold"""
        return [
            b for b in self._beliefs.values()
            if b.confidence_value < threshold
        ]

    def resolve_conflicts(self) -> List[Dict[str, Any]]:
        """Resolve conflicts between beliefs"""
        conflicts = []

        # Get beliefs by category
        for category, belief_ids in self._beliefs_by_category.items():
            beliefs = [self._beliefs[bid] for bid in belief_ids if bid in self._beliefs]

            # Simple conflict detection: same proposition from different sources
            propositions: Dict[str, List[Belief]] = {}
            for belief in beliefs:
                prop = belief.proposition
                if prop not in propositions:
                    propositions[prop] = []
                propositions[prop].append(belief)

            # Check for conflicts
            for prop, same_prop_beliefs in propositions.items():
                if len(same_prop_beliefs) > 1:
                    # Different confidence levels
                    confidences = set((b.confidence, b.confidence_value) for b in same_prop_beliefs)
                    if len(confidences) > 1:
                        conflicts.append({
                            "type": "confidence_conflict",
                            "proposition": prop,
                            "beliefs": [
                                {
                                    "id": b.id,
                                    "confidence": b.confidence.value,
                                    "confidence_value": b.confidence_value,
                                    "source": b.source.value,
                                }
                                for b in same_prop_beliefs
                            ],
                        })

        return conflicts

    def _record_revision(self, action: str, belief_id: Optional[str]):
        """Record a revision in history"""
        self._last_revision += 1
        self._revision_history.append({
            "revision_id": self._last_revision,
            "action": action,
            "belief_id": belief_id,
            "timestamp": int(time.time() * 1000),
        })

    def get_revision_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get revision history"""
        return self._revision_history[-limit:]

    def serialize(self) -> Dict[str, Any]:
        """Serialize belief state"""
        return {
            "trace_id": self.trace_id,
            "beliefs": [b.__dict__ for b in self._beliefs.values()],
            "world_model": {
                "robot_state": self._world_model.robot_state,
                "environment_state": self._world_model.environment_state,
                "task_progress": self._world_model.task_progress,
                "last_update": self._world_model.last_update,
            },
            "revision_count": self._last_revision,
        }


# In-memory store for belief states
_belief_states: Dict[str, BeliefState] = {}


def get_or_create_belief_state(trace_id: str) -> BeliefState:
    """Get or create a belief state for a trace"""
    if trace_id not in _belief_states:
        _belief_states[trace_id] = BeliefState(trace_id)
    return _belief_states[trace_id]


def get_belief_state(trace_id: str) -> Optional[BeliefState]:
    """Get a belief state by trace ID"""
    return _belief_states.get(trace_id)
