"""
Pydantic schemas for real-time transcript events

Minimal schemas for ultra-low latency serialization/validation
"""

from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime


class RealtimeTranscriptChunk(BaseModel):
    """
    A single real-time transcript chunk from Recall.ai

    Optimized for minimal serialization overhead
    """
    meeting_id: int = Field(..., description="Meeting identifier")
    speaker: str = Field(..., description="Speaker name or ID")
    text: str = Field(..., description="Transcript text")
    timestamp: float = Field(..., description="Unix timestamp or seconds from meeting start")
    confidence: Optional[float] = Field(None, description="Speech recognition confidence (0-1)")
    is_final: Optional[bool] = Field(True, description="Whether this is a final transcript or interim")

    class Config:
        json_schema_extra = {
            "example": {
                "meeting_id": 123,
                "speaker": "John Doe",
                "text": "Hello everyone, welcome to the meeting",
                "timestamp": 1234567890.123,
                "confidence": 0.95,
                "is_final": True
            }
        }


class RecallWebhookEvent(BaseModel):
    """
    Webhook event received from Recall.ai realtime endpoint

    Based on Recall.ai's realtime webhook format
    """
    event_type: str = Field(..., description="Event type (e.g., 'transcript.data', 'bot.status_change')")
    bot_id: str = Field(..., description="Recall bot ID")
    data: Dict[str, Any] = Field(..., description="Event payload")

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "transcript.data",
                "bot_id": "550e8400-e29b-41d4-a716-446655440000",
                "data": {
                    "speaker": "John Doe",
                    "words": [
                        {"text": "Hello", "start": 0.0, "end": 0.5},
                        {"text": "everyone", "start": 0.5, "end": 1.0}
                    ],
                    "is_final": True,
                    "timestamp": 1234567890.123
                }
            }
        }


class TranscriptWord(BaseModel):
    """Individual word in a transcript with timing"""
    text: str
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    confidence: Optional[float] = None


class RecallTranscriptData(BaseModel):
    """
    Parsed transcript data from Recall.ai webhook

    This matches Recall.ai's actual payload structure
    """
    speaker: str = Field(..., description="Speaker identifier")
    words: List[TranscriptWord] = Field(..., description="List of words with timestamps")
    is_final: bool = Field(True, description="Whether this is a final transcript")
    timestamp: float = Field(..., description="Event timestamp")


class WebSocketMessage(BaseModel):
    """
    Generic WebSocket message format sent to frontend clients
    """
    type: str = Field(..., description="Message type (transcript_chunk, meeting_status, error, etc.)")
    meeting_id: int = Field(..., description="Meeting identifier")
    data: Optional[Dict[str, Any]] = Field(None, description="Message payload")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "transcript_chunk",
                "meeting_id": 123,
                "data": {
                    "speaker": "John Doe",
                    "text": "Hello everyone",
                    "timestamp": 1234567890.123
                }
            }
        }


class ConnectionMessage(BaseModel):
    """Message sent when WebSocket connection is established"""
    type: str = "connection_established"
    meeting_id: int
    message: str = "Connected to real-time transcript stream"


class ErrorMessage(BaseModel):
    """Error message sent over WebSocket"""
    type: str = "error"
    meeting_id: int
    error: str
    details: Optional[str] = None


class MeetingStatusMessage(BaseModel):
    """Meeting status change notification"""
    type: str = "meeting_status"
    meeting_id: int
    status: str = Field(..., description="New meeting status (in_progress, completed, etc.)")
    timestamp: Optional[datetime] = None


# Response schemas for REST endpoints

class WebSocketConnectionInfo(BaseModel):
    """Information about active WebSocket connections"""
    meeting_id: int
    active_connections: int
    redis_subscribers: int


class RealtimeStatusResponse(BaseModel):
    """Status of real-time transcription for a meeting"""
    meeting_id: int
    realtime_enabled: bool
    websocket_url: str
    active_connections: int
    last_chunk_at: Optional[datetime] = None
