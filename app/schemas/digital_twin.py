"""
Digital Twin schemas
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class DigitalTwinCreate(BaseModel):
    name: str
    description: Optional[str] = None
    personality_traits: Optional[Dict[str, Any]] = None
    communication_style: Optional[str] = "professional"
    response_patterns: Optional[Dict[str, Any]] = None
    meeting_preferences: Optional[Dict[str, Any]] = None


class DigitalTwinUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    personality_traits: Optional[Dict[str, Any]] = None
    communication_style: Optional[str] = None
    response_patterns: Optional[Dict[str, Any]] = None
    meeting_preferences: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class DigitalTwinResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    personality_traits: Optional[Dict[str, Any]]
    communication_style: Optional[str]
    response_patterns: Optional[Dict[str, Any]]
    voice_trained: bool
    meeting_preferences: Optional[Dict[str, Any]]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True