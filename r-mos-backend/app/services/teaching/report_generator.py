"""
P2-2: Teaching Evaluation Report Generator Service
生成 LLM 增强的教学评估报告

职责：
- 收集任务全程证据链
- 调用 LLM 生成叙述性评估报告
- 将报告写入 evidence_bundles
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.task import Task
from app.models.event import Event
from app.models.sop import SOP, SOPStep
from app.models.evidence import EvidenceBundle, EvidenceItem
from app.schemas.report import (
    LLMEvaluationReport,
    LLMEvaluationSection,
    PeerComparisonSection,
    ScoreBreakdown,
    StepScore,
)
from app.services.scoring_service import ScoringService
from app.services.llm.router import LLMRouter, LLMProvider
from app.services.teaching.group_stats import GroupStatsService
from app.core.config import settings

logger = logging.getLogger(__name__)


# P2-2: System prompt for evaluation report generation
EVALUATION_REPORT_SYSTEM_PROMPT = """你是一位专业的机器人维保培训导师，擅长分析学员的操作表现并提供建设性的反馈。

请根据以下任务评估数据，生成一份结构化的评估报告，包括：

1. **总体评估摘要** (summary): 简短总结学员的整体表现
2. **优势分析** (strengths): 列出学员做得好的方面
3. **待改进领域** (improvement_areas): 指出需要提高的方面
4. **根本原因分析** (root_cause_analysis): 分析问题背后的原因
5. **个性化建议** (personalized_suggestions): 针对该学员的具体建议
6. **下一步学习计划** (next_learning_plan): 推荐的下一步学习路径

请用中文回复，使用专业的培训术语。"""


class ReportGenerator:
    """LLM 增强的评估报告生成器"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.scoring_service = ScoringService(db)
        self.llm_router = LLMRouter()

    async def generate_report(
        self,
        task_id: int,
        use_llm: bool = True,
        include_peer_comparison: bool = True,
    ) -> LLMEvaluationReport:
        """
        生成任务评估报告

        Args:
            task_id: 任务 ID
            use_llm: 是否使用 LLM 生成叙述性内容
            include_peer_comparison: 是否包含同伴对比

        Returns:
            LLMEvaluationReport: 完整的评估报告
        """
        # 1. 加载任务基础数据
        task_data = await self._load_task_data(task_id)

        # 2. 计算评分
        score_result = await self.scoring_service.calculate_score(task_id)

        # 3. 构建基础报告
        base_report = self._build_base_report(task_data, score_result)

        # 4. 如果启用 LLM，生成叙述性评估
        llm_evaluation = None
        llm_provider = None
        llm_model = None

        if use_llm:
            try:
                llm_evaluation = await self._generate_llm_evaluation(
                    task_data, score_result
                )
                llm_provider = "openai"  # 可以从配置获取
                llm_model = "gpt-4"
            except Exception as e:
                logger.warning(f"[P2-2] LLM evaluation failed: {e}")
                # LLM 失败不影响基础报告生成

        # 5. P2-3: 同伴对比
        peer_comparison = None
        if include_peer_comparison:
            try:
                peer_comparison = await self._generate_peer_comparison(task_data)
            except Exception as e:
                logger.warning(f"[P2-3] Peer comparison failed: {e}")

        # 6. 组装完整报告
        return LLMEvaluationReport(
            **base_report.model_dump(),
            llm_evaluation=llm_evaluation,
            llm_provider=llm_provider,
            llm_model=llm_model,
            peer_comparison=peer_comparison,
        )

    async def _generate_peer_comparison(self, task_data: dict) -> Optional[PeerComparisonSection]:
        """P2-3: 生成同伴对比"""
        task = task_data["task"]

        # 只对有 user_id 的任务生成对比
        if not task.user_id:
            return None

        group_stats_service = GroupStatsService(self.db)

        try:
            comparison = await group_stats_service.get_comparison_context(
                student_id=task.user_id,
                sop_id=task.sop_id,
            )

            if "error" in comparison:
                logger.info(f"[P2-3] Peer comparison skipped: {comparison['error']}")
                return None

            return PeerComparisonSection(
                student_level=comparison["student_level"],
                group_stats=comparison["group_stats"],
                student_stats=comparison["student_stats"],
                comparison=comparison["comparison"],
            )
        except Exception as e:
            logger.warning(f"[P2-3] Failed to generate peer comparison: {e}")
            return None

    async def _load_task_data(self, task_id: int) -> dict:
        """加载任务相关数据"""
        # 加载任务
        result = await self.db.execute(
            select(Task).where(Task.id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # 加载 SOP
        sop = None
        if task.sop_id:
            sop_result = await self.db.execute(
                select(SOP).where(SOP.id == task.sop_id)
            )
            sop = sop_result.scalar_one_or_none()

        # 加载步骤
        steps = []
        if sop:
            steps_result = await self.db.execute(
                select(SOPStep)
                .where(SOPStep.sop_id == sop.id)
                .order_by(SOPStep.step_index)
            )
            steps = steps_result.scalars().all()

        # 加载事件
        events_result = await self.db.execute(
            select(Event).where(Event.task_id == task_id)
        )
        events = events_result.scalars().all()

        return {
            "task": task,
            "sop": sop,
            "steps": steps,
            "events": events,
        }

    def _build_base_report(
        self,
        task_data: dict,
        score_result: dict,
    ) -> LLMEvaluationReport:
        """构建基础报告（不含 LLM 内容）"""
        task = task_data["task"]
        sop = task_data.get("sop")

        return LLMEvaluationReport(
            task_id=task.id,
            task_title=task.title or f"任务 {task.id}",
            sop_name=sop.name if sop else None,
            user_id=task.user_id,
            started_at=task.created_at,
            completed_at=task.completed_at or datetime.now(timezone.utc),
            total_duration_seconds=int(
                (task.completed_at - task.created_at).total_seconds()
            ) if task.completed_at else 0,
            expected_duration_seconds=sop.estimated_time if sop else None,
            final_score=score_result.get("final_score", 0),
            pass_score=score_result.get("pass_score", 60),
            is_passed=score_result.get("is_passed", False),
            score_breakdown=score_result.get(
                "breakdown",
                ScoreBreakdown(
                    professionalism=0, compliance=0, efficiency=0, safety=0
                ),
            ),
            step_scores=score_result.get("step_scores", []),
            total_steps=len(task_data.get("steps", [])),
            completed_steps=score_result.get("completed_steps", 0),
            skipped_steps=score_result.get("skipped_steps", 0),
            error_count=score_result.get("error_count", 0),
            recommendations=score_result.get("recommendations", []),
            generated_at=datetime.now(),
        )

    async def _generate_llm_evaluation(
        self,
        task_data: dict,
        score_result: dict,
    ) -> Optional[LLMEvaluationSection]:
        """调用 LLM 生成叙述性评估"""
        # 构建上下文
        context = self._build_evaluation_context(task_data, score_result)

        # 调用 LLM
        try:
            messages = [
                {"role": "system", "content": EVALUATION_REPORT_SYSTEM_PROMPT},
                {"role": "user", "content": context},
            ]

            response = await self.llm_router.chat(
                messages=messages,
                provider=LLMProvider.DEEPSEEK,
                model=settings.LLM_MODEL_ADVANCED,
                temperature=0.7,
                max_tokens=2000,
            )

            # 解析 LLM 响应
            return self._parse_llm_response(response.content)

        except Exception as e:
            logger.error(f"[P2-2] LLM call failed: {e}")
            raise

    def _build_evaluation_context(
        self,
        task_data: dict,
        score_result: dict,
    ) -> str:
        """构建 LLM 评估所需的上下文"""
        task = task_data["task"]
        sop = task_data.get("sop")
        steps = task_data.get("steps", [])
        events = task_data.get("events", [])
        breakdown = score_result.get("breakdown")

        context_parts = [
            "=== 任务信息 ===",
            f"任务标题: {task.title or '未命名'}",
            f"SOP名称: {sop.name if sop else '无'}",
            f"任务状态: {task.status.value if hasattr(task.status, 'value') else task.status}",
            "",
            "=== 评分详情 ===",
            f"最终得分: {score_result.get('final_score', 0)}",
            f"是否通过: {'是' if score_result.get('is_passed') else '否'}",
        ]

        if breakdown:
            context_parts.extend([
                f"专业性: {breakdown.professionalism}/25",
                f"规范性: {breakdown.compliance}/25",
                f"效率: {breakdown.efficiency}/25",
                f"安全性: {breakdown.safety}/25",
            ])

        context_parts.extend([
            "",
            "=== 步骤执行情况 ===",
            f"总步骤数: {len(steps)}",
            f"完成步骤: {score_result.get('completed_steps', 0)}",
            f"跳过步骤: {score_result.get('skipped_steps', 0)}",
            f"错误次数: {score_result.get('error_count', 0)}",
        ])

        # 添加关键事件
        if events:
            context_parts.extend([
                "",
                "=== 关键事件 ===",
            ])
            for event in events[-10:]:  # 只取最近10个
                event_type = event.event_type.value if hasattr(event.event_type, 'value') else event.event_type
                context_parts.append(
                    f"- {event.created_at.strftime('%H:%M:%S')}: {event_type}"
                )

        # 添加建议
        recommendations = score_result.get("recommendations", [])
        if recommendations:
            context_parts.extend([
                "",
                "=== 已有建议 ===",
            ])
            for rec in recommendations[:5]:
                context_parts.append(f"- {rec}")

        return "\n".join(context_parts)

    def _parse_llm_response(self, content: str) -> Optional[LLMEvaluationSection]:
        """解析 LLM 响应为结构化数据"""
        try:
            # 尝试解析为 JSON
            data = json.loads(content)

            return LLMEvaluationSection(
                summary=data.get("summary", ""),
                strengths=data.get("strengths", []),
                improvement_areas=data.get("improvement_areas", []),
                root_cause_analysis=data.get("root_cause_analysis", ""),
                personalized_suggestions=data.get("personalized_suggestions", []),
                next_learning_plan=data.get("next_learning_plan", ""),
            )
        except json.JSONDecodeError:
            # 如果不是 JSON，尝试从文本中提取
            logger.warning("[P2-2] LLM response is not JSON, using fallback parsing")
            return self._fallback_parse(content)

    def _fallback_parse(self, content: str) -> LLMEvaluationSection:
        """降级解析：当 LLM 返回非 JSON 时的处理"""
        return LLMEvaluationSection(
            summary=content[:200] if content else "LLM 评估生成失败",
            strengths=[],
            improvement_areas=[],
            root_cause_analysis="",
            personalized_suggestions=[],
            next_learning_plan="",
        )

    async def save_to_evidence_bundle(
        self,
        report: LLMEvaluationReport,
        task_id: int,
    ) -> EvidenceBundle:
        """
        将报告保存到 evidence bundle

        Args:
            report: 评估报告
            task_id: 任务 ID

        Returns:
            EvidenceBundle: 创建的证据包
        """
        # 序列化报告
        report_json = report.model_dump_json(indent=2)
        content_hash = hashlib.sha256(report_json.encode()).hexdigest()

        bundle_id = str(uuid.uuid4())

        # 创建证据包
        bundle = EvidenceBundle(
            id=bundle_id,
            bundle_type="task_evaluation_report",
            bundle_hash=content_hash,
            bundle_hash_algo="sha256",
            observed_time_start=report.started_at,
            observed_time_end=report.completed_at,
            ingest_time=datetime.now(),
            is_sealed=True,
            sealed_at=datetime.now(),
            human_summary=f"任务 {task_id} 的 LLM 评估报告",
            machine_tags=["llm_evaluation", "task_report"],
        )

        self.db.add(bundle)

        # 创建证据项
        evidence_id = f"eval-report-{task_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        evidence_item = EvidenceItem(
            id=evidence_id,
            bundle_id=bundle_id,
            evidence_type="evaluation_report",
            content_uri=f"bundle:task:{task_id}:report",
            content_hash=content_hash,
            content_hash_algo="sha256",
            content_mime_type="application/json",
            size_bytes=len(report_json.encode("utf-8")),
            observed_time=report.completed_at,
            ingest_time=datetime.now(),
            human_summary=f"任务 {task_id} 的评估报告",
            machine_code=None,
            machine_tags=["llm_evaluation", "task_report"],
        )

        self.db.add(evidence_item)
        await self.db.commit()
        await self.db.refresh(bundle)

        logger.info(f"[P2-2] Saved evaluation report to bundle {bundle.id}")

        return bundle
