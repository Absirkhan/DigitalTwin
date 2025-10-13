"""
Meeting schemas
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class MeetingPlatform(str, Enum):
    ZOOM = "zoom"
    GOOGLE_MEET = "google_meet"
    MICROSOFT_TEAMS = "microsoft_teams"
    WEBEX = "webex"
    OTHER = "other"


class MeetingStatus(str, Enum):
    SCHEDULED = "scheduled"
    JOINING = "joining"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TranscriptChunk(BaseModel):
    speaker: str
    text: str
    timestamp: Optional[float] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class MeetingInfo(BaseModel):
    title: str
    platform: MeetingPlatform
    meeting_url: str
    scheduled_time: datetime
    duration_minutes: int
    bot_id: Optional[str] = None
    status: MeetingStatus
    participants: Optional[List[str]] = None


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


class MeetingJoinRequest(BaseModel):
    meeting_url: str
    recording_config: Optional[Dict[str, Any]] = None
    bot_name: Optional[str] = None
    profile_picture: Optional[str] = None  # URL for bot avatar
    enable_realtime_processing: Optional[bool] = False


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
    bot_id: Optional[str] = None  # Added for Recall API response

    class Config:
        from_attributes = True


class MeetingJoinResponse(BaseModel):
    """Response for joining a meeting via Recall API"""
    success: bool
    message: str
    bot_id: Optional[str] = None
    status: Optional[str] = None
    meeting_url: Optional[str] = None
    bot_name: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


class TranscriptSegment(BaseModel):
    """Individual transcript segment"""
    speaker: Optional[str] = None
    text: str
    timestamp: Optional[float] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class MeetingTranscriptRequest(BaseModel):
    """Request payload for receiving meeting transcript"""
    bot_id: str
    meeting_id: Optional[str] = None
    transcript_segments: List[TranscriptSegment]
    full_transcript: Optional[str] = None
    meeting_url: Optional[str] = None
    status: Optional[str] = None
    participants: Optional[List[str]] = None


class MeetingTranscriptResponse(BaseModel):
    """Response for transcript processing"""
    success: bool
    message: str
    meeting_id: Optional[int] = None
    transcript_saved: bool = False
    summary_generated: bool = False
    action_items_extracted: bool = False


class TranscriptGetResponse(BaseModel):
    """Response for getting transcripts"""
    success: bool
    message: str
    data: Optional[Any] = None  # Changed from List to Any to handle different response structures
    bot_id: Optional[str] = None
    total_count: Optional[int] = None
    error_details: Optional[Dict[str, Any]] = None


class TranscriptDetailResponse(BaseModel):
    """Response for getting a specific transcript"""
    success: bool
    message: str
    data: Optional[Any] = None  # Changed from Dict to Any to handle different response structures
    error_details: Optional[Dict[str, Any]] = None