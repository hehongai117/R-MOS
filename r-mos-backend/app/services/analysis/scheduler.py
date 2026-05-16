"""AnalysisScheduler — 从数据库取 AnalysisTask，按类型分发到处理器，管理状态流转。"""
import logging
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_task import AnalysisTask, AnalysisTaskType, AnalysisTaskStatus

logger = logging.getLogger(__name__)


async def process_pdf_extract(task: AnalysisTask, db) -> dict:
    """PDF 文档提取处理器（Task 3.2 实现）。"""
    from app.services.analysis.pdf_extractor import PdfExtractor
    return await PdfExtractor().process(task, db)


async def process_sop_generate(task: AnalysisTask, db) -> dict:
    """SOP 生成处理器（Task 3.3 实现）。"""
    from app.services.analysis.sop_extractor import SopExtractor
    return await SopExtractor().process(task, db)


async def process_cad_parse(task: AnalysisTask, db) -> dict:
    """CAD 解析处理器（Task 3.5 实现）。"""
    from app.services.analysis.cad_converter import CadConverter
    return await CadConverter().process(task, db)


async def process_assembly_build(task: AnalysisTask, db) -> dict:
    """Assembly build — URDF parse + mesh convert + manifest generation."""
    from app.services.analysis.assembly_builder import AssemblyBuilder
    return await AssemblyBuilder().process(task, db)


class AnalysisScheduler:
    """AI 分析任务调度器。

    负责：
    1. 按任务类型分发到对应处理器
    2. 管理 PENDING → RUNNING → COMPLETED/FAILED 状态流转
    3. FULL 类型依次执行所有子处理器，子步骤失败只记录 error，整体仍标记 COMPLETED
    """

    def _get_processor(self, task_type: AnalysisTaskType) -> Callable:
        """返回与任务类型对应的处理器函数（或绑定方法）。"""
        mapping: dict[AnalysisTaskType, Callable] = {
            AnalysisTaskType.PDF_EXTRACT: process_pdf_extract,
            AnalysisTaskType.SOP_GENERATE: process_sop_generate,
            AnalysisTaskType.CAD_PARSE: process_cad_parse,
            AnalysisTaskType.FULL: self._process_full,
        }
        return mapping[task_type]

    async def dispatch(self, task: AnalysisTask, db: AsyncSession) -> None:
        """执行任务调度：PENDING → RUNNING，调用处理器，→ COMPLETED/FAILED，commit。"""
        task_id = task.id
        task_type = task.task_type
        robot_model_id = task.robot_model_id

        # 1. 标记为 RUNNING 并提交
        task.status = AnalysisTaskStatus.RUNNING
        await db.commit()
        await db.refresh(task)
        logger.info("Task %s (type=%s) RUNNING", task_id, task_type)

        try:
            processor = self._get_processor(task_type)
            result = await processor(task, db)
            task.status = AnalysisTaskStatus.COMPLETED
            task.output_summary = result
            task.completed_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info("Task %s COMPLETED", task_id)
        except Exception as e:
            await db.rollback()
            # Re-fetch task after rollback
            from sqlalchemy import select
            res = await db.execute(select(AnalysisTask).where(AnalysisTask.id == task_id))
            task = res.scalar_one()
            task.status = AnalysisTaskStatus.FAILED
            task.error_message = str(e)[:500]
            task.completed_at = datetime.now(timezone.utc)
            await db.commit()
            logger.error("Task %s FAILED: %s", task_id, e)

    async def _process_full(self, task: AnalysisTask, db: AsyncSession) -> dict:
        """FULL 类型：依次运行 PDF 提取 → SOP 生成 → CAD 解析 → 装配构建。

        每个子步骤的异常单独捕获，只在结果中记录 error，整体任务仍然 COMPLETED。
        """
        results: dict = {}

        for name, processor in [
            ("pdf_extract", process_pdf_extract),
            ("sop_generate", process_sop_generate),
            ("cad_parse", process_cad_parse),
            ("assembly_build", process_assembly_build),
        ]:
            try:
                step_result = await processor(task, db)
                results[name] = step_result
            except Exception as e:
                results[name] = {"error": str(e)}

        return results
