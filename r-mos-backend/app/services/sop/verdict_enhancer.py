"""
VerdictEnhancer - P1-4
SOP 裁决 LLM 解释层 (L2)
在 L1 规则判断后，LLM 生成解释：原因 + 建议 + 引用
"""
import logging
from dataclasses import dataclass
from typing import Optional, Any

from app.services.llm import LLMProvider, llm_router, prompt_engine
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class VerdictExplanation:
    """裁决解释结果 (L2)"""
    reason: str                      # 判断原因
    suggestions: list[str]           # 改进建议
    citations: list[str]              # 引用 (SOP/步骤 ID)
    confidence: float                 # 置信度 0-1
    alternative_approaches: Optional[list[str]] = None  # 替代方案


class VerdictEnhancer:
    """
    L2 裁决解释生成器

    在 L1 规则判断后使用 LLM 生成更丰富的解释
    """

    def __init__(self):
        self.llm = llm_router

    async def explain(
        self,
        step_name: str,
        step_description: str,
        sop_name: str,
        user_action: str,
        l1_verdict: str,  # "pass" | "fail"
        robot_state: Optional[dict] = None,
        knowledge_context: Optional[list[dict]] = None,
    ) -> VerdictExplanation:
        """
        生成 L2 裁决解释

        Args:
            step_name: 步骤名称
            step_description: 步骤描述
            sop_name: SOP 名称
            user_action: 用户实际执行的动作
            l1_verdict: L1 规则判断结果
            robot_state: 机器人状态
            knowledge_context: 知识上下文

        Returns:
            VerdictExplanation: 包含原因、建议、引用
        """
        # 构建提示词
        prompt = self._build_prompt(
            step_name=step_name,
            step_description=step_description,
            sop_name=sop_name,
            user_action=user_action,
            l1_verdict=l1_verdict,
            robot_state=robot_state,
            knowledge_context=knowledge_context,
        )

        try:
            response = await self.llm.chat(
                messages=prompt,
                provider=LLMProvider.DEEPSEEK,
                model=settings.LLM_MODEL_BASIC,
                temperature=0.3,
                max_tokens=800,
            )
            return self._parse_response(response.content, l1_verdict)
        except Exception as e:
            logger.warning(f"L2 explanation generation failed: {e}")
            # 降级到简单解释
            return self._fallback_explanation(l1_verdict)

    def _build_prompt(
        self,
        step_name: str,
        step_description: str,
        sop_name: str,
        user_action: str,
        l1_verdict: str,
        robot_state: Optional[dict],
        knowledge_context: Optional[list[dict]],
    ) -> list[dict]:
        """构建 LLM 提示词"""

        content_parts = [
            f"你是一个专业的维保培训评估专家。请根据以下信息，生成裁决解释。",
            "",
            f"## SOP 信息",
            f"- SOP 名称: {sop_name}",
            f"- 步骤名称: {step_name}",
            f"- 步骤描述: {step_description}",
            "",
            f"## 用户操作",
            f"实际执行: {user_action}",
            "",
            f"## L1 规则判断",
            f"判定结果: {l1_verdict}",
        ]

        if robot_state:
            content_parts.extend([
                "",
                f"## 机器人状态",
                f"{robot_state}",
            ])

        if knowledge_context:
            content_parts.extend([
                "",
                f"## 相关知识参考",
            ])
            for i, chunk in enumerate(knowledge_context[:3], 1):
                content_parts.append(f"{i}. {chunk.get('title', '')}: {chunk.get('content', '')[:100]}")

        content_parts.extend([
            "",
            "## 输出要求",
            "请以 JSON 格式输出，包含以下字段：",
            "- reason: 判断原因 (50字以内)",
            "- suggestions: 改进建议列表 (2-3条)",
            "- citations: 引用的 SOP/步骤 ID",
            "- confidence: 置信度 (0-1)",
            "- alternative_approaches: 替代方案 (可选)",
        ])

        return [
            {"role": "system", "content": "你是一个专业的维保培训评估专家。"},
            {"role": "user", "content": "\n".join(content_parts)}
        ]

    def _parse_response(self, content: str, l1_verdict: str) -> VerdictExplanation:
        """解析 LLM 响应"""
        import json

        try:
            # 尝试解析 JSON
            data = json.loads(content)

            return VerdictExplanation(
                reason=data.get("reason", "基于规则判断"),
                suggestions=data.get("suggestions", []),
                citations=data.get("citations", []),
                confidence=data.get("confidence", 0.8),
                alternative_approaches=data.get("alternative_approaches"),
            )
        except json.JSONDecodeError:
            # 解析失败，尝试从文本提取
            return self._parse_text_response(content, l1_verdict)

    def _parse_text_response(self, content: str, l1_verdict: str) -> VerdictExplanation:
        """从文本响应中提取信息"""
        lines = content.split("\n")

        reason = l1_verdict.upper()
        suggestions = []
        citations = []

        for line in lines:
            if "建议" in line:
                suggestions.append(line.split("建议")[1].strip() if "建议" in line else line)
            if "引用" in line or "参考" in line:
                citations.append(line.strip())

        return VerdictExplanation(
            reason=reason,
            suggestions=suggestions[:3],
            citations=citations[:2],
            confidence=0.5,
        )

    def _fallback_explanation(self, l1_verdict: str) -> VerdictExplanation:
        """降级到简单解释"""
        if l1_verdict == "pass":
            return VerdictExplanation(
                reason="符合 SOP 操作规范",
                suggestions=["继续保持规范操作"],
                citations=[],
                confidence=0.9,
            )
        else:
            return VerdictExplanation(
                reason="不符合 SOP 操作规范",
                suggestions=["请重新阅读 SOP", "按步骤顺序操作"],
                citations=[],
                confidence=0.9,
            )


# 全局实例
verdict_enhancer = VerdictEnhancer()
