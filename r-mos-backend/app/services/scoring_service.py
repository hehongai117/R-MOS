"""
评分服务（V2.3完整版）
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from app.models.task import Task
from app.models.event import Event, EventType
from app.models.sop import SOP, SOPStep
from app.models.snapshot import Snapshot
from app.schemas.report import ScoreBreakdown, StepScore

logger = logging.getLogger(__name__)


class ScoringService:
    """评分服务（V2.3完整实现）
    
    职责：
    - 计算Task最终得分
    - 生成评分细分（4个维度）
    - 生成步骤得分列表
    - 生成改进建议
    
    评分规则（MVP版本）：
    - 基础分100分
    - 跳过步骤：-5分/次
    - 错误操作：-10分/次
    - 超时：-15分
    - 按比例分配到4个维度
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def calculate_score(self, task_id: int) -> Dict[str, Any]:
        """计算Task得分（V2.3核心方法）
        
        Returns:
            {
                "final_score": 85.0,
                "breakdown": ScoreBreakdown,
                "step_scores": List[StepScore],
                "recommendations": List[str]
            }
        """
        # 1. 加载Task和相关数据
        task = await self._load_task(task_id)
        events = await self._load_events(task_id)
        sop = await self._load_sop(task.sop_id) if task.sop_id else None
        
        # 2. 统计关键指标（V2.4：包含异常快照统计）
        anomaly_count = await self._count_anomaly_snapshots(task_id)
        stats = self._calculate_stats(task, events, sop, anomaly_count)
        
        # 3. 计算得分
        base_score = 100.0
        deductions = []
        
        # 跳过步骤扣分
        if stats["skipped_steps"] > 0:
            deduction = stats["skipped_steps"] * 5.0
            base_score -= deduction
            deductions.append({
                "reason": "跳过步骤",
                "count": stats["skipped_steps"],
                "points": -deduction
            })
        
        # 错误操作扣分
        if stats["error_count"] > 0:
            deduction = stats["error_count"] * 10.0
            base_score -= deduction
            deductions.append({
                "reason": "错误操作",
                "count": stats["error_count"],
                "points": -deduction
            })
        
        # 超时扣分
        if stats["is_timeout"]:
            deduction = 15.0
            base_score -= deduction
            deductions.append({
                "reason": "执行超时",
                "points": -deduction
            })
        
        # V2.4 新增：故障惩罚（检测到活动故障的快照）
        if stats["anomaly_count"] > 0:
            deduction = stats["anomaly_count"] * 15.0  # 每个异常快照扣15分
            base_score -= deduction
            deductions.append({
                "reason": "检测到故障",
                "count": stats["anomaly_count"],
                "points": -deduction
            })
        
        final_score = max(0.0, min(100.0, base_score))
        
        # 4. 分配到4个维度（简化版本，按比例）
        breakdown = ScoreBreakdown(
            professionalism=final_score * 0.25,
            compliance=final_score * 0.25,
            efficiency=final_score * 0.25,
            safety=final_score * 0.25
        )
        
        # 5. 生成步骤得分（MVP版本：已执行步骤100分，跳过0分）
        step_scores = []
        if sop:
            for step in sop.steps:
                is_skipped = any(
                    e.event_type == EventType.STEP_SKIPPED.value and e.step_index == step.step_index
                    for e in events
                )
                step_scores.append(StepScore(
                    step_index=step.step_index,
                    step_title=step.title,
                    score=0.0 if is_skipped else 10.0,
                    max_score=10.0,
                    deductions=deductions if is_skipped else [],
                    remarks="已跳过" if is_skipped else "已完成"
                ))
        
        # 6. 生成建议
        recommendations = self._generate_recommendations(stats, deductions)
        
        logger.info(f"评分完成: task_id={task_id}, score={final_score}")
        
        return {
            "final_score": final_score,
            "breakdown": breakdown,
            "step_scores": step_scores,
            "recommendations": recommendations
        }
    
    async def _load_task(self, task_id: int) -> Task:
        """加载Task"""
        result = await self.db.execute(
            select(Task).where(Task.id == task_id)
        )
        return result.scalar_one()
    
    async def _load_events(self, task_id: int) -> List[Event]:
        """加载Task的所有Event"""
        result = await self.db.execute(
            select(Event).where(Event.task_id == task_id).order_by(Event.timestamp)
        )
        return result.scalars().all()
    
    async def _load_sop(self, sop_id: int) -> Optional[SOP]:
        """加载SOP（含步骤预加载）"""
        if not sop_id:
            return None
        result = await self.db.execute(
            select(SOP).where(SOP.id == sop_id).options(selectinload(SOP.steps))
        )
        return result.scalar_one_or_none()
    
    async def _count_anomaly_snapshots(self, task_id: int) -> int:
        """V2.4 新增：统计包含异常的快照数量"""
        result = await self.db.execute(
            select(func.count(Snapshot.id)).where(
                Snapshot.task_id == task_id,
                Snapshot.is_anomaly == True
            )
        )
        return result.scalar() or 0
    
    def _calculate_stats(self, task: Task, events: List[Event], sop: Optional[SOP], anomaly_count: int = 0) -> Dict[str, Any]:
        """计算统计指标（V2.4：支持异常统计）"""
        skipped_steps = sum(1 for e in events if e.event_type == EventType.STEP_SKIPPED.value)
        error_count = sum(1 for e in events if e.is_error)
        
        # 检查是否超时
        is_timeout = False
        if task.time_limit and task.started_at and task.completed_at:
            duration = (task.completed_at - task.started_at).total_seconds()
            is_timeout = duration > task.time_limit
        
        return {
            "skipped_steps": skipped_steps,
            "error_count": error_count,
            "is_timeout": is_timeout,
            "anomaly_count": anomaly_count,  # V2.4 新增
            "total_steps": len(sop.steps) if sop else 0,
            "completed_steps": task.current_step_index
        }
    
    def _generate_recommendations(self, stats: Dict[str, Any], deductions: List[Dict]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        if stats["skipped_steps"] > 0:
            recommendations.append(f"建议完成所有步骤，避免跳过（当前跳过{stats['skipped_steps']}步）")
        
        if stats["error_count"] > 0:
            recommendations.append(f"注意操作规范，减少错误（当前错误{stats['error_count']}次）")
        
        if stats["is_timeout"]:
            recommendations.append("建议提升操作熟练度，避免超时")
        
        if not recommendations:
            recommendations.append("表现优秀，继续保持！")
        
        return recommendations
