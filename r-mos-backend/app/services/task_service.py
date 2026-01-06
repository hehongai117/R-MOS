"""
Task服务（V2.3完整版）
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from app.models.task import Task, TaskStatus
from app.models.sop import SOP, SOPStep
from app.models.event import EventType
from app.schemas.task import TaskCreate, StepExecutionRequest, StepExecutionResponse
from app.core.exceptions import BusinessRuleViolation
from app.services.snapshot_service import SnapshotService
from app.services.event_service import EventService
from app.services.scoring_service import ScoringService

logger = logging.getLogger(__name__)


class TaskService:
    """Task服务（V2.3完整版）
    
    职责：
    - Task生命周期管理
    - 步骤执行与验证
    - 集成Snapshot、Event、Scoring服务
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.snapshot_service = SnapshotService(db)
        self.event_service = EventService(db)
        self.scoring_service = ScoringService(db)
    
    async def create_task(self, request: TaskCreate) -> Task:
        """创建Task"""
        # 验证SOP存在
        sop = await self._get_sop(request.sop_id)
        if not sop:
            raise BusinessRuleViolation(
                message="SOP不存在",
                code="SOP_NOT_FOUND",
                details={"sop_id": request.sop_id}
            )
        
        task = Task(
            title=request.title,
            sop_id=request.sop_id,
            user_id=request.user_id,
            status=TaskStatus.PENDING,
            current_step_index=0,
            time_limit=request.time_limit,
            pass_score=request.pass_score
        )
        
        self.db.add(task)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(task)
        
        logger.info(f"Task创建成功: task_id={task.id}, sop_id={request.sop_id}")
        return task
    
    async def start_task(self, task_id: int) -> Task:
        """开始Task"""
        task = await self._get_task(task_id)
        
        if task.status != TaskStatus.PENDING:
            raise BusinessRuleViolation(
                message="Task状态错误，只有PENDING状态可以开始",
                code="TASK_NOT_PENDING",
                details={"current_status": task.status.value}
            )
        
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.utcnow()
        
        # 创建TASK_STARTED事件
        await self.event_service.create_event(
            task_id=task_id,
            event_type=EventType.TASK_STARTED.value,
            result="started"
        )
        
        await self.db.commit()
        logger.info(f"Task已开始: task_id={task_id}")
        return task
    
    async def execute_step(
        self,
        task_id: int,
        request: StepExecutionRequest
    ) -> StepExecutionResponse:
        """执行步骤（V2.3核心方法 - 300行完整实现）
        
        流程：
        1. 验证Task状态
        2. 验证步骤顺序（含跳过逻辑）
        3. 创建Event
        4. 尝试创建Snapshot（允许失败）
        5. 更新Task状态
        6. 检查是否完成
        7. 返回响应
        """
        start_time = datetime.utcnow()
        
        # 1. 加载Task和SOP
        task = await self._get_task(task_id)
        
        if task.status != TaskStatus.IN_PROGRESS:
            raise BusinessRuleViolation(
                message="Task未在进行中",
                code="TASK_NOT_IN_PROGRESS",
                details={"current_status": task.status.value}
            )
        
        # 加载SOP（可能为NULL）
        sop = await self._get_sop(task.sop_id) if task.sop_id else None
        if not sop:
            raise BusinessRuleViolation(
                message="关联的SOP已被删除，无法继续执行",
                code="SOP_NOT_FOUND",
                details={"task_id": task_id}
            )
        
        # 2. 验证步骤顺序（V2.3核心逻辑 - 响应审计P0-NEW-02）
        expected_step_index = task.current_step_index + 1
        requested_step_index = request.step_index
        
        # 情况1：正常顺序执行
        if requested_step_index == expected_step_index:
            step_status = "success"
            message = f"步骤{requested_step_index}执行成功"
            
            # 创建STEP_EXECUTED事件
            event = await self.event_service.create_event(
                task_id=task_id,
                event_type=EventType.STEP_EXECUTED.value,
                step_index=requested_step_index,
                action=request.action,
                parameters=request.parameters,
                result="success",
                duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
            )
            
            # 尝试创建Snapshot（失败不阻断，符合骨架§5.4）
            snapshot_id = None
            snapshot = await self.snapshot_service.create_snapshot(
                task_id=task_id,
                step_index=requested_step_index,
                trigger="step_execution"
            )
            if snapshot:
                snapshot_id = snapshot.id
                await self.event_service.create_event(
                    task_id=task_id,
                    event_type=EventType.SNAPSHOT_CREATED.value,
                    step_index=requested_step_index,
                    result="success"
                )
            else:
                # Snapshot创建失败，记录但不阻断
                await self.event_service.create_event(
                    task_id=task_id,
                    event_type=EventType.SNAPSHOT_FAILED.value,
                    step_index=requested_step_index,
                    is_error=False,  # 降级，不算错误
                    error_message="Snapshot创建失败（Adapter连接问题）"
                )
            
            # 更新Task进度
            task.current_step_index = requested_step_index
        
        # 情况2：尝试跳过一个步骤
        elif requested_step_index == expected_step_index + 1:
            skipped_step = await self._get_sop_step(sop.id, expected_step_index)
            
            if not skipped_step:
                raise BusinessRuleViolation(
                    message=f"步骤{expected_step_index}不存在",
                    code="STEP_NOT_FOUND",
                    details={"step_index": expected_step_index}
                )
            
            # 检查是否允许跳过（响应骨架§5.3）
            if not skipped_step.allow_skip:
                raise BusinessRuleViolation(
                    message=f"步骤{expected_step_index}为关键步骤，不允许跳过",
                    code="CRITICAL_STEP_CANNOT_SKIP",
                    details={
                        "step_index": expected_step_index,
                        "step_title": skipped_step.title,
                        "is_critical": skipped_step.is_critical
                    }
                )
            
            # 允许跳过：创建STEP_SKIPPED事件
            await self.event_service.create_event(
                task_id=task_id,
                event_type=EventType.STEP_SKIPPED.value,
                step_index=expected_step_index,
                action="skip",
                result="skipped"
            )
            
            # 执行当前步骤
            event = await self.event_service.create_event(
                task_id=task_id,
                event_type=EventType.STEP_EXECUTED.value,
                step_index=requested_step_index,
                action=request.action,
                parameters=request.parameters,
                result="success",
                duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
            )
            
            # 创建Snapshot（仅为已执行步骤）
            snapshot_id = None
            snapshot = await self.snapshot_service.create_snapshot(
                task_id=task_id,
                step_index=requested_step_index,
                trigger="step_execution"
            )
            if snapshot:
                snapshot_id = snapshot.id
            
            # 更新Task进度
            task.current_step_index = requested_step_index
            step_status = "success"
            message = f"步骤{expected_step_index}已跳过，步骤{requested_step_index}执行成功"
        
        # 情况3：步骤顺序错误
        else:
            raise BusinessRuleViolation(
                message=f"必须先执行步骤{expected_step_index}",
                code="STEP_SEQUENCE_VIOLATION",
                details={
                    "current_step": task.current_step_index,
                    "requested_step": requested_step_index,
                    "expected_step": expected_step_index
                }
            )
        
        # 3. 检查是否完成Task
        total_steps = len(sop.steps)
        is_task_completed = (task.current_step_index >= total_steps)
        
        if is_task_completed:
            await self._complete_task(task_id)
        
        await self.db.commit()
        
        # 4. 返回响应
        return StepExecutionResponse(
            task_id=task_id,
            step_index=requested_step_index,
            status=step_status,
            message=message,
            snapshot_id=snapshot_id,
            next_step_index=task.current_step_index + 1 if not is_task_completed else None,
            is_task_completed=is_task_completed
        )
    
    async def _complete_task(self, task_id: int):
        """完成Task（V2.3新增 - 响应审计P1-NEW-10）
        
        ⚠️ 内部方法，不直接对外暴露
        
        流程：
        1. 更新Task状态
        2. 调用评分引擎
        3. 写入最终得分
        4. 创建TASK_COMPLETED事件
        """
        task = await self._get_task(task_id)
        
        # 1. 更新状态
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        
        # 2. 调用评分引擎（V2.3核心集成）
        try:
            score_result = await self.scoring_service.calculate_score(task_id)
            
            # 3. 写入评分结果
            task.final_score = int(score_result["final_score"])
            task.is_passed = (task.final_score >= task.pass_score)
            
            logger.info(f"Task评分完成: task_id={task_id}, score={task.final_score}, passed={task.is_passed}")
        except Exception as e:
            # 评分失败不阻断任务完成（MVP降级策略）
            logger.error(f"评分失败: task_id={task_id}, error={e}")
            task.final_score = None
            task.is_passed = False
        
        # 4. 创建完成Event
        await self.event_service.create_event(
            task_id=task_id,
            event_type=EventType.TASK_COMPLETED.value,
            result="completed"
        )
        
        logger.info(f"Task已完成: task_id={task_id}")
    
    async def pause_task(self, task_id: int) -> Task:
        """暂停Task"""
        task = await self._get_task(task_id)
        
        if task.status != TaskStatus.IN_PROGRESS:
            raise BusinessRuleViolation(
                message="只有进行中的Task可以暂停",
                code="TASK_NOT_IN_PROGRESS",
                details={"current_status": task.status.value}
            )
        
        task.status = TaskStatus.PAUSED
        task.paused_at = datetime.utcnow()
        
        await self.event_service.create_event(
            task_id=task_id,
            event_type=EventType.TASK_PAUSED.value,
            result="paused"
        )
        
        await self.db.commit()
        logger.info(f"Task已暂停: task_id={task_id}")
        return task
    
    async def resume_task(self, task_id: int) -> Task:
        """恢复Task"""
        task = await self._get_task(task_id)
        
        if task.status != TaskStatus.PAUSED:
            raise BusinessRuleViolation(
                message="只有暂停的Task可以恢复",
                code="TASK_NOT_PAUSED",
                details={"current_status": task.status.value}
            )
        
        task.status = TaskStatus.IN_PROGRESS
        task.paused_at = None
        
        await self.event_service.create_event(
            task_id=task_id,
            event_type=EventType.TASK_RESUMED.value,
            result="resumed"
        )
        
        await self.db.commit()
        logger.info(f"Task已恢复: task_id={task_id}")
        return task
    
    async def get_task(self, task_id: int) -> Task:
        """查询Task"""
        return await self._get_task(task_id)
    
    async def _get_task(self, task_id: int) -> Task:
        """内部：获取Task（抛出异常）"""
        result = await self.db.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            raise BusinessRuleViolation(
                message="Task不存在",
                code="TASK_NOT_FOUND",
                details={"task_id": task_id}
            )
        return task
    
    async def _get_sop(self, sop_id: int) -> Optional[SOP]:
        """内部：获取SOP（含步骤预加载）"""
        if not sop_id:
            return None
        result = await self.db.execute(
            select(SOP).where(SOP.id == sop_id).options(selectinload(SOP.steps))
        )
        return result.scalar_one_or_none()
    
    async def _get_sop_step(self, sop_id: int, step_index: int) -> Optional[SOPStep]:
        """内部：获取SOP步骤"""
        result = await self.db.execute(
            select(SOPStep).where(
                SOPStep.sop_id == sop_id,
                SOPStep.step_index == step_index
            )
        )
        return result.scalar_one_or_none()
