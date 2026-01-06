"""
Event相关Pydantic Schema
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class EventCreate(BaseModel):
    """创建Event请求"""
    task_id: int
    event_type: str
    step_index: Optional[int] = None
    action: Optional[str] = None
    target: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    result: Optional[str] = None
    duration_ms: Optional[int] = None
    is_error: bool = False
    error_message: Optional[str] = None


class EventResponse(BaseModel):
    """Event响应"""
    id: int
    task_id: int
    event_type: str
    step_index: Optional[int]
    timestamp: datetime
    action: Optional[str]
    target: Optional[str]
    parameters: Optional[Dict[str, Any]]
    result: Optional[str]
    duration_ms: Optional[int]
    is_error: bool
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


class EventStreamResponse(BaseModel):
    """Event流响应"""
    task_id: int
    events: List[EventResponse]
    total_events: int
