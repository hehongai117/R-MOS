"""
P2-3-4: SOP Quality Monitor Service
SOP 质量监控服务

职责：
- 监控 SOP 步骤失败率
- 当某步骤失败率 > 40% 时自动创建审核工单
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.teaching import AssignmentAttempt, Assignment
from app.models.sop import SOP, SOPStep
from app.models.event import Event, EventType

logger = logging.getLogger(__name__)

# 失败率阈值
FAILURE_RATE_THRESHOLD = 40.0  # 40%


class StepFailureStats:
    """步骤失败统计"""

    def __init__(
        self,
        step_index: int,
        step_title: str,
        total_attempts: int,
        failed_attempts: int,
        failure_rate: float,
    ):
        self.step_index = step_index
        self.step_title = step_title
        self.total_attempts = total_attempts
        self.failed_attempts = failed_attempts
        self.failure_rate = failure_rate


class QualityAlert:
    """质量告警"""

    def __init__(
        self,
        sop_id: int,
        sop_name: str,
        step_index: int,
        step_title: str,
        failure_rate: float,
        total_attempts: int,
    ):
        self.sop_id = sop_id
        self.sop_name = sop_name
        self.step_index = step_index
        self.step_title = step_title
        self.failure_rate = failure_rate
        self.total_attempts = total_attempts
        self.alert_id = f"quality-alert-{sop_id}-{step_index}-{datetime.now().strftime('%Y%m%d%H%M%S')}"


class SOPQualityMonitor:
    """SOP 质量监控服务 - P2-3-4

    职责：
    - 定期检查 SOP 步骤失败率
    - 失败率 > 40% 时创建审核工单
    - 避免重复创建工单
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.failure_threshold = FAILURE_RATE_THRESHOLD

    async def check_sop_quality(
        self,
        sop_id: int,
        time_range_days: int = 30,
    ) -> list[QualityAlert]:
        """
        检查 SOP 质量

        Args:
            sop_id: SOP ID
            time_range_days: 检查时间范围（天）

        Returns:
            告警列表
        """
        # 获取 SOP 信息
        sop_result = await self.db.execute(
            select(SOP).where(SOP.id == sop_id)
        )
        sop = sop_result.scalar_one_or_none()
        if not sop:
            return []

        # 获取所有步骤
        steps_result = await self.db.execute(
            select(SOPStep)
            .where(SOPStep.sop_id == sop_id)
            .order_by(SOPStep.step_index)
        )
        steps = steps_result.scalars().all()

        # 计算每个步骤的失败率
        alerts = []
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=time_range_days)

        for step in steps:
            stats = await self._calculate_step_failure_rate(
                sop_id, step.step_index, cutoff_date
            )

            if stats and stats.failure_rate > self.failure_threshold:
                # 检查是否已存在未处理的工单
                existing_alert = await self._check_existing_alert(
                    sop_id, step.step_index
                )

                if not existing_alert:
                    alert = QualityAlert(
                        sop_id=sop_id,
                        sop_name=sop.name,
                        step_index=step.step_index,
                        step_title=step.title,
                        failure_rate=stats.failure_rate,
                        total_attempts=stats.total_attempts,
                    )
                    alerts.append(alert)
                    logger.warning(
                        f"[P2-3-4] Quality alert: SOP {sop_id} step {step.step_index} "
                        f"failure rate {stats.failure_rate:.1f}% > {self.failure_threshold}%"
                    )

        return alerts

    async def _calculate_step_failure_rate(
        self,
        sop_id: int,
        step_index: int,
        cutoff_date: datetime,
    ) -> Optional[StepFailureStats]:
        """计算步骤失败率"""
        # 获取该 SOP 的所有任务
        task_query = (
            select(Assignment.task_id)
            .join(Assignment, Assignment.id == AssignmentAttempt.assignment_id)
            .where(Assignment.sop_id == sop_id)
            .distinct()
        )
        task_result = await self.db.execute(task_query)
        task_ids = [row[0] for row in task_result.all()]

        if not task_ids:
            return None

        # 获取该步骤的事件统计
        # 假设步骤失败会记录为 error 或 skipped 事件
        failed_query = (
            select(func.count(Event.id))
            .where(
                and_(
                    Event.task_id.in_(task_ids),
                    Event.step_index == step_index,
                    Event.created_at >= cutoff_date,
                    or_(
                        Event.event_type == EventType.ERROR,
                        Event.event_type == EventType.STEP_SKIPPED,
                    ),
                )
            )
        )
        failed_result = await self.db.execute(failed_query)
        failed_count = failed_result.scalar() or 0

        # 获取总尝试次数
        total_query = (
            select(func.count(AssignmentAttempt.id))
            .join(Assignment, Assignment.id == AssignmentAttempt.assignment_id)
            .where(
                and_(
                    Assignment.sop_id == sop_id,
                    AssignmentAttempt.created_at >= cutoff_date,
                )
            )
        )
        total_result = await self.db.execute(total_query)
        total_count = total_result.scalar() or 0

        if total_count == 0:
            return None

        failure_rate = (failed_count / total_count) * 100

        # 获取步骤标题
        step_result = await self.db.execute(
            select(SOPStep.title).where(
                and_(SOPStep.sop_id == sop_id, SOPStep.step_index == step_index)
            )
        )
        step_title = step_result.scalar_one_or_none() or f"Step {step_index}"

        return StepFailureStats(
            step_index=step_index,
            step_title=step_title,
            total_attempts=total_count,
            failed_attempts=failed_count,
            failure_rate=failure_rate,
        )

    async def _check_existing_alert(
        self,
        sop_id: int,
        step_index: int,
    ) -> bool:
        """检查是否已存在未处理的告警"""

        # 暂时返回 False，允许重复创建
        # 实际实现应该查询 incidents 或 approvals 表
        return False

    async def create_quality_ticket(
        self,
        alert: QualityAlert,
        created_by_user_id: Optional[int] = None,
    ) -> dict:
        """
        创建质量审核工单

        Args:
            alert: 质量告警
            created_by_user_id: 创建人用户 ID

        Returns:
            工单信息
        """

        # 这里只是一个示例实现
        ticket = {
            "ticket_id": alert.alert_id,
            "type": "sop_quality_review",
            "sop_id": alert.sop_id,
            "sop_name": alert.sop_name,
            "step_index": alert.step_index,
            "step_title": alert.step_title,
            "failure_rate": alert.failure_rate,
            "total_attempts": alert.total_attempts,
            "status": "pending_review",
            "created_at": datetime.now().isoformat(),
            "created_by": created_by_user_id,
        }

        logger.info(
            f"[P2-3-4] Created quality ticket: {ticket['ticket_id']} "
            f"for SOP {alert.sop_id} step {alert.step_index}"
        )

        return ticket

    async def run_quality_check(
        self,
        time_range_days: int = 30,
    ) -> list[dict]:
        """
        运行全量质量检查

        Args:
            time_range_days: 检查时间范围（天）

        Returns:
            创建的工单列表
        """
        # 获取所有活跃的 SOP
        sop_query = select(SOP).where(SOP.is_active == True)  # noqa: E712
        sop_result = await self.db.execute(sop_query)
        sops = sop_result.scalars().all()

        all_alerts = []
        created_tickets = []

        for sop in sops:
            alerts = await self.check_sop_quality(sop.id, time_range_days)
            all_alerts.extend(alerts)

            for alert in alerts:
                ticket = await self.create_quality_ticket(alert)
                created_tickets.append(ticket)

        logger.info(
            f"[P2-3-4] Quality check complete: {len(all_alerts)} alerts, "
            f"{len(created_tickets)} tickets created"
        )

        return created_tickets
