"""Background analysis worker — polls pending tasks and dispatches them."""
import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.analysis_task import AnalysisTask, AnalysisTaskStatus
from app.models.robot_model import RobotModel, RobotStatus
from app.services.analysis.scheduler import AnalysisScheduler
from app.services.robot_asset_validator import validate_robot_assets
from app.services.storage.file_storage import LocalFileStorage

logger = logging.getLogger(__name__)
_storage = LocalFileStorage()


class AnalysisWorker:
    """后台异步 worker，轮询 pending 分析任务。"""

    def __init__(self, poll_interval: float = 10.0):
        self.poll_interval = poll_interval
        self.scheduler = AnalysisScheduler()
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """启动 worker 轮询循环。"""
        self._running = True
        logger.info(f"分析 Worker 启动 (轮询间隔: {self.poll_interval}s)")
        while self._running:
            try:
                count = await self._poll_once()
                if count > 0:
                    logger.info(f"本轮处理了 {count} 个分析任务")
            except Exception as e:
                logger.error(f"Worker 轮询异常: {e}", exc_info=True)
            await asyncio.sleep(self.poll_interval)

    async def stop(self) -> None:
        """停止 worker。"""
        self._running = False
        logger.info("分析 Worker 已停止")

    async def _poll_once(self) -> int:
        """查询并处理 pending 任务，返回处理数量。"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(AnalysisTask)
                .where(AnalysisTask.status == AnalysisTaskStatus.PENDING)
                .order_by(AnalysisTask.created_at)
                .limit(5)
            )
            tasks = result.scalars().all()

            if not tasks:
                return 0

            for task in tasks:
                await self.scheduler.dispatch(task, db)
                await self._update_robot_status(task, db)

            return len(tasks)

    async def _update_robot_status(self, task: AnalysisTask, db: AsyncSession) -> None:
        """根据任务完成状态更新 RobotModel 状态。"""
        if task.status != AnalysisTaskStatus.COMPLETED:
            return

        result = await db.execute(
            select(RobotModel).where(RobotModel.id == task.robot_model_id)
        )
        robot = result.scalar_one_or_none()
        if robot and robot.status == RobotStatus.ANALYZING:
            # 检查是否还有其他未完成任务
            pending_result = await db.execute(
                select(AnalysisTask).where(
                    AnalysisTask.robot_model_id == task.robot_model_id,
                    AnalysisTask.status.in_([AnalysisTaskStatus.PENDING, AnalysisTaskStatus.RUNNING]),
                )
            )
            if not pending_result.scalar_one_or_none():
                missing = validate_robot_assets(robot.id, _storage)
                if missing:
                    robot.status = RobotStatus.DRAFT
                    logger.warning(
                        "机器人 %s 分析完成但资产不完整（缺 %d 项），置为 DRAFT 待教师处理",
                        robot.id, len(missing),
                    )
                else:
                    robot.status = RobotStatus.READY
                await db.commit()


# 全局实例
analysis_worker = AnalysisWorker()
