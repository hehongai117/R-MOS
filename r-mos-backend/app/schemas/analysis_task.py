# r-mos-backend/app/schemas/analysis_task.py
"""Pydantic schemas for AnalysisTask API responses."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class AnalysisTaskResponse(BaseModel):
    id: int
    robot_model_id: int
    task_type: str
    status: str
    input_document_ids: Optional[list] = None
    output_summary: Optional[dict] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisTaskListResponse(BaseModel):
    items: List[AnalysisTaskResponse]
    total: int
