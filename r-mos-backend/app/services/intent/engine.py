"""
IntentEngine - P1-3
LLM 意图理解引擎
"""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from app.services.llm import LLMProvider, llm_router, prompt_engine
from app.core.config import settings

logger = logging.getLogger(__name__)


class IntentScene(str, Enum):
    """意图场景枚举 - UF-03-a-1 新增训练专项类型"""
    TASK_EXECUTION = "task_execution"       # 任务执行
    DIAGNOSIS = "diagnosis"                 # 故障诊断
    KNOWLEDGE_QUERY = "knowledge_query"     # 知识查询
    TEACHING_GUIDE = "teaching_guide"       # 教学指导
    TASK_STATUS = "task_status"             # 任务状态查询
    HELP_REQUEST = "help_request"           # 请求帮助
    GENERAL_CHAT = "general_chat"            # 通用对话

    # UF-03-a: 训练专项意图
    TRAINING_NEW = "training_new"           # 新建训练
    TRAINING_WEAKNESS = "training_weakness"  # 弱点强化训练
    TRAINING_CERT = "training_cert"         # 认证考前训练
    TRAINING_ASSIGNED = "training_assigned" # 分配的任务训练
    TRAINING_EXPLORE = "training_explore"   # 探索式训练


class EntityType(str, Enum):
    """实体类型"""
    SOP = "sop"
    TASK = "task"
    STEP = "step"
    ROBOT = "robot"
    USER = "user"
    SKILL = "skill"


@dataclass
class IntentEntity:
    """识别的实体"""
    type: EntityType
    value: str
    confidence: float


@dataclass
class IntentResult:
    """意图识别结果"""
    scene: IntentScene
    action: str
    entities: list[IntentEntity]
    confidence: float
    raw_text: str
    clarification_request: Optional[str] = None
    suggested_response: Optional[str] = None


# 意图分类的关键词映射
SCENE_KEYWORDS = {
    IntentScene.TASK_EXECUTION: ["执行", "开始", "完成", "任务", "派单", "创建"],
    IntentScene.DIAGNOSIS: ["诊断", "问题", "故障", "错误", "异常", "维修"],
    IntentScene.KNOWLEDGE_QUERY: ["查询", "知识", "搜索", "找", "什么是", "如何"],
    IntentScene.TEACHING_GUIDE: ["指导", "教学", "步骤", "下一步", "教程", "学习"],
    IntentScene.TASK_STATUS: ["状态", "进度", "查看", "当前", "进行中"],
    IntentScene.HELP_REQUEST: ["帮助", "求助", "不会", "不懂", "怎么办"],
    IntentScene.GENERAL_CHAT: [],
}


class IntentEngine:
    """
    意图理解引擎

    使用 LLM 进行结构化意图识别，低置信度时返回澄清请求
    """

    def __init__(self):
        self.llm = llm_router
        self.prompt = prompt_engine
        self._confidence_threshold = 0.6

    def set_confidence_threshold(self, threshold: float):
        """设置置信度阈值"""
        self._confidence_threshold = threshold

    async def recognize(
        self,
        user_text: str,
        context: Optional[dict] = None,
        use_llm: bool = True,
    ) -> IntentResult:
        """
        识别用户意图

        Args:
            user_text: 用户输入文本
            context: 上下文信息 (可选)
            use_llm: 是否使用 LLM (True) 或规则 (False)

        Returns:
            IntentResult: 结构化意图结果
        """
        # 1. 规则匹配作为快速路径
        rule_result = self._rule_based_recognize(user_text)

        if not use_llm:
            return rule_result

        # 2. 使用 LLM 进行更准确的理解
        try:
            llm_result = await self._llm_recognize(user_text, context)

            # 如果 LLM 结果置信度更高，使用 LLM 结果
            if llm_result.confidence > rule_result.confidence:
                return llm_result

            return rule_result
        except Exception as e:
            logger.warning(f"LLM intent recognition failed: {e}, using rule-based")
            return rule_result

    def _rule_based_recognize(self, user_text: str) -> IntentResult:
        """基于规则的意图识别"""
        text_lower = user_text.lower()

        # 计算每个场景的匹配分数
        scores = {}
        for scene, keywords in SCENE_KEYWORDS.items():
            if not keywords:
                continue
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[scene] = score

        if scores:
            # 选择得分最高的场景
            scene = max(scores, key=scores.get)
            confidence = scores[scene] / len(SCENE_KEYWORDS[scene])
            confidence = min(confidence, 0.8)  # 规则匹配最高 0.8
        else:
            scene = IntentScene.GENERAL_CHAT
            confidence = 0.5

        return IntentResult(
            scene=scene,
            action=self._get_default_action(scene),
            entities=[],
            confidence=confidence,
            raw_text=user_text,
        )

    async def _llm_recognize(
        self,
        user_text: str,
        context: Optional[dict],
    ) -> IntentResult:
        """使用 LLM 进行意图识别"""
        # 构建提示词
        system_prompt = """你是一个意图识别专家。根据用户的输入，识别其意图。

可选场景:
- task_execution: 执行维保任务
- diagnosis: 诊断故障问题
- knowledge_query: 查询维保知识
- teaching_guide: 请求教学指导
- task_status: 查看任务状态
- help_request: 请求帮助
- general_chat: 通用对话

请以 JSON 格式输出:
{
    "scene": "场景名",
    "action": "具体动作",
    "confidence": 0.0-1.0,
    "entities": [{"type": "类型", "value": "值"}],
    "clarification_request": "如果置信度低于0.6，说明需要澄清的内容"
}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ]

        if context:
            messages.append({
                "role": "system",
                "content": f"上下文: {context}"
            })

        response = await self.llm.chat(
            messages=messages,
            provider=LLMProvider.DEEPSEEK,
            model=settings.LLM_MODEL_BASIC,
            temperature=0.3,
            max_tokens=500,
        )

        # 解析 JSON 响应
        import json
        try:
            result = json.loads(response.content)

            scene = IntentScene(result.get("scene", "general_chat"))
            entities = [
                IntentEntity(
                    type=EntityType(e["type"]),
                    value=e["value"],
                    confidence=e.get("confidence", 0.8)
                )
                for e in result.get("entities", [])
            ]

            confidence = float(result.get("confidence", 0.5))

            # 低置信度时返回澄清请求
            if confidence < self._confidence_threshold:
                return IntentResult(
                    scene=scene,
                    action=result.get("action", ""),
                    entities=entities,
                    confidence=confidence,
                    raw_text=user_text,
                    clarification_request=result.get(
                        "clarification_request",
                        "请更详细地描述您的需求"
                    )
                )

            return IntentResult(
                scene=scene,
                action=result.get("action", ""),
                entities=entities,
                confidence=confidence,
                raw_text=user_text,
                suggested_response=result.get("suggested_response")
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse LLM intent response: {e}")
            # 降级到规则匹配
            return self._rule_based_recognize(user_text)

    def _get_default_action(self, scene: IntentScene) -> str:
        """获取场景的默认动作"""
        actions = {
            IntentScene.TASK_EXECUTION: "create_task",
            IntentScene.DIAGNOSIS: "diagnose",
            IntentScene.KNOWLEDGE_QUERY: "search",
            IntentScene.TEACHING_GUIDE: "guide",
            IntentScene.TASK_STATUS: "query_status",
            IntentScene.HELP_REQUEST: "provide_help",
            IntentScene.GENERAL_CHAT: "chat",
        }
        return actions.get(scene, "unknown")

    async def clarify(
        self,
        intent: IntentResult,
        clarification: str,
    ) -> IntentResult:
        """
        根据用户澄清更新意图

        Args:
            intent: 之前的意图结果
            clarification: 用户的澄清内容

        Returns:
            IntentResult: 更新后的意图结果
        """
        # 重新识别，传入澄清内容
        combined_text = f"{intent.raw_text} {clarification}"
        return await self.recognize(combined_text, use_llm=True)


# 全局实例
intent_engine = IntentEngine()
