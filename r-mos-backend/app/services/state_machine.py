"""
Task 状态机模块（V2.3 新增 - Phase 2）

严格控制 Task 生命周期状态流转：
- PENDING → IN_PROGRESS（仅此转换）
- IN_PROGRESS → PAUSED / COMPLETED / FAILED
- PAUSED → IN_PROGRESS / CANCELLED
- FAILED / COMPLETED / CANCELLED 为终态，不可转换

禁止的非法转换会抛出 BusinessRuleViolation 异常。
"""
from enum import Enum
from typing import Dict, Set, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

from app.models.task import TaskStatus
from app.core.exceptions import BusinessRuleViolation

logger = logging.getLogger(__name__)


# 状态转换动作
class TaskAction(str, Enum):
    START = "start"           # PENDING → IN_PROGRESS
    PAUSE = "pause"           # IN_PROGRESS → PAUSED
    RESUME = "resume"         # PAUSED → IN_PROGRESS
    COMPLETE = "complete"     # IN_PROGRESS → COMPLETED
    FAIL = "fail"             # IN_PROGRESS → FAILED
    CANCEL = "cancel"         # PENDING / PAUSED → CANCELLED
    TIMEOUT = "timeout"       # IN_PROGRESS → FAILED (自动)


# 状态转换规则定义
VALID_TRANSITIONS: Dict[TaskStatus, Dict[TaskAction, TaskStatus]] = {
    TaskStatus.PENDING: {
        TaskAction.START: TaskStatus.IN_PROGRESS,
        TaskAction.CANCEL: TaskStatus.CANCELLED,
    },
    TaskStatus.IN_PROGRESS: {
        TaskAction.PAUSE: TaskStatus.PAUSED,
        TaskAction.COMPLETE: TaskStatus.COMPLETED,
        TaskAction.FAIL: TaskStatus.FAILED,
        TaskAction.TIMEOUT: TaskStatus.TIMEOUT,  # 超时为独立终态
    },
    TaskStatus.PAUSED: {
        TaskAction.RESUME: TaskStatus.IN_PROGRESS,
        TaskAction.CANCEL: TaskStatus.CANCELLED,
    },
    # 终态：不允许任何转换
    TaskStatus.COMPLETED: {},
    TaskStatus.FAILED: {},
    TaskStatus.CANCELLED: {},
    TaskStatus.TIMEOUT: {},  # V2.3 新增
}

# 终态集合
TERMINAL_STATES: Set[TaskStatus] = {
    TaskStatus.COMPLETED,
    TaskStatus.FAILED,
    TaskStatus.CANCELLED,
    TaskStatus.TIMEOUT,  # V2.3 新增
}


@dataclass
class StateTransition:
    """状态转换记录"""
    task_id: int
    from_status: TaskStatus
    to_status: TaskStatus
    action: TaskAction
    actor_id: Optional[str] = None
    reason: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class TaskStateMachine:
    """Task 状态机
    
    用法示例：
    ```python
    machine = TaskStateMachine()
    
    # 验证转换是否允许
    if machine.can_transition(TaskStatus.PENDING, TaskAction.START):
        new_status = machine.transition(task_id, TaskStatus.PENDING, TaskAction.START)
    ```
    """
    
    def __init__(self):
        self._transitions: Dict[TaskStatus, Dict[TaskAction, TaskStatus]] = VALID_TRANSITIONS
        self._history: list[StateTransition] = []
    
    def can_transition(self, current_status: TaskStatus, action: TaskAction) -> bool:
        """检查是否允许状态转换"""
        if current_status in TERMINAL_STATES:
            return False
        return action in self._transitions.get(current_status, {})
    
    def get_next_status(self, current_status: TaskStatus, action: TaskAction) -> TaskStatus:
        """获取转换后的状态（不执行转换）"""
        if not self.can_transition(current_status, action):
            raise BusinessRuleViolation(
                message=f"不允许的状态转换: {current_status.value} + {action.value}",
                code="INVALID_STATE_TRANSITION",
                details={
                    "current_status": current_status.value,
                    "action": action.value,
                    "allowed_actions": list(self._transitions.get(current_status, {}).keys())
                }
            )
        return self._transitions[current_status][action]
    
    def transition(
        self,
        task_id: int,
        current_status: TaskStatus,
        action: TaskAction,
        actor_id: Optional[str] = None,
        reason: Optional[str] = None
    ) -> TaskStatus:
        """执行状态转换并记录历史"""
        new_status = self.get_next_status(current_status, action)
        
        record = StateTransition(
            task_id=task_id,
            from_status=current_status,
            to_status=new_status,
            action=action,
            actor_id=actor_id,
            reason=reason
        )
        self._history.append(record)
        
        logger.info(
            f"[TaskStateMachine] Task {task_id}: "
            f"{current_status.value} --[{action.value}]--> {new_status.value}"
        )
        
        return new_status
    
    def get_allowed_actions(self, current_status: TaskStatus) -> list[TaskAction]:
        """获取当前状态允许的动作列表"""
        return list(self._transitions.get(current_status, {}).keys())
    
    def is_terminal(self, status: TaskStatus) -> bool:
        """检查是否为终态"""
        return status in TERMINAL_STATES
    
    def get_transition_history(self, task_id: Optional[int] = None) -> list[StateTransition]:
        """获取状态转换历史"""
        if task_id is None:
            return self._history
        return [r for r in self._history if r.task_id == task_id]


# 全局单例
state_machine = TaskStateMachine()
