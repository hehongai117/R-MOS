"""
LLMRiskScorer - P1-9
LLM 动态风险评分服务
"""
import logging
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from app.services.llm import LLMProvider, llm_router

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """风险等级"""
    LOW = "low"         # 0-30
    MEDIUM = "medium"   # 31-60
    HIGH = "high"       # 61-80
    CRITICAL = "critical"  # 81-100


@dataclass
class RiskScore:
    """风险评分结果"""
    score: int              # 0-100
    level: RiskLevel        # 风险等级
    factors: list[str]       # 风险因素
    recommendation: str      # 建议


class LLMRiskScorer:
    """
    LLM 动态风险评分器

    输入：学员历史 / 设备状态 / 步骤复杂度
    输出：0-100 风险分
    """

    def __init__(self):
        self.llm = llm_router
        self._threshold_high = 60   # 高风险阈值
        self._threshold_medium = 30  # 中风险阈值

    def set_thresholds(self, high: int, medium: int):
        """设置风险阈值"""
        self._threshold_high = high
        self._threshold_medium = medium

    async def score(
        self,
        user_history: list[dict],
        robot_state: Optional[dict],
        step_complexity: str,  # "simple" | "medium" | "complex"
        action_type: str,      # "diagnosis" | "maintenance" | "emergency"
    ) -> RiskScore:
        """
        计算风险评分

        Args:
            user_history: 用户历史操作
            robot_state: 机器人状态
            step_complexity: 步骤复杂度
            action_type: 操作类型

        Returns:
            RiskScore: 风险评分
        """
        # 1. 使用 LLM 分析风险
        try:
            llm_result = await self._llm_score(
                user_history=user_history,
                robot_state=robot_state,
                step_complexity=step_complexity,
                action_type=action_type,
            )
            return llm_result
        except Exception as e:
            logger.warning(f"LLM risk scoring failed: {e}")
            # 2. 降级到规则评分
            return self._rule_based_score(
                user_history=user_history,
                robot_state=robot_state,
                step_complexity=step_complexity,
                action_type=action_type,
            )

    async def _llm_score(
        self,
        user_history: list[dict],
        robot_state: Optional[dict],
        step_complexity: str,
        action_type: str,
    ) -> RiskScore:
        """使用 LLM 进行风险评估"""

        history_summary = self._summarize_history(user_history)

        prompt = f"""你是一个风险评估专家。请评估以下维保操作的风险等级。

## 操作信息
- 操作类型: {action_type}
- 步骤复杂度: {step_complexity}

## 用户历史
{history_summary}

## 机器人状态
{robot_state if robot_state else "未知"}

## 输出要求
请以 JSON 格式输出:
{{
    "score": 0-100,
    "factors": ["风险因素1", "风险因素2"],
    "recommendation": "建议内容"
}}
"""

        response = await self.llm.chat(
            messages=[
                {"role": "system", "content": "你是一个风险评估专家。"},
                {"role": "user", "content": prompt}
            ],
            provider=LLMProvider.OPENAI,
            model="gpt-3.5-turbo",
            temperature=0.3,
            max_tokens=300,
        )

        # 解析响应
        import json
        try:
            data = json.loads(response.content)
            score = int(data.get("score", 50))
            score = max(0, min(100, score))  # 限制在 0-100
        except:
            score = 50

        return RiskScore(
            score=score,
            level=self._get_level(score),
            factors=data.get("factors", []),
            recommendation=data.get("recommendation", ""),
        )

    def _rule_based_score(
        self,
        user_history: list[dict],
        robot_state: Optional[dict],
        step_complexity: str,
        action_type: str,
    ) -> RiskScore:
        """基于规则的风险评分"""

        score = 20  # 基础分

        # 根据步骤复杂度加分
        if step_complexity == "medium":
            score += 15
        elif step_complexity == "complex":
            score += 30

        # 根据操作类型加分
        if action_type == "emergency":
            score += 30
        elif action_type == "maintenance":
            score += 10

        # 根据历史错误加分
        if user_history:
            error_count = sum(1 for h in user_history if h.get("result") == "error")
            score += min(error_count * 10, 20)

        # 根据机器人状态加分
        if robot_state:
            if robot_state.get("error"):
                score += 20

        score = min(score, 100)

        return RiskScore(
            score=score,
            level=self._get_level(score),
            factors=["基于规则计算"],
            recommendation="请谨慎操作" if score > 60 else "可正常操作"
        )

    def _summarize_history(self, history: list[dict]) -> str:
        """总结用户历史"""
        if not history:
            return "无历史记录"

        summary = []
        for h in history[-5:]:  # 只看最近5条
            action = h.get("action", "")
            result = h.get("result", "")
            summary.append(f"- {action}: {result}")

        return "\n".join(summary)

    def _get_level(self, score: int) -> RiskLevel:
        """根据分数确定风险等级"""
        if score >= 80:
            return RiskLevel.CRITICAL
        elif score >= 60:
            return RiskLevel.HIGH
        elif score >= 30:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def should_require_approval(self, score: RiskScore) -> bool:
        """判断是否需要审批"""
        return score.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]


# 全局实例
llm_risk_scorer = LLMRiskScorer()
