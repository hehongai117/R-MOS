"""Unit tests for fault code extractor."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.analysis_task import AnalysisTask, AnalysisTaskType
from app.models.knowledge_document import KnowledgeDocument
from app.services.analysis.fault_extractor import FaultExtractor


@pytest.fixture
def extractor():
    return FaultExtractor()


@pytest.fixture
def mock_task():
    task = MagicMock(spec=AnalysisTask)
    task.id = 1
    task.robot_model_id = 10
    task.task_type = AnalysisTaskType.FULL
    task.input_document_ids = [100]
    return task


@pytest.fixture
def sample_llm_response():
    return json.dumps({
        "fault_codes": [
            {
                "fault_type": "E001_OVERHEAT",
                "description": "电机过热，温度超过 80°C",
                "symptoms": ["电机发出异味", "温度传感器报警"],
                "difficulty": "intermediate",
            },
            {
                "fault_type": "E002_ENCODER_FAIL",
                "description": "编码器信号丢失",
                "symptoms": ["关节位置跳变"],
                "difficulty": "advanced",
            },
        ]
    })


@pytest.mark.asyncio
async def test_process_extracts_fault_codes(extractor, mock_task, sample_llm_response):
    """应从 LLM 响应提取故障码列表。"""
    mock_db = AsyncMock()
    mock_doc = MagicMock(spec=KnowledgeDocument)
    mock_doc.content = "故障排除手册内容" * 20
    mock_doc.robot_model_id = 10
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_doc]
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.services.analysis.fault_extractor.llm_router") as mock_router:
        mock_llm_resp = MagicMock()
        mock_llm_resp.content = sample_llm_response
        mock_router.chat_with_fallback = AsyncMock(return_value=mock_llm_resp)

        result = await extractor.process(mock_task, mock_db)

    assert result["fault_codes_extracted"] == 2
    assert len(result["fault_codes"]) == 2
    assert result["fault_codes"][0]["fault_type"] == "E001_OVERHEAT"
    # 不应有数据库 add 调用（不创建 FaultSOPMapping）
    mock_db.add.assert_not_called()


@pytest.mark.asyncio
async def test_process_no_documents(extractor, mock_task):
    """没有知识文档时应返回空结果。"""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await extractor.process(mock_task, mock_db)
    assert result["fault_codes_extracted"] == 0
    assert result["fault_codes"] == []


@pytest.mark.asyncio
async def test_process_handles_invalid_json(extractor, mock_task):
    """LLM 返回无效 JSON 时应优雅降级。"""
    mock_db = AsyncMock()
    mock_doc = MagicMock(spec=KnowledgeDocument)
    mock_doc.content = "故障排除内容" * 20
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_doc]
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.services.analysis.fault_extractor.llm_router") as mock_router:
        mock_llm_resp = MagicMock()
        mock_llm_resp.content = "无效JSON"
        mock_router.chat_with_fallback = AsyncMock(return_value=mock_llm_resp)

        result = await extractor.process(mock_task, mock_db)
    assert result["fault_codes_extracted"] == 0
    assert result["fault_codes"] == []
