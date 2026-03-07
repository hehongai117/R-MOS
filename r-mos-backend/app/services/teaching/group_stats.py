"""
P2-3: Teaching Group Statistics Service
匿名群体统计服务

职责：
- 按学员级别聚合统计（脱敏）
- 返回同级均值/分位数
- 确保隐私保护（最小组大小限制）
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.teaching import AssignmentAttempt, Assignment
from app.models.task import Task
from app.models.user import User
from app.models.rbac import UserRole, Role

logger = logging.getLogger(__name__)

# 隐私保护：最小组大小（低于此值不返回统计数据）
MIN_GROUP_SIZE = 5


class GroupStatsResult:
    """群体统计数据结果"""

    def __init__(
        self,
        level: str,
        count: int,
        avg_score: Optional[float] = None,
        median_score: Optional[float] = None,
        p75_score: Optional[float] = None,
        p90_score: Optional[float] = None,
        pass_rate: Optional[float] = None,
        avg_duration_seconds: Optional[float] = None,
        step_failure_rates: Optional[dict] = None,
    ):
        self.level = level
        self.count = count
        self.avg_score = avg_score
        self.median_score = median_score
        self.p75_score = p75_score
        self.p90_score = p90_score
        self.pass_rate = pass_rate
        self.avg_duration_seconds = avg_duration_seconds
        self.step_failure_rates = step_failure_rates

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "count": self.count,
            "avg_score": round(self.avg_score, 2) if self.avg_score else None,
            "median_score": round(self.median_score, 2) if self.median_score else None,
            "p75_score": round(self.p75_score, 2) if self.p75_score else None,
            "p90_score": round(self.p90_score, 2) if self.p90_score else None,
            "pass_rate": round(self.pass_rate, 2) if self.pass_rate else None,
            "avg_duration_seconds": round(self.avg_duration_seconds, 0) if self.avg_duration_seconds else None,
            "step_failure_rates": self.step_failure_rates,
        }


class GroupStatsService:
    """群体统计服务 - P2-3

    职责：
    - 按学员级别聚合统计
    - 计算均值、中位数、分位数
    - 隐私保护：低于最小组大小不返回
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_group_stats(
        self,
        sop_id: Optional[int] = None,
        time_range_days: Optional[int] = None,
    ) -> list[GroupStatsResult]:
        """
        获取群体统计数据

        Args:
            sop_id: 可选，按 SOP 筛选
            time_range_days: 可选，按时间范围筛选（天数）

        Returns:
            按级别分组的统计数据列表
        """
        # 构建基础查询条件
        conditions = [
            AssignmentAttempt.status == "completed",
            AssignmentAttempt.score.isnot(None),
        ]

        if sop_id:
            # 通过 Assignment 关联 SOP
            conditions.append(
                Assignment.assignment_id.in_(
                    select(Assignment.id).where(Assignment.sop_id == sop_id)
                )
            )

        if time_range_days:
            cutoff_date = datetime.now() - timedelta(days=time_range_days)
            conditions.append(AssignmentAttempt.created_at >= cutoff_date)

        # 查询所有完成的尝试
        query = (
            select(
                UserRole.role_id,
                Role.name.label("level"),
                func.count(AssignmentAttempt.id).label("count"),
                func.avg(AssignmentAttempt.score).label("avg_score"),
                func.avg(
                    func.extract('epoch', Task.completed_at - Task.created_at)
                ).label("avg_duration"),
            )
            .join(User, User.id == AssignmentAttempt.student_id)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .join(Task, Task.id == AssignmentAttempt.task_id)
            .join(Assignment, Assignment.id == AssignmentAttempt.assignment_id)
            .where(and_(*conditions))
            .group_by(UserRole.role_id, Role.name)
        )

        result = await self.db.execute(query)
        rows = result.all()

        # 处理结果
        stats_list = []
        for row in rows:
            # 隐私保护：低于最小组大小不返回
            if row.count < MIN_GROUP_SIZE:
                logger.info(f"[P2-3] Skipping level {row.level}: count {row.count} < {MIN_GROUP_SIZE}")
                continue

            # 通过的判断：score >= 60
            pass_query = (
                select(func.count(AssignmentAttempt.id))
                .join(User, User.id == AssignmentAttempt.student_id)
                .join(UserRole, UserRole.user_id == User.id)
                .join(Role, Role.id == UserRole.role_id)
                .join(Task, Task.id == AssignmentAttempt.task_id)
                .join(Assignment, Assignment.id == AssignmentAttempt.assignment_id)
                .where(
                    and_(
                        *conditions,
                        UserRole.role_id == row.role_id,
                        AssignmentAttempt.score >= 60,
                    )
                )
            )
            pass_result = await self.db.execute(pass_query)
            pass_count = pass_result.scalar() or 0
            pass_rate = (pass_count / row.count * 100) if row.count > 0 else 0

            stats = GroupStatsResult(
                level=row.level,
                count=row.count,
                avg_score=float(row.avg_score) if row.avg_score else None,
                avg_duration_seconds=float(row.avg_duration) if row.avg_duration else None,
                pass_rate=pass_rate,
            )
            stats_list.append(stats)

        # 计算分位数
        for stats in stats_list:
            percentiles = await self._calculate_percentiles(
                stats.level, sop_id, time_range_days
            )
            stats.median_score = percentiles.get("p50")
            stats.p75_score = percentiles.get("p75")
            stats.p90_score = percentiles.get("p90")

        return stats_list

    async def _calculate_percentiles(
        self,
        level: str,
        sop_id: Optional[int],
        time_range_days: Optional[int],
    ) -> dict:
        """计算分位数"""
        # 获取该级别的所有分数
        conditions = [
            AssignmentAttempt.status == "completed",
            AssignmentAttempt.score.isnot(None),
            Role.name == level,
        ]

        if sop_id:
            conditions.append(
                Assignment.assignment_id.in_(
                    select(Assignment.id).where(Assignment.sop_id == sop_id)
                )
            )

        if time_range_days:
            cutoff_date = datetime.now() - timedelta(days=time_range_days)
            conditions.append(AssignmentAttempt.created_at >= cutoff_date)

        query = (
            select(AssignmentAttempt.score)
            .join(User, User.id == AssignmentAttempt.student_id)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .join(Assignment, Assignment.id == AssignmentAttempt.assignment_id)
            .where(and_(*conditions))
            .order_by(AssignmentAttempt.score)
        )

        result = await self.db.execute(query)
        scores = [row[0] for row in result.all()]

        if not scores:
            return {}

        n = len(scores)
        return {
            "p50": scores[int(n * 0.5)] if n > 0 else None,
            "p75": scores[int(n * 0.75)] if n > 0 else None,
            "p90": scores[int(n * 0.90)] if n > 0 else None,
        }

    async def get_comparison_context(
        self,
        student_id: int,
        sop_id: Optional[int] = None,
    ) -> dict:
        """
        获取学员的同伴对比上下文

        Args:
            student_id: 学员 ID
            sop_id: 可选，按 SOP 筛选

        Returns:
            包含学员自身统计和群体统计的对比数据
        """
        # 获取学员级别
        user_role_query = (
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == student_id)
        )
        result = await self.db.execute(user_role_query)
        student_level = result.scalar_one_or_none()

        if not student_level:
            return {"error": "Student level not found"}

        # 获取该级别的群体统计
        group_stats = await self.get_group_stats(sop_id=sop_id)
        level_stats = next((s for s in group_stats if s.level == student_level), None)

        if not level_stats:
            return {"error": f"No group stats for level {student_level}"}

        # 获取学员个人统计
        student_stats = await self._get_student_stats(student_id, sop_id)

        # 构建对比
        comparison = {
            "student_level": student_level,
            "group_stats": level_stats.to_dict(),
            "student_stats": student_stats,
            "comparison": {
                "score_vs_group": (
                    student_stats["avg_score"] - level_stats.avg_score
                    if student_stats.get("avg_score") and level_stats.avg_score
                    else None
                ),
                "pass_rate_vs_group": (
                    student_stats["pass_rate"] - level_stats.pass_rate
                    if student_stats.get("pass_rate") and level_stats.pass_rate
                    else None
                ),
            },
        }

        return comparison

    async def _get_student_stats(
        self,
        student_id: int,
        sop_id: Optional[int],
    ) -> dict:
        """获取学员个人统计"""
        conditions = [
            AssignmentAttempt.student_id == student_id,
            AssignmentAttempt.status == "completed",
            AssignmentAttempt.score.isnot(None),
        ]

        if sop_id:
            conditions.append(
                Assignment.assignment_id.in_(
                    select(Assignment.id).where(Assignment.sop_id == sop_id)
                )
            )

        # 计算平均分
        avg_query = (
            select(func.avg(AssignmentAttempt.score))
            .join(Assignment, Assignment.id == AssignmentAttempt.assignment_id)
            .where(and_(*conditions))
        )
        avg_result = await self.db.execute(avg_query)
        avg_score = avg_result.scalar_one()

        # 计算通过率
        pass_query = (
            select(func.count(AssignmentAttempt.id))
            .join(Assignment, Assignment.id == AssignmentAttempt.assignment_id)
            .where(and_(*conditions, AssignmentAttempt.score >= 60))
        )
        pass_result = await self.db.execute(pass_query)
        pass_count = pass_result.scalar() or 0

        # 计算总尝试次数
        count_query = (
            select(func.count(AssignmentAttempt.id))
            .join(Assignment, Assignment.id == AssignmentAttempt.assignment_id)
            .where(and_(*conditions))
        )
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar() or 0

        return {
            "avg_score": float(avg_score) if avg_score else None,
            "pass_rate": (pass_count / total_count * 100) if total_count > 0 else None,
            "total_attempts": total_count,
        }
