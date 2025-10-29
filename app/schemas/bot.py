"""
Bot schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
from datetime import datetime


class BotResponse(BaseModel):
    id: int
    bot_id: str
    user_id: int
    platform: Optional[str] = None
    bot_name: Optional[str] = None
    video_download_url: Optional[str] = None
    transcript_url: Optional[str] = None
    meeting_id: Optional[int] = None
    recording_status: str = "pending"
    recording_data: Optional[Dict[str, Any]] = None
    video_recording_url: Optional[str] = None
    recording_expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BotDetailResponse(BaseModel):
    id: int
    bot_id: str
    user_id: int
    platform: Optional[str] = None
    bot_name: Optional[str] = None
    video_download_url: Optional[str] = None
    transcript_url: Optional[str] = None
    meeting_id: Optional[int] = None
    recording_status: str = "pending"
    recording_data: Optional[Dict[str, Any]] = None
    video_recording_url: Optional[str] = None
    recording_expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Meeting details
    meeting_title: Optional[str] = None
    meeting_url: Optional[str] = None
    meeting_platform: Optional[str] = None
    meeting_scheduled_time: Optional[datetime] = None
    meeting_status: Optional[str] = None

    class Config:
        from_attributes = True


class BotsListResponse(BaseModel):
    success: bool = True
    message: str = "Bots retrieved successfully"
    data: List[Union[BotResponse, BotDetailResponse]]
    total_count: int
    filtered_count: Optional[int] = None
    filters_applied: Optional[Dict[str, Any]] = None