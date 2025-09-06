"""
Meeting schemas
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


class MeetingCreate(BaseModel):
    title: str
    description: Optional[str] = None
    meeting_url: str
    platform: str
    scheduled_time: datetime
    duration_minutes: Optional[int] = 60
    digital_twin_id: Optional[int] = None
    auto_join: Optional[bool] = True


class MeetingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    meeting_url: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    digital_twin_id: Optional[int] = None
    auto_join: Optional[bool] = None
    status: Optional[str] = None


class MeetingResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    meeting_url: str
    platform: str
    scheduled_time: datetime
    duration_minutes: int
    digital_twin_id: Optional[int]
    status: str
    auto_join: bool
    transcript: Optional[str]
    summary: Optional[str]
    action_items: Optional[List[Dict[str, Any]]]
    participants: Optional[List[str]]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True