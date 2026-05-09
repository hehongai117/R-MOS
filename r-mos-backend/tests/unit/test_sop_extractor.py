"""Unit tests for SOP extractor."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.analysis_task import AnalysisTask, AnalysisTaskType
from app.models.knowledge_document import KnowledgeDocument
from app.models.sop import SOP, SOPStep
from app.services.analysis.sop_extractor import SopExtractor


@pytest.fixture
def extractor():
    return SopExtractor()


@pytest.fixture
def mock_task():
    task = MagicMock(spec=AnalysisTask)
    task.id = 1
    task.robot_model_id = 10
    task.task_type = AnalysisTaskType.SOP_GENERATE
    task.input_document_ids = [100]
    return task


@pytest.fixture
def sample_llm_response():
    return json.dumps({
        "sops": [
            {
                "name": "电机更换流程",
                "description": "更换机器人关节电机的标准操作流程",
                "category": "维修",
                "difficulty_level": "medium",
                "estimated_time": 1800,
                "steps": [
                    {
                        "title": "断电确认",
                        "description": "确保机器人已完全断电，检查电源指示灯熄灭",
                        "expected_action": "verify",
                        "is_critical": True,
                    },
                    {
                        "title": "拆卸外壳",
                        "description": "使用 T10 螺丝刀拆卸关节外壳 4 颗固定螺丝",
                        "expected_action": "remove",
                        "is_critical": False,
                    },
                ]
            }
        ]
    })


@pytest.mark.asyncio
async def test_process_creates_sop_and_steps(extractor, mock_task, sample_llm_response):
    """应从 LLM 响应创建 SOP 及其步骤。"""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()

    mock_doc = MagicMock(spec=KnowledgeDocument)
    mock_doc.content = "这是一份关于电机更换的维保手册..." * 20
    mock_doc.robot_model_id = 10
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_doc]
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.services.analysis.sop_extractor.llm_router") as mock_router:
        mock_llm_resp = MagicMock()
        mock_llm_resp.content = sample_llm_response
        mock_router.chat_with_fallback = AsyncMock(return_value=mock_llm_resp)

        result = await extractor.process(mock_task, mock_db)

    assert result["sops_created"] == 1
    assert result["steps_created"] == 2
    sop_call = mock_db.add.call_args_list[0][0][0]
    assert isinstance(sop_call, SOP)
    assert sop_call.robot_model_id == 10
    assert sop_call.name == "电机更换流程"


@pytest.mark.asyncio
async def test_process_no_documents(extractor, mock_task):
    """没有知识文档时应返回空结果。"""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await extractor.process(mock_task, mock_db)
    assert result["sops_created"] == 0
    assert result["steps_created"] == 0


@pytest.mark.asyncio
async def test_process_handles_invalid_llm_json(extractor, mock_task):
    """LLM 返回无效 JSON 时应优雅降级。"""
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_doc = MagicMock(spec=KnowledgeDocument)
    mock_doc.content = "维保手册内容" * 20
    mock_doc.robot_model_id = 10
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_doc]
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.services.analysis.sop_extractor.llm_router") as mock_router:
        mock_llm_resp = MagicMock()
        mock_llm_resp.content = "这不是有效的 JSON"
        mock_router.chat_with_fallback = AsyncMock(return_value=mock_llm_resp)

        result = await extractor.process(mock_task, mock_db)

    assert result["sops_created"] == 0
    assert "steps_created" in result or "parse_error" in result
