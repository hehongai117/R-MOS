"""Test that FULL pipeline includes assembly_build step."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.analysis.scheduler import AnalysisScheduler


@pytest.mark.asyncio
async def test_full_pipeline_includes_assembly_build():
    """FULL pipeline should include assembly_build step."""
    scheduler = AnalysisScheduler()
    task = MagicMock()
    task.id = 1
    task.robot_model_id = 1
    db = AsyncMock()

    with patch("app.services.analysis.scheduler.process_pdf_extract", new_callable=AsyncMock) as mock_pdf, \
         patch("app.services.analysis.scheduler.process_sop_generate", new_callable=AsyncMock) as mock_sop, \
         patch("app.services.analysis.scheduler.process_cad_parse", new_callable=AsyncMock) as mock_cad, \
         patch("app.services.analysis.scheduler.process_assembly_build", new_callable=AsyncMock) as mock_assembly:
        mock_pdf.return_value = {"docs_created": 0}
        mock_sop.return_value = {"sops_created": 0}
        mock_cad.return_value = {"models_converted": 0}
        mock_assembly.return_value = {"assembly_built": True}

        result = await scheduler._process_full(task, db)

        mock_assembly.assert_called_once_with(task, db)
        assert "assembly_build" in result
        assert result["assembly_build"] == {"assembly_built": True}
