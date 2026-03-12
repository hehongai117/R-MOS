"""
OrchestratorV2 - Phase 1 Week 3
Agent Orchestrator with module dispatching, state machine, idempotency, and budget control

This is a major upgrade from the original AgentOrchestrator, providing:
- Module-based skill dispatching
- Task FSM (Finite State Machine)
- Idempotency control
- Budget control
- Policy evaluation integration
"""

import uuid
import time
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from dataclasses import asdict, dataclass, field, is_dataclass

from app.adapters.factory import AdapterFactory
from app.core.resource_parser import resource_parser, ResourceRef, ResourceBindingResult
from app.services.diagnosis.fault_diagnosis_engine import diagnosis_engine
from app.services.diagnosis.maintenance_plan_generator import maintenance_plan_generator
from app.services.policy_matrix import policy_matrix, PolicyDecision, RiskLevel, ActionCategory
from app.services.intent import intent_engine, IntentScene
from app.services.llm.telemetry_context_builder import TelemetryContextBuilder
from app.services.simulation.simulation_executor import SimulationExecutor
from app.services.knowledge_governance import KnowledgeSearchQuery, KnowledgeStatus, knowledge_governance


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


class ModuleRegistry:
    """Registry for skill modules"""

    def __init__(self):
        self._modules: Dict[str, Callable] = {}
        self._module_metadata: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        module_id: str,
        module_name: str,
        handler: Callable,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Register a skill module"""
        self._modules[module_id] = handler
        self._module_metadata[module_id] = {
            "name": module_name,
            "metadata": metadata or {}
        }

    def get_handler(self, module_id: str) -> Optional[Callable]:
        """Get module handler by ID"""
        return self._modules.get(module_id)

    def get_metadata(self, module_id: str) -> Optional[Dict[str, Any]]:
        """Get module metadata"""
        return self._module_metadata.get(module_id)

    def list_modules(self) -> List[str]:
        """List all registered module IDs"""
        return list(self._modules.keys())


class IdempotencyCache:
    """In-memory idempotency cache"""

    def __init__(self, ttl_seconds: int = 3600):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._timestamps: Dict[str, int] = {}
        self._ttl_seconds = ttl_seconds

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached response"""
        # Check expiry
        if key in self._timestamps:
            if time.time() - self._timestamps[key] > self._ttl_seconds:
                del self._cache[key]
                del self._timestamps[key]
                return None
        return self._cache.get(key)

    def set(self, key: str, value: Dict[str, Any]):
        """Cache response"""
        self._cache[key] = value
        self._timestamps[key] = int(time.time())

    def has(self, key: str) -> bool:
        """Check if key exists and is valid"""
        if key not in self._cache:
            return False
        # Check expiry
        if time.time() - self._timestamps[key] > self._ttl_seconds:
            del self._cache[key]
            del self._timestamps[key]
            return False
        return True

    def clear(self):
        """Clear all cache"""
        self._cache.clear()
        self._timestamps.clear()


class OrchestratorV2:
    """
    V2 Agent Orchestrator with full Phase 1 features:
    - Module-based dispatching
    - Task FSM
    - Idempotency control
    - Budget control
    - Policy evaluation
    """

    def __init__(
        self,
        diagnosis_engine: Any = diagnosis_engine,
        maintenance_plan_generator: Any = maintenance_plan_generator,
        simulation_executor: Any = None,
    ):
        # Task contexts
        self._task_contexts: Dict[str, TaskContext] = {}
        self._diagnosis_engine = diagnosis_engine
        self._maintenance_plan_generator = maintenance_plan_generator
        self._simulation_executor = simulation_executor or SimulationExecutor()
        self._telemetry_builder = TelemetryContextBuilder()

        # Module registry
        self._module_registry = ModuleRegistry()
        self._register_default_modules()

        # Idempotency cache
        self._idempotency_cache = IdempotencyCache()

        # Event history for replay
        self._event_history: List[Dict[str, Any]] = []
        self._last_event_sequence: int = 0

        # Budget tracking
        self._budget_pools: Dict[str, int] = {}  # user_id -> budget_remaining_ms

    @staticmethod
    def _to_dict(payload: Any) -> dict[str, Any]:
        if hasattr(payload, "model_dump"):
            return payload.model_dump()
        if is_dataclass(payload):
            return asdict(payload)
        if isinstance(payload, dict):
            return payload
        return {"value": payload}

    def _register_default_modules(self):
        """Register default skill modules"""
        self._module_registry.register(
            "general",
            "General Assistant",
            self._general_handler,
            {"description": "Handles general workbench questions and summaries"}
        )
        self._module_registry.register(
            "coach",
            "Coach Agent",
            self._coach_handler,
            {"description": "Provides coaching and guidance"}
        )
        self._module_registry.register(
            "diagnoser",
            "Diagnoser Agent",
            self._diagnosis_handler,
            {"description": "Diagnoses errors and provides solutions"}
        )
        self._module_registry.register(
            "knowledge",
            "Knowledge Governance",
            self._knowledge_handler,
            {"description": "Manages knowledge entries"}
        )
        self._module_registry.register(
            "execution",
            "Task Execution",
            self._execution_handler,
            {"description": "Executes robot tasks"}
        )

    def _default_module_handler(self, context: TaskContext) -> Any:
        """Default module handler placeholder"""
        return {"status": "ok", "message": "Module handler not implemented"}

    @staticmethod
    def _normalize_prompt(message: str, fallback: str) -> str:
        normalized = (message or "").strip()
        return normalized if normalized else fallback

    @staticmethod
    def _map_policy_intent(intent: str) -> str:
        if intent == "execute-task":
            return "plan-task"
        return intent

    def _general_handler(self, context: TaskContext) -> Any:
        message = self._normalize_prompt(
            str(context.metadata.get("message") or ""),
            "请概述当前工作台状态。",
        )
        if any(keyword in message for keyword in ["审批", "审核"]):
            content = (
                "当前没有需要你直接处理的审批待办。若涉及高风险维修或知识写入，"
                "请在工作台中补充上下文后上报教师审核。"
            )
            action = {
                "type": "approval_summary",
                "pending_count": 0,
                "next_step": "如需发起审批，请先补充任务目标、风险点和证据。",
            }
        elif any(keyword in message for keyword in ["报告", "总结"]):
            content = (
                "今日执行摘要：1. 暂无挂起高风险任务；2. 可继续发起维保派单、故障诊断或知识查询；"
                "3. 如需正式报告，请补充时间范围和任务范围。"
            )
            action = {
                "type": "report_summary",
                "sections": ["任务进展", "风险关注", "后续建议"],
            }
        elif any(keyword in message for keyword in ["任务", "状态"]):
            content = (
                "当前任务概览：尚未发现进行中的执行任务。你可以从“派单维保”“诊断问题”或“知识查询”开始，"
                "我会继续跟踪当前 trace。"
            )
            action = {
                "type": "task_summary",
                "active_task_count": 0,
                "suggestions": ["派单维保", "诊断问题", "知识查询"],
            }
        else:
            content = (
                "我可以在 AI 工作台帮你做四类事：维保派单、故障诊断、知识查询和训练指导。"
                "告诉我机器人型号、故障现象或训练目标即可。"
            )
            action = {
                "type": "workbench_overview",
                "suggestions": ["派单维保", "诊断问题", "知识查询", "训练指导"],
            }
        return {
            "status": "ok",
            "message": content,
            "action": action,
            "trace_id": context.trace_id,
        }

    def _execution_handler(self, context: TaskContext) -> Any:
        message = self._normalize_prompt(
            str(context.metadata.get("message") or ""),
            "创建维保派单",
        )
        steps = [
            "确认机器人型号、故障现象与停机条件。",
            "准备绝缘防护、扭矩工具和记录介质，建立安全边界。",
            "进入 SOP 工作台执行检查、拆装和复位，并同步上传关键证据。",
            "完成后回到 AI 工作台复核结论，必要时上报教师审核。",
        ]
        return {
            "status": "ok",
            "message": "已生成维保派单建议，可按以下步骤执行：\n" + "\n".join(
                f"{index + 1}. {step}" for index, step in enumerate(steps)
            ),
            "action": {
                "type": "maintenance_dispatch",
                "task_summary": message,
                "steps": steps,
                "recommended_route": "/maintenance",
            },
            "trace_id": context.trace_id,
        }

    def _coach_handler(self, context: TaskContext) -> Any:
        message = self._normalize_prompt(
            str(context.metadata.get("message") or ""),
            "请给我训练指导建议。",
        )
        checklist = [
            "先确认训练目标、成功标准和安全边界。",
            "每一步操作前口述工具、风险和预期结果。",
            "遇到不确定项先暂停并记录，再请求教师或 AI 补充说明。",
        ]
        return {
            "status": "ok",
            "message": "训练指导建议：\n" + "\n".join(
                f"{index + 1}. {item}" for index, item in enumerate(checklist)
            ),
            "action": {
                "type": "training_guidance",
                "task_summary": message,
                "checklist": checklist,
            },
            "trace_id": context.trace_id,
        }

    def _knowledge_handler(self, context: TaskContext) -> Any:
        message = self._normalize_prompt(
            str(context.metadata.get("message") or ""),
            "查询机器人维保知识。",
        )
        intent = str(context.metadata.get("intent") or "read-kb")

        if intent == "write-kb" or any(keyword in message for keyword in ["记录", "沉淀", "新增", "写入"]):
            template = {
                "现象": "描述现场观察到的症状",
                "根因": "记录确认后的根因",
                "证据": "上传照片、日志或波形文件",
                "适用范围": "标明机器人型号、部件和版本",
            }
            return {
                "status": "ok",
                "message": "已为你整理知识记录草稿，请补充现象、根因、证据和适用范围后，再提交教师审核。",
                "action": {
                    "type": "knowledge_draft",
                    "template": template,
                },
                "trace_id": context.trace_id,
            }

        matches = knowledge_governance.search_knowledge(
            KnowledgeSearchQuery(query=message, status=KnowledgeStatus.APPROVED)
        )
        if matches:
            top_matches = matches[:3]
            lines = [
                f"{index + 1}. {match.entry.title}（风险 {match.entry.risk_level.value}，相关度 {match.relevance_score:.2f}）"
                for index, match in enumerate(top_matches)
            ]
            content = "已检索到以下知识条目：\n" + "\n".join(lines)
        else:
            content = (
                f"当前知识库没有直接命中“{message}”的已审批条目。"
                "建议换成更具体的部件名、故障码或 SOP 名称继续检索。"
            )
        return {
            "status": "ok",
            "message": content,
            "action": {
                "type": "knowledge_summary",
                "query": message,
                "match_count": len(matches),
            },
            "trace_id": context.trace_id,
        }

    async def process_request(
        self,
        user_id: str,
        message: str,
        resource_ref: Optional[Dict[str, Any]] = None,
        policy_context: Optional[Dict[str, Any]] = None,
        intent_classification: Optional[str] = None,
        trace_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        telemetry_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process agent request with full Phase 1 features
        """
        # 1. Check idempotency
        if idempotency_key:
            cached = self._idempotency_cache.get(idempotency_key)
            if cached:
                return {
                    **cached,
                    "from_cache": True
                }

        # 2. Generate trace_id if not provided
        if not trace_id:
            trace_id = f"trace-{uuid.uuid4().hex[:12]}"

        # 3. Parse and validate resource binding
        resources: List[ResourceRef] = []
        if resource_ref:
            binding_result = resource_parser.parse_resource_ref(resource_ref)
            if not binding_result.is_valid:
                return {
                    "success": False,
                    "error": "Invalid resource binding",
                    "errors": binding_result.errors,
                }
            resources = binding_result.resources

        # 4. Evaluate policy
        intent = intent_classification or self._classify_intent(message)
        policy_intent = self._map_policy_intent(intent)
        policy_decision = policy_matrix.evaluate(policy_intent, {
            "user_id": user_id,
            "message": message,
            "resources": [self._to_dict(r) for r in resources],
            **(policy_context or {})
        })

        if not policy_decision.allowed:
            return {
                "success": False,
                "error": "Policy denied",
                "policy_decision": self._to_dict(policy_decision),
            }

        # 5. Dispatch to appropriate module
        module_result = await self._dispatch_module(
            intent=intent,
            message=message,
            resources=resources,
            user_id=user_id,
            trace_id=trace_id,
            telemetry_payload=telemetry_payload,
        )

        if not module_result.success:
            self._record_event(trace_id, "request_processed", {
                "intent": intent,
                "policy_intent": policy_intent,
                "success": False,
                "policy_decision": self._to_dict(policy_decision),
                "error": module_result.error,
            })
            return {
                "success": False,
                "trace_id": trace_id,
                "error": module_result.error or "Module execution failed",
                "policy_decision": {
                    "allowed": policy_decision.allowed,
                    "risk_level": policy_decision.risk_level.value,
                    "requires_approval": policy_decision.requires_approval,
                    "approval_level": policy_decision.approval_level,
                    "evidence_required": policy_decision.evidence_required,
                },
                "from_cache": False,
                "timestamp": int(time.time() * 1000),
            }

        # 6. Build response
        response = {
            "success": True,
            "trace_id": trace_id,
            "message": module_result.output.get("message", "Operation completed") if module_result.output else "Completed",
            "result": module_result.output,
            "action_suggested": module_result.output.get("action") if module_result.output else None,
            "confidence": policy_decision.risk_level.value,
            "evidence_refs": module_result.evidence_required,
            "policy_decision": {
                "allowed": policy_decision.allowed,
                "risk_level": policy_decision.risk_level.value,
                "requires_approval": policy_decision.requires_approval,
                "approval_level": policy_decision.approval_level,
                "evidence_required": policy_decision.evidence_required,
            },
            "from_cache": False,
            "timestamp": int(time.time() * 1000),
        }

        # 7. Cache response for idempotency
        if idempotency_key:
            self._idempotency_cache.set(idempotency_key, response)

        # 8. Record event for replay
        self._record_event(trace_id, "request_processed", {
                "intent": intent,
                "policy_intent": policy_intent,
                "success": True,
                "policy_decision": self._to_dict(policy_decision),
            })

        return response

    def _classify_intent(self, message: str) -> str:
        """Classify user intent using IntentEngine (P1-3-4)"""
        import asyncio

        try:
            # Use LLM-based intent recognition
            result = asyncio.run(intent_engine.recognize(message, use_llm=True))

            # Map IntentScene to module action
            scene_to_action = {
                IntentScene.TASK_EXECUTION: "execute-task",
                IntentScene.DIAGNOSIS: "delegate-diagnoser",
                IntentScene.KNOWLEDGE_QUERY: "read-kb",
                IntentScene.TEACHING_GUIDE: "delegate-coach",
                IntentScene.TASK_STATUS: "query-status",
                IntentScene.HELP_REQUEST: "delegate-coach",
                IntentScene.GENERAL_CHAT: "general",
            }

            return scene_to_action.get(result.scene, "general")
        except Exception:
            # Fallback to keyword-based classification
            message_lower = message.lower()

            if any(kw in message_lower for kw in ["开始", "start", "练习", "执行"]):
                return "execute-task"
            elif any(kw in message_lower for kw in ["求助", "help", "怎么办", "怎么"]):
                return "delegate-coach"
            elif any(kw in message_lower for kw in ["诊断", "diagnose", "为什么"]):
                return "delegate-diagnoser"
            elif any(kw in message_lower for kw in ["知识", "knowledge", "搜索"]):
                return "read-kb"
            elif any(kw in message_lower for kw in ["创建", "create", "添加"]):
                return "write-kb"
            else:
                return "general"

    async def _dispatch_module(
        self,
        intent: str,
        message: str,
        resources: List[ResourceRef],
        user_id: str,
        trace_id: str,
        telemetry_payload: Optional[Dict[str, Any]] = None,
    ) -> ModuleDispatchResult:
        """Dispatch to appropriate skill module"""
        start_time = int(time.time() * 1000)

        # Map intent to module
        module_map = {
            "execute-task": "execution",
            "delegate-coach": "coach",
            "delegate-diagnoser": "diagnoser",
            "read-kb": "knowledge",
            "write-kb": "knowledge",
        }

        module_id = module_map.get(intent, "general")
        handler = self._module_registry.get_handler(module_id)

        if not handler:
            return ModuleDispatchResult(
                module_id=module_id,
                module_name=module_id,
                success=False,
                error=f"Module {module_id} not found",
                execution_time_ms=int(time.time() * 1000) - start_time,
            )

        # Create minimal context
        context = TaskContext(
            task_id=f"task-{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            trace_id=trace_id,
            resource_refs=resources,
            metadata={
                "message": message,
                "telemetry_payload": telemetry_payload,
                "intent": intent,
            },
        )

        try:
            output = handler(context)
            if hasattr(output, "__await__"):
                output = await output
            return ModuleDispatchResult(
                module_id=module_id,
                module_name=self._module_registry.get_metadata(module_id).get("name", module_id),
                success=True,
                output=output,
                execution_time_ms=int(time.time() * 1000) - start_time,
            )
        except Exception as e:
            return ModuleDispatchResult(
                module_id=module_id,
                module_name=module_id,
                success=False,
                error=str(e),
                execution_time_ms=int(time.time() * 1000) - start_time,
            )

    async def _diagnosis_handler(self, context: TaskContext) -> Any:
        telemetry_payload = context.metadata.get("telemetry_payload")
        if not telemetry_payload:
            return {"status": "error", "message": "缺少遥测数据，无法诊断"}

        telemetry_context = self._telemetry_builder.build_from_payload(telemetry_payload)
        diagnosis = await self._diagnosis_engine.diagnose(
            telemetry_context,
            use_llm=bool(getattr(self._diagnosis_engine, "llm_router", None)),
        )
        maintenance_plan = await self._maintenance_plan_generator.generate(
            diagnosis,
            use_llm=bool(getattr(self._maintenance_plan_generator, "llm_router", None)),
        )
        adapter = await AdapterFactory.get_adapter()
        verification = await self._simulation_executor.execute_and_verify(maintenance_plan, adapter)

        return {
            "status": "ok",
            "message": "诊断完成",
            "diagnosis": self._to_dict(diagnosis),
            "maintenance_plan": self._to_dict(maintenance_plan),
            "verification": self._to_dict(verification),
            "trace_id": context.trace_id,
        }

    def _record_event(self, trace_id: str, event_type: str, payload: Dict[str, Any]):
        """Record event for replay"""
        self._last_event_sequence += 1
        self._event_history.append({
            "event_id": f"evt-{uuid.uuid4().hex[:8]}",
            "event_sequence": self._last_event_sequence,
            "trace_id": trace_id,
            "event_type": event_type,
            "timestamp": int(time.time() * 1000),
            "payload": payload,
        })

    # ============ Task FSM Methods ============

    def create_task(
        self,
        user_id: str,
        skill_id: Optional[str] = None,
        resource_refs: Optional[List[ResourceRef]] = None,
        budget_limit_ms: int = 300000,
    ) -> TaskContext:
        """Create a new task"""
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        trace_id = f"trace-{uuid.uuid4().hex[:12]}"

        context = TaskContext(
            task_id=task_id,
            user_id=user_id,
            trace_id=trace_id,
            state=TaskFSMState.CREATED,
            skill_id=skill_id,
            resource_refs=resource_refs or [],
            budget_limit_ms=budget_limit_ms,
        )

        self._task_contexts[task_id] = context
        self._budget_pools[user_id] = budget_limit_ms

        self._record_event(trace_id, "task_created", {
            "task_id": task_id,
            "skill_id": skill_id,
        })

        return context

    def transition_state(
        self,
        task_id: str,
        event: TaskEventType,
    ) -> tuple[bool, str, TaskFSMState]:
        """Transition task state based on event"""
        if task_id not in self._task_contexts:
            return False, "Task not found", TaskFSMState.IDLE

        context = self._task_contexts[task_id]
        old_state = context.state

        # FSM transitions
        transitions = {
            (TaskFSMState.CREATED, TaskEventType.START): TaskFSMState.READY,
            (TaskFSMState.READY, TaskEventType.START): TaskFSMState.RUNNING,
            (TaskFSMState.RUNNING, TaskEventType.PAUSE): TaskFSMState.PAUSED,
            (TaskFSMState.PAUSED, TaskEventType.RESUME): TaskFSMState.RUNNING,
            (TaskFSMState.RUNNING, TaskEventType.COMPLETE): TaskFSMState.COMPLETED,
            (TaskFSMState.RUNNING, TaskEventType.FAIL): TaskFSMState.FAILED,
            (TaskFSMState.CREATED, TaskEventType.CANCEL): TaskFSMState.CANCELLED,
            (TaskFSMState.WAITING_APPROVAL, TaskEventType.APPROVE): TaskFSMState.RUNNING,
            (TaskFSMState.WAITING_APPROVAL, TaskEventType.REJECT): TaskFSMState.FAILED,
        }

        new_state = transitions.get((old_state, event))
        if new_state is None:
            return False, f"Invalid transition from {old_state} with {event}", old_state

        context.state = new_state
        if new_state == TaskFSMState.RUNNING and not context.started_at:
            context.started_at = int(time.time() * 1000)
        if new_state in [TaskFSMState.COMPLETED, TaskFSMState.FAILED, TaskFSMState.CANCELLED]:
            context.completed_at = int(time.time() * 1000)

        self._record_event(context.trace_id, "state_transition", {
            "task_id": task_id,
            "old_state": old_state.value,
            "new_state": new_state.value,
            "event": event.value,
        })

        return True, "Transition successful", new_state

    def get_task_context(self, task_id: str) -> Optional[TaskContext]:
        """Get task context"""
        return self._task_contexts.get(task_id)

    def check_budget(self, user_id: str, required_ms: int) -> tuple[bool, int]:
        """Check if user has enough budget"""
        remaining = self._budget_pools.get(user_id, 0)
        if remaining >= required_ms:
            return True, remaining - required_ms
        return False, remaining

    def consume_budget(self, user_id: str, used_ms: int):
        """Consume budget"""
        if user_id in self._budget_pools:
            self._budget_pools[user_id] -= used_ms

    def get_trace_events(self, trace_id: str) -> List[Dict[str, Any]]:
        """Get events for a trace"""
        return [e for e in self._event_history if e.get("trace_id") == trace_id]

    def record_trace_event(self, trace_id: str, event_type: str, payload: Dict[str, Any]) -> None:
        """Public wrapper for adding custom trace events from API actions."""
        self._record_event(trace_id, event_type, payload)


# Singleton instance
orchestrator_v2 = OrchestratorV2()
