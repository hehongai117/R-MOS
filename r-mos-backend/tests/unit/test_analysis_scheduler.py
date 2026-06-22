"""Unit tests for analysis task scheduler."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.models.analysis_task import AnalysisTask, AnalysisTaskType, AnalysisTaskStatus
from app.services.analysis.scheduler import AnalysisScheduler


@pytest.fixture
def scheduler():
    return AnalysisScheduler()


@pytest.fixture
def mock_task():
    task = MagicMock(spec=AnalysisTask)
    task.id = 1
    task.robot_model_id = 10
    task.task_type = AnalysisTaskType.FULL
    task.status = AnalysisTaskStatus.PENDING
    task.input_document_ids = [1, 2]
    task.output_summary = None
    task.error_message = None
    task.completed_at = None
    return task


@pytest.mark.asyncio
async def test_dispatch_sets_running_then_completed(scheduler, mock_task):
    mock_db = AsyncMock()
    mock_task.task_type = AnalysisTaskType.PDF_EXTRACT

    with patch.object(scheduler, "_get_processor") as mock_get:
        mock_processor = AsyncMock(return_value={"documents_created": 3})
        mock_get.return_value = mock_processor

        await scheduler.dispatch(mock_task, mock_db)

    assert mock_task.status == AnalysisTaskStatus.COMPLETED
    assert mock_task.output_summary == {"documents_created": 3}
    assert mock_task.completed_at is not None
    assert mock_db.commit.await_count >= 1


@pytest.mark.asyncio
async def test_dispatch_sets_failed_on_error(scheduler, mock_task):
    mock_db = AsyncMock()
    mock_task.task_type = AnalysisTaskType.PDF_EXTRACT

    # 失败分支会回滚后重新查询 task（res.scalar_one()），让该重查返回同一个 mock_task
    refetch_result = MagicMock()
    refetch_result.scalar_one.return_value = mock_task
    mock_db.execute.return_value = refetch_result

    with patch.object(scheduler, "_get_processor") as mock_get:
        mock_get.return_value = AsyncMock(side_effect=ValueError("PDF 解析失败"))

        await scheduler.dispatch(mock_task, mock_db)

    assert mock_task.status == AnalysisTaskStatus.FAILED
    assert "PDF 解析失败" in mock_task.error_message
    assert mock_db.commit.await_count >= 1


@pytest.mark.asyncio
async def test_get_processor_returns_correct_handler(scheduler):
    for task_type in AnalysisTaskType:
        processor = scheduler._get_processor(task_type)
        assert callable(processor), f"No processor for {task_type}"


@pytest.mark.asyncio
async def test_dispatch_full_runs_all_sub_processors(scheduler, mock_task):
    mock_db = AsyncMock()
    mock_task.task_type = AnalysisTaskType.FULL

    with patch("app.services.analysis.scheduler.process_pdf_extract", new_callable=AsyncMock) as mock_pdf, \
         patch("app.services.analysis.scheduler.process_sop_generate", new_callable=AsyncMock) as mock_sop, \
         patch("app.services.analysis.scheduler.process_cad_parse", new_callable=AsyncMock) as mock_cad:
        mock_pdf.return_value = {"documents_created": 2}
        mock_sop.return_value = {"sops_created": 1}
        mock_cad.return_value = {"skipped": True}

        await scheduler.dispatch(mock_task, mock_db)

    assert mock_task.status == AnalysisTaskStatus.COMPLETED
    mock_pdf.assert_awaited_once()
    mock_sop.assert_awaited_once()
    mock_cad.assert_awaited_once()
