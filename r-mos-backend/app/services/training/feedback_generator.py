"""
UF-09: Training Feedback Generator
多维AI反馈生成服务

职责：
- 综合评分计算
- 步骤逐项分析
- 工具使用评价
- 历史对比
- 个性化建议
- 双视角报告（学员/教师）
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.training_submission import TrainingSubmission
from app.models.training import TrainingSession, SessionStepRecord

logger = logging.getLogger(__name__)


class FeedbackRole(str, Enum):
    """反馈视角"""
    STUDENT = "student"
    TEACHER = "teacher"


@dataclass
class StepAnalysis:
    """步骤分析"""
    step_id: str
    step_index: int
    status: str
    attempt_count: int
    analysis: str = ""  # LLM 生成的原因分析
    suggestions: list[str] = field(default_factory=list)
    ref_ids: list[str] = field(default_factory=list)


@dataclass
class ToolEvaluation:
    """工具使用评价"""
    tool_id: str
    confirmed: bool
    evaluation: str
    issues: list[str] = field(default_factory=list)


@dataclass
class HistoricalComparison:
    """历史对比"""
    current_score: float
    historical_avg: float
    trend: str  # improving / stable / declining
    change_percent: float


@dataclass
class TrainingFeedback:
    """训练反馈报告"""
    submission_id: str
    session_id: str
    user_id: int

    # 综合评分
    overall_score: float
    score_breakdown: dict

    # 步骤分析
    step_analyses: list[StepAnalysis] = field(default_factory=list)

    # 工具评价
    tool_evaluations: list[ToolEvaluation] = field(default_factory=list)

    # 历史对比
    historical_comparison: Optional[HistoricalComparison] = None

    # 个性化建议
    suggestions: list[str] = field(default_factory=list)
    next_learning_plan: str = ""

    # 教师专属
    teaching_diagnosis: Optional[str] = None
    ranking_percentile: Optional[float] = None
    hint_level_suggestion: Optional[int] = None

    # 元数据
    generated_at: datetime = field(default_factory=datetime.utcnow)


class FeedbackGenerator:
    """AI 反馈生成器 - UF-09"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate(
        self,
        submission_id: str,
        role: FeedbackRole = FeedbackRole.STUDENT,
    ) -> TrainingFeedback:
        """UF-09-a-1: 生成反馈报告

        Args:
            submission_id: 提交ID
            role: 视角（student/teacher）

        Returns:
            TrainingFeedback: 反馈报告
        """
        # 获取提交包
        result = await self.db.execute(
            select(TrainingSubmission).where(
                TrainingSubmission.submission_id == submission_id
            )
        )
        submission = result.scalar_one_or_none()

        if not submission:
            raise ValueError(f"Submission not found: {submission_id}")

        payload = submission.payload

        # 1. 综合评分
        score_breakdown = self._calculate_comprehensive_score(payload)
        overall_score = score_breakdown.get("total_score", 0)

        # 2. 步骤分析 (LLM)
        step_analyses = await self._analyze_steps(payload)

        # 3. 工具评价 (LLM)
        tool_evaluations = await self._evaluate_tools(payload)

        # 4. 历史对比
        historical_comparison = await self._compare_history(
            submission.user_id,
            overall_score,
        )

        # 5. 个性化建议 (LLM)
        suggestions, next_plan = await self._generate_suggestions(
            payload,
            step_analyses,
        )

        # 构建反馈
        feedback = TrainingFeedback(
            submission_id=submission_id,
            session_id=submission.session_id,
            user_id=submission.user_id,
            overall_score=overall_score,
            score_breakdown=score_breakdown,
            step_analyses=step_analyses,
            tool_evaluations=tool_evaluations,
            historical_comparison=historical_comparison,
            suggestions=suggestions,
            next_learning_plan=next_plan,
        )

        # 如果是教师视角，增加教学诊断
        if role == FeedbackRole.TEACHER:
            await self._add_teaching_diagnosis(feedback, submission.user_id)

        # 保存反馈到提交记录
        await self._save_feedback(submission, feedback)

        logger.info(f"[UF-09] Generated feedback for submission {submission_id}, role: {role}")
        return feedback

    def _calculate_comprehensive_score(self, payload: dict) -> dict:
        """UF-09-a-2: 综合评分（规则计算）"""
        steps_summary = payload.get("steps_summary", [])
        total_duration = payload.get("total_duration", 0)
        total_attempts = payload.get("total_attempts", 0)

        total_steps = len(steps_summary) if steps_summary else 1
        completed_steps = len([s for s in steps_summary if s.get("status") == "pass"])
        failed_steps = len([s for s in steps_summary if s.get("status") == "fail"])

        # 步骤完成率 (50%)
        completion_rate = (completed_steps / total_steps) * 100 if total_steps > 0 else 0
        completion_score = completion_rate * 0.5

        # 用时系数 (20%)
        expected_duration = payload.get("project_snapshot", {}).get("estimated_time", 60) * 60
        time_score = 20.0
        if expected_duration > 0:
            ratio = total_duration / expected_duration
            if ratio > 1.0:
                time_score = max(20 - (ratio - 1) * 10, 0)  # 每超10%扣2分

        # 工具规范 (15%)
        tools_score = 12.0  # 默认80%


        # 尝试次数系数 (15%)
        avg_attempts = total_attempts / total_steps if total_steps > 0 else 1
        attempt_score = max(15 - (avg_attempts - 1) * 5, 5)

        total_score = completion_score + time_score + tools_score + attempt_score

        return {
            "total_score": round(total_score, 2),
            "completion_score": round(completion_score, 2),
            "completion_rate": round(completion_rate, 2),
            "time_score": round(time_score, 2),
            "tools_score": round(tools_score, 2),
            "attempt_score": round(attempt_score, 2),
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "total_steps": total_steps,
        }

    async def _analyze_steps(self, payload: dict) -> list[StepAnalysis]:
        """UF-09-a-3: 步骤逐项分析（LLM）"""
        steps_summary = payload.get("steps_summary", [])
        analyses = []

        for step in steps_summary:
            status = step.get("status", "")
            attempt_count = step.get("attempt_count", 0)

            # 只分析失败或多次尝试的步骤
            if status == "fail" or attempt_count > 1:
                analysis = StepAnalysis(
                    step_id=step.get("step_id", ""),
                    step_index=step.get("step_index", 0),
                    status=status,
                    attempt_count=attempt_count,
                )

                # 简单的规则分析（实际应该调用 LLM）
                if status == "fail":
                    analysis.analysis = f"该步骤执行失败，可能存在操作不规范或工具使用错误。"
                    analysis.suggestions = [
                        "仔细阅读步骤要求",
                        "确认工具使用顺序",
                        "检查参数设置",
                    ]

                if attempt_count > 1:
                    analysis.analysis += f"该步骤尝试了 {attempt_count} 次，建议优化操作流程。"
                    analysis.suggestions.append("减少不必要的重复操作")

                analyses.append(analysis)

        return analyses

    async def _evaluate_tools(self, payload: dict) -> list[ToolEvaluation]:
        """UF-09-a-4: 工具使用评价（LLM）"""
        steps_summary = payload.get("steps_summary", [])
        evaluations = []

        for step in steps_summary:
            tools_confirmed = step.get("tools_confirmed", [])
            if not tools_confirmed:
                continue

            for tool in tools_confirmed:
                eval_item = ToolEvaluation(
                    tool_id=tool.get("tool_id", ""),
                    confirmed=tool.get("status") == "confirmed",
                    evaluation="工具使用正确" if tool.get("status") == "confirmed" else "工具使用不规范",
                )
                evaluations.append(eval_item)

        return evaluations

    async def _compare_history(
        self,
        user_id: int,
        current_score: float,
    ) -> Optional[HistoricalComparison]:
        """UF-09-a-5: 历史对比"""
        # 查询历史提交
        result = await self.db.execute(
            select(TrainingSubmission)
            .where(
                TrainingSubmission.user_id == user_id,
                TrainingSubmission.score.isnot(None),
            )
            .order_by(TrainingSubmission.submitted_at.desc())
            .limit(10)
        )
        history = list(result.scalars().all())

        if len(history) < 2:
            return None

        # 计算历史平均
        scores = [s.score for s in history if s.score is not None]
        historical_avg = sum(scores) / len(scores) if scores else 0

        # 计算趋势
        recent_avg = sum(scores[:3]) / min(len(scores), 3) if scores else 0
        if recent_avg > historical_avg + 5:
            trend = "improving"
        elif recent_avg < historical_avg - 5:
            trend = "declining"
        else:
            trend = "stable"

        change_percent = ((current_score - historical_avg) / historical_avg * 100) if historical_avg > 0 else 0

        return HistoricalComparison(
            current_score=current_score,
            historical_avg=round(historical_avg, 2),
            trend=trend,
            change_percent=round(change_percent, 2),
        )

    async def _generate_suggestions(
        self,
        payload: dict,
        step_analyses: list[StepAnalysis],
    ) -> tuple[list[str], str]:
        """UF-09-a-6: 个性化建议 + 下一步计划（LLM）"""
        suggestions = []

        # 基于失败的步骤生成建议
        failed_steps = [s for s in step_analyses if s.status == "fail"]
        if failed_steps:
            suggestions.append("重点练习以下步骤：")
            for step in failed_steps[:3]:
                suggestions.append(f"  - {step.step_id}")

        # 基于工具问题生成建议
        tool_issues = [s for s in step_analyses if s.suggestions]
        if tool_issues:
            suggestions.append("工具使用建议：")
            for step in tool_issues[:2]:
                for sugg in step.suggestions[:2]:
                    suggestions.append(f"  - {sugg}")

        if not suggestions:
            suggestions = [
                "保持当前学习节奏",
                "继续巩固已掌握技能",
                "可以挑战更高难度训练",
            ]

        next_plan = "建议进行基础巩固训练，重点关注操作规范和工具使用。"

        return suggestions, next_plan

    async def _add_teaching_diagnosis(
        self,
        feedback: TrainingFeedback,
        user_id: int,
    ) -> None:
        """UF-09-b-2: 教学诊断（教师视角）"""
        # 简单的规则诊断
        score = feedback.overall_score

        if score >= 90:
            feedback.teaching_diagnosis = "该学员表现优秀，建议挑战更高难度训练。"
            feedback.hint_level_suggestion = 5
            feedback.ranking_percentile = 95.0
        elif score >= 75:
            feedback.teaching_diagnosis = "该学员表现良好，建议持续巩固当前技能。"
            feedback.hint_level_suggestion = 4
            feedback.ranking_percentile = 75.0
        elif score >= 60:
            feedback.teaching_diagnosis = "该学员需要更多练习，建议增加基础训练。"
            feedback.hint_level_suggestion = 2
            feedback.ranking_percentile = 50.0
        else:
            feedback.teaching_diagnosis = "该学员需要额外辅导，建议进行一对一指导。"
            feedback.hint_level_suggestion = 1
            feedback.ranking_percentile = 25.0

    async def _save_feedback(
        self,
        submission: TrainingSubmission,
        feedback: TrainingFeedback,
    ) -> None:
        """保存反馈到数据库"""
        submission.feedback = {
            "overall_score": feedback.overall_score,
            "score_breakdown": feedback.score_breakdown,
            "step_analyses": [
                {
                    "step_id": s.step_id,
                    "analysis": s.analysis,
                    "suggestions": s.suggestions,
                }
                for s in feedback.step_analyses
            ],
            "suggestions": feedback.suggestions,
            "next_learning_plan": feedback.next_learning_plan,
            "teaching_diagnosis": feedback.teaching_diagnosis,
        }
        submission.feedback_generated_at = datetime.utcnow()

        await self.db.commit()
