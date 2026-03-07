"""
TeachingChatEngine - P1-5
教学对话引擎，根据学员历史和当前步骤提供个性化指导
"""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.services.llm import LLMProvider, llm_router

logger = logging.getLogger(__name__)


class TeachingMode(str, Enum):
    """教学指导模式"""
    FULL_GUIDANCE = "full"     # AI 全程指导
    ON_DEMAND = "on_demand"    # 按需指导
    SILENT = "silent"          # 静默模式（仅在危险时提醒）


@dataclass
class TeachingContext:
    """教学上下文"""
    task_id: str
    step_index: int
    step_name: str
    step_description: str
    sop_name: str
    user_history: list[dict]  # 用户历史操作
    robot_state: Optional[dict] = None


@dataclass
class TeachingResponse:
    """教学响应"""
    content: str                    # 指导内容
    mode: TeachingMode              # 教学模式
    is_safety_alert: bool          # 是否为安全警告
    next_step_hint: Optional[str] = None  # 下一步提示


class TeachingChatEngine:
    """
    教学对话引擎

    支持三种教学模式：
    - FULL_GUIDANCE: 每步都提供详细指导
    - ON_DEMAND: 学员请求时才提供指导
    - SILENT: 仅在危险操作时提醒
    """

    def __init__(self):
        self.llm = llm_router

    async def teach(
        self,
        user_message: str,
        context: TeachingContext,
        mode: TeachingMode = TeachingMode.ON_DEMAND,
    ) -> TeachingResponse:
        """
        生成教学指导

        Args:
            user_message: 学员的消息
            context: 教学上下文
            mode: 教学模式

        Returns:
            TeachingResponse: 教学响应
        """
        # 1. 检查是否为安全关键操作
        if self._is_safety_critical(context.step_name):
            return TeachingResponse(
                content=self._get_safety_warning(context),
                mode=mode,
                is_safety_alert=True,
            )

        # 2. 根据模式决定是否响应
        if mode == TeachingMode.SILENT:
            return TeachingResponse(
                content="",
                mode=mode,
                is_safety_alert=False,
            )

        if mode == TeachingMode.ON_DEMAND:
            # 按需模式：只有学员明确请求帮助时才响应
            if not self._is_help_request(user_message):
                return TeachingResponse(
                    content="",
                    mode=mode,
                    is_safety_alert=False,
                )

        # 3. 生成指导内容
        return await self._generate_guidance(user_message, context)

    async def _generate_guidance(
        self,
        user_message: str,
        context: TeachingContext,
    ) -> TeachingResponse:
        """生成个性化指导"""

        prompt = self._build_teaching_prompt(user_message, context)

        try:
            response = await self.llm.chat(
                messages=prompt,
                provider=LLMProvider.OPENAI,
                model="gpt-3.5-turbo",
                temperature=0.7,
                max_tokens=500,
            )

            content = response.content
            next_hint = self._extract_next_hint(content)

            return TeachingResponse(
                content=content,
                mode=TeachingMode.FULL_GUIDANCE,
                is_safety_alert=False,
                next_step_hint=next_hint,
            )
        except Exception as e:
            logger.warning(f"Teaching guidance generation failed: {e}")
            return self._fallback_guidance(context)

    def _build_teaching_prompt(
        self,
        user_message: str,
        context: TeachingContext,
    ) -> list[dict]:
        """构建教学提示词"""
        history_summary = self._summarize_history(context.user_history)

        content = f"""你是一个专业的维保培训导师。根据学员的当前状态和请求，提供个性化指导。

## 当前任务
- 任务ID: {context.task_id}
- SOP: {context.sop_name}
- 当前步骤: {context.step_index + 1}
- 步骤名称: {context.step_name}
- 步骤描述: {context.step_description}

## 学员历史
{history_summary}

## 学员请求
{user_message}

## 指导要求
1. 简洁明了，不超过 100 字
2. 结合 SOP 规范
3. 如有历史错误，指出并纠正
4. 提供下一步操作提示
"""

        return [
            {"role": "system", "content": "你是一个专业的维保培训导师。"},
            {"role": "user", "content": content}
        ]

    def _summarize_history(self, history: list[dict]) -> str:
        """总结用户历史"""
        if not history:
            return "无历史记录"

        summary = []
        for i, h in enumerate(history[-3:], 1):  # 只看最近3条
            action = h.get("action", "")
            result = h.get("result", "")
            summary.append(f"{i}. {action} - {result}")

        return "\n".join(summary)

    def _extract_next_hint(self, content: str) -> Optional[str]:
        """提取下一步提示"""
        keywords = ["下一步", "接下来", "然后", "建议"]
        for kw in keywords:
            if kw in content:
                idx = content.find(kw)
                return content[idx:idx+50]
        return None

    def _is_help_request(self, message: str) -> bool:
        """判断是否为请求帮助"""
        help_keywords = ["帮助", "指导", "怎么办", "不懂", "不会", "求助"]
        return any(kw in message for kw in help_keywords)

    def _is_safety_critical(self, step_name: str) -> bool:
        """判断是否为安全关键步骤"""
        critical_keywords = ["断电", "高压", "制动", "安全", "急停"]
        return any(kw in step_name for kw in critical_keywords)

    def _get_safety_warning(self, context: TeachingContext) -> str:
        """获取安全警告"""
        return f"⚠️ 安全提醒：步骤「{context.step_name}」涉及安全操作，请确保设备已断电并遵守 SOP 规范。"

    def _fallback_guidance(self, context: TeachingContext) -> TeachingResponse:
        """降级指导"""
        return TeachingResponse(
            content=f"请按照 SOP「{context.sop_name}」的步骤 {context.step_index + 1} 执行操作：{context.step_description}",
            mode=TeachingMode.FULL_GUIDANCE,
            is_safety_alert=False,
        )


# 全局实例
teaching_chat_engine = TeachingChatEngine()
