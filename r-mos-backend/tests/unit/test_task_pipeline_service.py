"""Task pipeline service tests."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.v1.endpoints.pipeline import StepCompleteRequest
from app.services.pipeline.task_pipeline_service import TaskPipelineService


@pytest.mark.asyncio
async def test_create_task_from_diagnosis():
    """Creates task + execution from diagnosis result."""
    mock_db = AsyncMock()

    # Track added objects to set IDs on flush
    added_objects = []
    def track_add(obj):
        added_objects.append(obj)
    mock_db.add = MagicMock(side_effect=track_add)

    async def mock_flush():
        # Simulate DB setting IDs
        for i, obj in enumerate(added_objects):
            if not hasattr(obj, 'id') or obj.id is None:
                obj.id = i + 1
    mock_db.flush = AsyncMock(side_effect=mock_flush)
    mock_db.commit = AsyncMock()

    # Mock mapping query (first call) and SOP query (second call)
    mock_mapping = MagicMock()
    mock_mapping.sop_id = 10
    mock_sop = MagicMock()
    mock_sop.id = 10
    mock_sop.name = "关节过热应急处理"

    mock_result_mapping = MagicMock()
    mock_result_mapping.scalar_one_or_none.return_value = mock_mapping
    mock_result_sop = MagicMock()
    mock_result_sop.scalar_one_or_none.return_value = mock_sop

    mock_db.execute = AsyncMock(side_effect=[mock_result_mapping, mock_result_sop])

    service = TaskPipelineService(mock_db)
    result = await service.create_task_from_diagnosis(
        diagnosis_trace_id="trace-001",
        fault_type="E001_OVERHEAT",
        student_id=1,
    )

    assert result["sop_name"] == "关节过热应急处理"
    assert result["task_id"] is not None
    assert mock_db.add.called


@pytest.mark.asyncio
async def test_complete_step_records_result():
    """Completing a step persists evidence and duration."""
    mock_db = AsyncMock()
    added_results = []
    mock_db.add = MagicMock(side_effect=added_results.append)
    mock_db.commit = AsyncMock()

    # Mock execution query
    mock_execution = MagicMock()
    mock_execution.id = 1
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_execution
    mock_db.execute = AsyncMock(return_value=mock_result)

    service = TaskPipelineService(mock_db)
    result = await service.complete_step(
        execution_id=1,
        step_index=1,
        evidence_type="photo",
        evidence_value={"url": "https://example.com/photo.jpg"},
        duration_seconds=45,
        is_compliant=False,
    )

    assert result["is_compliant"] is False
    assert len(added_results) == 1
    persisted = added_results[0]
    assert persisted.evidence_type == "photo"
    assert persisted.evidence_value == {"url": "https://example.com/photo.jpg"}
    assert persisted.duration_seconds == 45
    assert persisted.is_compliant is False


@pytest.mark.asyncio
async def test_complete_step_without_evidence_remains_backward_compatible():
    """Legacy callers may omit every optional evidence field."""
    mock_db = AsyncMock()
    added_results = []
    mock_db.add = MagicMock(side_effect=added_results.append)
    mock_db.commit = AsyncMock()

    request = StepCompleteRequest(step_index=2)
    service = TaskPipelineService(mock_db)
    result = await service.complete_step(
        execution_id=1,
        step_index=request.step_index,
        evidence_type=request.evidence_type,
        evidence_value=request.evidence_value,
        duration_seconds=request.duration_seconds,
        is_compliant=request.is_compliant,
    )

    assert result["is_compliant"] is True
    assert len(added_results) == 1
    persisted = added_results[0]
    assert persisted.evidence_type is None
    assert persisted.evidence_value is None
    assert persisted.duration_seconds is None
    assert persisted.is_compliant is True
