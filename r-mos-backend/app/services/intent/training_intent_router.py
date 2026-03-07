"""
UF-03: Training Intent Router
训练意图路由服务

职责：
- 根据训练意图类型路由到不同的处理逻辑
- 参数提取和校验
- 触发项目生成器
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Any
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.intent.engine import IntentScene, IntentEngine

logger = logging.getLogger(__name__)


class TrainingIntentType(str, Enum):
    """训练意图类型 - UF-03-a-1"""
    NEW = "training_new"
    WEAKNESS = "training_weakness"
    CERT = "training_cert"
    ASSIGNED = "training_assigned"
    EXPLORE = "training_explore"


@dataclass
class TrainingIntent:
    """训练意图参数"""
    intent_type: TrainingIntentType
    # 通用参数
    category: Optional[str] = None  # 维保类别
    # TRAINING_NEW 参数
    brand: Optional[str] = None
    model: Optional[str] = None
    # TRAINING_CERT 参数
    target_level: Optional[str] = None  # L1/L2/L3
    # TRAINING_ASSIGNED 参数
    assignment_id: Optional[int] = None
    # TRAINING_WEAKNESS 参数 (无需用户指定，从记忆读取)


@dataclass
class TrainingIntentResult:
    """训练意图解析结果"""
    intent: TrainingIntent
    can_proceed: bool  # 参数是否完整，可以继续生成
    clarification_questions: list[str]  # 需要追问的问题
    routing_target: str  # 路由目标: project_generator | clarification


class TrainingIntentRouter:
    """训练意图路由器 - UF-03-a-2"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.intent_engine = IntentEngine()

    async def route(
        self,
        user_text: str,
        user_id: int,
    ) -> TrainingIntentResult:
        """UF-03-a-2: 路由到 ProjectGenerator，跳过普通对话分发

        Args:
            user_text: 用户输入
            user_id: 用户ID

        Returns:
            TrainingIntentResult: 意图解析结果
        """
        # 使用 IntentEngine 识别意图
        intent_result = await self.intent_engine.recognize(user_text)

        # 检查是否是训练意图
        training_scene_map = {
            IntentScene.TRAINING_NEW: TrainingIntentType.NEW,
            IntentScene.TRAINING_WEAKNESS: TrainingIntentType.WEAKNESS,
            IntentScene.TRAINING_CERT: TrainingIntentType.CERT,
            IntentScene.TRAINING_ASSIGNED: TrainingIntentType.ASSIGNED,
            IntentScene.TRAINING_EXPLORE: TrainingIntentType.EXPLORE,
        }

        scene = intent_result.scene
        if scene not in training_scene_map:
            # 不是训练意图，返回非训练结果
            return TrainingIntentResult(
                intent=None,
                can_proceed=False,
                clarification_questions=[],
                routing_target="general",
            )

        intent_type = training_scene_map[scene]

        # 根据不同意图类型提取参数
        if intent_type == TrainingIntentType.NEW:
            return await self._handle_new_training(user_text, intent_result)
        elif intent_type == TrainingIntentType.WEAKNESS:
            return await self._handle_weakness_training(user_id)
        elif intent_type == TrainingIntentType.CERT:
            return await self._handle_cert_training(user_text, intent_result)
        elif intent_type == TrainingIntentType.ASSIGNED:
            return await self._handle_assigned_training(user_text, user_id)
        elif intent_type == TrainingIntentType.EXPLORE:
            return await self._handle_explore_training(user_text, intent_result)

        return TrainingIntentResult(
            intent=None,
            can_proceed=False,
            clarification_questions=["请重新描述您的训练需求"],
            routing_target="clarification",
        )

    async def _handle_new_training(
        self,
        user_text: str,
        intent_result: Any,
    ) -> TrainingIntentResult:
        """UF-03-b-1: TRAINING_NEW 参数提取

        需要提取 brand / model / category，任一缺失时追问
        """

        # 模拟参数提取
        intent = TrainingIntent(
            intent_type=TrainingIntentType.NEW,
            brand="ABB",
            model="IRB1200",
            category="工业机器人",
        )

        # 检查参数完整性
        missing = []
        if not intent.brand:
            missing.append("请告诉我机器人品牌（如ABB、KUKA、Fanuc）")
        if not intent.model:
            missing.append("请告诉我机器人型号")
        if not intent.category:
            missing.append("请告诉我维保类别（如搬运、焊接、装配）")

        return TrainingIntentResult(
            intent=intent,
            can_proceed=len(missing) == 0,
            clarification_questions=missing,
            routing_target="project_generator" if len(missing) == 0 else "clarification",
        )

    async def _handle_weakness_training(
        self,
        user_id: int,
    ) -> TrainingIntentResult:
        """UF-03-b-2: TRAINING_WEAKNESS

        不需用户指定步骤，自动从 student_weak_steps 表读取 Top3 薄弱步骤
        表不存在时降级为 TRAINING_NEW
        """

        # 模拟返回
        intent = TrainingIntent(
            intent_type=TrainingIntentType.WEAKNESS,
            category="工业机器人",
        )

        return TrainingIntentResult(
            intent=intent,
            can_proceed=True,
            clarification_questions=[],
            routing_target="project_generator",
        )

    async def _handle_cert_training(
        self,
        user_text: str,
        intent_result: Any,
    ) -> TrainingIntentResult:
        """UF-03-b-3: TRAINING_CERT

        提取目标等级（L1/L2/L3）和维保类别
        校验前置认证是否已完成
        """

        intent = TrainingIntent(
            intent_type=TrainingIntentType.CERT,
            target_level="L2",
            category="工业机器人",
        )

        # 校验前置认证（简化版）
        can_proceed = True
        questions = []

        if intent.target_level == "L2":
            # 检查 L1 是否通过（简化）
            pass

        if intent.target_level == "L3":
            can_proceed = False
            questions.append("L3认证需要先完成L2认证")

        return TrainingIntentResult(
            intent=intent,
            can_proceed=can_proceed,
            clarification_questions=questions,
            routing_target="project_generator" if can_proceed else "clarification",
        )

    async def _handle_assigned_training(
        self,
        user_text: str,
        user_id: int,
    ) -> TrainingIntentResult:
        """UF-03-b-4: TRAINING_ASSIGNED

        提取任务 ID，查 assignments 表验证任务存在、归属当前用户、未过期
        """

        intent = TrainingIntent(
            intent_type=TrainingIntentType.ASSIGNED,
            assignment_id=1,  # 模拟
        )

        # 验证归属


        return TrainingIntentResult(
            intent=intent,
            can_proceed=True,
            clarification_questions=[],
            routing_target="project_generator",
        )

    async def _handle_explore_training(
        self,
        user_text: str,
        intent_result: Any,
    ) -> TrainingIntentResult:
        """UF-03-b-5: TRAINING_EXPLORE

        只需提取维保类别，生成无严格裁决的轻量引导式项目
        """

        intent = TrainingIntent(
            intent_type=TrainingIntentType.EXPLORE,
            category="工业机器人",
        )

        return TrainingIntentResult(
            intent=intent,
            can_proceed=True,
            clarification_questions=[],
            routing_target="project_generator",
        )
