"""
UF-06: Training Session Service
训练会话状态机服务

职责：
- 创建/更新/暂停/恢复会话
- 会话状态流转
- 中断续训支持
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.training import TrainingSession, SessionStepRecord

logger = logging.getLogger(__name__)


class SessionService:
    """会话状态机服务 - UF-06"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(
        self,
        user_id: int,
        project_id: str,
        project_snapshot: dict,
        ab_group: Optional[str] = None,
    ) -> str:
        """UF-06-b-1: 创建新会话

        Args:
            user_id: 用户ID
            project_id: 项目ID
            project_snapshot: 项目配置快照
            ab_group: A/B测试分组

        Returns:
            session_id: 会话ID
        """
        session_id = str(uuid.uuid4())

        # 创建会话记录
        session = TrainingSession(
            session_id=session_id,
            project_id=project_id,
            user_id=user_id,
            status="active",
            current_step=0,
            project_snapshot=project_snapshot,
            started_at=datetime.utcnow(),
            total_duration=0,
            ab_group=ab_group,
        )

        self.db.add(session)
        await self.db.commit()

        logger.info(f"[UF-06] Created session {session_id} for user {user_id}")
        return session_id

    async def initialize_steps(self, session_id: str, steps: list[dict]) -> None:
        """为真实训练工作台初始化步骤记录。"""
        existing_result = await self.db.execute(
            select(SessionStepRecord).where(SessionStepRecord.session_id == session_id)
        )
        if existing_result.scalars().first() is not None:
            return

        for index, step in enumerate(steps):
            self.db.add(
                SessionStepRecord(
                    record_id=str(uuid.uuid4()),
                    session_id=session_id,
                    step_id=str(step.get("id") or f"step-{index + 1}"),
                    step_index=int(step.get("step_index", index)),
                    status="pending",
                    attempt_count=0,
                    tools_confirmed=[],
                    evidence=None,
                    verdict_result=None,
                )
            )

        await self.db.commit()
        logger.info(f"[UF-06] Initialized {len(steps)} steps for session {session_id}")

    async def update_step(
        self,
        session_id: str,
        step_id: str,
        step_index: int,
        status: str,
        attempt_count: int = 0,
        tools_confirmed: Optional[list] = None,
        evidence: Optional[dict] = None,
        verdict_result: Optional[dict] = None,
        duration_sec: Optional[int] = None,
    ) -> str:
        """UF-06-b-2: 写入步骤操作记录（checkpoint）

        每步操作完成后自动 checkpoint

        Args:
            session_id: 会话ID
            step_id: 步骤ID
            step_index: 步骤索引
            status: 步骤状态 (pending/in_progress/pass/fail/skip)
            attempt_count: 尝试次数
            tools_confirmed: 工具确认列表
            evidence: 证据数据
            verdict_result: 评判结果
            duration_sec: 耗时(秒)

        Returns:
            record_id: 步骤记录ID
        """
        # 查询是否已存在记录
        result = await self.db.execute(
            select(SessionStepRecord).where(
                and_(
                    SessionStepRecord.session_id == session_id,
                    SessionStepRecord.step_id == step_id,
                )
            )
        )
        existing = result.scalar_one_or_none()

        record_id = existing.record_id if existing else str(uuid.uuid4())
        now = datetime.utcnow()

        if existing:
            # 更新已有记录
            existing.status = status
            existing.attempt_count = attempt_count
            existing.tools_confirmed = tools_confirmed
            existing.evidence = evidence
            existing.verdict_result = verdict_result
            existing.duration_sec = duration_sec
            if status in ("pass", "fail", "skip"):
                existing.completed_at = now
        else:
            # 创建新记录
            record = SessionStepRecord(
                record_id=record_id,
                session_id=session_id,
                step_id=step_id,
                step_index=step_index,
                status=status,
                attempt_count=attempt_count,
                tools_confirmed=tools_confirmed,
                evidence=evidence,
                verdict_result=verdict_result,
                duration_sec=duration_sec,
                started_at=now if status != "pending" else None,
                completed_at=now if status in ("pass", "fail", "skip") else None,
            )
            self.db.add(record)

        # 更新会话当前步骤
        await self.db.execute(
            update(TrainingSession)
            .where(TrainingSession.session_id == session_id)
            .values(current_step=step_index + 1)
        )

        await self.db.commit()

        logger.info(
            f"[UF-06] Updated step for session {session_id}: "
            f"step={step_id}, status={status}, attempt={attempt_count}"
        )
        return record_id

    async def pause(self, session_id: str) -> Optional[TrainingSession]:
        """UF-06-b-1: 暂停会话

        状态 → PAUSED，记录 paused_at

        Returns:
            更新后的会话
        """
        result = await self.db.execute(
            select(TrainingSession).where(
                TrainingSession.session_id == session_id
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            logger.warning(f"[UF-06] Session not found: {session_id}")
            return None

        if session.status != "active":
            logger.warning(f"[UF-06] Cannot pause session {session_id}, status: {session.status}")
            return session

        # 计算已持续时长
        if session.started_at:
            duration = int((datetime.utcnow() - session.started_at).total_seconds())
            session.total_duration += duration

        session.status = "paused"
        session.paused_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(session)

        logger.info(f"[UF-06] Paused session {session_id}")
        return session

    async def resume(self, session_id: str) -> Optional[TrainingSession]:
        """UF-06-b-1: 恢复会话

        状态 → ACTIVE，重置 started_at

        Returns:
            更新后的会话
        """
        result = await self.db.execute(
            select(TrainingSession).where(
                TrainingSession.session_id == session_id
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            logger.warning(f"[UF-06] Session not found: {session_id}")
            return None

        if session.status != "paused":
            logger.warning(f"[UF-06] Cannot resume session {session_id}, status: {session.status}")
            return session

        session.status = "active"
        session.started_at = datetime.utcnow()
        session.paused_at = None

        await self.db.commit()
        await self.db.refresh(session)

        logger.info(f"[UF-06] Resumed session {session_id}")
        return session

    async def get_session(self, session_id: str) -> Optional[TrainingSession]:
        """UF-06-b-3: 获取会话状态和步骤记录

        供工作台恢复使用

        Returns:
            会话及步骤记录
        """
        result = await self.db.execute(
            select(TrainingSession).where(
                TrainingSession.session_id == session_id
            )
        )
        return result.scalar_one_or_none()

    async def get_session_with_steps(self, session_id: str) -> Optional[dict]:
        """获取会话及完整步骤记录

        Returns:
            包含会话和步骤记录的字典
        """
        result = await self.db.execute(
            select(TrainingSession).where(
                TrainingSession.session_id == session_id
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            return None

        steps_result = await self.db.execute(
            select(SessionStepRecord)
            .where(SessionStepRecord.session_id == session_id)
            .order_by(SessionStepRecord.step_index)
        )
        steps = steps_result.scalars().all()

        return {
            "session": session,
            "steps": steps,
        }

    async def abandon(self, session_id: str) -> bool:
        """UF-06-c-4: 放弃会话

        状态 → ABANDONED，已完成步骤记录保留

        Returns:
            是否成功
        """
        result = await self.db.execute(
            select(TrainingSession).where(
                TrainingSession.session_id == session_id
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            logger.warning(f"[UF-06] Session not found: {session_id}")
            return False

        # 计算最终时长
        if session.started_at and session.status == "active":
            duration = int((datetime.utcnow() - session.started_at).total_seconds())
            session.total_duration += duration

        session.status = "abandoned"

        await self.db.commit()

        logger.info(f"[UF-06] Abandoned session {session_id}")
        return True

    async def expire_stale(self) -> int:
        """UF-06-b-4: 定时任务，将超过 48h 未操作的 ACTIVE 会话标记为 EXPIRED

        Returns:
            过期会话数量
        """
        cutoff = datetime.utcnow() - timedelta(hours=48)

        # 查询并更新
        result = await self.db.execute(
            select(TrainingSession).where(
                and_(
                    TrainingSession.status == "active",
                    TrainingSession.started_at < cutoff,
                )
            )
        )
        sessions = result.scalars().all()

        for session in sessions:
            # 计算最终时长
            if session.started_at:
                duration = int((datetime.utcnow() - session.started_at).total_seconds())
                session.total_duration += duration
            session.status = "expired"

        await self.db.commit()

        count = len(sessions)
        logger.info(f"[UF-06] Expired {count} stale sessions")
        return count

    async def submit(
        self,
        session_id: str,
        submit_type: str = "manual",
        score: Optional[float] = None,
    ) -> Optional[dict]:
        """UF-08: 提交训练

        Args:
            session_id: 会话ID
            submit_type: 提交类型 (manual/timeout/teacher/abandoned)
            score: 得分

        Returns:
            提交包
        """
        result = await self.db.execute(
            select(TrainingSession).where(
                TrainingSession.session_id == session_id
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            logger.warning(f"[UF-06] Session not found: {session_id}")
            return None

        # 计算最终时长
        if session.started_at:
            duration = int((datetime.utcnow() - session.started_at).total_seconds())
            session.total_duration += duration

        session.status = "submitted"
        session.submitted_at = datetime.utcnow()
        session.submit_type = submit_type
        if score is not None:
            session.score = score

        await self.db.commit()

        logger.info(f"[UF-06] Submitted session {session_id}, type: {submit_type}, score: {score}")

        return {
            "session_id": session_id,
            "status": "submitted",
            "submit_type": submit_type,
            "score": score,
            "total_duration": session.total_duration,
        }

    async def get_user_active_session(self, user_id: int) -> Optional[TrainingSession]:
        """获取用户当前活跃会话

        Returns:
            活跃会话或None
        """
        result = await self.db.execute(
            select(TrainingSession).where(
                and_(
                    TrainingSession.user_id == user_id,
                    TrainingSession.status.in_(["active", "paused"]),
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_user_sessions(
        self,
        user_id: int,
        status: Optional[str] = None,
        limit: int = 10,
    ) -> list[TrainingSession]:
        """获取用户会话列表

        Args:
            user_id: 用户ID
            status: 状态过滤
            limit: 返回数量限制

        Returns:
            会话列表
        """
        query = select(TrainingSession).where(
            TrainingSession.user_id == user_id
        )

        if status:
            query = query.where(TrainingSession.status == status)

        query = query.order_by(TrainingSession.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())
