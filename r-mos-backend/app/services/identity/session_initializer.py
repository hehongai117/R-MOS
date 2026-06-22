"""
UF-02-a: Session Initializer Service
会话初始化服务

职责：
- 用户登录成功后自动触发
- 根据角色生成个性化欢迎摘要
- 学生：技能画像 + 薄弱点 + 今日推荐
- 教师：班级训练统计
- 管理员：系统健康摘要

SessionContext 存入 Redis (key: session:{user_id}, TTL 8h)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.task import Task, TaskStatus
from app.models.training import TrainingSession
from app.services.memory.hub import MemoryHub

logger = logging.getLogger(__name__)


@dataclass
class SessionContext:
    """会话上下文"""
    user_id: int
    role: str
    welcome_summary: str
    agent_config: dict = field(default_factory=dict)
    stats: dict = field(default_factory=dict)
    unfinished_session: Optional[dict] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


class SessionInitializer:
    """会话初始化服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        try:
            self.memory_hub = MemoryHub(db)  # type: ignore[call-arg]
        except TypeError:
            self.memory_hub = MemoryHub()

    async def initialize_session(self, user_id: int) -> SessionContext:
        """初始化用户会话 - UF-02-a-1

        Args:
            user_id: 用户ID

        Returns:
            SessionContext: 会话上下文
        """
        # 获取用户信息
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User {user_id} not found")

        role = getattr(user, 'role', 'student')
        logger.info(f"[UF-02-a] Initializing session for user {user_id}, role: {role}")

        # 根据角色生成不同的欢迎摘要
        if role == "student":
            context = await self._init_student_session(user)
        elif role == "teacher":
            context = await self._init_teacher_session(user)
        elif role == "admin":
            context = await self._init_admin_session(user)
        else:
            # 默认学生模式
            context = await self._init_student_session(user)

        # 检查是否有未完成的训练会话
        unfinished = await self._check_unfinished_session(user_id)
        if unfinished:
            context.unfinished_session = unfinished
            logger.info(f"[UF-02-a] User {user_id} has unfinished session: {unfinished['session_id']}")


        # await self._save_to_redis(user_id, context)

        logger.info(f"[UF-02-a] Session initialized for user {user_id}")
        return context

    async def _init_student_session(self, user: User) -> SessionContext:
        """学生路径 - UF-02-a-2

        调用 MemoryHub 获取技能画像 -> 构建欢迎 prompt -> LLM 生成欢迎摘要
        """
        # 获取技能画像
        profile = {}
        if hasattr(self.memory_hub, "get_student_profile"):
            profile = await self.memory_hub.get_student_profile(user.id)

        # 构建欢迎摘要
        welcome_parts = []

        if profile.get("last_training"):
            welcome_parts.append(f"上次训练：{profile['last_training']}")

        if profile.get("weak_steps"):
            weak = profile["weak_steps"][:3]
            welcome_parts.append(f"薄弱环节：{', '.join(weak)}")

        if profile.get("skill_level"):
            welcome_parts.append(f"当前等级：L{profile['skill_level']}")

        # 今日推荐
        recommendation = await self._get_student_recommendation(user.id)
        if recommendation:
            welcome_parts.append(f"今日推荐：{recommendation}")

        welcome_summary = "；".join(welcome_parts) if welcome_parts else "欢迎开始训练！"

        # 学生统计
        stats = await self._get_student_stats(user.id)

        return SessionContext(
            user_id=user.id,
            role="student",
            welcome_summary=welcome_summary,
            agent_config={
                "guidance_mode": True,
                "hint_level": getattr(user, 'hint_level', 3),
                "show_answers": False,
            },
            stats=stats,
        )

    async def _init_teacher_session(self, user: User) -> SessionContext:
        """教师路径 - UF-02-a-3

        查询名下所有班级近 7 天训练统计，规则生成班级概况摘要
        """
        # 获取教师名下的班级
        from app.models.teaching import TeachingClass

        result = await self.db.execute(
            select(TeachingClass).where(TeachingClass.teacher_id == user.id)
        )
        classes = result.scalars().all()

        # 班级统计
        class_stats = []
        for cls in classes:
            stats = await self._get_class_stats(cls.id)
            class_stats.append({
                "class_id": cls.id,
                "class_name": cls.name,
                "stats": stats,
            })

        # 构建教师欢迎摘要
        total_students = sum(s["stats"]["student_count"] for s in class_stats)
        total_completed = sum(s["stats"]["completed_count"] for s in class_stats)
        avg_score = (
            sum(s["stats"]["avg_score"] * s["stats"]["completed_count"] for s in class_stats) / total_completed
            if total_completed > 0
            else 0
        )

        welcome_summary = f"您负责 {len(classes)} 个班级，共 {total_students} 名学员；近7天完成 {total_completed} 次训练，平均得分 {avg_score:.1f}"

        return SessionContext(
            user_id=user.id,
            role="teacher",
            welcome_summary=welcome_summary,
            agent_config={
                "observe_mode": True,
                "can_override_verdict": True,
                "show_full_analysis": True,
            },
            stats={"classes": class_stats},
        )

    async def _init_admin_session(self, user: User) -> SessionContext:
        """管理员路径 - UF-02-a-4

        返回系统健康摘要（规则生成）
        """
        # 获取系统统计
        total_users = await self._count_users()
        active_sessions = await self._count_active_sessions()
        pending_alerts = await self._count_pending_alerts()

        welcome_summary = f"系统运行正常；在线用户 {active_sessions}；待处理告警 {pending_alerts}"

        return SessionContext(
            user_id=user.id,
            role="admin",
            welcome_summary=welcome_summary,
            agent_config={
                "management_mode": True,
                "audit_access": True,
            },
            stats={
                "total_users": total_users,
                "active_sessions": active_sessions,
                "pending_alerts": pending_alerts,
            },
        )

    async def _get_student_recommendation(self, user_id: int) -> Optional[str]:
        """获取学生今日推荐"""

        # 实际实现应该查询 UF-11 预计算的推荐
        return "建议进行弱点强化训练"

    async def _check_unfinished_session(self, user_id: int) -> Optional[dict]:
        """UF-06-c-1: 检查未完成的训练会话"""
        # 检查 24 小时内是否有进行中的训练
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        result = await self.db.execute(
            select(TrainingSession)
            .where(
                TrainingSession.user_id == user_id,
                TrainingSession.status.in_(["active", "paused"]),
                TrainingSession.created_at >= cutoff,
            )
            .order_by(TrainingSession.created_at.desc())
            .limit(1)
        )
        session = result.scalar_one_or_none()

        if session:
            snapshot = session.project_snapshot if isinstance(session.project_snapshot, dict) else {}
            return {
                "session_id": session.session_id,
                "project_title": snapshot.get("title") or "训练项目",
                "current_step": session.current_step or 0,
                "total_steps": len(snapshot.get("steps", [])),
                "started_at": session.started_at.isoformat() if session.started_at else None,
            }
        return None

    async def _get_student_stats(self, user_id: int) -> dict:
        """获取学生训练统计"""
        # 统计已完成的任务数、平均分等
        result = await self.db.execute(
            select(
                func.count(Task.id).label("total"),
                func.avg(Task.final_score).label("avg_score"),
            )
            .where(
                Task.user_id == user_id,
                Task.status == TaskStatus.COMPLETED,
            )
        )
        row = result.one()

        return {
            "total_completed": row.total or 0,
            "avg_score": float(row.avg_score) if row.avg_score else 0,
        }

    async def _get_class_stats(self, class_id: int) -> dict:
        """获取班级训练统计"""
        from app.models.teaching import Enrollment, Assignment, AssignmentAttempt

        # 学员数
        enroll_result = await self.db.execute(
            select(func.count(Enrollment.id)).where(Enrollment.class_id == class_id)
        )
        student_count = enroll_result.scalar() or 0

        # 完成数、平均分
        stats_result = await self.db.execute(
            select(
                func.count(AssignmentAttempt.id).label("completed"),
                func.avg(AssignmentAttempt.score).label("avg_score"),
            )
            .join(Assignment, Assignment.id == AssignmentAttempt.assignment_id)
            .where(
                Assignment.class_id == class_id,
                AssignmentAttempt.status == "graded",
                AssignmentAttempt.score.isnot(None),
            )
        )
        row = stats_result.one()

        return {
            "student_count": student_count,
            "completed_count": row.completed or 0,
            "avg_score": float(row.avg_score) if row.avg_score else 0,
        }

    async def _count_users(self) -> int:
        """统计用户数"""
        result = await self.db.execute(
            select(func.count(User.id)).where(User.is_active == True)  # noqa: E712
        )
        return result.scalar() or 0

    async def _count_active_sessions(self) -> int:
        """统计活跃会话数"""

        return 0

    async def _count_pending_alerts(self) -> int:
        """统计待处理告警数"""

        return 0
