"""
UF-02-b: Agent Policy Factory
Agent 策略工厂

职责：
- 根据用户角色和记忆构建 Agent 配置
- 学生/教师/管理员有不同的行为策略
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Agent 配置"""
    guidance_mode: bool = True
    hint_level: int = 3
    difficulty_cap: int = 5
    show_answers: bool = False
    observe_mode: bool = False
    can_override_verdict: bool = False
    show_full_analysis: bool = False
    management_mode: bool = False
    audit_access: bool = False
    system_prompt_addition: str = ""


class AgentPolicyFactory:
    """Agent 策略工厂"""

    @staticmethod
    async def build(
        db: AsyncSession,
        user_id: int,
        memory: Optional[dict] = None,
    ) -> AgentConfig:
        """UF-02-b-1: 构建 Agent 配置

        Args:
            db: 数据库会话
            user_id: 用户ID
            memory: 可选的记忆数据

        Returns:
            AgentConfig: Agent 配置
        """
        # 获取用户信息
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"[UF-02-b] User {user_id} not found, using default config")
            return AgentConfig()

        role = getattr(user, 'role', 'student')
        hint_level = getattr(user, 'hint_level', 3)
        skill_level = memory.get("skill_level", 1) if memory else 1

        if role == "student":
            config = AgentPolicyFactory._build_student_config(hint_level, skill_level)
        elif role == "teacher":
            config = AgentPolicyFactory._build_teacher_config()
        elif role == "admin":
            config = AgentPolicyFactory._build_admin_config()
        else:
            config = AgentPolicyFactory._build_student_config(hint_level, skill_level)

        logger.info(f"[UF-02-b] Built agent config for user {user_id}, role: {role}")
        return config

    @staticmethod
    def _build_student_config(hint_level: int, skill_level: int) -> AgentConfig:
        """UF-02-b-2: 学生配置"""
        return AgentConfig(
            guidance_mode=True,
            hint_level=hint_level,
            difficulty_cap=skill_level + 1,
            show_answers=False,
            system_prompt_addition=(
                "你是一位维保培训导师。请引导学生思考，"
                "不要直接给出答案或正确数值。"
                f"根据学生的提示级别({hint_level})调整指导细度。"
            ),
        )

    @staticmethod
    def _build_teacher_config() -> AgentConfig:
        """UF-02-b-3: 教师配置"""
        return AgentConfig(
            guidance_mode=False,
            observe_mode=True,
            can_override_verdict=True,
            show_full_analysis=True,
            system_prompt_addition=(
                "你是一位专业的维保培训教师。"
                "请直接给出完整的分析和参考答案。"
                "可以查看学员的完整操作历史并提供教学指导。"
            ),
        )

    @staticmethod
    def _build_admin_config() -> AgentConfig:
        """UF-02-b-4: 管理员配置"""
        return AgentConfig(
            guidance_mode=False,
            management_mode=True,
            audit_access=True,
            system_prompt_addition=(
                "你是一位系统管理员。"
                "可以访问审计日志和系统配置。"
            ),
        )

    @staticmethod
    def get_hint_level_prompt(hint_level: int) -> str:
        """UF-02-b-2: hint_level 映射到提示细度"""
        hints = {
            1: "只确认操作结果是否正确，不给出进一步提示。",
            2: "简要确认操作结果，可给出轻微暗示。",
            3: "给出操作要点提示，引导学生思考。",
            4: "给出较详细的步骤提示，但仍不直接告诉答案。",
            5: "提供逐步骤详细引导，帮助学生完成操作。",
        }
        return hints.get(hint_level, hints[3])
