"""AnalysisScheduler — 从数据库取 AnalysisTask，按类型分发到处理器，管理状态流转。"""
from datetime import datetime, timezone
from typing import Callable

from app.models.analysis_task import AnalysisTask, AnalysisTaskType, AnalysisTaskStatus


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

    async def dispatch(self, task: AnalysisTask, db) -> None:
        """执行任务调度：PENDING → RUNNING，调用处理器，→ COMPLETED/FAILED，commit。"""
        # 1. 标记为 RUNNING 并提交
        task.status = AnalysisTaskStatus.RUNNING
        await db.commit()

        processor = self._get_processor(task.task_type)

        try:
            result = await processor(task, db)
            task.status = AnalysisTaskStatus.COMPLETED
            task.output_summary = result
            task.completed_at = datetime.now(timezone.utc)
        except Exception as e:
            task.status = AnalysisTaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.now(timezone.utc)

        await db.commit()

    async def _process_full(self, task: AnalysisTask, db) -> dict:
        """FULL 类型：依次运行 PDF 提取 → SOP 生成 → CAD 解析。

        每个子步骤的异常单独捕获，只在结果中记录 error，整体任务仍然 COMPLETED。
        """
        results: dict = {}

        for name, processor in [
            ("pdf_extract", process_pdf_extract),
            ("sop_generate", process_sop_generate),
            ("cad_parse", process_cad_parse),
        ]:
            try:
                step_result = await processor(task, db)
                results[name] = step_result
            except Exception as e:
                results[name] = {"error": str(e)}

        return results
