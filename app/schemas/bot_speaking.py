"""
Bot Speaking Schemas

Pydantic schemas for bot speaking API requests and responses.
"""

from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel, Field, validator


class BotResponseItem(BaseModel):
    """Single bot response item in history."""
    id: int
    trigger_text: str
    response_text: str
    response_style: str
    timestamp: datetime
    success: bool
    latency_ms: Optional[int] = None
    audio_url: Optional[str] = None

    class Config:
        from_attributes = True


class BotResponseHistoryResponse(BaseModel):
    """Response for bot response history endpoint."""
    meeting_id: int
    meeting_title: str
    total_responses: int
    responses: List[BotResponseItem]
    bot_response_enabled: bool
    bot_response_count: int
    bot_max_responses: int
    bot_response_style: str


class MeetingBotSpeakingUpdate(BaseModel):
    """Update bot speaking settings for a meeting."""
    bot_response_enabled: Optional[bool] = Field(None, description="Enable/disable bot speaking")
    bot_response_style: Optional[str] = Field(
        None,
        description="Response style: professional, casual, technical, brief"
    )
    bot_max_responses: Optional[int] = Field(
        None,
        ge=1,
        le=100,
        description="Maximum responses allowed per meeting"
    )

    @validator('bot_response_style')
    def validate_response_style(cls, v):
        if v is not None:
            allowed_styles = ['professional', 'casual', 'technical', 'brief']
            if v not in allowed_styles:
                raise ValueError(f"Response style must be one of: {', '.join(allowed_styles)}")
        return v


class BotSpeakingSettingsResponse(BaseModel):
    """Response for global bot speaking settings."""
    enable_bot_speaking: bool
    bot_name: str

    class Config:
        from_attributes = True


class BotSpeakingSettingsUpdate(BaseModel):
    """Update global bot speaking settings."""
    enable_bot_speaking: Optional[bool] = Field(None, description="Global toggle for bot speaking")
    bot_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Bot name")


class BotSpeakingStatsResponse(BaseModel):
    """Statistics for bot speaking activity."""
    total_responses: int
    successful_responses: int
    failed_responses: int
    success_rate: float = Field(..., description="Success rate as percentage (0-100)")
    average_latency_ms: int
    responses_by_style: Dict[str, int]
    total_meetings_with_responses: int
    period_days: int
