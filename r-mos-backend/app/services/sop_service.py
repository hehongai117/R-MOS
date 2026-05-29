"""
SOP服务（V2.3完整版）
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload
from typing import List, Dict, Any, Optional
import logging

from app.models.sop import SOP, SOPStep
from app.models.task import Task
from app.schemas.sop import SOPCreate, SOPDeleteWarning, SOPDeleteResponse, DIFFICULTY_MAP, SOPAdjudicationStepResponse, SOPAdjudicationResponse, SOPAdjudicationListResponse
from app.core.exceptions import BusinessRuleViolation, ResourceNotFoundError

logger = logging.getLogger(__name__)


class SOPService:
    """SOP服务
    
    职责：
    - SOP的CRUD操作
    - SOP删除二次确认逻辑（V2.3核心）
    - SOP与Task的关联检查
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_sop(self, request: SOPCreate) -> SOP:
        """创建SOP（含步骤）"""
        # 1. 创建SOP主记录
        sop = SOP(
            name=request.name,
            description=request.description,
            applicable_model=request.applicable_model,
            category=request.category,
            difficulty_level=request.difficulty_level,
            estimated_time=request.estimated_time
        )
        
        self.db.add(sop)
        await self.db.flush()  # 获取ID
        
        # 2. 创建步骤
        for step_data in request.steps:
            step = SOPStep(
                sop_id=sop.id,
                step_index=step_data.step_index,
                title=step_data.title,
                description=step_data.description,
                target_part=step_data.target_part,
                expected_action=step_data.expected_action,
                action_params=step_data.action_params,
                validation_rules=step_data.validation_rules,
                is_critical=step_data.is_critical,
                timeout_seconds=step_data.timeout_seconds,
                allow_skip=step_data.allow_skip,
                hints=step_data.hints,
                tools_required=step_data.tools_required
            )
            self.db.add(step)
        
        await self.db.commit()
        await self.db.refresh(sop)
        
        logger.info(f"SOP创建成功: id={sop.id}, name={sop.name}, steps={len(request.steps)}")
        return sop
    
    async def get_sop(self, sop_id: int) -> SOP:
        """查询SOP（含步骤预加载）"""
        result = await self.db.execute(
            select(SOP).where(SOP.id == sop_id).options(selectinload(SOP.steps))
        )
        sop = result.scalar_one_or_none()

        if not sop:
            raise ResourceNotFoundError("SOP", sop_id)

        return sop
    
    async def list_sops(
        self,
        applicable_model: Optional[str] = None,
        category: Optional[str] = None,
        robot_model_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """查询SOP列表，返回分页格式 {"items": [...], "total": N}"""
        # 构建 count 查询
        count_query = select(func.count()).select_from(SOP)

        if applicable_model:
            count_query = count_query.where(SOP.applicable_model == applicable_model)

        if category:
            count_query = count_query.where(SOP.category == category)

        if robot_model_id is not None:
            count_query = count_query.where(SOP.robot_model_id == robot_model_id)

        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        # 构建数据查询
        query = select(SOP)

        if applicable_model:
            query = query.where(SOP.applicable_model == applicable_model)

        if category:
            query = query.where(SOP.category == category)

        if robot_model_id is not None:
            query = query.where(SOP.robot_model_id == robot_model_id)

        query = query.order_by(SOP.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        sops = result.scalars().all()

        return {"items": sops, "total": total}
    
    async def delete_sop(
        self,
        sop_id: int,
        force: bool = False
    ) -> SOPDeleteResponse:
        """删除SOP（V2.3核心方法 - 实现骨架§5.5规则）
        
        删除流程：
        1. 检查SOP是否存在
        2. 查询关联的Task
        3. 如有Task且force=False → 抛出409异常（前端需调用check_delete_impact）
        4. 如有Task且force=True → 物理删除SOP，Task.sop_id设为NULL
        5. 如无Task → 直接删除
        
        Args:
            sop_id: SOP ID
            force: 是否强制删除（忽略关联Task）
            
        Returns:
            SOPDeleteResponse: 删除结果
            
        Raises:
            ResourceNotFoundError: SOP不存在
            BusinessRuleViolation: 有关联Task且force=False
        """
        # 1. 检查SOP是否存在
        sop = await self.get_sop(sop_id)
        
        # 2. 查询关联的Task
        affected_tasks = await self._get_affected_tasks(sop_id)
        
        # 3. 判断是否可删除
        if affected_tasks and not force:
            # 有关联Task且未强制删除 → 抛出409异常
            raise BusinessRuleViolation(
                message=f"此SOP被{len(affected_tasks)}个Task引用，删除需要force=true参数",
                code="SOP_REFERENCED_BY_TASKS",
                details={
                    "sop_id": sop_id,
                    "affected_task_count": len(affected_tasks),
                    "affected_tasks": [
                        {
                            "task_id": t.id,
                            "title": t.title,
                            # V2.3.1 修复: 兼容字符串和枚举两种类型
                            "status": t.status.value if hasattr(t.status, 'value') else t.status
                        }
                        for t in affected_tasks[:10]  # 最多返回10个
                    ],
                    "force_required": True
                }
            )
        
        # 4. 执行删除
        if affected_tasks:
            # 有关联Task：设置Task.sop_id为NULL（符合骨架§5.5）
            for task in affected_tasks:
                task.sop_id = None
            
            logger.warning(
                f"强制删除SOP: id={sop_id}, 受影响Task数量={len(affected_tasks)}"
            )
        
        # 删除SOP步骤（通过relationship获取）
        for step in sop.steps:
            await self.db.delete(step)
        
        # 删除SOP主记录
        await self.db.delete(sop)
        await self.db.commit()
        
        logger.info(f"SOP已删除: id={sop_id}, name={sop.name}")
        
        return SOPDeleteResponse(
            success=True,
            message=f"SOP已删除{f'，{len(affected_tasks)}个关联Task的sop_id已设为NULL' if affected_tasks else ''}",
            deleted_sop_id=sop_id,
            affected_task_count=len(affected_tasks)
        )
    
    async def check_delete_impact(self, sop_id: int) -> SOPDeleteWarning:
        """检查删除SOP的影响（V2.3新增 - 供前端调用）
        
        前端流程：
        1. 用户点击删除
        2. 前端调用此接口查询影响
        3. 如有警告 → 显示确认对话框
        4. 用户确认 → 调用delete_sop(force=True)
        
        Args:
            sop_id: SOP ID
            
        Returns:
            SOPDeleteWarning: 删除影响评估
        """
        # 检查SOP是否存在
        sop = await self.get_sop(sop_id)
        
        # 查询关联Task
        affected_tasks = await self._get_affected_tasks(sop_id)
        
        if not affected_tasks:
            # 无关联Task，可直接删除
            return SOPDeleteWarning(
                can_delete=True,
                warning_type="NO_IMPACT",
                message="此SOP无关联Task，可直接删除",
                affected_tasks=[],
                force_required=False
            )
        
        # 有关联Task，需要二次确认
        return SOPDeleteWarning(
            can_delete=False,
            warning_type="REFERENCED_BY_TASKS",
            message=f"此SOP被{len(affected_tasks)}个Task引用，删除后这些Task将无法查看原SOP信息",
            affected_tasks=[
                {
                    "task_id": t.id,
                    "title": t.title,
                    # V2.3.1 修复: 兼容字符串和枚举两种类型
                    "status": t.status.value if hasattr(t.status, 'value') else t.status,
                    "created_at": t.created_at.isoformat()
                }
                for t in affected_tasks[:20]  # 最多返回20个
            ],
            force_required=True
        )
    
    def _sop_to_adjudication(self, sop: SOP) -> SOPAdjudicationResponse:
        """将DB SOP对象转换为裁决格式"""
        sorted_steps = sorted(sop.steps, key=lambda s: s.step_index)
        adj_steps = []
        for i, step in enumerate(sorted_steps):
            action_params = step.action_params or {}
            validation_rules = step.validation_rules or {}

            # Determine nextStepId from ordering
            next_step = sorted_steps[i + 1] if i + 1 < len(sorted_steps) else None
            next_step_id = f"step-{next_step.id}" if next_step else None

            on_success = action_params.get("onSuccess", {})
            if not on_success and next_step_id:
                on_success = {"nextStepId": next_step_id}

            on_failure = action_params.get("onFailure", {})

            target_parts = action_params.get("targetParts", [])
            if not target_parts and step.target_part:
                target_parts = [step.target_part]

            required_tool = action_params.get("requiredTool")
            if not required_tool and step.tools_required:
                required_tool = step.tools_required[0] if step.tools_required else None

            adj_steps.append(SOPAdjudicationStepResponse(
                stepId=f"step-{step.id}",
                stepIndex=step.step_index,
                title=step.title,
                description=step.description,
                action=step.expected_action,
                targetParts=target_parts,
                requiredTool=required_tool,
                preconditions=action_params.get("preconditions", []),
                validations=validation_rules.get("validations", []),
                failureReasons=validation_rules.get("failureReasons", []),
                onSuccess=on_success,
                onFailure=on_failure,
                isIrreversible=action_params.get("isIrreversible", False),
                fatalOnFailure=step.is_critical,
            ))

        return SOPAdjudicationResponse(
            sopId=f"sop-db-{sop.id}",
            title=sop.name,
            version=sop.version or "1.0",
            targetModule=sop.target_module or sop.category or "general",
            estimatedTime=sop.estimated_time or 0,
            difficulty=DIFFICULTY_MAP.get(sop.difficulty_level, "intermediate"),
            steps=adj_steps,
        )

    async def list_adjudication_sops(
        self,
        robot_model_id: Optional[int] = None,
        applicable_model: Optional[str] = None,
        category: Optional[str] = None,
    ) -> SOPAdjudicationListResponse:
        """查询SOP列表并转换为裁决格式"""
        query = select(SOP).options(selectinload(SOP.steps))

        if robot_model_id is not None:
            query = query.where(SOP.robot_model_id == robot_model_id)
        if applicable_model:
            query = query.where(SOP.applicable_model == applicable_model)
        if category:
            query = query.where(SOP.category == category)

        query = query.order_by(SOP.created_at.desc())
        result = await self.db.execute(query)
        sops = result.scalars().all()

        items = [self._sop_to_adjudication(sop) for sop in sops]
        return SOPAdjudicationListResponse(total=len(items), items=items)

    async def _get_affected_tasks(self, sop_id: int) -> List[Task]:
        """内部方法：查询关联的Task列表"""
        result = await self.db.execute(
            select(Task)
            .where(Task.sop_id == sop_id)
            .order_by(Task.created_at.desc())
        )
        return result.scalars().all()
