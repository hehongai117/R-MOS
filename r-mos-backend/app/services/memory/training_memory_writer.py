"""
UF-11: Training Memory Writer
训练记忆写入触发器

职责：
- 薄弱点更新
- 技能画像更新
- 训练历史写入
- 对话摘要写入情景记忆
- 下次推荐预计算
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.training_submission import TrainingSubmission
from app.models.training import TrainingSession
from app.services.memory import SkillProfileService

logger = logging.getLogger(__name__)


class TrainingMemoryWriter:
    """训练记忆写入器 - UF-11

    作为后台异步任务执行，不阻塞反馈页面展示
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def process_submission(self, submission_id: str) -> bool:
        """UF-11-a: 处理提交记忆写入

        按顺序执行 5 个步骤

        Args:
            submission_id: 提交ID

        Returns:
            bool: 是否成功
        """
        try:
            # 获取提交包
            result = await self.db.execute(
                select(TrainingSubmission).where(
                    TrainingSubmission.submission_id == submission_id
                )
            )
            submission = result.scalar_one_or_none()

            if not submission:
                logger.error(f"[UF-11] Submission not found: {submission_id}")
                return False

            payload = submission.payload
            user_id = submission.user_id
            steps_summary = payload.get("steps_summary", [])

            # Step 1: 薄弱点更新 (优先级最高)
            await self._update_weak_steps(user_id, steps_summary)

            # Step 2: 技能画像更新
            skill_service = SkillProfileService(self.db)
            await skill_service.update_scores(user_id, payload)

            # Step 3: 训练历史写入
            await self._update_training_history(submission)

            # Step 4: 对话摘要写入情景记忆
            await self._write_conversation_summary(submission)

            # Step 5: 下次推荐预计算
            await self._precompute_next_recommendation(user_id)

            logger.info(f"[UF-11] Memory write completed for submission {submission_id}")
            return True

        except Exception as e:
            logger.error(f"[UF-11] Memory write failed for {submission_id}: {e}")
            return False

    async def _update_weak_steps(self, user_id: int, steps_summary: list[dict]) -> None:
        """UF-11-a-2: 薄弱点更新"""
        skill_service = SkillProfileService(self.db)

        for step in steps_summary:
            step_id = step.get("step_id", "")
            status = step.get("status", "")
            attempt_count = max(int(step.get("attempt_count", 0)), 0)

            if not step_id:
                continue

            if status == "fail":
                # 若最终状态仍是 fail，则把该步骤累计尝试次数计入失败数。
                await skill_service.update_weak_step(
                    user_id=user_id,
                    step_id=step_id,
                    failed=True,
                    fail_increment=max(attempt_count, 1),
                )
            elif status == "pass":
                if attempt_count > 1:
                    # 通过前的失败尝试也计入薄弱点记忆。
                    await skill_service.update_weak_step(
                        user_id=user_id,
                        step_id=step_id,
                        failed=True,
                        fail_increment=attempt_count - 1,
                    )
                # 通过后标记该步骤已解决。
                await skill_service.update_weak_step(
                    user_id=user_id,
                    step_id=step_id,
                    failed=False,
                )

        logger.info(f"[UF-11] Updated weak steps for user {user_id}")

    async def _update_training_history(self, submission: TrainingSubmission) -> None:
        """UF-11-a-4: 训练历史写入

        更新 training_sessions 状态和最终分数
        """
        # 获取会话
        result = await self.db.execute(
            select(TrainingSession).where(
                TrainingSession.session_id == submission.session_id
            )
        )
        session = result.scalar_one_or_none()

        if session:
            session.status = "submitted"
            session.score = submission.score
            await self.db.commit()

        logger.info(f"[UF-11] Updated training history for session {submission.session_id}")

    async def _write_conversation_summary(self, submission: TrainingSubmission) -> None:
        """UF-11-a-5: 对话摘要写入情景记忆

        调用 LLM 将对话压缩为 2-3 句摘要
        写入 MemoryHub 的 pgvector 情景记忆层
        """

        # 1. 从 conversation_turns 表获取本 session 的对话
        # 2. 调用 LLM 生成摘要
        # 3. 写入 MemoryHub

        logger.info(
            f"[UF-11] Conversation summary write not implemented yet "
            f"for submission {submission.submission_id}"
        )

    async def _precompute_next_recommendation(self, user_id: int) -> None:
        """UF-11-a-6: 下次推荐预计算

        基于更新后的薄弱点和技能等级，预先计算下次推荐的训练类型
        缓存到 Redis（TTL 24h）
        """

        # 1. 获取更新后的薄弱点
        # 2. 获取技能等级
        # 3. 生成推荐
        # 4. 缓存到 Redis

        logger.info(f"[UF-11] Next recommendation precompute not implemented yet for user {user_id}")


async def trigger_memory_write(submission_id: str, db: AsyncSession) -> None:
    """触发记忆写入任务

    异步调用，不阻塞主流程
    """
    writer = TrainingMemoryWriter(db)
    success = await writer.process_submission(submission_id)

    if success:
        logger.info(f"[UF-11] Memory write triggered for {submission_id}")
    else:
        logger.error(f"[UF-11] Memory write failed for {submission_id}")
