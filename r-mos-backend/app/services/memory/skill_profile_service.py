"""
UF-10-b: Skill Profile Service
学员技能画像更新服务
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill_profile import StudentSkillProfile, StudentWeakStep
from app.models.training import TrainingSession

logger = logging.getLogger(__name__)


@dataclass
class ScoreUpdate:
    """五维评分更新"""
    score_safety: float
    score_procedure: float
    score_precision: float
    score_efficiency: float
    score_tools: float


class SkillProfileService:
    """技能画像服务 - UF-10"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_profile(self, user_id: int) -> StudentSkillProfile:
        """获取或创建技能画像"""
        result = await self.db.execute(
            select(StudentSkillProfile).where(
                StudentSkillProfile.user_id == user_id
            )
        )
        profile = result.scalar_one_or_none()

        if not profile:
            profile = StudentSkillProfile(user_id=user_id)
            self.db.add(profile)
            await self.db.commit()
            await self.db.refresh(profile)
            logger.info(f"[UF-10] Created skill profile for user {user_id}")

        return profile

    async def update_scores(
        self,
        user_id: int,
        submission: dict,
        feedback: Optional[dict] = None,
    ) -> StudentSkillProfile:
        """UF-10-b-2: 更新技能画像评分

        Args:
            user_id: 用户ID
            submission: 提交包数据
            feedback: AI 反馈数据（可选）

        Returns:
            更新后的画像
        """
        profile = await self.get_or_create_profile(user_id)

        # 从提交包提取评分数据
        steps_summary = submission.get("steps_summary", [])

        # 计算各维度评分
        scores = self._calculate_scores(steps_summary, submission)

        # 更新评分（使用移动平均）
        profile.score_safety = self._update_average(profile.score_safety, scores.score_safety)
        profile.score_procedure = self._update_average(profile.score_procedure, scores.score_procedure)
        profile.score_precision = self._update_average(profile.score_precision, scores.score_precision)
        profile.score_efficiency = self._update_average(profile.score_efficiency, scores.score_efficiency)
        profile.score_tools = self._update_average(profile.score_tools, scores.score_tools)

        # 更新统计
        profile.total_sessions += 1
        profile.total_duration += submission.get("total_duration", 0)
        profile.last_trained_at = datetime.utcnow()

        # 评估升级
        await self._check_level_up(profile)

        # 更新认证资格
        await self._update_cert_eligibility(profile)

        await self.db.commit()
        await self.db.refresh(profile)

        logger.info(f"[UF-10] Updated scores for user {user_id}: {scores}")
        return profile

    def _calculate_scores(self, steps_summary: list[dict], submission: dict) -> ScoreUpdate:
        """计算各维度评分

        基于提交包数据计算评分
        """
        if not steps_summary:
            return ScoreUpdate(
                score_safety=70.0,
                score_procedure=70.0,
                score_precision=70.0,
                score_efficiency=70.0,
                score_tools=70.0,
            )

        # 安全评分：基于失败步骤中的安全相关标签
        safety_score = 80.0
        failed_steps = [s for s in steps_summary if s.get("status") == "fail"]
        if failed_steps:
            # 有失败步骤扣分
            safety_score = max(80 - len(failed_steps) * 10, 40)

        # 步骤评分：基于完成率
        total_steps = len(steps_summary)
        completed_steps = len([s for s in steps_summary if s.get("status") == "pass"])
        procedure_score = (completed_steps / total_steps * 100) if total_steps > 0 else 0

        # 精度评分：基于尝试次数（一次通过最好）
        total_attempts = sum(s.get("attempt_count", 1) for s in steps_summary)
        avg_attempts = total_attempts / total_steps if total_steps > 0 else 1
        precision_score = max(100 - (avg_attempts - 1) * 25, 50)

        # 效率评分：基于用时
        total_duration = submission.get("total_duration", 0)
        expected_duration = submission.get("project_snapshot", {}).get("estimated_time", 60) * 60
        if expected_duration > 0:
            ratio = total_duration / expected_duration
            if ratio <= 1.0:
                efficiency_score = 100
            else:
                efficiency_score = max(100 - (ratio - 1) * 50, 50)
        else:
            efficiency_score = 80.0

        # 工具评分：基于工具确认状态
        tools_scores = []
        for step in steps_summary:
            tools_confirmed = step.get("tools_confirmed", [])
            if tools_confirmed:
                confirmed = sum(1 for t in tools_confirmed if t.get("status") == "confirmed")
                tools_scores.append(confirmed / len(tools_confirmed) * 100)
            else:
                tools_scores.append(70)  # 默认

        tools_score = sum(tools_scores) / len(tools_scores) if tools_scores else 70.0

        return ScoreUpdate(
            score_safety=round(safety_score, 2),
            score_procedure=round(procedure_score, 2),
            score_precision=round(precision_score, 2),
            score_efficiency=round(efficiency_score, 2),
            score_tools=round(tools_score, 2),
        )

    def _update_average(self, old_value: Optional[float], new_value: float) -> float:
        """使用移动平均更新评分"""
        if old_value is None:
            return new_value
        # 70% 历史 + 30% 新值
        return round(old_value * 0.7 + new_value * 0.3, 2)

    async def _check_level_up(self, profile: StudentSkillProfile) -> bool:
        """UF-10-b-3: 检查是否可以升级

        规则：五维平均分 >= 80 AND 本等级已完成训练次数 >= 5 AND 最近3次训练均通过
        """
        if profile.overall_level >= 5:
            return False

        if profile.total_sessions < 5:
            return False

        # 计算平均分
        scores = [
            profile.score_safety,
            profile.score_procedure,
            profile.score_precision,
            profile.score_efficiency,
            profile.score_tools,
        ]
        valid_scores = [s for s in scores if s is not None]
        if not valid_scores:
            return False

        avg_score = sum(valid_scores) / len(valid_scores)

        if avg_score < 80:
            return False

        recent_result = await self.db.execute(
            select(TrainingSession)
            .where(
                TrainingSession.user_id == profile.user_id,
                TrainingSession.status == "submitted",
                TrainingSession.score.isnot(None),
            )
            .order_by(TrainingSession.submitted_at.desc())
            .limit(3)
        )
        recent_sessions = list(recent_result.scalars().all())
        if len(recent_sessions) < 3:
            return False

        if not all((session.score or 0) >= 60 for session in recent_sessions):
            return False

        profile.overall_level += 1
        logger.info(f"[UF-10] User {profile.user_id} leveled up to {profile.overall_level}")
        return True

    async def _update_cert_eligibility(self, profile: StudentSkillProfile) -> None:
        """UF-10-b-4: 更新认证资格

        L3 资格：L2通过 AND 完成 L2 及以上训练 >= 5 次
        """
        # 目前简化处理
        if profile.cert_l2_passed and profile.total_sessions >= 5:
            profile.cert_l3_eligible = True

    async def update_weak_step(
        self,
        user_id: int,
        step_id: str,
        sop_id: Optional[str] = None,
        failed: bool = True,
        fail_increment: int = 1,
        fail_tags: Optional[list] = None,
    ) -> None:
        """更新薄弱步骤

        Args:
            user_id: 用户ID
            step_id: 步骤ID
            sop_id: SOP ID
            failed: 是否失败
            fail_tags: 失败标签
        """
        result = await self.db.execute(
            select(StudentWeakStep).where(
                and_(
                    StudentWeakStep.user_id == user_id,
                    StudentWeakStep.step_id == step_id,
                )
            )
        )
        weak_step = result.scalar_one_or_none()

        if failed:
            increment = max(int(fail_increment), 1)
            if weak_step:
                weak_step.fail_count += increment
                weak_step.last_failed_at = datetime.utcnow()
                weak_step.is_resolved = False

                # 合并失败标签
                if fail_tags:
                    existing_tags = weak_step.fail_tags or []
                    weak_step.fail_tags = list(set(existing_tags + fail_tags))
            else:
                weak_step = StudentWeakStep(
                    user_id=user_id,
                    step_id=step_id,
                    sop_id=sop_id,
                    fail_count=increment,
                    last_failed_at=datetime.utcnow(),
                    fail_tags=fail_tags,
                    is_resolved=False,
                )
                self.db.add(weak_step)
        else:
            # 通过：标记为已解决
            if weak_step:
                weak_step.is_resolved = True

        await self.db.commit()

    async def get_weak_steps(
        self,
        user_id: int,
        unresolved_only: bool = False,
        limit: int = 20,
    ) -> list[StudentWeakStep]:
        """获取薄弱步骤列表"""
        query = select(StudentWeakStep).where(
            StudentWeakStep.user_id == user_id
        )

        if unresolved_only:
            query = query.where(StudentWeakStep.is_resolved == False)

        query = query.order_by(StudentWeakStep.fail_count.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_profile(self, user_id: int) -> Optional[StudentSkillProfile]:
        """获取技能画像"""
        result = await self.db.execute(
            select(StudentSkillProfile).where(
                StudentSkillProfile.user_id == user_id
            )
        )
        return result.scalar_one_or_none()
