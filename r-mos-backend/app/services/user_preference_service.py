"""
P2-4: User Preference Service
用户偏好设置服务

职责：
- 存储和获取用户偏好设置
- 支持指导模式偏好（full_time / on_demand / silent）
"""

from __future__ import annotations

import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_preference import UserPreference

logger = logging.getLogger(__name__)


class GuidanceMode:
    """指导模式常量"""
    FULL_TIME = "full_time"  # 全程指导
    ON_DEMAND = "on_demand"    # 按需指导
    SILENT = "silent"          # 静默模式

    ALL_MODES = [FULL_TIME, ON_DEMAND, SILENT]

    @classmethod
    def get_display_name(cls, mode: str) -> str:
        """获取模式的中文显示名称"""
        names = {
            cls.FULL_TIME: "全程指导",
            cls.ON_DEMAND: "按需指导",
            cls.SILENT: "静默模式",
        }
        return names.get(mode, mode)


class UserPreferenceService:
    """用户偏好设置服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_preference(
        self,
        user_id: int,
    ) -> Optional[UserPreference]:
        """获取用户偏好设置"""
        result = await self.db.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create_preference(
        self,
        user_id: int,
    ) -> UserPreference:
        """获取或创建用户偏好设置"""
        pref = await self.get_preference(user_id)
        if not pref:
            pref = UserPreference(
                user_id=user_id,
                guidance_mode=GuidanceMode.ON_DEMAND,
                preferences={},
            )
            self.db.add(pref)
            await self.db.commit()
            await self.db.refresh(pref)
            logger.info(f"[P2-4] Created default preference for user {user_id}")
        return pref

    async def update_guidance_mode(
        self,
        user_id: int,
        mode: str,
    ) -> UserPreference:
        """更新用户指导模式"""
        if mode not in GuidanceMode.ALL_MODES:
            raise ValueError(
                f"Invalid guidance mode: {mode}. "
                f"Valid modes: {GuidanceMode.ALL_MODES}"
            )

        pref = await self.get_or_create_preference(user_id)
        old_mode = pref.guidance_mode
        pref.guidance_mode = mode

        await self.db.commit()
        await self.db.refresh(pref)

        logger.info(
            f"[P2-4] User {user_id} guidance mode changed: {old_mode} -> {mode}"
        )

        return pref

    async def update_preferences(
        self,
        user_id: int,
        preferences: dict,
    ) -> UserPreference:
        """更新其他偏好设置"""
        pref = await self.get_or_create_preference(user_id)
        current_prefs = pref.preferences or {}
        current_prefs.update(preferences)
        pref.preferences = current_prefs

        await self.db.commit()
        await self.db.refresh(pref)

        logger.info(f"[P2-4] Updated preferences for user {user_id}")

        return pref

    async def get_guidance_mode(
        self,
        user_id: int,
    ) -> str:
        """获取用户的指导模式（便捷方法）"""
        pref = await self.get_or_create_preference(user_id)
        return pref.guidance_mode
