"""Unit tests for PDF document extractor."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.analysis_task import AnalysisTask, AnalysisTaskType, AnalysisTaskStatus
from app.models.robot_asset import RobotAsset, AssetType
from app.models.knowledge_document import KnowledgeDocument
from app.services.analysis.pdf_extractor import PdfExtractor


@pytest.fixture
def extractor():
    return PdfExtractor()


@pytest.fixture
def mock_task():
    task = MagicMock(spec=AnalysisTask)
    task.id = 1
    task.robot_model_id = 10
    task.task_type = AnalysisTaskType.PDF_EXTRACT
    task.input_document_ids = [100, 101]
    return task


@pytest.mark.asyncio
async def test_process_creates_knowledge_documents(extractor, mock_task):
    """应为每个 PDF 页面创建 KnowledgeDocument (ai_draft)。"""
    mock_db = AsyncMock()
    mock_asset = MagicMock(spec=RobotAsset)
    mock_asset.id = 100
    mock_asset.robot_model_id = 10
    mock_asset.asset_type = AssetType.UPLOAD_ORIGINAL
    mock_asset.file_path = "10/uploads/manual.pdf"

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_asset]
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch.object(extractor, "_extract_text_from_pdf") as mock_extract:
        mock_extract.return_value = [
            {"title": "第一章 概述", "content": "这是概述内容" * 50},
            {"title": "第二章 安装", "content": "这是安装内容" * 50},
        ]
        result = await extractor.process(mock_task, mock_db)

    assert result["documents_created"] == 2
    assert mock_db.add.call_count == 2
    created_doc = mock_db.add.call_args_list[0][0][0]
    assert isinstance(created_doc, KnowledgeDocument)
    assert created_doc.robot_model_id == 10
    assert created_doc.generation_status == "ai_draft"


@pytest.mark.asyncio
async def test_process_no_pdf_assets(extractor, mock_task):
    """没有 PDF 资产时应返回 documents_created=0。"""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await extractor.process(mock_task, mock_db)
    assert result["documents_created"] == 0


@pytest.mark.asyncio
async def test_extract_text_skips_empty_pages(extractor):
    """空白页面应被跳过。"""
    with patch("app.services.analysis.pdf_extractor.fitz") as mock_fitz:
        mock_doc = MagicMock()
        mock_page1 = MagicMock()
        mock_page1.get_text.return_value = "有内容的页面 " * 20
        mock_page2 = MagicMock()
        mock_page2.get_text.return_value = "   "
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page1, mock_page2]))
        mock_doc.__len__ = MagicMock(return_value=2)
        mock_doc.metadata = {"title": "测试文档"}
        mock_fitz.open.return_value.__enter__ = MagicMock(return_value=mock_doc)
        mock_fitz.open.return_value.__exit__ = MagicMock(return_value=False)

        chunks = extractor._extract_text_from_pdf("/fake/path.pdf")
    assert len(chunks) == 1
