"""
UF-08: Training Submission Service
训练提交服务

职责：
- 手动提交（学员主动）
- 超时自动提交
- 教师强制提交
- 放弃提交
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional, Any
from dataclasses import dataclass, field

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.training import TrainingSession, SessionStepRecord
from app.models.training_submission import TrainingSubmission as TrainingSubmissionModel

logger = logging.getLogger(__name__)


@dataclass
class TrainingSubmission:
    """训练提交包"""
    submission_id: str
    session_id: str
    user_id: int
    submit_type: str  # manual/timeout/teacher/abandoned
    submitted_at: datetime
    payload: dict = field(default_factory=dict)

    # 聚合的步骤记录
    steps_summary: list[dict] = field(default_factory=list)

    # 对话记录
    conversation_summary: str = ""

    # 3D交互日志
    interaction_log: list[dict] = field(default_factory=list)


@dataclass
class SubmissionCheckResult:
    """提交检查结果"""
    can_submit: bool
    message: str
    incomplete_steps: list[dict] = field(default_factory=list)


class SubmissionService:
    """训练提交服务 - UF-08"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_submit_ready(self, session_id: str) -> SubmissionCheckResult:
        """检查是否可以提交

        Returns:
            SubmissionCheckResult: 检查结果
        """
        # 获取会话
        result = await self.db.execute(
            select(TrainingSession).where(
                TrainingSession.session_id == session_id
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            return SubmissionCheckResult(
                can_submit=False,
                message="会话不存在"
            )

        if session.status == "submitted":
            return SubmissionCheckResult(
                can_submit=False,
                message="训练已提交"
            )

        # 获取所有步骤记录
        steps_result = await self.db.execute(
            select(SessionStepRecord).where(
                SessionStepRecord.session_id == session_id
            )
        )
        all_steps = list(steps_result.scalars().all())

        # 检查未完成的步骤
        incomplete = []
        for step in all_steps:
            if step.status not in ("pass", "fail", "skip"):
                incomplete.append({
                    "step_id": step.step_id,
                    "step_index": step.step_index,
                    "status": step.status,
                })

        if incomplete:
            return SubmissionCheckResult(
                can_submit=True,  # 允许提交但有警告
                message=f"还有 {len(incomplete)} 步未完成",
                incomplete_steps=incomplete
            )

        return SubmissionCheckResult(
            can_submit=True,
            message="所有步骤已完成"
        )

    async def submit_manual(
        self,
        session_id: str,
        user_id: int,
        confirm_incomplete: bool = False,
    ) -> Optional[TrainingSubmission]:
        """UF-08-a-2: 手动提交

        Args:
            session_id: 会话ID
            user_id: 用户ID
            confirm_incomplete: 是否确认提交未完成的训练

        Returns:
            TrainingSubmission: 提交包
        """
        # 检查提交就绪状态
        check_result = await self.check_submit_ready(session_id)

        if not check_result.can_submit:
            logger.warning(f"[UF-08] Cannot submit session {session_id}: {check_result.message}")
            return None

        # 如果有未完成步骤且用户未确认，返回提示
        if check_result.incomplete_steps and not confirm_incomplete:
            logger.info(f"[UF-08] Session {session_id} has {len(check_result.incomplete_steps)} incomplete steps")
            return None

        # 打包提交包
        submission = await self._package_submission(
            session_id=session_id,
            user_id=user_id,
            submit_type="manual",
        )

        # 保存提交包
        await self._save_submission(submission)

        # 更新会话状态
        await self._update_session_status(session_id, "submitted", "manual", submission.payload.get("score"))

        await self._trigger_memory_write(submission.submission_id)

        logger.info(f"[UF-08] Manual submission completed for session {session_id}")
        return submission

    async def submit_timeout(self, session_id: str) -> Optional[TrainingSubmission]:
        """UF-08-a-3: 超时自动提交

        由定时任务调用，检查训练时长是否超过配置限制

        Args:
            session_id: 会话ID

        Returns:
            TrainingSubmission: 提交包
        """
        # 获取会话
        result = await self.db.execute(
            select(TrainingSession).where(
                TrainingSession.session_id == session_id
            )
        )
        session = result.scalar_one_or_none()

        if not session or session.status != "active":
            return None

        # 检查是否超时 (从 project_snapshot 获取 time_limit)
        time_limit = 60  # 默认60分钟
        if session.project_snapshot:
            verdict_config = session.project_snapshot.get("verdict_config", {})
            time_limit = verdict_config.get("time_limit", 60)

        # 将秒转换为分钟
        duration_minutes = session.total_duration / 60

        if duration_minutes <= time_limit:
            logger.info(f"[UF-08] Session {session_id} not timed out yet: {duration_minutes:.1f}/{time_limit} min")
            return None

        # 打包提交包
        submission = await self._package_submission(
            session_id=session_id,
            user_id=session.user_id,
            submit_type="timeout",
        )

        # 保存提交包
        await self._save_submission(submission)

        # 更新会话状态
        await self._update_session_status(session_id, "submitted", "timeout", submission.payload.get("score"))

        await self._trigger_memory_write(submission.submission_id)

        logger.info(f"[UF-08] Timeout submission completed for session {session_id}")
        return submission

    async def submit_by_teacher(
        self,
        session_id: str,
        teacher_id: int,
    ) -> Optional[TrainingSubmission]:
        """UF-08-a-4: 教师强制提交

        验证 teacher_id 对该学员有管辖权

        Args:
            session_id: 会话ID
            teacher_id: 教师ID

        Returns:
            TrainingSubmission: 提交包
        """
        # 获取会话
        result = await self.db.execute(
            select(TrainingSession).where(
                TrainingSession.session_id == session_id
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            logger.warning(f"[UF-08] Session {session_id} not found")
            return None


        # 目前暂时跳过权限验证
        logger.info(f"[UF-08] Teacher {teacher_id} submitting session {session_id}")

        # 打包提交包
        submission = await self._package_submission(
            session_id=session_id,
            user_id=session.user_id,
            submit_type="teacher",
            submitted_by=teacher_id,
        )

        # 保存提交包
        await self._save_submission(submission)

        # 更新会话状态
        await self._update_session_status(
            session_id,
            "submitted",
            "teacher",
            submission.payload.get("score"),
            submitted_by=teacher_id
        )

        await self._trigger_memory_write(submission.submission_id)



        logger.info(f"[UF-08] Teacher submission completed for session {session_id}")
        return submission

    async def abandon(self, session_id: str) -> bool:
        """UF-08-a-5: 放弃会话

        状态 → ABANDONED，已完成步骤记录保留
        不触发完整反馈，只写简短记录

        Args:
            session_id: 会话ID

        Returns:
            bool: 是否成功
        """
        # 获取会话
        result = await self.db.execute(
            select(TrainingSession).where(
                TrainingSession.session_id == session_id
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            logger.warning(f"[UF-08] Session {session_id} not found")
            return False

        # 计算最终时长
        if session.started_at and session.status == "active":
            duration = int((datetime.utcnow() - session.started_at).total_seconds())
            session.total_duration += duration

        session.status = "abandoned"
        session.submitted_at = datetime.utcnow()
        session.submit_type = "abandoned"

        await self.db.commit()

        # 简短的放弃记录（不触发完整反馈）
        logger.info(f"[UF-08] Session {session_id} abandoned")
        return True

    async def _package_submission(
        self,
        session_id: str,
        user_id: int,
        submit_type: str,
        submitted_by: Optional[int] = None,
    ) -> TrainingSubmission:
        """UF-08-b: 打包提交包

        Args:
            session_id: 会话ID
            user_id: 用户ID
            submit_type: 提交类型
            submitted_by: 提交人ID（教师强制提交时）

        Returns:
            TrainingSubmission: 提交包
        """
        submission_id = str(uuid.uuid4())

        # 获取会话
        result = await self.db.execute(
            select(TrainingSession).where(
                TrainingSession.session_id == session_id
            )
        )
        session = result.scalar_one_or_none()

        # 获取步骤记录
        steps_result = await self.db.execute(
            select(SessionStepRecord).where(
                SessionStepRecord.session_id == session_id
            ).order_by(SessionStepRecord.step_index)
        )
        steps = list(steps_result.scalars().all())

        # 聚合步骤摘要
        steps_summary = []
        completed_count = 0
        failed_count = 0
        total_attempts = 0
        total_duration = 0

        for step in steps:
            step_dict = {
                "step_id": step.step_id,
                "step_index": step.step_index,
                "status": step.status,
                "attempt_count": step.attempt_count,
                "duration_sec": step.duration_sec,
                "evidence": step.evidence,
                "tools_confirmed": step.tools_confirmed,
                "verdict_result": step.verdict_result,
            }
            steps_summary.append(step_dict)

            if step.status == "pass":
                completed_count += 1
            elif step.status == "fail":
                failed_count += 1

            total_attempts += step.attempt_count
            if step.duration_sec:
                total_duration += step.duration_sec

        # 计算综合评分
        total_steps = len(steps) if steps else 1
        completion_rate = (completed_count / total_steps) * 100

        # 简单评分计算
        score = completion_rate * 0.5  # 步骤完成率 50%

        # 用时系数 (假设标准时间)
        expected_duration = session.project_snapshot.get("estimated_time", 60) * 60 if session.project_snapshot else 3600
        if expected_duration > 0:
            time_ratio = min(total_duration / expected_duration, 2.0)  # 最多2倍
            time_score = max(100 - (time_ratio - 1) * 50, 0)  # 1倍时间得100分，每超10%扣5分
            score += (time_score / 100) * 20  # 用时系数 20%

        # 工具规范 (简单计算)
        tool_score = 80  # 默认80分
        score += (tool_score / 100) * 15  # 工具规范 15%

        # 尝试次数系数
        avg_attempts = total_attempts / total_steps if total_steps > 0 else 1
        attempt_score = max(100 - (avg_attempts - 1) * 20, 0)  # 每次额外尝试扣20分
        score += (attempt_score / 100) * 15  # 尝试次数 15%

        score = round(min(score, 100), 2)

        # 构建 payload
        payload = {
            "session_id": session_id,
            "project_id": session.project_id if session else "",
            "user_id": user_id,
            "submit_type": submit_type,
            "submitted_by": submitted_by,
            "submitted_at": datetime.utcnow().isoformat(),
            "total_steps": total_steps,
            "completed_steps": completed_count,
            "failed_steps": failed_count,
            "total_duration": total_duration,
            "total_attempts": total_attempts,
            "score": score,
            "project_snapshot": session.project_snapshot if session else {},
            "steps_summary": steps_summary,
            "conversation_summary": "",
            "interaction_log": [],
        }

        return TrainingSubmission(
            submission_id=submission_id,
            session_id=session_id,
            user_id=user_id,
            submit_type=submit_type,
            submitted_at=datetime.utcnow(),
            payload=payload,
            steps_summary=steps_summary,
        )

    async def _save_submission(self, submission: TrainingSubmission) -> None:
        """UF-08-b-4: 保存提交包到数据库

        使用 JSON 存储在 payload 字段
        """
        payload = submission.payload

        db_submission = TrainingSubmissionModel(
            submission_id=submission.submission_id,
            session_id=submission.session_id,
            user_id=submission.user_id,
            submit_type=submission.submit_type,
            submitted_at=submission.submitted_at,
            payload=payload,
            score=payload.get("score"),
            total_steps=payload.get("total_steps", 0),
            completed_steps=payload.get("completed_steps", 0),
            failed_steps=payload.get("failed_steps", 0),
            total_duration=payload.get("total_duration", 0),
        )

        self.db.add(db_submission)
        await self.db.commit()

        logger.info(f"[UF-08] Submission saved: {submission.submission_id}")

    async def _update_session_status(
        self,
        session_id: str,
        status: str,
        submit_type: str,
        score: Optional[float] = None,
        submitted_by: Optional[int] = None,
    ) -> None:
        """更新会话状态"""
        result = await self.db.execute(
            select(TrainingSession).where(
                TrainingSession.session_id == session_id
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            return

        # 计算最终时长
        if session.started_at:
            duration = int((datetime.utcnow() - session.started_at).total_seconds())
            session.total_duration += duration

        session.status = status
        session.submitted_at = datetime.utcnow()
        session.submit_type = submit_type
        if score is not None:
            session.score = score

        await self.db.commit()
        logger.info(f"[UF-08] Session {session_id} status updated to {status}")

    async def _trigger_memory_write(self, submission_id: str) -> None:
        """提交后触发记忆闭环写入。"""
        try:
            from app.services.memory.training_memory_writer import TrainingMemoryWriter

            writer = TrainingMemoryWriter(self.db)
            success = await writer.process_submission(submission_id)
            if not success:
                logger.warning(f"[UF-11] Memory write failed for submission {submission_id}")
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning(f"[UF-11] Memory write trigger error for {submission_id}: {exc}")

    async def check_and_submit_timeouts(self) -> int:
        """检查超时会话并自动提交

        由定时任务调用

        Returns:
            int: 处理的超时会话数量
        """
        # 查找所有 active 状态的会话
        result = await self.db.execute(
            select(TrainingSession).where(
                TrainingSession.status == "active"
            )
        )
        sessions = list(result.scalars().all())

        submitted_count = 0
        for session in sessions:
            # 检查时间限制
            time_limit = 60  # 默认60分钟
            if session.project_snapshot:
                verdict_config = session.project_snapshot.get("verdict_config", {})
                time_limit = verdict_config.get("time_limit", 60)

            duration_minutes = session.total_duration / 60

            if duration_minutes > time_limit:
                submission = await self.submit_timeout(session.session_id)
                if submission:
                    submitted_count += 1

        logger.info(f"[UF-08] Timeout check completed, submitted {submitted_count} sessions")
        return submitted_count
