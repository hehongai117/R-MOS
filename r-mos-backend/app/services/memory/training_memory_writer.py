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
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.training_submission import TrainingSubmission
from app.models.training import TrainingSession
from app.models.conversation import ConversationTurn
from app.services.memory import SkillProfileService
from app.services.memory.hub import MemoryHub

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
        try:
            # 1. 从 conversation_turns 表获取本 session 的对话
            result = await self.db.execute(
                select(ConversationTurn).where(
                    ConversationTurn.session_id == submission.session_id
                ).order_by(ConversationTurn.created_at)
            )
            turns = result.scalars().all()

            if not turns:
                logger.info(f"[UF-11] No conversation turns found for session {submission.session_id}")
                return

            # 构建对话文本
            conversation_text = "\n".join(
                f"{turn.role}: {turn.content[:200]}"
                for turn in turns
            )

            # 2. 调用 LLM 生成摘要
            summary = await self._generate_summary_with_llm(conversation_text)

            if not summary:
                logger.warning(f"[UF-11] Failed to generate summary for session {submission.session_id}")
                return

            # 3. 写入 MemoryHub
            memory_hub = MemoryHub()
            trace_id = f"trace-{uuid.uuid4().hex[:12]}"

            await memory_hub.write(
                session_id=submission.session_id,
                data={
                    "type": "conversation_summary",
                    "summary": summary,
                    "turn_count": len(turns),
                    "submission_id": submission.submission_id,
                },
                user_id=str(submission.user_id),
                trace_id=trace_id,
                db=self.db,
                is_long_term=True,
            )

            logger.info(
                f"[UF-11] Conversation summary written for session {submission.session_id}: "
                f"{summary[:100]}..."
            )

        except Exception as e:
            logger.error(
                f"[UF-11] Failed to write conversation summary "
                f"for submission {submission.submission_id}: {e}"
            )

    async def _generate_summary_with_llm(self, conversation_text: str) -> str:
        """使用 LLM 生成对话摘要"""
        try:
            from app.services.llm.router import LLMRouter, LLMProvider
            from app.core.config import settings

            router = LLMRouter()

            prompt = f"""请将以下对话压缩为 2-3 句话的摘要，只保留关键信息：

{conversation_text}

请直接输出摘要，不要有额外解释。"""

            response = await router.chat(
                messages=[{"role": "user", "content": prompt}],
                provider=LLMProvider.DEEPSEEK,
                model=settings.LLM_MODEL_ADVANCED,
                temperature=0.3,
                max_tokens=200,
            )

            return response.content.strip()

        except Exception as e:
            logger.warning(f"[UF-11] LLM summary generation failed: {e}")
            # Fallback: 简单截取
            lines = conversation_text.split("\n")
            return f"对话共 {len(lines)} 轮，主要涉及训练操作和问题解答。"

    async def _precompute_next_recommendation(self, user_id: int) -> None:
        """UF-11-a-6: 下次推荐预计算

        基于更新后的薄弱点和技能等级，预先计算下次推荐的训练类型
        缓存到 Redis（TTL 24h）
        """
        try:
            # 1. 获取更新后的薄弱点
            skill_service = SkillProfileService(self.db)
            weak_steps = await skill_service.get_weak_steps(
                user_id=user_id,
                unresolved_only=True,
                limit=10,
            )

            # 2. 获取技能等级
            profile = await skill_service.get_profile(user_id)

            if not profile:
                logger.info(f"[UF-11] No skill profile found for user {user_id}")
                return

            # 3. 生成推荐
            recommendation = self._generate_recommendation(
                weak_steps=weak_steps,
                profile=profile,
            )

            # 4. 缓存到 Redis (使用 MemoryHub 的短期记忆)
            memory_hub = MemoryHub()
            cache_key = f"recommendation:{user_id}"

            # 使用 short_term 写入 Redis
            memory_hub.short_term._ttl = 86400  # 24 小时

            success = memory_hub.short_term.write(
                session_id=cache_key,
                data=recommendation,
            )

            if success:
                logger.info(
                    f"[UF-11] Recommendation precomputed for user {user_id}: "
                    f"{recommendation.get('recommended_type', 'unknown')}"
                )
            else:
                logger.warning(f"[UF-11] Failed to cache recommendation for user {user_id}")

        except Exception as e:
            logger.error(f"[UF-11] Failed to precompute recommendation for user {user_id}: {e}")

    def _generate_recommendation(
        self,
        weak_steps: list,
        profile,
    ) -> dict:
        """基于薄弱点和技能画像生成推荐"""
        # 分析薄弱点
        weak_step_ids = [ws.step_id for ws in weak_steps]
        weak_sop_ids = [ws.sop_id for ws in weak_steps if ws.sop_id]

        # 分析技能等级
        scores = {
            "safety": profile.score_safety or 0,
            "procedure": profile.score_procedure or 0,
            "precision": profile.score_precision or 0,
            "efficiency": profile.score_efficiency or 0,
            "tools": profile.score_tools or 0,
        }

        # 找出最弱的维度
        weakest_dimension = min(scores, key=scores.get)
        weakest_score = scores[weakest_dimension]

        # 根据最弱维度确定推荐类型
        dimension_to_type = {
            "safety": "安全规范训练",
            "procedure": "步骤规范训练",
            "precision": "操作精度训练",
            "efficiency": "时间效率训练",
            "tools": "工具使用训练",
        }

        # 如果有未解决的薄弱点，优先推荐薄弱点相关的训练
        if weak_steps:
            recommended_type = f"薄弱点专项训练 ({len(weak_steps)} 个待改进步骤)"
            reason = f"您有 {len(weak_steps)} 个未解决的薄弱步骤，需要重点练习"
        elif weakest_score < 60:
            recommended_type = dimension_to_type.get(weakest_dimension, "综合训练")
            reason = f"您的{weakest_dimension}维度评分较低({weakest_score:.1f})，建议加强"
        else:
            recommended_type = "综合训练"
            reason = "您的各项技能较为均衡，建议综合练习"

        # 生成推荐的具体步骤
        recommended_steps = weak_step_ids[:3] if weak_step_ids else []

        return {
            "recommended_type": recommended_type,
            "reason": reason,
            "weak_dimensions": [weakest_dimension] if weakest_score < 60 else [],
            "weak_step_count": len(weak_steps),
            "recommended_steps": recommended_steps,
            "current_level": profile.overall_level or 1,
            "scores": scores,
        }


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
