"""Unit tests for analysis background worker."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.analysis.worker import AnalysisWorker


@pytest.fixture
def worker():
    return AnalysisWorker(poll_interval=0.05)


@pytest.mark.asyncio
async def test_worker_starts_and_stops(worker):
    """Worker 应能启动和停止。"""
    with patch.object(worker, "_poll_once", new_callable=AsyncMock) as mock_poll:
        mock_poll.return_value = 0

        task = asyncio.create_task(worker.start())
        await asyncio.sleep(0.2)
        await worker.stop()

        # 给 worker 一点时间完成当前 sleep
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass

    assert mock_poll.await_count >= 1


@pytest.mark.asyncio
async def test_poll_once_dispatches_pending_tasks(worker):
    """_poll_once 应查询 pending 任务并分发。"""
    mock_task = MagicMock()
    mock_task.id = 1

    with patch("app.services.analysis.worker.AsyncSessionLocal") as mock_factory:
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_task]
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = mock_db

        with patch.object(worker.scheduler, "dispatch", new_callable=AsyncMock) as mock_dispatch, \
             patch.object(worker, "_update_robot_status", new_callable=AsyncMock):
            count = await worker._poll_once()

    assert count == 1
    mock_dispatch.assert_awaited_once_with(mock_task, mock_db)


@pytest.mark.asyncio
async def test_poll_once_no_tasks(worker):
    """没有 pending 任务时应返回 0。"""
    with patch("app.services.analysis.worker.AsyncSessionLocal") as mock_factory:
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = mock_db

        count = await worker._poll_once()

    assert count == 0
