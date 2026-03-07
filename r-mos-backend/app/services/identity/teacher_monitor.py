"""
UF-07: Teacher Monitoring Service
教师实时监控服务

职责：
- WebSocket 频道管理 (/ws/class/{class_id})
- 训练状态变更事件发布
- 步骤失败预警推送
"""
from __future__ import annotations

import logging
from typing import Optional
from datetime import datetime

from app.services.websocket_manager import manager

logger = logging.getLogger(__name__)


class TeacherMonitorService:
    """教师实时监控服务 - UF-07"""

    # 频道前缀
    CLASS_CHANNEL_PREFIX = "class:"

    async def subscribe_teacher(
        self,
        teacher_id: int,
        class_ids: list[int],
    ) -> None:
        """UF-07-a-1: 教师登录后订阅班级频道

        Args:
            teacher_id: 教师ID
            class_ids: 管理的班级ID列表
        """
        # 订阅每个班级的频道
        for class_id in class_ids:
            channel = self._class_channel(class_id)

            logger.info(f"[UF-07] Teacher {teacher_id} subscribed to channel {channel}")

    async def publish_session_update(
        self,
        class_id: int,
        event_type: str,
        data: dict,
    ) -> None:
        """UF-07-a-2: 发布训练会话状态变更事件

        Args:
            class_id: 班级ID
            event_type: 事件类型 (step_completed / step_failed / session_submitted)
            data: 事件数据
        """
        channel = self._class_channel(class_id)

        message = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": data,
        }

        await manager.broadcast_to_channel(channel, message)
        logger.info(f"[UF-07] Published {event_type} to channel {channel}")

    async def publish_step_warning(
        self,
        class_id: int,
        user_id: int,
        step_id: str,
        attempt_count: int,
    ) -> None:
        """UF-07-a-3: 发布步骤失败预警

        当学员步骤 attempt_count >= 3 时触发

        Args:
            class_id: 班级ID
            user_id: 学员ID
            step_id: 步骤ID
            attempt_count: 当前尝试次数
        """
        channel = self._class_channel(class_id)

        message = {
            "type": "step_warning",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": {
                "user_id": user_id,
                "step_id": step_id,
                "attempt_count": attempt_count,
                "message": f"学员步骤 {step_id} 已失败 {attempt_count} 次",
            },
        }

        await manager.broadcast_to_channel(channel, message)
        logger.warning(
            f"[UF-07] Step warning: user {user_id}, step {step_id}, "
            f"attempts {attempt_count} in class {class_id}"
        )

    async def publish_teacher_message(
        self,
        class_id: int,
        user_id: int,
        message: str,
    ) -> None:
        """UF-07-b-3: 教师发送提示给学员

        Args:
            class_id: 班级ID
            user_id: 学员ID
            message: 教师消息内容
        """
        channel = self._class_channel(class_id)

        # 构建消息
        ws_message = {
            "type": "teacher_message",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": {
                "user_id": user_id,
                "message": message,
                "sender_type": "teacher",
            },
        }

        # 发送给特定学员
        await manager.send_to_user(user_id, ws_message)
        logger.info(f"[UF-07] Sent teacher message to user {user_id}")

    def _class_channel(self, class_id: int) -> str:
        """获取班级频道名称"""
        return f"{self.CLASS_CHANNEL_PREFIX}{class_id}"


# 全局实例
teacher_monitor = TeacherMonitorService()
